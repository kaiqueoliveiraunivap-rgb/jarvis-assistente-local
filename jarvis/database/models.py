from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class MemoryKind(StrEnum):
    SHORT_TERM = "SHORT_TERM"
    LONG_TERM = "LONG_TERM"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    id: int
    kind: MemoryKind
    content: str
    metadata: dict[str, Any]
    importance: int
    created_at: datetime
    accessed_at: datetime


@dataclass(frozen=True, slots=True)
class CommandRecord:
    id: int
    text: str
    intent: str
    success: bool
    duration_ms: int
    created_at: datetime

