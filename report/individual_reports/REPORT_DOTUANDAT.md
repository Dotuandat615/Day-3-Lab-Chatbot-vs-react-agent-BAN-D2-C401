# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Đỗ Tuấn Đạt
- **Student ID**: 2A202600818
- **Role**: Người 1 — Business Workflow + Database + Report + Integration
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

### Các module và tác vụ đã triển khai

| File / Tác vụ | Mô tả |
|:-------------|:------|
| [`data/`](../../data/) | Thiết kế và tạo toàn bộ **16 bảng CSV synthetic data** mô phỏng hệ thống bệnh viện thực tế (3.229 slots, 48 bác sĩ, 501 bệnh nhân...) |
| [`scripts/build_database.py`](../../scripts/build_database.py) | Script chuyển đổi toàn bộ CSV → SQLite `hospital.db` (804 KB) với DDL đầy đủ, foreign keys, WAL mode, post-processing `available` column |
| [`scripts/fix_db.py`](../../scripts/fix_db.py) | Script sửa lỗi data: đồng bộ `time ← start_time`, fix `NULL estimated_wait_time → 30` để tool backend hoạt động đúng |
| [`scripts/download_model.py`](../../scripts/download_model.py) | Script tự động tải Llama 3.2 3B Instruct Q4_K_M từ Hugging Face với progress bar |
| [`scripts/check_system.py`](../../scripts/check_system.py) | Script kiểm tra toàn bộ hệ thống: import tất cả module, chạy 6 test tool cases end-to-end để đảm bảo pipeline hoạt động |
| [`app.py`](../../app.py) | **Tích hợp tổng hợp**: Kết nối BaselineChatbot + ReActAgent + Tool Registry + Telemetry Logger + UI Components thành sản phẩm demo hoàn chỉnh |
| [`report/group_report/GROUP_REPORT_BAN-D2-C401.md`](../group_report/GROUP_REPORT_BAN-D2-C401.md) | Tổng hợp và viết Group Report đầy đủ: kiến trúc, flowchart, ablation experiments, RCA, production review |

---

### Code Highlights

#### 1. Thiết kế Schema Database — `scripts/build_database.py`

Database gồm **15 bảng quan hệ** được thiết kế để phản ánh đúng nghiệp vụ bệnh viện thực tế:

```python
# Trích DDL — build_database.py
DDL = """
CREATE TABLE IF NOT EXISTS appointment_slots (
    slot_id             TEXT PRIMARY KEY,
    doctor_id           TEXT,
    service_id          TEXT,
    date                TEXT NOT NULL,
    time                TEXT,
    start_time          TEXT,
    end_time            TEXT,
    status              TEXT,
    capacity            INTEGER,
    booked_count        INTEGER,
    estimated_wait_time INTEGER,   -- ← Cột quan trọng cho rank_slots tool
    is_telehealth       TEXT,
    room                TEXT,
    available           INTEGER DEFAULT 1,
    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
);
"""
```

**Quyết định thiết kế quan trọng**: Cột `available` được tính toán động sau khi import CSV, không lưu trực tiếp từ nguồn:

```python
def _compute_available(conn):
    conn.execute("""
        UPDATE appointment_slots
        SET available = CASE
            WHEN LOWER(TRIM(status)) IN ('available', 'open') THEN 1
            WHEN booked_count < capacity THEN 1
            ELSE 0
        END
    """)
```

Lý do: CSV nguồn không có cột `available` trực tiếp. Bằng cách tính lại sau import, đảm bảo dữ liệu nhất quán bất kể nguồn dữ liệu thay đổi.

---

#### 2. Synthetic Data Generation — 16 CSV Files

Dữ liệu giả lập được thiết kế bao quát đủ các kịch bản test của ReAct Agent:

```
data/
├── hospital_info.csv           →  1 bản ghi  (thông tin bệnh viện)
├── specialties.csv             → 12 bản ghi  (chuyên khoa)
├── symptom_specialty_map.csv   → 69 bản ghi  (map triệu chứng → chuyên khoa)
├── doctors.csv                 → 48 bản ghi  (bác sĩ + rating + phí)
├── services.csv                → 36 bản ghi  (dịch vụ theo chuyên khoa)
├── doctor_schedule_templates   → 254 bản ghi (lịch làm việc mẫu)
├── appointment_slots.csv       → 3.229 bản ghi (slot 2 tuần tới)  ← Core
├── wait_time_history.csv       → 288 bản ghi  (lịch sử thời gian chờ)
├── patients.csv                → 501 bản ghi  (bệnh nhân giả lập)
├── appointments.csv            → 1.142 bản ghi (lịch hẹn đã đặt)
├── reminder_logs.csv           → 853 bản ghi  (log nhắc lịch)
├── hospital_policies.csv       → 24 bản ghi   (FAQ / chính sách)
├── escalation_tickets.csv      → 120 bản ghi  (ticket escalate)
├── feedback_reviews.csv        → 350 bản ghi  (review sau khám)
├── payment_coverage_types.csv  →  3 bản ghi   (loại thanh toán)
└── data_dictionary.csv         → 16 bản ghi   (mô tả schema)
```

**Tổng: 7.016 bản ghi — Database size: 804 KB**

---

#### 3. System Integration — `app.py`

Tổng hợp code từ 4 thành viên còn lại thành pipeline hoạt động hoàn chỉnh:

```
Người 2: BaselineChatbot (src/chatbot/baseline_chatbot.py)
         + Local LLM Provider (src/providers/local_llm.py)
    │
Người 3: Tool Registry (src/tools/tool_registry.py)
         + Appointment Tools (src/tools/appointment_tools.py)
    │                                           │
Người 4: ReActAgent (src/agent/agent.py)        │
         + Guardrail (src/agent/guardrail.py)   │
    │                                           │
Người 5: UI Components (src/ui/components.py)  │
         + Telemetry Logger + Metrics           │
    │                                           │
    └───────────────── app.py ──────────────────┘
                   (Tổng hợp bởi Người 1)
```

**Công việc tích hợp cụ thể:**
- Kết nối `get_llm_provider()` → `run_chatbot()` / `run_agent()` với đúng signature
- Wiring tool registry vào agent: build `tools` list từ `TOOL_REGISTRY`
- Đăng ký `custom_log_event` hook để bắt trace từ agent loop
- Xử lý các edge case: `llm is None` → demo mode, error_code detection, fallback routing

---

#### 4. Local Model Setup — `scripts/download_model.py`

```python
URL = "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
DEST = "models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

def download_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    percent = (downloaded / total_size) * 100
    sys.stdout.write(f"\rDownloading: {percent:.1f}% ({downloaded/(1024*1024):.1f} MB)")
```

Script tải Llama 3.2 3B Instruct (~2.02 GB) với real-time progress. Sau khi tải, cấu hình `.env` để `LocalProvider` load model và chạy offline hoàn toàn.

---

#### 5. End-to-End System Check — `scripts/check_system.py`

Script xác nhận toàn bộ pipeline hoạt động trước khi demo:

```python
mods_to_test = [
    'src.telemetry.logger', 'src.telemetry.metrics',
    'src.providers.base', 'src.providers.local_llm',
    'src.chatbot.baseline_chatbot', 'src.tools.tool_registry',
    'src.agent.agent', 'src.core.openai_provider', ...
]
# 6 tool test cases: search, hallucinated_tool, missing_field,
# bad_date_format, suggest_alternative_dates, rank_slots
```

---

### Cách code tương tác với toàn bộ hệ thống

```
[Data Layer - Người 1]
  data/hospital.db ← build_database.py ← 16 CSV files
        │
        ▼
[Tool Layer - Người 3]
  appointment_tools.py → kết nối SQLite, trả về dict chuẩn
        │
        ▼
[Agent Layer - Người 4]
  ReActAgent.run() → gọi tools qua tool_registry.run_tool()
        │
        ▼
[Chatbot Layer - Người 2]
  BaselineChatbot.chat() → gọi LLM trực tiếp (không tool)
        │
        ▼
[Integration - Người 1, app.py]
  run_agent() / run_chatbot() → kết nối tất cả layers
        │
        ▼
[UI Layer - Người 5]
  Streamlit render_trace() + render_metrics()
```

---

## II. Debugging Case Study (10 Points)

### Vấn đề 1: `appointment_slots.time` bị NULL → Tool `search_available_slots` không trả về kết quả

**Mô tả:** Sau khi import CSV vào SQLite, cột `time` trong bảng `appointment_slots` toàn bộ bị `NULL`. Tool `search_available_slots` truy vấn `WHERE time IS NOT NULL` → trả về `NO_SLOT_FOUND` với mọi query.

**Diagnosis từ database:**
```sql
SELECT COUNT(*) FROM appointment_slots WHERE time IS NULL;
-- Kết quả: 3229 (toàn bộ!)

SELECT COUNT(*) FROM appointment_slots WHERE start_time IS NOT NULL;
-- Kết quả: 3229 (start_time đầy đủ, time bị bỏ trống trong CSV)
```

**Root Cause:** CSV gốc lưu thời gian vào cột `start_time`, nhưng tool backend query cột `time`. Hai cột cùng tồn tại trong schema nhưng CSV chỉ populate `start_time`.

**Solution — `scripts/fix_db.py`:**
```python
# Đồng bộ time ← start_time
conn.execute("UPDATE appointment_slots SET time = start_time WHERE start_time IS NOT NULL")
conn.commit()

# Sau fix: kiểm tra
avail = conn.execute(
    "SELECT COUNT(*) FROM appointment_slots WHERE available=1 AND time IS NOT NULL"
).fetchone()[0]
print(f"Available slots with valid time: {avail}")  # → 1847 slots
```

**Kết quả:** Sau fix, `search_available_slots` trả về đúng kết quả với đầy đủ slot.

---

### Vấn đề 2: `ModuleNotFoundError` khi tích hợp code từ nhiều thành viên

**Mô tả:** Khi tổng hợp code từ 4 thành viên, mỗi người dùng import path khác nhau:
- Người 2 dùng: `from src.providers.base import LLMProvider`
- Người 4 dùng: `from src.core.llm_provider import LLMProvider`
- Người 3 dùng: `from appointment_tools import ...` (chạy trực tiếp)

Khi chạy qua `app.py`, nhiều module không resolve được import.

**Root Cause:** Không có thống nhất về package structure. Mỗi người test file của họ trong isolation, không trong context của project root.

**Solution — Pattern try/except import:**
```python
# baseline_chatbot.py - xử lý cả 2 import path
try:
    from src.providers.base import LLMProvider as _ProviderBase
except ImportError:
    from src.core.llm_provider import LLMProvider as _ProviderBase  # fallback

# tool_registry.py - tương tự
try:
    from . import appointment_tools as T
    from .tool_schema import (BookAppointmentInput, ...)
except ImportError:  # khi chạy file lẻ
    import appointment_tools as T
    from tool_schema import (...)
```

**Thêm sys.path fix trong `app.py`:**
```python
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
```

**Bài học:** Cần thống nhất package structure ngay từ đầu và test integration sớm, không đợi đến cuối.

---

### Vấn đề 3: `estimated_wait_time` NULL → `rank_slots` tool crash

**Mô tả:** Sau khi `search_available_slots` trả về danh sách slot, agent gọi `rank_slots`. Tool này sort theo `estimated_wait_time`, nhưng một số slot có giá trị `NULL` → Python raise `TypeError: '<' not supported between instances of 'NoneType' and 'int'`.

**Diagnosis từ log:**
```json
{
  "event": "TOOL_ERROR",
  "tool": "rank_slots",
  "error": "TypeError: '<' not supported between instances of 'NoneType' and 'int'"
}
```

**Solution:**
```python
# scripts/fix_db.py - fix NULL → default 30 phút
conn.execute("""
    UPDATE appointment_slots
    SET estimated_wait_time = 30
    WHERE estimated_wait_time IS NULL OR CAST(estimated_wait_time AS TEXT) = ''
""")
```

**Thêm defensive sort trong tool:**
```python
# appointment_tools.py - sort an toàn với NULL
slots.sort(key=lambda x: x.get("estimated_wait_time") or 9999)
```

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Reasoning — Dữ liệu là nền tảng, không phải LLM

Trải nghiệm thực tế khi xây dựng database cho thấy: **chất lượng dữ liệu quyết định 50% thành công của Agent**, không phải sức mạnh của LLM.

Khi `time = NULL`, dù LLM có reasoning tốt đến đâu, tool vẫn trả về `NO_SLOT_FOUND` → Agent thất bại hoàn toàn. Ngược lại, khi database sạch và đầy đủ, ngay cả model nhỏ (Llama 3.2 3B) cũng có thể hoàn thành task multi-step.

**Bài học**: Trong production, 80% công sức nên dành cho data pipeline và data quality, không phải model tuning.

---

### 2. Reliability — Integration là điểm yếu nhất của hệ thống đa người

Khi tích hợp code từ 4 thành viên, tôi nhận ra rằng **interface contract giữa các module quan trọng hơn implementation của từng module**.

Cụ thể:
- Agent (`Người 4`) gọi tool và nhận dict. Tool (`Người 3`) trả về dict. Nhưng agent expect `{"status": "success", "slots": [...]}` còn tool đôi khi trả về `{"data": [...]}` mà không có `status`.
- Chatbot (`Người 2`) trả về `{"content": "..."}` nhưng app.py expect `{"answer": "..."}`.

Phải viết thêm adapter layer trong `app.py` để normalize output từ mỗi thành viên.

**Bài học**: Hệ thống multi-person cần định nghĩa **API contract** (input/output dict schema) trước khi mỗi người bắt đầu code.

---

### 3. Observation — Chatbot "tự tin sai", Agent "thừa nhận không biết"

Khi test với query `"Khám Tim mạch sáng thứ 3, bác sĩ Lan có rảnh không?"`:

- **Chatbot baseline** trả lời ngay: *"Bác sĩ Lan có lịch sáng thứ 3, bạn có thể đến lúc 9h30."* — Không có thông tin này trong database, hoàn toàn hallucinate.
- **Agent v2** gọi `search_available_slots` → thực sự tìm trong database → trả về slot thực tế với wait time chính xác.

Sự khác biệt cốt lõi không phải ở "AI thông minh hơn", mà ở **nguồn thông tin**:
- Chatbot lấy từ **tham số đã học** (có thể outdated, sai) 
- Agent lấy từ **database thực tế** (luôn đúng tại thời điểm query)

Điều này giải thích tại sao Chatbot phù hợp cho FAQ tĩnh, Agent phù hợp cho dữ liệu động.

---

## IV. Future Improvements (5 Points)

### Scalability — Database Production

Hiện tại dùng SQLite phù hợp cho demo. Để scale lên production:

- **PostgreSQL + pgvector**: Hỗ trợ concurrent write (nhiều user đặt lịch cùng lúc), semantic search cho `symptom_specialty_map` (tìm chuyên khoa theo mô tả triệu chứng dạng tự nhiên).
- **Data versioning**: Dùng Alembic để track schema migration, tránh phải chạy lại `build_database.py` mỗi lần thay đổi cấu trúc.
- **Synthetic data pipeline**: Thay CSV tĩnh bằng Faker + custom generator để tự động tạo slot mới mỗi tuần (hiện tại slot chỉ có trong 2 tuần cố định).

### Safety — Data Integrity

- **Booking conflict detection**: Hiện tại `book_appointment` không check concurrent booking. Hai user có thể book cùng 1 slot trong cùng giây. Cần `SELECT ... FOR UPDATE` (PostgreSQL) hoặc `BEGIN EXCLUSIVE` (SQLite).
- **Audit trail**: Thêm bảng `audit_log` ghi lại mọi thay đổi booking (ai đặt, khi nào, từ đâu) để hỗ trợ dispute resolution.

### Performance — Indexing

Hiện tại database chưa có index. Với production load:

```sql
-- Index quan trọng nhất cho search_available_slots
CREATE INDEX idx_slots_specialty_date ON appointment_slots(date, available);
CREATE INDEX idx_slots_doctor ON appointment_slots(doctor_id, date);
```

Ước tính: Query time giảm từ O(n) full scan → O(log n) index scan, đặc biệt quan trọng khi `appointment_slots` có >100K rows.

### Multi-Hospital Support

Mở rộng schema thêm `hospital_id` foreign key vào tất cả bảng, cho phép một agent phục vụ mạng lưới nhiều cơ sở y tế. Kết hợp với multi-agent architecture (một coordinator agent phân phối request đến sub-agent của từng bệnh viện).

---

> [!NOTE]
> Báo cáo này thuộc về **Đỗ Tuấn Đạt (2A202600818)** — Role 1: Business Workflow + Database + Integration.
> Đặt tại `report/individual_reports/REPORT_DoTuanDat.md`.
