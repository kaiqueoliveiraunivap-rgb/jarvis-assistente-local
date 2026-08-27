from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIRECTORY_NAME = "JARVIS"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def application_directory() -> Path:
    return Path(sys.executable).resolve().parent if is_frozen() else project_root()


def resource_root() -> Path:
    bundled = getattr(sys, "_MEIPASS", None)
    return Path(bundled).resolve() if bundled else project_root()


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def portable_mode() -> bool:
    value = os.getenv("JARVIS_PORTABLE", "").strip().casefold()
    return value in {"1", "true", "yes", "on"} or (
        is_frozen() and (application_directory() / "portable.flag").is_file()
    )


def user_data_root() -> Path:
    override = os.getenv("JARVIS_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if portable_mode():
        return application_directory()
    if is_frozen():
        local_app_data = os.getenv("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("A pasta LOCALAPPDATA do Windows não foi encontrada")
        return Path(local_app_data) / APP_DIRECTORY_NAME
    return project_root()


def settings_path() -> Path:
    root = user_data_root()
    return root / ("config" if is_frozen() or os.getenv("JARVIS_DATA_DIR") else "data") / "settings.json"


def custom_commands_path() -> Path:
    root = user_data_root()
    return root / ("config" if is_frozen() or os.getenv("JARVIS_DATA_DIR") else "data") / "custom_commands.json"


def database_path() -> Path:
    return user_data_root() / "data" / "jarvis.db"


def log_path() -> Path:
    return user_data_root() / "logs" / "jarvis.log"


def screenshot_directory() -> Path:
    return user_data_root() / "data" / "screenshots"


def ensure_user_directories() -> dict[str, Path]:
    root = user_data_root()
    directories = {
        "root": root,
        "config": root / "config",
        "data": root / "data",
        "logs": root / "logs",
        "cache": root / "cache",
        "models": root / "models",
    }
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)
    return directories
