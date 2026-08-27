from __future__ import annotations

import ctypes

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


def _media_key(key: int, presses: int = 1) -> None:
    user32 = ctypes.windll.user32
    for _ in range(max(1, presses)):
        user32.keybd_event(key, 0, 0, 0)
        user32.keybd_event(key, 0, KEYEVENTF_KEYUP, 0)


def _endpoint():
    try:
        from pycaw.pycaw import AudioUtilities  # type: ignore
        device = AudioUtilities.GetSpeakers()
        endpoint = getattr(device, "EndpointVolume", None)
        if endpoint is not None:
            return endpoint
        # Compatibilidade com versões anteriores do pycaw.
        from ctypes import POINTER, cast
        from comtypes import CLSCTX_ALL  # type: ignore
        from pycaw.pycaw import IAudioEndpointVolume  # type: ignore
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception as exc:
        raise RuntimeError("Instale pycaw e comtypes para controle exato de áudio") from exc


@tool("set_volume", "Definir o volume principal", category="audio", risk=RiskLevel.LOW)
def set_volume(level: int) -> ToolResult:
    if not 0 <= int(level) <= 100:
        return ToolResult.fail("O volume precisa estar entre 0 e 100%.", "INVALID_LEVEL")
    endpoint = _endpoint()
    endpoint.SetMasterVolumeLevelScalar(int(level) / 100.0, None)
    if level > 0 and endpoint.GetMute():
        endpoint.SetMute(0, None)
    return ToolResult.ok(f"{int(level)}%.", {"level": int(level)})


@tool("get_volume", "Obter o volume principal", category="audio")
def get_volume() -> ToolResult:
    endpoint = _endpoint()
    level = round(float(endpoint.GetMasterVolumeLevelScalar()) * 100)
    muted = bool(endpoint.GetMute())
    return ToolResult.ok(f"Volume em {level}%{' e mudo' if muted else ''}.", {"level": level, "muted": muted})


@tool("volume_up", "Aumentar o volume", category="audio", risk=RiskLevel.LOW)
def volume_up(steps: int = 2) -> ToolResult:
    _media_key(VK_VOLUME_UP, max(1, min(int(steps), 20)))
    return ToolResult.ok("Volume aumentado.")


@tool("volume_down", "Diminuir o volume", category="audio", risk=RiskLevel.LOW)
def volume_down(steps: int = 2) -> ToolResult:
    _media_key(VK_VOLUME_DOWN, max(1, min(int(steps), 20)))
    return ToolResult.ok("Volume reduzido.")


@tool("mute", "Silenciar o áudio", category="audio", risk=RiskLevel.LOW)
def mute() -> ToolResult:
    endpoint = _endpoint()
    endpoint.SetMute(1, None)
    return ToolResult.ok("Mudo.")


@tool("unmute", "Restaurar o áudio", category="audio", risk=RiskLevel.LOW)
def unmute() -> ToolResult:
    endpoint = _endpoint()
    endpoint.SetMute(0, None)
    return ToolResult.ok("Áudio restaurado.")


@tool("play_pause_media", "Pausar ou continuar a mídia", category="media", risk=RiskLevel.LOW)
def play_pause_media() -> ToolResult:
    _media_key(VK_MEDIA_PLAY_PAUSE)
    return ToolResult.ok("Mídia alternada.")


@tool("next_media", "Avançar para a próxima faixa", category="media", risk=RiskLevel.LOW)
def next_media() -> ToolResult:
    _media_key(VK_MEDIA_NEXT_TRACK)
    return ToolResult.ok("Próxima.")


@tool("previous_media", "Voltar para a faixa anterior", category="media", risk=RiskLevel.LOW)
def previous_media() -> ToolResult:
    _media_key(VK_MEDIA_PREV_TRACK)
    return ToolResult.ok("Faixa anterior.")
