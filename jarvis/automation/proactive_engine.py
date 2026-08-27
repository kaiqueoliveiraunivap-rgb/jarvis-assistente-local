from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from jarvis.computer.hardware import HardwareSnapshot, snapshot
from jarvis.core.config import AutomationSettings, ProactivityLevel
from jarvis.core.event_bus import Event, EventBus, EventType


class ProactiveEngine:
    def __init__(self, settings: AutomationSettings, event_bus: EventBus) -> None:
        self.settings = settings
        self.event_bus = event_bus
        self._last_alert: dict[EventType, datetime] = {}
        self._task: asyncio.Task[None] | None = None
        self._idle_since: datetime | None = None

    def start(self) -> None:
        if self.settings.proactivity is ProactivityLevel.OFF or self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="jarvis-proactive-monitor")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                self._task = None
                return
            self._task = None

    async def check_once(self) -> list[Event]:
        state = await asyncio.to_thread(snapshot)
        candidates: list[Event] = []
        if state.cpu_percent is not None and state.cpu_percent >= 95:
            candidates.append(Event(EventType.HIGH_CPU, {"percent": state.cpu_percent}, 65))
        if state.ram_percent is not None and state.ram_percent >= 90:
            candidates.append(Event(EventType.HIGH_RAM, {"percent": state.ram_percent}, 75))
        if state.disk_percent is not None and state.disk_percent >= 92:
            candidates.append(Event(EventType.LOW_DISK, {"percent": state.disk_percent}, 80))
        if state.battery_percent is not None and not state.plugged and state.battery_percent <= 8:
            candidates.append(Event(EventType.LOW_BATTERY, {"percent": state.battery_percent}, 100))
        emitted: list[Event] = []
        now = datetime.now(UTC)
        cooldown = timedelta(seconds=self.settings.cooldown_seconds)
        for event in candidates:
            previous = self._last_alert.get(event.type)
            if previous and now - previous < cooldown:
                continue
            self._last_alert[event.type] = now
            emitted.append(event)
            await self.event_bus.publish(event)
        try:
            from jarvis.context.system_context import idle_seconds
            idle = await asyncio.to_thread(idle_seconds)
            if idle >= 300 and self._idle_since is None:
                self._idle_since = now - timedelta(seconds=idle)
                event = Event(EventType.USER_IDLE, {"idle_seconds": round(idle)}, 5)
                emitted.append(event)
                await self.event_bus.publish(event)
            elif idle < 10 and self._idle_since is not None:
                away = (now - self._idle_since).total_seconds()
                self._idle_since = None
                importance = 55 if away >= 7200 else 20
                event = Event(EventType.USER_RETURNED, {"away_seconds": round(away)}, importance)
                emitted.append(event)
                await self.event_bus.publish(event)
        except Exception:
            self._idle_since = None
        return emitted

    async def _run(self) -> None:
        interval = max(10.0, self.settings.monitor_interval_seconds)
        while True:
            try:
                await self.check_once()
            except Exception as exc:
                await self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"source": "monitor", "error": str(exc)}, 20))
            await asyncio.sleep(interval)
