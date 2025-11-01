# 🧭 ClarityCoach — Student Mental-Health Chatbot

ClarityCoach is a lightweight Streamlit app that combines:
- **Chat** (empathetic replies + optional LLM backends),
- **Focus Timer**, and
- **Journal** with simple analytics,

…wrapped with a minimal **SQLite + Passlib (bcrypt)** login system.

> **Note**: ClarityCoach is not medical advice. If you’re in crisis, call your local emergency number or 988 in the US.

---

## ✨ Features

- 🔐 **Auth**: Local SQLite user store with bcrypt hashing  
- 💬 **Chat**: Deterministic rules + plug-in hooks for LLMs (OpenAI / Anthropic optional)  
- ⏱️ **Timer**: Start/Pause/Resume/Stop + progress  
- 📒 **Journal**: Save entries and view recent notes  
- 🧠 **Mood hints**: Quick regex-based mood tags (anxious/sad/stressed/lonely)  
- 🧩 **Modular core**: `core/` holds dialog, memory, analytics, tools

---

## 🧱 Project Structure


> **Important:** Utility modules should define functions only—**no network calls or DB writes at import time**. Call them from `app.py` after the user triggers an action.

---

## 🚀 Quick Start

### 1) Create & activate a virtual env
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
