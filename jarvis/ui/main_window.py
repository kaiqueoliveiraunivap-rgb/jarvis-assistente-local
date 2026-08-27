from __future__ import annotations

import asyncio
import html
import sys
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCloseEvent, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QProgressBar, QSizePolicy, QStackedWidget, QSystemTrayIcon,
    QTextBrowser, QVBoxLayout, QWidget,
)

from jarvis.core.assistant import AssistantResponse, JarvisAssistant
from jarvis.core.event_bus import Event
from jarvis.core.paths import resource_path
from jarvis.core.decision_engine import Decision, DecisionContext, DecisionEngine
from jarvis.core.state_manager import AssistantState
from jarvis.ui.core_visual import CoreVisual
from jarvis.ui.commands_page import CommandsPage
from jarvis.ui.first_run import FirstRunWizard
from jarvis.ui.overlay import StatusOverlay
from jarvis.ui.settings_window import SettingsWindow
from jarvis.ui.tray import create_tray
from jarvis.ui.waveform import Waveform


class Bridge(QObject):
    response = Signal(object)
    state_changed = Signal(str)
    event_received = Signal(object)
    transcription = Signal(str)
    error = Signal(str)
    started = Signal(str)
    voice_status = Signal(bool)


class AssistantRuntime:
    def __init__(self, assistant: JarvisAssistant, bridge: Bridge, monitor: bool) -> None:
        self.assistant = assistant
        self.bridge = bridge
        self.monitor = monitor
        self.loop: asyncio.AbstractEventLoop | None = None
        self.thread = threading.Thread(target=self._thread_main, name="jarvis-runtime", daemon=True)
        self.voice = None
        self.voice_task: asyncio.Task[None] | None = None
        self.greeting = ""
        self._voice_started_once = False

    def start(self) -> None:
        self.thread.start()

    def _thread_main(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.assistant.state.subscribe(lambda change: self.bridge.state_changed.emit(change.current.value))
        self.assistant.events.subscribe(None, lambda event: self.bridge.event_received.emit(event))
        try:
            greeting = self.loop.run_until_complete(self.assistant.start(background_monitor=self.monitor))
            self.greeting = greeting
            self.bridge.started.emit(greeting)
            self.loop.run_forever()
        except Exception as exc:
            self.bridge.error.emit(str(exc))
        finally:
            if self.assistant.state.state.value != "OFFLINE":
                self.loop.run_until_complete(self.assistant.stop())
            self.loop.close()

    def submit(self, text: str) -> None:
        if not self.loop:
            self.bridge.error.emit("O núcleo ainda está iniciando.")
            return
        future = asyncio.run_coroutine_threadsafe(self.assistant.handle_text(text), self.loop)

        def complete(done) -> None:
            try:
                self.bridge.response.emit(done.result())
            except Exception as exc:
                self.bridge.error.emit(str(exc))
        future.add_done_callback(complete)

    def start_voice(self) -> None:
        if not self.loop:
            return

        async def start() -> None:
            if self.voice_task and not self.voice_task.done():
                return
            try:
                from jarvis.voice.microphone import Microphone
                await asyncio.to_thread(Microphone.devices)
                from jarvis.voice.voice_manager import VoiceManager
                self.voice = VoiceManager(self.assistant.settings.voice)
            except Exception as exc:
                self.bridge.error.emit(str(exc))
                self.bridge.voice_status.emit(False)
                return

            async def handle(text: str) -> str:
                response = await self.assistant.handle_text(text)
                self.bridge.response.emit(response)
                return "" if self.assistant.settings.mode == "SILENT" else response.text

            async def woke() -> None:
                self.bridge.state_changed.emit("LISTENING")

            try:
                if not self._voice_started_once and self.greeting and self.assistant.settings.mode != "SILENT":
                    await self.assistant.state.transition(AssistantState.SPEAKING, "Saudação inicial")
                    await self.voice.speak(self.greeting)
                    await self.assistant.state.transition(AssistantState.STANDBY, "Wake word em espera")
                self._voice_started_once = True
                self.bridge.voice_status.emit(True)
                self.voice_task = asyncio.create_task(
                    self.voice.run_forever(
                        handle, on_wake=woke, on_transcription=self.bridge.transcription.emit,
                        on_error=lambda exc: self.bridge.error.emit(str(exc)),
                    )
                )
            except Exception as exc:
                self.bridge.error.emit(f"Voz indisponível: {exc}")
                self.bridge.voice_status.emit(False)
        asyncio.run_coroutine_threadsafe(start(), self.loop)

    def stop_voice(self) -> None:
        if not self.loop:
            return

        def stop() -> None:
            if self.voice:
                self.voice.stop()
            if self.voice_task:
                self.voice_task.cancel()
            self.bridge.voice_status.emit(False)
        self.loop.call_soon_threadsafe(stop)

    def stop(self) -> None:
        if not self.loop:
            return
        self.stop_voice()

        async def shutdown() -> None:
            await self.assistant.stop()
            self.loop.stop()
        asyncio.run_coroutine_threadsafe(shutdown(), self.loop)


class MetricCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        self.title = QLabel(title)
        self.value = QLabel("—")
        self.value.setObjectName("metricValue")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.bar)

    def set_value(self, value: float | None, suffix: str = "%") -> None:
        if value is None:
            self.value.setText("—")
            self.bar.setValue(0)
            return
        self.value.setText(f"{value:.0f}{suffix}")
        self.bar.setValue(round(value))


class MainWindow(QMainWindow):
    def __init__(self, assistant: JarvisAssistant, monitor: bool = True) -> None:
        super().__init__()
        self.assistant = assistant
        self._quitting = False
        self._voice_active = False
        self.decision_engine = DecisionEngine()
        self.setWindowTitle("J.A.R.V.I.S.")
        self.resize(1180, 760)
        self.setMinimumSize(940, 620)
        self.bridge = Bridge()
        self.runtime = AssistantRuntime(assistant, self.bridge, monitor)
        self.overlay = StatusOverlay()
        self._build_ui()
        self._connect()
        self.tray = create_tray(self, self.windowIcon())
        self.runtime.start()
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start(1500)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(lambda: self.clock.setText(datetime.now().strftime("%H:%M:%S")))
        self._clock_timer.start(1000)

    def _build_ui(self) -> None:
        icon_path = resource_path("assets", "jarvis.ico")
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            icon = QPixmap(64, 64)
            icon.fill(Qt.transparent)
            painter = QPainter(icon)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor("#48e5ff"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(8, 8, 48, 48)
            painter.setBrush(QColor("#07131e"))
            painter.drawEllipse(18, 18, 28, 28)
            painter.end()
            self.setWindowIcon(QIcon(icon))

        root = QWidget()
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(208)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 24, 18, 20)
        side.setSpacing(8)
        monogram = QLabel("J")
        monogram.setObjectName("monogram")
        brand_side = QLabel("J.A.R.V.I.S.")
        brand_side.setObjectName("sideBrand")
        caption = QLabel("LOCAL INTELLIGENCE")
        caption.setObjectName("muted")
        side.addWidget(monogram, 0, Qt.AlignLeft)
        side.addWidget(brand_side)
        side.addWidget(caption)
        side.addSpacing(25)
        self.dashboard_nav = QPushButton("◉   CENTRAL")
        self.commands_nav = QPushButton("⌁   COMANDOS")
        self.settings_nav = QPushButton("⚙   AJUSTES")
        self.dashboard_nav.setObjectName("navButton")
        self.commands_nav.setObjectName("navButton")
        self.settings_nav.setObjectName("navButton")
        for button in (self.dashboard_nav, self.commands_nav):
            button.setCheckable(True)
            side.addWidget(button)
        side.addWidget(self.settings_nav)
        side.addStretch()
        side_status = QLabel("●  SISTEMA LOCAL\n    CONEXÃO SEGURA")
        side_status.setObjectName("sideStatus")
        side.addWidget(side_status)
        shell.addWidget(sidebar)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(24, 18, 24, 22)
        main.setSpacing(14)
        header = QHBoxLayout()
        brand = QLabel("J.A.R.V.I.S.")
        brand.setObjectName("brand")
        self.state_label = QLabel("● STARTING")
        self.state_label.setObjectName("state")
        self.clock = QLabel("--:--:--")
        self.clock.setObjectName("clock")
        model = QLabel(f"LOCAL CORE  /  {self.assistant.settings.ai.model}")
        model.setObjectName("model")
        header.addWidget(brand)
        header.addWidget(self.state_label)
        header.addStretch()
        header.addWidget(model)
        header.addWidget(self.clock)
        main.addLayout(header)

        self.pages = QStackedWidget()
        dashboard = QWidget()
        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        left = QFrame()
        left.setObjectName("panel")
        left_layout = QVBoxLayout(left)
        self.core = CoreVisual()
        self.waveform = Waveform()
        left_layout.addWidget(self.core, 1)
        left_layout.addWidget(self.waveform)
        tools_row = QHBoxLayout()
        self.mic_button = QPushButton("MIC  OFF")
        self.mic_button.setCheckable(True)
        self.silent_button = QPushButton("SILENT")
        self.silent_button.setCheckable(True)
        screenshot = QPushButton("CAPTURE")
        settings = QPushButton("SETTINGS")
        screenshot.clicked.connect(lambda: self.send_command("tire uma screenshot"))
        settings.clicked.connect(self.open_settings)
        tools_row.addWidget(self.mic_button)
        tools_row.addWidget(self.silent_button)
        tools_row.addWidget(screenshot)
        tools_row.addWidget(settings)
        left_layout.addLayout(tools_row)
        grid.addWidget(left, 0, 0, 2, 1)

        metrics = QHBoxLayout()
        self.cpu = MetricCard("CPU")
        self.ram = MetricCard("MEMORY")
        self.disk = MetricCard("DISK")
        self.battery = MetricCard("BATTERY")
        for card in (self.cpu, self.ram, self.disk, self.battery):
            metrics.addWidget(card)
        grid.addLayout(metrics, 0, 1)

        chat_panel = QFrame()
        chat_panel.setObjectName("panel")
        chat_layout = QVBoxLayout(chat_panel)
        title = QLabel("LIVE CONSOLE")
        title.setObjectName("sectionTitle")
        self.history = QTextBrowser()
        self.history.setOpenExternalLinks(False)
        self.history.setPlaceholderText("O sistema está iniciando…")
        command_row = QHBoxLayout()
        self.command = QLineEdit()
        self.command.setPlaceholderText("Digite um comando ou converse com J.A.R.V.I.S.")
        send = QPushButton("ENVIAR")
        send.setObjectName("primary")
        command_row.addWidget(self.command, 1)
        command_row.addWidget(send)
        chat_layout.addWidget(title)
        chat_layout.addWidget(self.history, 1)
        chat_layout.addLayout(command_row)
        grid.addWidget(chat_panel, 1, 1)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 7)
        grid.setRowStretch(1, 1)
        dashboard_layout.addLayout(grid, 1)
        self.pages.addWidget(dashboard)
        self.commands_page = CommandsPage(self.assistant.macros, self.assistant.registry)
        self.pages.addWidget(self.commands_page)
        main.addWidget(self.pages, 1)
        shell.addWidget(content, 1)

        self.command.returnPressed.connect(self._submit)
        send.clicked.connect(self._submit)
        self.mic_button.toggled.connect(self.toggle_voice)
        self.silent_button.toggled.connect(lambda checked: self.send_command("modo silencioso" if checked else "modo normal"))
        self.dashboard_nav.clicked.connect(lambda: self._switch_page(0))
        self.commands_nav.clicked.connect(lambda: self._switch_page(1))
        self.settings_nav.clicked.connect(self.open_settings)
        self.commands_page.command_created.connect(
            lambda name: self._append("system", f"Comando {name} salvo e pronto para uso.")
        )
        self.commands_page.command_deleted.connect(
            lambda name: self._append("system", f"Comando {name} removido.")
        )
        self._switch_page(0)
        self.setStyleSheet(self._stylesheet())

    def _switch_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.dashboard_nav.setChecked(index == 0)
        self.commands_nav.setChecked(index == 1)

    def _connect(self) -> None:
        self.bridge.started.connect(self._on_started)
        self.bridge.response.connect(self._on_response)
        self.bridge.state_changed.connect(self._on_state)
        self.bridge.transcription.connect(self._on_transcription)
        self.bridge.error.connect(self._on_error)
        self.bridge.event_received.connect(self._on_event)
        self.bridge.voice_status.connect(self._set_voice_button)

    def _on_started(self, greeting: str) -> None:
        self._append("jarvis", greeting)
        self.state_label.setText("● STANDBY")
        if self.assistant.settings.voice.enabled:
            QTimer.singleShot(250, lambda: self.toggle_voice(True))

    def _submit(self) -> None:
        text = self.command.text().strip()
        if text:
            self.command.clear()
            self.send_command(text)

    def send_command(self, text: str) -> None:
        self._append("user", text)
        self.runtime.submit(text)

    def _on_response(self, response: AssistantResponse) -> None:
        self._append("jarvis", response.text, error=not response.success and not response.confirmation_required)
        if response.confirmation_required:
            self.overlay.show_status("CONFIRMATION", response.text, 6000)

    def _on_state(self, state: str) -> None:
        self.state_label.setText(f"● {state}")
        self.core.set_state(state)

    def _on_transcription(self, text: str) -> None:
        self.core.set_audio_level(0.8)
        self.waveform.set_level(0.8)
        self.overlay.show_status("LISTENING", text)
        self._append("user", text)

    def _on_error(self, message: str) -> None:
        self._append("system", message, error=True)
        self.tray.showMessage("J.A.R.V.I.S.", message, QSystemTrayIcon.Warning, 5000) if hasattr(self, "tray") else None

    def _on_event(self, event: Event) -> None:
        monitored_alerts = {"HIGH_RAM", "HIGH_CPU", "LOW_DISK", "LOW_BATTERY"}
        if event.type.value in monitored_alerts and event.importance < self.assistant.settings.automation.alert_threshold:
            return
        decision = self.decision_engine.decide(DecisionContext(
            event.importance,
            self.assistant.settings.automation.proactivity,
            self.assistant.settings.mode,
        ))
        if decision is not Decision.IGNORE:
            messages = {
                "HIGH_RAM": f"Memória em {event.payload.get('percent', '?')}%.",
                "HIGH_CPU": f"CPU em {event.payload.get('percent', '?')}%.",
                "LOW_DISK": f"Disco em {event.payload.get('percent', '?')}%.",
                "LOW_BATTERY": f"Bateria em {event.payload.get('percent', '?')}%.",
                "USER_RETURNED": "Bem-vindo de volta.",
                "ROUTINE_SUGGESTION": str(event.payload.get("message", "Rotina detectada.")),
            }
            message = messages.get(event.type.value)
            if message:
                self._append("system", message)
                self.overlay.show_status("ALERT", message, 7000)

    def _append(self, role: str, text: str, error: bool = False) -> None:
        colors = {"user": "#8ea8b8", "jarvis": "#d7faff", "system": "#f3c969"}
        label = {"user": "VOCÊ", "jarvis": "J.A.R.V.I.S.", "system": "SISTEMA"}.get(role, role.upper())
        color = "#ff7487" if error else colors.get(role, "#d7faff")
        self.history.append(
            f'<div style="margin:7px 0"><span style="color:#48e5ff;font-size:10px;letter-spacing:1px">{label}</span><br>'
            f'<span style="color:{color}">{html.escape(text)}</span></div>'
        )
        self.history.verticalScrollBar().setValue(self.history.verticalScrollBar().maximum())

    def _refresh_stats(self) -> None:
        try:
            import psutil  # type: ignore
            self.cpu.set_value(psutil.cpu_percent())
            self.ram.set_value(psutil.virtual_memory().percent)
            self.disk.set_value(psutil.disk_usage("C:\\").percent)
            battery = psutil.sensors_battery()
            self.battery.set_value(battery.percent if battery else None)
        except ImportError:
            self.cpu.set_value(None)
            self.ram.set_value(None)
            self.disk.set_value(None)
            self.battery.set_value(None)
        if self.runtime.voice:
            level = self.runtime.voice.microphone.level
            self.core.set_audio_level(level)
            self.waveform.set_level(level)

    def toggle_voice(self, enabled: bool) -> None:
        self._voice_active = bool(enabled)
        self._set_voice_button(self._voice_active)
        if self._voice_active:
            self.runtime.start_voice()
        else:
            self.runtime.stop_voice()

    def _set_voice_button(self, enabled: bool) -> None:
        self._voice_active = enabled
        self.mic_button.blockSignals(True)
        self.mic_button.setChecked(self._voice_active)
        self.mic_button.setText("MIC  ON" if self._voice_active else "MIC  OFF")
        self.mic_button.blockSignals(False)

    def open_settings(self) -> None:
        dialog = SettingsWindow(self.assistant.settings, self.assistant.config_manager, self)
        if dialog.exec():
            voice_was_active = self._voice_active
            if voice_was_active:
                self.runtime.stop_voice()
                QTimer.singleShot(300, self.runtime.start_voice)
            self._append("system", "Configurações salvas. A voz será recarregada automaticamente.")

    def show_and_raise(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def quit_application(self) -> None:
        self._quitting = True
        self.runtime.stop()
        QApplication.instance().quit()

    def restart_application(self) -> None:
        if QProcess.startDetached(sys.executable, sys.argv):
            self.quit_application()
        else:
            self._on_error("Não consegui reiniciar o aplicativo.")

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._quitting:
            event.accept()
        else:
            event.ignore()
            self.hide()
            self.tray.showMessage("J.A.R.V.I.S.", "Continuo disponível na bandeja.", QSystemTrayIcon.Information, 2500)

    @staticmethod
    def _stylesheet() -> str:
        return """
            QMainWindow, QWidget { background:#04090e; color:#c9edf2; font-family:'Segoe UI'; font-size:13px; }
            QFrame#sidebar { background:#061119; border-right:1px solid #123846; }
            QLabel#monogram { color:#52f6ec; background:#0a2630; border:2px solid #29d8d1; border-radius:27px;
                              min-width:54px; min-height:54px; max-width:54px; max-height:54px;
                              font-size:28px; font-weight:700; qproperty-alignment:AlignCenter; }
            QLabel#sideBrand { color:#e7ffff; font-size:16px; font-weight:700; letter-spacing:3px; }
            QLabel#sideStatus { color:#3dd9d2; font:10px 'Consolas'; line-height:18px; }
            QLabel#brand { color:#e7ffff; font-size:21px; font-weight:600; letter-spacing:5px; }
            QLabel#state { color:#52f6ec; padding-left:18px; font-size:11px; letter-spacing:1px; }
            QLabel#model, QLabel#muted { color:#567984; font-size:10px; letter-spacing:1px; }
            QLabel#clock { color:#8fe4e2; font:18px 'Consolas'; padding-left:18px; }
            QLabel#pageTitle { color:#e7ffff; font-size:25px; font-weight:600; }
            QFrame#panel, QFrame#metricCard { background:#07141d; border:1px solid #123744; border-radius:3px; }
            QFrame#metricCard { min-width:110px; border-top:2px solid #27cfc9; }
            QLabel#metricValue { color:#e8ffff; font-size:23px; font-weight:600; }
            QLabel#sectionTitle { color:#52f6ec; font-size:10px; letter-spacing:2px; }
            QProgressBar { background:#0d2730; border:0; height:3px; }
            QProgressBar::chunk { background:#39e0d9; }
            QTextBrowser, QTextEdit, QListWidget { background:#040d13; border:1px solid #102d38; padding:8px; color:#c9edf2; }
            QListWidget#commandList::item { border-bottom:1px solid #12313b; padding:14px 10px; }
            QListWidget#commandList::item:selected { background:#0d3038; color:#eaffff; border-left:3px solid #43ebe4; }
            QLineEdit, QComboBox { background:#061119; border:1px solid #1b4653; border-radius:3px; padding:10px; color:#e1fbff; }
            QLineEdit:focus, QComboBox:focus { border-color:#43ebe4; }
            QPushButton { background:#0b2029; border:1px solid #24515d; border-radius:3px; padding:10px 13px; color:#9edfe1; font-size:10px; letter-spacing:1px; }
            QPushButton:hover, QPushButton:checked { color:#031013; background:#43ebe4; border-color:#43ebe4; }
            QPushButton#primary { background:#0c4c52; color:#e8ffff; border-color:#32cfc9; }
            QPushButton#danger { color:#ff8995; border-color:#773845; }
            QPushButton#navButton { text-align:left; border:0; border-left:2px solid transparent; padding:12px 10px; background:transparent; }
            QPushButton#navButton:hover { color:#58f3ec; background:#091c24; }
            QPushButton#navButton:checked { color:#58f3ec; background:#0b252d; border-left-color:#58f3ec; }
        """


def launch(
    assistant: JarvisAssistant,
    monitor: bool = True,
    background: bool = False,
    smoke_output: Path | None = None,
) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("J.A.R.V.I.S.")
    icon_path = resource_path("assets", "jarvis.ico")
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setQuitOnLastWindowClosed(False)
    if not assistant.settings.first_run_complete:
        wizard = FirstRunWizard(assistant.settings, assistant.config_manager)
        wizard.exec()
        # Recria serviços ainda não iniciados para aplicar modelo e privacidade escolhidos.
        assistant = JarvisAssistant(assistant.settings, assistant.database, assistant.config_manager)
    window = MainWindow(assistant, monitor)
    if not background:
        window.show()
    if smoke_output:
        window.overlay.show_status("SMOKE TEST", "Overlay, tray e interface inicializados.", 1800)
        def finish_smoke() -> None:
            smoke_output.parent.mkdir(parents=True, exist_ok=True)
            if not window.grab().save(str(smoke_output), "PNG"):
                window._on_error(f"Não foi possível salvar smoke test em {smoke_output}")
            window.quit_application()
        QTimer.singleShot(2200, finish_smoke)
    return app.exec()
