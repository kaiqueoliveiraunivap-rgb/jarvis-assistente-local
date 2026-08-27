from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolSpec


class PermissionDecision(StrEnum):
    ALLOW = "ALLOW"
    CONFIRM = "CONFIRM"
    DENY = "DENY"


@dataclass(frozen=True, slots=True)
class PermissionCheck:
    decision: PermissionDecision
    reason: str


class PermissionManager:
    """Política local. Tools críticas ficam bloqueadas até autorização explícita na configuração."""

    def __init__(self, allowed_critical_tools: set[str] | None = None) -> None:
        self.allowed_critical_tools = allowed_critical_tools or set()

    def check(self, spec: ToolSpec, arguments: dict[str, Any], *, confirmed: bool = False) -> PermissionCheck:
        if spec.risk is RiskLevel.CRITICAL and spec.name not in self.allowed_critical_tools:
            return PermissionCheck(PermissionDecision.DENY, "Ação crítica não autorizada pela política local.")
        needs_confirmation = spec.confirmation_required or spec.risk >= RiskLevel.HIGH
        if needs_confirmation and not confirmed:
            return PermissionCheck(PermissionDecision.CONFIRM, self.confirmation_prompt(spec, arguments))
        return PermissionCheck(PermissionDecision.ALLOW, "Permitido pela política local.")

    @staticmethod
    def confirmation_prompt(spec: ToolSpec, arguments: dict[str, Any]) -> str:
        if spec.name == "shutdown_pc":
            return "Confirma que deseja desligar o computador?"
        if spec.name == "restart_pc":
            return "Confirma que deseja reiniciar o computador?"
        if spec.name == "sleep_pc":
            return "Confirma que deseja suspender o computador?"
        if spec.name.startswith("delete_"):
            return f"Confirma a exclusão de {arguments.get('path', 'este item')}?"
        return f"A ação “{spec.description}” exige confirmação. Posso continuar?"

