"""
app.py — Streamlit UI chính
Người 5 — UI/UX + Monitoring Dashboard + Evaluation

Chạy: streamlit run app.py
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, List

import streamlit as st

# Thêm root vào sys.path để import src.*
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.ui.components import (
    apply_custom_css,
    render_header,
    render_mode_selector,
    render_welcome_screen,
    render_chat_message,
    render_final_answer,
    render_trace,
    render_metrics,
    render_log_json,
    render_comparison_table,
    render_error_message,
    render_footer,
)
from src.telemetry.logger import IndustryLogger
from src.telemetry.metrics import PerformanceTracker

# ─────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Trợ Lý Đặt Lịch Khám",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_css()

# ─────────────────────────────────────────────────────────────────
# Global services
# ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_logger():
    return IndustryLogger(log_dir="logs")

@st.cache_resource
def get_tracker():
    return PerformanceTracker()

app_logger = get_logger()
tracker = get_tracker()

# ─────────────────────────────────────────────────────────────────
# LLM Provider factory (graceful fallback)
# ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_llm_provider():
    """
    Khởi tạo LLM Provider theo .env.
    Ưu tiên: gemini → openai → local (nếu có).
    Nếu thiếu key, trả về None → chạy demo mode.
    """
    from dotenv import load_dotenv
    load_dotenv()

    provider_name = os.getenv("DEFAULT_PROVIDER", "gemini").lower()

    try:
        if provider_name == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return None
            from src.core.gemini_provider import GeminiProvider
            model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            return GeminiProvider(model_name=model, api_key=api_key)

        elif provider_name == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None
            from src.core.openai_provider import OpenAIProvider
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            return OpenAIProvider(model_name=model, api_key=api_key)

        elif provider_name == "local":
            model_path = os.getenv("LOCAL_MODEL_PATH", "")
            if not model_path or not os.path.exists(model_path):
                return None
            from src.core.local_provider import LocalProvider
            return LocalProvider(model_path=model_path)

    except Exception as e:
        st.warning(f"⚠️ Không thể khởi tạo LLM provider: {e}")
        return None

    return None


# ─────────────────────────────────────────────────────────────────
# Demo stubs (khi chưa có LLM / tools thật)
# ─────────────────────────────────────────────────────────────────
DEMO_RESPONSES = {
    "chatbot": {
        "answer": "Xin chào! Tôi có thể tư vấn về lịch khám bệnh. Để đặt lịch khám Tim mạch, bạn có thể liên hệ trực tiếp với bệnh viện hoặc truy cập website của chúng tôi. Lưu ý: Tôi không có khả năng kiểm tra lịch trống thực tế.",
        "trace": [],
        "loop_count": 0,
        "tools_called": [],
        "final_status": "success",
        "error_code": None,
        "fallback_used": False,
        "token_prompt_estimate": 120,
        "token_completion_estimate": 85,
        "latency": 1.2,
    },
    "agent_v1": {
        "answer": "Hiện có lịch khám Tim mạch lúc 09:30 sáng thứ 3 tuần sau, thời gian chờ dự kiến khoảng 20 phút. Bạn có muốn xác nhận lịch này không?",
        "trace": [
            {
                "step": 1,
                "thought": "Cần kiểm tra các slot Tim mạch còn trống vào sáng thứ 3.",
                "action": "search_available_slots",
                "action_input": {"specialty": "Tim mạch", "date": "2026-06-09", "preferred_time": "morning"},
                "observation": "Tìm thấy 3 slot: 08:30 (45 phút chờ), 09:30 (20 phút chờ), 10:30 (35 phút chờ).",
            },
            {
                "step": 2,
                "thought": "Cần chọn slot có thời gian chờ thấp nhất.",
                "action": "rank_slots",
                "action_input": {"criteria": "lowest_wait_time", "slots": ["08:30", "09:30", "10:30"]},
                "observation": "Slot tốt nhất là 09:30 vì wait_time = 20 phút.",
            },
        ],
        "loop_count": 2,
        "tools_called": ["search_available_slots", "rank_slots"],
        "final_status": "success",
        "error_code": None,
        "fallback_used": False,
        "token_prompt_estimate": 450,
        "token_completion_estimate": 210,
        "latency": 5.8,
    },
    "agent_v2": {
        "answer": "Tôi đã tìm thấy slot khám Tim mạch phù hợp nhất:\n\n**Dr. Lan — 09:30, thứ 3 ngày 09/06/2026**\n⏱️ Thời gian chờ dự kiến: **20 phút**\n🏥 Phòng: 202\n\nBạn có muốn tôi xác nhận đặt lịch này không? Nếu có, vui lòng cho tôi biết tên và số điện thoại.",
        "trace": [
            {
                "step": 1,
                "thought": "Người dùng muốn khám Tim mạch, buổi sáng. Cần tìm slot còn trống.",
                "action": "search_available_slots",
                "action_input": {"specialty": "Tim mạch", "date": "2026-06-09", "preferred_time": "morning"},
                "observation": "Tìm thấy 3 slot: 08:30 (45 phút), 09:30 (20 phút), 10:30 (35 phút).",
            },
            {
                "step": 2,
                "thought": "Có 3 slot. Cần xếp hạng theo thời gian chờ thấp nhất.",
                "action": "rank_slots",
                "action_input": {"criteria": "lowest_wait_time", "slots": ["SL001", "SL002", "SL003"]},
                "observation": "Slot tốt nhất: SL002 (Dr. Lan, 09:30, wait=20 phút).",
            },
            {
                "step": 3,
                "thought": "Đã có slot tốt nhất, cần hỏi người dùng xác nhận trước khi đặt lịch chính thức.",
                "action": None,
                "action_input": None,
                "observation": None,
            },
        ],
        "loop_count": 3,
        "tools_called": ["search_available_slots", "rank_slots"],
        "final_status": "success",
        "error_code": None,
        "fallback_used": False,
        "token_prompt_estimate": 680,
        "token_completion_estimate": 195,
        "latency": 4.3,
    },
}


def run_demo_mode(query: str, mode: str) -> Dict[str, Any]:
    """Trả về dữ liệu demo khi chưa có LLM thật."""
    resp = DEMO_RESPONSES.get(mode, DEMO_RESPONSES["chatbot"]).copy()
    # Giả lập latency
    time.sleep(min(resp["latency"] * 0.3, 2.0))
    resp["user_query"] = query
    resp["start_time"] = datetime.utcnow().isoformat()
    resp["end_time"] = datetime.utcnow().isoformat()
    return resp


# ─────────────────────────────────────────────────────────────────
# Agent runner (sẽ dùng khi có LLM thật)
# ─────────────────────────────────────────────────────────────────
def run_chatbot(query: str, llm) -> Dict[str, Any]:
    """Chạy chatbot baseline."""
    from dotenv import load_dotenv
    load_dotenv()

    start = time.time()
    start_time = datetime.utcnow().isoformat()

    system_prompt = (
        "Bạn là trợ lý tư vấn đặt lịch khám bệnh. "
        "Trả lời câu hỏi của người dùng một cách thân thiện và ngắn gọn. "
        "LƯU Ý: Bạn không có khả năng truy vấn database, hãy nói rõ điều này nếu được hỏi về lịch cụ thể."
    )

    result = llm.generate(query, system_prompt=system_prompt)
    latency = time.time() - start

    tracker.track_request(
        provider=result.get("provider", "unknown"),
        model=llm.model_name,
        usage=result.get("usage", {}),
        latency_ms=int(latency * 1000),
        version="chatbot",
    )

    return {
        "answer": result.get("content", ""),
        "trace": [],
        "loop_count": 0,
        "tools_called": [],
        "final_status": "success",
        "error_code": None,
        "fallback_used": False,
        "token_prompt_estimate": result.get("usage", {}).get("prompt_tokens", 0),
        "token_completion_estimate": result.get("usage", {}).get("completion_tokens", 0),
        "latency": latency,
        "user_query": query,
        "start_time": start_time,
        "end_time": datetime.utcnow().isoformat(),
    }


def run_agent(query: str, llm, version: str = "agent_v1") -> Dict[str, Any]:
    """
    Chạy ReAct Agent (v1 hoặc v2).
    Stub — được thay thế bởi src/agent/react_agent.py khi Người 4 hoàn thiện.
    """
    from src.agent.agent import ReActAgent

    # Tool stubs (thay bằng tools thật của Người 3)
    tools = [
        {
            "name": "search_available_slots",
            "description": "Tìm các slot khám còn trống theo chuyên khoa, ngày và buổi. Input: {specialty, date, preferred_time?}",
        },
        {
            "name": "rank_slots",
            "description": "Xếp hạng danh sách slot theo tiêu chí (lowest_wait_time). Input: {slots, criteria}",
        },
        {
            "name": "book_appointment",
            "description": "Đặt lịch khám sau khi người dùng xác nhận. Input: {patient_name, phone, slot_id}",
        },
        {
            "name": "suggest_alternative_dates",
            "description": "Gợi ý ngày khám thay thế khi ngày mong muốn hết slot. Input: {specialty, from_date}",
        },
        {
            "name": "escalate_to_human",
            "description": "Chuyển sang điều phối viên khi agent không thể xử lý. Input: {reason, user_query}",
        },
    ]

    max_steps = 5 if version == "agent_v2" else 10
    agent = ReActAgent(llm=llm, tools=tools, max_steps=max_steps)

    start = time.time()
    start_time = datetime.utcnow().isoformat()

    answer = agent.run(query)
    latency = time.time() - start

    return {
        "answer": answer,
        "trace": [],
        "loop_count": 0,
        "tools_called": [],
        "final_status": "success",
        "error_code": None,
        "fallback_used": False,
        "token_prompt_estimate": 0,
        "token_completion_estimate": 0,
        "latency": latency,
        "user_query": query,
        "start_time": start_time,
        "end_time": datetime.utcnow().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────
def main():
    render_header()
    mode = render_mode_selector()

    # ── Tabs chính ─────────────────────────────────────────────
    tab_chat, tab_history, tab_comparison = st.tabs([
        "💬 Chat",
        "📜 Lịch sử & Logs",
        "📊 So sánh & Evaluation",
    ])

    # ── TAB 1: CHAT ────────────────────────────────────────────
    with tab_chat:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Hiển thị welcome screen nếu chưa có tin nhắn
        if not st.session_state.messages:
            render_welcome_screen()

        # Hiển thị các tin nhắn trong lịch sử chat
        for msg in st.session_state.messages:
            render_chat_message(msg["role"], msg["content"], msg.get("mode"))
            if msg["role"] == "assistant" and msg.get("trace"):
                render_trace(msg["trace"])
                # Bọc metrics và log trong expander
                with st.expander("📊 Xem metrics & log của lượt phản hồi này", expanded=False):
                    render_metrics(msg.get("metrics", {}))
                    render_log_json(msg.get("metrics", {}))

        # Nhận query đầu vào (từ st.chat_input hoặc ví dụ gợi ý)
        query = None
        if "submit_query" in st.session_state and st.session_state["submit_query"]:
            query = st.session_state.pop("submit_query")
        else:
            query = st.chat_input("Hỏi gì đó về đặt lịch khám...")

        if query:
            # Hiển thị tin nhắn user lập tức
            render_chat_message("user", query)
            st.session_state.messages.append({"role": "user", "content": query})

            llm = get_llm_provider()

            with st.spinner(f"Đang xử lý bằng {mode}..."):
                try:
                    if llm is None:
                        # Chạy demo mode khi không có API key
                        result = run_demo_mode(query, mode)
                    elif mode == "chatbot":
                        result = run_chatbot(query, llm)
                    else:
                        result = run_agent(query, llm, version=mode)

                    # Lưu log
                    run_id = app_logger.save_run_log(
                        version=mode,
                        user_query=result.get("user_query", query),
                        start_time=result.get("start_time", ""),
                        end_time=result.get("end_time", ""),
                        latency_seconds=result.get("latency", 0.0),
                        loop_count=result.get("loop_count", 0),
                        tools_called=result.get("tools_called", []),
                        final_status=result.get("final_status", "unknown"),
                        error_code=result.get("error_code"),
                        fallback_used=result.get("fallback_used", False),
                        token_prompt_estimate=result.get("token_prompt_estimate", 0),
                        token_completion_estimate=result.get("token_completion_estimate", 0),
                        trace=result.get("trace", []),
                        final_answer=result.get("answer", ""),
                    )

                    run_log = {
                        "latency_seconds": result.get("latency", 0),
                        "loop_count": result.get("loop_count", 0),
                        "token_prompt_estimate": result.get("token_prompt_estimate", 0),
                        "token_completion_estimate": result.get("token_completion_estimate", 0),
                        "final_status": result.get("final_status", "unknown"),
                        "tools_called": result.get("tools_called", []),
                        "error_code": result.get("error_code"),
                        "fallback_used": result.get("fallback_used", False),
                        "run_id": run_id,
                        "version": mode,
                    }

                    # Thêm câu trả lời vào messages
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result.get("answer", ""),
                        "mode": mode,
                        "trace": result.get("trace", []),
                        "metrics": run_log
                    })

                    # Lưu vào session history
                    if "history" not in st.session_state:
                        st.session_state.history = []
                    st.session_state.history.insert(0, {
                        "run_id": run_id,
                        "mode": mode,
                        "query": query,
                        "result": result,
                    })

                    if hasattr(st, "rerun"):
                        st.rerun()
                    else:
                        st.experimental_rerun()

                except Exception as e:
                    st.error(f"❌ Lỗi hệ thống: {e}")
                    app_logger.error(f"App error: {e}")

    # ── TAB 2: HISTORY & LOGS ──────────────────────────────────
    with tab_history:
        st.markdown("### 📜 Lịch sử Các Run Trong Session")
        history = st.session_state.get("history", [])
        if not history:
            st.info("Chưa có run nào trong session hiện tại. Hãy thử gửi một yêu cầu ở tab Chat!")
        else:
            for item in history:
                with st.expander(
                    f"[{item['mode'].upper()}] {item['query'][:60]}… — {item['run_id']}",
                    expanded=False,
                ):
                    render_final_answer(item["result"].get("answer", ""), item["mode"])
                    render_trace(item["result"].get("trace", []))
                    render_log_json(item["result"])

        st.markdown("---")
        st.markdown("### 📂 Tất Cả Log Files (logs/)")
        all_logs = app_logger.load_run_logs(version="all")
        if all_logs:
            st.success(f"Tìm thấy **{len(all_logs)}** log file(s).")
            for lg in all_logs[-10:]:  # Hiển thị 10 log gần nhất
                with st.expander(f"{lg.get('run_id','?')} — {lg.get('version','?')} — {lg.get('final_status','?')}", expanded=False):
                    st.json(lg)
        else:
            st.info("Chưa có log file nào. Chạy demo để tạo log.")

    # ── TAB 3: COMPARISON & EVALUATION ────────────────────────
    with tab_comparison:
        st.markdown("### 📊 Bảng So Sánh: Chatbot vs Agent v1 vs Agent v2")

        all_logs = app_logger.load_run_logs(version="all")

        if all_logs:
            # Nhóm logs theo version
            grouped: Dict[str, List[Dict]] = {"chatbot": [], "agent_v1": [], "agent_v2": []}
            for lg in all_logs:
                v = lg.get("version", "")
                if v in grouped:
                    grouped[v].append(lg)

            stats = {}
            for key, logs in grouped.items():
                if logs:
                    stats[key] = tracker.compute_aggregate(logs)

            render_comparison_table(stats)

            # Chi tiết từng version
            if stats:
                st.markdown("---")
                st.markdown("#### 🔎 Chi Tiết Từng Version")
                cols = st.columns(len(stats))
                for i, (key, m) in enumerate(stats.items()):
                    label = {"chatbot": "💬 Chatbot", "agent_v1": "🤖 Agent v1", "agent_v2": "🚀 Agent v2"}.get(key, key)
                    with cols[i]:
                        st.markdown(f"**{label}**")
                        st.metric("Success Rate", f"{m.get('success_rate', 0)}%")
                        st.metric("Avg Latency", f"{m.get('avg_latency_s', 0):.2f}s")
                        st.metric("Avg Loop Count", m.get("avg_loop_count", 0))
                        st.metric("Fallback Rate", f"{m.get('fallback_rate', 0)}%")
                        st.metric("Parser Error", f"{m.get('parser_error_rate', 0)}%")
        else:
            # Hiển thị bảng tĩnh mẫu từ INSTRUCTOR_ROLE.md
            st.info("📝 Chưa có log thực tế. Dưới đây là bảng kết quả mẫu từ tài liệu hướng dẫn:")
            import pandas as pd
            sample_data = {
                "Version": ["💬 Chatbot Baseline", "🤖 Agent v1", "🚀 Agent v2"],
                "Success Rate (%)": [40, 65, 85],
                "Avg Latency (s)": [1.2, 6.5, 5.2],
                "Avg Loop Count": [0, 4.1, 3.0],
                "Parser Error (%)": [0, 20, 5],
                "Timeout (%)": [0, 10, 5],
                "Fallback Rate (%)": [0, 15, 8],
            }
            df = pd.DataFrame(sample_data).set_index("Version")
            st.dataframe(df, use_container_width=True)
            st.caption("⚠️ Số liệu trên là ví dụ. Chạy test cases để lấy số liệu thực tế.")

        # Link tới evaluation script
        st.markdown("---")
        st.markdown(
            "💡 **Chạy evaluation đầy đủ**: `python tests/run_evaluation.py` "
            "để parse toàn bộ logs và xuất bảng metrics chính xác."
        )

    render_footer()


if __name__ == "__main__":
    main()
