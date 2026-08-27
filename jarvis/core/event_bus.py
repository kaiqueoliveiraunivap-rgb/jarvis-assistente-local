from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Awaitable, Callable


class EventType(StrEnum):
    SYSTEM_STARTED = "SYSTEM_STARTED"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    USER_RETURNED = "USER_RETURNED"
    USER_IDLE = "USER_IDLE"
    WAKE_WORD_DETECTED = "WAKE_WORD_DETECTED"
    COMMAND_RECEIVED = "COMMAND_RECEIVED"
    COMMAND_FINISHED = "COMMAND_FINISHED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    APP_OPENED = "APP_OPENED"
    APP_CLOSED = "APP_CLOSED"
    HIGH_CPU = "HIGH_CPU"
    HIGH_RAM = "HIGH_RAM"
    LOW_BATTERY = "LOW_BATTERY"
    LOW_DISK = "LOW_DISK"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    SCREEN_ANALYSIS_STARTED = "SCREEN_ANALYSIS_STARTED"
    SCREEN_ANALYSIS_FINISHED = "SCREEN_ANALYSIS_FINISHED"
    STATE_CHANGED = "STATE_CHANGED"
    ROUTINE_SUGGESTION = "ROUTINE_SUGGESTION"


@dataclass(frozen=True, slots=True)
class Event:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    importance: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not 0 <= self.importance <= 100:
            raise ValueError("importance precisa estar entre 0 e 100")


EventHandler = Callable[[Event], None | Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[EventType | None, list[EventHandler]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: EventType | None, handler: EventHandler) -> Callable[[], None]:
        self._subscribers[event_type].append(handler)

        def unsubscribe() -> None:
            handlers = self._subscribers[event_type]
            if handler in handlers:
                handlers.remove(handler)

        return unsubscribe

    async def publish(self, event: Event) -> None:
        async with self._lock:
            handlers = tuple(self._subscribers[event.type]) + tuple(self._subscribers[None])
        for handler in handlers:
            try:
                outcome = handler(event)
                if inspect.isawaitable(outcome):
                    await outcome
            except Exception:
                # Um assinante defeituoso não pode impedir os demais.
                continue
