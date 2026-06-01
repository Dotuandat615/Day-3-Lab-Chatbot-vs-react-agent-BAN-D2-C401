import re

ALLOWED_INTENTS = {
    "book_appointment",
    "reschedule_appointment",
    "cancel_appointment",
    "check_availability"
}

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"show\s+(me\s+)?(the\s+)?system\s+prompt",
    r"reveal\s+(your\s+)?instructions",
    r"act\s+as\s+another\s+assistant",
    r"developer\s+message",
    r"system\s+prompt",
    r"jailbreak",
    r"override\s+instructions"
]

INTENT_KEYWORDS = {
    "book_appointment": [
        "đặt lịch",
        "đăng ký khám",
        "book lịch",
        "hẹn khám",
        "muốn khám",
        "cần khám",
        "xin đặt",
        "đặt hẹn",
    ],
    "reschedule_appointment": [
        "đổi lịch",
        "dời lịch",
        "reschedule",
        "thay đổi lịch",
    ],
    "cancel_appointment": [
        "hủy lịch",
        "cancel lịch",
        "hủy hẹn",
        "không đến được",
    ],
    "check_availability": [
        "còn lịch",
        "lịch trống",
        "bác sĩ nào rảnh",
        "available",
        "khám",
        "chuyên khoa",
        "triệu chứng",
        "tư vấn",
        "nên khám",
        "khám gì",
        "bị đau",
        "bệnh",
        "phòng khám",
        "bác sĩ",
    ]
}


def guardrail(user_input: str, llm) -> bool:

    text = user_input.lower()

    # -------------------------
    # Prompt Injection Check
    # -------------------------

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            return False

    # -------------------------
    # Fast Keyword Intent Check
    # -------------------------

    for keywords in INTENT_KEYWORDS.values():
        for kw in keywords:
            if kw in text:
                return True

    # -------------------------
    # Fallback LLM Classifier
    # -------------------------

    try:
        raw = llm.generate(
            text,
            system_prompt="""
Classify the user request.

Allowed intents:
- book_appointment
- reschedule_appointment
- cancel_appointment
- check_availability

Return ONLY one of:

book_appointment
reschedule_appointment
cancel_appointment
check_availability
unknown
"""
        )

        # Fix: raw is a dict, extract 'content' first
        intent = raw.get("content", "").strip() if isinstance(raw, dict) else str(raw).strip()

        return intent in ALLOWED_INTENTS

    except Exception:

        # Fail closed
        return False