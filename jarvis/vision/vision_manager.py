from __future__ import annotations

from pathlib import Path

from jarvis.core.config import ScreenAwareness
from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.vision.screen_analyzer import ScreenAnalyzer
from jarvis.vision.screenshot import take_screenshot


class VisionManager:
    def __init__(self, mode: ScreenAwareness, analyzer: ScreenAnalyzer, event_bus: EventBus) -> None:
        self.mode = mode
        self.analyzer = analyzer
        self.event_bus = event_bus

    async def inspect_screen(self, question: str = "") -> tuple[str, Path | None]:
        if self.mode is ScreenAwareness.OFF:
            return "A análise de tela está desativada nas configurações de privacidade.", None
        await self.event_bus.publish(Event(EventType.SCREEN_ANALYSIS_STARTED, {"indicator": True}, 20))
        capture = take_screenshot()
        if not capture.success:
            await self.event_bus.publish(Event(EventType.SCREEN_ANALYSIS_FINISHED, {"success": False}, 20))
            return capture.message, None
        path = Path(capture.data["path"])
        try:
            analysis = await self.analyzer.analyze(path, question or "O que está aparecendo na tela?")
            return analysis, path
        except Exception as exc:
            return f"Capturei a tela, mas não consegui analisá-la: {exc}", path
        finally:
            await self.event_bus.publish(Event(EventType.SCREEN_ANALYSIS_FINISHED, {"success": True, "path": str(path)}, 20))

