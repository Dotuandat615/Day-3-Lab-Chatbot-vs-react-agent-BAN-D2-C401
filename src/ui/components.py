"""
src/ui/components.py
Người 5 — UI/UX + Monitoring Dashboard + Evaluation
Các Streamlit UI components tái sử dụng cho app.py (Đã nâng cấp giao diện ChatGPT)
"""

import streamlit as st
from typing import List, Dict, Any, Optional

# ─────────────────────────────────────────────────────────────────
# CSS + Page Setup
# ─────────────────────────────────────────────────────────────────
def apply_custom_css():
    """Inject CSS tùy chỉnh cho giao diện ChatGPT Dark Mode hiện đại."""
    st.markdown(
        """
        <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* ChatGPT Dark Mode background */
        .stApp {
            background-color: #212121;
            min-height: 100vh;
            color: #ececec;
        }

        /* Sidebar styling to match ChatGPT */
        [data-testid="stSidebar"] {
            background-color: #171717 !important;
            border-right: 1px solid #2f2f2f;
        }
        
        [data-testid="stSidebar"] .stMarkdown, 
        [data-testid="stSidebar"] .stText,
        [data-testid="stSidebar"] label {
            color: #c5c5d2 !important;
        }

        /* Glassmorphism card for non-chat elements (like metrics, evaluation) */
        .glass-card {
            background: #2f2f2f;
            border: 1px solid #424242;
            border-radius: 12px;
            padding: 18px 22px;
            margin-bottom: 16px;
        }

        /* ChatGPT Chat Bubble styles */
        .chat-message-user {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 1.5rem;
            width: 100%;
        }
        
        .chat-message-assistant {
            display: flex;
            justify-content: flex-start;
            margin-bottom: 1.5rem;
            width: 100%;
        }
        
        .chat-bubble-user {
            background-color: #2f2f2f;
            color: #f7f7f8;
            border-radius: 18px;
            padding: 10px 16px;
            max-width: 70%;
            word-wrap: break-word;
            font-size: 0.95rem;
            line-height: 1.5;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        }
        
        .chat-bubble-assistant {
            background-color: transparent;
            color: #ececec;
            padding: 4px 0px;
            max-width: 100%;
            word-wrap: break-word;
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .assistant-wrapper {
            display: flex;
            align-items: flex-start;
            gap: 16px;
            width: 100%;
        }

        .assistant-avatar {
            background-color: #10a37f;
            color: white;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        }

        .user-avatar {
            background-color: #ab68ff;
            color: white;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
            margin-left: 12px;
        }

        /* Trace step styling inside expander */
        .trace-thought {
            background: rgba(99, 102, 241, 0.1);
            border-left: 3px solid #6366f1;
            border-radius: 6px;
            padding: 8px 12px;
            margin: 4px 0;
            color: #c7d2fe;
            font-size: 0.85rem;
        }
        
        .trace-action {
            background: rgba(245, 158, 11, 0.1);
            border-left: 3px solid #f59e0b;
            border-radius: 6px;
            padding: 8px 12px;
            margin: 4px 0;
            color: #fde68a;
            font-size: 0.85rem;
            font-family: monospace;
        }
        
        .trace-observation {
            background: rgba(16, 185, 129, 0.1);
            border-left: 3px solid #10b981;
            border-radius: 6px;
            padding: 8px 12px;
            margin: 4px 0;
            color: #a7f3d0;
            font-size: 0.85rem;
        }

        /* Error banner styling */
        .error-banner {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            padding: 10px 14px;
            color: #fca5a5;
            font-size: 0.88rem;
            margin: 8px 0;
        }

        /* Metric card */
        .metric-box {
            background: #2f2f2f;
            border-radius: 12px;
            padding: 12px 10px;
            text-align: center;
            border: 1px solid #424242;
        }
        
        .metric-value {
            font-size: 1.4rem;
            font-weight: 700;
            color: #10a37f;
        }
        
        .metric-label {
            font-size: 0.75rem;
            color: #94a3b8;
            margin-top: 4px;
        }

        /* Mode selector badge */
        .mode-badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.3px;
        }
        .badge-chatbot { background: #4b5563; color: #f3f4f6; }
        .badge-v1      { background: #1e3a8a; color: #93c5fd; }
        .badge-v2      { background: #064e3b; color: #6ee7b7; }

        /* Scrollable log box */
        .log-box {
            background: #171717;
            border-radius: 8px;
            padding: 10px 12px;
            font-family: 'Courier New', monospace;
            font-size: 0.78rem;
            color: #a5b4fc;
            max-height: 240px;
            overflow-y: auto;
            border: 1px solid #2f2f2f;
            white-space: pre-wrap;
            word-break: break-all;
        }

        /* Custom style for Streamlit buttons acting as ChatGPT quick examples */
        div.stButton > button {
            background-color: #2f2f2f !important;
            color: #b4b4b4 !important;
            border: 1px solid #424242 !important;
            border-radius: 12px !important;
            padding: 12px 16px !important;
            width: 100% !important;
            text-align: left !important;
            font-size: 0.88rem !important;
            transition: all 0.2s ease-in-out !important;
            display: block !important;
            white-space: normal !important;
            height: auto !important;
            min-height: 70px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }
        
        div.stButton > button:hover {
            background-color: #383838 !important;
            color: #ececec !important;
            border-color: #4f4f4f !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
        }

        /* Fix Streamlit chat input alignment and styling */
        .stChatInputContainer {
            border-radius: 16px !important;
            background-color: #2f2f2f !important;
            border: 1px solid #424242 !important;
        }
        
        .stChatInputContainer textarea {
            color: #ececec !important;
        }

        .status-success { color: #10a37f; font-weight: 600; }
        .status-error   { color: #ef4444; font-weight: 600; }
        .status-fallback{ color: #f59e0b; font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────
def render_header():
    """Render tiêu đề nhỏ gọn để dành khoảng trống cho hội thoại."""
    st.markdown(
        """
        <div style="padding: 10px 0; border-bottom: 1px solid #2f2f2f; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.5rem;">🏥</span>
                <span style="font-weight: 700; font-size: 1.2rem; color: #ffffff;">AI Medical Booking Assistant</span>
            </div>
            <div style="color: #94a3b8; font-size: 0.8rem;">
                VinUni AI Thực Chiến · Lab 3
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────
# Welcome Screen (ChatGPT Style)
# ─────────────────────────────────────────────────────────────────
def render_welcome_screen():
    """Hiển thị màn hình chào mừng tối giản và danh sách ví dụ gợi ý khi chưa có tin nhắn."""
    st.markdown(
        """
        <div style="text-align: center; margin-top: 3.5rem; margin-bottom: 2.5rem;">
            <div style="display: inline-flex; align-items: center; justify-content: center; background-color: #10a37f; color: white; width: 64px; height: 64px; border-radius: 50%; font-size: 2.2rem; margin-bottom: 1.2rem; box-shadow: 0 4px 12px rgba(16,163,127,0.3);">
                🏥
            </div>
            <h2 style="font-size: 2.2rem; font-weight: 700; color: #ffffff; margin-bottom: 0.5rem;
                       background: linear-gradient(90deg, #a5b4fc, #67e8f9, #6ee7b7);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Tôi có thể giúp gì cho bạn hôm nay?
            </h2>
            <p style="color: #94a3b8; font-size: 1rem; max-width: 500px; margin: 0 auto;">
                Đặt lịch khám bệnh nhanh chóng với AI Trợ Lý. Vui lòng chọn một câu hỏi gợi ý bên dưới hoặc tự nhập yêu cầu của bạn.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<p style='text-align: center; color: #8e8e9f; font-size: 0.85rem; font-weight: 600; margin-bottom: 1rem;'>💡 Ví dụ đặt câu hỏi:</p>", unsafe_allow_html=True)
    
    examples = [
        ("🩺 Chuyên khoa Tim mạch", "Tôi muốn khám Tim mạch sáng thứ 3 tuần sau, ít phải chờ."),
        ("👶 Chuyên khoa Nhi", "Có bác sĩ Nhi nào rảnh cuối tuần không?"),
        ("⚡ Đặt nhanh sớm nhất", "Đặt lịch khám cho tôi càng sớm càng tốt."),
        ("🧪 Chuyên khoa Da liễu", "Khám Da liễu chiều mai được không?")
    ]
    
    col1, col2 = st.columns(2)
    with col1:
        for title, text in examples[:2]:
            if st.button(f"{title}\n\n{text}", key=f"ex_btn_{hash(text)}", use_container_width=True):
                # Gán vào submit_query để app.py tự chạy
                st.session_state["submit_query"] = text
                if hasattr(st, "rerun"):
                    st.rerun()
                else:
                    st.experimental_rerun()
                    
    with col2:
        for title, text in examples[2:]:
            if st.button(f"{title}\n\n{text}", key=f"ex_btn_{hash(text)}", use_container_width=True):
                st.session_state["submit_query"] = text
                if hasattr(st, "rerun"):
                    st.rerun()
                else:
                    st.experimental_rerun()


# ─────────────────────────────────────────────────────────────────
# Mode selector sidebar
# ─────────────────────────────────────────────────────────────────
def render_mode_selector() -> str:
    """
    Sidebar mode selector, được thiết kế lại gọn gàng, tinh tế kiểu ChatGPT.
    Returns: 'chatbot' | 'agent_v1' | 'agent_v2'
    """
    with st.sidebar:
        # Nút New Chat để xóa lịch sử
        if st.button("➕ Cuộc trò chuyện mới", use_container_width=True, key="new_chat_btn_sidebar"):
            st.session_state.messages = []
            st.session_state.history = []
            # Reset query submit
            st.session_state.pop("submit_query", None)
            if hasattr(st, "rerun"):
                st.rerun()
            else:
                st.experimental_rerun()

        st.markdown("<div style='margin: 15px 0; border-top: 1px solid #2f2f2f;'></div>", unsafe_allow_html=True)
        st.markdown("### ⚙️ Cấu hình Mô hình")
        
        mode = st.selectbox(
            "Chọn chế độ xử lý:",
            options=["chatbot", "agent_v1", "agent_v2"],
            format_func=lambda x: {
                "chatbot": "💬 Chatbot Baseline",
                "agent_v1": "🤖 ReAct Agent v1",
                "agent_v2": "🚀 ReAct Agent v2",
            }[x],
            key="mode_select",
        )

        st.markdown("<div style='margin: 15px 0; border-top: 1px solid #2f2f2f;'></div>", unsafe_allow_html=True)
        st.markdown("**Chi tiết chế độ:**")
        descriptions = {
            "chatbot": "LLM thông thường trả lời trực tiếp, không sử dụng công cụ (Tools). Tốc độ nhanh nhưng không tra cứu được lịch khám thực tế.",
            "agent_v1": "ReAct Agent (Thought → Action → Observation) cơ bản. Có khả năng tự động gọi tools để tra cứu & đặt lịch.",
            "agent_v2": "ReAct Agent nâng cao. Thêm cơ chế xử lý lỗi, retry khi phân tích sai cú pháp, giới hạn bước lặp và cơ chế tự động chuyển hướng thông minh.",
        }
        st.info(descriptions[mode])

    return mode


# ─────────────────────────────────────────────────────────────────
# Chat input area (Fallback nếu không dùng st.chat_input)
# ─────────────────────────────────────────────────────────────────
def render_input_area() -> str:
    """Render input box thông thường làm fallback."""
    default_val = st.session_state.pop("example_query", "")
    query = st.text_area(
        "💬 Nhập yêu cầu đặt lịch của bạn:",
        value=default_val,
        placeholder="Ví dụ: Tôi muốn khám Tim mạch sáng thứ 3 tuần sau, ưu tiên slot ít phải chờ.",
        height=80,
        key="user_input",
    )
    return query.strip()


# ─────────────────────────────────────────────────────────────────
# Chat Message Renderers (ChatGPT style)
# ─────────────────────────────────────────────────────────────────
def render_chat_message(role: str, text: str, mode: Optional[str] = None):
    """
    Render một tin nhắn đơn lẻ theo style ChatGPT.
    role: 'user' | 'assistant'
    """
    if role == "user":
        st.markdown(
            f"""
            <div class="chat-message-user">
                <div class="chat-bubble-user">
                    {text}
                </div>
                <div class="user-avatar">👤</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        badge_html = ""
        if mode:
            badge_cls = {
                "chatbot": "badge-chatbot",
                "agent_v1": "badge-v1",
                "agent_v2": "badge-v2",
            }.get(mode, "badge-chatbot")
            mode_label = {
                "chatbot": "Chatbot Baseline",
                "agent_v1": "Agent v1",
                "agent_v2": "Agent v2",
            }.get(mode, mode)
            badge_html = f'<span class="mode-badge {badge_cls}" style="margin-left: 8px; vertical-align: middle;">{mode_label}</span>'
        
        st.markdown(
            f"""
            <div class="chat-message-assistant">
                <div class="assistant-wrapper">
                    <div class="assistant-avatar">🏥</div>
                    <div style="flex-grow: 1;">
                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                            <span style="font-weight: 600; color: #ececec; font-size: 0.9rem;">AI Assistant</span>
                            {badge_html}
                        </div>
                        <div class="chat-bubble-assistant">
                            {text}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_final_answer(answer: str, mode: str):
    """Hiển thị câu trả lời cuối cùng (tương thích ngược với code cũ)."""
    render_chat_message("assistant", answer, mode)


# ─────────────────────────────────────────────────────────────────
# Trace viewer
# ─────────────────────────────────────────────────────────────────
def render_trace(trace: List[Dict[str, Any]]):
    """
    Hiển thị trace Thought / Action / Observation dưới dạng expander thu gọn.
    trace: list of {step, thought, action, action_input, observation}
    """
    if not trace:
        return

    # Sử dụng expander để thu gọn trace suy nghĩ giống AI Reasoning
    with st.expander("⚙️ Xem quá trình suy nghĩ (ReAct Trace)", expanded=False):
        for step in trace:
            step_num = step.get("step", "?")
            st.markdown(f"<p style='color:#a5b4fc; font-weight:600; margin-bottom: 4px;'>Bước {step_num}:</p>", unsafe_allow_html=True)
            if step.get("thought"):
                st.markdown(
                    f'<div class="trace-thought">💭 <b>Thought:</b> {step["thought"]}</div>',
                    unsafe_allow_html=True,
                )
            if step.get("action"):
                action_input = step.get("action_input", "")
                if isinstance(action_input, dict):
                    import json as _json
                    action_input = _json.dumps(action_input, ensure_ascii=False)
                st.markdown(
                    f'<div class="trace-action">⚡ <b>Action:</b> {step["action"]}<br>'
                    f'<span style="opacity:0.7">Input: {action_input}</span></div>',
                    unsafe_allow_html=True,
                )
            if step.get("observation"):
                st.markdown(
                    f'<div class="trace-observation">👁️ <b>Observation:</b> {step["observation"]}</div>',
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────────
# Metrics panel
# ─────────────────────────────────────────────────────────────────
def render_metrics(run_log: Dict[str, Any]):
    """Hiển thị metrics của một run: latency, tokens, loop count, status."""
    st.markdown("#### 📊 Metrics Phản Hồi")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        latency = run_log.get("latency_seconds", 0)
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{latency:.2f}s</div>'
            f'<div class="metric-label">Latency</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        loop = run_log.get("loop_count", 0)
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{loop}</div>'
            f'<div class="metric-label">Loop Count</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        tokens = run_log.get("token_prompt_estimate", 0) + run_log.get("token_completion_estimate", 0)
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{tokens}</div>'
            f'<div class="metric-label">Tokens Est.</div></div>',
            unsafe_allow_html=True,
        )
    with col4:
        status = run_log.get("final_status", "unknown")
        css = "status-success" if status == "success" else "status-error"
        st.markdown(
            f'<div class="metric-box"><div class="metric-value {css}">{status.upper()}</div>'
            f'<div class="metric-label">Status</div></div>',
            unsafe_allow_html=True,
        )

    # Tools called
    tools = run_log.get("tools_called", [])
    if tools:
        st.markdown(f"<span style='color: #94a3b8; font-size: 0.85rem;'>Công cụ đã dùng:</span> `{'`, `'.join(tools)}`", unsafe_allow_html=True)

    # Error code
    error_code = run_log.get("error_code")
    fallback = run_log.get("fallback_used", False)
    if error_code:
        render_error_message(error_code)
    if fallback:
        st.warning("⚠️ Cơ chế Fallback dự phòng được kích hoạt cho lượt chạy này.")


# ─────────────────────────────────────────────────────────────────
# Error messages
# ─────────────────────────────────────────────────────────────────
ERROR_MESSAGES: Dict[str, str] = {
    "MISSING_INFORMATION": "ℹ️ Mình cần thêm chuyên khoa hoặc ngày khám để kiểm tra lịch phù hợp.",
    "NO_SLOT_FOUND": "📅 Hiện chưa có slot phù hợp. Mình có thể gợi ý ngày gần nhất hoặc chuyển cho điều phối viên.",
    "PARSER_ERROR": "⚠️ Mình chưa thể xử lý yêu cầu tự động ngay lúc này. Vui lòng thử lại hoặc để nhân viên hỗ trợ.",
    "HALLUCINATED_TOOL": "🔧 Hệ thống đang gặp lỗi chọn công cụ xử lý. Mình sẽ chuyển sang kênh hỗ trợ dự phòng.",
    "TOOL_RUNTIME_ERROR": "❗ Có lỗi khi kiểm tra lịch khám. Vui lòng thử lại hoặc để nhân viên hỗ trợ tiếp.",
    "TIMEOUT": "⏰ Hệ thống đang mất nhiều thời gian hơn dự kiến. Mình sẽ chuyển yêu cầu sang hỗ trợ dự phòng.",
    "MAX_STEPS_EXCEEDED": "🔄 Mình chưa thể hoàn tất yêu cầu tự động sau nhiều bước. Mình sẽ chuyển ca này cho điều phối viên.",
    "FALLBACK_TO_CHATBOT": "💬 Đang chuyển sang Chatbot Baseline để hỗ trợ bạn.",
    "FALLBACK_TO_HUMAN": "🧑‍⚕️ Đang chuyển yêu cầu của bạn sang điều phối viên để được hỗ trợ chính xác hơn.",
}


def render_error_message(error_code: str):
    """Hiển thị error message thân thiện cho người dùng."""
    msg = ERROR_MESSAGES.get(error_code, f"⚠️ Đã xảy ra lỗi: {error_code}")
    st.markdown(
        f'<div class="error-banner">{msg}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────
# Log JSON viewer
# ─────────────────────────────────────────────────────────────────
def render_log_json(run_log: Dict[str, Any]):
    """Hiển thị raw log JSON trong collapsible box."""
    import json as _json

    with st.expander("🗂️ Raw Log JSON (Chẩn đoán)", expanded=False):
        st.markdown(
            f'<div class="log-box">{_json.dumps(run_log, ensure_ascii=False, indent=2)}</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────
# Comparison table
# ─────────────────────────────────────────────────────────────────
def render_comparison_table(stats: Dict[str, Dict[str, Any]]):
    """
    Hiển thị bảng so sánh Chatbot vs Agent v1 vs Agent v2.
    stats: { 'chatbot': {...metrics}, 'agent_v1': {...}, 'agent_v2': {...} }
    """
    import pandas as pd

    st.markdown("#### 📋 Bảng So Sánh Tổng Hợp Hiệu Năng")

    labels = {
        "chatbot": "💬 Chatbot",
        "agent_v1": "🤖 Agent v1",
        "agent_v2": "🚀 Agent v2",
    }

    rows = []
    for key, label in labels.items():
        m = stats.get(key, {})
        if m:
            rows.append({
                "Version": label,
                "N Runs": m.get("n_runs", 0),
                "Success Rate (%)": m.get("success_rate", 0),
                "Avg Latency (s)": m.get("avg_latency_s", 0),
                "Avg Loop Count": m.get("avg_loop_count", 0),
                "Parser Error (%)": m.get("parser_error_rate", 0),
                "Timeout (%)": m.get("timeout_rate", 0),
                "Hallucination (%)": m.get("hallucination_rate", 0),
                "Fallback Rate (%)": m.get("fallback_rate", 0),
                "Avg Prompt Tokens": m.get("avg_prompt_tokens", 0),
            })

    if rows:
        df = pd.DataFrame(rows).set_index("Version")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Chưa có đủ log để tạo bảng so sánh. Hãy chạy một số test cases trước.")


# ─────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────
def render_footer():
    st.markdown("---")
    st.markdown(
        '<p style="text-align:center; color:#555555; font-size:0.78rem;">'
        "AI Trợ Lý Đặt Lịch Khám · Lab 3 · VinUni AI Thực Chiến · Người 5: UI/UX + Monitoring"
        "</p>",
        unsafe_allow_html=True,
    )
