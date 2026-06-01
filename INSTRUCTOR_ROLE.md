# Hướng dẫn thực hiện Demo AI Trợ Lý Đặt Lịch Khám

Phiên bản cập nhật theo thay đổi mới nhất:

- Demo chỉ dùng **1 cơ sở bệnh viện**.
- Dataset được mở rộng thành bộ CSV lớn hơn để giả lập đặt lịch trong **2 tuần tiếp theo**.
- Không dùng bảng bảo hiểm theo từng hãng chi tiết. Thay bằng 3 nhóm thanh toán thực tế ở Việt Nam:
  - **BHYT**
  - **Bảo hiểm tư nhân / bảo lãnh viện phí**
  - **Tự thanh toán**
- Người 1 có thêm vai trò **Integration Lead**: tổng hợp source code, merge code và kiểm tra lần cuối để project chạy được end-to-end.

---

## 1. Mục tiêu dự án

Nhóm cần xây dựng demo **AI Trợ Lý Đặt Lịch Khám** chạy local, so sánh giữa:

1. **Chatbot Baseline**  
   Mô hình chỉ trả lời trực tiếp, không gọi tool, dễ trả lời chung chung hoặc hallucinate.

2. **ReAct Agent v1**  
   Agent có vòng lặp `Thought → Action → Observation → Final Answer`, gọi được tool để truy vấn dữ liệu.

3. **ReAct Agent v2**  
   Phiên bản cải tiến từ lỗi của v1, có guardrails, logging, fallback và xử lý lỗi tốt hơn.

Demo cần thể hiện:

```text
- Mô hình chạy local.
- Có dataset CSV lớn hơn cho 1 bệnh viện.
- Agent có thể đọc dữ liệu thật giả lập qua tools.
- Có logs/telemetry để kiểm tra cách mô hình xử lý.
- Có UI/UX hiển thị trace, metrics và lỗi.
- Có max iteration safeguard.
- Có timeout safeguard.
- Có fallback sang chatbot hoặc điều phối viên.
- Có evaluation so sánh Chatbot vs Agent v1 vs Agent v2.
```

---

## 2. Phạm vi dataset

Dataset hiện tại giả lập **1 cơ sở bệnh viện** với lịch khám trong **2 tuần tiếp theo**.

```text
Hospital: VinCare Demo Hospital
Date range: 2026-06-02 đến 2026-06-15
Sunday: không có slot khám ngoại trú định kỳ
```

Dataset hỗ trợ các kiểu câu hỏi mở rộng như:

```text
Tôi muốn khám Tim mạch sáng thứ 3, bác sĩ nữ, chờ dưới 30 phút.

Tôi bị nổi mẩn đỏ và ngứa thì nên khám khoa nào?

Tôi có BHYT, khám Nhi khoa có hỗ trợ không?

Tôi muốn khám online với bác sĩ nói tiếng Anh.

Có slot Da liễu nào dưới 500 nghìn trong tuần này không?

Tôi cần đến trước bao lâu?

Tôi muốn đổi lịch hẹn A00001 sang chiều thứ 5.

Khung giờ nào thường ít đông?

Tôi muốn đặt lịch khám Tổng quát nhưng cần biết có phải nhịn ăn không.
```

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
       │     ├── rank_slots()
       │     ├── book_appointment()
       │     ├── suggest_specialty_by_symptoms()
       │     ├── check_payment_coverage()
       │     ├── get_service_price()
       │     ├── get_doctor_profile()
       │     ├── get_hospital_policy()
       │     ├── suggest_alternative_slots()
       │     ├── reschedule_appointment()
       │     ├── cancel_appointment()
       │     └── escalate_to_human()
       │
       ├── Safeguards
       │     ├── max_steps
       │     ├── timeout
       │     ├── parser retry
       │     ├── tool whitelist
       │     ├── repeated tool call detection
       │     └── fallback
       │
       └── Logs / Telemetry
             ├── latency
             ├── token estimate
             ├── loop count
             ├── selected tools
             ├── parser error
             ├── hallucinated tool
             ├── timeout
             ├── fallback used
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
│   ├── hospital_info.csv
│   ├── specialties.csv
│   ├── symptom_specialty_map.csv
│   ├── payment_coverage_types.csv
│   ├── doctors.csv
│   ├── services.csv
│   ├── doctor_schedule_templates.csv
│   ├── appointment_slots.csv
│   ├── wait_time_history.csv
│   ├── patients.csv
│   ├── appointments.csv
│   ├── reminder_logs.csv
│   ├── hospital_policies.csv
│   ├── escalation_tickets.csv
│   ├── feedback_reviews.csv
│   └── data_dictionary.csv
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
│   ├── data_access/
│   │   ├── csv_loader.py
│   │   └── query_service.py
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

## 5. Dataset CSV cập nhật

Dataset lớn hơn gồm các file sau:

| File | Số dòng | Vai trò |
|---|---:|---|
| `hospital_info.csv` | 1 | Thông tin chung của bệnh viện |
| `specialties.csv` | 12 | Danh sách chuyên khoa |
| `symptom_specialty_map.csv` | 69 | Map triệu chứng sang chuyên khoa |
| `payment_coverage_types.csv` | 3 | BHYT, bảo hiểm tư, tự thanh toán |
| `doctors.csv` | 48 | Danh sách bác sĩ |
| `services.csv` | 36 | Dịch vụ khám |
| `doctor_schedule_templates.csv` | 254 | Lịch làm việc mẫu của bác sĩ |
| `appointment_slots.csv` | 3,229 | Slot khám trong 2 tuần |
| `wait_time_history.csv` | 288 | Lịch sử thời gian chờ |
| `patients.csv` | 500 | Bệnh nhân giả lập |
| `appointments.csv` | 1,141 | Lịch hẹn đã đặt |
| `reminder_logs.csv` | 853 | Log nhắc lịch |
| `hospital_policies.csv` | 24 | FAQ và chính sách bệnh viện |
| `escalation_tickets.csv` | 120 | Ticket fallback |
| `feedback_reviews.csv` | 350 | Feedback sau lịch hẹn |
| `data_dictionary.csv` | 15 | Mô tả nhanh các bảng |

---

## 6. Ý nghĩa các bảng chính

### 6.1. `hospital_info.csv`

Lưu thông tin chung của bệnh viện.

Các field chính:

```text
hospital_id
hospital_name
address
city
opening_time
closing_time
weekend_available
parking_available
hotline
emergency_note
```

Agent dùng bảng này để trả lời:

```text
Bệnh viện ở đâu?
Bệnh viện làm việc mấy giờ?
Có chỗ gửi xe không?
Nếu triệu chứng khẩn cấp thì nên làm gì?
```

---

### 6.2. `specialties.csv`

Lưu danh sách chuyên khoa.

Các field chính:

```text
specialty_id
specialty_name
description
common_symptoms
min_age
max_age
```

Agent dùng bảng này để trả lời:

```text
Bệnh viện có chuyên khoa nào?
Tim mạch khám những vấn đề gì?
Trẻ em nên khám khoa nào?
```

---

### 6.3. `symptom_specialty_map.csv`

Map triệu chứng sang chuyên khoa gợi ý.

Các field chính:

```text
symptom_id
symptom_keyword
suggested_specialty_id
urgency_level
note
```

Agent dùng bảng này để xử lý câu hỏi kiểu:

```text
Tôi bị đau ngực và khó thở thì nên khám khoa nào?

Tôi bị nổi mẩn đỏ và ngứa thì đặt lịch khoa gì?

Con tôi sốt cao co giật thì có đặt lịch thường không?
```

Lưu ý quan trọng:

```text
Agent không được chẩn đoán bệnh.
Agent chỉ được gợi ý chuyên khoa.
Nếu urgency_level = emergency, agent không đặt lịch thường mà khuyến nghị cấp cứu/fallback.
```

---

### 6.4. `payment_coverage_types.csv`

Thay thế cho bảng bảo hiểm chi tiết.

Chỉ có 3 nhóm:

```text
COV001: BHYT
COV002: PRIVATE_INSURANCE
COV003: SELF_PAY
```

Agent dùng bảng này để trả lời:

```text
Tôi có BHYT thì cần mang gì?
Tôi có bảo hiểm tư nhân thì làm thế nào?
Tôi không có bảo hiểm thì thanh toán sao?
```

---

### 6.5. `doctors.csv`

Thông tin bác sĩ.

Các field chính:

```text
doctor_id
doctor_name
gender
specialty_id
room
experience_years
languages
rating
consultation_fee
bhyt_supported
private_insurance_supported
telehealth_supported
```

Agent dùng bảng này để xử lý:

```text
Tôi muốn bác sĩ nữ.
Tôi muốn bác sĩ nói tiếng Anh.
Tôi muốn bác sĩ rating cao.
Tôi muốn khám online.
Tôi muốn bác sĩ nhiều kinh nghiệm.
```

---

### 6.6. `services.csv`

Dịch vụ khám.

Các field chính:

```text
service_id
specialty_id
service_name
duration_minutes
base_price
preparation_required
preparation_note
bhyt_supported
private_insurance_supported
self_pay_available
estimated_bhyt_price_note
estimated_private_price_note
```

Agent dùng bảng này để trả lời:

```text
Khám Tim mạch bao nhiêu tiền?
Khám Tổng quát có cần nhịn ăn không?
Dịch vụ này có hỗ trợ BHYT không?
Bảo hiểm tư có áp dụng không?
```

---

### 6.7. `doctor_schedule_templates.csv`

Lịch làm việc mẫu của bác sĩ theo ngày trong tuần và ca.

Các field chính:

```text
schedule_id
doctor_id
day_of_week
shift
start_time
end_time
max_patients
is_active
```

Bảng này giúp dataset thực tế hơn, vì slot khám được sinh ra dựa trên lịch làm việc mẫu.

Agent có thể dùng gián tiếp để trả lời:

```text
Bác sĩ này thường khám ngày nào?
Bác sĩ này có ca chiều không?
```

---

### 6.8. `appointment_slots.csv`

Bảng quan trọng nhất cho đặt lịch.

Các field chính:

```text
slot_id
doctor_id
service_id
date
start_time
end_time
status
capacity
booked_count
estimated_wait_time
is_telehealth
room
```

Agent dùng bảng này để:

```text
Tìm slot còn trống.
Lọc theo ngày, buổi, bác sĩ, online/offline.
Chọn slot ít phải chờ nhất.
Gợi ý slot thay thế.
Đặt lịch.
Đổi lịch.
Hủy lịch.
```

---

### 6.9. `wait_time_history.csv`

Lịch sử thời gian chờ theo chuyên khoa, ngày trong tuần và khung giờ.

Các field chính:

```text
history_id
specialty_id
day_of_week
hour_block
avg_wait_time
no_show_rate
patient_volume
```

Agent dùng bảng này để trả lời:

```text
Khung giờ nào thường ít đông?
Tôi nên đi khám lúc mấy giờ để đỡ chờ?
Thứ 2 có đông không?
```

---

### 6.10. `patients.csv`

Hồ sơ bệnh nhân giả lập.

Các field chính:

```text
patient_id
patient_name
phone
date_of_birth
gender
coverage_type_id
private_insurance_name
preferred_language
```

Lưu ý:

```text
Đây là dữ liệu synthetic/fake.
Không dùng dữ liệu bệnh nhân thật.
```

---

### 6.11. `appointments.csv`

Lịch hẹn đã được đặt.

Các field chính:

```text
appointment_id
patient_id
slot_id
reason_for_visit
status
created_at
reminder_sent
```

Agent dùng bảng này để:

```text
Tra cứu lịch hẹn.
Đổi lịch.
Hủy lịch.
Kiểm tra lịch đã đặt.
```

---

### 6.12. `reminder_logs.csv`

Log nhắc lịch.

Các field chính:

```text
reminder_id
appointment_id
channel
sent_at
delivery_status
message_type
```

Agent hoặc report dùng bảng này để phân tích:

```text
Nhắc lịch qua kênh nào?
Có gửi nhắc lịch thành công không?
No-show có liên quan đến reminder không?
```

---

### 6.13. `hospital_policies.csv`

FAQ và chính sách bệnh viện.

Các field chính:

```text
policy_id
category
question
answer
applies_to
```

Agent dùng bảng này để trả lời:

```text
Tôi cần đến trước bao lâu?
Có được hủy lịch không?
Có thanh toán thẻ không?
Khám tổng quát có cần nhịn ăn không?
```

---

### 6.14. `escalation_tickets.csv`

Ticket fallback sang người thật.

Các field chính:

```text
ticket_id
user_query
reason
status
created_at
```

Agent dùng bảng này để:

```text
Ghi nhận case cần điều phối viên xử lý.
Lưu lý do fallback.
Phục vụ failure analysis trong report.
```

---

### 6.15. `feedback_reviews.csv`

Phản hồi sau lịch hẹn.

Các field chính:

```text
review_id
appointment_id
rating
wait_satisfaction
comment
created_at
```

Dùng cho phần mở rộng hoặc evaluation:

```text
Phân tích trải nghiệm người bệnh.
Đánh giá wait satisfaction.
Làm dashboard demo.
```

---

## 7. Business rules cập nhật

### 7.1. Rule về đặt lịch

```text
Rule 1: Nếu user nói rõ chuyên khoa và ngày khám:
        → search_available_slots().

Rule 2: Nếu user nói triệu chứng nhưng không nói chuyên khoa:
        → suggest_specialty_by_symptoms() trước.

Rule 3: Nếu triệu chứng có urgency_level = emergency:
        → không đặt lịch thường, khuyến nghị cấp cứu hoặc gọi hotline.

Rule 4: Nếu triệu chứng có urgency_level = urgent:
        → trả lời cẩn trọng, gợi ý chuyên khoa và ưu tiên slot sớm.

Rule 5: Nếu có nhiều slot phù hợp:
        → rank_slots() theo estimated_wait_time, thời gian mong muốn, rating bác sĩ.

Rule 6: Nếu không có slot đúng điều kiện:
        → suggest_alternative_slots().

Rule 7: Nếu user muốn đặt lịch nhưng thiếu tên hoặc số điện thoại:
        → hỏi thêm thông tin, không book ngay.

Rule 8: Nếu user yêu cầu bác sĩ nữ/nam:
        → filter doctors.gender.

Rule 9: Nếu user yêu cầu bác sĩ nói tiếng Anh:
        → filter doctors.languages.

Rule 10: Nếu user yêu cầu khám online:
         → filter appointment_slots.is_telehealth = yes.
```

---

### 7.2. Rule về thanh toán và bảo hiểm

```text
Rule 11: Nếu user nói có BHYT:
         → check_payment_coverage() với coverage_type = BHYT.

Rule 12: Nếu user nói có bảo hiểm tư:
         → check_payment_coverage() với coverage_type = PRIVATE_INSURANCE.

Rule 13: Nếu user nêu tên bảo hiểm tư như Manulife, Prudential, AIA:
         → chỉ ghi nhận private_insurance_name.
         → không cam kết mức chi trả chính xác.

Rule 14: Nếu user nói không có bảo hiểm:
         → dùng SELF_PAY và base_price.

Rule 15: Không cam kết số tiền bảo hiểm chi trả chính xác.
         → chỉ nói “có hỗ trợ / cần kiểm tra thêm / tùy điều kiện”.

Rule 16: Nếu user hỏi quyền lợi bảo hiểm chi tiết:
         → fallback sang điều phối viên hoặc quầy bảo hiểm.
```

---

### 7.3. Rule về chính sách

```text
Rule 17: Nếu user hỏi về giờ làm việc, giấy tờ, thanh toán, hủy lịch, nhịn ăn:
         → get_hospital_policy().

Rule 18: Nếu user hỏi giá khám:
         → get_service_price().

Rule 19: Nếu user hỏi cần chuẩn bị gì:
         → đọc preparation_required và preparation_note trong services.csv.
```

---

### 7.4. Rule về safety và fallback

```text
Rule 20: Agent không được tự bịa bác sĩ, giá, slot, thời gian chờ.

Rule 21: Nếu tool lỗi:
         → log TOOL_RUNTIME_ERROR và fallback.

Rule 22: Nếu parser lỗi:
         → retry 1–2 lần.

Rule 23: Nếu gọi tool không tồn tại:
         → log HALLUCINATED_TOOL.

Rule 24: Nếu quá max_steps:
         → log MAX_STEPS_EXCEEDED và escalate_to_human().

Rule 25: Nếu quá timeout:
         → log TIMEOUT và fallback.

Rule 26: Nếu user yêu cầu gặp người thật:
         → escalate_to_human().
```

---

## 8. Phân công cho 5 người

### Người 1 — Project Lead + Rich Dataset + Integration Lead

#### Vai trò chính

```text
Project Lead
Domain Designer
Dataset Owner
Integration Lead
Final Code Reviewer
```

#### Trách nhiệm

```text
- Quản lý tổng thể workflow đặt lịch khám.
- Quản lý dataset CSV.
- Đảm bảo data đúng logic và đủ thực tế.
- Viết data dictionary và business rules.
- Tạo cấu trúc repo chuẩn.
- Quy định cách đặt tên file, function, branch.
- Tổng hợp source code từ các thành viên.
- Merge code cuối cùng.
- Kiểm tra conflict.
- Chạy end-to-end demo lần cuối.
- Kiểm tra app.py chạy được.
- Kiểm tra chatbot baseline chạy được.
- Kiểm tra Agent v1/v2 chạy được.
- Kiểm tra logs sinh ra đúng.
- Kiểm tra UI hiển thị trace và error message.
- Viết phần project overview + dataset + workflow trong report.
```

#### Output cần nộp

```text
data/*.csv
docs/database_schema.md
docs/data_dictionary.md
docs/business_rules.md
docs/workflow.md
README.md
Final integrated repo
Final run checklist
```

---

### Người 2 — Local LLM Provider + Chatbot Baseline

#### Trách nhiệm

```text
- Setup mô hình local bằng Phi-3, llama-cpp-python hoặc Ollama.
- Viết LocalLLMProvider.
- Viết chatbot baseline.
- Log latency và token estimate cho chatbot.
- Chạy chatbot với toàn bộ test cases.
- Viết hướng dẫn setup local model.
```

#### Output cần nộp

```text
src/providers/base.py
src/providers/local_llm.py
src/chatbot/baseline_chatbot.py
logs/chatbot/
docs/local_model_setup.md
```

---

### Người 3 — Tool Design + Data Access + Test Cases

#### Trách nhiệm

```text
- Viết Pydantic schemas.
- Viết csv_loader.py để load dataset.
- Viết query_service.py để filter dữ liệu.
- Viết appointment tools.
- Tạo tool registry.
- Viết tool descriptions rõ ràng.
- Viết 10–15 test cases chính.
- Viết unit test cho tools.
```

#### Output cần nộp

```text
src/data_access/csv_loader.py
src/data_access/query_service.py
src/tools/tool_schema.py
src/tools/appointment_tools.py
src/tools/tool_registry.py
tests/test_cases.json
tests/test_tools.py
```

---

### Người 4 — ReAct Agent v1/v2 + Safeguards

#### Trách nhiệm

```text
- Implement ReAct loop.
- Parse output của LLM.
- Feed Observation ngược lại vào prompt.
- Implement Agent v1.
- Implement Agent v2 cải tiến.
- Thêm max_steps.
- Thêm timeout.
- Thêm parser retry.
- Thêm tool whitelist.
- Thêm repeated tool call detection.
- Thêm fallback sang chatbot hoặc điều phối viên.
```

#### Output cần nộp

```text
src/agent/react_agent.py
src/agent/parser.py
src/agent/prompts.py
logs/agent/
```

---

### Người 5 — UI/UX + Monitoring Dashboard + Evaluation

#### Trách nhiệm

```text
- Làm Streamlit UI.
- Cho phép chọn mode: Chatbot Baseline / Agent v1 / Agent v2.
- Hiển thị câu trả lời.
- Hiển thị trace Thought / Action / Observation.
- Hiển thị metrics.
- Hiển thị log JSON.
- Hiển thị error message thân thiện.
- Viết script parse logs.
- Tạo bảng so sánh Chatbot vs Agent v1 vs Agent v2.
- Chuẩn bị demo flow.
```

#### Output cần nộp

```text
app.py
src/ui/components.py
src/telemetry/logger.py
src/telemetry/metrics.py
tests/run_evaluation.py
report/group_report/evaluation_table.md
```

---

## 9. Bảng chia việc tổng hợp

| Người | Vai trò | Output chính |
|---|---|---|
| Người 1 | Project Lead + Dataset + Integration Lead | Dataset, business rules, merge code, final testing |
| Người 2 | Local LLM + Chatbot Baseline | Local model, chatbot baseline, setup guide |
| Người 3 | Tools + Data Access + Test Cases | Pydantic schema, tools, CSV query, test cases |
| Người 4 | ReAct Agent Core | Agent v1/v2, parser, prompt, safeguards, fallback |
| Người 5 | UI + Logs + Evaluation | Streamlit UI, telemetry, metrics, evaluation table |

---

## 10. Git workflow

Mỗi người nên làm trên branch riêng:

```text
main
├── feature/database-integration-person1
├── feature/local-llm-person2
├── feature/tools-data-access-person3
├── feature/react-agent-person4
└── feature/ui-evaluation-person5
```

Quy tắc:

```text
- Không push trực tiếp vào main.
- Mỗi người làm trên branch riêng.
- Trước khi báo merge, phải chạy được phần code của mình.
- Người 1 là người merge cuối vào main.
- Sau khi merge, Người 1 chạy end-to-end test.
```

---

## 11. Final Integration Checklist cho Người 1

```text
[ ] Clone repo mới hoàn toàn về máy.
[ ] Tạo virtual environment.
[ ] Cài requirements.txt.
[ ] Kiểm tra file .env.
[ ] Kiểm tra local model path.
[ ] Kiểm tra thư mục data/ có đủ CSV.
[ ] Kiểm tra csv_loader.py đọc được tất cả file.
[ ] Kiểm tra tool search_available_slots().
[ ] Kiểm tra tool suggest_specialty_by_symptoms().
[ ] Kiểm tra tool check_payment_coverage().
[ ] Kiểm tra chatbot baseline chạy được.
[ ] Kiểm tra Agent v1 chạy được.
[ ] Kiểm tra Agent v2 chạy được.
[ ] Chạy Streamlit UI.
[ ] Test 3 case thành công.
[ ] Test 3 case lỗi/fallback.
[ ] Kiểm tra logs sinh ra trong logs/.
[ ] Kiểm tra evaluation script chạy được.
[ ] Kiểm tra README hướng dẫn chạy rõ ràng.
```

---

## 12. Pydantic tool schema cập nhật

Ví dụ file `src/tools/tool_schema.py`:

```python
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class SearchSlotInput(BaseModel):
    specialty: Optional[str] = None
    symptoms: Optional[List[str]] = None
    date: Optional[str] = None
    preferred_time: Optional[str] = None
    doctor_gender: Optional[str] = None
    language: Optional[str] = None
    coverage_type: Optional[str] = None
    max_wait_time: Optional[int] = None
    max_price: Optional[int] = None
    telehealth: Optional[bool] = None

class RankSlotsInput(BaseModel):
    slots: List[Dict[str, Any]]
    criteria: List[str] = ["lowest_wait_time", "preferred_time_match", "doctor_rating"]

class BookAppointmentInput(BaseModel):
    patient_name: str
    phone: str
    slot_id: str
    reason_for_visit: Optional[str] = None
    coverage_type: Optional[str] = None
    private_insurance_name: Optional[str] = None

class SymptomSpecialtyInput(BaseModel):
    symptoms: List[str]

class PaymentCoverageInput(BaseModel):
    service_id: str
    coverage_type: str

class PolicyInput(BaseModel):
    query: str
    category: Optional[str] = None

class DoctorProfileInput(BaseModel):
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None

class AlternativeSlotInput(BaseModel):
    specialty: str
    from_date: str
    preferred_time: Optional[str] = None
    max_results: int = 5

class RescheduleAppointmentInput(BaseModel):
    appointment_id: str
    new_slot_id: str

class CancelAppointmentInput(BaseModel):
    appointment_id: str
    reason: Optional[str] = None

class EscalateInput(BaseModel):
    reason: str
    user_query: str
```

---

## 13. Tool list cập nhật

### 13.1. `suggest_specialty_by_symptoms()`

Dùng khi user nói triệu chứng nhưng chưa nói chuyên khoa.

Input:

```json
{
  "symptoms": ["nổi mẩn đỏ", "ngứa"]
}
```

Output:

```json
{
  "status": "success",
  "suggested_specialty": "Da liễu",
  "urgency_level": "normal",
  "note": "Gợi ý khám Da liễu."
}
```

---

### 13.2. `search_available_slots()`

Dùng để tìm slot còn trống.

Input mở rộng:

```json
{
  "specialty": "Tim mạch",
  "date": "2026-06-09",
  "preferred_time": "morning",
  "doctor_gender": "Nữ",
  "language": "English",
  "coverage_type": "BHYT",
  "max_wait_time": 30,
  "max_price": 600000,
  "telehealth": true
}
```

Output:

```json
{
  "status": "success",
  "slots": [
    {
      "slot_id": "SL00027",
      "doctor_name": "BS. Trần Thu Lan",
      "specialty_name": "Tim mạch",
      "service_name": "Khám Tim mạch cơ bản",
      "date": "2026-06-09",
      "start_time": "09:30",
      "estimated_wait_time": 20,
      "base_price": 520000,
      "is_telehealth": "yes",
      "room": "202"
    }
  ]
}
```

---

### 13.3. `rank_slots()`

Dùng để xếp hạng slot phù hợp nhất.

Tiêu chí gợi ý:

```text
lowest_wait_time
preferred_time_match
doctor_rating
earliest_date
price_match
telehealth_match
```

---

### 13.4. `check_payment_coverage()`

Dùng để kiểm tra hỗ trợ BHYT/bảo hiểm tư/tự thanh toán.

Input:

```json
{
  "service_id": "SV001",
  "coverage_type": "BHYT"
}
```

Output:

```json
{
  "status": "success",
  "coverage_type": "BHYT",
  "supported": true,
  "note": "Dịch vụ có hỗ trợ BHYT. Mức hưởng phụ thuộc tuyến khám, giấy tờ hợp lệ và quy định hiện hành."
}
```

---

### 13.5. `get_service_price()`

Dùng để trả lời câu hỏi về giá.

Input:

```json
{
  "specialty": "Da liễu",
  "service_name": "Khám Da liễu tổng quát"
}
```

Output:

```json
{
  "status": "success",
  "service_name": "Khám Da liễu tổng quát",
  "base_price": 400000,
  "preparation_required": "no",
  "preparation_note": "Không bôi thuốc/mỹ phẩm lên vùng da cần khám nếu có thể."
}
```

---

### 13.6. `get_hospital_policy()`

Dùng để trả lời FAQ/chính sách.

Input:

```json
{
  "query": "Tôi cần đến trước bao lâu?"
}
```

Output:

```json
{
  "status": "success",
  "answer": "Bạn nên đến trước giờ hẹn khoảng 15–20 phút để làm thủ tục check-in."
}
```

---

### 13.7. `book_appointment()`

Dùng để đặt lịch sau khi user xác nhận.

Input:

```json
{
  "patient_name": "Nguyễn Văn Nam",
  "phone": "0901234567",
  "slot_id": "SL00027",
  "reason_for_visit": "Đau ngực nhẹ",
  "coverage_type": "BHYT"
}
```

Output:

```json
{
  "status": "success",
  "appointment_id": "A01142",
  "message": "Đặt lịch thành công."
}
```

---

### 13.8. `escalate_to_human()`

Dùng khi cần fallback sang điều phối viên.

Input:

```json
{
  "reason": "PAYMENT_COVERAGE_DETAIL",
  "user_query": "Bảo hiểm tư của tôi chi trả bao nhiêu phần trăm?"
}
```

Output:

```json
{
  "status": "escalated",
  "ticket_id": "T0121",
  "message": "Yêu cầu đã được chuyển sang điều phối viên."
}
```

---

## 14. Agent v1

Agent v1 cần chạy được ReAct loop cơ bản.

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
- Có thể parser error.
- Có thể gọi sai tool.
- Có thể bị loop.
- Chưa xử lý tốt thiếu thông tin.
- Có thể chưa xử lý tốt emergency symptoms.
```

Những lỗi này cần lưu lại để dùng cho phần Failure Analysis.

---

## 15. Agent v2

Agent v2 phải cải thiện dựa trên lỗi của v1.

Cải tiến nên có:

```text
- Tool whitelist.
- Parser retry.
- Missing info rule.
- Emergency symptom guardrail.
- Payment coverage guardrail.
- max_steps = 5.
- timeout_seconds = 20.
- Repeated tool call detection.
- Friendly error messages.
- Fallback sang chatbot hoặc điều phối viên.
```

---

## 16. ReAct format

Agent nên xuất theo format dễ parse.

```text
Thought: Cần kiểm tra chuyên khoa phù hợp từ triệu chứng người dùng.
Action: suggest_specialty_by_symptoms
Action Input: {"symptoms": ["nổi mẩn đỏ", "ngứa"]}
```

Sau khi tool chạy:

```text
Observation: Gợi ý chuyên khoa Da liễu, urgency_level = normal.
```

Sau đó:

```text
Thought: Cần tìm slot Da liễu còn trống theo thời gian người dùng muốn.
Action: search_available_slots
Action Input: {"specialty": "Da liễu", "date": "2026-06-06", "preferred_time": "afternoon"}
```

Khi đủ thông tin:

```text
Final Answer: Mình gợi ý bạn khám Da liễu. Hiện có slot lúc 14:30 ngày 2026-06-06 với thời gian chờ dự kiến 18 phút. Bạn có muốn xác nhận lịch này không?
```

---

## 17. Max iteration safeguard

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

return fallback_to_human(reason="MAX_STEPS_EXCEEDED")
```

Message cho user:

```text
Mình chưa thể hoàn tất yêu cầu tự động sau nhiều bước xử lý. 
Mình sẽ chuyển thông tin này cho điều phối viên để hỗ trợ bạn chính xác hơn.
```

---

## 18. Timeout safeguard

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

## 19. UI/UX yêu cầu

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
8. Bộ lọc demo optional: chuyên khoa, ngày, bác sĩ, BHYT, telehealth.
```

### Error message mapping

| Error code | Message cho người dùng |
|---|---|
| `MISSING_INFORMATION` | Mình cần thêm chuyên khoa, ngày khám hoặc thông tin liên hệ để hỗ trợ đặt lịch. |
| `NO_SLOT_FOUND` | Hiện chưa có slot phù hợp với tất cả điều kiện. Mình có thể gợi ý slot gần nhất hoặc chuyển cho điều phối viên. |
| `EMERGENCY_SYMPTOM` | Triệu chứng bạn mô tả có thể cần hỗ trợ y tế khẩn cấp. Vui lòng gọi cấp cứu hoặc liên hệ hotline bệnh viện. |
| `PAYMENT_COVERAGE_DETAIL` | Quyền lợi bảo hiểm chi tiết cần được quầy bảo hiểm kiểm tra theo hợp đồng. Mình sẽ chuyển yêu cầu sang điều phối viên. |
| `PARSER_ERROR` | Mình chưa thể xử lý yêu cầu tự động ngay lúc này. Vui lòng thử lại hoặc để nhân viên hỗ trợ. |
| `HALLUCINATED_TOOL` | Hệ thống đang gặp lỗi chọn công cụ xử lý. Mình sẽ chuyển sang kênh hỗ trợ dự phòng. |
| `TOOL_RUNTIME_ERROR` | Có lỗi khi kiểm tra lịch khám. Vui lòng thử lại hoặc để nhân viên hỗ trợ tiếp. |
| `TIMEOUT` | Hệ thống đang mất nhiều thời gian hơn dự kiến. Mình sẽ chuyển yêu cầu sang hỗ trợ dự phòng. |
| `MAX_STEPS_EXCEEDED` | Mình chưa thể hoàn tất yêu cầu tự động. Mình sẽ chuyển ca này cho điều phối viên. |

---

## 20. Logging / Telemetry

Mỗi lần chạy cần sinh một file log JSON trong `logs/`.

Ví dụ:

```json
{
  "run_id": "agent_v2_001",
  "version": "agent_v2",
  "user_query": "Tôi muốn khám Tim mạch sáng thứ 3, bác sĩ nữ, chờ dưới 30 phút.",
  "start_time": "2026-06-01T10:00:00",
  "end_time": "2026-06-01T10:00:05",
  "latency_seconds": 5.12,
  "loop_count": 3,
  "tools_called": [
    "search_available_slots",
    "rank_slots",
    "check_payment_coverage"
  ],
  "final_status": "success",
  "error_code": null,
  "fallback_used": false,
  "token_prompt_estimate": 1200,
  "token_completion_estimate": 360,
  "trace": [
    {
      "step": 1,
      "thought": "Cần tìm slot Tim mạch phù hợp với điều kiện của người dùng.",
      "action": "search_available_slots",
      "action_input": {
        "specialty": "Tim mạch",
        "date": "2026-06-09",
        "preferred_time": "morning",
        "doctor_gender": "Nữ",
        "max_wait_time": 30
      },
      "observation": "Tìm thấy 2 slot phù hợp."
    }
  ]
}
```

### Error codes nên có

```text
SUCCESS
MISSING_INFORMATION
NO_SLOT_FOUND
EMERGENCY_SYMPTOM
PAYMENT_COVERAGE_DETAIL
PARSER_ERROR
HALLUCINATED_TOOL
TOOL_RUNTIME_ERROR
TIMEOUT
MAX_STEPS_EXCEEDED
FALLBACK_TO_CHATBOT
FALLBACK_TO_HUMAN
```

---

## 21. Evaluation

Tạo file `tests/test_cases.json` gồm 10–15 cases.

Ví dụ:

```json
[
  {
    "id": "TC01",
    "query": "Tôi muốn khám Tim mạch sáng thứ 3 tuần sau, bác sĩ nữ, chờ dưới 30 phút.",
    "expected_behavior": "Agent tìm slot Tim mạch, filter bác sĩ nữ, chọn slot wait time thấp."
  },
  {
    "id": "TC02",
    "query": "Tôi bị nổi mẩn đỏ và ngứa thì nên khám khoa nào?",
    "expected_behavior": "Agent dùng suggest_specialty_by_symptoms và gợi ý Da liễu."
  },
  {
    "id": "TC03",
    "query": "Tôi có BHYT, khám Nhi khoa có hỗ trợ không?",
    "expected_behavior": "Agent dùng check_payment_coverage, trả lời có hỗ trợ nhưng không cam kết mức hưởng."
  },
  {
    "id": "TC04",
    "query": "Tôi muốn khám online với bác sĩ nói tiếng Anh.",
    "expected_behavior": "Agent tìm slot telehealth và doctor.languages có English."
  },
  {
    "id": "TC05",
    "query": "Tôi đau ngực dữ dội và khó thở nặng.",
    "expected_behavior": "Agent phát hiện emergency/urgent, không đặt lịch thường, khuyến nghị cấp cứu hoặc hotline."
  },
  {
    "id": "TC06",
    "query": "Có slot Da liễu nào dưới 500 nghìn trong tuần này không?",
    "expected_behavior": "Agent filter service price và slot available."
  },
  {
    "id": "TC07",
    "query": "Tôi cần đến trước bao lâu?",
    "expected_behavior": "Agent dùng get_hospital_policy."
  },
  {
    "id": "TC08",
    "query": "Tôi muốn đổi lịch hẹn A00001 sang chiều thứ 5.",
    "expected_behavior": "Agent kiểm tra appointment và slot thay thế."
  },
  {
    "id": "TC09",
    "query": "Khám tổng quát có cần nhịn ăn không?",
    "expected_behavior": "Agent dùng services.preparation_required và hospital_policies."
  },
  {
    "id": "TC10",
    "query": "Tôi muốn đặt lịch càng sớm càng tốt.",
    "expected_behavior": "Agent hỏi lại chuyên khoa hoặc triệu chứng, không tự bịa."
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
| Tool accuracy | Tỷ lệ chọn đúng tool |
| Safety compliance | Tỷ lệ xử lý đúng case urgent/emergency |

---

## 22. Trace thành công mẫu

```text
User:
Tôi muốn khám Tim mạch sáng thứ 3 tuần sau, bác sĩ nữ, chờ dưới 30 phút, có BHYT.

Step 1
Thought:
Cần tìm slot Tim mạch vào sáng thứ 3, bác sĩ nữ và thời gian chờ dưới 30 phút.

Action:
search_available_slots({
  "specialty": "Tim mạch",
  "date": "2026-06-09",
  "preferred_time": "morning",
  "doctor_gender": "Nữ",
  "max_wait_time": 30,
  "coverage_type": "BHYT"
})

Observation:
Tìm thấy 2 slot phù hợp:
- SL00027, 09:30, BS. Trần Thu Lan, wait_time = 20 phút
- SL00031, 10:00, BS. Nguyễn Ngọc Anh, wait_time = 25 phút

Step 2
Thought:
Cần chọn slot có thời gian chờ thấp nhất.

Action:
rank_slots({
  "slots": ["SL00027", "SL00031"],
  "criteria": ["lowest_wait_time", "preferred_time_match", "doctor_rating"]
})

Observation:
Slot tốt nhất là SL00027 lúc 09:30 vì wait_time = 20 phút.

Step 3
Thought:
Cần kiểm tra ghi chú hỗ trợ BHYT cho dịch vụ trước khi trả lời.

Action:
check_payment_coverage({
  "service_id": "SV001",
  "coverage_type": "BHYT"
})

Observation:
Dịch vụ có hỗ trợ BHYT, mức hưởng phụ thuộc tuyến khám và giấy tờ hợp lệ.

Final Answer:
Mình tìm được slot khám Tim mạch lúc 09:30 ngày 2026-06-09 với bác sĩ nữ, thời gian chờ dự kiến khoảng 20 phút. Dịch vụ có hỗ trợ BHYT, nhưng mức hưởng phụ thuộc tuyến khám và giấy tờ hợp lệ. Bạn nên mang thẻ BHYT và CCCD. Bạn có muốn xác nhận lịch này không?
```

---

## 23. Trace thất bại mẫu

```text
User:
Tôi đau ngực dữ dội và khó thở nặng, đặt lịch giúp tôi tuần sau.

Step 1
Thought:
Triệu chứng có thể khẩn cấp, cần kiểm tra mức độ urgency trước khi đặt lịch thường.

Action:
suggest_specialty_by_symptoms({
  "symptoms": ["đau ngực", "khó thở"]
})

Observation:
Triệu chứng gợi ý Tim mạch, urgency_level = urgent.

Step 2
Thought:
Vì người dùng mô tả đau ngực dữ dội và khó thở nặng, không nên tiếp tục đặt lịch thường.

Action:
escalate_to_human({
  "reason": "EMERGENCY_SYMPTOM",
  "user_query": "Tôi đau ngực dữ dội và khó thở nặng, đặt lịch giúp tôi tuần sau."
})

Observation:
Ticket đã được tạo và chuyển sang điều phối viên.

Final Answer:
Triệu chứng đau ngực dữ dội và khó thở nặng có thể cần hỗ trợ y tế khẩn cấp. Bạn không nên chờ lịch khám thường. Vui lòng gọi cấp cứu hoặc liên hệ hotline bệnh viện ngay. Mình cũng đã ghi nhận yêu cầu để điều phối viên hỗ trợ tiếp.
```

---

## 24. Failure Analysis mẫu cho report

### Failure case: Agent v1 tự bịa mức chi trả bảo hiểm

#### Log

```json
{
  "version": "agent_v1",
  "error_code": "PAYMENT_COVERAGE_DETAIL",
  "user_query": "Bảo hiểm tư Manulife chi trả bao nhiêu phần trăm cho khám tổng quát?",
  "agent_answer": "Bảo hiểm Manulife chi trả 80%.",
  "problem": "Dataset không có thông tin mức chi trả chi tiết theo hợp đồng."
}
```

#### Nguyên nhân

Agent v1 chưa có rule giới hạn về bảo hiểm tư. Mô hình tự suy đoán phần trăm chi trả.

#### Cách sửa ở Agent v2

```text
- Thêm business rule: không cam kết mức chi trả bảo hiểm tư.
- check_payment_coverage chỉ trả về có hỗ trợ/cần kiểm tra thêm.
- Nếu hỏi quyền lợi chi tiết, fallback sang điều phối viên.
```

#### Kết quả sau khi sửa

Agent v2 trả lời:

```text
Khám tổng quát có thể hỗ trợ bảo hiểm tư nhân tùy hợp đồng. 
Mức chi trả cụ thể cần quầy bảo hiểm kiểm tra theo quyền lợi của bạn. 
Mình có thể chuyển yêu cầu này cho điều phối viên hỗ trợ.
```

---

## 25. Timeline thực hiện 5 ngày

### Ngày 1 — Setup + Dataset + Rules

```text
- Tạo repo.
- Chốt use case.
- Copy dataset CSV vào data/.
- Viết data dictionary.
- Viết business rules.
- Setup local model.
- Viết test cases bản đầu.
```

Kết quả cuối ngày:

```text
- Dataset sẵn sàng.
- Local model chạy được.
- Có danh sách tool.
- Có test cases.
```

---

### Ngày 2 — Baseline + Data Access + Tools

```text
- Hoàn thành chatbot baseline.
- Hoàn thành csv_loader.py.
- Hoàn thành query_service.py.
- Hoàn thành tool schema.
- Hoàn thành appointment tools.
- Test từng tool độc lập.
```

Kết quả cuối ngày:

```text
- Chatbot baseline chạy được.
- Tools query được CSV.
- Có log chatbot.
```

---

### Ngày 3 — Agent v1

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

```text
- Sửa lỗi từ v1.
- Thêm max_steps.
- Thêm timeout.
- Thêm parser retry.
- Thêm emergency/payment guardrails.
- Thêm fallback.
- Hoàn thành Streamlit UI.
```

Kết quả cuối ngày:

```text
- Agent v2 tốt hơn v1.
- UI hiển thị trace, metrics và error handling.
```

---

### Ngày 5 — Evaluation + Integration + Report + Demo

```text
- Người 1 merge code lần cuối.
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
- Repo chạy được end-to-end.
```

---

## 26. Demo flow trước giảng viên

Nhóm nên demo 5 case.

### Case 1 — Chatbot baseline trả lời chung chung

User:

```text
Tôi muốn khám Tim mạch sáng thứ 3 tuần sau, bác sĩ nữ, chờ dưới 30 phút.
```

Thông điệp:

```text
Chatbot trả lời được nhưng không kiểm tra dữ liệu thật, không biết slot nào còn trống.
```

---

### Case 2 — Agent v2 đặt lịch thành công

Agent gọi:

```text
search_available_slots()
rank_slots()
check_payment_coverage()
```

Thông điệp:

```text
Agent biết dùng tool và trả lời dựa trên dataset.
```

---

### Case 3 — Đặt lịch theo triệu chứng

User:

```text
Tôi bị nổi mẩn đỏ và ngứa thì nên khám khoa nào?
```

Agent gọi:

```text
suggest_specialty_by_symptoms()
search_available_slots()
```

Thông điệp:

```text
Agent không cần user nói chuyên khoa từ đầu, có thể gợi ý chuyên khoa từ triệu chứng.
```

---

### Case 4 — Câu hỏi chính sách

User:

```text
Khám tổng quát có cần nhịn ăn không?
```

Agent gọi:

```text
get_hospital_policy()
get_service_price()
```

Thông điệp:

```text
Agent không chỉ đặt lịch mà còn trả lời FAQ dựa trên dữ liệu.
```

---

### Case 5 — Emergency / fallback

User:

```text
Tôi đau ngực dữ dội và khó thở nặng.
```

Agent gọi:

```text
suggest_specialty_by_symptoms()
escalate_to_human()
```

Thông điệp:

```text
Agent có safety guardrail, không cố đặt lịch thường cho case khẩn cấp.
```

---

## 27. Checklist trước khi nộp

### Code

```text
[ ] Chạy được local model.
[ ] Chạy được chatbot baseline.
[ ] Chạy được Agent v1.
[ ] Chạy được Agent v2.
[ ] Có ít nhất 2 tools.
[ ] Có dataset CSV trong data/.
[ ] Có Pydantic schema.
[ ] Có csv_loader.py.
[ ] Có query_service.py.
[ ] Có max_steps.
[ ] Có timeout.
[ ] Có fallback.
[ ] Có logs JSON.
[ ] Có Streamlit UI.
```

### Evaluation

```text
[ ] Có 10–15 test cases.
[ ] Có bảng so sánh Chatbot vs Agent v1 vs Agent v2.
[ ] Có success trace.
[ ] Có failed trace.
[ ] Có failure analysis.
[ ] Có metrics: latency, loop count, parser error, fallback rate.
[ ] Có safety compliance cho emergency symptoms.
```

### Report

```text
[ ] Có group report.
[ ] Có dataset description.
[ ] Có tool design evolution.
[ ] Có flowchart.
[ ] Có insight nhóm học được.
[ ] Mỗi thành viên có individual report.
[ ] Mỗi thành viên ghi rõ contribution.
[ ] Mỗi thành viên có debugging case study.
```

---

## 28. Cách đạt bonus

| Bonus | Cách làm |
|---|---|
| Extra Monitoring | Thêm latency, token estimate, cost estimate, loop count, fallback rate, tool accuracy |
| Extra Tools | Thêm `get_service_price`, `suggest_alternative_slots`, `reschedule_appointment`, `send_reminder` |
| Failure Handling | Thêm parser retry, timeout, max_steps, repeated tool detection, safety guardrails |
| Live System Demo | Demo trực tiếp bằng Streamlit |
| Ablation Experiments | So sánh Agent v1 prompt vs Agent v2 prompt; bật/tắt guardrails |

---

## 29. Kết luận

Workflow cập nhật:

```text
Người 1: Dataset + business rules + integration lead
Người 2: Local model + chatbot baseline
Người 3: Data access + tools + test cases
Người 4: ReAct agent + safeguards
Người 5: UI + logs + evaluation
```

Demo cần chứng minh:

```text
1. Chatbot nói được nhưng không kiểm chứng dữ liệu.
2. ReAct Agent biết gọi tool và xử lý bài toán nhiều bước.
3. Dataset đủ lớn để mô phỏng đặt lịch trong 2 tuần tiếp theo.
4. Agent v2 tốt hơn v1 vì được cải thiện bằng logs, trace và failure analysis.
5. Hệ thống có error handling, max iteration safeguard, timeout và fallback an toàn.
