from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class RoutineSuggestion:
    sequence: tuple[str, ...]
    occurrences: int
    message: str


class RoutineDetector:
    def __init__(self, minimum_occurrences: int = 3) -> None:
        self.minimum_occurrences = minimum_occurrences
        self._recent: deque[tuple[datetime, str]] = deque(maxlen=200)
        self._sequences: Counter[tuple[str, ...]] = Counter()

    def record_app_opened(self, name: str) -> RoutineSuggestion | None:
        now = datetime.now(UTC)
        self._recent.append((now, name.casefold()))
        current = tuple(item for timestamp, item in self._recent if now - timestamp <= timedelta(minutes=10))[-3:]
        if len(current) == 3:
            self._sequences[current] += 1
            count = self._sequences[current]
            if count == self.minimum_occurrences:
                return RoutineSuggestion(current, count, "Parece que você vai iniciar sua rotina. Quer que eu prepare o restante?")
        return None

