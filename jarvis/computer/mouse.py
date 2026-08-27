from __future__ import annotations

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


def _automation():
    try:
        import pyautogui  # type: ignore
        pyautogui.FAILSAFE = True
        return pyautogui
    except ImportError as exc:
        raise RuntimeError("Instale pyautogui para usar teclado e mouse") from exc


@tool("move_mouse", "Mover o cursor", category="input", risk=RiskLevel.LOW)
def move_mouse(x: int, y: int, duration: float = 0.2) -> ToolResult:
    screen_width, screen_height = _automation().size()
    if not 0 <= x < screen_width or not 0 <= y < screen_height:
        return ToolResult.fail("As coordenadas estão fora da tela principal.", "OUT_OF_BOUNDS")
    _automation().moveTo(x, y, duration=max(0.0, min(duration, 2.0)))
    return ToolResult.ok("Cursor movido.")


@tool("click", "Clicar com o botão esquerdo", category="input", risk=RiskLevel.MEDIUM)
def click(x: int | None = None, y: int | None = None) -> ToolResult:
    _automation().click(x=x, y=y)
    return ToolResult.ok("Clique.")


@tool("double_click", "Clicar duas vezes", category="input", risk=RiskLevel.MEDIUM)
def double_click(x: int | None = None, y: int | None = None) -> ToolResult:
    _automation().doubleClick(x=x, y=y, interval=0.12)
    return ToolResult.ok("Clique duplo.")


@tool("right_click", "Clicar com o botão direito", category="input", risk=RiskLevel.MEDIUM)
def right_click(x: int | None = None, y: int | None = None) -> ToolResult:
    _automation().rightClick(x=x, y=y)
    return ToolResult.ok("Menu de contexto aberto.")


@tool("scroll", "Rolar a tela", category="input", risk=RiskLevel.LOW)
def scroll(amount: int) -> ToolResult:
    amount = max(-100, min(100, int(amount)))
    _automation().scroll(amount)
    return ToolResult.ok("Rolagem concluída.")


@tool("drag", "Arrastar o cursor", category="input", risk=RiskLevel.MEDIUM)
def drag(x: int, y: int, duration: float = 0.5) -> ToolResult:
    _automation().dragTo(x, y, duration=max(0.1, min(duration, 3.0)), button="left")
    return ToolResult.ok("Arraste concluído.")

