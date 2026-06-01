# Individual Report: Lab 3 - Chatbot vs ReAct Agent

* **Student Name**: Hoàng Hiếu Trung
* **Student ID**: 2A202600702
* **Date**: 01/06/2026

---

# I. Technical Contribution (15 Points)

## Specific Contribution

Trong dự án AI Trợ Lý Đặt Lịch Khám, tôi phụ trách vai trò **Local LLM Provider + Chatbot Baseline**.

Các nhiệm vụ chính bao gồm:

* Thiết lập và chạy mô hình ngôn ngữ cục bộ bằng `llama-cpp-python`.
* Tích hợp mô hình `Phi-3-mini-4k-instruct` dưới định dạng GGUF.
* Xây dựng lớp `LocalProvider` để chuẩn hóa việc tương tác với mô hình.
* Xây dựng `BaselineChatbot` không sử dụng tool hoặc database.
* Thêm hệ thống logging cho latency, token usage và trace.
* Hỗ trợ kiểm thử hiệu năng chatbot để so sánh với ReAct Agent.

## Modules Implemented

```text
src/core/llm_provider.py
src/core/local_provider.py
src/chatbot/baseline.py
logs/chatbot/
```

## Code Highlights

### LocalProvider

```python
response = self.llm(
    full_prompt,
    max_tokens=1024,
    stop=["<|end|>", "Observation:"],
    echo=False
)
```

Provider chịu trách nhiệm:

* Load mô hình GGUF.
* Gửi prompt tới mô hình.
* Thu thập latency.
* Thu thập token usage.
* Trả kết quả theo định dạng thống nhất.

### Baseline Chatbot

```python
result = self.provider.generate(
    prompt=user_input,
    system_prompt=self.SYSTEM_PROMPT
)
```

Chatbot baseline chỉ dựa trên khả năng sinh văn bản của mô hình mà không truy cập dữ liệu thực tế.

## Documentation

Kiến trúc tôi phụ trách:

```text
User
 ↓
Baseline Chatbot
 ↓
LocalProvider
 ↓
Phi-3 GGUF
 ↓
Response
```

Khác với ReAct Agent, chatbot không sử dụng vòng lặp Thought → Action → Observation và không gọi bất kỳ tool nào.

---

# II. Debugging Case Study (10 Points)

## Problem Description

Trong quá trình tích hợp mô hình cục bộ, hệ thống không thể tải được mô hình GGUF.

Lỗi xuất hiện:

```text
ValueError: Failed to load model from file
```

## Log Source

```text
ValueError: Failed to load model from file:
D:/.../models/Qwen3-14B-Q4_K_M.gguf
```

## Diagnosis

Ban đầu tôi thử sử dụng mô hình Qwen3-14B GGUF.

Nguyên nhân gây lỗi gồm:

* Dung lượng mô hình quá lớn đối với môi trường thử nghiệm.
* Mô hình không phù hợp với tài nguyên phần cứng hiện có.
* Việc chuyển sang Qwen3 yêu cầu thay đổi chat template và phát sinh nhiều vấn đề tương thích.

Ngoài ra, thời gian phản hồi của mô hình 14B không phù hợp với yêu cầu latency của bài lab.

## Solution

Tôi quyết định quay lại sử dụng:

```text
Phi-3-mini-4k-instruct-q4.gguf
```

Các thay đổi:

* Khôi phục LocalProvider theo định dạng prompt của Phi-3.
* Giữ nguyên cấu trúc generate().
* Loại bỏ các thay đổi liên quan đến Qwen3 chat template.
* Kiểm thử lại chatbot bằng Phi-3.

Kết quả:

* Mô hình load thành công.
* Latency giảm đáng kể.
* Hệ thống ổn định hơn cho phần demo.

---

# III. Personal Insights: Chatbot vs ReAct (10 Points)

## 1. Reasoning

Chatbot chỉ sinh câu trả lời trực tiếp dựa trên prompt.

ReAct Agent có thêm bước suy luận thông qua khối Thought trước khi quyết định hành động tiếp theo.

Điều này giúp Agent:

* Chia nhỏ bài toán.
* Xác định khi nào cần gọi tool.
* Giảm khả năng trả lời cảm tính.

## 2. Reliability

Trong một số trường hợp Agent hoạt động kém hơn Chatbot:

* Gọi sai tool.
* Lỗi parser.
* Vòng lặp kéo dài nhiều bước.
* Timeout.

Trong khi đó chatbot luôn tạo phản hồi ngay lập tức vì không phụ thuộc vào tool.

Tuy nhiên chatbot không thể kiểm chứng dữ liệu thực tế và dễ tạo ra thông tin không chính xác.

## 3. Observation

Observation là yếu tố quan trọng nhất tạo nên sự khác biệt của Agent.

Ví dụ:

```text
Thought:
Cần tìm lịch khám còn trống.

Action:
search_available_slots()

Observation:
Tìm thấy 3 slot.
```

Agent sử dụng Observation làm dữ liệu đầu vào cho bước suy luận tiếp theo.

Chatbot không có cơ chế này nên không thể tương tác với môi trường bên ngoài.

---

# IV. Future Improvements (5 Points)

## Scalability

* Triển khai mô hình thông qua API service riêng.
* Hỗ trợ nhiều người dùng đồng thời.
* Sử dụng hàng đợi bất đồng bộ cho các tác vụ nặng.

## Safety

* Bổ sung cơ chế phát hiện Prompt Injection.
* Xây dựng lớp kiểm duyệt đầu vào và đầu ra.
* Giới hạn quyền truy cập tool bằng whitelist.

## Performance

* Sử dụng mô hình nhỏ hơn cho các tác vụ đơn giản.
* Áp dụng caching cho các truy vấn lặp lại.
* Sử dụng Vector Database khi số lượng tool tăng lên.

---

## Conclusion

Qua bài lab này, tôi hiểu rõ hơn sự khác biệt giữa chatbot truyền thống và ReAct Agent.

Chatbot có ưu điểm về tốc độ và tính đơn giản, trong khi ReAct Agent mạnh hơn ở khả năng suy luận nhiều bước và tương tác với môi trường thông qua tool. Việc xây dựng Local LLM Provider và Baseline Chatbot giúp tạo nền tảng để đánh giá khách quan hiệu quả của Agent trong các phần tiếp theo của dự án.
