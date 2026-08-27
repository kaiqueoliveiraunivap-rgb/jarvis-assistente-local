from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AIMessage:
    role: str
    content: str
    images: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AIResponse:
    content: str
    model: str
    done: bool = True
    metadata: dict[str, Any] | None = None


class AIProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[AIMessage], *, json_mode: bool = False, model: str | None = None) -> AIResponse:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> tuple[bool, str]:
        raise NotImplementedError

