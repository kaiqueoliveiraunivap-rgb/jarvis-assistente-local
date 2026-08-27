from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Activity:
    name: str
    details: dict[str, Any]
    created_at: datetime


class ActivityContext:
    def __init__(self, capacity: int = 30) -> None:
        self._activities: deque[Activity] = deque(maxlen=capacity)

    def record(self, name: str, **details: Any) -> None:
        self._activities.append(Activity(name, details, datetime.now(UTC)))

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        return [{"name": item.name, "details": item.details, "created_at": item.created_at.isoformat()} for item in list(self._activities)[-limit:]]

