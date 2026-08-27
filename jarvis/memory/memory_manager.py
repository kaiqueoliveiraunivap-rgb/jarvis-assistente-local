from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from jarvis.database.database import Database
from jarvis.database.models import MemoryKind, MemoryRecord
from jarvis.memory.memory_evaluator import MemoryEvaluator
from jarvis.memory.short_term import ShortTermMemory


class MemoryManager:
    def __init__(self, database: Database, enabled: bool = True) -> None:
        self.database = database
        self.enabled = enabled
        self.evaluator = MemoryEvaluator()
        self.short_term = ShortTermMemory()

    def remember(self, content: str, *, explicitly_requested: bool = False, metadata: dict[str, Any] | None = None) -> tuple[bool, str, int | None]:
        if not self.enabled:
            return False, "A memória persistente está desativada.", None
        evaluation = self.evaluator.evaluate(content, explicitly_requested=explicitly_requested)
        if not evaluation.should_store:
            return False, f"Não salvei: {evaluation.reason}.", None
        now = datetime.now(UTC).isoformat()
        memory_id = self.database.execute(
            """INSERT INTO memories(kind, content, metadata_json, importance, created_at, accessed_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (evaluation.kind.value, content.strip(), json.dumps(metadata or {}, ensure_ascii=False), evaluation.importance, now, now),
        )
        return True, "Vou me lembrar disso.", memory_id

    def add_episode(self, content: str, importance: int = 50, metadata: dict[str, Any] | None = None) -> int | None:
        if not self.enabled or importance < 40:
            return None
        now = datetime.now(UTC).isoformat()
        return self.database.execute(
            "INSERT INTO memories(kind, content, metadata_json, importance, created_at, accessed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (MemoryKind.EPISODIC.value, content, json.dumps(metadata or {}, ensure_ascii=False), max(0, min(importance, 100)), now, now),
        )

    def recall(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        if not self.enabled or not query.strip():
            return []
        limit = max(1, min(int(limit), 20))
        words = [word for word in query.casefold().split() if len(word) > 2]
        like = "%" + "%".join(words or [query.strip()]) + "%"
        rows = self.database.fetch_all(
            """SELECT id, kind, content, metadata_json, importance, created_at, accessed_at
            FROM memories WHERE lower(content) LIKE ? ORDER BY importance DESC, created_at DESC LIMIT ?""",
            (like, limit),
        )
        now = datetime.now(UTC).isoformat()
        records = [self._row(row) for row in rows]
        for record in records:
            self.database.execute("UPDATE memories SET accessed_at=? WHERE id=?", (now, record.id))
        return records

    def recent(self, kind: MemoryKind | None = None, limit: int = 10) -> list[MemoryRecord]:
        if kind:
            rows = self.database.fetch_all(
                "SELECT id, kind, content, metadata_json, importance, created_at, accessed_at FROM memories WHERE kind=? ORDER BY created_at DESC LIMIT ?",
                (kind.value, limit),
            )
        else:
            rows = self.database.fetch_all(
                "SELECT id, kind, content, metadata_json, importance, created_at, accessed_at FROM memories ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [self._row(row) for row in rows]

    def prune(self, short_term_days: int = 7) -> int:
        threshold = (datetime.now(UTC) - timedelta(days=short_term_days)).isoformat()
        with self.database.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE kind=? AND created_at < ?",
                (MemoryKind.SHORT_TERM.value, threshold),
            )
            return int(cursor.rowcount)

    @staticmethod
    def _row(row: Any) -> MemoryRecord:
        return MemoryRecord(
            id=int(row["id"]), kind=MemoryKind(row["kind"]), content=str(row["content"]),
            metadata=json.loads(row["metadata_json"]), importance=int(row["importance"]),
            created_at=datetime.fromisoformat(row["created_at"]), accessed_at=datetime.fromisoformat(row["accessed_at"]),
        )

