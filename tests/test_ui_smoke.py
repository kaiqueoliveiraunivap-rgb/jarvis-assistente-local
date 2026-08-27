from __future__ import annotations

import importlib.util
import os
import unittest


PYSIDE_AVAILABLE = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 não instalado")
class UISmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_core_and_waveform_render(self) -> None:
        from PySide6.QtGui import QImage
        from jarvis.ui.core_visual import CoreVisual
        from jarvis.ui.waveform import Waveform

        for widget in (CoreVisual(), Waveform()):
            widget.resize(420, max(widget.minimumHeight(), 160))
            image = QImage(widget.size(), QImage.Format_ARGB32)
            image.fill(0)
            widget.render(image)
            self.assertFalse(image.isNull())

    def test_settings_dialog_constructs(self) -> None:
        from jarvis.core.config import AppSettings
        from jarvis.ui.settings_window import SettingsWindow

        dialog = SettingsWindow(AppSettings(), None)
        self.assertGreaterEqual(dialog.width(), 600)
        dialog.close()

    def test_commands_page_constructs_and_lists_macros(self) -> None:
        import tempfile
        from pathlib import Path

        from jarvis.automation.macros import MacroManager
        from jarvis.core.config import AppSettings
        from jarvis.tools.builtin_tools import build_registry
        from jarvis.ui.commands_page import CommandsPage

        with tempfile.TemporaryDirectory() as directory:
            registry = build_registry(AppSettings())
            macros = MacroManager(registry, Path(directory) / "commands.json")
            macros.load()
            macros.create(
                "teste", [{"tool": "open_app", "args": {"name": "notepad"}}],
                ["executar teste"], "Comando de teste",
            )
            page = CommandsPage(macros, registry)
            self.assertEqual(page.command_list.count(), 1)
            page.close()


if __name__ == "__main__":
    unittest.main()
