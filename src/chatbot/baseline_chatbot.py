"""
src/chatbot/baseline_chatbot.py
Người 2 — Local LLM Provider + Chatbot Baseline

ChatBot Baseline: Trả lời trực tiếp từ LLM, KHÔNG gọi tool, KHÔNG truy vấn dữ liệu.

Mục đích:
  - Demo giới hạn của chatbot thuần (hallucination, câu trả lời chung chung).
  - So sánh với ReAct Agent (v1 và v2) để thấy rõ sự khác biệt.

Flow:
  User query → System prompt + Context → LLM.generate() → Log → Response
"""

import os
import time
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Type alias cho duck-typing: bất kỳ object nào có .generate() và .model_name
# Hỗ trợ cả src.providers.base.LLMProvider và src.core.llm_provider.LLMProvider
try:
    from src.providers.base import LLMProvider as _ProviderBase
except ImportError:
    from src.core.llm_provider import LLMProvider as _ProviderBase  # type: ignore

# ─────────────────────────────────────────────────────────────────
# System prompt mặc định cho chatbot baseline
# ─────────────────────────────────────────────────────────────────

CHATBOT_SYSTEM_PROMPT = """Bạn là trợ lý tư vấn đặt lịch khám bệnh của VinCare Demo Hospital.

Nhiệm vụ của bạn:
- Tư vấn thông tin về việc đặt lịch khám bệnh.
- Hướng dẫn bệnh nhân về các chuyên khoa và dịch vụ.
- Trả lời câu hỏi về giờ làm việc, thủ tục, thanh toán.

Quy tắc QUAN TRỌNG:
1. Bạn KHÔNG có khả năng kiểm tra lịch trống thực tế trong hệ thống.
2. Bạn KHÔNG được tự bịa đặt thông tin về bác sĩ, giá, hoặc slot cụ thể.
3. Nếu được hỏi về slot cụ thể, hãy nói rõ bạn không thể kiểm tra và hướng dẫn liên hệ.
4. Luôn thân thiện, ngắn gọn và hữu ích trong phạm vi kiến thức của bạn.
5. Nếu triệu chứng có vẻ khẩn cấp, hướng dẫn gọi cấp cứu hoặc hotline.

Thông tin bệnh viện:
- Tên: VinCare Demo Hospital
- Hotline: 1900-xxxx
- Giờ làm việc: 7:00 - 17:00 (Thứ 2 - Thứ 7)
- Các chuyên khoa: Tim mạch, Da liễu, Nhi khoa, Nội khoa, Thần kinh, Chỉnh hình, Mắt, Tai Mũi Họng, Răng Hàm Mặt, Sản phụ khoa, Tiêu hóa, Hô hấp.

Hãy trả lời bằng tiếng Việt, thân thiện và chuyên nghiệp."""


# ─────────────────────────────────────────────────────────────────
# Main ChatBot class
# ─────────────────────────────────────────────────────────────────

class BaselineChatbot:
    """
    Chatbot Baseline: Trả lời trực tiếp từ LLM.

    Đây là baseline để so sánh với ReAct Agent. Chatbot này:
    ✅ Trả lời câu hỏi chung về đặt lịch
    ✅ Tư vấn chuyên khoa theo mô tả triệu chứng cơ bản
    ✅ Log latency và token estimate
    ❌ KHÔNG truy vấn database thực tế
    ❌ KHÔNG kiểm tra slot trống
    ❌ KHÔNG gọi tool
    ❌ Dễ hallucinate thông tin cụ thể

    Attributes:
        llm (LLMProvider): LLM provider (local, OpenAI, Gemini).
        log_dir (str): Thư mục lưu log.
        system_prompt (str): System instruction cho chatbot.
    """

    def __init__(
        self,
        llm: Any,
        log_dir: str = "logs/chatbot",
        system_prompt: Optional[str] = None,
    ):
        """
        Khởi tạo BaselineChatbot.

        Args:
            llm (LLMProvider): LLM provider instance.
            log_dir (str): Thư mục lưu log JSON.
            system_prompt (Optional[str]): Override system prompt mặc định.
        """
        self.llm = llm
        self.log_dir = log_dir
        self.system_prompt = system_prompt or CHATBOT_SYSTEM_PROMPT

        # Tạo thư mục log nếu chưa có
        os.makedirs(log_dir, exist_ok=True)
        logger.info(f"BaselineChatbot khởi tạo | provider={llm.model_name} | log_dir={log_dir}")

    def _estimate_tokens(self, text: str) -> int:
        """Ước lượng số token. Dùng method của provider nếu có, fallback sang tính thủ công."""
        if hasattr(self.llm, "estimate_tokens"):
            return self.llm.estimate_tokens(text)
        # Fallback: 1 token ≈ 3.5 ký tự (hỗn hợp Anh/Việt)
        return max(1, int(len(text) / 3.5))

    # ─────────────────────────────────────────────────────────────────
    # Core: chat()
    # ─────────────────────────────────────────────────────────────────

    def chat(self, user_query: str) -> Dict[str, Any]:
        """
        Xử lý câu hỏi của người dùng và trả về kết quả.

        Args:
            user_query (str): Câu hỏi / yêu cầu từ người dùng.

        Returns:
            Dict[str, Any]:
                - answer (str): Câu trả lời từ LLM.
                - version (str): "chatbot"
                - user_query (str): Câu hỏi gốc.
                - start_time (str): ISO format timestamp bắt đầu.
                - end_time (str): ISO format timestamp kết thúc.
                - latency (float): Thời gian xử lý (giây).
                - token_prompt_estimate (int): Ước lượng token prompt.
                - token_completion_estimate (int): Ước lượng token response.
                - final_status (str): "success" | "error"
                - error_code (Optional[str]): Mã lỗi nếu có.
                - fallback_used (bool): Luôn False với chatbot baseline.
                - trace (list): Luôn [] với chatbot baseline.
                - tools_called (list): Luôn [] với chatbot baseline.
                - loop_count (int): Luôn 0 với chatbot baseline.
                - run_id (str): ID duy nhất của run này.
        """
        run_id = f"chatbot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        start_time = datetime.utcnow().isoformat()
        wall_start = time.time()

        logger.info(f"[{run_id}] Chatbot nhận query: {user_query[:80]}...")

        result = {
            "run_id": run_id,
            "version": "chatbot",
            "user_query": user_query,
            "start_time": start_time,
            "end_time": "",
            "latency": 0.0,
            "answer": "",
            "token_prompt_estimate": 0,
            "token_completion_estimate": 0,
            "final_status": "success",
            "error_code": None,
            "fallback_used": False,
            "trace": [],
            "tools_called": [],
            "loop_count": 0,
        }

        try:
            # Gọi LLM
            llm_result = self.llm.generate(
                prompt=user_query,
                system_prompt=self.system_prompt,
            )

            latency = time.time() - wall_start
            end_time = datetime.utcnow().isoformat()

            # Lấy usage
            usage = llm_result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", self._estimate_tokens(user_query))
            completion_tokens = usage.get("completion_tokens", self._estimate_tokens(llm_result.get("content", "")))

            # Điền kết quả
            result.update({
                "answer": llm_result.get("content", ""),
                "end_time": end_time,
                "latency": round(latency, 3),
                "token_prompt_estimate": prompt_tokens,
                "token_completion_estimate": completion_tokens,
                "final_status": "success",
            })

            logger.info(
                f"[{run_id}] Chatbot trả lời thành công | "
                f"latency={latency:.2f}s | tokens={prompt_tokens + completion_tokens}"
            )

        except Exception as e:
            latency = time.time() - wall_start
            error_msg = str(e)
            logger.error(f"[{run_id}] Chatbot lỗi: {error_msg}")

            result.update({
                "answer": f"Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại hoặc liên hệ hotline 1900-xxxx để được hỗ trợ.",
                "end_time": datetime.utcnow().isoformat(),
                "latency": round(latency, 3),
                "final_status": "error",
                "error_code": "CHATBOT_ERROR",
            })

        # Lưu log
        self._save_log(result)

        return result

    # ─────────────────────────────────────────────────────────────────
    # Multi-turn: chat_with_history()
    # ─────────────────────────────────────────────────────────────────

    def chat_with_history(
        self,
        user_query: str,
        history: Optional[List[Dict[str, str]]] = None,
        max_history_turns: int = 5,
    ) -> Dict[str, Any]:
        """
        Chat với lịch sử hội thoại (multi-turn).

        Args:
            user_query (str): Câu hỏi mới nhất.
            history (Optional[List]): Lịch sử chat [{role, content}].
            max_history_turns (int): Số lượt chat tối đa đưa vào context.

        Returns:
            Dict tương tự chat(), kèm trường "history_used" (int).
        """
        if history is None:
            history = []

        # Giới hạn context để tránh tràn
        recent_history = history[-max_history_turns * 2:] if history else []

        # Build context từ lịch sử
        context_parts = []
        for turn in recent_history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role == "user":
                context_parts.append(f"Người dùng: {content}")
            else:
                context_parts.append(f"Trợ lý: {content}")

        if context_parts:
            context = "\n".join(context_parts)
            enriched_query = f"Lịch sử hội thoại:\n{context}\n\nCâu hỏi mới: {user_query}"
        else:
            enriched_query = user_query

        result = self.chat(enriched_query)
        result["history_used"] = len(recent_history) // 2  # Số lượt
        return result

    # ─────────────────────────────────────────────────────────────────
    # Batch: run_test_cases()
    # ─────────────────────────────────────────────────────────────────

    def run_test_cases(
        self,
        test_cases: List[Dict[str, Any]],
        delay_seconds: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        Chạy chatbot trên toàn bộ test cases và log kết quả.

        Args:
            test_cases (List[Dict]): Danh sách test case [{id, query, expected_behavior}].
            delay_seconds (float): Thời gian chờ giữa các request (tránh overload CPU).

        Returns:
            List[Dict]: Danh sách kết quả từng test case.
        """
        results = []
        total = len(test_cases)
        logger.info(f"Bắt đầu chạy {total} test cases với chatbot baseline...")

        for i, tc in enumerate(test_cases, 1):
            tc_id = tc.get("id", f"TC{i:02d}")
            query = tc.get("query", "")
            expected = tc.get("expected_behavior", "")

            logger.info(f"[{i}/{total}] Test case {tc_id}: {query[:60]}...")

            result = self.chat(query)
            result["test_case_id"] = tc_id
            result["expected_behavior"] = expected

            # Đánh giá đơn giản (chatbot không có tool nên luôn không match fully)
            result["test_passed"] = result["final_status"] == "success"

            results.append(result)

            if i < total and delay_seconds > 0:
                time.sleep(delay_seconds)

        # Thống kê
        success_count = sum(1 for r in results if r["final_status"] == "success")
        avg_latency = sum(r["latency"] for r in results) / len(results) if results else 0
        avg_tokens = sum(r["token_prompt_estimate"] + r["token_completion_estimate"] for r in results) / len(results) if results else 0

        summary = {
            "total_cases": total,
            "success_count": success_count,
            "success_rate_pct": round(success_count / total * 100, 1) if total > 0 else 0,
            "avg_latency_s": round(avg_latency, 2),
            "avg_total_tokens": round(avg_tokens, 0),
        }

        logger.info(f"Kết quả chatbot: {summary}")

        # Lưu summary log
        self._save_batch_summary(results, summary)

        return results

    # ─────────────────────────────────────────────────────────────────
    # Logging
    # ─────────────────────────────────────────────────────────────────

    def _save_log(self, result: Dict[str, Any]) -> str:
        """
        Lưu một run log vào file JSON trong log_dir.

        Args:
            result (Dict): Kết quả từ chat().

        Returns:
            str: Đường dẫn file log đã lưu.
        """
        run_id = result.get("run_id", "unknown")
        filename = f"{run_id}.json"
        filepath = os.path.join(self.log_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.debug(f"Log lưu tại: {filepath}")
        except Exception as e:
            logger.warning(f"Không thể lưu log {filepath}: {e}")

        return filepath

    def _save_batch_summary(
        self,
        results: List[Dict[str, Any]],
        summary: Dict[str, Any],
    ) -> str:
        """Lưu tổng hợp kết quả batch test."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_summary_{timestamp}.json"
        filepath = os.path.join(self.log_dir, filename)

        payload = {
            "batch_run_at": datetime.utcnow().isoformat(),
            "version": "chatbot",
            "summary": summary,
            "results": results,
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info(f"Batch summary lưu tại: {filepath}")
        except Exception as e:
            logger.warning(f"Không thể lưu batch summary: {e}")

        return filepath


# ─────────────────────────────────────────────────────────────────
# Factory function
# ─────────────────────────────────────────────────────────────────

def create_baseline_chatbot(
    provider: str = "auto",
    log_dir: str = "logs/chatbot",
    system_prompt: Optional[str] = None,
) -> BaselineChatbot:
    """
    Factory function tạo BaselineChatbot tự động theo .env.

    Args:
        provider (str): "auto" | "local" | "openai" | "gemini".
                        "auto" sẽ đọc từ DEFAULT_PROVIDER trong .env.
        log_dir (str): Thư mục log.
        system_prompt (Optional[str]): Override system prompt.

    Returns:
        BaselineChatbot instance sẵn sàng dùng.

    Example:
        chatbot = create_baseline_chatbot(provider="local")
        result = chatbot.chat("Tôi muốn đặt lịch khám Tim mạch")
        print(result["answer"])
    """
    from dotenv import load_dotenv
    load_dotenv()

    if provider == "auto":
        provider = os.getenv("DEFAULT_PROVIDER", "local").lower()

    llm: LLMProvider

    if provider == "local":
        from src.providers.local_llm import LocalLLMProvider
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        llm = LocalLLMProvider(model_path=model_path)

    elif provider == "openai":
        from src.core.openai_provider import OpenAIProvider
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        llm = OpenAIProvider(model_name=model, api_key=api_key)

    elif provider == "gemini":
        from src.core.gemini_provider import GeminiProvider
        api_key = os.getenv("GEMINI_API_KEY", "")
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        llm = GeminiProvider(model_name=model, api_key=api_key)

    else:
        raise ValueError(f"Provider không hợp lệ: '{provider}'. Chọn: auto | local | openai | gemini")

    return BaselineChatbot(llm=llm, log_dir=log_dir, system_prompt=system_prompt)


# ─────────────────────────────────────────────────────────────────
# CLI (chạy trực tiếp để test)
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Chạy Chatbot Baseline")
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "local", "openai", "gemini"],
        help="LLM provider (mặc định: auto từ .env)",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Câu hỏi trực tiếp. Nếu không truyền, vào chế độ interactive.",
    )
    parser.add_argument(
        "--test-cases",
        default=None,
        help="Path tới file test_cases.json để chạy batch.",
    )
    parser.add_argument(
        "--log-dir",
        default="logs/chatbot",
        help="Thư mục lưu log (mặc định: logs/chatbot)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  AI Trợ Lý Đặt Lịch Khám — Chatbot Baseline")
    print("=" * 60)

    try:
        chatbot = create_baseline_chatbot(provider=args.provider, log_dir=args.log_dir)
        print(f"✅ Chatbot khởi tạo thành công | Provider: {chatbot.llm.model_name}")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo chatbot: {e}")
        sys.exit(1)

    # Batch test
    if args.test_cases:
        print(f"\n📋 Chạy test cases từ: {args.test_cases}")
        try:
            with open(args.test_cases, "r", encoding="utf-8") as f:
                test_cases = json.load(f)
            results = chatbot.run_test_cases(test_cases)
            print(f"\n✅ Hoàn thành {len(results)} test cases. Log lưu tại: {args.log_dir}/")
        except Exception as e:
            print(f"❌ Lỗi chạy test cases: {e}")
        sys.exit(0)

    # Single query
    if args.query:
        print(f"\n📝 Query: {args.query}")
        result = chatbot.chat(args.query)
        print(f"\n💬 Trả lời:\n{result['answer']}")
        print(f"\n📊 Metrics:")
        print(f"   Latency: {result['latency']:.2f}s")
        print(f"   Tokens (prompt/completion): {result['token_prompt_estimate']}/{result['token_completion_estimate']}")
        print(f"   Status: {result['final_status']}")
        sys.exit(0)

    # Interactive mode
    print("\n🚀 Chế độ interactive (gõ 'quit' hoặc Ctrl+C để thoát)")
    print("-" * 60)
    history = []

    while True:
        try:
            user_input = input("\nBạn: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "thoat", "q"):
                print("Tạm biệt! 👋")
                break

            result = chatbot.chat_with_history(user_input, history=history)
            print(f"\nTrợ lý: {result['answer']}")
            print(f"[Latency: {result['latency']:.2f}s | Tokens: {result['token_prompt_estimate'] + result['token_completion_estimate']}]")

            # Cập nhật history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": result["answer"]})

        except KeyboardInterrupt:
            print("\n\nTạm biệt! 👋")
            break
        except Exception as e:
            print(f"Lỗi: {e}")
