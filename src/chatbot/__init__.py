"""
src/chatbot/__init__.py
Người 2 — Local LLM Provider + Chatbot Baseline

Package chatbot: Export chatbot class để import dễ dàng.
"""

from src.chatbot.baseline_chatbot import BaselineChatbot, create_baseline_chatbot, CHATBOT_SYSTEM_PROMPT

__all__ = [
    "BaselineChatbot",
    "create_baseline_chatbot",
    "CHATBOT_SYSTEM_PROMPT",
]
