from __future__ import annotations

import os
import sys
from pathlib import Path

from jarvis.core.paths import application_directory, is_frozen


STARTUP_FILE = "JARVIS_startup.cmd"


def startup_directory() -> Path:
    appdata = os.getenv("APPDATA")
    if not appdata:
        raise RuntimeError("A pasta APPDATA do Windows não foi encontrada")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def configure_startup(enabled: bool, start_script: Path | str | None = None) -> Path:
    destination = startup_directory() / STARTUP_FILE
    if enabled:
        if start_script:
            command = f'"{Path(start_script).resolve()}" --background'
        elif is_frozen():
            command = f'"{Path(sys.executable).resolve()}" --background'
        else:
            script = application_directory() / "start_jarvis.bat"
            if not script.is_file():
                raise FileNotFoundError(f"Script de inicialização não encontrado: {script}")
            command = f'"{script.resolve()}" --background'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            f'@echo off\nstart "" {command}\n',
            encoding="utf-8",
        )
    elif destination.exists():
        destination.unlink()
    return destination


def startup_enabled() -> bool:
    return (startup_directory() / STARTUP_FILE).is_file()
