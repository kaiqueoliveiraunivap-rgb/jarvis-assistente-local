from __future__ import annotations

import re

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


_ALLOWED_KEYS = {
    "ctrl", "alt", "shift", "win", "enter", "esc", "escape", "tab", "space",
    "backspace", "delete", "home", "end", "pageup", "pagedown", "up", "down",
    "left", "right", "insert", "capslock", "f1", "f2", "f3", "f4", "f5", "f6",
    "f7", "f8", "f9", "f10", "f11", "f12",
} | set("abcdefghijklmnopqrstuvwxyz0123456789")


def _automation():
    try:
        import pyautogui  # type: ignore
        pyautogui.FAILSAFE = True
        return pyautogui
    except ImportError as exc:
        raise RuntimeError("Instale pyautogui para usar teclado e mouse") from exc


def _valid_key(key: str) -> str:
    normalized = key.casefold().strip()
    aliases = {"controle": "ctrl", "control": "ctrl", "windows": "win", "espaco": "space", "escape": "esc"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in _ALLOWED_KEYS:
        raise ValueError(f"Tecla não permitida: {key}")
    return normalized


@tool("type_text", "Digitar texto na janela ativa", category="input", risk=RiskLevel.MEDIUM)
def type_text(text: str, interval: float = 0.02) -> ToolResult:
    if len(text) > 10_000:
        return ToolResult.fail("O texto é grande demais para digitação automática.", "TEXT_TOO_LONG")
    _automation().write(text, interval=max(0.0, min(float(interval), 1.0)))
    return ToolResult.ok("Texto digitado.", {"characters": len(text)})


@tool("press_key", "Pressionar uma tecla", category="input", risk=RiskLevel.LOW)
def press_key(key: str) -> ToolResult:
    normalized = _valid_key(key)
    _automation().press(normalized)
    return ToolResult.ok(f"Tecla {normalized} pressionada.")


@tool("hotkey", "Pressionar uma combinação de teclas", category="input", risk=RiskLevel.MEDIUM)
def hotkey(keys: list[str]) -> ToolResult:
    if not 2 <= len(keys) <= 4:
        return ToolResult.fail("Uma combinação deve conter de duas a quatro teclas.", "INVALID_HOTKEY")
    normalized = [_valid_key(key) for key in keys]
    # Bloqueia sequências reservadas ou destrutivas.
    joined = "+".join(normalized)
    if joined in {"win+r", "ctrl+alt+delete", "alt+f4"}:
        return ToolResult.fail("Essa combinação está bloqueada pela política de entrada.", "HOTKEY_BLOCKED")
    _automation().hotkey(*normalized)
    return ToolResult.ok(f"{joined}.")

