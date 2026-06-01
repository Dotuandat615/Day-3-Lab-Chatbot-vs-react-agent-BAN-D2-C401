# Hướng dẫn Setup Local Model

**Người 2 — Local LLM Provider + Chatbot Baseline**

Tài liệu này hướng dẫn từng bước để cài đặt và chạy mô hình ngôn ngữ local (Phi-3) trên CPU mà không cần GPU hay API key.

---

## 1. Tổng quan

Dự án hỗ trợ chạy mô hình local thông qua **llama-cpp-python** — thư viện Python binding cho llama.cpp.

| Thông số | Giá trị |
|---|---|
| Model khuyến nghị | Phi-3-mini-4k-instruct-q4.gguf |
| Kích thước | ~2.2 GB |
| Định dạng | GGUF (quantized) |
| CPU tối thiểu | 4 core, 8 GB RAM |
| CPU khuyến nghị | 8 core, 16 GB RAM |
| Thời gian load | 5–15 giây |
| Thời gian generate | 5–30 giây/response (tùy CPU) |

---

## 2. Cài đặt Dependencies

### 2.1. Môi trường ảo (khuyến nghị)

```bash
# Tạo virtual environment
python -m venv .venv

# Kích hoạt (Windows)
.venv\Scripts\activate

# Kích hoạt (macOS/Linux)
source .venv/bin/activate
```

### 2.2. Cài thư viện

```bash
pip install -r requirements.txt
```

File `requirements.txt` đã có sẵn:

```
openai>=1.0.0
google-generativeai>=0.5.0
python-dotenv>=1.0.0
pydantic>=2.0.0
requests>=2.31.0
pytest>=7.4.0
llama-cpp-python>=0.2.0
streamlit>=1.28.0
pandas>=2.0.0
```

> [!NOTE]
> `llama-cpp-python` có thể mất 5–10 phút để compile trên lần cài đầu tiên. Đây là bình thường.

### 2.3. Cài llama-cpp-python riêng (nếu gặp lỗi)

```bash
# Cài bản pre-built (nhanh hơn)
pip install llama-cpp-python --prefer-binary

# Hoặc build từ source với số thread cụ thể
CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python
```

---

## 3. Tải Model

### 3.1. Tải từ Hugging Face

**Phi-3-mini-4k-instruct-q4.gguf** (~2.2 GB):

```
https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf
```

#### Cách 1: Tải thủ công

1. Mở link trên trong trình duyệt
2. Đợi tải xong (có thể mất 10–30 phút tùy mạng)
3. Chuyển file vào thư mục `models/`

#### Cách 2: Dùng wget / curl

```bash
# Linux/macOS
wget -O models/Phi-3-mini-4k-instruct-q4.gguf \
  https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf

# Windows PowerShell
Invoke-WebRequest -Uri "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf" -OutFile "models/Phi-3-mini-4k-instruct-q4.gguf"
```

#### Cách 3: Dùng huggingface_hub

```bash
pip install huggingface_hub
python -c "
from huggingface_hub import hf_hub_download
path = hf_hub_download(
    repo_id='microsoft/Phi-3-mini-4k-instruct-gguf',
    filename='Phi-3-mini-4k-instruct-q4.gguf',
    local_dir='./models'
)
print(f'Model tải về tại: {path}')
"
```

### 3.2. Kiểm tra file

```bash
# Kiểm tra file tồn tại và đúng kích thước (~2.2 GB)
ls -lh models/
# Expected: -rw-r--r-- 1 user group 2.2G Phi-3-mini-4k-instruct-q4.gguf

# Windows PowerShell
Get-Item models\Phi-3-mini-4k-instruct-q4.gguf | Select-Object Name, Length
```

---

## 4. Cấu hình .env

Mở file `.env` và cập nhật:

```env
# Chọn provider local
DEFAULT_PROVIDER=local

# Đường dẫn tới model file
LOCAL_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf

# Model name (để hiển thị trong UI)
DEFAULT_MODEL=Phi-3-mini-4k-instruct-q4

# Log level
LOG_LEVEL=INFO
```

> [!IMPORTANT]
> `LOCAL_MODEL_PATH` phải trỏ đúng tới file `.gguf`. Dùng đường dẫn tương đối từ thư mục gốc project.

---

## 5. Kiểm tra hoạt động

### 5.1. Test provider trực tiếp

```bash
python -c "
from src.providers.local_llm import LocalLLMProvider
provider = LocalLLMProvider('./models/Phi-3-mini-4k-instruct-q4.gguf')
result = provider.health_check()
print(result)
"
```

Kết quả mong đợi:
```json
{
  "status": "ok",
  "latency_ms": 8500,
  "model": "Phi-3-mini-4k-instruct-q4.gguf",
  "provider": "LocalLLMProvider",
  "sample_response": "Xin chào! Tôi là Phi, một trợ lý AI..."
}
```

### 5.2. Test chatbot baseline

```bash
# Interactive mode
python src/chatbot/baseline_chatbot.py --provider local

# Single query
python src/chatbot/baseline_chatbot.py --provider local --query "Tôi muốn đặt lịch khám Tim mạch"
```

### 5.3. Chạy Streamlit UI

```bash
streamlit run app.py
```

Trong UI:
1. Chọn mode **💬 Chatbot Baseline**
2. Gõ câu hỏi và nhấn Enter

---

## 6. Kiến trúc Provider

```
src/providers/
├── base.py          # Abstract base class LLMProvider
├── local_llm.py     # LocalLLMProvider (llama-cpp-python)
└── __init__.py

src/core/
├── llm_provider.py  # Base class gốc (tương thích ngược)
├── local_provider.py  # LocalProvider (alias, tương thích ngược)
├── openai_provider.py
└── gemini_provider.py
```

### Sơ đồ provider

```
LLMProvider (abstract base)
├── LocalLLMProvider   ← Người 2 implement
│     └── llama-cpp-python → Phi-3 GGUF
├── OpenAIProvider
│     └── openai SDK → gpt-4o
└── GeminiProvider
      └── google-generativeai → gemini-1.5-flash
```

### Interface thống nhất

```python
from src.providers.local_llm import LocalLLMProvider

provider = LocalLLMProvider("./models/Phi-3-mini-4k-instruct-q4.gguf")

# Non-streaming
result = provider.generate("Tôi muốn đặt lịch khám")
print(result["content"])     # Văn bản trả về
print(result["latency_ms"])  # Thời gian ms
print(result["usage"])       # Token usage

# Streaming
for token in provider.stream("Bệnh viện làm việc mấy giờ?"):
    print(token, end="", flush=True)
```

---

## 7. Tham số cấu hình LocalLLMProvider

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `model_path` | *(bắt buộc)* | Đường dẫn file .gguf |
| `n_ctx` | `4096` | Context window (số token tối đa) |
| `n_threads` | `auto` | Số CPU thread (auto = tất cả core - 1) |
| `max_tokens` | `1024` | Số token tối đa trong response |
| `temperature` | `0.1` | Nhiệt độ sampling (0.0 = deterministic) |
| `verbose` | `False` | In log nội bộ của llama.cpp |

```python
# Cấu hình tùy chỉnh
provider = LocalLLMProvider(
    model_path="./models/Phi-3-mini-4k-instruct-q4.gguf",
    n_ctx=4096,      # Context window
    n_threads=8,     # Số CPU threads (tùy máy)
    max_tokens=512,  # Giới hạn response ngắn hơn để nhanh hơn
    temperature=0.1, # Ít random, trả lời chính xác hơn
)
```

---

## 8. Chatbot Baseline

### 8.1. Mục đích

Chatbot baseline được thiết kế để **chứng minh giới hạn** của LLM thuần:

| Khả năng | Chatbot | ReAct Agent |
|---|---|---|
| Trả lời câu hỏi chung | ✅ | ✅ |
| Gợi ý chuyên khoa | ⚠️ (dự đoán) | ✅ (từ DB) |
| Kiểm tra slot trống | ❌ | ✅ |
| Giá dịch vụ chính xác | ❌ | ✅ |
| Đặt lịch thực tế | ❌ | ✅ |
| Kiểm tra BHYT | ❌ | ✅ |
| Xử lý emergency | ⚠️ (chung chung) | ✅ (guardrail) |

### 8.2. Sử dụng trong code

```python
from src.chatbot.baseline_chatbot import BaselineChatbot, create_baseline_chatbot
from src.providers.local_llm import LocalLLMProvider

# Cách 1: Factory function (khuyến nghị)
chatbot = create_baseline_chatbot(provider="local", log_dir="logs/chatbot")

# Cách 2: Khởi tạo thủ công
provider = LocalLLMProvider("./models/Phi-3-mini-4k-instruct-q4.gguf")
chatbot = BaselineChatbot(llm=provider, log_dir="logs/chatbot")

# Single turn
result = chatbot.chat("Tôi muốn đặt lịch khám Tim mạch")
print(result["answer"])
print(f"Latency: {result['latency']:.2f}s")
print(f"Tokens: {result['token_prompt_estimate'] + result['token_completion_estimate']}")

# Multi-turn với lịch sử
history = []
result1 = chatbot.chat_with_history("Tôi muốn khám Tim mạch", history=history)
history.extend([
    {"role": "user", "content": "Tôi muốn khám Tim mạch"},
    {"role": "assistant", "content": result1["answer"]},
])
result2 = chatbot.chat_with_history("Có bác sĩ nữ không?", history=history)
```

### 8.3. Log format

Mỗi request tạo ra một file log JSON trong `logs/chatbot/`:

```json
{
  "run_id": "chatbot_20260601_103000_a1b2c3d4",
  "version": "chatbot",
  "user_query": "Tôi muốn đặt lịch khám Tim mạch",
  "start_time": "2026-06-01T10:30:00.000000",
  "end_time": "2026-06-01T10:30:08.500000",
  "latency": 8.5,
  "answer": "Để đặt lịch khám Tim mạch...",
  "token_prompt_estimate": 185,
  "token_completion_estimate": 120,
  "final_status": "success",
  "error_code": null,
  "fallback_used": false,
  "trace": [],
  "tools_called": [],
  "loop_count": 0
}
```

---

## 9. Chạy Test Cases

```bash
# Chạy toàn bộ test cases với chatbot
python src/chatbot/baseline_chatbot.py \
  --provider local \
  --test-cases tests/test_cases.json \
  --log-dir logs/chatbot
```

Kết quả được lưu trong `logs/chatbot/batch_summary_YYYYMMDD_HHMMSS.json`.

---

## 10. Xử lý sự cố

### Lỗi: `FileNotFoundError: Model file không tìm thấy`

```bash
# Kiểm tra đường dẫn
ls models/
# Phải có: Phi-3-mini-4k-instruct-q4.gguf

# Kiểm tra .env
cat .env | grep LOCAL_MODEL_PATH
```

### Lỗi: `ImportError: llama-cpp-python chưa được cài`

```bash
pip install llama-cpp-python --prefer-binary
```

### Lỗi: Build fails khi cài llama-cpp-python

```bash
# Windows: Cần Visual C++ Build Tools
# Tải từ: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Sau đó thử lại:
pip install llama-cpp-python --prefer-binary
```

### Model chạy quá chậm

```python
# Giảm context window
provider = LocalLLMProvider(
    model_path="./models/Phi-3-mini-4k-instruct-q4.gguf",
    n_ctx=2048,      # Giảm từ 4096
    max_tokens=512,  # Giảm response length
    n_threads=None,  # Dùng tất cả CPU thread
)
```

### Lỗi RAM không đủ

Model cần ít nhất 4 GB RAM để chạy. Nếu máy yếu:
- Giảm `n_ctx=2048`
- Đóng các ứng dụng khác
- Hoặc dùng provider API (openai/gemini) thay thế

---

## 11. Chuyển sang provider khác

Nếu không muốn dùng local model, có thể chuyển sang OpenAI hoặc Gemini:

```env
# Dùng OpenAI
DEFAULT_PROVIDER=openai
OPENAI_API_KEY=sk-...
DEFAULT_MODEL=gpt-4o-mini

# Hoặc Gemini
DEFAULT_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-flash
```

Code chatbot sẽ tự động dùng provider tương ứng mà không cần sửa code.

---

*Tài liệu này viết bởi Người 2 — Local LLM Provider + Chatbot Baseline.*
