# ClarityCoach (Fresh LLM Chatbot Scaffold)

A clean, production‑minded scaffold for a chatbot with:
- NLU (intents/entities) • Dialogue manager (policies) • RAG (vector search)
- LLM abstraction (OpenAI/Anthropic/local) • Tools/Function calling
- Safety guardrails • Journaling & persistence • Analytics hooks

## Quickstart
1) Create a venv (optional) and install deps:
```
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```
2) Copy `.env.example` to `.env` and (optionally) set API keys + models.
3) Run the app:
```
streamlit run app.py
```
4) Drop your knowledge files (.txt/.md) into `data/kb/`.

## Milestones
- M1: Core plumbing (runs locally with small models)
- M2: Intent taxonomy + entity extraction
- M3: RAG grounding (MiniLM + FAISS)
- M4: Tool actions (pomodoro, journaling)
- M5: Safety & escalation
- M6: Metrics & evals
- M7: Deploy (Hugging Face Spaces / Streamlit Cloud / Docker)
