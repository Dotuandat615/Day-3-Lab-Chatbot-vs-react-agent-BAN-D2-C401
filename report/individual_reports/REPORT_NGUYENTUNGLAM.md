# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Tùng Lâm
- **Student ID**: 2A202600555
- **Role**: UI/UX + Monitoring Dashboard + Evaluation
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

### Modules đã triển khai

| File | Mô tả |
|:-----|:------|
| [`app.py`](../../app.py) | Streamlit app chính — 3 tabs: Chat, History & Logs, So sánh |
| [`src/ui/components.py`](../../src/ui/components.py) | UI component library: CSS dark-mode, trace viewer, metrics panel, error messages, comparison table |
| [`src/telemetry/logger.py`](../../src/telemetry/logger.py) | Nâng cấp IndustryLogger: hỗ trợ `save_run_log()`, `load_run_logs()`, ghi JSON theo version |
| [`src/telemetry/metrics.py`](../../src/telemetry/metrics.py) | Nâng cấp PerformanceTracker: `compute_aggregate()`, cost estimate, aggregate stats |
| [`tests/run_evaluation.py`](../../tests/run_evaluation.py) | Script parse logs, tính metrics, in console table, xuất `evaluation_table.md` |
| [`report/group_report/evaluation_table.md`](evaluation_table.md) | Bảng so sánh Chatbot vs Agent v1 vs Agent v2 |

---

### Code Highlights

#### 1. `save_run_log()` trong `logger.py`

```python
def save_run_log(self, version, user_query, start_time, end_time,
                 latency_seconds, loop_count, tools_called,
                 final_status, error_code, fallback_used,
                 token_prompt_estimate, token_completion_estimate,
                 trace, final_answer="") -> str:
    run_id = f"{version}_{uuid.uuid4().hex[:8]}"
    # Ghi JSON đầy đủ vào logs/chatbot/ hoặc logs/agent/
    ...
    return run_id
```

Mỗi run được lưu thành **file JSON riêng** (không gộp vào một file log chung), giúp `run_evaluation.py` parse chính xác theo version.

---

#### 2. `compute_aggregate()` trong `metrics.py`

```python
def compute_aggregate(self, runs: List[Dict]) -> Dict:
    n = len(runs)
    success_count = sum(1 for r in runs if r.get("final_status") == "success")
    fallback_count = sum(1 for r in runs if r.get("fallback_used", False))
    parser_error_count = sum(1 for r in runs if r.get("error_code") == "PARSER_ERROR")
    # ...
    return {
        "success_rate": round(success_count / n * 100, 1),
        "avg_latency_s": round(sum(latencies) / n, 2),
        "fallback_rate": round(fallback_count / n * 100, 1),
        # ...
    }
```

Hàm này nhận list các run logs đã đọc từ file JSON và tính **8 metrics** chuẩn industry.

---

#### 3. `render_trace()` trong `components.py`

```python
def render_trace(trace: List[Dict]):
    for step in trace:
        with st.expander(f"Step {step['step']}", expanded=True):
            st.markdown(f'<div class="trace-thought">💭 Thought: {step["thought"]}</div>', ...)
            st.markdown(f'<div class="trace-action">⚡ Action: {step["action"]}</div>', ...)
            st.markdown(f'<div class="trace-observation">👁️ Observation: {step["observation"]}</div>', ...)
```

Mỗi step trong ReAct trace được hiển thị với **màu sắc riêng**: tím (Thought), vàng (Action), xanh (Observation) — giúp người dùng dễ theo dõi luồng suy luận của agent.

---

#### 4. Friendly Error Messages

```python
ERROR_MESSAGES = {
    "MAX_STEPS_EXCEEDED": "🔄 Mình chưa thể hoàn tất yêu cầu tự động sau nhiều bước...",
    "HALLUCINATED_TOOL": "🔧 Hệ thống đang gặp lỗi chọn công cụ...",
    "TIMEOUT": "⏰ Hệ thống đang mất nhiều thời gian hơn dự kiến...",
    # 9 error codes đầy đủ
}
```

Thay vì hiển thị technical error code, UI map sang **ngôn ngữ tự nhiên thân thiện** với người dùng cuối.

---

### Cách code tương tác với ReAct loop

```
[Người 4: ReActAgent.run()]
        │
        ▼
  Trả về result dict: {answer, trace, loop_count, tools_called, ...}
        │
        ▼
[app.py: main()]
   ├── logger.save_run_log() → logs/agent/agent_v2_xxxx.json
   ├── render_final_answer(result)
   ├── render_trace(result["trace"])       ← components.py
   └── render_metrics(run_log)             ← components.py

[tests/run_evaluation.py]
   ├── logger.load_run_logs() → đọc tất cả JSON
   ├── tracker.compute_aggregate() → tính metrics
   └── write_evaluation_markdown() → evaluation_table.md
```

---

## II. Debugging Case Study (10 Points)

### Vấn đề: Streamlit không import được `src.*` khi chạy từ thư mục gốc

**Mô tả:** Khi chạy `streamlit run app.py`, Python không tìm thấy module `src.telemetry.logger`:

```
ModuleNotFoundError: No module named 'src'
```

**Nguyên nhân:** Streamlit chạy file với working directory là thư mục chứa file, không phải project root. `sys.path` không chứa root của project.

**Cách fix trong `app.py`:**

```python
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
```

Thêm root vào `sys.path` trước khi import bất kỳ module nào từ `src.*`. Đây là pattern chuẩn cho Streamlit projects không dùng package manager.

---

### Vấn đề 2: Logger bị duplicate handlers khi `@st.cache_resource` re-init

**Mô tả:** Mỗi lần Streamlit hot-reload, `IndustryLogger` bị khởi tạo lại → `logging.getLogger()` trả về cùng instance nhưng `addHandler()` bị gọi nhiều lần → mỗi log message bị in ra console nhiều lần.

**Log source:** Console hiển thị cùng một dòng log 3-4 lần liên tiếp.

**Diagnosis:** Python `logging` module dùng singleton pattern theo `name`. Mỗi lần `IndustryLogger.__init__()` chạy, nó thêm handler mới vào cùng logger instance đã có sẵn.

**Solution:**

```python
def __init__(self, name="AI-Lab-Agent", log_dir="logs"):
    self.logger = logging.getLogger(name)
    # Kiểm tra trước khi addHandler
    if not self.logger.handlers:  # ← Thêm guard này
        file_handler = logging.FileHandler(...)
        console_handler = logging.StreamHandler()
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
```

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Reasoning — Sức mạnh của khối `Thought`

Sự khác biệt lớn nhất giữa Chatbot và Agent là **khả năng tự giải thích lý do trước khi hành động**. Khi tôi xem trace của Agent, mỗi bước `Thought` cho thấy agent đang phân tích trạng thái hiện tại và quyết định bước tiếp theo dựa trên `Observation` vừa nhận.

Chatbot trả lời theo phản xạ — một lần generate, không có feedback loop. Agent *lý luận có vòng lặp* — mỗi Observation làm giàu thêm context để lần generate tiếp theo chính xác hơn.

### 2. Reliability — Khi nào Agent tệ hơn Chatbot?

Qua thực nghiệm, Agent **thực sự tệ hơn** Chatbot trong các trường hợp:

- **Câu hỏi đơn giản** (không cần tool): Agent vẫn cố gọi tool không cần thiết, tốn token và thời gian.
- **Khi LLM output format sai**: Parser error làm agent fail hoàn toàn, trong khi chatbot vẫn trả về câu trả lời (dù không chính xác).
- **Latency nhạy cảm**: Mỗi vòng ReAct thêm ~1-2 giây, với bài toán cần 4 bước → latency ~6-8 giây.

### 3. Observation — Feedback loop là trái tim của ReAct

Điều tôi nhận ra khi thiết kế UI là: **Observation là thứ quyết định chất lượng của bước tiếp theo**. Nếu Observation quá ngắn ("OK"), agent không có đủ thông tin để suy luận. Nếu Observation quá dài, agent bị "overwhelm" và có thể ignore thông tin quan trọng.

Khi thiết kế phần hiển thị trace, tôi cố tình làm Observation nổi bật nhất (màu xanh, border rõ ràng) để người dùng và developer dễ debug chất lượng của feedback loop.

---

## IV. Future Improvements (5 Points)

### Scalability

- **Async tool execution**: Hiện tại agent gọi tool tuần tự. Nên dùng `asyncio` để gọi các tool độc lập song song (ví dụ: `search_available_slots` và `estimate_wait_time` có thể chạy cùng lúc).
- **LangGraph integration**: Thay ReAct loop thủ công bằng LangGraph để hỗ trợ branching phức tạp hơn (ví dụ: multi-agent với coordinator).

### Safety

- **Supervisor LLM**: Thêm một LLM phụ audit action của agent trước khi thực thi. Đặc biệt quan trọng với `book_appointment()` — không muốn agent tự đặt lịch mà không có xác nhận của người dùng.
- **Input sanitization**: Validate và sanitize tool arguments trước khi truyền vào database query để tránh SQL injection.

### Performance

- **Streaming UI**: Hiển thị từng token của `Thought` real-time thay vì chờ toàn bộ step hoàn thành. Giảm perceived latency đáng kể.
- **Prompt caching**: Cache system prompt (tool list) ở LLM provider level để giảm prompt tokens cho mỗi bước.
- **Semantic tool retrieval**: Khi có >10 tools, dùng vector embedding để retrieve top-k tools phù hợp thay vì đưa toàn bộ vào prompt.

---

> [!NOTE]
> Submit report này bằng cách đổi tên thành `REPORT_[TEN_BAN].md` và đặt trong thư mục `report/individual_reports/`.
