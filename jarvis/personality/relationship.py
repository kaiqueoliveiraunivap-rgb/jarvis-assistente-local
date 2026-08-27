from __future__ import annotations

from jarvis.database.database import Database


class RelationshipModel:
    """Preferências funcionais; não modela apego ou dependência emocional."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def set_preference(self, key: str, value: object) -> None:
        self.database.set_preference(f"relationship.{key}", value)

    def get_preference(self, key: str, default: object = None) -> object:
        return self.database.get_preference(f"relationship.{key}", default)

