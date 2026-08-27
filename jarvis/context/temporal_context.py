from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TemporalContext:
    iso_datetime: str
    weekday: str
    period: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def current_temporal_context(now: datetime | None = None) -> TemporalContext:
    current = now or datetime.now().astimezone()
    weekdays = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")
    hour = current.hour
    period = "madrugada" if hour < 6 else "manhã" if hour < 12 else "tarde" if hour < 18 else "noite"
    return TemporalContext(current.isoformat(timespec="seconds"), weekdays[current.weekday()], period)

