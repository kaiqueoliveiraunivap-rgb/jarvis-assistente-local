from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget


class CoreVisual(QWidget):
    SPEED = {
        "STANDBY": 0.25, "IDLE": 0.3, "LISTENING": 1.1, "THINKING": 1.6,
        "PLANNING": 1.8, "EXECUTING": 1.25, "SPEAKING": 1.0, "ALERT": 2.3,
        "ERROR": 0.4, "SLEEPING": 0.08,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.state = "OFFLINE"
        self.audio_level = 0.0
        self.phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_state(self, state: str) -> None:
        self.state = state
        self.update()

    def set_audio_level(self, level: float) -> None:
        self.audio_level = max(0.0, min(float(level), 1.0))

    def _tick(self) -> None:
        self.phase = (self.phase + self.SPEED.get(self.state, 0.4)) % 360
        self.audio_level *= 0.91
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) * 0.32
        color = QColor("#ff5c72") if self.state in {"ALERT", "ERROR"} else QColor("#48e5ff")
        pulse = math.sin(math.radians(self.phase * 3)) * 4 + self.audio_level * 20

        glow = QRadialGradient(center, radius * 1.35)
        glow.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 85))
        glow.setColorAt(0.45, QColor(color.red(), color.green(), color.blue(), 25))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(center, radius * 1.35 + pulse, radius * 1.35 + pulse)

        for index, scale in enumerate((1.0, 0.78, 0.52)):
            alpha = 180 - index * 38
            pen = QPen(QColor(color.red(), color.green(), color.blue(), alpha), 2.0 if index == 0 else 1.2)
            pen.setDashPattern([8 + index * 3, 6 + index])
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            size = (radius + pulse * (0.4 + index * 0.2)) * scale
            rectangle = QRectF(center.x() - size, center.y() - size, size * 2, size * 2)
            span = 210 * 16 if index == 0 else 285 * 16
            direction = 1 if index % 2 == 0 else -1
            painter.drawArc(rectangle, int((self.phase * direction + index * 70) * 16), span)

        inner = radius * 0.36 + pulse * 0.15
        core_gradient = QRadialGradient(center, inner)
        core_gradient.setColorAt(0, QColor(225, 252, 255, 245))
        core_gradient.setColorAt(0.28, color)
        core_gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 12))
        painter.setPen(QPen(QColor(185, 248, 255, 170), 1.2))
        painter.setBrush(core_gradient)
        painter.drawEllipse(center, inner, inner)

        painter.setPen(QColor("#d7faff"))
        font = painter.font()
        font.setFamily("Segoe UI")
        font.setPixelSize(12)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        painter.setFont(font)
        label_rect = QRectF(0, center.y() + radius + 22, self.width(), 28)
        painter.drawText(label_rect, Qt.AlignCenter, self.state)
