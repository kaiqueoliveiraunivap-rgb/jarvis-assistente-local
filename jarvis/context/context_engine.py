from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from jarvis.context.activity_context import ActivityContext
from jarvis.context.screen_context import ScreenContext
from jarvis.context.system_context import system_snapshot
from jarvis.context.temporal_context import current_temporal_context
from jarvis.memory.memory_manager import MemoryManager


class ContextEngine:
    def __init__(self, memory: MemoryManager) -> None:
        self.memory = memory
        self.activity = ActivityContext()
        self.screen = ScreenContext()
        self.started_at = datetime.now(UTC)

    def collect(self, *, include_system: bool = True, memory_query: str | None = None) -> dict[str, Any]:
        context: dict[str, Any] = {
            "temporal": current_temporal_context().to_dict(),
            "session_seconds": int((datetime.now(UTC) - self.started_at).total_seconds()),
            "recent_activity": self.activity.recent(),
        }
        if include_system:
            context["system"] = system_snapshot()
        if memory_query:
            context["relevant_memories"] = [record.content for record in self.memory.recall(memory_query, limit=4)]
        return context

