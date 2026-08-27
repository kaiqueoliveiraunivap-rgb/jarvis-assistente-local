from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import asdict, dataclass

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


SW_HIDE = 0
SW_RESTORE = 9
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_SHOW = 5
WM_CLOSE = 0x0010


@dataclass(frozen=True, slots=True)
class WindowInfo:
    handle: int
    title: str
    left: int
    top: int
    width: int
    height: int


def _user32() -> ctypes.WinDLL:
    if not hasattr(ctypes, "windll"):
        raise RuntimeError("Controle de janelas está disponível somente no Windows")
    return ctypes.windll.user32


def list_visible_windows() -> list[WindowInfo]:
    user32 = _user32()
    windows: list[WindowInfo] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            title = buffer.value.strip()
            if title:
                windows.append(WindowInfo(int(hwnd), title, rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top))
        return True

    user32.EnumWindows(callback_type(callback), 0)
    return windows


def _find(title: str) -> WindowInfo | None:
    needle = title.casefold().strip()
    exact = [window for window in list_visible_windows() if window.title.casefold() == needle]
    if exact:
        return exact[0]
    return next((window for window in list_visible_windows() if needle in window.title.casefold()), None)


def _require_window(title: str) -> WindowInfo | ToolResult:
    window = _find(title)
    return window or ToolResult.fail(f"Não encontrei uma janela contendo “{title}”.", "WINDOW_NOT_FOUND")


@tool("list_windows", "Listar janelas visíveis", category="windows")
def list_windows() -> ToolResult:
    windows = [asdict(item) for item in list_visible_windows()]
    return ToolResult.ok(f"Encontrei {len(windows)} janelas visíveis.", windows)


def _show_window(title: str, command: int, verb: str) -> ToolResult:
    target = _require_window(title)
    if isinstance(target, ToolResult):
        return target
    _user32().ShowWindow(target.handle, command)
    return ToolResult.ok(f"Janela {verb}.", asdict(target))


@tool("minimize_app", "Minimizar uma janela de aplicativo", category="windows", risk=RiskLevel.LOW)
def minimize_app(name: str) -> ToolResult:
    return _show_window(name, SW_MINIMIZE, "minimizada")


@tool("maximize_app", "Maximizar uma janela de aplicativo", category="windows", risk=RiskLevel.LOW)
def maximize_app(name: str) -> ToolResult:
    return _show_window(name, SW_MAXIMIZE, "maximizada")


@tool("restore_app", "Restaurar uma janela de aplicativo", category="windows", risk=RiskLevel.LOW)
def restore_app(name: str) -> ToolResult:
    return _show_window(name, SW_RESTORE, "restaurada")


@tool("switch_window", "Alternar para uma janela", category="windows", risk=RiskLevel.LOW)
def switch_window(name: str) -> ToolResult:
    target = _require_window(name)
    if isinstance(target, ToolResult):
        return target
    user32 = _user32()
    user32.ShowWindow(target.handle, SW_RESTORE)
    if not user32.SetForegroundWindow(target.handle):
        return ToolResult.fail("O Windows bloqueou a troca de foco desta vez.", "FOCUS_DENIED")
    return ToolResult.ok(f"Voltando para {target.title}.", asdict(target))


@tool("move_window", "Mover uma janela", category="windows", risk=RiskLevel.LOW)
def move_window(title: str, x: int, y: int) -> ToolResult:
    target = _require_window(title)
    if isinstance(target, ToolResult):
        return target
    ok = _user32().MoveWindow(target.handle, int(x), int(y), target.width, target.height, True)
    return ToolResult.ok("Janela movida.") if ok else ToolResult.fail("Não consegui mover a janela.")


@tool("resize_window", "Redimensionar uma janela", category="windows", risk=RiskLevel.LOW)
def resize_window(title: str, width: int, height: int) -> ToolResult:
    if width < 200 or height < 120:
        return ToolResult.fail("O tamanho mínimo é 200 × 120 pixels.", "INVALID_SIZE")
    target = _require_window(title)
    if isinstance(target, ToolResult):
        return target
    ok = _user32().MoveWindow(target.handle, target.left, target.top, int(width), int(height), True)
    return ToolResult.ok("Janela redimensionada.") if ok else ToolResult.fail("Não consegui redimensionar a janela.")


def _work_area() -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    SPI_GETWORKAREA = 0x0030
    if not _user32().SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
        return (0, 0, _user32().GetSystemMetrics(0), _user32().GetSystemMetrics(1))
    return rect.left, rect.top, rect.right, rect.bottom


@tool("tile_window_left", "Posicionar uma janela à esquerda", category="windows", risk=RiskLevel.LOW)
def tile_window_left(title: str) -> ToolResult:
    return _tile(title, "left")


@tool("tile_window_right", "Posicionar uma janela à direita", category="windows", risk=RiskLevel.LOW)
def tile_window_right(title: str) -> ToolResult:
    return _tile(title, "right")


def _tile(title: str, side: str) -> ToolResult:
    target = _require_window(title)
    if isinstance(target, ToolResult):
        return target
    left, top, right, bottom = _work_area()
    half = (right - left) // 2
    x = left if side == "left" else left + half
    _user32().ShowWindow(target.handle, SW_RESTORE)
    ok = _user32().MoveWindow(target.handle, x, top, half, bottom - top, True)
    return ToolResult.ok(f"{target.title} à {'esquerda' if side == 'left' else 'direita'}.") if ok else ToolResult.fail("Não consegui posicionar a janela.")


@tool("organize_windows", "Organizar as duas janelas mais recentes lado a lado", category="windows", risk=RiskLevel.LOW)
def organize_windows() -> ToolResult:
    ignored = {"program manager", "windows input experience", "settings"}
    windows = [window for window in list_visible_windows() if window.title.casefold() not in ignored and window.width > 200]
    if len(windows) < 2:
        return ToolResult.fail("Preciso de ao menos duas janelas visíveis para organizar.", "NOT_ENOUGH_WINDOWS")
    left = _tile(windows[0].title, "left")
    right = _tile(windows[1].title, "right")
    if left.success and right.success:
        return ToolResult.ok("Janelas organizadas.", [windows[0].title, windows[1].title])
    return ToolResult.fail("Não consegui organizar todas as janelas.")

