from __future__ import annotations

import sqlite3


MIGRATIONS: tuple[tuple[int, str], ...] = (
    (1, """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL CHECK(kind IN ('SHORT_TERM','LONG_TERM','EPISODIC','SEMANTIC')),
            content TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            importance INTEGER NOT NULL DEFAULT 50 CHECK(importance BETWEEN 0 AND 100),
            created_at TEXT NOT NULL,
            accessed_at TEXT NOT NULL,
            expires_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_memories_kind_created ON memories(kind, created_at DESC);
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            intent TEXT NOT NULL,
            success INTEGER NOT NULL,
            duration_ms INTEGER NOT NULL,
            result_summary TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_commands_created ON commands(created_at DESC);
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            importance INTEGER NOT NULL DEFAULT 0,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, content='memories', content_rowid='id');
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
        END;
        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.id, old.content);
        END;
        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.id, old.content);
            INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
        END;
    """),
)


def migrate(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = connection.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
    current = int(row[0]) if row else 0
    for version, sql in MIGRATIONS:
        if version <= current:
            continue
        try:
            connection.executescript(sql)
        except sqlite3.OperationalError as exc:
            if "fts5" not in str(exc).lower():
                raise
            fallback = sql.split("CREATE VIRTUAL TABLE", 1)[0]
            connection.executescript(fallback)
        connection.execute("INSERT INTO schema_version(version) VALUES (?)", (version,))
        connection.commit()

