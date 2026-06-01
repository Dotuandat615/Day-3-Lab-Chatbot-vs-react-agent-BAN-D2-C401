"""
src/providers/__init__.py
Người 2 — Local LLM Provider + Chatbot Baseline

Package providers: Export các provider class để import dễ dàng.
"""

from src.providers.base import LLMProvider
from src.providers.local_llm import LocalLLMProvider, create_local_provider

__all__ = [
    "LLMProvider",
    "LocalLLMProvider",
    "create_local_provider",
]
