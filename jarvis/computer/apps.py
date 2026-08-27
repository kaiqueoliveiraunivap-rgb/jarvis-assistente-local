from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


_ALIASES: dict[str, str] = {}
_PROTECTED = {
    "csrss.exe", "wininit.exe", "winlogon.exe", "lsass.exe", "services.exe",
    "smss.exe", "system", "registry", "dwm.exe", "explorer.exe",
}


def configure_app_aliases(aliases: dict[str, str]) -> None:
    global _ALIASES
    _ALIASES = {key.casefold(): value for key, value in aliases.items()}


def _resolve(name: str) -> str:
    requested = name.strip().casefold()
    candidate = _ALIASES.get(requested, name.strip())
    expanded = os.path.expandvars(candidate)
    path = Path(expanded)
    if path.exists():
        return str(path.resolve())
    located = shutil.which(expanded)
    if located:
        return located
    executable_name = Path(expanded).name
    registry_path = _registry_app_path(executable_name)
    if registry_path:
        return registry_path
    known_name = "code.exe" if executable_name.casefold() in {"code.cmd", "code.bat"} else executable_name
    known = _well_known_app(known_name)
    if known:
        return str(known)
    protocol_fallbacks = {"spotify.exe": "spotify:"}
    return protocol_fallbacks.get(executable_name.casefold(), expanded)


def _registry_app_path(executable_name: str) -> str | None:
    try:
        import winreg
    except ImportError:
        return None
    subkey = rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{executable_name}"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for access in (winreg.KEY_READ, winreg.KEY_READ | getattr(winreg, "KEY_WOW64_32KEY", 0)):
            try:
                with winreg.OpenKey(hive, subkey, 0, access) as key:
                    value = str(winreg.QueryValue(key, None)).strip('"')
                    if Path(value).is_file():
                        return value
            except OSError:
                continue
    return None


def _well_known_app(executable_name: str) -> Path | None:
    local = Path(os.getenv("LOCALAPPDATA", ""))
    roaming = Path(os.getenv("APPDATA", ""))
    program_files = Path(os.getenv("ProgramFiles", "C:\\Program Files"))
    program_files_x86 = Path(os.getenv("ProgramFiles(x86)", "C:\\Program Files (x86)"))
    candidates: dict[str, list[Path]] = {
        "chrome.exe": [program_files / "Google/Chrome/Application/chrome.exe", program_files_x86 / "Google/Chrome/Application/chrome.exe"],
        "spotify.exe": [roaming / "Spotify/Spotify.exe", local / "Microsoft/WindowsApps/Spotify.exe"],
        "code.exe": [local / "Programs/Microsoft VS Code/Code.exe", program_files / "Microsoft VS Code/Code.exe"],
        "opera.exe": [local / "Programs/Opera/opera.exe", program_files / "Opera/opera.exe"],
    }
    if executable_name.casefold() == "discord.exe":
        candidates["discord.exe"] = sorted(local.glob("Discord/app-*/Discord.exe"), reverse=True)
    for path in candidates.get(executable_name.casefold(), []):
        try:
            if path.is_file():
                return path
        except OSError:
            # Alguns aliases em WindowsApps são visíveis, mas bloqueiam stat().
            continue
    return None


def _process_name(value: str) -> str:
    candidate = Path(_ALIASES.get(value.casefold(), value)).name.casefold()
    if candidate.endswith((".cmd", ".bat")):
        candidate = candidate.rsplit(".", 1)[0] + ".exe"
    if "." not in candidate:
        candidate += ".exe"
    return candidate


@tool("open_app", "Abrir um aplicativo instalado", category="apps", risk=RiskLevel.LOW)
def open_app(name: str) -> ToolResult:
    executable = _resolve(name)
    try:
        target = Path(executable)
        protocol = executable.endswith(":") and "\\" not in executable and "/" not in executable
        if target.exists() or target.suffix.casefold() in {".cmd", ".bat"} or protocol:
            os.startfile(executable)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(
                [executable],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        return ToolResult.ok(f"{name} aberto.", {"executable": executable})
    except (OSError, ValueError) as exc:
        return ToolResult.fail(
            f"Não encontrei “{name}”. Configure o caminho do aplicativo nas preferências. ({exc})",
            "APP_NOT_FOUND",
        )


@tool("close_app", "Fechar um aplicativo", category="apps", risk=RiskLevel.MEDIUM)
def close_app(name: str) -> ToolResult:
    expected = _process_name(name)
    if expected in _PROTECTED:
        return ToolResult.fail("Esse processo é protegido e não pode ser encerrado.", "PROTECTED_PROCESS")
    try:
        import psutil  # type: ignore
    except ImportError:
        return ToolResult.fail("Instale psutil para fechar aplicativos com segurança.", "DEPENDENCY_MISSING")
    matches = [process for process in psutil.process_iter(["name"]) if (process.info["name"] or "").casefold() == expected]
    if not matches:
        return ToolResult.ok(f"{name} já está fechado.")
    terminated = 0
    for process in matches:
        try:
            process.terminate()
            terminated += 1
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    if not terminated:
        return ToolResult.fail(f"Não consegui fechar {name} sem elevar permissões.", "ACCESS_DENIED")
    return ToolResult.ok(f"{name} fechado.", {"processes": terminated})


@tool("is_app_running", "Verificar se um aplicativo está em execução", category="apps")
def is_app_running(name: str) -> ToolResult:
    expected = _process_name(name)
    try:
        import psutil  # type: ignore
        running = any((process.info["name"] or "").casefold() == expected for process in psutil.process_iter(["name"]))
    except ImportError:
        output = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {expected}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, check=False, encoding="utf-8", errors="replace",
        ).stdout
        running = expected in output.casefold()
    return ToolResult.ok(f"{name} {'está aberto' if running else 'não está aberto'}.", {"running": running})


@tool("find_app", "Localizar o executável de um aplicativo", category="apps")
def find_app(name: str) -> ToolResult:
    resolved = _resolve(name)
    protocol = resolved.endswith(":") and "\\" not in resolved and "/" not in resolved
    exists = Path(resolved).exists() or shutil.which(resolved) is not None
    message = "Aplicativo localizado." if exists else "Aplicativo disponível por protocolo; a instalação será verificada ao abrir." if protocol else "Aplicativo não localizado."
    return ToolResult.ok(message, {"path": resolved, "exists": exists, "protocol": protocol})
