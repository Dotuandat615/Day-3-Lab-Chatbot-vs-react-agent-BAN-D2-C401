# Evaluation Table — Chatbot vs Agent v1 vs Agent v2

> Generated: 2026-06-01 (template — sẽ được overwrite bởi `tests/run_evaluation.py`)

---

## 1. Bảng So Sánh Tổng Hợp

> ⚠️ **Số liệu bên dưới là ví dụ tham khảo.** Chạy `python tests/run_evaluation.py` để cập nhật số liệu thực tế từ logs.

| Version | N Runs | Success Rate | Avg Latency | Avg Loop Count | Parser Error | Timeout | Hallucination | Fallback Rate |
|:--------|-------:|-------------:|------------:|---------------:|-------------:|--------:|--------------:|--------------:|
| 💬 Chatbot Baseline | 10 | 40.0% | 1.20s | 0.0 | 0.0% | 0.0% | 0.0% | 0.0% |
| 🤖 Agent v1 | 10 | 65.0% | 6.50s | 4.1 | 20.0% | 10.0% | 15.0% | 15.0% |
| 🚀 Agent v2 | 10 | 85.0% | 5.20s | 3.0 | 5.0% | 5.0% | 3.0% | 8.0% |

> Số liệu trên là ví dụ theo tài liệu hướng dẫn. Nhóm cần thay bằng số liệu thật từ log.

---

## 2. Metrics Definitions

| Metric | Ý nghĩa |
|:-------|:--------|
| Success Rate | Tỷ lệ run có `final_status = success` |
| Avg Latency | Thời gian xử lý trung bình (giây) |
| Avg Loop Count | Số vòng ReAct Thought→Action→Observation trung bình |
| Parser Error | Tỷ lệ run gặp lỗi parse output của LLM |
| Timeout | Tỷ lệ run bị timeout (> 20 giây) |
| Hallucination | Tỷ lệ run agent gọi tool không có trong registry |
| Fallback Rate | Tỷ lệ run phải fallback sang chatbot hoặc điều phối viên |

---

## 3. Test Cases Đã Sử Dụng

| ID | Query | Expected Behavior |
|:---|:------|:-----------------|
| TC01 | Tôi muốn khám Tim mạch sáng thứ 3 tuần sau, ít phải chờ. | Agent tìm slot Tim mạch, chọn slot wait time thấp nhất. |
| TC02 | Tôi muốn khám Da liễu chiều mai. | Agent tìm slot Da liễu vào buổi chiều. |
| TC03 | Đặt lịch khám cho tôi càng sớm càng tốt. | Agent hỏi lại chuyên khoa vì thiếu thông tin. |
| TC04 | Có bác sĩ Nhi nào rảnh cuối tuần không? | Agent tìm slot Nhi khoa cuối tuần. |
| TC05 | Tôi muốn khám Tim mạch nhưng ngày đó hết slot. | Agent gợi ý ngày thay thế. |
| TC06 | Đặt lịch cho Nguyễn Văn Nam, SĐT 0901234567, khám tổng quát. | Agent tìm slot tổng quát và đặt lịch sau khi xác nhận. |
| TC07 | Tôi bị đau ngực, muốn khám gấp. | Agent tìm slot Tim mạch sớm nhất. |
| TC08 | Hủy lịch khám của tôi. | Agent yêu cầu thêm thông tin hoặc escalate. |
| TC09 | Khám da liễu ở phòng nào? | Agent trả về thông tin phòng khám từ database. |
| TC10 | Bác sĩ Minh có lịch trống không tuần tới? | Agent tìm slot của bác sĩ Minh trong tuần tới. |

---

## 4. Failure Analysis

### Failure Case 1: Agent v1 gọi tool không tồn tại (HALLUCINATED_TOOL)

```json
{
  "version": "agent_v1",
  "error_code": "HALLUCINATED_TOOL",
  "tool_name": "check_doctor_schedule",
  "available_tools": ["search_available_slots", "rank_slots", "book_appointment"]
}
```

**Nguyên nhân:** Agent v1 chưa có tool whitelist rõ ràng trong system prompt. Mô hình tự tạo ra tool `check_doctor_schedule` vì tên nghe hợp lý với bài toán.

**Cách sửa ở Agent v2:**
- Thêm danh sách tool hợp lệ vào system prompt.
- Parser kiểm tra tool name có trong registry không.
- Nếu tool không tồn tại, log `HALLUCINATED_TOOL` và retry 1 lần với thông báo chỉ được dùng tool hợp lệ.

**Kết quả sau khi sửa:** Agent v2 chuyển sang dùng đúng tool `search_available_slots`.

---

### Failure Case 2: Agent v1 bị loop vô hạn (MAX_STEPS_EXCEEDED)

**Query:** "Đặt lịch cho tôi" (thiếu chuyên khoa và ngày)

**Trace Agent v1:**
```
Step 1: Thought: Cần tìm slot → Action: search_available_slots({}) → Error: Missing specialty
Step 2: Thought: Thử lại với specialty=null → Action: search_available_slots({specialty: null}) → Error
Step 3: Thought: Thử lại... → (lặp lại)
```

**Nguyên nhân:** Agent v1 không có missing info rule, cứ thử gọi tool thay vì hỏi lại người dùng.

**Cách sửa ở Agent v2:** Thêm rule: nếu thiếu `specialty` hoặc `date`, hỏi lại trước khi gọi tool.

---

## 5. Kết Luận và Phân Tích

| Điểm mạnh | 💬 Chatbot | 🤖 Agent v1 | 🚀 Agent v2 |
|:----------|:----------:|:-----------:|:-----------:|
| Tốc độ phản hồi | ✅ Nhanh (~1.2s) | ⚠️ Chậm (~6.5s) | ⚠️ Chậm hơn chatbot (~5.2s) |
| Truy vấn database thực | ❌ Không | ✅ Có | ✅ Có |
| Xử lý thông tin thiếu | ❌ Tự bịa | ⚠️ Có thể loop | ✅ Hỏi lại |
| Guardrails | ❌ Không | ❌ Không | ✅ max_steps + timeout |
| Parser robustness | N/A | ⚠️ Fragile | ✅ Retry logic |
| Độ chính xác multi-step | ⚠️ Hallucinate | ⚠️ Có thể sai | ✅ Tốt nhất |
| Fallback an toàn | ❌ Không | ❌ Không | ✅ Có |

### Nhận xét

1. **Chatbot Baseline** phù hợp cho câu hỏi đơn giản (Q&A), phản hồi nhanh. Tuy nhiên không thể truy vấn database thực và dễ hallucinate thông tin lịch khám.

2. **Agent v1** chứng minh được ReAct loop hoạt động. Có thể gọi tool và nhận Observation. Nhược điểm: chưa xử lý lỗi tốt, dễ bị loop khi thiếu thông tin.

3. **Agent v2** cải thiện rõ rệt dựa trên failure analysis của v1. Các guardrails (max_steps, timeout, parser retry, tool whitelist) giúp hệ thống ổn định hơn trong production.

> 🎯 **Kết luận chính**: Phương pháp ReAct Agent phù hợp cho bài toán đặt lịch khám (multi-step, cần truy vấn database). Việc so sánh v1→v2 thông qua logs và failure traces là phương pháp cải tiến dựa trên dữ liệu thực tế, không phải cảm tính.

---

## 6. Hướng Cải Tiến Tiếp Theo

| Cải tiến | Mô tả | Ưu tiên |
|:---------|:------|:-------:|
| RAG Integration | Thêm vector search để tra cứu thông tin bác sĩ linh hoạt hơn | ⭐⭐⭐ |
| Multi-agent | Tách agent đặt lịch và agent tư vấn y tế | ⭐⭐ |
| Streaming UI | Hiển thị trace real-time thay vì chờ hoàn thành | ⭐⭐ |
| Cost tracking | Theo dõi chi phí API thực tế | ⭐ |
| A/B testing | So sánh các prompt template khác nhau | ⭐ |

---

*Báo cáo này được tạo bởi `tests/run_evaluation.py`*
*Người 5 — UI/UX + Monitoring Dashboard + Evaluation*
