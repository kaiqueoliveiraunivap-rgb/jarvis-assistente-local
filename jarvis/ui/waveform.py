from __future__ import annotations

import math
from collections import deque

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class Waveform(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(54)
        self._level = 0.0
        self._phase = 0.0
        self._values: deque[float] = deque([0.0] * 72, maxlen=72)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(float(level), 1.0))

    def _tick(self) -> None:
        self._phase += 0.22
        idle = 0.025 + abs(math.sin(self._phase)) * 0.025
        self._values.append(max(self._level, idle))
        self._level *= 0.86
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#45dff7"), 1.6))
        middle = self.height() / 2
        step = self.width() / max(1, len(self._values) - 1)
        points = []
        for index, value in enumerate(self._values):
            amplitude = value * self.height() * 0.42
            y = middle + math.sin(index * 0.8 + self._phase) * amplitude
            points.append((index * step, y))
        for first, second in zip(points, points[1:]):
            painter.drawLine(int(first[0]), int(first[1]), int(second[0]), int(second[1]))

