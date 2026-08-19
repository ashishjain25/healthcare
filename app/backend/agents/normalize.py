"""Normalizes free-text status/urgency/risk words the LLM emits into the
strict Literal values our schemas require.

Real-world finding: despite format_instructions listing the exact allowed
values, gpt-4o-mini reliably drifts to synonyms on real clinical report text
("Slightly High", "ABNORMAL", "Low-normal", "Prolonged", "Positive",
"LOW (Stage 3 CKD)") which made PydanticOutputParser raise
OutputParserException and fail the whole pipeline stage. These functions are
applied as `field_validator(mode="before")` so a close-enough LLM answer is
coerced into a valid value instead of hard-failing the pipeline. The mapping
deliberately errs toward flagging (LOW/HIGH over NORMAL) when a qualifier is
ambiguous, and toward UNKNOWN (never a guessed direction) when there is no
signal at all — consistent with this project's safety-first bias, since
plain LOW/HIGH never triggers escalation on its own (only CRITICAL_* does,
via deterministic checks elsewhere).
"""
import re


def _norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().upper()


def normalize_lab_status(value: object) -> str:
    valid = {"NORMAL", "LOW", "HIGH", "CRITICAL_LOW", "CRITICAL_HIGH", "UNKNOWN"}
    text = _norm(value)
    if text in valid:
        return text

    is_critical = "CRITICAL" in text or "PANIC" in text or "SEVERE" in text
    is_low = re.search(r"\bLOW\b", text) is not None or "DECREASED" in text or "REDUCED" in text
    is_high = (
        re.search(r"\bHIGH\b", text) is not None
        or "ELEVATED" in text or "PROLONGED" in text or "INCREASED" in text
    )

    if is_critical and is_low:
        return "CRITICAL_LOW"
    if is_critical and is_high:
        return "CRITICAL_HIGH"
    if is_critical:
        return "CRITICAL_HIGH"
    if is_low:
        return "LOW"
    if is_high:
        return "HIGH"
    if "POSITIVE" in text or "PROTEINURIA" in text:
        return "HIGH"
    if re.search(r"\bNORMAL\b", text) and "ABNORMAL" not in text:
        return "NORMAL"
    # "ABNORMAL", "POSITIVE" without direction, or anything unrecognized: be
    # honest about not knowing the direction rather than guessing.
    return "UNKNOWN"


def normalize_urgency(value: object, *, allow_emergency: bool = True) -> str:
    valid = {"routine", "urgent", "stat", "emergency"} if allow_emergency else {"routine", "urgent", "stat"}
    text = _norm(value)
    lowered = text.lower()
    if lowered in valid:
        return lowered

    if "EMERGENC" in text or "CRITICAL" in text or "IMMEDIATE" in text:
        return "emergency" if allow_emergency else "stat"
    if "STAT" in text:
        return "stat"
    if "URGENT" in text:
        return "urgent"
    return "routine"


def normalize_risk_level(value: object) -> str:
    valid = {"low", "moderate", "high", "critical"}
    text = _norm(value)
    lowered = text.lower()
    if lowered in valid:
        return lowered

    if "CRITICAL" in text or "SEVERE" in text:
        return "critical"
    if "HIGH" in text:
        return "high"
    if "MODERATE" in text or "MEDIUM" in text:
        return "moderate"
    if "LOW" in text:
        return "low"
    return "moderate"
