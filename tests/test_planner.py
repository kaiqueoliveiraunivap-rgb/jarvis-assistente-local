from __future__ import annotations

import unittest

from jarvis.ai.planner import AIPlanner, DeterministicPlanner
from jarvis.ai.provider import AIMessage, AIProvider, AIResponse
from jarvis.ai.prompt_manager import PromptManager
from jarvis.core.config import AppSettings
from jarvis.core.intent_router import IntentRouter
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.tool import ToolResult, tool


@tool("allowed", "Ação permitida", category="test")
def allowed(value: str) -> ToolResult:
    return ToolResult.ok(value)


class FakeProvider(AIProvider):
    def __init__(self, content: str) -> None:
        self.content = content

    async def chat(self, messages: list[AIMessage], *, json_mode: bool = False, model: str | None = None) -> AIResponse:
        return AIResponse(self.content, "fake")

    async def health(self) -> tuple[bool, str]:
        return True, "ok"


class PlannerTests(unittest.IsolatedAsyncioTestCase):
    async def test_deterministic_direct_command(self) -> None:
        intent = IntentRouter().route("abra o Spotify")
        plan = DeterministicPlanner().plan(intent)
        self.assertEqual(plan.steps[0].tool, "open_app")  # type: ignore[union-attr]

    async def test_ai_plan_is_validated(self) -> None:
        registry = ToolRegistry()
        registry.register(allowed)
        provider = FakeProvider('{"kind":"plan","summary":"x","steps":[{"tool":"allowed","arguments":{"value":"ok"}}]}')
        planner = AIPlanner(provider, registry, PromptManager(AppSettings()))
        outcome = await planner.plan("faça x", {})
        self.assertEqual(outcome.plan.steps[0].tool, "allowed")  # type: ignore[union-attr]

    async def test_ai_cannot_invent_shell_tool(self) -> None:
        registry = ToolRegistry()
        registry.register(allowed)
        provider = FakeProvider('{"kind":"plan","steps":[{"tool":"powershell","arguments":{"code":"x"}}]}')
        outcome = await AIPlanner(provider, registry, PromptManager(AppSettings())).plan("x", {})
        self.assertIsNone(outcome.plan)
        self.assertIn("inválido", outcome.response)


if __name__ == "__main__":
    unittest.main()

