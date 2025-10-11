# core/analytics.py
from sqlmodel import SQLModel, Field, create_engine, Session
from datetime import datetime
from typing import Optional

# --- Rerun safety: remove any old table before re-declaring ---
existing = SQLModel.metadata.tables.get("turnlog")
if existing is not None:
    SQLModel.metadata.remove(existing)

engine = create_engine("sqlite:///data/claritycoach.db", echo=False)

class TurnLog(SQLModel, table=True):
    __tablename__ = "turnlog"
    __table_args__ = {"extend_existing": True}   # allow re-declare on rerun
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    user_text: str
    intent: str
    had_handoff: bool = False

def init_logs():
    SQLModel.metadata.create_all(engine)

def log_turn(user_text: str, intent: str, had_handoff: bool=False):
    with Session(engine) as s:
        s.add(TurnLog(user_text=user_text, intent=intent, had_handoff=had_handoff))
        s.commit()
