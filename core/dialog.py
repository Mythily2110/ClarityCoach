from typing import List
from .nlu import detect_intent, extract_entities
from .rag import tips_for_focus_phone, tips_for_stress, kb_search_unique
from .tools import timer as TIMER
from .memory import add_journal, get_journals

# -------------------------------------------------------------------
# Small, deterministic helpers (no API key)
# 
# -
# 
#------------------------------------------------------------------
def _exam_study_plan() -> str:
    return (
        "**3-Day Realistic Study Plan 📘**\n\n"
        "Here’s a focused approach you can start today:\n\n"
        "**Day 1 – Understand & Review Basics**\n"
        "• Go through all key topics once quickly.\n"
        "• Mark areas that feel confusing.\n"
        "• Take short notes in your own words.\n\n"
        "**Day 2 – Practice & Strengthen**\n"
        "• Do sample questions or mock tests on weak areas.\n"
        "• Use active recall (test yourself, don’t just reread).\n"
        "• Revise formulas / concepts you missed yesterday.\n\n"
        "**Day 3 – Final Review & Calm Prep**\n"
        "• Skim through summaries and key notes only.\n"
        "• Sleep early, eat well, and avoid last-minute cramming.\n"
        "• Spend 10-15 minutes visualizing success.\n\n"
        "🧠 *Tip:* Use 25-minute Pomodoro blocks, then rest 5 minutes. "
        "You can say “start a 25 minute focus timer” if you want me to time it."
    )

def _focus_no_phone_tips() -> str:
    return (
        "**Phone-free focus ideas**\n\n"
        "• Put the phone in another room; if needed, use Do Not Disturb or airplane mode.\n"
        "• Use a site blocker on laptop (e.g., block socials for 30–60 minutes).\n"
        "• Work in short sprints: 20–30 minutes, then a 5-minute stretch/water break.\n"
        "• Keep only one tab/app visible; full-screen the work window.\n"
        "• Prepare a zero-friction start: write a 1-line next action and begin there.\n"
        "• If urges hit, jot them on a 'later list' instead of picking up the phone.\n\n"
        "_If you like, say something like 'start a 25 minute focus timer' and I’ll run it._"
    )

def _rewrite_kindly(txt: str) -> str:
    """Very small, safe paraphraser to make text gentler without LLMs."""
    if not txt:
        return "Here’s a gentler way to put that: I’m having a hard time right now, but I’m learning and trying again."
    s = txt.strip()
    # soften a few harsh words
    replacements = {
        "stupid": "discouraged",
        "idiot": "really frustrated",
        "fail": "not going as planned",
        "failing": "not going the way I hoped",
        "hopeless": "really tough",
        "useless": "stuck",
    }
    out = s
    for k, v in replacements.items():
        out = out.replace(k, v).replace(k.capitalize(), v)

    return (
        "Here’s a kinder way to put that:\n\n"
        f"**“{out}.”**\n\n"
        "You’re not alone—progress is messy. What’s one tiny step you could try next?"
    )

def _weekly_summary(limit: int = 50) -> str:
    rows = list(get_journals(limit=limit))
    if not rows:
        return "No journal entries yet. Try writing a one-line note each day—then I can summarize your week."

    # very small heuristic summary
    days = sorted({j.ts.date() for j in rows})
    total = len(rows)
    latest = max(j.ts for j in rows)
    example = rows[-1].text[:120].replace("\n", " ")

    # tag hints
    tags = []
    for j in rows:
        t = j.text.lower()
        if any(k in t for k in ["exam", "test", "quiz", "assignment"]) and "exams" not in tags: tags.append("exams")
        if ("sleep" in t or "tired" in t) and "sleep" not in tags: tags.append("sleep")
        if ("focus" in t or "phone" in t or "distraction" in t) and "focus" not in tags: tags.append("focus")
        if ("anxiety" in t or "panic" in t) and "anxiety" not in tags: tags.append("anxiety")
        if ("stress" in t or "overwhelm" in t) and "stress" not in tags: tags.append("stress")

    parts = [
        f"**This week at a glance**",
        f"- {total} entries across {len(days)} day(s). Latest entry: {latest:%a %b %d %H:%M}.",
        f"- Common themes: {', '.join(tags) if tags else 'varied'}.",
        f"- Recent note: _{example}…_",
        "",
        "**Tiny next steps**",
        "- Keep a one-line journal daily for momentum.",
        "- Run one 10–25 minute focus block on something that matters.",
        "- If stressed: brain-dump for 2 minutes, then choose one small next move.",
    ]
    return "\n".join(parts)

# -------------------------------------------------------------------
# Main turn handler
# -------------------------------------------------------------------

def handle_turn(user_text: str) -> str:
    intent = detect_intent(user_text)
    ents = extract_entities(user_text)

    # Timer tools
    if intent == "pomodoro_start":
        mins = ents.get("duration_min") or 25
        TIMER.start(int(mins))
        return f"Started a **{int(mins)}-minute** focus timer."
    if intent == "pomodoro_stop":
        TIMER.stop()
        return "Stopped the timer."
    if intent == "pomodoro_status":
        pct = int(TIMER.progress_ratio() * 100)
        return f"{pct}% complete. {TIMER.status_text()}"
    if intent == "focus_tips_phonefree":
        return _focus_no_phone_tips()
    if intent == "exam_study_plan":
        return _exam_study_plan()

    # Journal
    if intent == "journal_add":
        add_journal(user_text)
        return "Added to your journal. Want a weekly summary?"
    if intent == "journal_summary":
        return _weekly_summary()

    # Tips (no duplicates, clean formatting)
    if intent == "focus_phone_tips":
        tips = tips_for_focus_phone()
        return "**Focus without your phone — quick playbook**\n\n" + "\n".join(f"- {t}" for t in tips)
    if intent == "stress_tips":
        tips = tips_for_stress()
        return "**Handling stress — try these**\n\n" + "\n".join(f"- {t}" for t in tips)

    # Rewrite kindly
    if intent == "rewrite_kindly":
        txt = ents.get("rewrite_text") or user_text.split(":", 1)[-1]
        return _rewrite_kindly(txt)

    # Greeting/Goodbye
    if intent == "greeting":
        return "Hi! I can help with focus routines, journaling, quick tips, or a weekly summary."
    if intent == "goodbye":
        return "Take care! Come back anytime."

    # Fallback: retrieve 3 focused snippets, unique and clean
    chunks = kb_search_unique(user_text, k=3)
    if chunks:
        return "\n\n".join(chunks) + "\n\n*Want me to tailor a tiny 3-step plan for today?*"
    return "I’m not fully sure yet, but I can help you set a 10-minute focus block or record a one-line journal."
