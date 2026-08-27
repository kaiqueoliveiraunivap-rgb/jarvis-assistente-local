from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.database.database import Database
from jarvis.memory.memory_manager import MemoryManager


class MemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.directory.name) / "test.db")
        self.database.initialize()
        self.memory = MemoryManager(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_explicit_memory_is_persisted_and_recalled(self) -> None:
        stored, _, memory_id = self.memory.remember(
            "meu projeto principal é Sistema da Gigi", explicitly_requested=True
        )
        self.assertTrue(stored)
        self.assertIsNotNone(memory_id)
        self.assertEqual(self.memory.recall("Sistema da Gigi")[0].content, "meu projeto principal é Sistema da Gigi")

    def test_sensitive_memory_is_rejected(self) -> None:
        stored, message, _ = self.memory.remember("minha senha é abc123", explicitly_requested=True)
        self.assertFalse(stored)
        self.assertIn("sensível", message)

    def test_incidental_content_is_not_persisted(self) -> None:
        stored, _, _ = self.memory.remember("a janela está azul")
        self.assertFalse(stored)


if __name__ == "__main__":
    unittest.main()

