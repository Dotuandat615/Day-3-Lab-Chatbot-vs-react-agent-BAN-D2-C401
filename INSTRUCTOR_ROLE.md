# Hướng dẫn thực hiện Demo AI Trợ Lý Đặt Lịch Khám

## 1. Mục tiêu dự án

Nhóm cần xây dựng một demo **AI Trợ Lý Đặt Lịch Khám** chạy local, có thể so sánh giữa:

1. **Chatbot Baseline**: mô hình chỉ trả lời trực tiếp, không gọi tool.
2. **ReAct Agent v1**: agent có vòng lặp `Thought → Action → Observation → Final Answer`, gọi được ít nhất 2 tool.
3. **ReAct Agent v2**: phiên bản cải tiến dựa trên lỗi của v1, có guardrails, logging, fallback và xử lý lỗi tốt hơn.

Demo cần thể hiện rõ:

- Mô hình chạy local.
- Có database đơn giản để agent truy vấn.
- Có logs/telemetry để kiểm tra cách mô hình trả lời.
- Có UI/UX hiển thị trace, metrics và thông báo lỗi.
- Có max iteration safeguard.
- Có fallback sang chatbot hoặc điều phối viên/con người.
- Có đánh giá so sánh Chatbot vs Agent v1 vs Agent v2.

---

## 2. Use case chính

Người dùng nhập yêu cầu đặt lịch khám, ví dụ:

```text
Tôi muốn khám Tim mạch vào sáng thứ 3 tuần sau, ưu tiên khung giờ ít phải chờ.
```

Agent cần xử lý:

1. Hiểu chuyên khoa người dùng muốn khám.
2. Hiểu ngày và buổi mong muốn.
3. Truy vấn database để tìm slot còn trống.
4. Xếp hạng slot theo thời gian chờ dự kiến.
5. Gợi ý slot tốt nhất.
6. Nếu người dùng xác nhận, đặt lịch.
7. Nếu thiếu thông tin, hỏi lại.
8. Nếu lỗi hoặc quá số bước, fallback sang chatbot hoặc con người.

---

## 3. Kiến trúc tổng thể

```text
User
 │
 ▼
Streamlit UI
 │
 ├── Chatbot Baseline
 │     └── Local LLM trả lời trực tiếp, không gọi tool
 │
 └── ReAct Agent
       │
       ├── Local LLM Provider
       │     └── Phi-3 / Llama.cpp / Ollama
       │
       ├── ReAct Loop
       │     ├── Thought
       │     ├── Action
       │     ├── Observation
       │     └── Final Answer
       │
       ├── Tools
       │     ├── search_available_slots()
       │     ├── estimate_wait_time()
       │     ├── rank_slots()
       │     ├── book_appointment()
       │     ├── suggest_alternative_dates()
       │     └── escalate_to_human()
       │
       ├── Safeguards
       │     ├── max_steps
       │     ├── timeout
       │     ├── parser retry
       │     ├── tool whitelist
       │     └── fallback
       │
       └── Logs / Telemetry
             ├── latency
             ├── token estimate
             ├── loop count
             ├── tool calls
             ├── parser error
             ├── timeout
             └── final status
```

---

## 4. Cấu trúc thư mục đề xuất

```text
ai-appointment-agent/
│
├── app.py
├── requirements.txt
├── .env.example
├── README.md
│
├── data/
│   ├── hospital.db
│   ├── seed_database.py
│   └── sample_queries.md
│
├── models/
│   └── Phi-3-mini-4k-instruct-q4.gguf
│
├── src/
│   ├── agent/
│   │   ├── react_agent.py
│   │   ├── parser.py
│   │   └── prompts.py
│   │
│   ├── chatbot/
│   │   └── baseline_chatbot.py
│   │
│   ├── providers/
│   │   ├── base.py
│   │   └── local_llm.py
│   │
│   ├── tools/
│   │   ├── appointment_tools.py
│   │   ├── tool_schema.py
│   │   └── tool_registry.py
│   │
│   ├── telemetry/
│   │   ├── logger.py
│   │   └── metrics.py
│   │
│   └── ui/
│       └── components.py
│
├── logs/
│   ├── chatbot/
│   └── agent/
│
├── tests/
│   ├── test_cases.json
│   └── run_evaluation.py
│
└── report/
    ├── group_report/
    │   └── group_report.md
    └── individual_reports/
        ├── member_1.md
        ├── member_2.md
        ├── member_3.md
        ├── member_4.md
        └── member_5.md
```

---

## 5. Phân công cho 5 người

### Người 1 — Project Lead + Domain + Database Design + Report

#### Trách nhiệm

- Thiết kế workflow đặt lịch khám.
- Thiết kế database đơn giản cho bệnh viện.
- Tạo mock data: chuyên khoa, bác sĩ, slot khám, bệnh nhân, lịch hẹn.
- Định nghĩa business rules cho agent.
- Viết test cases.
- Tổng hợp group report.
- Làm flowchart nghiệp vụ.

#### Output cần nộp

```text
data/hospital.db
data/seed_database.py
docs/business_rules.md
docs/workflow.md
tests/test_cases.json
report/group_report/group_report.md
```

#### Rubric liên quan

- Flowchart & Insight
- Evaluation & Analysis
- Trace Quality
- Group Report

---

### Người 2 — Local LLM Provider + Chatbot Baseline

#### Trách nhiệm

- Setup mô hình local bằng Phi-3, llama-cpp-python hoặc Ollama.
- Viết class `LocalLLMProvider`.
- Viết chatbot baseline.
- Log latency và token estimate cho chatbot.
- Chạy chatbot với toàn bộ test cases.

#### Output cần nộp

```text
src/providers/base.py
src/providers/local_llm.py
src/chatbot/baseline_chatbot.py
logs/chatbot/
```

#### Rubric liên quan

- Chatbot Baseline
- Local model
- Token efficiency
- Latency tracking

---

### Người 3 — Tool Design + Backend Logic

#### Trách nhiệm

- Viết tool schema bằng Pydantic.
- Viết các tool đọc database.
- Tạo tool registry.
- Xử lý lỗi ở tool level.
- Viết mô tả tool rõ ràng để agent biết khi nào dùng tool nào.

#### Tools cần có

```text
search_available_slots()
estimate_wait_time()
rank_slots()
book_appointment()
suggest_alternative_dates()
escalate_to_human()
```

#### Output cần nộp

```text
src/tools/tool_schema.py
src/tools/appointment_tools.py
src/tools/tool_registry.py
```

#### Rubric liên quan

- Agent v1 Working
- Tool Design Evolution
- Extra Tools bonus
- Failure Handling bonus

---

### Người 4 — ReAct Agent v1/v2 + Safeguards

#### Trách nhiệm

- Implement ReAct loop.
- Parse output của LLM.
- Feed Observation ngược lại vào prompt.
- Implement Agent v1.
- Implement Agent v2 cải tiến.
- Thêm max_steps.
- Thêm timeout.
- Thêm parser retry.
- Thêm tool whitelist.
- Thêm fallback sang chatbot hoặc con người.

#### Output cần nộp

```text
src/agent/react_agent.py
src/agent/parser.py
src/agent/prompts.py
logs/agent/
```

#### Rubric liên quan

- Agent v1 Working
- Agent v2 Improved
- Failure Handling
- Code Quality

---

### Người 5 — UI/UX + Monitoring Dashboard + Evaluation

#### Trách nhiệm

- Làm Streamlit UI.
- Cho phép chọn mode: Chatbot Baseline / Agent v1 / Agent v2.
- Hiển thị câu trả lời.
- Hiển thị trace `Thought / Action / Observation`.
- Hiển thị log và metrics.
- Hiển thị error message thân thiện.
- Viết script parse logs.
- Tạo bảng so sánh Chatbot vs Agent v1 vs Agent v2.

#### Output cần nộp

```text
app.py
src/ui/components.py
src/telemetry/logger.py
src/telemetry/metrics.py
tests/run_evaluation.py
report/group_report/evaluation_table.md
```

#### Rubric liên quan

- Trace Quality
- Evaluation & Analysis
- Extra Monitoring bonus
- Live System Demo bonus

---

## 6. Database đơn giản

Nhóm nên dùng **SQLite** để demo giống hệ thống thật nhưng vẫn dễ chạy local.

### 6.1. Bảng `specialties`

Lưu danh sách chuyên khoa.

| Field | Type | Ý nghĩa |
|---|---|---|
| specialty_id | TEXT | Mã chuyên khoa |
| specialty_name | TEXT | Tên chuyên khoa |
| description | TEXT | Mô tả |

Ví dụ:

```text
S001 | Tim mạch | Khám tim, huyết áp, đau ngực
S002 | Da liễu | Khám da, dị ứng, mụn
S003 | Nhi khoa | Khám trẻ em
S004 | Tổng quát | Khám sức khỏe tổng quát
```

---

### 6.2. Bảng `doctors`

Lưu thông tin bác sĩ.

| Field | Type | Ý nghĩa |
|---|---|---|
| doctor_id | TEXT | Mã bác sĩ |
| doctor_name | TEXT | Tên bác sĩ |
| specialty_id | TEXT | Mã chuyên khoa |
| room | TEXT | Phòng khám |
| experience_years | INTEGER | Số năm kinh nghiệm |

Ví dụ:

```text
D001 | Dr. Minh | S001 | Phòng 201 | 10
D002 | Dr. Lan | S001 | Phòng 202 | 8
D003 | Dr. Hương | S002 | Phòng 305 | 6
```

---

### 6.3. Bảng `appointment_slots`

Lưu khung giờ khám.

| Field | Type | Ý nghĩa |
|---|---|---|
| slot_id | TEXT | Mã slot |
| doctor_id | TEXT | Mã bác sĩ |
| date | TEXT | Ngày khám |
| time | TEXT | Giờ khám |
| available | INTEGER | 1 là còn trống, 0 là đã kín |
| estimated_wait_time | INTEGER | Thời gian chờ dự kiến, tính bằng phút |

Ví dụ:

```text
SL001 | D001 | 2026-06-09 | 08:30 | 1 | 45
SL002 | D002 | 2026-06-09 | 09:30 | 1 | 20
SL003 | D001 | 2026-06-09 | 10:30 | 1 | 35
SL004 | D003 | 2026-06-09 | 14:00 | 0 | 60
```

---

### 6.4. Bảng `patients`

Lưu bệnh nhân giả lập.

| Field | Type | Ý nghĩa |
|---|---|---|
| patient_id | TEXT | Mã bệnh nhân |
| patient_name | TEXT | Tên bệnh nhân |
| phone | TEXT | Số điện thoại |
| date_of_birth | TEXT | Ngày sinh |

Ví dụ:

```text
P001 | Nguyễn Văn Nam | 0901234567 | 1998-05-12
P002 | Trần Thị Mai | 0912345678 | 1985-09-20
```

---

### 6.5. Bảng `appointments`

Lưu lịch hẹn đã đặt.

| Field | Type | Ý nghĩa |
|---|---|---|
| appointment_id | TEXT | Mã lịch hẹn |
| patient_id | TEXT | Mã bệnh nhân |
| slot_id | TEXT | Mã slot |
| status | TEXT | Trạng thái |
| created_at | TEXT | Thời điểm tạo lịch |

Ví dụ:

```text
A001 | P001 | SL002 | confirmed | 2026-06-01 10:00:00
```

---

## 7. Business rules cho Agent

Người 1 cần viết rõ các rule này để Người 4 đưa vào prompt và Người 3 đưa vào tool logic.

```text
Rule 1: Nếu user thiếu chuyên khoa, agent phải hỏi lại chuyên khoa.
Rule 2: Nếu user thiếu ngày khám, agent phải hỏi lại ngày khám.
Rule 3: Nếu user chỉ nói "càng sớm càng tốt", agent tìm ngày gần nhất có slot.
Rule 4: Nếu có nhiều slot, ưu tiên slot có estimated_wait_time thấp nhất.
Rule 5: Nếu slot đúng ngày đã hết, agent gợi ý ngày gần nhất.
Rule 6: Nếu user muốn đặt lịch nhưng thiếu tên hoặc số điện thoại, agent phải hỏi thêm.
Rule 7: Agent không được tự bịa bác sĩ, ngày khám hoặc thời gian chờ.
Rule 8: Nếu tool lỗi, agent dùng fallback.
Rule 9: Nếu quá max_steps, agent chuyển sang điều phối viên.
Rule 10: Nếu timeout, agent trả thông báo thân thiện và fallback.
```

---

## 8. Pydantic tool schema

Pydantic giúp định nghĩa input/output của tool để agent gọi đúng format.

Ví dụ file `src/tools/tool_schema.py`:

```python
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class SearchSlotInput(BaseModel):
    specialty: str
    date: str
    preferred_time: Optional[str] = None

class EstimateWaitTimeInput(BaseModel):
    doctor_id: str
    date: str
    time: str

class RankSlotsInput(BaseModel):
    slots: List[Dict[str, Any]]
    criteria: str = "lowest_wait_time"

class BookAppointmentInput(BaseModel):
    patient_name: str
    phone: str
    slot_id: str

class EscalateInput(BaseModel):
    reason: str
    user_query: str
```

---

## 9. Tool list đề xuất

### 9.1. `search_available_slots`

Mục đích: tìm slot còn trống theo chuyên khoa, ngày và buổi.

Input:

```json
{
  "specialty": "Tim mạch",
  "date": "2026-06-09",
  "preferred_time": "morning"
}
```

Output:

```json
{
  "status": "success",
  "slots": [
    {
      "slot_id": "SL001",
      "doctor_name": "Dr. Minh",
      "date": "2026-06-09",
      "time": "08:30",
      "estimated_wait_time": 45
    },
    {
      "slot_id": "SL002",
      "doctor_name": "Dr. Lan",
      "date": "2026-06-09",
      "time": "09:30",
      "estimated_wait_time": 20
    }
  ]
}
```

---

### 9.2. `rank_slots`

Mục đích: chọn slot tốt nhất.

Input:

```json
{
  "slots": [
    {"slot_id": "SL001", "estimated_wait_time": 45},
    {"slot_id": "SL002", "estimated_wait_time": 20}
  ],
  "criteria": "lowest_wait_time"
}
```

Output:

```json
{
  "status": "success",
  "best_slot": {
    "slot_id": "SL002",
    "time": "09:30",
    "estimated_wait_time": 20
  }
}
```

---

### 9.3. `book_appointment`

Mục đích: đặt lịch sau khi người dùng xác nhận.

Input:

```json
{
  "patient_name": "Nguyễn Văn Nam",
  "phone": "0901234567",
  "slot_id": "SL002"
}
```

Output:

```json
{
  "status": "success",
  "appointment_id": "A002",
  "message": "Đặt lịch thành công."
}
```

---

### 9.4. `suggest_alternative_dates`

Mục đích: nếu ngày mong muốn hết slot, gợi ý ngày khác.

Input:

```json
{
  "specialty": "Tim mạch",
  "from_date": "2026-06-09"
}
```

Output:

```json
{
  "status": "success",
  "alternatives": [
    {
      "date": "2026-06-10",
      "time": "08:30",
      "estimated_wait_time": 25
    }
  ]
}
```

---

### 9.5. `escalate_to_human`

Mục đích: fallback sang điều phối viên.

Input:

```json
{
  "reason": "MAX_STEPS_EXCEEDED",
  "user_query": "Tôi muốn đặt lịch khám nhưng agent không hoàn tất được."
}
```

Output:

```json
{
  "status": "escalated",
  "message": "Yêu cầu đã được chuyển sang điều phối viên."
}
```

---

## 10. ReAct Agent format

Agent nên xuất theo format có cấu trúc để dễ parse.

### Format gợi ý cho v1

```text
Thought: Cần kiểm tra slot còn trống theo chuyên khoa và ngày.
Action: search_available_slots
Action Input: {"specialty": "Tim mạch", "date": "2026-06-09", "preferred_time": "morning"}
```

Sau đó hệ thống gọi tool và đưa lại:

```text
Observation: Tìm thấy 3 slot còn trống.
```

Khi đủ thông tin:

```text
Final Answer: Hiện có lịch khám Tim mạch lúc 09:30 với thời gian chờ dự kiến 20 phút.
```

---

## 11. Agent v1

Agent v1 chỉ cần chạy được ReAct loop cơ bản.

Yêu cầu tối thiểu:

```text
- Có ít nhất 2 tools.
- Gọi được tool.
- Nhận Observation.
- Có Final Answer.
- Có log từng bước.
```

Nhược điểm có thể chấp nhận ở v1:

```text
- Có thể bị parser error.
- Có thể gọi sai tool.
- Có thể bị loop.
- Chưa xử lý tốt thiếu thông tin.
```

Những lỗi này nên được ghi lại để dùng cho phần Failure Analysis.

---

## 12. Agent v2

Agent v2 phải cải thiện dựa trên lỗi của v1.

Cải tiến nên có:

```text
- Tool whitelist: chỉ được gọi tool có trong registry.
- Parser retry: nếu output sai JSON, yêu cầu model xuất lại đúng format.
- Missing info rule: thiếu chuyên khoa/ngày thì hỏi lại, không tự bịa.
- Max steps: nếu quá 5 vòng thì fallback.
- Timeout: nếu quá 20 giây thì fallback.
- Repeated tool call detection: nếu gọi cùng tool với cùng input quá 2 lần thì dừng.
- Friendly error messages cho user.
```

---

## 13. Max iteration safeguard

Thiết kế:

```python
MAX_STEPS = 5

for step in range(MAX_STEPS):
    llm_output = llm.generate(prompt)
    parsed = parse_react_output(llm_output)

    if parsed.type == "final_answer":
        return parsed.final_answer

    if parsed.type == "action":
        observation = run_tool(parsed.tool_name, parsed.tool_input)
        add_observation_to_prompt(observation)

# Nếu hết vòng lặp mà chưa có Final Answer
return fallback_to_human(reason="MAX_STEPS_EXCEEDED")
```

Message cho user:

```text
Mình chưa thể hoàn tất yêu cầu tự động sau nhiều bước xử lý. 
Mình sẽ chuyển thông tin này cho điều phối viên để hỗ trợ bạn chính xác hơn.
```

---

## 14. Timeout safeguard

Thiết kế:

```text
timeout_seconds = 20
```

Logic:

```text
Nếu tổng thời gian xử lý > 20 giây:
    log error_code = TIMEOUT
    fallback sang chatbot hoặc điều phối viên
```

Message cho user:

```text
Hệ thống đang phản hồi chậm hơn dự kiến. 
Mình sẽ chuyển yêu cầu sang kênh hỗ trợ dự phòng để bạn không phải chờ lâu.
```

---

## 15. UI/UX yêu cầu

Nên dùng **Streamlit**.

UI cần có:

```text
1. Input box cho người dùng nhập yêu cầu.
2. Dropdown chọn mode: Chatbot Baseline / Agent v1 / Agent v2.
3. Khu vực hiển thị câu trả lời cuối.
4. Khu vực hiển thị trace Thought / Action / Observation.
5. Khu vực hiển thị metrics.
6. Khu vực hiển thị log JSON.
7. Error message thân thiện.
```

### Error message mapping

| Error code | Message cho người dùng |
|---|---|
| MISSING_INFORMATION | Mình cần thêm chuyên khoa hoặc ngày khám để kiểm tra lịch phù hợp. |
| NO_SLOT_FOUND | Hiện chưa có slot phù hợp. Mình có thể gợi ý ngày gần nhất hoặc chuyển cho điều phối viên. |
| PARSER_ERROR | Mình chưa thể xử lý yêu cầu tự động ngay lúc này. Vui lòng thử lại hoặc để nhân viên hỗ trợ. |
| HALLUCINATED_TOOL | Hệ thống đang gặp lỗi chọn công cụ xử lý. Mình sẽ chuyển sang kênh hỗ trợ dự phòng. |
| TOOL_RUNTIME_ERROR | Có lỗi khi kiểm tra lịch khám. Vui lòng thử lại hoặc để nhân viên hỗ trợ tiếp. |
| TIMEOUT | Hệ thống đang mất nhiều thời gian hơn dự kiến. Mình sẽ chuyển yêu cầu sang hỗ trợ dự phòng. |
| MAX_STEPS_EXCEEDED | Mình chưa thể hoàn tất yêu cầu tự động. Mình sẽ chuyển ca này cho điều phối viên. |

---

## 16. Logging / Telemetry

Mỗi lần chạy cần sinh một file log JSON trong thư mục `logs/`.

Ví dụ log:

```json
{
  "run_id": "agent_v2_001",
  "version": "agent_v2",
  "user_query": "Tôi muốn khám Tim mạch sáng thứ 3, ít phải chờ.",
  "start_time": "2026-06-01T10:00:00",
  "end_time": "2026-06-01T10:00:05",
  "latency_seconds": 5.12,
  "loop_count": 3,
  "tools_called": [
    "search_available_slots",
    "rank_slots"
  ],
  "final_status": "success",
  "error_code": null,
  "fallback_used": false,
  "token_prompt_estimate": 812,
  "token_completion_estimate": 246,
  "trace": [
    {
      "step": 1,
      "thought": "Cần kiểm tra slot Tim mạch còn trống.",
      "action": "search_available_slots",
      "action_input": {
        "specialty": "Tim mạch",
        "date": "2026-06-09",
        "preferred_time": "morning"
      },
      "observation": "Tìm thấy 3 slot còn trống."
    }
  ]
}
```

### Error codes nên có

```text
SUCCESS
MISSING_INFORMATION
NO_SLOT_FOUND
PARSER_ERROR
HALLUCINATED_TOOL
TOOL_RUNTIME_ERROR
TIMEOUT
MAX_STEPS_EXCEEDED
FALLBACK_TO_CHATBOT
FALLBACK_TO_HUMAN
```

---

## 17. Evaluation

Tạo file `tests/test_cases.json` gồm 10–15 cases.

Ví dụ:

```json
[
  {
    "id": "TC01",
    "query": "Tôi muốn khám Tim mạch sáng thứ 3 tuần sau, ít phải chờ.",
    "expected_behavior": "Agent tìm slot Tim mạch, chọn slot wait time thấp nhất."
  },
  {
    "id": "TC02",
    "query": "Tôi muốn khám Da liễu chiều mai.",
    "expected_behavior": "Agent tìm slot Da liễu vào buổi chiều."
  },
  {
    "id": "TC03",
    "query": "Đặt lịch khám cho tôi càng sớm càng tốt.",
    "expected_behavior": "Agent hỏi lại chuyên khoa hoặc gợi ý khám tổng quát nếu policy cho phép."
  },
  {
    "id": "TC04",
    "query": "Có bác sĩ Nhi nào rảnh cuối tuần không?",
    "expected_behavior": "Agent tìm slot Nhi khoa cuối tuần."
  },
  {
    "id": "TC05",
    "query": "Tôi muốn khám Tim mạch nhưng ngày đó hết slot.",
    "expected_behavior": "Agent gợi ý ngày thay thế."
  }
]
```

### Metrics cần tính

| Metric | Ý nghĩa |
|---|---|
| Success rate | Tỷ lệ trả lời đúng kỳ vọng |
| Hallucination rate | Tỷ lệ bịa tool/bịa thông tin |
| Parser error rate | Tỷ lệ lỗi parse output |
| Timeout rate | Tỷ lệ quá thời gian |
| Avg latency | Thời gian xử lý trung bình |
| Avg loop count | Số vòng ReAct trung bình |
| Fallback rate | Tỷ lệ phải fallback |
| Token estimate | Ước lượng token prompt và completion |

### Bảng kết quả cần có trong report

| Version | Success Rate | Avg Latency | Avg Loop Count | Parser Error | Timeout | Fallback Rate |
|---|---:|---:|---:|---:|---:|---:|
| Chatbot Baseline | 40% | 1.2s | 0 | 0% | 0% | 0% |
| Agent v1 | 65% | 6.5s | 4.1 | 20% | 10% | 15% |
| Agent v2 | 85% | 5.2s | 3.0 | 5% | 5% | 8% |

Lưu ý: số liệu trên là ví dụ. Nhóm cần thay bằng số liệu thật từ log.

---

## 18. Trace thành công mẫu

```text
User:
Tôi muốn khám Tim mạch sáng thứ 3 tuần sau, ưu tiên khung giờ ít phải chờ.

Step 1
Thought:
Cần kiểm tra các slot Tim mạch còn trống vào sáng thứ 3.

Action:
search_available_slots({
  "specialty": "Tim mạch",
  "date": "2026-06-09",
  "preferred_time": "morning"
})

Observation:
Tìm thấy 3 slot:
- 08:30, wait_time = 45 phút
- 09:30, wait_time = 20 phút
- 10:30, wait_time = 35 phút

Step 2
Thought:
Cần chọn slot có thời gian chờ thấp nhất.

Action:
rank_slots({
  "criteria": "lowest_wait_time",
  "slots": ["08:30", "09:30", "10:30"]
})

Observation:
Slot tốt nhất là 09:30 vì wait_time = 20 phút.

Step 3
Thought:
Đã có slot phù hợp, cần hỏi người dùng xác nhận trước khi đặt lịch.

Action:
generate_confirmation_message({
  "specialty": "Tim mạch",
  "date": "2026-06-09",
  "time": "09:30"
})

Observation:
Tin nhắn xác nhận đã được tạo.

Final Answer:
Hiện có lịch khám Tim mạch lúc 09:30 sáng thứ 3 tuần sau, thời gian chờ dự kiến khoảng 20 phút. Bạn có muốn xác nhận lịch này không?
```

---

## 19. Trace thất bại mẫu

```text
User:
Đặt lịch khám cho tôi càng sớm càng tốt.

Step 1
Thought:
Yêu cầu thiếu chuyên khoa, cần hỏi lại thay vì tự đoán.

Action:
none

Observation:
Missing required field: specialty.

Final Answer:
Mình cần biết bạn muốn khám chuyên khoa nào, ví dụ Tim mạch, Da liễu, Nhi khoa hoặc Tổng quát, để kiểm tra lịch phù hợp.
```

---

## 20. Failure Analysis mẫu cho report

### Failure case: Agent v1 gọi tool không tồn tại

#### Log

```json
{
  "version": "agent_v1",
  "error_code": "HALLUCINATED_TOOL",
  "tool_name": "check_doctor_schedule",
  "available_tools": [
    "search_available_slots",
    "rank_slots",
    "book_appointment"
  ]
}
```

#### Nguyên nhân

Agent v1 chưa có tool whitelist rõ ràng trong prompt. Mô hình tự tạo ra tool `check_doctor_schedule` vì tên này nghe hợp lý.

#### Cách sửa ở Agent v2

```text
- Thêm danh sách tool hợp lệ vào system prompt.
- Parser kiểm tra tool name có trong registry không.
- Nếu tool không tồn tại, log HALLUCINATED_TOOL.
- Cho model retry 1 lần với thông báo chỉ được dùng tool hợp lệ.
```

#### Kết quả sau khi sửa

Agent v2 chuyển sang dùng đúng tool `search_available_slots`.

---

## 21. Timeline thực hiện 5 ngày

### Ngày 1 — Setup + thiết kế

Việc cần làm:

```text
- Tạo repo.
- Chốt use case.
- Setup local model.
- Thiết kế database.
- Viết seed data.
- Viết business rules.
- Viết test cases.
```

Kết quả cuối ngày:

```text
- Local model chạy được.
- Có database mock.
- Có danh sách tool.
- Có test cases.
```

---

### Ngày 2 — Baseline + Tools

Việc cần làm:

```text
- Hoàn thành chatbot baseline.
- Hoàn thành tool schema.
- Hoàn thành appointment tools.
- Test từng tool độc lập.
- Log chatbot response.
```

Kết quả cuối ngày:

```text
- Chatbot baseline chạy được.
- Tools chạy được bằng Python.
- Có log chatbot.
```

---

### Ngày 3 — Agent v1

Việc cần làm:

```text
- Implement ReAct loop.
- Agent gọi được tool.
- Lưu trace Thought/Action/Observation.
- Chạy test cases lần 1.
- Ghi lại lỗi của v1.
```

Kết quả cuối ngày:

```text
- Agent v1 chạy được.
- Có success trace.
- Có failed trace.
```

---

### Ngày 4 — Agent v2 + UI

Việc cần làm:

```text
- Sửa lỗi từ v1.
- Thêm max_steps.
- Thêm timeout.
- Thêm parser retry.
- Thêm fallback.
- Hoàn thành Streamlit UI.
```

Kết quả cuối ngày:

```text
- Agent v2 tốt hơn v1.
- UI hiển thị trace, metrics và error handling.
```

---

### Ngày 5 — Evaluation + Report + Demo

Việc cần làm:

```text
- Chạy toàn bộ test cases.
- Parse logs thành bảng metrics.
- So sánh Chatbot vs Agent v1 vs Agent v2.
- Viết group report.
- Mỗi người viết individual report.
- Chuẩn bị live demo.
```

Kết quả cuối ngày:

```text
- Có demo hoàn chỉnh.
- Có report.
- Có bảng evaluation.
- Có trace thành công và thất bại.
```

---

## 22. Demo flow trước giảng viên

Nhóm nên demo 4 case.

### Case 1 — Chatbot baseline trả lời chung chung

User:

```text
Tôi muốn khám Tim mạch sáng thứ 3 tuần sau, chọn slot ít phải chờ nhất.
```

Thông điệp cần nói:

```text
Chatbot có thể trả lời tự nhiên nhưng không kiểm tra được database, không biết slot thật, dễ hallucinate.
```

---

### Case 2 — Agent v1 success

Agent gọi:

```text
search_available_slots()
rank_slots()
```

Thông điệp cần nói:

```text
Agent biết chia bài toán thành nhiều bước, gọi tool và dùng Observation để trả lời.
```

---

### Case 3 — Agent v1 fail, Agent v2 sửa được

Ví dụ lỗi:

```text
Agent v1 tự đoán ngày khám khi user không nói rõ ngày.
```

Agent v2 sửa:

```text
Agent hỏi lại ngày khám thay vì tự bịa.
```

Thông điệp cần nói:

```text
Nhóm cải thiện agent bằng log và failure trace, không chỉ sửa prompt theo cảm tính.
```

---

### Case 4 — Timeout hoặc max iteration fallback

Giả lập tool delay hoặc agent loop.

Thông điệp cần nói:

```text
Agent có guardrails nên không chạy vô hạn. Khi lỗi, hệ thống fallback an toàn sang chatbot hoặc điều phối viên.
```

---

## 23. Checklist trước khi nộp

### Code

- [ ] Chạy được local model.
- [ ] Chạy được chatbot baseline.
- [ ] Chạy được Agent v1.
- [ ] Chạy được Agent v2.
- [ ] Có ít nhất 2 tools.
- [ ] Có database đơn giản.
- [ ] Có Pydantic schema.
- [ ] Có max_steps.
- [ ] Có timeout.
- [ ] Có fallback.
- [ ] Có logs JSON.
- [ ] Có Streamlit UI.

### Evaluation

- [ ] Có 10–15 test cases.
- [ ] Có bảng so sánh Chatbot vs Agent v1 vs Agent v2.
- [ ] Có success trace.
- [ ] Có failed trace.
- [ ] Có failure analysis.
- [ ] Có metrics: latency, loop count, parser error, fallback rate.

### Report

- [ ] Có group report.
- [ ] Có tool design evolution.
- [ ] Có flowchart.
- [ ] Có insight nhóm học được.
- [ ] Mỗi thành viên có individual report.
- [ ] Mỗi thành viên ghi rõ contribution.
- [ ] Mỗi thành viên có debugging case study.

---

## 24. Cách đạt bonus

Nhóm nên làm thêm các phần sau:

| Bonus | Cách làm |
|---|---|
| Extra Monitoring | Thêm latency, token estimate, cost estimate, loop count, fallback rate |
| Extra Tools | Thêm `send_reminder`, `suggest_alternative_dates`, `estimate_wait_time` |
| Failure Handling | Thêm parser retry, timeout, max_steps, fallback |
| Live System Demo | Demo trực tiếp bằng Streamlit |
| Ablation Experiments | So sánh Agent v1 prompt vs Agent v2 prompt |

---

## 25. Kết luận

Workflow tốt nhất cho nhóm:

```text
Người 1: Business workflow + database + report
Người 2: Local model + chatbot baseline
Người 3: Tools + backend database query
Người 4: ReAct agent + safeguards
Người 5: UI + logs + evaluation
```

Demo cần chứng minh được:

```text
1. Chatbot nói được nhưng không kiểm chứng dữ liệu.
2. ReAct Agent biết gọi tool và xử lý bài toán nhiều bước.
3. Agent v2 tốt hơn v1 vì được cải thiện bằng logs, trace và failure analysis.
4. Hệ thống có error handling, max iteration safeguard và fallback an toàn.
```
