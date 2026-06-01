"""
src/tools/tool_registry.py
===========================
Registry trung tâm cho toàn bộ tool. Đây là CỬA NGÕ DUY NHẤT mà agent
(Người 4) nên dùng để gọi tool: chỉ cần biết tên tool + dict input.

Cung cấp:
- TOOL_REGISTRY            : tên tool -> ToolSpec (hàm, schema, mô tả, when_to_use).
- get_tool_names()         : danh sách tool hợp lệ -> dùng làm WHITELIST (chống HALLUCINATED_TOOL).
- is_valid_tool(name)      : kiểm tra nhanh tool có hợp lệ không.
- get_tools_description()  : sinh chuỗi mô tả để chèn vào system prompt của agent.
- run_tool(name, raw_input): validate input bằng Pydantic + chạy tool + bắt MỌI lỗi
                             -> luôn trả dict chuẩn {status, error_code, message, ...}.

Đây là nơi xử lý các failure ở tầng điều phối tool:
  HALLUCINATED_TOOL  -> agent gọi tên tool không tồn tại.
  MISSING_INFORMATION/VALIDATION_ERROR -> input thiếu field bắt buộc / sai định dạng.
  TOOL_RUNTIME_ERROR -> lỗi bất ngờ khi chạy tool.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

# Hỗ trợ cả import theo package (from src.tools...) lẫn chạy trực tiếp.
try:
    from . import appointment_tools as T
    from .tool_schema import (
        BookAppointmentInput,
        EscalateInput,
        EstimateWaitTimeInput,
        RankSlotsInput,
        SearchSlotInput,
        SuggestAlternativeDatesInput,
    )
except ImportError:  # pragma: no cover - fallback khi chạy file lẻ
    import appointment_tools as T  # type: ignore
    from tool_schema import (  # type: ignore
        BookAppointmentInput,
        EscalateInput,
        EstimateWaitTimeInput,
        RankSlotsInput,
        SearchSlotInput,
        SuggestAlternativeDatesInput,
    )


@dataclass(frozen=True)
class ToolSpec:
    name: str
    func: Callable[..., Dict[str, Any]]
    input_schema: Type[BaseModel]
    description: str   # tool LÀM GÌ
    when_to_use: str   # KHI NÀO agent nên gọi


# --------------------------------------------------------------------------- #
# Đăng ký tool. Mô tả viết rõ để LLM nhỏ (Phi-3) biết khi nào dùng tool nào.
# --------------------------------------------------------------------------- #
TOOL_REGISTRY: Dict[str, ToolSpec] = {
    "search_available_slots": ToolSpec(
        name="search_available_slots",
        func=T.search_available_slots,
        input_schema=SearchSlotInput,
        description="Tìm các slot khám CÒN TRỐNG theo chuyên khoa và ngày. YÊU CẦU: 'specialty' PHẢI là tiếng Việt có dấu (ví dụ 'Tim mạch', 'Da liễu'), và 'date' PHẢI ở định dạng YYYY-MM-DD (ví dụ '2026-06-09').",
        when_to_use="Khi đã biết chuyên khoa + ngày và cần xem còn lịch trống nào. Thường là bước đầu tiên.",
    ),
    "estimate_wait_time": ToolSpec(
        name="estimate_wait_time",
        func=T.estimate_wait_time,
        input_schema=EstimateWaitTimeInput,
        description="Tra thời gian chờ dự kiến (phút) của một slot cụ thể. YÊU CẦU: 'date' PHẢI ở định dạng YYYY-MM-DD (ví dụ '2026-06-09').",
        when_to_use="Khi cần xác nhận lại wait_time của một slot trước khi tư vấn cho người dùng.",
    ),
    "rank_slots": ToolSpec(
        name="rank_slots",
        func=T.rank_slots,
        input_schema=RankSlotsInput,
        description="Xếp hạng danh sách slot và chọn slot tốt nhất theo tiêu chí (mặc định: ít chờ nhất).",
        when_to_use="Khi search_available_slots trả về nhiều slot và cần chọn 1 slot tốt nhất.",
    ),
    "book_appointment": ToolSpec(
        name="book_appointment",
        func=T.book_appointment,
        input_schema=BookAppointmentInput,
        description="Đặt lịch cho một slot, cần tên + số điện thoại bệnh nhân + slot_id.",
        when_to_use="CHỈ gọi sau khi người dùng đã xác nhận slot và đã cung cấp tên + số điện thoại.",
    ),
    "suggest_alternative_dates": ToolSpec(
        name="suggest_alternative_dates",
        func=T.suggest_alternative_dates,
        input_schema=SuggestAlternativeDatesInput,
        description="Gợi ý các ngày khác còn slot trống khi ngày mong muốn đã hết. YÊU CẦU: 'specialty' PHẢI là tiếng Việt có dấu, và 'from_date' PHẢI ở định dạng YYYY-MM-DD (ví dụ '2026-06-09').",
        when_to_use="Khi search_available_slots trả về NO_SLOT_FOUND cho ngày người dùng muốn.",
    ),
    "escalate_to_human": ToolSpec(
        name="escalate_to_human",
        func=T.escalate_to_human,
        input_schema=EscalateInput,
        description="Chuyển yêu cầu sang điều phối viên (con người) - fallback an toàn.",
        when_to_use="Khi vượt max_steps, timeout, lỗi không tự xử lý được, hoặc người dùng đòi gặp người thật.",
    ),
}


# --------------------------------------------------------------------------- #
# Tiện ích cho agent / prompt
# --------------------------------------------------------------------------- #
def get_tool_names() -> List[str]:
    """Whitelist tên tool hợp lệ. Người 4 dùng để chặn HALLUCINATED_TOOL."""
    return list(TOOL_REGISTRY.keys())


def is_valid_tool(name: str) -> bool:
    return name in TOOL_REGISTRY


def get_tool(name: str) -> Optional[ToolSpec]:
    return TOOL_REGISTRY.get(name)


def get_tools_description() -> str:
    """Sinh đoạn mô tả tool để chèn vào system prompt của agent ReAct."""
    lines: List[str] = ["Bạn CHỈ được phép dùng các tool sau (không được bịa tool khác):", ""]
    for spec in TOOL_REGISTRY.values():
        fields = list(spec.input_schema.model_fields.keys())
        lines.append(f"- {spec.name}({', '.join(fields)})")
        lines.append(f"    Mô tả: {spec.description}")
        lines.append(f"    Khi nào dùng: {spec.when_to_use}")
        lines.append("")
    return "\n".join(lines).rstrip()


# --------------------------------------------------------------------------- #
# run_tool: cửa ngõ duy nhất để chạy tool an toàn
# --------------------------------------------------------------------------- #
def _format_validation_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", []))
        parts.append(f"{loc}: {err.get('msg')}")
    return "; ".join(parts)


def run_tool(
    name: str,
    raw_input: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate input -> chạy tool -> bắt mọi lỗi. LUÔN trả dict chuẩn.

    Args:
        name: tên tool agent muốn gọi.
        raw_input: dict input agent sinh ra (đã parse từ Action Input).
        db_path: tùy chọn, ép đường dẫn DB (hữu ích khi test).
    """
    raw_input = raw_input or {}

    # 1) Whitelist: chống agent bịa tool không tồn tại.
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        return {
            "status": "error",
            "error_code": "HALLUCINATED_TOOL",
            "message": (
                f"Tool '{name}' không tồn tại. "
                f"Chỉ được dùng: {', '.join(get_tool_names())}."
            ),
            "tool_name": name,
            "available_tools": get_tool_names(),
        }

    # 2) Validate input bằng Pydantic schema.
    try:
        validated = spec.input_schema(**raw_input)
    except ValidationError as e:
        msg = _format_validation_error(e)
        # Thiếu field bắt buộc -> coi là MISSING_INFORMATION, còn lại VALIDATION_ERROR.
        code = "MISSING_INFORMATION" if "Field required" in str(e) or "Thiếu" in msg else "VALIDATION_ERROR"
        return {
            "status": "error",
            "error_code": code,
            "message": f"Input cho tool '{name}' không hợp lệ: {msg}",
            "tool_name": name,
        }
    except TypeError as e:
        return {
            "status": "error",
            "error_code": "VALIDATION_ERROR",
            "message": f"Input cho tool '{name}' sai kiểu: {e}",
            "tool_name": name,
        }

    # 3) Chạy tool. Truyền db_path cho các tool có hỗ trợ.
    kwargs: Dict[str, Any] = validated.model_dump()
    if db_path is not None and "db_path" in spec.func.__code__.co_varnames:
        kwargs["db_path"] = db_path

    try:
        result = spec.func(**kwargs)
    except Exception as e:  # noqa: BLE001 - chốt chặn cuối cùng
        return {
            "status": "error",
            "error_code": "TOOL_RUNTIME_ERROR",
            "message": f"Lỗi khi chạy tool '{name}': {e}",
            "tool_name": name,
        }

    # 4) Đảm bảo output có đủ field khung chuẩn.
    if isinstance(result, dict):
        result.setdefault("error_code", None)
        result.setdefault("tool_name", name)
    return result


if __name__ == "__main__":
    import json
    import os
    import tempfile

    # Dựng DB demo để test run_tool end-to-end.
    tmp = os.path.join(tempfile.gettempdir(), "demo_hospital_registry.db")
    T._build_demo_db(tmp)

    print("--- Whitelist ---")
    print(get_tool_names())
    print("\n--- Mô tả tool cho prompt ---")
    print(get_tools_description())

    def show(title: str, result: Dict[str, Any]) -> None:
        print(f"\n=== {title} ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    show("OK: search hợp lệ",
         run_tool("search_available_slots",
                  {"specialty": "Tim mạch", "date": "2026-06-09", "preferred_time": "morning"},
                  db_path=tmp))
    show("HALLUCINATED_TOOL", run_tool("check_doctor_schedule", {"x": 1}, db_path=tmp))
    show("MISSING_INFORMATION (thiếu date)",
         run_tool("search_available_slots", {"specialty": "Tim mạch"}, db_path=tmp))
    show("VALIDATION_ERROR (sai định dạng date)",
         run_tool("search_available_slots", {"specialty": "Tim mạch", "date": "09/06/2026"}, db_path=tmp))