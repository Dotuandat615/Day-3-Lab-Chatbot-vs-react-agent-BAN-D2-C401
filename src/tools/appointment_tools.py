"""
src/tools/appointment_tools.py
===============================
Các tool thao tác trực tiếp với database bệnh viện (SQLite).

NGUYÊN TẮC QUAN TRỌNG (tool-level error handling):
- Tool KHÔNG BAO GIỜ raise exception ra ngoài. Mọi lỗi đều được bắt
  và trả về dict có "status" + "error_code" để agent/loop xử lý an toàn.
  (Business Rule 7: không bịa dữ liệu; Rule 8: tool lỗi -> fallback.)
- Mọi truy vấn đều dùng tham số hoá (?) để tránh SQL injection.
- DB chỉ-đọc với các tool tìm kiếm; chỉ book_appointment mới ghi.

Cấu hình DB:
- Đường dẫn DB lấy từ biến môi trường HOSPITAL_DB_PATH,
  mặc định 'data/hospital.db'. Mỗi tool cũng nhận tham số db_path
  để dễ test độc lập (xem khối __main__).
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = os.environ.get("HOSPITAL_DB_PATH", "data/hospital.db")


# --------------------------------------------------------------------------- #
# Helper nội bộ
# --------------------------------------------------------------------------- #
def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # truy cập theo tên cột
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _ok(**fields: Any) -> Dict[str, Any]:
    return {"status": "success", "error_code": None, **fields}


def _err(error_code: str, message: str, **fields: Any) -> Dict[str, Any]:
    return {"status": "error", "error_code": error_code, "message": message, **fields}


def _classify_period(time_str: str) -> str:
    """'09:30' -> 'morning' | 'afternoon' | 'evening'."""
    try:
        hh = int(time_str.split(":")[0])
    except (ValueError, IndexError):
        return "unknown"
    if hh < 12:
        return "morning"
    if hh < 18:
        return "afternoon"
    return "evening"


def _normalize_period(pref: Optional[str]) -> Optional[str]:
    """Chuẩn hoá buổi mong muốn (VN/EN) -> morning/afternoon/evening, hoặc None nếu không lọc."""
    if pref is None:
        return None
    p = pref.strip().lower()
    mapping = {
        "sáng": "morning", "sang": "morning", "morning": "morning",
        "chiều": "afternoon", "chieu": "afternoon", "afternoon": "afternoon",
        "tối": "evening", "toi": "evening", "evening": "evening",
        "any": None, "bất kỳ": None, "bat ky": None, "": None,
    }
    return mapping.get(p, None)


def _next_id(conn: sqlite3.Connection, table: str, id_col: str, prefix: str) -> str:
    """Sinh ID kế tiếp dạng PREFIX + số (vd P003, A002) dựa trên ID lớn nhất hiện có."""
    rows = conn.execute(f"SELECT {id_col} FROM {table}").fetchall()
    max_num = 0
    for r in rows:
        m = re.search(r"(\d+)$", str(r[id_col]))
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"{prefix}{max_num + 1:03d}"


# --------------------------------------------------------------------------- #
# TOOL 1: search_available_slots
# --------------------------------------------------------------------------- #
def search_available_slots(
    specialty: str,
    date: str,
    preferred_time: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Tìm các slot CÒN TRỐNG theo chuyên khoa + ngày (+ buổi nếu có).

    Dùng khi: người dùng đã cho biết chuyên khoa và ngày, cần biết còn lịch nào trống.
    Trả về danh sách slot, sắp xếp sẵn theo thời gian chờ tăng dần.
    """
    try:
        conn = _get_connection(db_path)
    except Exception as e:  # noqa: BLE001
        return _err("TOOL_RUNTIME_ERROR", f"Không kết nối được database: {e}")

    try:
        period = _normalize_period(preferred_time)
        rows = conn.execute(
            """
            SELECT s.slot_id, d.doctor_id, d.doctor_name, d.room,
                   s.date, s.time, s.estimated_wait_time
            FROM appointment_slots s
            JOIN doctors    d  ON s.doctor_id    = d.doctor_id
            JOIN specialties sp ON d.specialty_id = sp.specialty_id
            WHERE s.available = 1
              AND s.date = ?
              AND LOWER(TRIM(sp.specialty_name)) = LOWER(TRIM(?))
            ORDER BY s.estimated_wait_time ASC, s.time ASC
            """,
            (date, specialty),
        ).fetchall()

        slots: List[Dict[str, Any]] = []
        for r in rows:
            if period and _classify_period(r["time"]) != period:
                continue
            slots.append(
                {
                    "slot_id": r["slot_id"],
                    "doctor_id": r["doctor_id"],
                    "doctor_name": r["doctor_name"],
                    "room": r["room"],
                    "date": r["date"],
                    "time": r["time"],
                    "estimated_wait_time": r["estimated_wait_time"],
                }
            )

        if not slots:
            return _err(
                "NO_SLOT_FOUND",
                f"Không tìm thấy slot trống cho chuyên khoa '{specialty}' vào ngày {date}"
                + (f" ({preferred_time})." if preferred_time else "."),
                slots=[],
            )
        return _ok(slots=slots)
    except Exception as e:  # noqa: BLE001
        return _err("TOOL_RUNTIME_ERROR", f"Lỗi khi tìm slot: {e}")
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# TOOL 2: estimate_wait_time
# --------------------------------------------------------------------------- #
def estimate_wait_time(
    doctor_id: str,
    date: str,
    time: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Lấy thời gian chờ dự kiến (phút) của một slot cụ thể.

    Dùng khi: cần xác nhận lại wait_time của một bác sĩ/giờ cụ thể trước khi tư vấn.
    """
    try:
        conn = _get_connection(db_path)
    except Exception as e:  # noqa: BLE001
        return _err("TOOL_RUNTIME_ERROR", f"Không kết nối được database: {e}")

    try:
        row = conn.execute(
            """
            SELECT slot_id, estimated_wait_time, available
            FROM appointment_slots
            WHERE doctor_id = ? AND date = ? AND time = ?
            """,
            (doctor_id, date, time),
        ).fetchone()

        if row is None:
            return _err(
                "NO_SLOT_FOUND",
                f"Không có slot nào của bác sĩ {doctor_id} vào {date} {time}.",
            )
        return _ok(
            slot_id=row["slot_id"],
            estimated_wait_time=row["estimated_wait_time"],
            available=bool(row["available"]),
        )
    except Exception as e:  # noqa: BLE001
        return _err("TOOL_RUNTIME_ERROR", f"Lỗi khi tra wait_time: {e}")
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# TOOL 3: rank_slots  (logic thuần, không đụng DB)
# --------------------------------------------------------------------------- #
def rank_slots(
    slots: List[Dict[str, Any]],
    criteria: str = "lowest_wait_time",
) -> Dict[str, Any]:
    """Chọn slot tốt nhất từ danh sách theo tiêu chí.

    Dùng khi: search_available_slots trả về nhiều slot và cần chọn 1 slot tốt nhất.
    criteria: lowest_wait_time (mặc định) | earliest_time | most_experienced_doctor.
    """
    try:
        if not slots:
            return _err("NO_SLOT_FOUND", "Danh sách slot rỗng, không có gì để xếp hạng.")

        if criteria == "earliest_time":
            best = min(slots, key=lambda s: str(s.get("time", "99:99")))
        elif criteria == "most_experienced_doctor":
            best = max(slots, key=lambda s: s.get("experience_years", -1))
        else:  # mặc định lowest_wait_time (Business Rule 4)
            criteria = "lowest_wait_time"
            best = min(slots, key=lambda s: s.get("estimated_wait_time", 10**9))

        ranked = sorted(
            slots,
            key=lambda s: s.get("estimated_wait_time", 10**9)
            if criteria == "lowest_wait_time"
            else str(s.get("time", "99:99")),
        )
        return _ok(best_slot=best, ranked=ranked, criteria=criteria)
    except Exception as e:  # noqa: BLE001
        return _err("TOOL_RUNTIME_ERROR", f"Lỗi khi xếp hạng slot: {e}")


# --------------------------------------------------------------------------- #
# TOOL 4: book_appointment  (ghi DB - có transaction)
# --------------------------------------------------------------------------- #
def book_appointment(
    patient_name: str,
    phone: str,
    slot_id: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Đặt lịch sau khi người dùng đã xác nhận.

    Dùng khi: đã chọn được slot và có đủ tên + số điện thoại bệnh nhân.
    Tự tạo bệnh nhân nếu chưa tồn tại (match theo phone), rồi tạo appointment
    và đánh dấu slot không còn trống.
    """
    try:
        conn = _get_connection(db_path)
    except Exception as e:  # noqa: BLE001
        return _err("TOOL_RUNTIME_ERROR", f"Không kết nối được database: {e}")

    try:
        # 1) Kiểm tra slot còn trống không (khoá hàng đọc trong transaction)
        slot = conn.execute(
            "SELECT slot_id, available FROM appointment_slots WHERE slot_id = ?",
            (slot_id,),
        ).fetchone()
        if slot is None:
            return _err("NO_SLOT_FOUND", f"Không tìm thấy slot {slot_id}.")
        if slot["available"] != 1:
            return _err("NO_SLOT_FOUND", f"Slot {slot_id} đã được đặt, vui lòng chọn slot khác.")

        # 2) Tìm bệnh nhân theo phone, chưa có thì tạo mới
        patient = conn.execute(
            "SELECT patient_id FROM patients WHERE phone = ?", (phone,)
        ).fetchone()
        if patient is None:
            patient_id = _next_id(conn, "patients", "patient_id", "P")
            conn.execute(
                "INSERT INTO patients (patient_id, patient_name, phone, date_of_birth) "
                "VALUES (?, ?, ?, ?)",
                (patient_id, patient_name, phone, None),
            )
        else:
            patient_id = patient["patient_id"]

        # 3) Tạo appointment + khoá slot (cùng 1 transaction)
        appointment_id = _next_id(conn, "appointments", "appointment_id", "A")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO appointments (appointment_id, patient_id, slot_id, status, created_at) "
            "VALUES (?, ?, ?, 'confirmed', ?)",
            (appointment_id, patient_id, slot_id, created_at),
        )
        conn.execute(
            "UPDATE appointment_slots SET available = 0 WHERE slot_id = ?", (slot_id,)
        )
        conn.commit()

        return _ok(
            appointment_id=appointment_id,
            patient_id=patient_id,
            slot_id=slot_id,
            message="Đặt lịch thành công.",
        )
    except Exception as e:  # noqa: BLE001
        conn.rollback()
        return _err("TOOL_RUNTIME_ERROR", f"Lỗi khi đặt lịch: {e}")
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# TOOL 5: suggest_alternative_dates
# --------------------------------------------------------------------------- #
def suggest_alternative_dates(
    specialty: str,
    from_date: str,
    max_results: int = 3,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Gợi ý các NGÀY khác còn slot trống khi ngày mong muốn đã hết (Business Rule 5).

    Dùng khi: search_available_slots trả NO_SLOT_FOUND cho ngày người dùng muốn.
    Trả về tối đa max_results ngày gần nhất (kể từ from_date), mỗi ngày lấy slot
    có thời gian chờ thấp nhất.
    """
    try:
        conn = _get_connection(db_path)
    except Exception as e:  # noqa: BLE001
        return _err("TOOL_RUNTIME_ERROR", f"Không kết nối được database: {e}")

    try:
        rows = conn.execute(
            """
            SELECT s.date, s.time, s.slot_id, d.doctor_name, s.estimated_wait_time
            FROM appointment_slots s
            JOIN doctors     d  ON s.doctor_id    = d.doctor_id
            JOIN specialties sp ON d.specialty_id = sp.specialty_id
            WHERE s.available = 1
              AND s.date > ?
              AND LOWER(TRIM(sp.specialty_name)) = LOWER(TRIM(?))
            ORDER BY s.date ASC, s.estimated_wait_time ASC
            """,
            (from_date, specialty),
        ).fetchall()

        # Mỗi ngày chỉ giữ slot tốt nhất (wait_time thấp nhất nhờ ORDER BY trên)
        best_by_date: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            if r["date"] not in best_by_date:
                best_by_date[r["date"]] = {
                    "date": r["date"],
                    "time": r["time"],
                    "slot_id": r["slot_id"],
                    "doctor_name": r["doctor_name"],
                    "estimated_wait_time": r["estimated_wait_time"],
                }

        alternatives = list(best_by_date.values())[:max_results]
        if not alternatives:
            return _err(
                "NO_SLOT_FOUND",
                f"Không còn ngày nào trống cho chuyên khoa '{specialty}' sau {from_date}.",
                alternatives=[],
            )
        return _ok(alternatives=alternatives)
    except Exception as e:  # noqa: BLE001
        return _err("TOOL_RUNTIME_ERROR", f"Lỗi khi gợi ý ngày thay thế: {e}")
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# TOOL 6: escalate_to_human
# --------------------------------------------------------------------------- #
def escalate_to_human(
    reason: str,
    user_query: str,
    db_path: Optional[str] = None,  # giữ chữ ký đồng nhất, không dùng DB
) -> Dict[str, Any]:
    """Chuyển yêu cầu sang điều phối viên (fallback an toàn).

    Dùng khi: vượt max_steps, timeout, lỗi không tự xử lý được, hoặc người dùng
    yêu cầu gặp người thật.
    """
    return {
        "status": "escalated",
        "error_code": None,
        "reason": reason,
        "user_query": user_query,
        "message": "Yêu cầu đã được chuyển sang điều phối viên.",
    }


# --------------------------------------------------------------------------- #
# Self-test: tạo DB tạm trong bộ nhớ-trên-đĩa, seed mini data, chạy thử từng tool.
# Cho phép Người 3 test độc lập trước khi Người 1 hoàn tất data/hospital.db.
#   chạy:  python -m src.tools.appointment_tools
# --------------------------------------------------------------------------- #
def _build_demo_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        DROP TABLE IF EXISTS appointments;
        DROP TABLE IF EXISTS appointment_slots;
        DROP TABLE IF EXISTS doctors;
        DROP TABLE IF EXISTS specialties;
        DROP TABLE IF EXISTS patients;

        CREATE TABLE specialties (specialty_id TEXT PRIMARY KEY, specialty_name TEXT, description TEXT);
        CREATE TABLE doctors (doctor_id TEXT PRIMARY KEY, doctor_name TEXT, specialty_id TEXT,
                              room TEXT, experience_years INTEGER);
        CREATE TABLE appointment_slots (slot_id TEXT PRIMARY KEY, doctor_id TEXT, date TEXT, time TEXT,
                                        available INTEGER, estimated_wait_time INTEGER);
        CREATE TABLE patients (patient_id TEXT PRIMARY KEY, patient_name TEXT, phone TEXT, date_of_birth TEXT);
        CREATE TABLE appointments (appointment_id TEXT PRIMARY KEY, patient_id TEXT, slot_id TEXT,
                                   status TEXT, created_at TEXT);

        INSERT INTO specialties VALUES
            ('S001','Tim mạch','Khám tim, huyết áp'),
            ('S002','Da liễu','Khám da, dị ứng');
        INSERT INTO doctors VALUES
            ('D001','Dr. Minh','S001','Phòng 201',10),
            ('D002','Dr. Lan','S001','Phòng 202',8),
            ('D003','Dr. Hương','S002','Phòng 305',6);
        INSERT INTO appointment_slots VALUES
            ('SL001','D001','2026-06-09','08:30',1,45),
            ('SL002','D002','2026-06-09','09:30',1,20),
            ('SL003','D001','2026-06-09','10:30',1,35),
            ('SL004','D003','2026-06-09','14:00',0,60),
            ('SL005','D001','2026-06-10','08:30',1,25);
        INSERT INTO patients VALUES ('P001','Nguyễn Văn Nam','0901234567','1998-05-12');
        """
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    import json
    import tempfile

    tmp = os.path.join(tempfile.gettempdir(), "demo_hospital.db")
    _build_demo_db(tmp)

    def show(title: str, result: Dict[str, Any]) -> None:
        print(f"\n=== {title} ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    show("search Tim mạch sáng 2026-06-09",
         search_available_slots("Tim mạch", "2026-06-09", "morning", db_path=tmp))

    res = search_available_slots("Tim mạch", "2026-06-09", db_path=tmp)
    show("rank_slots (lowest_wait_time)", rank_slots(res["slots"]))

    show("estimate_wait_time D002 09:30",
         estimate_wait_time("D002", "2026-06-09", "09:30", db_path=tmp))

    show("book SL002", book_appointment("Trần Thị Mai", "0912345678", "SL002", db_path=tmp))
    show("book SL002 lần 2 (đã kín)", book_appointment("X", "0900000000", "SL002", db_path=tmp))

    show("search Tim mạch chiều (NO_SLOT)",
         search_available_slots("Tim mạch", "2026-06-09", "afternoon", db_path=tmp))
    show("suggest_alternative_dates", suggest_alternative_dates("Tim mạch", "2026-06-09", db_path=tmp))

    show("escalate", escalate_to_human("MAX_STEPS_EXCEEDED", "Đặt lịch giúp tôi"))