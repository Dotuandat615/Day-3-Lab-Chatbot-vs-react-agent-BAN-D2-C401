"""
tests/run_evaluation.py
Người 5 — UI/UX + Monitoring Dashboard + Evaluation

Script parse logs JSON và tính aggregate metrics cho bảng so sánh.
Chạy: python tests/run_evaluation.py

Output:
- In bảng so sánh Chatbot vs Agent v1 vs Agent v2 ra console
- Ghi report/group_report/evaluation_table.md (overwrite)
"""

import os
import sys
import json
import re
from datetime import datetime
from typing import List, Dict, Any

# Thêm root vào sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.telemetry.logger import IndustryLogger
from src.telemetry.metrics import PerformanceTracker

# ─────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(ROOT, "logs")
TEST_CASES_FILE = os.path.join(ROOT, "tests", "test_cases.json")
OUTPUT_MD = os.path.join(ROOT, "report", "group_report", "evaluation_table.md")

# ─────────────────────────────────────────────────────────────────
# Load test cases
# ─────────────────────────────────────────────────────────────────
def load_test_cases() -> List[Dict[str, Any]]:
    if not os.path.exists(TEST_CASES_FILE):
        print(f"[WARN] test_cases.json not found at {TEST_CASES_FILE}. Using built-in sample cases.")
        return SAMPLE_TEST_CASES
    with open(TEST_CASES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


SAMPLE_TEST_CASES = [
    {"id": "TC01", "query": "Tôi muốn khám Tim mạch sáng thứ 3 tuần sau, ít phải chờ.",
     "expected_behavior": "Agent tìm slot Tim mạch, chọn slot wait time thấp nhất."},
    {"id": "TC02", "query": "Tôi muốn khám Da liễu chiều mai.",
     "expected_behavior": "Agent tìm slot Da liễu vào buổi chiều."},
    {"id": "TC03", "query": "Đặt lịch khám cho tôi càng sớm càng tốt.",
     "expected_behavior": "Agent hỏi lại chuyên khoa vì thiếu thông tin."},
    {"id": "TC04", "query": "Có bác sĩ Nhi nào rảnh cuối tuần không?",
     "expected_behavior": "Agent tìm slot Nhi khoa cuối tuần."},
    {"id": "TC05", "query": "Tôi muốn khám Tim mạch nhưng ngày đó hết slot.",
     "expected_behavior": "Agent gợi ý ngày thay thế."},
    {"id": "TC06", "query": "Đặt lịch cho Nguyễn Văn Nam, SĐT 0901234567, khám tổng quát.",
     "expected_behavior": "Agent tìm slot tổng quát và đặt lịch sau khi xác nhận."},
    {"id": "TC07", "query": "Tôi bị đau ngực, muốn khám gấp.",
     "expected_behavior": "Agent tìm slot Tim mạch sớm nhất."},
    {"id": "TC08", "query": "Hủy lịch khám của tôi.",
     "expected_behavior": "Agent yêu cầu thêm thông tin (mã lịch hẹn) hoặc escalate."},
    {"id": "TC09", "query": "Khám da liễu ở phòng nào?",
     "expected_behavior": "Agent truy vấn database và trả về thông tin phòng khám."},
    {"id": "TC10", "query": "Bác sĩ Minh có lịch trống không tuần tới?",
     "expected_behavior": "Agent tìm slot của bác sĩ Minh trong tuần tới."},
]


# ─────────────────────────────────────────────────────────────────
# Parse and aggregate logs
# ─────────────────────────────────────────────────────────────────
def load_all_logs() -> Dict[str, List[Dict[str, Any]]]:
    """Đọc toàn bộ log JSON, nhóm theo version."""
    logger = IndustryLogger(log_dir=LOG_DIR)
    all_runs = logger.load_run_logs(version="all")

    grouped: Dict[str, List[Dict[str, Any]]] = {
        "chatbot": [],
        "agent_v1": [],
        "agent_v2": [],
    }

    for run in all_runs:
        v = run.get("version", "")
        if v in grouped:
            grouped[v].append(run)

    return grouped


def compute_metrics(grouped: Dict[str, List[Dict]]) -> Dict[str, Dict[str, Any]]:
    tracker = PerformanceTracker()
    stats = {}
    for key, runs in grouped.items():
        if runs:
            stats[key] = tracker.compute_aggregate(runs)
    return stats


# ─────────────────────────────────────────────────────────────────
# Print console table
# ─────────────────────────────────────────────────────────────────
def print_comparison_table(stats: Dict[str, Dict[str, Any]]):
    """In bảng so sánh ra console."""
    print("\n" + "=" * 90)
    print("📊 EVALUATION TABLE — Chatbot Baseline vs Agent v1 vs Agent v2")
    print("=" * 90)

    headers = [
        "Version", "N Runs", "Success %", "Avg Latency(s)",
        "Avg Loops", "Parser Err%", "Timeout%", "Hallucin%", "Fallback%",
    ]
    widths = [18, 8, 11, 16, 11, 13, 10, 11, 11]

    header_row = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(header_row)
    print("-" * len(header_row))

    labels = {
        "chatbot": "Chatbot Baseline",
        "agent_v1": "Agent v1",
        "agent_v2": "Agent v2",
    }

    for key, label in labels.items():
        m = stats.get(key, {})
        if not m:
            row = [label, "0", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]
        else:
            row = [
                label,
                str(m.get("n_runs", 0)),
                f"{m.get('success_rate', 0):.1f}%",
                f"{m.get('avg_latency_s', 0):.2f}s",
                str(m.get("avg_loop_count", 0)),
                f"{m.get('parser_error_rate', 0):.1f}%",
                f"{m.get('timeout_rate', 0):.1f}%",
                f"{m.get('hallucination_rate', 0):.1f}%",
                f"{m.get('fallback_rate', 0):.1f}%",
            ]
        print(" | ".join(v.ljust(w) for v, w in zip(row, widths)))

    print("=" * 90 + "\n")


# ─────────────────────────────────────────────────────────────────
# Failure analysis
# ─────────────────────────────────────────────────────────────────
def analyze_failures(grouped: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
    """Trích xuất các failure cases nổi bật để đưa vào report."""
    failures = []
    for version, runs in grouped.items():
        for run in runs:
            ec = run.get("error_code")
            if ec and ec != "SUCCESS":
                failures.append({
                    "version": version,
                    "run_id": run.get("run_id", "?"),
                    "query": run.get("user_query", ""),
                    "error_code": ec,
                    "fallback_used": run.get("fallback_used", False),
                    "loop_count": run.get("loop_count", 0),
                    "latency_seconds": run.get("latency_seconds", 0),
                })
    return failures


# ─────────────────────────────────────────────────────────────────
# Write Markdown evaluation table
# ─────────────────────────────────────────────────────────────────
def write_evaluation_markdown(
    stats: Dict[str, Dict[str, Any]],
    failures: List[Dict[str, Any]],
    test_cases: List[Dict[str, Any]],
):
    """Ghi file evaluation_table.md."""
    os.makedirs(os.path.dirname(OUTPUT_MD), exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    has_data = bool(stats)

    lines = [
        "# Evaluation Table — Chatbot vs Agent v1 vs Agent v2",
        "",
        f"> Generated: {now}",
        "",
        "---",
        "",
        "## 1. Bảng So Sánh Tổng Hợp",
        "",
    ]

    if has_data:
        lines += [
            "| Version | N Runs | Success Rate | Avg Latency | Avg Loop Count | Parser Error | Timeout | Hallucination | Fallback Rate |",
            "|:--------|-------:|-------------:|------------:|---------------:|-------------:|--------:|--------------:|--------------:|",
        ]
        labels = {
            "chatbot": "💬 Chatbot Baseline",
            "agent_v1": "🤖 Agent v1",
            "agent_v2": "🚀 Agent v2",
        }
        for key, label in labels.items():
            m = stats.get(key, {})
            if m:
                lines.append(
                    f"| {label} | {m.get('n_runs',0)} | {m.get('success_rate',0):.1f}% "
                    f"| {m.get('avg_latency_s',0):.2f}s | {m.get('avg_loop_count',0):.1f} "
                    f"| {m.get('parser_error_rate',0):.1f}% | {m.get('timeout_rate',0):.1f}% "
                    f"| {m.get('hallucination_rate',0):.1f}% | {m.get('fallback_rate',0):.1f}% |"
                )
            else:
                lines.append(f"| {label} | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |")
    else:
        lines += [
            "> ⚠️ **Chưa có log thực tế.** Dưới đây là số liệu ví dụ từ tài liệu hướng dẫn.",
            "",
            "| Version | N Runs | Success Rate | Avg Latency | Avg Loop Count | Parser Error | Timeout | Fallback Rate |",
            "|:--------|-------:|-------------:|------------:|---------------:|-------------:|--------:|--------------:|",
            "| 💬 Chatbot Baseline | 10 | 40.0% | 1.20s | 0.0 | 0.0% | 0.0% | 0.0% |",
            "| 🤖 Agent v1 | 10 | 65.0% | 6.50s | 4.1 | 20.0% | 10.0% | 15.0% |",
            "| 🚀 Agent v2 | 10 | 85.0% | 5.20s | 3.0 | 5.0% | 5.0% | 8.0% |",
            "",
            "> Số liệu trên là ví dụ. Nhóm cần thay bằng số liệu thật từ log.",
        ]

    lines += [
        "",
        "---",
        "",
        "## 2. Metrics Definitions",
        "",
        "| Metric | Ý nghĩa |",
        "|:-------|:--------|",
        "| Success Rate | Tỷ lệ run có `final_status = success` |",
        "| Avg Latency | Thời gian xử lý trung bình (giây) |",
        "| Avg Loop Count | Số vòng ReAct Thought→Action→Observation trung bình |",
        "| Parser Error | Tỷ lệ run gặp lỗi parse output của LLM |",
        "| Timeout | Tỷ lệ run bị timeout |",
        "| Hallucination | Tỷ lệ run agent gọi tool không có trong registry |",
        "| Fallback Rate | Tỷ lệ run phải fallback sang chatbot hoặc điều phối viên |",
        "",
        "---",
        "",
        "## 3. Test Cases Đã Sử Dụng",
        "",
        "| ID | Query | Expected Behavior |",
        "|:---|:------|:-----------------|",
    ]
    for tc in test_cases:
        lines.append(f"| {tc['id']} | {tc['query']} | {tc['expected_behavior']} |")

    lines += [
        "",
        "---",
        "",
        "## 4. Failure Analysis",
        "",
    ]

    if failures:
        lines += [
            "| Run ID | Version | Error Code | Query | Fallback |",
            "|:-------|:--------|:-----------|:------|:---------|",
        ]
        for f in failures[:20]:  # Giới hạn 20 failures
            lines.append(
                f"| `{f['run_id']}` | {f['version']} | `{f['error_code']}` "
                f"| {f['query'][:60]}… | {'✅' if f['fallback_used'] else '❌'} |"
            )
    else:
        lines += [
            "> Chưa có failure case nào trong log. Chạy test cases để phát hiện lỗi.",
            "",
            "### Failure Case Mẫu (theo INSTRUCTOR_ROLE.md)",
            "",
            "**Case: Agent v1 gọi tool không tồn tại (HALLUCINATED_TOOL)**",
            "",
            "```json",
            '{',
            '  "version": "agent_v1",',
            '  "error_code": "HALLUCINATED_TOOL",',
            '  "tool_name": "check_doctor_schedule",',
            '  "available_tools": ["search_available_slots", "rank_slots", "book_appointment"]',
            '}',
            "```",
            "",
            "**Nguyên nhân:** Agent v1 chưa có tool whitelist rõ ràng trong prompt.",
            "",
            "**Cách sửa ở Agent v2:**",
            "- Thêm danh sách tool hợp lệ vào system prompt.",
            "- Parser kiểm tra tool name có trong registry không.",
            "- Nếu tool không tồn tại, log `HALLUCINATED_TOOL` và retry 1 lần.",
        ]

    lines += [
        "",
        "---",
        "",
        "## 5. Kết Luận",
        "",
        "| Điểm mạnh | Chatbot | Agent v1 | Agent v2 |",
        "|:----------|:-------:|:--------:|:--------:|",
        "| Tốc độ phản hồi | ✅ Nhanh | ⚠️ Chậm | ⚠️ Chậm hơn chatbot |",
        "| Truy vấn database | ❌ Không | ✅ Có | ✅ Có |",
        "| Xử lý lỗi | ❌ Không | ⚠️ Cơ bản | ✅ Đầy đủ |",
        "| Guardrails | ❌ Không | ❌ Không | ✅ max_steps + timeout |",
        "| Độ chính xác | ⚠️ Hallucinate | ⚠️ Có thể lỗi | ✅ Tốt nhất |",
        "",
        "> 🎯 **Kết luận**: ReAct Agent v2 vượt trội cho các bài toán multi-step cần truy vấn database.",
        "> Chatbot baseline phù hợp cho Q&A đơn giản và phản hồi nhanh.",
        "",
        "---",
        "",
        "*Báo cáo này được tạo tự động bởi `tests/run_evaluation.py`*",
        f"*Người 5 — UI/UX + Monitoring Dashboard + Evaluation — {now}*",
    ]

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ Saved evaluation table → {OUTPUT_MD}")


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────
def main():
    print("\n🔍 Loading logs from:", LOG_DIR)
    grouped = load_all_logs()

    total = sum(len(v) for v in grouped.values())
    print(f"📂 Found {total} log file(s): "
          f"chatbot={len(grouped['chatbot'])}, "
          f"agent_v1={len(grouped['agent_v1'])}, "
          f"agent_v2={len(grouped['agent_v2'])}")

    print("\n📊 Computing aggregate metrics...")
    stats = compute_metrics(grouped)

    print_comparison_table(stats)

    failures = analyze_failures(grouped)
    if failures:
        print(f"⚠️  Found {len(failures)} failure case(s).")
        for f in failures[:5]:
            print(f"  - [{f['version']}] {f['error_code']}: {f['query'][:50]}…")

    test_cases = load_test_cases()
    print(f"\n📝 Test cases loaded: {len(test_cases)}")

    write_evaluation_markdown(stats, failures, test_cases)

    if not stats:
        print("\n💡 TIP: Chưa có log thực tế. Hãy chạy app.py và thử một số query,")
        print("         sau đó chạy lại script này để xem số liệu thực.")


if __name__ == "__main__":
    main()
