from jarvis.memory.memory_manager import MemoryManager


class EpisodicMemory:
    def __init__(self, manager: MemoryManager) -> None:
        self.manager = manager

    def record(self, content: str, importance: int = 50) -> int | None:
        return self.manager.add_episode(content, importance)

