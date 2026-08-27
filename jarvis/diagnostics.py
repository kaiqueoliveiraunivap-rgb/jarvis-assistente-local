from __future__ import annotations

import argparse
import asyncio
import importlib.util
import platform
import sys
from dataclasses import dataclass
from pathlib import Path

from jarvis.ai.ollama_client import OllamaClient
from jarvis.core.config import ConfigManager
from jarvis.database.database import Database


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _module(name: str, required: bool = True) -> Check:
    available = importlib.util.find_spec(name) is not None
    return Check(name, available, "instalado" if available else "ausente", required)


async def run_checks(config_path: Path | None = None) -> list[Check]:
    checks = [
        Check("Python", sys.version_info >= (3, 12), platform.python_version()),
        Check("Windows", platform.system() == "Windows", platform.platform()),
    ]
    try:
        manager = ConfigManager(config_path)
        settings = manager.load()
        checks.append(Check("Configuração", True, str(manager.path)))
    except Exception as exc:
        checks.append(Check("Configuração", False, str(exc)))
        settings = ConfigManager(config_path).settings
    try:
        database = Database()
        database.initialize()
        database.execute("SELECT 1")
        checks.append(Check("SQLite", True, str(database.path)))
    except Exception as exc:
        checks.append(Check("SQLite", False, str(exc)))

    checks.extend((
        _module("PySide6"), _module("psutil"), _module("PIL"), _module("pyautogui"),
        _module("win32com"), _module("pycaw"), _module("screen_brightness_control"),
        _module("sounddevice", required=False), _module("faster_whisper", required=False),
        _module("openwakeword", required=False),
    ))
    if importlib.util.find_spec("sounddevice"):
        try:
            from jarvis.voice.microphone import Microphone
            devices = Microphone.devices()
            checks.append(Check("Microfone", bool(devices), f"{len(devices)} dispositivo(s)", required=False))
        except Exception as exc:
            checks.append(Check("Microfone", False, str(exc), required=False))
    if importlib.util.find_spec("openwakeword"):
        try:
            import openwakeword  # type: ignore
            wake_paths = openwakeword.get_pretrained_model_paths("onnx")
            jarvis_paths = [Path(path) for path in wake_paths if "hey_jarvis" in path]
            available = bool(jarvis_paths and jarvis_paths[0].is_file())
            checks.append(Check("Wake model hey_jarvis", available,
                                str(jarvis_paths[0]) if jarvis_paths else "não catalogado", required=False))
        except Exception as exc:
            checks.append(Check("Wake model hey_jarvis", False, str(exc), required=False))
    client = OllamaClient(settings.ai.endpoint, settings.ai.model, timeout=3.0)
    ok, detail = await client.health()
    checks.append(Check("Ollama", ok, detail, required=False))
    if settings.voice.piper_model:
        model = Path(settings.voice.piper_model)
        checks.append(Check("Modelo Piper", model.is_file(), str(model), required=False))
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico do J.A.R.V.I.S.")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    checks = asyncio.run(run_checks(args.config))
    print("\nJ.A.R.V.I.S. — diagnóstico\n")
    for check in checks:
        icon = "OK" if check.ok else ("ERRO" if check.required else "AVISO")
        print(f"[{icon:5}] {check.name:26} {check.detail}")
    required_failures = [check for check in checks if check.required and not check.ok]
    print("\nResultado:", "pronto" if not required_failures else f"{len(required_failures)} requisito(s) ausente(s)")
    return 1 if required_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
