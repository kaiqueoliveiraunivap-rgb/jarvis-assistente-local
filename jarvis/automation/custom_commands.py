from __future__ import annotations

from jarvis.automation.macros import MacroManager


class CustomCommandResolver:
    def __init__(self, macros: MacroManager) -> None:
        self.macros = macros

    def resolve(self, text: str) -> str:
        replacement = self.macros.resolve_alias(text)
        return replacement

