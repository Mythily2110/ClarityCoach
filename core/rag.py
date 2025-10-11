from typing import List
import json
from pathlib import Path

KB_PATH = Path("data/kb.json")  # optional small JSON knowledge base

def _load_kb() -> List[dict]:
    if KB_PATH.exists():
        try:
            return json.loads(KB_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _unique(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for s in seq:
        s2 = " ".join(s.split())
        if s2 not in seen:
            seen.add(s2)
            out.append(s)
    return out

# Pre-baked tip sets (deterministic, small, clean)
def tips_for_focus_phone() -> List[str]:
    items = [
        "Put phone in another room; disable notifications.",
        "Full-screen your work; close unrelated tabs.",
        "Run 10–25 min blocks (Pomodoro 25/5); take real breaks.",
        "Write a 1-line target before you start.",
        "If stuck, start with a 10-minute 'quick win'.",
    ]
    return _unique(items)

def tips_for_stress() -> List[str]:
    items = [
        "2-minute brain-dump to park everything.",
        "Sort items: do now (<10m), schedule, or drop.",
        "Breathe 4-4-6 for one minute.",
        "Pick one tiny next step and start a 10-minute focus block.",
    ]
    return _unique(items)

def kb_search_unique(query: str, k: int = 3) -> List[str]:
    # Extremely light retrieval over local KB if present
    kb = _load_kb()
    q = query.lower()
    scored = []
    for row in kb:
        text = f"{row.get('title','')}: {row.get('body','')}".strip()
        score = sum(1 for w in q.split() if w in text.lower())
        if score:
            scored.append((score, text))
    scored.sort(reverse=True)
    top = [t for _, t in scored[:k]]
    return _unique(top)
