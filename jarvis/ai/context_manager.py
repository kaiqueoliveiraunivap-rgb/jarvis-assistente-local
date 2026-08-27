from __future__ import annotations

from jarvis.ai.provider import AIMessage
from jarvis.memory.short_term import ShortTermMemory


class AIContextManager:
    def __init__(self, short_term: ShortTermMemory) -> None:
        self.short_term = short_term

    def messages(self, system_prompt: str, user_text: str, limit: int = 10) -> list[AIMessage]:
        messages = [AIMessage("system", system_prompt)]
        messages.extend(AIMessage(turn.role, turn.content) for turn in self.short_term.recent(limit))
        messages.append(AIMessage("user", user_text))
        return messages

