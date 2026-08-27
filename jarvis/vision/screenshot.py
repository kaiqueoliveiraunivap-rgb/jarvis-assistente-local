from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jarvis.core.paths import screenshot_directory
from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


_OUTPUT_DIRECTORY = screenshot_directory()
_ENABLED = True


def configure_screenshots(enabled: bool, output_directory: Path | str | None = None) -> None:
    global _ENABLED, _OUTPUT_DIRECTORY
    _ENABLED = enabled
    if output_directory:
        _OUTPUT_DIRECTORY = Path(output_directory)


@tool("take_screenshot", "Capturar a tela sob solicitação", category="vision", risk=RiskLevel.MEDIUM)
def take_screenshot(output_path: str | None = None) -> ToolResult:
    if not _ENABLED:
        return ToolResult.fail("A análise de tela está desativada nas configurações de privacidade.", "SCREEN_DISABLED")
    try:
        from PIL import ImageGrab  # type: ignore
    except ImportError:
        return ToolResult.fail("Instale Pillow para capturar a tela.", "DEPENDENCY_MISSING")
    if output_path:
        target = Path(output_path).expanduser().resolve()
    else:
        _OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        target = _OUTPUT_DIRECTORY / f"screen_{datetime.now():%Y%m%d_%H%M%S}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    image = ImageGrab.grab(all_screens=True)
    image.save(target, format="PNG")
    return ToolResult.ok("Captura de tela concluída.", {"path": str(target), "width": image.width, "height": image.height})
