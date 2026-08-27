from __future__ import annotations

import unittest

from jarvis.core.permissions import PermissionDecision, PermissionManager
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


@tool("safe_mock", "Consultar algo", category="test")
def safe_mock(value: int) -> ToolResult:
    return ToolResult.ok(data=value)


@tool("danger_mock", "Apagar algo", category="test", risk=RiskLevel.HIGH, confirmation_required=True)
def danger_mock(path: str) -> ToolResult:
    return ToolResult.ok(data=path)


@tool("critical_mock", "Administrar o sistema", category="test", risk=RiskLevel.CRITICAL)
def critical_mock() -> ToolResult:
    return ToolResult.ok()


class ToolAndPermissionTests(unittest.TestCase):
    def test_registry_rejects_unknown_and_bad_arguments(self) -> None:
        registry = ToolRegistry()
        registry.register(safe_mock)
        self.assertEqual(registry.require("safe_mock").name, "safe_mock")
        with self.assertRaises(KeyError):
            registry.require("shell")
        with self.assertRaises(ValueError):
            registry.require("safe_mock").validate_arguments({"unexpected": 1})

    def test_high_risk_requires_confirmation(self) -> None:
        manager = PermissionManager()
        spec = getattr(danger_mock, "__jarvis_tool__")
        self.assertIs(manager.check(spec, {"path": "x"}).decision, PermissionDecision.CONFIRM)
        self.assertIs(manager.check(spec, {"path": "x"}, confirmed=True).decision, PermissionDecision.ALLOW)

    def test_critical_denied_by_default(self) -> None:
        manager = PermissionManager()
        spec = getattr(critical_mock, "__jarvis_tool__")
        self.assertIs(manager.check(spec, {}).decision, PermissionDecision.DENY)


if __name__ == "__main__":
    unittest.main()

