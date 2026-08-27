from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, get_type_hints

from jarvis.tools.risk import RiskLevel


ToolHandler = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    category: str
    risk: RiskLevel
    confirmation_required: bool
    handler: ToolHandler
    parameters: Mapping[str, inspect.Parameter] = field(default_factory=dict)
    type_hints: Mapping[str, Any] = field(default_factory=dict)

    def validate_arguments(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        unknown = set(arguments) - set(self.parameters)
        if unknown:
            raise ValueError(f"Argumentos desconhecidos para {self.name}: {', '.join(sorted(unknown))}")
        missing = [
            name for name, parameter in self.parameters.items()
            if parameter.default is inspect.Parameter.empty and name not in arguments
        ]
        if missing:
            raise ValueError(f"Argumentos obrigatórios ausentes: {', '.join(missing)}")
        return dict(arguments)


@dataclass(frozen=True, slots=True)
class ToolResult:
    success: bool
    message: str
    data: Any = None
    error_code: str | None = None

    @classmethod
    def ok(cls, message: str = "Pronto.", data: Any = None) -> "ToolResult":
        return cls(True, message, data)

    @classmethod
    def fail(cls, message: str, error_code: str = "TOOL_ERROR", data: Any = None) -> "ToolResult":
        return cls(False, message, data, error_code)


def tool(
    name: str,
    description: str,
    *,
    category: str,
    risk: RiskLevel = RiskLevel.SAFE,
    confirmation_required: bool = False,
) -> Callable[[ToolHandler], ToolHandler]:
    def decorate(handler: ToolHandler) -> ToolHandler:
        signature = inspect.signature(handler)
        spec = ToolSpec(
            name=name,
            description=description,
            category=category,
            risk=risk,
            confirmation_required=confirmation_required,
            handler=handler,
            parameters=signature.parameters,
            type_hints=get_type_hints(handler),
        )
        setattr(handler, "__jarvis_tool__", spec)
        return handler
    return decorate

