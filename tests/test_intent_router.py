from __future__ import annotations

import unittest

from jarvis.core.intent_router import IntentRouter, IntentType, normalize_text


class IntentRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = IntentRouter()

    def test_required_examples(self) -> None:
        cases = {
            "Jarvis, abra o Spotify.": IntentType.OPEN_APP,
            "Jarvis, feche o Spotify.": IntentType.CLOSE_APP,
            "Jarvis, volume 30%.": IntentType.SET_VOLUME,
            "Jarvis, mute.": IntentType.MUTE,
            "Jarvis, próxima música.": IntentType.NEXT_MEDIA,
            "Jarvis, abra o YouTube.": IntentType.OPEN_URL,
            "abre o youtube": IntentType.OPEN_URL,
            "Jarvis, pesquise Python no Google.": IntentType.WEB_SEARCH,
            "Quanto de RAM estou usando?": IntentType.RAM_USAGE,
            "Quais programas estão usando mais memória?": IntentType.LIST_PROCESSES,
            "Jarvis, tire uma screenshot.": IntentType.SCREENSHOT,
            "Jarvis, olha esse erro.": IntentType.ANALYZE_SCREEN,
            "Jarvis, escreva Olá mundo.": IntentType.TYPE_TEXT,
            "Jarvis, Ctrl S.": IntentType.HOTKEY,
            "Jarvis, organize minhas janelas.": IntentType.ORGANIZE_WINDOWS,
            "Jarvis, modo silencioso.": IntentType.SET_MODE,
            "Jarvis, cancelar.": IntentType.CANCEL,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertIs(self.router.route(text).type, expected)

    def test_wake_word_only(self) -> None:
        intent = self.router.route("Jarvis")
        self.assertIs(intent.type, IntentType.WAKE)
        self.assertTrue(intent.addressed)

    def test_custom_alias_command(self) -> None:
        intent = self.router.route("Jarvis, quando eu falar navegador, quero dizer Opera")
        self.assertIs(intent.type, IntentType.SET_ALIAS)
        self.assertEqual(intent.arguments["replacement"], "opera")

    def test_normalization(self) -> None:
        self.assertEqual(normalize_text("  PRÓXIMA   MÚSICA! "), "proxima musica")


if __name__ == "__main__":
    unittest.main()
