"""
src/tools/tool_schema.py
=========================
Định nghĩa input/output schema cho TẤT CẢ tool bằng Pydantic.

Mục đích:
- Ép agent gọi tool đúng format (đúng tên field, đúng kiểu dữ liệu).
- Bắt lỗi thiếu thông tin ngay tại tầng schema -> map sang error_code
  MISSING_INFORMATION / VALIDATION_ERROR ở tool_registry.run_tool().
- Làm tài liệu sống cho Người 4 (agent) biết mỗi tool cần input gì.

Quy ước chung cho OUTPUT của mọi tool (xem appointment_tools.py):
    {
        "status": "success" | "error" | "escalated",
        "error_code": <None hoặc một trong ERROR_CODES>,
        "message": "<thông báo thân thiện, có thể None khi success>",
        ... các field riêng của từng tool (slots / best_slot / appointment_id ...)
    }
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# --------------------------------------------------------------------------- #
# Hằng số dùng chung
# --------------------------------------------------------------------------- #
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")   # YYYY-MM-DD
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")         # HH:MM

# Tập error_code thống nhất toàn hệ thống (khớp mục 16 trong INSTRUCTOR_ROLE).
ERROR_CODES = {
    "SUCCESS",
    "MISSING_INFORMATION",
    "NO_SLOT_FOUND",
    "PARSER_ERROR",
    "HALLUCINATED_TOOL",
    "TOOL_RUNTIME_ERROR",
    "TIMEOUT",
    "MAX_STEPS_EXCEEDED",
    "FALLBACK_TO_CHATBOT",
    "FALLBACK_TO_HUMAN",
    "VALIDATION_ERROR",
}


class PreferredTime(str, Enum):
    """Buổi khám mong muốn. Chấp nhận cả tiếng Việt lẫn tiếng Anh khi parse."""
    morning = "morning"
    afternoon = "afternoon"
    evening = "evening"
    any = "any"


class RankCriteria(str, Enum):
    """Tiêu chí xếp hạng slot."""
    lowest_wait_time = "lowest_wait_time"
    earliest_time = "earliest_time"
    most_experienced_doctor = "most_experienced_doctor"


# --------------------------------------------------------------------------- #
# INPUT SCHEMAS
# --------------------------------------------------------------------------- #
class SearchSlotInput(BaseModel):
    """Input cho search_available_slots()."""
    specialty: str = Field(..., description="Tên chuyên khoa, ví dụ 'Tim mạch', 'Da liễu'.")
    date: str = Field(..., description="Ngày khám, định dạng YYYY-MM-DD, ví dụ '2026-06-09'.")
    preferred_time: Optional[str] = Field(
        default=None,
        description="Buổi mong muốn: morning/afternoon/evening hoặc sáng/chiều/tối. Bỏ trống nếu không yêu cầu.",
    )

    @field_validator("specialty")
    @classmethod
    def _specialty_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Thiếu chuyên khoa (specialty).")
        return v.strip()

    @field_validator("date")
    @classmethod
    def _date_format(cls, v: str) -> str:
        if not _DATE_RE.match(v.strip()):
            raise ValueError("date phải có định dạng YYYY-MM-DD.")
        return v.strip()


class EstimateWaitTimeInput(BaseModel):
    """Input cho estimate_wait_time()."""
    doctor_id: str = Field(..., description="Mã bác sĩ, ví dụ 'D001'.")
    date: str = Field(..., description="Ngày khám, định dạng YYYY-MM-DD.")
    time: str = Field(..., description="Giờ khám, định dạng HH:MM, ví dụ '09:30'.")

    @field_validator("date")
    @classmethod
    def _date_format(cls, v: str) -> str:
        if not _DATE_RE.match(v.strip()):
            raise ValueError("date phải có định dạng YYYY-MM-DD.")
        return v.strip()

    @field_validator("time")
    @classmethod
    def _time_format(cls, v: str) -> str:
        if not _TIME_RE.match(v.strip()):
            raise ValueError("time phải có định dạng HH:MM.")
        return v.strip()


class RankSlotsInput(BaseModel):
    """Input cho rank_slots(). slots thường lấy trực tiếp từ output của search_available_slots."""
    slots: List[Dict[str, Any]] = Field(..., description="Danh sách slot cần xếp hạng.")
    criteria: str = Field(
        default="lowest_wait_time",
        description="Tiêu chí: lowest_wait_time | earliest_time | most_experienced_doctor.",
    )

    @field_validator("slots")
    @classmethod
    def _slots_not_empty(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not v:
            raise ValueError("Danh sách slots rỗng, không có gì để xếp hạng.")
        return v


class BookAppointmentInput(BaseModel):
    """Input cho book_appointment()."""
    patient_name: str = Field(..., description="Họ tên bệnh nhân.")
    phone: str = Field(..., description="Số điện thoại bệnh nhân.")
    slot_id: str = Field(..., description="Mã slot muốn đặt, ví dụ 'SL002'.")

    @field_validator("patient_name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Thiếu tên bệnh nhân (patient_name).")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def _phone_valid(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) < 9:
            raise ValueError("Số điện thoại (phone) không hợp lệ.")
        return v.strip()


class SuggestAlternativeDatesInput(BaseModel):
    """Input cho suggest_alternative_dates()."""
    specialty: str = Field(..., description="Tên chuyên khoa cần tìm ngày thay thế.")
    from_date: str = Field(..., description="Tìm các ngày trống KỂ TỪ ngày này (YYYY-MM-DD).")
    max_results: int = Field(default=3, ge=1, le=10, description="Số ngày gợi ý tối đa.")

    @field_validator("from_date")
    @classmethod
    def _date_format(cls, v: str) -> str:
        if not _DATE_RE.match(v.strip()):
            raise ValueError("from_date phải có định dạng YYYY-MM-DD.")
        return v.strip()


class EscalateInput(BaseModel):
    """Input cho escalate_to_human()."""
    reason: str = Field(..., description="Lý do escalate, ví dụ 'MAX_STEPS_EXCEEDED'.")
    user_query: str = Field(..., description="Yêu cầu gốc của người dùng để điều phối viên nắm ngữ cảnh.")


# --------------------------------------------------------------------------- #
# OUTPUT SCHEMAS (để document & validate output nếu cần)
# --------------------------------------------------------------------------- #
class SlotItem(BaseModel):
    slot_id: str
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    room: Optional[str] = None
    date: str
    time: str
    estimated_wait_time: int


class ToolResult(BaseModel):
    """Khung output chung. Các tool trả dict, schema này chỉ dùng để validate/test."""
    status: str
    error_code: Optional[str] = None
    message: Optional[str] = None

    @field_validator("error_code")
    @classmethod
    def _valid_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ERROR_CODES:
            raise ValueError(f"error_code '{v}' không nằm trong ERROR_CODES.")
        return v


# Map nhanh: tên tool -> schema input. tool_registry sẽ dùng map này.
INPUT_SCHEMA_BY_TOOL = {
    "search_available_slots": SearchSlotInput,
    "estimate_wait_time": EstimateWaitTimeInput,
    "rank_slots": RankSlotsInput,
    "book_appointment": BookAppointmentInput,
    "suggest_alternative_dates": SuggestAlternativeDatesInput,
    "escalate_to_human": EscalateInput,
}