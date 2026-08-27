from __future__ import annotations

import asyncio
import inspect
from collections.abc import Iterable
from typing import Any, Callable

from jarvis.tools.tool import ToolResult, ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, handler: Callable[..., Any], *, replace: bool = False) -> ToolSpec:
        spec = getattr(handler, "__jarvis_tool__", None)
        if not isinstance(spec, ToolSpec):
            raise TypeError("A função precisa usar o decorador @tool")
        if spec.name in self._tools and not replace:
            raise ValueError(f"Tool já registrada: {spec.name}")
        self._tools[spec.name] = spec
        return spec

    def register_many(self, handlers: Iterable[Callable[..., Any]]) -> None:
        for handler in handlers:
            self.register(handler)

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def require(self, name: str) -> ToolSpec:
        spec = self.get(name)
        if spec is None:
            raise KeyError(f"Tool não autorizada ou inexistente: {name}")
        return spec

    def list(self, category: str | None = None) -> tuple[ToolSpec, ...]:
        values = self._tools.values()
        return tuple(spec for spec in values if category is None or spec.category == category)

    async def invoke(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        spec = self.require(name)
        validated = spec.validate_arguments(arguments or {})
        try:
            if inspect.iscoroutinefunction(spec.handler):
                outcome = await spec.handler(**validated)
            else:
                outcome = await asyncio.to_thread(spec.handler, **validated)
            if isinstance(outcome, ToolResult):
                return outcome
            return ToolResult.ok(data=outcome)
        except Exception as exc:
            return ToolResult.fail(f"Não consegui executar {name}: {exc}", type(exc).__name__)

