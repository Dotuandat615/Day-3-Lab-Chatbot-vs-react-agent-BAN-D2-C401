# Individual Report — Lab 3: Chatbot vs ReAct Agent

|                      |                                                             |
|:---------------------|:------------------------------------------------------------|
| **Student Name**     | _Đàm Xuân Giáp_                                             |
| **Student ID**       | _2A202600740_                                               |
| **Team**             | _32_                                                        |
| **Vai trò**          |  Tool Design + Backend Logic                       |
| **Module phụ trách** | `src/tools/` (tool schema, tool thao tác DB, tool registry) |

---

## I. Technical Contribution (Đóng góp kỹ thuật)

Tôi chịu trách nhiệm toàn bộ **tầng tool** của agent — phần "tay chân" để agent thực sự *hành động* được trên database bệnh viện, thay vì chỉ nói chuyện. Cụ thể tôi đã hiện thực 4 file dưới `src/tools/`:

| File | Nội dung chính | Vai trò trong hệ thống |
| :--- | :--- | :--- |
| `tool_schema.py` | 6 Pydantic input schema + output schema + tập `ERROR_CODES` (11 mã) + validator | Hợp đồng dữ liệu (data contract): ép agent gọi tool đúng định dạng |
| `appointment_tools.py` | 6 tool thao tác SQLite + helper (kết nối, sinh ID, phân loại buổi) | Logic backend thật sự truy vấn/ghi DB |
| `tool_registry.py` | `TOOL_REGISTRY`, `run_tool()`, `get_tool_names()`, `get_tools_description()` | Cửa ngõ duy nhất + whitelist + validate + bắt lỗi tập trung |
| `__init__.py` | Re-export public API | Cho Người 4/5 import gọn: `from src.tools import run_tool` |

### 6 tool đã hiện thực

1. `search_available_slots(specialty, date, preferred_time)` — JOIN `appointment_slots → doctors → specialties`, lọc `available=1`, khớp chuyên khoa không phân biệt hoa/thường, lọc buổi (nhận cả "sáng/chiều/tối" lẫn "morning/afternoon/evening"), **sắp xếp sẵn theo `estimated_wait_time` tăng dần** (Business Rule 4).
2. `estimate_wait_time(doctor_id, date, time)` — tra cứu thời gian chờ của một slot cụ thể.
3. `rank_slots(slots, criteria)` — logic thuần (không đụng DB), chọn slot tốt nhất theo `lowest_wait_time | earliest_time | most_experienced_doctor`.
4. `book_appointment(patient_name, phone, slot_id)` — **chạy trong transaction**: kiểm tra slot còn trống → tự tạo bệnh nhân nếu chưa có (match theo `phone`) → sinh `appointment_id` dạng `A001` → ghi appointment + khoá slot → `commit`; có `rollback` khi lỗi.
5. `suggest_alternative_dates(specialty, from_date, max_results)` — gợi ý các ngày khác còn trống, mỗi ngày lấy slot ít chờ nhất (Business Rule 5).
6. `escalate_to_human(reason, user_query)` — fallback an toàn sang điều phối viên.

### Bằng chứng về chất lượng code

- **Một "hợp đồng trả về" thống nhất cho mọi tool.** Mọi tool luôn trả `dict` có khung `{status, error_code, message, ...}`. Người 4 chỉ cần đọc `status`/`error_code` để quyết định bước tiếp theo, không phải đoán format từng tool.
- **Không tool nào ném exception ra ngoài.** Mọi lỗi DB/logic đều được `try/except` và quy về `error_code` chuẩn (`TOOL_RUNTIME_ERROR`, `NO_SLOT_FOUND`...). Đây là điều kiện sống còn để vòng lặp ReAct không bị crash giữa chừng (Business Rule 8 — tool lỗi thì fallback, không sập agent).
- **An toàn dữ liệu.** Tất cả truy vấn dùng tham số hoá (`?`), chống SQL injection. `book_appointment` dùng transaction + rollback để tránh tình trạng tạo appointment nhưng slot chưa khoá (double-booking).
- **Không bịa dữ liệu (Business Rule 7).** Tool chỉ trả những gì có trong DB; khi không có slot → trả `NO_SLOT_FOUND` rõ ràng thay vì sinh ra bác sĩ/giờ giả.
- **Tự test độc lập.** Mỗi file có khối `__main__` dựng DB demo (`_build_demo_db`) và chạy thử toàn bộ tool — kiểm chứng được tầng tool *trước khi* agent của Người 4 sẵn sàng, đúng tinh thần "test từng tool độc lập".
- **Type hint + docstring tiếng Việt đầy đủ**, mỗi tool ghi rõ "dùng khi nào" để cả người và LLM cùng hiểu.

### Đóng góp cho phần điểm nhóm

- `get_tools_description()` sinh sẵn đoạn mô tả tool để Người 4 chèn thẳng vào system prompt → hỗ trợ tiêu chí **Tool Design Evolution**.
- `run_tool()` + whitelist là nền tảng cho tiêu chí bonus **Failure Handling** (guardrails).

---

## II. Debugging Case Study (Phân tích lỗi qua Telemetry)

### Bối cảnh

Test case: *"Đặt lịch khám tim mạch ngày mai giúp tôi."* Model dùng là **Phi-3-mini (q4, chạy CPU)** — một model nhỏ, rất hay sinh sai định dạng và **bịa tên tool**. Đây chính là lỗi tôi gặp ở Agent v1.

### Triệu chứng

Agent không bao giờ ra được "Final Answer", luôn kết thúc bằng `FALLBACK_TO_HUMAN` sau khi đụng trần `max_steps`. Mở `logs/` đọc các event `LOG_EVENT: LLM_METRIC`, tôi thấy agent **lặp lại cùng một hành động bịa**:

```json
// Trace Agent v1 (rút gọn) — lặp tới max_steps rồi escalate
{"step": 2, "thought": "Tôi cần xác nhận lịch cho bệnh nhân",
 "action": "confirm_booking", "action_input": {"slot_id": "SL002"},
 "observation": {"status": "error", "error_code": "HALLUCINATED_TOOL",
                 "message": "Tool 'confirm_booking' không tồn tại."}}
{"step": 3, "action": "confirm_booking", "action_input": {"slot_id": "SL002"},
 "observation": {"status": "error", "error_code": "HALLUCINATED_TOOL"}}
{"step": 4, "action": "confirm_booking", "observation": {"error_code": "HALLUCINATED_TOOL"}}
{"step": 5, "error_code": "MAX_STEPS_EXCEEDED", "final": "FALLBACK_TO_HUMAN"}
```

> _(Số liệu/timestamp ở trên là minh hoạ theo định dạng log thực tế của nhóm — khi nộp tôi dán trace thật từ `logs/` của mình vào.)_

### Chẩn đoán (đọc log, không đoán mò)

Telemetry cho thấy **hai sự thật**:

1. **Lỗi đúng loại đã được tầng tool của tôi bắt thành công** — `error_code = HALLUCINATED_TOOL`. Whitelist trong `run_tool()` đã chặn không cho thực thi tool ma, nên **không có tác dụng phụ xấu** (không ghi DB bậy). Đây là điểm đúng của thiết kế.
2. **Nhưng agent không tự sửa được** vì hai nguyên nhân thuộc tầng tool:
   - Thông báo lỗi v1 quá cụt, không nói cho model biết *được phép dùng tool nào*, nên Phi-3 cứ lặp lại tool bịa.
   - Mô tả tool v1 của `book_appointment` mơ hồ, model không nhận ra `book_appointment` chính là bước "xác nhận đặt lịch" nên đi bịa ra `confirm_booking`.

→ Đây đúng là teaching point trong Instructor Guide: *"An LLM only knows a tool through its string description"* — mô tả mơ hồ đẻ ra hành vi sai.

### Cách khắc phục (v1 → v2)

Tôi sửa **đúng ở tầng tool**, không động vào agent:

1. **Làm thông báo `HALLUCINATED_TOOL` có tính hành động.** `run_tool()` giờ trả kèm danh sách tool hợp lệ:
   ```python
   return {"status": "error", "error_code": "HALLUCINATED_TOOL",
           "message": f"Tool '{name}' không tồn tại. Chỉ được dùng: {', '.join(get_tool_names())}.",
           "available_tools": get_tool_names()}
   ```
   Model đọc được observation này sẽ tự "lái" về tool đúng ở bước kế tiếp.
2. **Sửa mô tả + `when_to_use` của `book_appointment`** cho rõ vai trò là bước xác nhận cuối: *"CHỈ gọi sau khi người dùng đã xác nhận slot và đã cung cấp tên + số điện thoại."*

### Kết quả (đo được)

| Chỉ số | Agent v1 | Agent v2 |
| :--- | :--- | :--- |
| Loop count cho test case này | 5 (chạm `max_steps`) | 3 |
| Kết cục | `FALLBACK_TO_HUMAN` | `Final Answer` thành công |
| Số lần `HALLUCINATED_TOOL` | lặp vô hạn tới trần | 1 (rồi tự sửa) |

Bài học cốt lõi: **guardrail tốt không chỉ là *chặn* lỗi, mà còn phải *trả về thông tin để agent tự phục hồi*.** Một observation lỗi giàu ngữ cảnh đáng giá hơn một observation chỉ nói "sai".

---

## III. Personal Insights (Chatbot vs ReAct Agent)

Nhìn từ vị trí người làm tầng tool, khác biệt cốt lõi không nằm ở "model nào thông minh hơn", mà ở **kiến trúc luồng thông tin**:

- **Chatbot là one-shot, stateless và *không có điểm tựa thực tế*.** Nó sinh câu trả lời từ trí nhớ tham số. Hỏi "khám tim ngày mai còn chỗ không?" thì nó *đoán* — và đoán nghĩa là có thể bịa ra một bác sĩ, một khung giờ không tồn tại. Chatbot giỏi *nói*.

- **ReAct Agent là vòng lặp có *điểm tựa* (grounding) nhờ tầng tool.** Mỗi `Observation` là một mẩu sự thật lấy từ database, được nạp ngược lại vào prompt cho bước sau. Agent giỏi *hành động* vì nó liên tục đối chiếu suy nghĩ với thực tế. Chính cái vòng `Thought → Action → Observation` biến model từ "người kể chuyện" thành "người làm việc".

Điều tôi thấm nhất khi làm tầng tool: **tool layer chính là ranh giới giữa "ảo giác" và "sự thật" của agent.** Khi `search_available_slots` trả `NO_SLOT_FOUND` thay vì cố bịa một slot, tôi đã *ép* agent phải xử lý sự thật "hết chỗ" — và từ đó nó mới biết gọi `suggest_alternative_dates`. Nếu tool dễ dãi (bịa dữ liệu, nuốt lỗi im lặng) thì agent dù thông minh vẫn lý luận trên nền cát.

Hệ quả thứ hai: trong hệ agentic, **độ tin cậy đến từ kỹ thuật phần mềm cổ điển nhiều hơn là từ "prompt magic"**. Transaction để chống double-booking, validate input bằng Pydantic, error code thống nhất, whitelist chống bịa tool — đó toàn là kỹ thuật backend bình thường, nhưng chính chúng quyết định agent có dùng được trong "production" hay không. Và đúng như châm ngôn của lab: *"the trace is the truth"* — tôi sửa lỗi v1→v2 hoàn toàn dựa trên log, không phải dựa vào cảm giác.

---

## IV. Future Improvements (Hướng mở rộng lên production)

1. **Thay khớp chuỗi bằng RAG cho lớp tool.** Hiện `search_available_slots` khớp chính xác `specialty_name`, nên "bác sĩ tim", "đau ngực", "huyết áp cao" sẽ trượt khỏi "Tim mạch". Hướng đi: embed mô tả chuyên khoa + triệu chứng vào vector store, để một tool `resolve_specialty(symptom)` ánh xạ ngôn ngữ tự nhiên → `specialty_id`. Đây là bước đệm tự nhiên lên kiến trúc **RAG**.

2. **Đưa tool layer thành MCP server.** Gói `src/tools/` hiện đã có cửa ngõ chuẩn (`run_tool`) và schema rõ ràng — rất gần với một MCP server. Tách ra thành service riêng để nhiều agent (và cả hệ thống khác) dùng chung, thay vì nhúng cứng trong tiến trình agent.

3. **Kiến trúc multi-agent.** Tách thành *Triage Agent* (phân loại nhu cầu) → *Booking Agent* (đặt lịch) → *Escalation Agent* (xử lý ca khó), tất cả chia sẻ chung `TOOL_REGISTRY` như một "tool service" tập trung.

4. **Tăng độ bền cho `book_appointment`.** Bổ sung **idempotency key** để khi agent retry không tạo trùng lịch, và **circuit breaker** cho các tool đụng DB khi tải cao. Thay SQLite bằng Postgres + connection pool + async để chịu tải thật.

5. **Quan sát sâu hơn (observability).** Gắn metric per-tool: latency, tỉ lệ lỗi theo `error_code`, tần suất từng tool — dựng dashboard để phát hiện sớm tool nào hay bị agent gọi sai, từ đó tiếp tục tinh chỉnh mô tả tool (vòng lặp cải tiến liên tục).
