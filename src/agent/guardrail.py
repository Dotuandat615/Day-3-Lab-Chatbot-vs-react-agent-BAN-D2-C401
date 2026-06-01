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
        "hẹn khám"
    ],
    "reschedule_appointment": [
        "đổi lịch",
        "dời lịch",
        "reschedule"
    ],
    "cancel_appointment": [
        "hủy lịch",
        "cancel lịch"
    ],
    "check_availability": [
        "còn lịch",
        "lịch trống",
        "bác sĩ nào rảnh",
        "available"
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

        intent = raw.strip()

        return intent in ALLOWED_INTENTS

    except Exception:

        # Fail closed
        return False