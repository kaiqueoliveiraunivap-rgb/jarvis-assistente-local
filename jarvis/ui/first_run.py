from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWizard, QWizardPage,
)

from jarvis.core.config import AppSettings, ConfigManager, ScreenAwareness
from jarvis.core.config import ProactivityLevel


class FirstRunWizard(QWizard):
    def __init__(self, settings: AppSettings, manager: ConfigManager | None, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.manager = manager
        self.setWindowTitle("Configurar J.A.R.V.I.S.")
        self.resize(650, 430)
        self.addPage(self._welcome_page())
        self.addPage(self._identity_page())
        self.addPage(self._voice_page())
        self.addPage(self._personality_page())
        self.addPage(self._privacy_page())
        self.finished.connect(self._finish)
        self.setStyleSheet("QWizard{background:#08131e;color:#d9f8ff;} QLabel,QCheckBox{color:#d9f8ff;} QLineEdit,QComboBox{background:#102231;color:#d9f8ff;border:1px solid #2c5970;padding:8px;}")

    def _welcome_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Bem-vindo")
        layout = QVBoxLayout(page)
        label = QLabel("Este assistente executa ações locais somente por ferramentas autorizadas.\nMicrofone e tela sempre possuem indicação visível.")
        label.setWordWrap(True)
        layout.addWidget(label)
        return page

    def _identity_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Identidade")
        form = QFormLayout(page)
        self.user_name = QLineEdit(self.settings.user_name)
        self.assistant_name = QLineEdit(self.settings.assistant_name)
        form.addRow("Seu nome", self.user_name)
        form.addRow("Nome do assistente", self.assistant_name)
        return page

    def _voice_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Voz e IA local")
        form = QFormLayout(page)
        self.microphone = QComboBox()
        self.microphone.addItem("Dispositivo padrão", None)
        try:
            from jarvis.voice.microphone import Microphone
            for device in Microphone.devices():
                self.microphone.addItem(device.name, device.index)
        except Exception:
            self.microphone.addItem("Instale requirements-voice.txt para listar", None)
        self.wake_word = QLineEdit(self.settings.voice.wake_word)
        self.model = QLineEdit(self.settings.ai.model)
        self.whisper_model = QComboBox()
        self.whisper_model.addItems(["tiny", "base", "small"])
        self.whisper_model.setCurrentText(self.settings.voice.whisper_model)
        self.voice_name = QComboBox()
        self.voice_name.addItem("Voz padrão do Windows", None)
        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
            pythoncom.CoInitialize()
            sapi = win32com.client.Dispatch("SAPI.SpVoice")
            for voice in sapi.GetVoices():
                description = voice.GetDescription()
                self.voice_name.addItem(description, description)
            pythoncom.CoUninitialize()
        except Exception:
            pass
        self.tts_enabled = QCheckBox("Ativar resposta por voz")
        self.tts_enabled.setChecked(self.settings.voice.tts_enabled)
        form.addRow("Microfone", self.microphone)
        form.addRow("Saída de áudio", QLabel("Dispositivo padrão do Windows"))
        form.addRow("Wake word", self.wake_word)
        form.addRow("Reconhecimento de voz", self.whisper_model)
        form.addRow("Voz", self.voice_name)
        form.addRow("", self.tts_enabled)
        form.addRow("Modelo Ollama", self.model)
        return page

    def _personality_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Personalidade")
        form = QFormLayout(page)
        self.personality_mode = QComboBox()
        self.personality_mode.addItem("Equilibrada", "balanced")
        self.personality_mode.addItem("Formal", "formal")
        self.personality_mode.addItem("Concisa", "concise")
        self.personality_mode.addItem("Bem-humorada", "humorous")
        form.addRow("Estilo", self.personality_mode)
        form.addRow(QLabel("Você poderá ajustar formality, humor, sarcasmo e iniciativa nas configurações."))
        return page

    def _privacy_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Privacidade e presença")
        layout = QVBoxLayout(page)
        self.screen = QCheckBox("Permitir captura de tela somente quando eu pedir")
        self.screen.setChecked(True)
        self.proactive = QComboBox()
        self.proactive.addItem("Desativada", ProactivityLevel.OFF)
        self.proactive.addItem("Baixa", ProactivityLevel.LOW)
        self.proactive.addItem("Normal", ProactivityLevel.NORMAL)
        self.proactive.addItem("Alta", ProactivityLevel.HIGH)
        self.proactive.setCurrentIndex(2)
        self.start_windows = QCheckBox("Iniciar com o Windows")
        layout.addWidget(self.screen)
        layout.addWidget(QLabel("Proatividade e monitoramento"))
        layout.addWidget(self.proactive)
        layout.addWidget(self.start_windows)
        return page

    def _finish(self, result: int) -> None:
        if result != QWizard.Accepted:
            return
        self.settings.user_name = self.user_name.text().strip() or "Usuário"
        self.settings.assistant_name = self.assistant_name.text().strip() or "J.A.R.V.I.S."
        self.settings.voice.microphone = self.microphone.currentData()
        self.settings.voice.wake_word = self.wake_word.text().strip() or "jarvis"
        self.settings.voice.whisper_model = self.whisper_model.currentText()
        self.settings.voice.voice_name = self.voice_name.currentData()
        self.settings.voice.tts_enabled = self.tts_enabled.isChecked()
        self.settings.ai.model = self.model.text().strip() or "qwen3:4b"
        self.settings.privacy.screen_awareness = ScreenAwareness.ON_DEMAND if self.screen.isChecked() else ScreenAwareness.OFF
        self.settings.automation.proactivity = self.proactive.currentData()
        presets = {
            "balanced": (70, 20, 35, 50, 20),
            "formal": (95, 5, 40, 35, 5),
            "concise": (75, 10, 10, 40, 10),
            "humorous": (55, 30, 45, 55, 65),
        }
        values = presets[self.personality_mode.currentData()]
        for name, value in zip(("formality", "sarcasm", "verbosity", "initiative", "humor"), values):
            setattr(self.settings.personality, name, value)
        self.settings.start_with_windows = self.start_windows.isChecked()
        self.settings.first_run_complete = True
        if self.manager:
            self.manager.save(self.settings)
        if self.settings.start_with_windows:
            try:
                from jarvis.computer.startup import configure_startup
                configure_startup(True)
            except Exception:
                self.settings.start_with_windows = False
                if self.manager:
                    self.manager.save(self.settings)
