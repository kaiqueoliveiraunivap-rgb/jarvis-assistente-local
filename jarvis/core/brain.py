from __future__ import annotations

from jarvis.ai.context_manager import AIContextManager
from jarvis.ai.planner import AIPlanner, PlanningOutcome
from jarvis.ai.prompt_manager import PromptManager
from jarvis.ai.provider import AIProvider
from jarvis.context.context_engine import ContextEngine
from jarvis.memory.short_term import ShortTermMemory


class Brain:
    def __init__(
        self,
        provider: AIProvider,
        planner: AIPlanner,
        prompts: PromptManager,
        context: ContextEngine,
        short_term: ShortTermMemory,
    ) -> None:
        self.provider = provider
        self.planner = planner
        self.prompts = prompts
        self.context = context
        self.ai_context = AIContextManager(short_term)

    async def interpret(self, text: str) -> PlanningOutcome:
        context = self.context.collect(include_system=False, memory_query=text)
        return await self.planner.plan(text, context)

    async def converse(self, text: str) -> str:
        context = self.context.collect(include_system=False, memory_query=text)
        prompt = self.prompts.system_prompt(context)
        response = await self.provider.chat(self.ai_context.messages(prompt, text))
        return response.content

