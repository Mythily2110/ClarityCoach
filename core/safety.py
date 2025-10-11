import re
CRISIS = re.compile(r"(suicide|kill myself|end my life|self-harm|overdose)", re.I)

def safety_check(text: str):
    if CRISIS.search(text):
        return {
            "action": "escalate",
            "message": ("I'm really sorry you're feeling this way. "
                        "If you're in immediate danger, call your local emergency number. "
                        "You can reach the **988 Suicide & Crisis Lifeline (US)** by dialing 988 or visiting 988lifeline.org.")
        }
    return {"action": "ok"}
