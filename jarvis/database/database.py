from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Sequence

from jarvis.core.paths import database_path
from jarvis.database.migrations import migrate


class Database:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()

    def initialize(self) -> None:
        with self.connection() as connection:
            migrate(connection)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def execute(self, sql: str, parameters: Sequence[Any] = ()) -> int:
        with self.connection() as connection:
            cursor = connection.execute(sql, parameters)
            return int(cursor.lastrowid or 0)

    def fetch_all(self, sql: str, parameters: Sequence[Any] = ()) -> list[sqlite3.Row]:
        with self.connection() as connection:
            return list(connection.execute(sql, parameters).fetchall())

    def set_preference(self, key: str, value: Any) -> None:
        now = datetime.now(UTC).isoformat()
        self.execute(
            """INSERT INTO preferences(key, value_json, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at""",
            (key, json.dumps(value, ensure_ascii=False), now),
        )

    def get_preference(self, key: str, default: Any = None) -> Any:
        rows = self.fetch_all("SELECT value_json FROM preferences WHERE key=?", (key,))
        return json.loads(rows[0]["value_json"]) if rows else default

    def close(self) -> None:
        """Conexões são curtas e fechadas por operação; mantido para ciclo de vida uniforme."""
