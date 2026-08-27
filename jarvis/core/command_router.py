from __future__ import annotations

from jarvis.ai.planner import DeterministicPlanner
from jarvis.core.executor import ExecutionPlan
from jarvis.core.intent_router import Intent, IntentRouter


class CommandRouter:
    def __init__(self, intents: IntentRouter, planner: DeterministicPlanner) -> None:
        self.intents = intents
        self.planner = planner

    def route(self, text: str) -> tuple[Intent, ExecutionPlan | None]:
        intent = self.intents.route(text)
        return intent, self.planner.plan(intent)

