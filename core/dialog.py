import re
from typing import List, Dict, Set

RISK = re.compile(r"\b(suicide|kill myself|end it all|want to die|self[- ]harm|cutting)\b", re.I)
PANIC = re.compile(r"\b(panic attack|can.?t breathe|heart racing|chest tight|dizzy|hyperventilat)\b", re.I)
HEALTH_ALERT = re.compile(r"\b(chest pain|severe headache|fainting|passed out|stroke|seizure)\b", re.I)

INTENT_PATTERNS = {
    "anxiety_worry": r"\b(anxious|anxiety|worry|worried|panic|nervous|overthink)\b",
    "low_mood_depression": r"\b(depressed|worthless|useless|empty|numb|hopeless)\b",
    "stress_overwhelm": r"\b(stress(ed)?|overwhelmed|burn(?:ed)?\s*out|too much|exhausted)\b",
    "loneliness_isolation": r"\b(lonely|alone|isolated|no one cares)\b",
    "relationship_conflict": r"\b(boyfriend|girlfriend|partner|spouse|breakup|argu(?:e|ment)|fight)\b",
    "work_school_performance": r"\b(manager|boss|work|salary|deadline|job|exam|quiz|assignment|grade|professor|class)\b",
    "financial_stress": r"\b(rent|bills?|loan|debt|tuition|money)\b",
    "sleep_issue": r"\b(sleep|insomnia|can.?t sleep|nightmare|wake up|tired)\b",
    "boredom_motivation": r"\b(bored|no motivation|can.?t start|stuck)\b",
    "planning_productivity": r"\b(plan|schedule|timer|focus|pomodoro|study plan)\b",
    "gratitude_reflection": r"\b(grateful|gratitude|appreciate)\b",
    "small_talk": r"\b(hi|hello|hey|how are you|what.?s up)\b",
}

def detect_intents(text: str) -> List[str]:
    text_l = text.lower()
    if RISK.search(text_l):
        return ["crisis_risk"]
    if PANIC.search(text_l):
        return ["panic_attack"]
    if HEALTH_ALERT.search(text_l):
        return ["health_concern"]

    found: List[str] = []
    for k, pattern in INTENT_PATTERNS.items():
        if re.search(pattern, text_l, re.I):
            found.append(k)

    # pick up to 2 most helpful
    # prioritize emotional + situational over small_talk
    priority = [
        "anxiety_worry","low_mood_depression","stress_overwhelm","loneliness_isolation",
        "relationship_conflict","work_school_performance","financial_stress","sleep_issue",
        "boredom_motivation","planning_productivity","gratitude_reflection","small_talk"
    ]
    found_sorted = [i for i in priority if i in found]
    return found_sorted[:2] or ["small_talk"]

def h_crisis(_: str) -> str:
    return (
        "**I’m really glad you reached out.** When things feel this heavy, please get immediate help.\n\n"
        "- If you’re in the US, call or text **988** (24/7). If outside the US, contact your local emergency number.\n"
        "- If you’d like, I can guide a 60-second grounding exercise right now."
    )

def h_panic(_: str) -> str:
    return (
        "**That sounds frightening. Let’s do a quick 60-second reset.**\n"
        "1) Breathe in 4 • hold 4 • out 6 — three times.\n"
        "2) Name 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, 1 you can taste.\n"
        "3) When ready, tell me one tiny next step (e.g., sip water, step outside for 1 minute)."
    )

def h_health(_: str) -> str:
    return (
        "Those symptoms can be serious. I’m not a medical service — please seek **medical advice now** or emergency care "
        "if symptoms are acute. I can stay with you through a short breathing exercise if that helps."
    )

def h_anxiety(text: str) -> str:
    return (
        "**It makes sense to feel keyed-up.** Two tiny moves:\n"
        "• Do a 2-minute brain-dump: write every worry without judging.\n"
        "• Pick one 10-minute task and start a focus timer. I can help you time it."
    )

def h_low_mood(text: str) -> str:
    return (
        "**I’m sorry you’re feeling low.** Try one gentle action:\n"
        "• Water, stretch, or sit near daylight for 2 minutes.\n"
        "• Note one small thing you handled today. I can save it to your journal."
    )

def h_stress(text: str) -> str:
    return (
        "**That’s a lot to carry.** Let’s shrink it:\n"
        "• List the top 3 tasks. Circle just one and do a 10-minute starter.\n"
        "• Batch the rest for later. Want me to start a 10-minute timer?"
    )

def h_lonely(text: str) -> str:
    return (
        "**Feeling disconnected can sting.** Two small ideas:\n"
        "• Send a simple ‘thinking of you’ text to one person.\n"
        "• Sit near people (library/café) for 15–20 minutes."
    )

def h_relationship(text: str) -> str:
    return (
        "**Conflicts are draining.** Try this:\n"
        "• Write what you feel + what you need in one sentence each.\n"
        "• If you speak, use “when X happens, I feel Y. I need Z.”\n"
        "Want to store a draft in your journal?"
    )

def h_work_school(text: str) -> str:
    # if user mentions exam, call your existing exam plan function
    if re.search(r"\b(exam|quiz|test)\b", text, re.I):
        # <- call your current exam-plan helper if you have one
        return (
            "**Exam coming up?** I can make a 3-day study plan with short blocks.\n"
            "Say: *make me a realistic 3-day plan*."
        )
    # else default
    return (
        "**Work/school pressure is real.** Two tiny steps:\n"
        "• Write the next *visible* task (e.g., open slide deck, reply to John).\n"
        "• Start a 10-minute timer to just begin."
    )

def h_finance(text: str) -> str:
    return (
        "**Money stress is heavy.** Two quick moves:\n"
        "• Write a 3-number snapshot: rent/bills/free.\n"
        "• Email yourself a ‘mini-plan’ to call one resource tomorrow.\n"
        "I can save today’s note into your journal."
    )

def h_sleep(text: str) -> str:
    return (
        "**Sleep struggles compound everything.** Tonight:\n"
        "• Pick a 30-min wind-down: dim lights, screens away, warm shower.\n"
        "• Try 4-7-8 breathing in bed for 1 minute."
    )

def h_boredom(text: str) -> str:
    return (
        "**Let’s shake boredom.** Choose one 15-minute activity:\n"
        "• Walk & music • doodle/journal • tidy one small area • text a friend.\n"
        "Want me to start a 15-minute timer?"
    )

def h_planning(text: str) -> str:
    return (
        "**We can make a tiny plan.** Tell me one task and we’ll do a 10-minute focus block.\n"
        "I can also add a one-line journal after."
    )

def h_gratitude(text: str) -> str:
    return (
        "**Gratitude check-in.** Finish this: *One thing I appreciated today was…*\n"
        "Say it here and I’ll save it to your journal."
    )

def h_smalltalk(text: str) -> str:
    return "Hi! I’m here for chat or quick support. Tell me what’s on your mind, or say ‘start a 10-minute timer’."

INTENT_HANDLERS = {
    "crisis_risk": h_crisis,
    "panic_attack": h_panic,
    "health_concern": h_health,
    "anxiety_worry": h_anxiety,
    "low_mood_depression": h_low_mood,
    "stress_overwhelm": h_stress,
    "loneliness_isolation": h_lonely,
    "relationship_conflict": h_relationship,
    "work_school_performance": h_work_school,
    "financial_stress": h_finance,
    "sleep_issue": h_sleep,
    "boredom_motivation": h_boredom,
    "planning_productivity": h_planning,
    "gratitude_reflection": h_gratitude,
    "small_talk": h_smalltalk,
}

def handle_turn(user_text: str) -> str:
    intents = detect_intents(user_text)

    # hard priorities already enforced in detect_intents
    if intents == ["crisis_risk"]:
        return INTENT_HANDLERS["crisis_risk"](user_text)
    if intents == ["panic_attack"]:
        return INTENT_HANDLERS["panic_attack"](user_text)
    if intents == ["health_concern"]:
        return INTENT_HANDLERS["health_concern"](user_text)

    # combine up to two skills concisely
    msgs = []
    for it in intents:
        fn = INTENT_HANDLERS.get(it)
        if fn:
            msgs.append(fn(user_text))
    # Join compactly (keep it short)
    return "\n\n".join(msgs[:2])
