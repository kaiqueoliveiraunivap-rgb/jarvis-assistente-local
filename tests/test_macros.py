from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.automation.macros import MacroManager
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.tool import ToolResult, tool


@tool("open_mock", "Abrir mock", category="test")
def open_mock(name: str) -> ToolResult:
    return ToolResult.ok(name)


class MacroTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        registry = ToolRegistry()
        registry.register(open_mock)
        self.manager = MacroManager(registry, Path(self.directory.name) / "macros.json")
        self.manager.load()

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_create_reload_and_match(self) -> None:
        self.manager.create(
            "work", [{"tool": "open_mock", "args": {"name": "editor"}}], ["vamos trabalhar"]
        )
        self.assertIsNotNone(self.manager.match("Vamos trabalhar!"))
        self.assertEqual(self.manager.plan("work").steps[0].arguments["name"], "editor")  # type: ignore[union-attr]

    def test_rejects_unknown_tool(self) -> None:
        with self.assertRaises(KeyError):
            self.manager.create("bad", [{"tool": "shell", "args": {}}], ["ruim"])


if __name__ == "__main__":
    unittest.main()

