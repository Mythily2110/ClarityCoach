# app.py — ClarityCoach (Chat • Timer • Journal) with bcrypt login
from __future__ import annotations

import re
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv
from passlib.hash import bcrypt  # ✅ use ONE algorithm consistently

# --- core modules from your project ---
from core.dialog import handle_turn
from core.tools import timer
from core.memory import init_db, add_journal, get_journals
from core.analytics import init_logs

# -----------------------------------------------------------------------------
# App config
# -----------------------------------------------------------------------------
load_dotenv()
st.set_page_config(page_title="ClarityCoach", page_icon="🧭", layout="centered")

# Optional CSS
css = Path("assets/style.css")
if css.exists():
    st.markdown(f"<style>{css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# Single chat input key (avoid duplicate-key errors)
CHAT_INPUT_KEY = "chat_input_main_v2"

# -----------------------------------------------------------------------------
# Auth (SQLite + Passlib/bcrypt)
# -----------------------------------------------------------------------------
AUTH_DB = Path("auth.db").resolve()


def _auth_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(AUTH_DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "username TEXT UNIQUE NOT NULL,"
        "name TEXT NOT NULL,"
        "pw_hash TEXT NOT NULL,"
        "created_at TEXT NOT NULL)"
    )
    return conn


def init_auth_db() -> None:
    _auth_conn().close()


def create_user(username: str, name: str, password: str) -> Tuple[bool, str]:
    username = username.strip()
    name = name.strip()
    if not username or not name or not password:
        return False, "Please fill all fields."

    # ✅ hash INSIDE the function (no top-level password usage)
    pw_hash = bcrypt.hash(password)

    try:
        conn = _auth_conn()
        with conn:
            conn.execute(
                "INSERT INTO users(username, name, pw_hash, created_at) "
                "VALUES (?, ?, ?, ?)",
                (username, name, pw_hash, datetime.utcnow().isoformat(timespec="seconds")),
            )
        return True, "Account created. You can sign in now."
    except sqlite3.IntegrityError:
        return False, "That username already exists."
    finally:
        conn.close()


def get_user(username: str) -> Optional[Tuple[int, str, str, str, str]]:
    conn = _auth_conn()
    try:
        cur = conn.execute(
            "SELECT id, username, name, pw_hash, created_at FROM users WHERE username=?",
            (username.strip(),),
        )
        row = cur.fetchone()
        return row
    finally:
        conn.close()


def verify_login(username: str, password: str) -> Tuple[bool, str, Optional[str]]:
    row = get_user(username)
    if not row:
        return False, "No such user.", None
    _, _, name, pw_hash, _ = row
    try:
        ok = bcrypt.verify(password, pw_hash)
    except Exception:
        return False, "Password check failed.", None
    return (True, "OK", name) if ok else (False, "Invalid credentials.", None)


def auth_gate() -> None:
    st.header("Sign in")
    with st.form("login_form", clear_on_submit=False):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in", use_container_width=True)

    if submit:
        ok, msg, name = verify_login(u, p)
        if ok:
            st.session_state["user"] = {"username": u, "name": name}
            st.success(f"Welcome, {name}!")
            st.rerun()
        else:
            st.error(msg)

    with st.expander("Create account"):
        su_user = st.text_input("New username", key="__su_user")
        su_name = st.text_input("Display name", key="__su_name")
        su_pass = st.text_input("New password", type="password", key="__su_pass")
        if st.button("Create account", use_container_width=True):
            ok, msg = create_user(su_user, su_name, su_pass)
            (st.success if ok else st.warning)(msg)
            if ok:
                st.info("Sign in above when ready.")

# -----------------------------------------------------------------------------
# Helpers for Chat page
# -----------------------------------------------------------------------------
def compute_7day_streak_from_journal() -> int:
    rows = get_journals(limit=500)
    days = {j.ts.date() for j in rows}
    streak = 0
    cur = datetime.now().date()
    while cur in days:
        streak += 1
        cur = cur - timedelta(days=1)
    return streak


MOOD_PATTERNS = {
    "anxious": re.compile(r"\b(anxious|anxiety|panic|nervous)\b", re.I),
    "sad": re.compile(r"\b(sad|depressed|low mood|hopeless)\b", re.I),
    "stressed": re.compile(
        r"\b(stress(ed)?|overwhelmed|burn(?:ed)?\s*out|too much|"
        r"exhaust(?:ed|ion)|tired|fatigued|drained)\b",
        re.I,
    ),
    "lonely": re.compile(r"\b(lonely|alone|isolated)\b", re.I),
}


def detect_mood(text: str) -> Optional[str]:
    for label, rgx in MOOD_PATTERNS.items():
        if rgx.search(text):
            return label
    return None


def empathetic_reply(mood: str, user_text: str) -> str:
    steps = {
        "anxious": [
            "Try 4-7-8 breathing once.",
            "Write the top worry and a 10-minute first step.",
        ],
        "sad": [
            "Do one gentle thing: water, stretch, or step outside.",
            "Note one small win from today.",
        ],
        "stressed": [
            "Dump everything into a quick 2-minute brain-dump.",
            "Pick a single 10-minute task and start a timer.",
        ],
        "lonely": [
            "Send a 'thinking of you' message to one person.",
            "Sit near people (library/cafe) for 15–20 minutes.",
        ],
    }
    s = steps.get(mood, ["Take a slow 4-4-6 breath.", "Pick a tiny next step."])
    title = {
        "anxious": "It makes sense to feel anxious.",
        "sad": "I'm sorry you're feeling low.",
        "stressed": "That sounds like a lot to carry.",
        "lonely": "Feeling disconnected can sting.",
    }.get(mood, "I'm listening.")
    return (
        f"**{title}**\n\n"
        f"Two tiny moves to try:\n"
        f"1) {s[0]}\n"
        f"2) {s[1]}\n\n"
        f"If it helps, I can start a 10-minute focus timer or add a quick journal note."
    )

def tag_hints(text: str) -> List[str]:
    tags = []
    t = text.lower()
    if any(k in t for k in ["exam", "quiz", "assignment"]):
        tags.append("exams")
    if "sleep" in t or "tired" in t:
        tags.append("sleep")
    if any(k in t for k in ["focus", "distraction", "phone"]):
        tags.append("focus")
    if "anxiety" in t or "panic" in t:
        tags.append("anxiety")
    if "stress" in t or "overwhelm" in t:
        tags.append("stress")
    return tags[:3]

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
st.title("🧭 ClarityCoach — Student Mental-Health Chatbot")
st.caption("Not medical advice. If you're in crisis, call your local emergency number or 988 in the US.")
st.divider()

# -----------------------------------------------------------------------------
# Init stores
# -----------------------------------------------------------------------------
init_db()
init_logs()
init_auth_db()

# -----------------------------------------------------------------------------
# Auth gate
# -----------------------------------------------------------------------------
if "user" not in st.session_state:
    auth_gate()
    st.stop()

# -----------------------------------------------------------------------------
# Sidebar navigation
# -----------------------------------------------------------------------------
if "section" not in st.session_state:
    st.session_state.section = "Chat"

with st.sidebar:
    st.header("☰ Sections")
    st.session_state.section = st.radio(
        "Go to",
        ["Chat", "Timer", "Journal"],
        index=["Chat", "Timer", "Journal"].index(st.session_state.section),
        label_visibility="collapsed",
    )
    user = st.session_state["user"]
    st.markdown(f"**Signed in as:** {user['name']} (`{user['username']}`)")
    if st.button("Log out"):
        st.session_state.pop("user", None)
        st.rerun()

# -----------------------------------------------------------------------------
# CHAT
# -----------------------------------------------------------------------------
if st.session_state.section == "Chat":
    streak = compute_7day_streak_from_journal()
    pill = f"🔥 {streak}-day streak" if streak else "Let’s start a streak ✨"
    st.markdown(f"<div style='font-weight:600;margin-bottom:.5rem'>{pill}</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    def _fill_and_send(txt: str):
        st.session_state[CHAT_INPUT_KEY] = txt
        st.session_state["__send_now"] = True
        st.rerun()

    c1.button("3-day exam plan", on_click=_fill_and_send,
              args=("I have an exam in 3 days. Make me a realistic 3-day study plan.",),
              use_container_width=True)
    c2.button("rewrite kindly", on_click=_fill_and_send,
              args=("rewrite kindly: I keep failing and feel stupid",),
              use_container_width=True)
    c3.button("focus w/o phone", on_click=_fill_and_send,
              args=("tips to focus without my phone",),
              use_container_width=True)
    c4.button("summarize week", on_click=_fill_and_send,
              args=("summarize my week",),
              use_container_width=True)

    # previous turns
    if "history" not in st.session_state:
        st.session_state.history = []

    for role, msg in st.session_state.history:
        st.chat_message("user" if role == "user" else "assistant").markdown(msg)

    prompt = st.chat_input("Tell me what's up… (e.g., start a 25 minute focus timer)", key=CHAT_INPUT_KEY)
    if st.session_state.pop("__send_now", False):
        prompt = st.session_state.get(CHAT_INPUT_KEY, "")

    if prompt:
        st.chat_message("user").markdown(prompt)
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("…")

            mood = detect_mood(prompt)
            if mood:
                reply = empathetic_reply(mood, prompt)
            else:
                reply = handle_turn(prompt)  # your NLU/LLM routing

            placeholder.markdown(reply)

        st.session_state.history.append(("user", prompt))
        st.session_state.history.append(("assistant", reply))
        st.rerun()

# -----------------------------------------------------------------------------
# TIMER
# -----------------------------------------------------------------------------
if st.session_state.section == "Timer":
    st.subheader("⏱️ Focus Timer")
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
    with c1:
        mins = st.number_input("Minutes", min_value=1, max_value=120, value=25, step=1)
    with c2:
        if st.button("Start", use_container_width=True):
            timer.start(int(mins))
            st.rerun()
    with c3:
        if timer.running and not timer.paused:
            if st.button("Pause", use_container_width=True):
                timer.pause()
                st.rerun()
        elif timer.running and timer.paused:
            if st.button("Resume", use_container_width=True):
                timer.resume()
                st.rerun()
        else:
            st.button("Pause", disabled=True, use_container_width=True)
    with c4:
        if st.button("Stop", use_container_width=True):
            timer.stop()
            st.rerun()

    pct = int(timer.progress_ratio() * 100)
    st.progress(pct, text=f"{pct}% complete")
    if timer.running and not timer.paused:
        st.info(timer.status_text())
        time.sleep(1)
        st.rerun()
    elif timer.running and timer.paused:
        st.warning("Paused.")
    else:
        st.info("Timer is idle. Set minutes and press Start.")

# -----------------------------------------------------------------------------
# JOURNAL
# -----------------------------------------------------------------------------
if st.session_state.section == "Journal":
    st.subheader("📒 Journal")
    st.caption("Write a quick note. The bot can summarize your week from your entries.")

    def _save_journal():
        text = st.session_state.get("journal_text", "").strip()
        if not text:
            st.session_state["__journal_msg"] = ("warn", "Write something before saving.")
            return
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
                st.session_state["journal_text"] = (
                    (st.session_state.get("journal_text", "") + " " + p).strip()
                )

    note = st.text_area(
        "Add a quick note",
        key="journal_text",
        placeholder="How are you feeling? What did you work on?",
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
            tags = tag_hints(j.text)
            hint = f"  \n<span style='opacity:.7'>tags: {', '.join(tags)}</span>" if tags else ""
            st.markdown(f"**{j.ts:%Y-%m-%d %H:%M}** — {j.text}{hint}", unsafe_allow_html=True)
