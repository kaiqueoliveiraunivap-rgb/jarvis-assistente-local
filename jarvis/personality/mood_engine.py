from __future__ import annotations

from enum import StrEnum


class Mood(StrEnum):
    NEUTRAL = "NEUTRAL"
    HAPPY = "HAPPY"
    FOCUSED = "FOCUSED"
    CURIOUS = "CURIOUS"
    CONCERNED = "CONCERNED"
    CALM = "CALM"
    EXCITED = "EXCITED"
    TIRED = "TIRED"


class MoodEngine:
    def __init__(self) -> None:
        self.mood = Mood.NEUTRAL

    def observe(self, event: str, value: float | None = None) -> Mood:
        if event in {"WORK_STARTED", "CODE_ACTIVE"}:
            self.mood = Mood.FOCUSED
        elif event in {"TASK_COMPLETED", "ERROR_RESOLVED"}:
            self.mood = Mood.HAPPY
        elif event in {"ERROR_REPEATED", "HIGH_RAM", "HIGH_CPU"}:
            self.mood = Mood.CONCERNED
        elif event in {"NEW_DISCOVERY", "QUESTION"}:
            self.mood = Mood.CURIOUS
        elif event == "CASUAL":
            self.mood = Mood.CALM
        return self.mood

