from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any

from jarvis.ai.provider import AIMessage, AIProvider, AIResponse


class OllamaClient(AIProvider):
    def __init__(self, endpoint: str, model: str, temperature: float = 0.35, timeout: float = 90.0) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    async def chat(self, messages: list[AIMessage], *, json_mode: bool = False, model: str | None = None) -> AIResponse:
        return await asyncio.to_thread(self._chat_sync, messages, json_mode, model)

    def _chat_sync(self, messages: list[AIMessage], json_mode: bool, model: str | None) -> AIResponse:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "stream": False,
            "messages": [
                {"role": message.role, "content": message.content, **({"images": list(message.images)} if message.images else {})}
                for message in messages
            ],
            "options": {"temperature": self.temperature},
        }
        if json_mode:
            payload["format"] = "json"
        data = self._request("/api/chat", payload)
        message = data.get("message", {})
        content = str(message.get("content", "")).strip()
        return AIResponse(content, str(data.get("model", model or self.model)), bool(data.get("done", True)), data)

    async def health(self) -> tuple[bool, str]:
        try:
            data = await asyncio.to_thread(self._request, "/api/tags", None)
            names = [str(item.get("name", "")) for item in data.get("models", [])]
            if not names:
                return True, "Ollama online, sem modelos instalados."
            configured = any(name == self.model or name.startswith(self.model + ":") for name in names)
            return True, "Ollama online." if configured else f"Ollama online; modelo {self.model} ainda não encontrado."
        except Exception as exc:
            return False, str(exc)

    def _request(self, route: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint + route,
            data=body,
            headers={"Content-Type": "application/json"},
            method="GET" if body is None else "POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Ollama indisponível em {self.endpoint}: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama retornou uma resposta inválida") from exc

