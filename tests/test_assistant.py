from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.core.assistant import JarvisAssistant
from jarvis.core.config import AppSettings, ProactivityLevel
from jarvis.database.database import Database


class AssistantTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        database = Database(Path(self.directory.name) / "assistant.db")
        database.initialize()
        settings = AppSettings()
        settings.automation.proactivity = ProactivityLevel.OFF
        self.assistant = JarvisAssistant(settings, database)
        await self.assistant.start(background_monitor=False)

    async def asyncTearDown(self) -> None:
        await self.assistant.stop()
        self.directory.cleanup()

    async def test_memory_round_trip(self) -> None:
        remembered = await self.assistant.handle_text("Jarvis, lembre que meu projeto principal é Gigi")
        recalled = await self.assistant.handle_text("Jarvis, lembra de projeto principal")
        self.assertTrue(remembered.success)
        self.assertIn("Gigi", recalled.text)

    async def test_destructive_action_requires_confirmation(self) -> None:
        response = await self.assistant.handle_text("Jarvis, desligue o computador")
        self.assertTrue(response.confirmation_required)
        denied = await self.assistant.handle_text("não")
        self.assertEqual(denied.text, "Tudo bem, cancelado.")

    async def test_cancel_clears_pending_action(self) -> None:
        await self.assistant.handle_text("Jarvis, reinicie o computador")
        cancelled = await self.assistant.handle_text("cancelar")
        self.assertEqual(cancelled.intent, "CANCEL")
        followup = await self.assistant.handle_text("sim")
        self.assertIn("não há", followup.text.casefold())


if __name__ == "__main__":
    unittest.main()

