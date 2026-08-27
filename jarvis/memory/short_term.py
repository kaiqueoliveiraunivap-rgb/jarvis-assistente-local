from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    role: str
    content: str
    created_at: datetime


class ShortTermMemory:
    def __init__(self, max_turns: int = 30) -> None:
        self._turns: deque[ConversationTurn] = deque(maxlen=max_turns)

    def add(self, role: str, content: str) -> None:
        if role not in {"user", "assistant", "system"}:
            raise ValueError("Papel de conversa inválido")
        self._turns.append(ConversationTurn(role, content.strip(), datetime.now(UTC)))

    def recent(self, limit: int = 12) -> tuple[ConversationTurn, ...]:
        return tuple(list(self._turns)[-max(0, limit):])

    def clear(self) -> None:
        self._turns.clear()

