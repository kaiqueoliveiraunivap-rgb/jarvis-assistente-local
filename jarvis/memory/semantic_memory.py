from jarvis.memory.memory_manager import MemoryManager


class SemanticMemory:
    def __init__(self, manager: MemoryManager) -> None:
        self.manager = manager

    def search(self, query: str) -> list[str]:
        return [record.content for record in self.manager.recall(query)]

