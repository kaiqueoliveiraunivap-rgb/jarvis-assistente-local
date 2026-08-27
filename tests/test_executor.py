from __future__ import annotations

import unittest

from jarvis.core.event_bus import EventBus
from jarvis.core.executor import ExecutionPlan, Executor, PlanStep
from jarvis.core.permissions import PermissionManager
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


CALLS: list[str] = []


@tool("record", "Registrar chamada", category="test")
def record(value: str) -> ToolResult:
    CALLS.append(value)
    return ToolResult.ok(value)


@tool("confirmed", "Ação confirmada", category="test", risk=RiskLevel.HIGH)
def confirmed(value: str) -> ToolResult:
    CALLS.append(value)
    return ToolResult.ok(value)


class ExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        CALLS.clear()
        registry = ToolRegistry()
        registry.register_many((record, confirmed))
        self.executor = Executor(registry, PermissionManager(), EventBus())

    async def test_executes_sequential_plan(self) -> None:
        report = await self.executor.execute(ExecutionPlan((
            PlanStep("record", {"value": "a"}), PlanStep("record", {"value": "b"}),
        )))
        self.assertTrue(report.success)
        self.assertEqual(CALLS, ["a", "b"])

    async def test_pauses_before_high_risk_without_executing(self) -> None:
        report = await self.executor.execute(ExecutionPlan((PlanStep("confirmed", {"value": "x"}),)))
        self.assertTrue(report.confirmation_required)
        self.assertEqual(CALLS, [])
        resumed = await self.executor.execute(report.remaining_plan, confirm_first=True)  # type: ignore[arg-type]
        self.assertTrue(resumed.success)
        self.assertEqual(CALLS, ["x"])

    async def test_rejects_unregistered_tool(self) -> None:
        report = await self.executor.execute(ExecutionPlan((PlanStep("python_exec", {}),)))
        self.assertFalse(report.success)
        self.assertEqual(report.executions[0].result.error_code, "INVALID_PLAN")


if __name__ == "__main__":
    unittest.main()

