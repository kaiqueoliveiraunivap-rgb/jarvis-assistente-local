from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from jarvis.core.config import ProactivityLevel


class Decision(StrEnum):
    IGNORE = "IGNORE"
    NOTIFY = "NOTIFY"
    SPEAK = "SPEAK"
    ASK = "ASK"
    SUGGEST = "SUGGEST"
    ACT = "ACT"


@dataclass(frozen=True, slots=True)
class DecisionContext:
    importance: int
    proactivity: ProactivityLevel = ProactivityLevel.NORMAL
    mode: str = "NORMAL"
    previously_authorized: bool = False
    user_idle: bool = False


class DecisionEngine:
    def decide(self, context: DecisionContext) -> Decision:
        if context.proactivity is ProactivityLevel.OFF:
            return Decision.IGNORE
        penalty = 15 if context.mode in {"FOCUS", "GAMING", "SILENT"} else 0
        importance = context.importance - penalty
        if importance >= 95:
            return Decision.SPEAK if context.mode != "SILENT" else Decision.NOTIFY
        if importance >= 70:
            return Decision.NOTIFY
        if importance >= 50 and context.proactivity in {ProactivityLevel.NORMAL, ProactivityLevel.HIGH}:
            return Decision.SUGGEST
        if importance >= 30 and context.proactivity is ProactivityLevel.HIGH:
            return Decision.NOTIFY
        return Decision.IGNORE

