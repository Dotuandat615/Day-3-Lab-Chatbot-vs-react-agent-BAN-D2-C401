"""
src/telemetry/metrics.py
Người 5 — UI/UX + Monitoring Dashboard + Evaluation
Nâng cấp PerformanceTracker: tính đầy đủ các industry metrics từ log files.
"""

import time
from typing import Dict, Any, List, Optional
from src.telemetry.logger import logger


class PerformanceTracker:
    """
    Tracking industry-standard metrics cho LLM và ReAct Agent.

    Metrics được theo dõi:
    - Latency (ms)
    - Token usage (prompt / completion / total)
    - Cost estimate
    - Loop count (chỉ cho agent)
    - Parser error rate
    - Hallucination rate
    - Timeout rate
    - Fallback rate
    - Success rate
    """

    def __init__(self):
        self.session_metrics: List[Dict[str, Any]] = []

    # ─────────────────────────────────────────────
    # Track một request LLM đơn lẻ
    # ─────────────────────────────────────────────
    def track_request(
        self,
        provider: str,
        model: str,
        usage: Dict[str, int],
        latency_ms: int,
        version: str = "unknown",
        loop_count: int = 0,
        error_code: Optional[str] = None,
        fallback_used: bool = False,
    ):
        """
        Logs một request metric vào telemetry.
        """
        metric = {
            "provider": provider,
            "model": model,
            "version": version,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "loop_count": loop_count,
            "error_code": error_code,
            "fallback_used": fallback_used,
            "cost_estimate_usd": self._calculate_cost(model, usage),
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """
        Ước lượng chi phí dựa trên model name.
        Giá tham khảo (USD per 1K tokens):
        - GPT-4o: 0.005 prompt / 0.015 completion
        - Gemini Flash: 0.00035 / 0.00105
        - Local model: free (0)
        """
        total_tokens = usage.get("total_tokens", 0)
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        pricing = {
            "gpt-4o": (0.005, 0.015),
            "gpt-4o-mini": (0.00015, 0.0006),
            "gemini-1.5-flash": (0.00035, 0.00105),
            "gemini-1.5-pro": (0.00125, 0.005),
        }

        for key, (p_price, c_price) in pricing.items():
            if key in model.lower():
                cost = (prompt_tokens / 1000 * p_price) + (completion_tokens / 1000 * c_price)
                return round(cost, 6)

        # Local / unknown model
        return 0.0

    # ─────────────────────────────────────────────
    # Tính aggregate metrics từ danh sách log runs
    # ─────────────────────────────────────────────
    def compute_aggregate(self, runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Tính các aggregate metrics từ danh sách run logs (output của logger.load_run_logs).
        Dùng để tạo bảng so sánh Chatbot vs Agent v1 vs Agent v2.

        Args:
            runs: List of run log dicts (đọc từ logs/*.json)

        Returns:
            Dict chứa các metrics đã tính.
        """
        if not runs:
            return {}

        n = len(runs)
        latencies = [r.get("latency_seconds", 0) for r in runs]
        loop_counts = [r.get("loop_count", 0) for r in runs]

        success_count = sum(1 for r in runs if r.get("final_status") == "success")
        fallback_count = sum(1 for r in runs if r.get("fallback_used", False))
        parser_error_count = sum(
            1 for r in runs if r.get("error_code") in ("PARSER_ERROR",)
        )
        timeout_count = sum(1 for r in runs if r.get("error_code") == "TIMEOUT")
        hallucination_count = sum(
            1 for r in runs if r.get("error_code") == "HALLUCINATED_TOOL"
        )

        prompt_tokens = [r.get("token_prompt_estimate", 0) for r in runs]
        completion_tokens = [r.get("token_completion_estimate", 0) for r in runs]

        return {
            "n_runs": n,
            "success_rate": round(success_count / n * 100, 1),
            "avg_latency_s": round(sum(latencies) / n, 2),
            "max_latency_s": round(max(latencies), 2),
            "avg_loop_count": round(sum(loop_counts) / n, 1),
            "parser_error_rate": round(parser_error_count / n * 100, 1),
            "timeout_rate": round(timeout_count / n * 100, 1),
            "hallucination_rate": round(hallucination_count / n * 100, 1),
            "fallback_rate": round(fallback_count / n * 100, 1),
            "avg_prompt_tokens": round(sum(prompt_tokens) / n, 0),
            "avg_completion_tokens": round(sum(completion_tokens) / n, 0),
        }

    def print_summary(self):
        """In tóm tắt metrics của session hiện tại."""
        if not self.session_metrics:
            print("No metrics recorded yet.")
            return

        print("\n" + "=" * 60)
        print("📊 SESSION METRICS SUMMARY")
        print("=" * 60)
        print(f"Total requests:    {len(self.session_metrics)}")
        latencies = [m["latency_ms"] for m in self.session_metrics]
        tokens = [m["total_tokens"] for m in self.session_metrics]
        costs = [m["cost_estimate_usd"] for m in self.session_metrics]

        print(f"Avg latency:       {sum(latencies)/len(latencies):.0f} ms")
        print(f"Max latency:       {max(latencies)} ms")
        print(f"Avg tokens/req:    {sum(tokens)/len(tokens):.0f}")
        print(f"Total cost (est):  ${sum(costs):.4f}")
        print("=" * 60 + "\n")


# Global tracker instance
tracker = PerformanceTracker()
