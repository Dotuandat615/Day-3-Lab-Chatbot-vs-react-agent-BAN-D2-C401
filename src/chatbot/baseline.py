import json
from pathlib import Path
from datetime import datetime

from src.core.local_provider import LocalProvider


class BaselineChatbot:
    """
    Chatbot Baseline

    - Không gọi tool
    - Không truy cập database
    - Chỉ sử dụng LLM trả lời trực tiếp
    - Ghi log latency và token usage
    """

    SYSTEM_PROMPT = """
Bạn là AI Trợ Lý Đặt Lịch Khám.

Quy tắc:
- Trả lời bằng tiếng Việt.
- Lịch sự, rõ ràng.
- Không được tự tạo lịch khám.
- Không được tự tạo bác sĩ.
- Không được tự tạo thời gian chờ.
- Không được giả vờ truy cập được cơ sở dữ liệu bệnh viện.
- Nếu người dùng hỏi lịch khám cụ thể, hãy nói rằng bạn không thể kiểm tra lịch thực tế ở chế độ chatbot.
"""

    def __init__(self, provider: LocalProvider):
        self.provider = provider

        Path("logs/chatbot").mkdir(
            parents=True,
            exist_ok=True
        )

    def chat(self, user_input: str) -> dict:
        """
        Generate chatbot response.
        """

        result = self.provider.generate(
            prompt=user_input,
            system_prompt=self.SYSTEM_PROMPT
        )

        self._save_log(
            user_input=user_input,
            result=result
        )

        return result

    def _save_log(
        self,
        user_input: str,
        result: dict
    ) -> None:

        log_data = {
            "timestamp": datetime.now().isoformat(),
            "mode": "chatbot_baseline",
            "query": user_input,
            "response": result["content"],
            "latency_ms": result["latency_ms"],
            "provider": result["provider"],
            "prompt_tokens": result["usage"]["prompt_tokens"],
            "completion_tokens": result["usage"]["completion_tokens"],
            "total_tokens": result["usage"]["total_tokens"]
        }

        with open(
            "logs/chatbot/chatbot_logs.jsonl",
            "a",
            encoding="utf-8"
        ) as f:
            f.write(
                json.dumps(
                    log_data,
                    ensure_ascii=False
                )
                + "\n"
            )