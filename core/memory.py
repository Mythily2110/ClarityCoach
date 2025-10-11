# core/memory.py
from sqlmodel import SQLModel, Field, create_engine, Session, select
from datetime import datetime
from typing import Optional

# --- Rerun safety: remove any old table before re-declaring ---
existing = SQLModel.metadata.tables.get("journal")
if existing is not None:
    SQLModel.metadata.remove(existing)

engine = create_engine("sqlite:///data/claritycoach.db", echo=False)

class Journal(SQLModel, table=True):
    __tablename__ = "journal"
    __table_args__ = {"extend_existing": True}   # allow re-declare on rerun
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    text: str

def init_db():
    SQLModel.metadata.create_all(engine)

def add_journal(text: str):
    with Session(engine) as s:
        s.add(Journal(text=text)); s.commit()

def get_journals(limit=50):
    with Session(engine) as s:
        return s.exec(select(Journal).order_by(Journal.ts.desc()).limit(limit)).all()
