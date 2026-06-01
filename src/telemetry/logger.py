"""
src/telemetry/logger.py
Người 5 — UI/UX + Monitoring Dashboard + Evaluation
Nâng cấp IndustryLogger: hỗ trợ log JSON chuẩn industry với trace, run_id và error_code.
"""

import logging
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class IndustryLogger:
    """
    Structured logger mô phỏng industry practices.
    - Ghi log JSON theo từng run ra file riêng biệt trong logs/chatbot/ hoặc logs/agent/.
    - Hỗ trợ trace Thought/Action/Observation.
    - Hỗ trợ error_code, fallback_used, token estimate.
    """

    def __init__(self, name: str = "AI-Lab-Agent", log_dir: str = "logs"):
        self.log_dir = log_dir
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter("%(message)s")
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    # ─────────────────────────────────────────────
    # Core event logger
    # ─────────────────────────────────────────────
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Logs một event có timestamp và type."""
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "data": data,
        }
        self.logger.info(json.dumps(payload, ensure_ascii=False))

    def info(self, msg: str):
        self.logger.info(msg)

    def error(self, msg: str, exc_info=False):
        self.logger.error(msg, exc_info=exc_info)

    # ─────────────────────────────────────────────
    # Run-level JSON logger (ghi file riêng theo version)
    # ─────────────────────────────────────────────
    def save_run_log(
        self,
        version: str,
        user_query: str,
        start_time: str,
        end_time: str,
        latency_seconds: float,
        loop_count: int,
        tools_called: List[str],
        final_status: str,
        error_code: Optional[str],
        fallback_used: bool,
        token_prompt_estimate: int,
        token_completion_estimate: int,
        trace: List[Dict[str, Any]],
        final_answer: str = "",
    ) -> str:
        """
        Tạo và lưu log JSON đầy đủ cho mỗi run.
        Trả về run_id để tham chiếu.
        """
        run_id = f"{version}_{uuid.uuid4().hex[:8]}"

        # Tạo sub-folder theo version
        if "chatbot" in version.lower():
            sub_dir = os.path.join(self.log_dir, "chatbot")
        else:
            sub_dir = os.path.join(self.log_dir, "agent")
        os.makedirs(sub_dir, exist_ok=True)

        log_payload = {
            "run_id": run_id,
            "version": version,
            "user_query": user_query,
            "start_time": start_time,
            "end_time": end_time,
            "latency_seconds": round(latency_seconds, 3),
            "loop_count": loop_count,
            "tools_called": tools_called,
            "final_status": final_status,
            "error_code": error_code,
            "fallback_used": fallback_used,
            "token_prompt_estimate": token_prompt_estimate,
            "token_completion_estimate": token_completion_estimate,
            "final_answer": final_answer,
            "trace": trace,
        }

        log_file = os.path.join(sub_dir, f"{run_id}.json")
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_payload, f, ensure_ascii=False, indent=2)

        self.log_event("RUN_SAVED", {"run_id": run_id, "path": log_file})
        return run_id

    def load_run_logs(self, version: str = "all") -> List[Dict[str, Any]]:
        """
        Đọc tất cả log JSON từ logs/chatbot/ và logs/agent/.
        version: 'chatbot', 'agent', hoặc 'all'
        """
        results = []
        dirs_to_scan = []

        if version in ("chatbot", "all"):
            dirs_to_scan.append(os.path.join(self.log_dir, "chatbot"))
        if version in ("agent", "all"):
            dirs_to_scan.append(os.path.join(self.log_dir, "agent"))

        for d in dirs_to_scan:
            if not os.path.isdir(d):
                continue
            for fname in os.listdir(d):
                if fname.endswith(".json"):
                    fpath = os.path.join(d, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            results.append(json.load(f))
                    except Exception as e:
                        self.error(f"Cannot read log file {fpath}: {e}")

        return results


# Global logger instance
logger = IndustryLogger()
