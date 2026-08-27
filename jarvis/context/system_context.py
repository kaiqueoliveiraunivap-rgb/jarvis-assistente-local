from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import asdict
from typing import Any

from jarvis.computer.hardware import snapshot


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def idle_seconds() -> float:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    elapsed_ms = (ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF
    return elapsed_ms / 1000.0


def active_window() -> dict[str, Any]:
    user32 = ctypes.windll.user32
    handle = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(handle)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(handle, buffer, length + 1)
    return {"handle": int(handle), "title": buffer.value}


def system_snapshot() -> dict[str, Any]:
    try:
        hardware = asdict(snapshot())
    except Exception as exc:
        hardware = {"error": str(exc)}
    try:
        window = active_window()
        idle = idle_seconds()
    except Exception as exc:
        window, idle = {"error": str(exc)}, None
    return {"hardware": hardware, "active_window": window, "idle_seconds": idle}

