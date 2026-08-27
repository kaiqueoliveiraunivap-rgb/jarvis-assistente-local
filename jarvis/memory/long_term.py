from jarvis.memory.memory_manager import MemoryManager


class LongTermMemory:
    def __init__(self, manager: MemoryManager) -> None:
        self.manager = manager

    def remember_preference(self, content: str) -> tuple[bool, str, int | None]:
        return self.manager.remember(content, explicitly_requested=True, metadata={"source": "preference"})

