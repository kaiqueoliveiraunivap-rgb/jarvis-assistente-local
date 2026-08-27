from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(slots=True)
class ScreenContext:
    analyzing: bool = False
    last_capture: Path | None = None
    last_analysis: str | None = None
    updated_at: datetime | None = None

    def update(self, path: Path, analysis: str | None = None) -> None:
        self.last_capture = path
        self.last_analysis = analysis
        self.updated_at = datetime.now(UTC)

