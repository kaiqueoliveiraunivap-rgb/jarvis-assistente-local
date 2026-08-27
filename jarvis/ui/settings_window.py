from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QMessageBox, QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from jarvis.core.config import AppSettings, ConfigManager, ProactivityLevel, ScreenAwareness


class SettingsWindow(QDialog):
    def __init__(self, settings: AppSettings, manager: ConfigManager | None, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.manager = manager
        self.setWindowTitle("Configurações — J.A.R.V.I.S.")
        self.resize(620, 520)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        general = QWidget()
        general_form = QFormLayout(general)
        self.user_name = QLineEdit(settings.user_name)
        self.assistant_name = QLineEdit(settings.assistant_name)
        self.start_windows = QCheckBox("Iniciar com o Windows")
        self.start_windows.setChecked(settings.start_with_windows)
        general_form.addRow("Seu nome", self.user_name)
        general_form.addRow("Assistente", self.assistant_name)
        general_form.addRow("Inicialização", self.start_windows)
        tabs.addTab(general, "Geral")

        voice = QWidget()
        voice_form = QFormLayout(voice)
        self.microphone = QLineEdit(settings.voice.microphone or "")
        self.wake_word = QLineEdit(settings.voice.wake_word)
        self.whisper_model = QComboBox()
        self.whisper_model.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.whisper_model.setCurrentText(settings.voice.whisper_model)
        self.tts_enabled = QCheckBox("Resposta falada")
        self.tts_enabled.setChecked(settings.voice.tts_enabled)
        self.voice_volume = QSpinBox()
        self.voice_volume.setRange(0, 100)
        self.voice_volume.setValue(settings.voice.volume)
        self.voice_name = QComboBox()
        self.voice_name.addItem("Automática (priorizar português do Brasil)", "")
        try:
            from jarvis.voice.text_to_speech import list_installed_voices
            for voice_name in list_installed_voices():
                self.voice_name.addItem(voice_name, voice_name)
        except Exception:
            pass
        selected_voice = settings.voice.voice_name or ""
        selected_index = self.voice_name.findData(selected_voice)
        if selected_voice and selected_index < 0:
            self.voice_name.addItem(selected_voice, selected_voice)
            selected_index = self.voice_name.count() - 1
        self.voice_name.setCurrentIndex(max(0, selected_index))
        self.voice_speed = QSlider(Qt.Horizontal)
        self.voice_speed.setRange(70, 120)
        self.voice_speed.setValue(round(settings.voice.speed * 100))
        self.voice_speed.setToolTip(f"{self.voice_speed.value()}%")
        self.voice_speed.valueChanged.connect(
            lambda value: self.voice_speed.setToolTip(f"{value}%")
        )
        self.piper_model = QLineEdit(settings.voice.piper_model or "")
        voice_form.addRow("Microfone (nome/índice)", self.microphone)
        voice_form.addRow("Wake word", self.wake_word)
        voice_form.addRow("Whisper", self.whisper_model)
        voice_form.addRow("Piper .onnx", self.piper_model)
        voice_form.addRow("Voz", self.voice_name)
        voice_form.addRow("Ritmo natural", self.voice_speed)
        voice_form.addRow("Volume da voz", self.voice_volume)
        voice_form.addRow("TTS", self.tts_enabled)
        tabs.addTab(voice, "Voz")

        ai = QWidget()
        ai_form = QFormLayout(ai)
        self.provider = QComboBox()
        self.provider.addItem("ollama")
        self.model = QLineEdit(settings.ai.model)
        self.vision_model = QLineEdit(settings.ai.vision_model or "")
        self.endpoint = QLineEdit(settings.ai.endpoint)
        ai_form.addRow("Provider", self.provider)
        ai_form.addRow("Modelo", self.model)
        ai_form.addRow("Modelo visual", self.vision_model)
        ai_form.addRow("Endpoint", self.endpoint)
        tabs.addTab(ai, "IA")

        personality = QWidget()
        personality_form = QFormLayout(personality)
        self.personality_sliders: dict[str, QSlider] = {}
        for name, label in (("formality", "Formalidade"), ("sarcasm", "Sarcasmo"), ("humor", "Humor"),
                            ("verbosity", "Verbosidade"), ("initiative", "Iniciativa")):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(getattr(settings.personality, name))
            slider.setToolTip(str(slider.value()))
            slider.valueChanged.connect(lambda value, target=slider: target.setToolTip(str(value)))
            personality_form.addRow(label, slider)
            self.personality_sliders[name] = slider
        tabs.addTab(personality, "Personalidade")

        privacy = QWidget()
        privacy_form = QFormLayout(privacy)
        self.screen_mode = QComboBox()
        self.screen_mode.addItems([item.value for item in ScreenAwareness])
        self.screen_mode.setCurrentText(settings.privacy.screen_awareness.value)
        self.camera = QCheckBox("Permitir câmera (continua exigindo indicador)")
        self.camera.setChecked(settings.privacy.camera_enabled)
        self.history = QCheckBox("Salvar histórico local")
        self.history.setChecked(settings.privacy.save_history)
        self.memory = QCheckBox("Memória persistente")
        self.memory.setChecked(settings.privacy.memory_enabled)
        privacy_form.addRow("Análise de tela", self.screen_mode)
        privacy_form.addRow("Câmera", self.camera)
        privacy_form.addRow("Histórico", self.history)
        privacy_form.addRow("Memória", self.memory)
        tabs.addTab(privacy, "Privacidade")

        automation = QWidget()
        automation_form = QFormLayout(automation)
        self.proactivity = QComboBox()
        self.proactivity.addItems([item.value for item in ProactivityLevel])
        self.proactivity.setCurrentText(settings.automation.proactivity.value)
        self.threshold = QSpinBox()
        self.threshold.setRange(0, 100)
        self.threshold.setValue(settings.automation.alert_threshold)
        automation_form.addRow("Proatividade", self.proactivity)
        automation_form.addRow("Limiar de alerta", self.threshold)
        tabs.addTab(automation, "Automação")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setStyleSheet("QDialog,QWidget{background:#09131e;color:#d9f8ff;} QLineEdit,QComboBox,QSpinBox{background:#101f2c;border:1px solid #24465c;padding:7px;border-radius:5px;} QTabBar::tab:selected{color:#48e5ff;}")

    def _save(self) -> None:
        previous_startup = self.settings.start_with_windows
        self.settings.user_name = self.user_name.text().strip() or "Usuário"
        self.settings.assistant_name = self.assistant_name.text().strip() or "J.A.R.V.I.S."
        self.settings.start_with_windows = self.start_windows.isChecked()
        microphone = self.microphone.text().strip()
        self.settings.voice.microphone = int(microphone) if microphone.isdigit() else (microphone or None)
        self.settings.voice.wake_word = self.wake_word.text().strip() or "jarvis"
        self.settings.voice.whisper_model = self.whisper_model.currentText()
        self.settings.voice.tts_enabled = self.tts_enabled.isChecked()
        self.settings.voice.volume = self.voice_volume.value()
        self.settings.voice.voice_name = str(self.voice_name.currentData() or "") or None
        self.settings.voice.speed = self.voice_speed.value() / 100
        self.settings.voice.piper_model = self.piper_model.text().strip() or None
        self.settings.ai.provider = self.provider.currentText()
        self.settings.ai.model = self.model.text().strip()
        self.settings.ai.vision_model = self.vision_model.text().strip() or None
        self.settings.ai.endpoint = self.endpoint.text().strip()
        for name, slider in self.personality_sliders.items():
            setattr(self.settings.personality, name, slider.value())
        self.settings.privacy.screen_awareness = ScreenAwareness(self.screen_mode.currentText())
        self.settings.privacy.camera_enabled = self.camera.isChecked()
        self.settings.privacy.save_history = self.history.isChecked()
        self.settings.privacy.memory_enabled = self.memory.isChecked()
        self.settings.automation.proactivity = ProactivityLevel(self.proactivity.currentText())
        self.settings.automation.alert_threshold = self.threshold.value()
        if self.manager:
            self.manager.save(self.settings)
        if previous_startup != self.settings.start_with_windows:
            from jarvis.computer.startup import configure_startup
            try:
                configure_startup(self.settings.start_with_windows)
            except Exception as exc:
                # A configuração permanece salva; o diagnóstico mostrará o problema de startup.
                self.settings.start_with_windows = False
                if self.manager:
                    self.manager.save(self.settings)
                QMessageBox.warning(self, "Inicialização com Windows", str(exc))
        self.accept()
