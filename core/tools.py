# core/tools.py
from __future__ import annotations
from dataclasses import dataclass
import time

# Your existing Timer singleton should already be here; keeping compatible.
@dataclass
class FocusTimer:
    running: bool = False
    paused: bool = False
    duration_sec: int = 0
    end_time: float = 0.0
    remaining_sec: int = 0

    def start(self, minutes: int = 25):
        self.duration_sec = max(60, int(minutes) * 60)
        self.end_time = time.time() + self.duration_sec
        self.running = True
        self.paused = False
        self.remaining_sec = self.duration_sec

    def pause(self):
        if self.running and not self.paused:
            self.paused = True
            self.remaining_sec = max(0, int(self.end_time - time.time()))

    def resume(self):
        if self.running and self.paused:
            self.end_time = time.time() + self.remaining_sec
            self.paused = False

    def stop(self):
        self.running = False
        self.paused = False
        self.duration_sec = 0
        self.end_time = 0.0
        self.remaining_sec = 0

    def progress_ratio(self) -> float:
        if not self.running:
            return 0.0
        total = max(1, self.duration_sec)  # avoid division by zero
        if self.paused:
            done = total - self.remaining_sec
        else:
            left = max(0, int(self.end_time - time.time()))
            done = total - left
        return max(0.0, min(1.0, done / total))

    def status_text(self) -> str:
        if not self.running:
            return "Timer is idle."
        if self.paused:
            m, s = divmod(self.remaining_sec, 60)
            return f"Paused — {m:02d}:{s:02d} remaining."
        left = max(0, int(self.end_time - time.time()))
        if left == 0:
            self.stop()
            return "✅ Time's up! Take a short break."
        m, s = divmod(left, 60)
        return f"{m:02d}:{s:02d} remaining."

# global singleton
timer = FocusTimer()

# ---------- Study Sprint Planner (deterministic, human) ----------
def make_study_sprint(subject: str = "your subject", days: int = 3, hours_per_day: float = 2.0) -> str:
    days = max(1, int(days))
    hours_per_day = max(1.0, float(hours_per_day))
    per_day = int(hours_per_day * 60)

    L = []
    for d in range(1, days + 1):
        L.append(f"**Day {d} — {subject.title()}**")
        L.append(f"- {int(per_day*0.45)} min **Active recall**: brain dump → read to fill gaps.")
        L.append(f"- {int(per_day*0.35)} min **Practice**: past questions/problems; keep an error log.")
        L.append(f"- {int(per_day*0.20)} min **Review**: 1-page summary or flashcards.")
        L.append("- Breaks: 5–10 min between blocks; water + stretch.")
        if d % 2 == 0 and d != days:
            L.append("- Optional 20-min **mini-mock** in the evening.")
        L.append("")
    L.append("**Exam-eve tips**: light review, pack materials, 20–30 min phone-free wind-down.")
    return "\n".join(L)

# ---------- Tool registry exposed to dialog ----------
def register_tools():
    return {
        "pomodoro_start": lambda minutes=25: (timer.start(int(minutes)), f"Pomodoro started for {int(minutes)} minutes.")[1],
        "pomodoro_stop":  lambda: (timer.stop(), "Stopped Pomodoro.")[1],
        "pomodoro_status": lambda: timer.status_text(),
        "study_sprint":   lambda subject="your subject", days=3, hours_per_day=2.0:
            make_study_sprint(subject, days, hours_per_day),
    }
