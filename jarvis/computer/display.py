from __future__ import annotations

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


@tool("set_brightness", "Definir o brilho da tela", category="display", risk=RiskLevel.LOW)
def set_brightness(level: int, display: int | None = None) -> ToolResult:
    if not 0 <= int(level) <= 100:
        return ToolResult.fail("O brilho precisa estar entre 0 e 100%.", "INVALID_LEVEL")
    try:
        import screen_brightness_control as sbc  # type: ignore
        sbc.set_brightness(int(level), display=display)
        return ToolResult.ok(f"Brilho em {int(level)}%.", {"level": int(level)})
    except ImportError:
        return ToolResult.fail("Instale screen-brightness-control para ajustar o brilho.", "DEPENDENCY_MISSING")
    except Exception as exc:
        return ToolResult.fail(f"O monitor não aceitou o ajuste de brilho: {exc}", "DISPLAY_UNAVAILABLE")


@tool("get_brightness", "Obter o brilho da tela", category="display")
def get_brightness() -> ToolResult:
    try:
        import screen_brightness_control as sbc  # type: ignore
        levels = [int(value) for value in sbc.get_brightness()]
        return ToolResult.ok(f"Brilho em {levels[0]}%.", {"levels": levels})
    except ImportError:
        return ToolResult.fail("Instale screen-brightness-control para consultar o brilho.", "DEPENDENCY_MISSING")
    except Exception as exc:
        return ToolResult.fail(f"Brilho indisponível: {exc}", "DISPLAY_UNAVAILABLE")

