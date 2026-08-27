from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class StatusOverlay(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(360, 110)
        layout = QVBoxLayout(self)
        self.state_label = QLabel("◉ STANDBY")
        self.text_label = QLabel("")
        self.text_label.setWordWrap(True)
        layout.addWidget(self.state_label)
        layout.addWidget(self.text_label)
        self.setStyleSheet(
            "QWidget {background: rgba(7, 18, 29, 228); border: 1px solid rgba(72,229,255,150); border-radius: 14px;}"
            "QLabel {background: transparent; border: none; color: #d7faff; padding: 2px 10px; font: 12px 'Segoe UI';}"
        )
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_status(self, state: str, text: str = "", timeout_ms: int = 3200) -> None:
        self.state_label.setText(f"◉ {state}")
        self.text_label.setText(text)
        screen = self.screen().availableGeometry()
        self.move(screen.right() - self.width() - 24, screen.bottom() - self.height() - 24)
        self.show()
        self.raise_()
        self._timer.start(timeout_ms)

