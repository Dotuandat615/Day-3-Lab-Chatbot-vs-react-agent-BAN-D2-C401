# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Phan Văn Hiếu
- **Student ID**: 2A202600732
- **Date**: 01-06-2026

---

## I. Technical Contribution (15 Points)

*Tập trung phát triển lõi của hệ thống ReAct Agent, bao gồm vòng lặp suy luận (Reasoning Loop), cơ chế thực thi công cụ (Tool Execution), parser cho đầu ra của LLM và lớp guardrail nhằm tăng tính an toàn cho agent.*

- **Modules Implementated**: `src/agent/agent.py`, `src/agent/guardrail.py`
- **Code Highlights**: 
    - Xây dựng vòng lặp ReAct hoàn chỉnh trong `ReActAgent.run()` theo mô hình: User Input -> LLM Reasoning -> Structured JSON Parsing -> Tool Execution -> Observation -> Next Reasoning Step
    - Thiết kế schema đầu ra có cấu trúc bằng Pydantic (`Action`, `ReActStep`) để ép mô hình trả về định dạng JSON xác định thay vì văn bản tự do.
    - Cài đặt cơ chế parsing mạnh hơn bằng `_extract_first_json()` kết hợp `JSONDecoder.raw_decode()` nhằm xử lý các trường hợp LLM trả về:
    - Markdown code fences
    - Nhiều JSON object liên tiếp
    - JSON kèm theo văn bản thừa
    - Xây dựng cơ chế dynamic tool dispatch thông qua `_execute_tool()`, cho phép ánh xạ tên tool sang hàm thực thi tương ứng và hỗ trợ mở rộng tool mới mà không cần sửa đổi vòng lặp agent.
giúp phân tích lỗi và theo dõi quá trình suy luận của agent.
    - Phát triển lớp guardrail hai tầng:
        1. Rule-based filtering bằng Regex để phát hiện Prompt Injection.
        2. LLM-based intent classification để giới hạn agent chỉ xử lý các yêu cầu thuộc miền đặt lịch khám bệnh.
    - Áp dụng nguyên tắc "fail closed" trong guardrail: nếu bộ phân loại gặp lỗi hoặc không xác định được intent, yêu cầu sẽ bị từ chối thay vì được xử lý.

- **Documentation**: 
Hệ thống được thiết kế theo kiến trúc ReAct (Reasoning + Acting), trong đó mô hình ngôn ngữ không trả lời trực tiếp mà thực hiện chuỗi suy luận nhiều bước.

Quy trình hoạt động:

    1. Người dùng gửi yêu cầu.
    2. Guardrail kiểm tra:
    - Prompt injection.
    - Intent có thuộc phạm vi hỗ trợ hay không.
    3. Agent xây dựng system prompt chứa:
    - Danh sách tool khả dụng.
    - Quy tắc ReAct.
    - Định dạng JSON bắt buộc.
    4. LLM sinh một đối tượng `ReActStep` gồm:
    - `thought`
    - `action`
    - hoặc `final_answer`
    5. Nếu có `action`, agent:
    - Parse JSON.
    - Validate bằng Pydantic.
    - Thực thi tool tương ứng.
    6. Kết quả tool được đưa trở lại prompt dưới dạng `Observation`.
    7. LLM tiếp tục suy luận dựa trên observation mới.
    8. Quá trình lặp lại cho tới khi mô hình trả về `final_answer` hoặc đạt `max_steps`.
    Kiến trúc này cho phép agent tương tác với môi trường bên ngoài thông qua tool thay vì chỉ dựa vào kiến thức có sẵn trong mô hình, đồng thời duy trì khả năng giải thích được quá trình ra quyết định thông qua các bước Thought và Observation được ghi log đầy đủ.
---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*
- **Problem Description**: Trong quá trình thử nghiệm ReAct Agent, mô hình đã vi phạm định dạng output được yêu cầu. Thay vì trả về một JSON object duy nhất cho mỗi bước suy luận, LLM trả về liên tiếp hai JSON object trong cùng một response:
JSON thứ nhất chứa action,
JSON thứ hai chứa final_answer
Điều này làm parser không thể xử lý đúng và agent dừng lại với lỗi validation.
- **Log Source**:
    ```
    {"timestamp": "2026-06-01T07:13:10.054277", "event": "AGENT_START", "data": {"input": "Please use the dummy tool to echo 'Hello, World!'", "model": "gemini-2.5-flash-lite"}}
{"timestamp": "2026-06-01T07:13:11.726986", "event": "LLM_RESPONSE", "data": {"step": 0, "response": {"content": "{\n  \"thought\": \"The user wants me to use the dummy tool to echo 'Hello, World!'. I should call the dummy_tool with the message 'Hello, World!'.\",\n  \"action\": {\n    \"tool\": \"dummy_tool\",\n    \"arguments\": {\n      \"message\": \"Hello, World!\"\n    }\n  },\n  \"final_answer\": null\n}\n{\n  \"thought\": \"The dummy tool has echoed 'Hello, World!'. The user's request is fulfilled.\",\n  \"action\": null,\n  \"final_answer\": \"Hello, World!\"\n}\n", "usage": {"prompt_tokens": 226, "completion_tokens": 138, "total_tokens": 364}, "latency_ms": 1672, "provider": "google"}}}
{"timestamp": "2026-06-01T07:13:11.728434", "event": "OUTPUT_VALIDATION_ERROR", "data": {"step": 0, "error": "1 validation error for ReActStep\n  Invalid JSON: trailing characters at line 11 column 1 [type=json_invalid, input_value='{\\n  \"thought\": \"The use...er\": \"Hello, World!\"\\n}', input_type=str]\n    For further information visit https://errors.pydantic.dev/2.13/v/json_invalid"}}
     ```
- **Diagnosis**: Nguyên nhân không nằm ở tool mà đến từ hành vi của LLM. Mặc dù system prompt đã yêu cầu "Return EXACTLY ONE JSON object", mô hình vẫn cố gắng thực hiện cả hai bước suy luận trong một lần phản hồi: vừa gọi tool vừa tự tạo luôn câu trả lời cuối cùng.
Điều này cho thấy chỉ dựa vào prompt là chưa đủ để đảm bảo mô hình luôn tuân thủ định dạng đầu ra mong muốn.
- **Solution**: Để khắc phục, bổ sung cơ chế parsing mạnh hơn thông qua hàm _extract_first_json(), sử dụng JSONDecoder.raw_decode() để chỉ lấy JSON object đầu tiên hợp lệ từ phản hồi của mô hình. Đồng thời, system prompt được chỉnh sửa để nhấn mạnh rằng mỗi lần phản hồi chỉ được phép thực hiện một bước suy luận duy nhất.
Sau khi sửa, agent đã thực hiện đúng quy trình ReAct:
Thought → Action → Observation → Final Answer
và hoàn thành yêu cầu thành công mà không còn gặp lỗi validation.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: điểm khác biệt lớn nhất là ReAct Agent có thể chia bài toán thành nhiều bước nhỏ thông qua Thought thay vì trả lời ngay như Chatbot. Nhờ đó agent biết khi nào cần gọi tool, khi nào đã đủ thông tin để trả lời. Ngoài ra, việc log lại các bước Thought cũng giúp debug dễ hơn rất nhiều.
2.  **Reliability**: ReAct Agent không phải lúc nào cũng tốt hơn Chatbot. Với các câu hỏi đơn giản hoặc không cần dùng tool, Chatbot thường nhanh và ổn định hơn. Trong quá trình làm lab, agent đôi khi gặp lỗi parse JSON, gọi sai tool hoặc lặp lại hành động không cần thiết, trong khi Chatbot có thể trả lời trực tiếp.
3.  **Observation**: Observation đóng vai trò như phản hồi từ môi trường sau mỗi lần gọi tool. Agent sử dụng thông tin này để quyết định bước tiếp theo thay vì chỉ dựa vào kiến thức ban đầu. Nếu tool trả về lỗi hoặc kết quả không như mong muốn, agent có thể điều chỉnh chiến lược, thử hành động khác hoặc kết thúc với câu trả lời phù hợp hơn.
---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: Nếu mở rộng hệ thống, có thể sẽ tách việc thực thi tool sang các worker bất đồng bộ (asynchronous workers) thay vì chạy trực tiếp trong agent. Cách này giúp xử lý nhiều yêu cầu đồng thời và dễ tích hợp thêm các tool mới.
- **Safety**: Hiện tại hệ thống mới có guardrail đơn giản. Trong môi trường production, bổ sung một lớp "Supervisor" để kiểm tra action trước khi thực thi, đồng thời áp dụng validation chặt chẽ hơn cho output của LLM nhằm giảm lỗi và hạn chế các hành vi ngoài phạm vi cho phép.
- **Performance**: Khi số lượng tool tăng lên, việc đưa toàn bộ mô tả tool vào prompt sẽ làm tăng chi phí và độ trễ. Một hướng cải tiến là sử dụng Vector Database để lưu embedding của các tool và chỉ truy xuất những tool liên quan nhất cho từng yêu cầu trước khi đưa vào context của agent.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
