# core/nlu.py
import re
from typing import Dict, Any, Optional

# -------------------------
# Helpers & regex patterns
# -------------------------
AFFIRM_RX       = re.compile(r"^\s*(sure|ok|okay|yes|yeah|yup|go ahead|please)\s*\.?\s*$", re.I)
START_TIMER_RE  = re.compile(r"\b(start|begin|run|set)\b.*\b(timer|pomodoro)\b", re.I)
DURATION_RE     = re.compile(r"(\d+)\s*(min|minute|minutes|m)\b", re.I)

def _minutes(text: str) -> Optional[int]:
    m = DURATION_RE.search(text or "")
    return int(m.group(1)) if m else None

# -------------------------
# Intent detection
# -------------------------
def detect_intent(text: str) -> str:
    """
    Rule order: most-specific -> least-specific.
    Keeps your existing intent names.
    """
    t = (text or "").strip().lower()

    # rewrite / paraphrase kindly (keep your label)
    if t.startswith("rewrite kindly") or t.startswith("paraphrase kindly"):
        return "rewrite_kindly"

    # journaling
    if re.search(r"\b(add|save|put|log)\b.*\b(journal|note)\b", t):
        return "journal_add"
    if re.search(r"\b(summarize|summary)\b.*\b(week|weekly)\b", t) or t == "summarize my week":
        return "journal_summary"

    # phone-free focus tips (must come BEFORE timer rules)
    if ("focus" in t) and (
        "phone" in t or "mobile" in t or "without my phone" in t or "w/o phone" in t
    ) and ("without" in t or "w/o" in t or "no " in t or "without my phone" in t):
        return "focus_phone_tips"

    # STRICT timer controls (avoid false-positives)
    # - explicit /timer
    # - "start/begin/run/set ... timer/pomodoro"
    # - mentions timer/pomodoro + explicit duration
    if "/timer" in t or START_TIMER_RE.search(t) or (("timer" in t or "pomodoro" in t) and DURATION_RE.search(t)):
        return "pomodoro_start"
    if re.search(r"\b(stop|end|cancel)\b.*\b(timer|pomodoro)\b", t):
        return "pomodoro_stop"
    if re.search(r"\b(status|remaining|how much|left)\b.*\b(timer|pomodoro)\b", t):
        return "pomodoro_status"

    # exam study plan
    if "exam" in t or "test" in t or "study plan" in t or "revision" in t:
        return "exam_study_plan"

    # greeting/goodbye / affirmations
    if re.search(r"\b(hi|hello|hey)\b", t):
        return "greeting"
    if re.search(r"\b(bye|goodbye|see you)\b", t):
        return "goodbye"
    if AFFIRM_RX.match(t):
        return "affirm"

    # default
    return "fallback"

# -------------------------
# Entity extraction
# -------------------------
def extract_entities(text: str) -> Dict[str, Any]:
    ents: Dict[str, Any] = {}
    mins = _minutes(text or "")
    if mins:
        ents["duration_min"] = mins

    # extract rewrite body "rewrite/paraphrase kindly: <text>"
    m = re.match(r"\s*(?:rewrite|paraphrase)\s+kindly\s*:\s*(.+)$", text or "", re.I)
    if m:
        ents["rewrite_text"] = m.group(1).strip()

    return ents
