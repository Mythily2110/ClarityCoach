# app.py — ClarityCoach (single-page) ============================================
# - Login + Sign-up (local SQLite + bcrypt)
# - Sidebar: Chat · Timer · Journal
# - Single chat input + chips that auto-send
# - Empathy + OFFER state machine (timer or journal)
# - 7-day streak from journal
# - Timer & Journal sections preserved
# ===============================================================================

from __future__ import annotations

import re
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import streamlit as st
from dotenv import load_dotenv
from passlib.hash import argon2
pw_hash = argon2.hash(password)
ok = argon2.verify(password, hash_from_db)



# ---- core modules (must be above any call that uses them) ----------------------
from core.dialog import handle_turn          # your deterministic NLU/logic
from core.tools import timer                 # FocusTimer singleton (start/pause/resume/stop)
from core.memory import init_db, add_journal, get_journals
from core.analytics import init_logs

# ------------------------------------------------------------------------------
# App config / assets
# ------------------------------------------------------------------------------
load_dotenv()
st.set_page_config(page_title="ClarityCoach", page_icon="🧭", layout="centered")

# Optional custom CSS
_css_path = Path("assets/style.css")
if _css_path.exists():
    st.markdown(f"<style>{_css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# AUTH (SQLite + bcrypt, 6–72 bytes passwords)
# ------------------------------------------------------------------------------
USERS_DB = Path("data/users.db")
USERS_DB.parent.mkdir(parents=True, exist_ok=True)

BCRYPT_MAX = 72  # bcrypt hashes max 72 bytes; we'll cap and validate

def _cap_utf8(s: str, limit: int = BCRYPT_MAX) -> str:
    """Truncate a string so its UTF-8 encoding is <= limit bytes."""
    if s is None:
        return ""
    b = s.encode("utf-8")
    if len(b) <= limit:
        return s
    # remove trailing characters until <= limit bytes
    while len(b) > limit and s:
        s = s[:-1]
        b = s.encode("utf-8")
    return s

def _auth_conn():
    return sqlite3.connect(USERS_DB)

def init_auth_db():
    with _auth_conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username   TEXT PRIMARY KEY,
                full_name  TEXT NOT NULL,
                pw_hash    TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()

def user_exists(username: str) -> bool:
    if not username:
        return False
    with _auth_conn() as con:
        cur = con.execute("SELECT 1 FROM users WHERE username = ?", (username.strip().lower(),))
        return cur.fetchone() is not None

def create_user(username: str, full_name: str, password: str) -> tuple[bool, str]:
    """
    Returns (ok, message).
    Validates username format, password 6..72 bytes, and duplicates.
    """
    u = (username or "").strip().lower()
    name = (full_name or "").strip()
    pw = (password or "")

    if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", u):
        return False, "Usernames must be 3–32 chars: letters, numbers, or _ only."
    if not name:
        return False, "Please enter your full name."
    if len(pw.encode("utf-8")) < 6:
        return False, "Password too short (min 6 characters)."
    if len(pw.encode("utf-8")) > BCRYPT_MAX:
        return False, f"Password too long (max {BCRYPT_MAX} bytes). Please shorten it."
    if user_exists(u):
        return False, "That username is already taken."

    pw_hash = bcrypt.hash(_cap_utf8(pw, BCRYPT_MAX))
    with _auth_conn() as con:
        con.execute(
            "INSERT INTO users (username, full_name, pw_hash) VALUES (?, ?, ?)",
            (u, name, pw_hash),
        )
        con.commit()
    return True, "Account created."

def verify_login(username: str, password: str) -> tuple[bool, str, str]:
    """
    Returns (ok, message, full_name). ok=True if verified.
    Caps password to 72 bytes before verify.
    """
    u = (username or "").strip().lower()
    pw = (password or "")
    if not u or not pw:
        return False, "Enter username and password.", ""

    with _auth_conn() as con:
        cur = con.execute("SELECT full_name, pw_hash FROM users WHERE username = ?", (u,))
        row = cur.fetchone()
        if not row:
            return False, "User not found.", ""

    full_name, pw_hash = row
    ok = bcrypt.verify(_cap_utf8(pw, BCRYPT_MAX), pw_hash)
    if not ok:
        return False, "Incorrect password.", ""
    return True, "Signed in.", full_name

def auth_gate():
    """Render login/signup and stop until authenticated."""
    st.title("🧭 ClarityCoach — Student Mental-Health Chatbot")
    st.caption("Not medical advice. If you're in crisis, call your local emergency number or 988 in the US.")
    st.divider()

    tab_login, tab_signup = st.tabs(["Login", "Sign up"])

    with tab_login:
        st.subheader("Login")
        u = st.text_input("Username", key="auth_login_user")
        p = st.text_input("Password", type="password", key="auth_login_pass")
        if st.button("Sign in", type="primary", use_container_width=True):
            ok, msg, name = verify_login(u, p)
            if ok:
                st.session_state["user"] = {"username": u.strip().lower(), "name": name}
                st.success(f"Welcome back, {name}!")
                st.rerun()
            else:
                st.error(msg)

    with tab_signup:
        st.subheader("Create a new account")
        su_name = st.text_input("Full name", key="auth_signup_name")
        su_user = st.text_input("Username (letters/numbers/_)", key="auth_signup_user")
        su_pass = st.text_input("Password (6–72 bytes)", type="password", key="auth_signup_pass")

        # Live byte-length hint
        if su_pass:
            bytelen = len(su_pass.encode("utf-8"))
            if bytelen > BCRYPT_MAX:
                st.warning(f"Password is {bytelen} bytes (> {BCRYPT_MAX}). Please shorten it.")

        if st.button("Create account", use_container_width=True):
            ok, msg = create_user(su_user, su_name, su_pass)
            if ok:
                st.success("Account created. You can sign in now.")
            else:
                st.warning(msg)

    st.stop()

# ------------------------------------------------------------------------------
# Boot order
# ------------------------------------------------------------------------------
init_db()
init_logs()
init_auth_db()

# Gate: stop here until the user logs in
if "user" not in st.session_state:
    auth_gate()

# ------------------------------------------------------------------------------
# Sidebar (nav + logout)
# ------------------------------------------------------------------------------
if "section" not in st.session_state:
    st.session_state.section = "Chat"

with st.sidebar:
    # identity
    if "user" in st.session_state:
        user = st.session_state["user"]
        st.markdown(f"**Signed in as:** {user['name']} (`{user['username']}`)")

    # navigation
    st.header("☰ Sections")
    st.session_state.section = st.radio(
        "Go to", ["Chat", "Timer", "Journal"],
        index=["Chat", "Timer", "Journal"].index(st.session_state.section),
        label_visibility="collapsed"
    )
    st.caption("Tip: You can also control everything via chat (e.g., “start a 25 minute focus timer”).")

    # logout
    if st.button("Log out"):
        st.session_state.pop("user", None)
        st.session_state.pop("history", None)  # clear chat transcript
        st.rerun()

# ------------------------------------------------------------------------------
# Helpers: streak, mood, empathy, tag hints
# ------------------------------------------------------------------------------
def compute_7day_streak_from_journal() -> int:
    rows = get_journals(limit=500)
    days_with_entry = {j.ts.date() for j in rows}
    streak = 0
    cur = datetime.now().date()
    while cur in days_with_entry:
        streak += 1
        cur = cur - timedelta(days=1)
    return streak

MOOD_PATTERNS = {
    "anxious":  re.compile(r"\b(anxious|anxiety|panic|panic attack|nervous)\b", re.I),
    "sad":      re.compile(r"\b(sad|down|depressed|low mood|hopeless)\b", re.I),
    "stressed": re.compile(r"\b(stress(ed)?|overwhelmed|burn(ed)? ?out|too much)\b", re.I),
    "lonely":   re.compile(r"\b(lonely|alone|isolated)\b", re.I),
    "unwell":   re.compile(r"\b(not feeling well|feel unwell|sick|ill|not ok|not okay)\b", re.I),
}

def detect_mood(text: str) -> Optional[str]:
    for label, rx in MOOD_PATTERNS.items():
        if rx.search(text):
            return label
    return None

def empathetic_reply(mood: str, user_text: str) -> str:
    steps = {
        "anxious": [
            "Try the 4-7-8 breath once: inhale 4s, hold 7s, exhale 8s.",
            "Write your top worry, then a 10-minute 'first step' you can do now."
        ],
        "sad": [
            "Do one gentle thing: water, 60s stretch, or open a window.",
            "Note one small win from today (even tiny)."
        ],
        "stressed": [
            "Quick brain-dump for 2 minutes to park everything.",
            "Pick a 10-minute task and start a timer—progress beats perfection."
        ],
        "lonely": [
            "Send a 'thinking of you' message to one person.",
            "Sit near people (library/cafe) 15–20 minutes for ambient connection."
        ],
        "unwell": [
            "Drink water and rest a little; lighten the plan today.",
            "When ready, try a 10-minute easy task."
        ],
    }
    s = steps.get(mood, [
        "Take one slow breath (4-4-6), then name what you feel.",
        "Pick one small next step that helps Future-You."
    ])
    title = {
        "anxious": "It makes sense to feel anxious.",
        "sad": "I'm really sorry you're feeling low.",
        "stressed": "That sounds like a lot to carry.",
        "lonely": "Feeling disconnected can really sting.",
        "unwell": "Sorry you're not feeling well today.",
    }.get(mood, "I'm listening.")
    return (
        f"**{title}**\n\n"
        f"I’m here with you. Two tiny moves you can try now:\n"
        f"1) {s[0]}\n"
        f"2) {s[1]}\n\n"
        f"If you like, I can **start a focus timer** or **add a quick journal note**."
    )

def tag_hints(text: str) -> List[str]:
    tags = []
    lower = text.lower()
    if any(k in lower for k in ["exam", "test", "quiz", "assignment"]): tags.append("exams")
    if "sleep" in lower or "tired" in lower: tags.append("sleep")
    if "friend" in lower or "family" in lower: tags.append("relationships")
    if "focus" in lower or "distraction" in lower or "phone" in lower: tags.append("focus")
    if "anxiety" in lower or "panic" in lower: tags.append("anxiety")
    if "stress" in lower or "overwhelm" in lower: tags.append("stress")
    return tags[:3]

def _is_affirmation(t: str) -> bool:
    return re.fullmatch(r"\s*(sure|yes|yeah|yup|ok(?:ay)?|alright|please|go ahead)\.?\s*", t, flags=re.I) is not None

def _extract_minutes(t: str, default_min: int = 10) -> int:
    m = re.search(r"(\d+)\s*(min|minute|minutes|m)\b", t, re.I)
    return int(m.group(1)) if m else default_min

# ------------------------------------------------------------------------------
# Header
# ------------------------------------------------------------------------------
st.title("🧭 ClarityCoach — Student Mental-Health Chatbot")
st.caption("Not medical advice. If you're in crisis, call your local emergency number or 988 in the US.")
st.divider()

# ------------------------------------------------------------------------------
# SECTION: CHAT
# ------------------------------------------------------------------------------
CHAT_INPUT_KEY = "chat_input_main_v3"

if st.session_state.section == "Chat":
    # Streak pill
    streak = compute_7day_streak_from_journal()
    streak_text = f"🔥 {streak}-day streak" if streak > 0 else "Let’s start a streak today ✨"
    st.markdown(f"<div style='margin-bottom:.5rem; font-weight:600;'>{streak_text}</div>", unsafe_allow_html=True)

    # Chips → auto-fill + auto-send
    def _fill_and_send(txt: str):
        st.session_state[CHAT_INPUT_KEY] = txt
        st.session_state["__send_now"] = True
        st.rerun()

    c1, c2, c3, c4 = st.columns(4)
    c1.button("3-day exam plan", on_click=_fill_and_send,
              args=("I have an exam in 3 days. Make me a realistic 3-day study plan.",))
    c2.button("rewrite kindly", on_click=_fill_and_send,
              args=("rewrite kindly: I keep failing and feel discouraged",))
    c3.button("focus w/o phone", on_click=_fill_and_send,
              args=("tips to focus without my phone",))
    c4.button("summarize week", on_click=_fill_and_send,
              args=("summarize my week",))

    # Render transcript
    if "history" not in st.session_state:
        st.session_state.history = []
    for role, msg in st.session_state.history:
        st.chat_message("user" if role == "user" else "assistant").markdown(msg)

    # Single chat input
    prompt = st.chat_input("Tell me what's up… (e.g., start a 25 minute focus timer)", key=CHAT_INPUT_KEY)
    if st.session_state.pop("__send_now", False):
        prompt = st.session_state.get(CHAT_INPUT_KEY, "")

    # OFFER state machine:
    # - 'timer_or_journal' → the next input chooses timer or journal
    # - 'await_journal_text' → the next input is saved as a journal entry
    if prompt:
        st.chat_message("user").markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("…")

            # 1) Awaiting journal text: save it
            if st.session_state.get("pending_offer") == "await_journal_text":
                note = prompt.strip()
                if note:
                    add_journal(note)
                    reply = "Added to your journal. Want a weekly summary?"
                    st.session_state.pop("pending_offer", None)
                else:
                    reply = "Tell me the note to add and I’ll save it."
                placeholder.markdown(reply)

            # 2) Offered timer/journal: interpret choice or ask clarify
            elif st.session_state.get("pending_offer") == "timer_or_journal":
                txt = prompt.lower().strip()
                if "timer" in txt or "focus" in txt:
                    mins = _extract_minutes(prompt, default_min=10)
                    st.session_state.pop("pending_offer", None)
                    reply = handle_turn(f"start a {mins} minute focus timer")
                elif "journal" in txt or "note" in txt:
                    st.session_state["pending_offer"] = "await_journal_text"
                    reply = "Okay—what should I add to your journal?"
                elif _is_affirmation(prompt):
                    reply = "Great—should I **start a focus timer** (how many minutes?) or **add a journal note**?"
                else:
                    st.session_state.pop("pending_offer", None)
                    reply = handle_turn(prompt)
                placeholder.markdown(reply)

            # 3) Normal: empathy first, then set offer; otherwise route
            else:
                mood = detect_mood(prompt)
                if mood:
                    reply = empathetic_reply(mood, prompt)
                    st.session_state["pending_offer"] = "timer_or_journal"
                else:
                    reply = handle_turn(prompt)
                placeholder.markdown(reply)

        # persist transcript
        st.session_state.history.append(("user", prompt))
        st.session_state.history.append(("assistant", reply))
        st.rerun()

# ------------------------------------------------------------------------------
# SECTION: TIMER
# ------------------------------------------------------------------------------
if st.session_state.section == "Timer":
    st.subheader("⏱️ Focus Timer")
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
    with c1:
        mins = st.number_input("Minutes", min_value=1, max_value=120, value=25, step=1)
    with c2:
        if st.button("Start", use_container_width=True):
            timer.start(int(mins)); st.rerun()
    with c3:
        if timer.running and not timer.paused:
            if st.button("Pause", use_container_width=True): timer.pause(); st.rerun()
        elif timer.running and timer.paused:
            if st.button("Resume", use_container_width=True): timer.resume(); st.rerun()
        else:
            st.button("Pause", disabled=True, use_container_width=True)
    with c4:
        if st.button("Stop", use_container_width=True): timer.stop(); st.rerun()

    try:
        pct = int(timer.progress_ratio() * 100)
    except ZeroDivisionError:
        pct = 0
    st.progress(pct, text=f"{pct}% complete")
    if timer.running and not timer.paused:
        st.info(timer.status_text())
        time.sleep(1); st.rerun()
    elif timer.running and timer.paused:
        st.warning("Paused.")
    else:
        st.info("Timer is idle. Set minutes and press Start.")

# ------------------------------------------------------------------------------
# SECTION: JOURNAL
# ------------------------------------------------------------------------------
if st.session_state.section == "Journal":
    st.subheader("📒 Journal")
    st.caption("Write a quick note. The bot can summarize your week from your entries.")

    def _save_journal():
        text = st.session_state.get("journal_text", "").strip()
        if not text:
            st.session_state["__journal_msg"] = ("warn", "Write something before saving."); return
        add_journal(text)
        st.session_state["journal_text"] = ""
        st.session_state["__journal_msg"] = ("ok", "Saved to your journal.")

    def _summarize_week():
        st.session_state.setdefault("history", [])
        st.session_state["history"].append(("user", "summarize my week"))
        resp = handle_turn("summarize my week")
        st.session_state["history"].append(("assistant", resp))

    with st.expander("Guided prompts"):
        prompts = [
            "Gratitude: One thing I appreciated today was…",
            "Challenge: The hardest moment today was…",
            "Win: A small thing I did well was…",
        ]
        cols = st.columns(3)
        for i, p in enumerate(prompts):
            if cols[i].button(p):
                st.session_state["journal_text"] = (st.session_state.get("journal_text", "") + " " + p).strip()

    note = st.text_area(
        "Add a quick note",
        key="journal_text",
        placeholder="How are you feeling? What did you work on?"
    )

    colA, colB = st.columns(2)
    colA.button("Add to Journal", use_container_width=True, on_click=_save_journal)
    colB.button("Summarize my week", use_container_width=True, on_click=_summarize_week)

    if "__journal_msg" in st.session_state:
        kind, msg = st.session_state.pop("__journal_msg")
        (st.success if kind == "ok" else st.warning)(msg)

    st.markdown("### Recent entries")
    rows = get_journals(limit=10)
    if not rows:
        st.info("No entries yet. Try writing one line.")
    else:
        for j in rows:
            lower = j.text.lower()
            tags = []
            if any(k in lower for k in ["exam", "test", "quiz", "assignment"]): tags.append("exams")
            if "sleep" in lower or "tired" in lower: tags.append("sleep")
            if "focus" in lower or "distraction" in lower or "phone" in lower: tags.append("focus")
            if "anxiety" in lower or "panic" in lower: tags.append("anxiety")
            if "stress" in lower or "overwhelm" in lower: tags.append("stress")
            hint = f"  \n<span style='opacity:.7'>tags: {', '.join(tags)}</span>" if tags else ""
            st.markdown(f"**{j.ts:%Y-%m-%d %H:%M}** — {j.text}{hint}", unsafe_allow_html=True)
