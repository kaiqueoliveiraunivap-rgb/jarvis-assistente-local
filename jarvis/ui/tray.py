from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def create_tray(window, icon: QIcon) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(icon, window)
    tray.setToolTip("J.A.R.V.I.S. — online")
    menu = QMenu()
    show_action = QAction("Abrir J.A.R.V.I.S.", tray)
    show_action.triggered.connect(window.show_and_raise)
    menu.addAction(show_action)
    microphone = QAction("Ativar microfone", tray)
    microphone.setCheckable(True)
    microphone.triggered.connect(window.toggle_voice)
    menu.addAction(microphone)
    silent = QAction("Modo silencioso", tray)
    silent.setCheckable(True)
    silent.triggered.connect(lambda checked: window.send_command("modo silencioso" if checked else "modo normal"))
    menu.addAction(silent)
    menu.addSeparator()
    settings = QAction("Configurações", tray)
    settings.triggered.connect(window.open_settings)
    menu.addAction(settings)
    restart = QAction("Reiniciar J.A.R.V.I.S.", tray)
    restart.triggered.connect(window.restart_application)
    menu.addAction(restart)
    quit_action = QAction("Encerrar", tray)
    quit_action.triggered.connect(window.quit_application)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: window.show_and_raise()
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
    )
    tray.show()
    return tray
