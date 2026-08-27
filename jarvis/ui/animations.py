from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget


class AnimatedPageStack(QStackedWidget):
    """Pilha de páginas com entrada suave e previsível por opacidade."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_animation: QPropertyAnimation | None = None

    def show_page(self, index: int, *, animate: bool = True) -> None:
        if not 0 <= index < self.count():
            return
        self.setCurrentIndex(index)
        page = self.currentWidget()
        if not animate or page is None:
            return
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(260)
        animation.setStartValue(0.18)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.finished.connect(lambda: page.setGraphicsEffect(None))
        self._page_animation = animation
        animation.start()


class StatusPulse:
    """Mantém o indicador de estado discretamente pulsante."""

    def __init__(self, widget: QWidget) -> None:
        self.effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(self.effect)
        self.animation = QPropertyAnimation(self.effect, b"opacity", widget)
        self.animation.setDuration(1250)
        self.animation.setStartValue(0.48)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.InOutSine)
        self.animation.setLoopCount(-1)
        self.animation.start()


class AnimatedHudBackground(QWidget):
    """Fundo leve com grade técnica e linha de varredura animada."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scan_position = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_scan)
        self._timer.start(45)

    def _advance_scan(self) -> None:
        self._scan_position = (self._scan_position + 2) % max(1, self.height())
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        grid_pen = QPen(QColor(39, 214, 207, 11), 1)
        painter.setPen(grid_pen)
        spacing = 40
        for x in range(0, self.width(), spacing):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), spacing):
            painter.drawLine(0, y, self.width(), y)
        painter.setPen(QPen(QColor(69, 241, 233, 28), 1))
        painter.drawLine(0, self._scan_position, self.width(), self._scan_position)
        painter.end()
