"""
src/providers/base.py
Người 2 — Local LLM Provider + Chatbot Baseline

Abstract base class định nghĩa interface thống nhất cho tất cả LLM providers.
Hỗ trợ: OpenAI, Gemini, Local (llama-cpp-python / Ollama).
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Generator, List


class LLMProvider(ABC):
    """
    Abstract Base Class cho tất cả LLM Providers.

    Mọi provider (OpenAI, Gemini, Local) phải kế thừa class này
    và implement các phương thức abstract bên dưới.

    Attributes:
        model_name (str): Tên model đang dùng (e.g. "gpt-4o", "gemini-1.5-flash", "Phi-3-mini-4k-instruct-q4.gguf").
        api_key (Optional[str]): API key nếu cần (None với local model).
    """

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key

    # ─────────────────────────────────────────────────────────────────
    # Core methods (phải implement)
    # ─────────────────────────────────────────────────────────────────

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Sinh văn bản (non-streaming).

        Args:
            prompt (str): Prompt người dùng.
            system_prompt (Optional[str]): System instruction.

        Returns:
            Dict[str, Any] chứa:
                - content (str): Văn bản trả về.
                - usage (Dict):
                    - prompt_tokens (int)
                    - completion_tokens (int)
                    - total_tokens (int)
                - latency_ms (int): Thời gian phản hồi tính bằng ms.
                - provider (str): Tên provider (e.g. "local", "openai", "gemini").
        """
        pass

    @abstractmethod
    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        """
        Sinh văn bản theo dạng streaming (từng token một).

        Args:
            prompt (str): Prompt người dùng.
            system_prompt (Optional[str]): System instruction.

        Yields:
            str: Từng token/chunk văn bản.
        """
        pass

    # ─────────────────────────────────────────────────────────────────
    # Utility methods (có thể override)
    # ─────────────────────────────────────────────────────────────────

    def estimate_tokens(self, text: str) -> int:
        """
        Ước lượng số token từ văn bản.
        Công thức gần đúng: 1 token ≈ 4 ký tự (English).
        Với tiếng Việt, 1 token ≈ 2.5 ký tự.

        Args:
            text (str): Văn bản cần ước lượng.

        Returns:
            int: Số token ước lượng.
        """
        if not text:
            return 0
        # Ước lượng đơn giản: trung bình 3.5 ký tự/token (hỗn hợp Anh/Việt)
        return max(1, int(len(text) / 3.5))

    def get_provider_name(self) -> str:
        """Trả về tên provider (class name)."""
        return self.__class__.__name__

    def health_check(self) -> Dict[str, Any]:
        """
        Kiểm tra provider có hoạt động không bằng cách gửi prompt thử.

        Returns:
            Dict với keys: status ("ok" | "error"), latency_ms, error_message.
        """
        try:
            start = time.time()
            result = self.generate("Xin chào", system_prompt="Trả lời ngắn gọn.")
            elapsed = int((time.time() - start) * 1000)
            return {
                "status": "ok",
                "latency_ms": elapsed,
                "model": self.model_name,
                "provider": self.get_provider_name(),
                "error_message": None,
            }
        except Exception as e:
            return {
                "status": "error",
                "latency_ms": -1,
                "model": self.model_name,
                "provider": self.get_provider_name(),
                "error_message": str(e),
            }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name})"
