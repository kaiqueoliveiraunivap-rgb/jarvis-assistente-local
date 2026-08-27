from __future__ import annotations

import ipaddress
import urllib.parse
import webbrowser

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


def _safe_url(url: str) -> str:
    candidate = url.strip()
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Somente URLs HTTP ou HTTPS são permitidas")
    if parsed.username or parsed.password:
        raise ValueError("Credenciais não podem ser incluídas na URL")
    return candidate


@tool("open_url", "Abrir uma URL no navegador padrão", category="browser", risk=RiskLevel.LOW)
def open_url(url: str) -> ToolResult:
    try:
        target = _safe_url(url)
    except ValueError as exc:
        return ToolResult.fail(str(exc), "INVALID_URL")
    opened = webbrowser.open(target, new=2)
    return ToolResult.ok("Navegador aberto.", {"url": target}) if opened else ToolResult.fail("Não consegui abrir o navegador.")


@tool("google_search", "Pesquisar no Google", category="browser", risk=RiskLevel.LOW)
def google_search(query: str) -> ToolResult:
    cleaned = query.strip()
    if not cleaned:
        return ToolResult.fail("A pesquisa está vazia.", "EMPTY_QUERY")
    url = "https://www.google.com/search?" + urllib.parse.urlencode({"q": cleaned})
    opened = webbrowser.open(url, new=2)
    return ToolResult.ok(f"Pesquisando “{cleaned}”.", {"url": url}) if opened else ToolResult.fail("Não consegui abrir o navegador.")

