from __future__ import annotations

from jarvis.browser.web_actions import _safe_url
from jarvis.tools.tool import ToolResult


class PlaywrightController:
    """Sessão opcional isolada; não reutiliza credenciais do navegador pessoal."""

    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._page = None

    async def start(self) -> None:
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Instale requirements-browser.txt e execute playwright install chromium") from exc
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._page = await self._browser.new_page()

    async def navigate(self, url: str) -> ToolResult:
        if self._page is None:
            await self.start()
        target = _safe_url(url)
        await self._page.goto(target, wait_until="domcontentloaded")
        return ToolResult.ok("Página carregada.", {"url": self._page.url, "title": await self._page.title()})

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._playwright = self._browser = self._page = None

