from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.core.permissions import PermissionDecision, PermissionManager
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.tool import ToolResult


@dataclass(frozen=True, slots=True)
class PlanStep:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    steps: tuple[PlanStep, ...]
    summary: str = ""


@dataclass(frozen=True, slots=True)
class StepExecution:
    step: PlanStep
    result: ToolResult


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    success: bool
    executions: tuple[StepExecution, ...]
    message: str
    confirmation_required: bool = False
    remaining_plan: ExecutionPlan | None = None
    cancelled: bool = False


class Executor:
    def __init__(self, registry: ToolRegistry, permissions: PermissionManager, event_bus: EventBus) -> None:
        self.registry = registry
        self.permissions = permissions
        self.event_bus = event_bus
        self._cancel_event = asyncio.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    async def execute(self, plan: ExecutionPlan, *, confirm_first: bool = False) -> ExecutionReport:
        self._cancel_event.clear()
        executions: list[StepExecution] = []
        await self.event_bus.publish(Event(EventType.TASK_STARTED, {"summary": plan.summary}))
        for index, step in enumerate(plan.steps):
            if self._cancel_event.is_set():
                return ExecutionReport(False, tuple(executions), "Cancelado.", cancelled=True)
            try:
                spec = self.registry.require(step.tool)
                arguments = spec.validate_arguments(step.arguments)
            except (KeyError, ValueError) as exc:
                result = ToolResult.fail(str(exc), "INVALID_PLAN")
                executions.append(StepExecution(step, result))
                return ExecutionReport(False, tuple(executions), result.message)

            permission = self.permissions.check(spec, arguments, confirmed=confirm_first and index == 0)
            if permission.decision is PermissionDecision.DENY:
                result = ToolResult.fail(permission.reason, "PERMISSION_DENIED")
                executions.append(StepExecution(step, result))
                return ExecutionReport(False, tuple(executions), permission.reason)
            if permission.decision is PermissionDecision.CONFIRM:
                remaining = ExecutionPlan(plan.steps[index:], plan.summary)
                return ExecutionReport(
                    False, tuple(executions), permission.reason,
                    confirmation_required=True, remaining_plan=remaining,
                )

            result = await self.registry.invoke(step.tool, arguments)
            executions.append(StepExecution(step, result))
            if not result.success:
                return ExecutionReport(False, tuple(executions), result.message)
            lifecycle_event = {
                "open_app": EventType.APP_OPENED,
                "close_app": EventType.APP_CLOSED,
            }.get(step.tool)
            if lifecycle_event:
                await self.event_bus.publish(Event(lifecycle_event, {"name": arguments.get("name", "")}, 0))
        message = executions[-1].result.message if executions else "Nada para executar."
        await self.event_bus.publish(Event(EventType.TASK_COMPLETED, {"summary": plan.summary, "success": True}))
        return ExecutionReport(True, tuple(executions), message)
