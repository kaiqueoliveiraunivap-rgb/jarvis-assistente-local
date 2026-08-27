from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Awaitable, Callable


class AssistantState(StrEnum):
    OFFLINE = "OFFLINE"
    STARTING = "STARTING"
    SLEEPING = "SLEEPING"
    IDLE = "IDLE"
    STANDBY = "STANDBY"
    OBSERVING = "OBSERVING"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    CURIOUS = "CURIOUS"
    ALERT = "ALERT"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class StateChange:
    previous: AssistantState
    current: AssistantState
    reason: str
    changed_at: datetime


StateListener = Callable[[StateChange], None | Awaitable[None]]


class StateManager:
    def __init__(self, initial: AssistantState = AssistantState.OFFLINE) -> None:
        self._state = initial
        self._listeners: list[StateListener] = []
        self._lock = asyncio.Lock()
        self._last_change = datetime.now(UTC)

    @property
    def state(self) -> AssistantState:
        return self._state

    @property
    def last_change(self) -> datetime:
        return self._last_change

    def subscribe(self, listener: StateListener) -> Callable[[], None]:
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    async def transition(self, target: AssistantState, reason: str = "") -> StateChange | None:
        async with self._lock:
            if target == self._state:
                return None
            previous = self._state
            self._state = target
            self._last_change = datetime.now(UTC)
            change = StateChange(previous, target, reason, self._last_change)
        for listener in tuple(self._listeners):
            result = listener(change)
            if asyncio.iscoroutine(result):
                await result
        return change

