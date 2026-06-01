"""
src/providers/local_llm.py
Người 2 — Local LLM Provider + Chatbot Baseline

LocalLLMProvider: Chạy mô hình GGUF local qua llama-cpp-python.
Hỗ trợ:
  - Phi-3-mini-4k-instruct-q4.gguf (khuyến nghị)
  - Bất kỳ GGUF model nào tương thích với llama.cpp

Cài đặt:
    pip install llama-cpp-python>=0.2.0

Tải model:
    https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf
"""

import os
import time
import logging
from typing import Dict, Any, Optional, Generator

from src.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class LocalLLMProvider(LLMProvider):
    """
    Provider chạy mô hình GGUF local trên CPU qua llama-cpp-python.

    Features:
    - Hỗ trợ Phi-3, Llama-3, Mistral và các model GGUF khác.
    - Tự động detect số CPU thread tối ưu.
    - Ước lượng token usage từ response thực tế.
    - Hỗ trợ streaming.
    - Log latency từng request.

    Usage:
        provider = LocalLLMProvider(model_path="./models/Phi-3-mini-4k-instruct-q4.gguf")
        result = provider.generate("Xin chào, tôi muốn đặt lịch khám")
        print(result["content"])
    """

    # Phi-3 / Llama-3 chat template tokens
    SYSTEM_TOKEN_START = "<|system|>"
    SYSTEM_TOKEN_END = "<|end|>"
    USER_TOKEN_START = "<|user|>"
    USER_TOKEN_END = "<|end|>"
    ASSISTANT_TOKEN_START = "<|assistant|>"
    STOP_TOKENS = ["<|end|>", "<|user|>", "Observation:", "User:"]

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_threads: Optional[int] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        verbose: bool = False,
    ):
        """
        Khởi tạo LocalLLMProvider.

        Args:
            model_path (str): Đường dẫn tới file .gguf.
            n_ctx (int): Kích thước context window. Mặc định 4096.
            n_threads (Optional[int]): Số luồng CPU. None = tự động (dùng tất cả core).
            max_tokens (int): Số token tối đa cho response. Mặc định 1024.
            temperature (float): Temperature cho sampling. Mặc định 0.1 (deterministic hơn).
            verbose (bool): In log của llama-cpp. Mặc định False.

        Raises:
            FileNotFoundError: Nếu model_path không tồn tại.
            ImportError: Nếu llama-cpp-python chưa được cài.
            RuntimeError: Nếu không load được model.
        """
        model_name = os.path.basename(model_path)
        super().__init__(model_name=model_name)

        self.model_path = model_path
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Validate model file
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model file không tìm thấy tại: {model_path}\n"
                f"Tải model tại: https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf\n"
                f"File cần tải: Phi-3-mini-4k-instruct-q4.gguf (~2.2GB)"
            )

        # Import llama_cpp
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python chưa được cài đặt.\n"
                "Cài đặt bằng: pip install llama-cpp-python>=0.2.0\n"
                "Hoặc xem: https://github.com/abetlen/llama-cpp-python"
            )

        # Tự động xác định số thread
        if n_threads is None:
            import multiprocessing
            n_threads = max(1, multiprocessing.cpu_count() - 1)
            logger.info(f"Auto-detected {n_threads} CPU threads cho llama.cpp")

        logger.info(f"Đang load model: {model_name} | ctx={n_ctx} | threads={n_threads}")
        load_start = time.time()

        try:
            self.llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_threads=n_threads,
                verbose=verbose,
            )
        except Exception as e:
            raise RuntimeError(f"Không thể load model {model_name}: {e}")

        load_time = time.time() - load_start
        logger.info(f"Load model thành công trong {load_time:.2f}s")

    # ─────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────

    def _build_prompt(self, prompt: str, system_prompt: Optional[str]) -> str:
        """
        Xây dựng prompt theo format Phi-3 chat template.

        Format:
            <|system|>
            {system_prompt}<|end|>
            <|user|>
            {user_prompt}<|end|>
            <|assistant|>
        """
        if system_prompt:
            return (
                f"{self.SYSTEM_TOKEN_START}\n{system_prompt}{self.SYSTEM_TOKEN_END}\n"
                f"{self.USER_TOKEN_START}\n{prompt}{self.USER_TOKEN_END}\n"
                f"{self.ASSISTANT_TOKEN_START}"
            )
        else:
            return (
                f"{self.USER_TOKEN_START}\n{prompt}{self.USER_TOKEN_END}\n"
                f"{self.ASSISTANT_TOKEN_START}"
            )

    def _extract_usage(self, response: Dict) -> Dict[str, int]:
        """Trích xuất token usage từ response của llama-cpp."""
        raw_usage = response.get("usage", {})
        prompt_tokens = raw_usage.get("prompt_tokens", 0)
        completion_tokens = raw_usage.get("completion_tokens", 0)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": raw_usage.get("total_tokens", prompt_tokens + completion_tokens),
        }

    # ─────────────────────────────────────────────────────────────────
    # Core methods
    # ─────────────────────────────────────────────────────────────────

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Sinh văn bản (non-streaming).

        Args:
            prompt (str): Câu hỏi / prompt từ người dùng.
            system_prompt (Optional[str]): System instruction.

        Returns:
            Dict[str, Any]:
                - content (str): Văn bản trả về.
                - usage (Dict): prompt_tokens, completion_tokens, total_tokens.
                - latency_ms (int): Thời gian phản hồi (ms).
                - provider (str): "local".
                - model (str): Tên model file.
        """
        full_prompt = self._build_prompt(prompt, system_prompt)

        start_time = time.time()
        try:
            response = self.llm(
                full_prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stop=self.STOP_TOKENS,
                echo=False,
            )
        except Exception as e:
            logger.error(f"Lỗi sinh văn bản: {e}")
            raise RuntimeError(f"LocalLLMProvider.generate() thất bại: {e}")

        latency_ms = int((time.time() - start_time) * 1000)
        content = response["choices"][0]["text"].strip()
        usage = self._extract_usage(response)

        logger.debug(
            f"generate() | latency={latency_ms}ms | "
            f"tokens={usage['total_tokens']} | content_len={len(content)}"
        )

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "local",
            "model": self.model_name,
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        """
        Sinh văn bản theo dạng streaming.

        Args:
            prompt (str): Câu hỏi / prompt từ người dùng.
            system_prompt (Optional[str]): System instruction.

        Yields:
            str: Từng token/chunk văn bản.
        """
        full_prompt = self._build_prompt(prompt, system_prompt)

        try:
            stream = self.llm(
                full_prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stop=self.STOP_TOKENS,
                stream=True,
                echo=False,
            )

            for chunk in stream:
                token = chunk["choices"][0]["text"]
                if token:
                    yield token

        except Exception as e:
            logger.error(f"Lỗi streaming: {e}")
            yield f"\n[Lỗi streaming: {e}]"

    # ─────────────────────────────────────────────────────────────────
    # Override health_check với thông tin chi tiết hơn
    # ─────────────────────────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """Kiểm tra model có hoạt động không."""
        try:
            start = time.time()
            result = self.generate(
                "Xin chào, cho tôi biết tên bạn.",
                system_prompt="Trả lời rất ngắn gọn, tối đa 10 từ."
            )
            elapsed = int((time.time() - start) * 1000)
            return {
                "status": "ok",
                "latency_ms": elapsed,
                "model": self.model_name,
                "model_path": self.model_path,
                "provider": "LocalLLMProvider",
                "sample_response": result["content"][:100],
                "error_message": None,
            }
        except Exception as e:
            return {
                "status": "error",
                "latency_ms": -1,
                "model": self.model_name,
                "model_path": self.model_path,
                "provider": "LocalLLMProvider",
                "sample_response": None,
                "error_message": str(e),
            }


# ─────────────────────────────────────────────────────────────────
# Factory function tiện lợi
# ─────────────────────────────────────────────────────────────────

def create_local_provider(
    model_path: Optional[str] = None,
    n_ctx: int = 4096,
    max_tokens: int = 1024,
) -> LocalLLMProvider:
    """
    Tạo LocalLLMProvider từ biến môi trường hoặc path trực tiếp.

    Args:
        model_path (Optional[str]): Đường dẫn model. Nếu None, đọc từ LOCAL_MODEL_PATH.
        n_ctx (int): Context window size.
        max_tokens (int): Max tokens cho response.

    Returns:
        LocalLLMProvider instance.

    Example:
        provider = create_local_provider()
        result = provider.generate("Tôi muốn đặt lịch khám Tim mạch")
    """
    if model_path is None:
        from dotenv import load_dotenv
        load_dotenv()
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")

    return LocalLLMProvider(model_path=model_path, n_ctx=n_ctx, max_tokens=max_tokens)
