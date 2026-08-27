from __future__ import annotations

from jarvis.ai.ollama_client import OllamaClient
from jarvis.ai.provider import AIProvider
from jarvis.core.config import AISettings


class ModelManager:
    def __init__(self, settings: AISettings) -> None:
        self.settings = settings
        self._provider: AIProvider | None = None

    def provider(self) -> AIProvider:
        if self._provider is None:
            if self.settings.provider.casefold() != "ollama":
                raise ValueError(f"Provider de IA não suportado: {self.settings.provider}")
            self._provider = OllamaClient(
                self.settings.endpoint,
                self.settings.model,
                self.settings.temperature,
                self.settings.request_timeout_seconds,
            )
        return self._provider

