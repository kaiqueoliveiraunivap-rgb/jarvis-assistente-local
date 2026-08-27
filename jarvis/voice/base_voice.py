from __future__ import annotations

from abc import ABC, abstractmethod


class BaseVoice(ABC):
    @abstractmethod
    async def speak(self, text: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

