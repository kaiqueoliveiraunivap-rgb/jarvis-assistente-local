from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jarvis.core.config import ConfigManager, ProactivityLevel, ScreenAwareness
from jarvis.core.logger import redact


class ConfigTests(unittest.TestCase):
    def test_creates_and_round_trips_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            manager = ConfigManager(path)
            settings = manager.load()
            settings.user_name = "Kaique"
            settings.privacy.screen_awareness = ScreenAwareness.OFF
            settings.automation.proactivity = ProactivityLevel.LOW
            manager.save(settings)
            loaded = ConfigManager(path).load()
            self.assertEqual(loaded.user_name, "Kaique")
            self.assertIs(loaded.privacy.screen_awareness, ScreenAwareness.OFF)
            self.assertIs(loaded.automation.proactivity, ProactivityLevel.LOW)

    def test_rejects_out_of_range_personality(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = ConfigManager(Path(directory) / "settings.json")
            settings = manager.load()
            settings.personality.humor = 101
            with self.assertRaises(ValueError):
                manager.save(settings)

    def test_rejects_insecure_remote_ai_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            manager = ConfigManager(path)
            settings = manager.load()
            settings.ai.endpoint = "http://example.com:11434"
            with self.assertRaises(ValueError):
                manager.save(settings)

    def test_log_redaction_hides_secrets_and_card_like_numbers(self) -> None:
        redacted = redact("minha senha é abc123 e cartão 4111 1111 1111 1111")
        self.assertNotIn("abc123", redacted)
        self.assertNotIn("4111", redacted)
        self.assertIn("[REDACTED]", redacted)


if __name__ == "__main__":
    unittest.main()
