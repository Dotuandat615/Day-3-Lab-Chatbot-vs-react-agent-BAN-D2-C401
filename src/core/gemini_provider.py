import time
from typing import Dict, Any, Optional, Generator

from google import genai
from google.genai import types

from src.core.llm_provider import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(
        self,
        model_name: str = "gemini-2.5-flash-lite",
        api_key: Optional[str] = None,
    ):
        super().__init__(model_name, api_key)

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:

        start_time = time.time()

        config = None
        if system_prompt:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt
            )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        usage_metadata = getattr(response, "usage_metadata", None)

        usage = {
            "prompt_tokens": getattr(
                usage_metadata,
                "prompt_token_count",
                0,
            ),
            "completion_tokens": getattr(
                usage_metadata,
                "candidates_token_count",
                0,
            ),
            "total_tokens": getattr(
                usage_metadata,
                "total_token_count",
                0,
            ),
        }

        return {
            "content": response.text,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "google",
        }

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Generator[str, None, None]:

        config = None
        if system_prompt:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt
            )

        stream = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        for chunk in stream:
            if chunk.text:
                yield chunk.text