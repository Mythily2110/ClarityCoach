import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from transformers import pipeline

try:
    import openai
except Exception:
    openai = None

try:
    import anthropic
except Exception:
    anthropic = None

@dataclass
class LLMConfig:
    provider: str = os.getenv("LLM_PROVIDER", "local")
    model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Local small model fallback for summarization/paraphrase
_local_summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
_local_t2t = pipeline("text2text-generation", model="t5-small")

def chat(messages: List[Dict[str, str]], cfg: Optional[LLMConfig] = None) -> str:
    cfg = cfg or LLMConfig()
    if cfg.provider == "openai" and openai is not None and os.getenv("OPENAI_API_KEY"):
        client = openai.OpenAI()
        resp = client.chat.completions.create(model=cfg.model, messages=messages)
        return resp.choices[0].message.content
    elif cfg.provider == "anthropic" and anthropic is not None and os.getenv("ANTHROPIC_API_KEY"):
        client = anthropic.Anthropic()
        resp = client.messages.create(model=cfg.model, max_tokens=600, messages=[{"role": m["role"], "content": m["content"]} for m in messages])
        return resp.content[0].text
    else:
        # Local naive fallback: summarize user message and echo guidance
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        summ = _local_summarizer(last_user, truncation=True, max_length=120)[0]["summary_text"]
        out = _local_t2t(f"Paraphrase kindly:\n\n{summ}", max_length=120, num_beams=4)[0]["generated_text"]
        return out
