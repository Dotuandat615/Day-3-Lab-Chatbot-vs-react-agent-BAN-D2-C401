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
    from src.chatbot.baseline_chatbot import BaselineChatbot
    chatbot = BaselineChatbot(llm=llm, log_dir="logs")
    result = chatbot.chat(query)
    
    # Cập nhật tracker của Người 5 để hiển thị lên bảng so sánh
    tracker.track_request(
        provider=llm.model_name,
        model=llm.model_name,
        usage={"prompt_tokens": result.get("token_prompt_estimate", 0), "completion_tokens": result.get("token_completion_estimate", 0), "total_tokens": result.get("token_prompt_estimate", 0) + result.get("token_completion_estimate", 0)},
        latency_ms=int(result.get("latency", 0) * 1000),
        version="chatbot",
    )
    
    return result


def run_agent(query: str, llm, version: str = "agent_v1") -> Dict[str, Any]:
    """
    Chạy ReAct Agent (v1 hoặc v2).
    """
    from src.agent.agent import ReActAgent
    from src.tools.tool_registry import TOOL_REGISTRY, run_tool
    from src.telemetry.logger import logger as global_logger
    import json
    import time
    from datetime import datetime

    # 1) Thiết lập danh sách tools thực tế với function wrapper gọi run_tool
    tools = []
    for name, spec in TOOL_REGISTRY.items():
        def make_wrapper(tool_name):
            # Hàm wrapper gọi qua registry để tận dụng validate/error handling chuẩn hóa
            return lambda **kwargs: run_tool(tool_name, kwargs)
        
        tools.append({
            "name": name,
            "description": spec.description,
            "function": make_wrapper(name)
        })

    max_steps = 5 if version == "agent_v2" else 10
    agent = ReActAgent(llm=llm, tools=tools, max_steps=max_steps)

    start = time.time()
    start_time = datetime.utcnow().isoformat()

    # 2) Đăng ký custom handler để hứng tất cả log event trong quá trình ReAct suy nghĩ
    events = []
    original_log_event = global_logger.log_event

    def custom_log_event(event_type, data):
        events.append({"event": event_type, "data": data})
        original_log_event(event_type, data)

    global_logger.log_event = custom_log_event

    answer = "Xin lỗi, không có phản hồi từ Agent."
    final_status = "success"
    error_code = None
    fallback_used = False

    try:
        answer = agent.run(query)
        # Nếu Agent vượt quá số bước tối đa
        if "Maximum reasoning steps reached" in answer:
            final_status = "error"
            error_code = "MAX_STEPS_EXCEEDED"
            # Trong agent_v2, tự động fallback sang escalate_to_human
            if version == "agent_v2":
                fallback_used = True
                # Gọi escalate_to_human trực tiếp để lấy câu trả lời an toàn
                fallback_res = run_tool("escalate_to_human", {"reason": "Vượt số bước suy nghĩ cho phép", "user_query": query})
                answer = fallback_res.get("message", "Đã chuyển tiếp tới bộ phận hỗ trợ khách hàng.")
        elif "invalid structured output" in answer.lower():
            final_status = "error"
            error_code = "PARSER_ERROR"
            if version == "agent_v2":
                fallback_used = True
                fallback_res = run_tool("escalate_to_human", {"reason": "Lỗi parse JSON output của model", "user_query": query})
                answer = fallback_res.get("message", "Đã chuyển tiếp tới bộ phận hỗ trợ khách hàng.")
    except Exception as e:
        final_status = "error"
        error_code = "TOOL_RUNTIME_ERROR"
        answer = f"Lỗi hệ thống: {e}"
        if version == "agent_v2":
            fallback_used = True
            fallback_res = run_tool("escalate_to_human", {"reason": f"Lỗi runtime: {e}", "user_query": query})
            answer = fallback_res.get("message", "Đã chuyển tiếp tới bộ phận hỗ trợ khách hàng.")
    finally:
        global_logger.log_event = original_log_event

    latency = time.time() - start

    # 3) Phân tích các sự kiện thu được để cấu trúc lại trace và tính toán token estimate
    trace = []
    steps_data = {}
    tools_called = []
    token_prompt_estimate = 0
    token_completion_estimate = 0

    for ev in events:
        evt = ev["event"]
        d = ev["data"]
        
        # Đếm token tích lũy từ các cuộc gọi LLM trong ReAct loop
        if evt == "LLM_RESPONSE":
            resp = d.get("response", {})
            usage = resp.get("usage", {})
            token_prompt_estimate += usage.get("prompt_tokens", 0)
            token_completion_estimate += usage.get("completion_tokens", 0)

        step_idx = d.get("step")
        if step_idx is not None:
            if step_idx not in steps_data:
                steps_data[step_idx] = {
                    "step": step_idx + 1,
                    "thought": "",
                    "action": None,
                    "action_input": None,
                    "observation": None
                }
            if evt == "THOUGHT":
                steps_data[step_idx]["thought"] = d.get("thought", "")
            elif evt == "TOOL_CALL":
                tool_name = d.get("tool")
                steps_data[step_idx]["action"] = tool_name
                steps_data[step_idx]["action_input"] = d.get("arguments")
                if tool_name not in tools_called:
                    tools_called.append(tool_name)
            elif evt == "OBSERVATION":
                obs = d.get("observation")
                if isinstance(obs, dict):
                    if obs.get("status") == "success":
                        if "slots" in obs:
                            steps_data[step_idx]["observation"] = f"Tìm thấy {len(obs['slots'])} slot trống."
                        elif "appointment_id" in obs:
                            steps_data[step_idx]["observation"] = f"Đặt lịch thành công! Mã cuộc hẹn: {obs.get('appointment_id')}."
                        elif "best_slot" in obs:
                            best = obs["best_slot"]
                            steps_data[step_idx]["observation"] = f"Slot tốt nhất: {best.get('slot_id')} (Bác sĩ: {best.get('doctor_name')}, Ước tính chờ: {best.get('estimated_wait_time')} phút)."
                        elif "alternatives" in obs:
                            steps_data[step_idx]["observation"] = f"Tìm thấy {len(obs['alternatives'])} lịch thay thế."
                        else:
                            steps_data[step_idx]["observation"] = json.dumps(obs, ensure_ascii=False)
                    else:
                        steps_data[step_idx]["observation"] = f"Lỗi ({obs.get('error_code')}): {obs.get('message')}"
                        # Nếu có lỗi khi chạy tool, lưu error_code cho lượt chạy
                        if not error_code:
                            error_code = obs.get("error_code")
                            final_status = "error"
                else:
                    steps_data[step_idx]["observation"] = str(obs)

    # Đưa các bước vào trace có thứ tự tăng dần
    for step_idx in sorted(steps_data.keys()):
        trace.append(steps_data[step_idx])

    # Nếu không đếm được token qua API (ví dụ local), ta fallback tính xấp xỉ chiều dài chữ
    if token_prompt_estimate == 0:
        token_prompt_estimate = max(1, int(len(query) / 3.5))
    if token_completion_estimate == 0:
        token_completion_estimate = max(1, int(len(answer) / 3.5))

    # Cập nhật tracker của Người 5 để Monitoring dashboard cập nhật chính xác
    tracker.track_request(
        provider=llm.model_name,
        model=llm.model_name,
        usage={"prompt_tokens": token_prompt_estimate, "completion_tokens": token_completion_estimate, "total_tokens": token_prompt_estimate + token_completion_estimate},
        latency_ms=int(latency * 1000),
        version=version,
    )

    return {
        "answer": answer,
        "trace": trace,
        "loop_count": len(trace),
        "tools_called": tools_called,
        "final_status": final_status,
        "error_code": error_code,
        "fallback_used": fallback_used,
        "token_prompt_estimate": token_prompt_estimate,
        "token_completion_estimate": token_completion_estimate,
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
