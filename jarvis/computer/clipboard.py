from __future__ import annotations

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


def _with_tk(action):
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        try:
            return action(root)
        finally:
            root.destroy()
    except Exception as exc:
        raise RuntimeError(f"Não foi possível acessar a área de transferência: {exc}") from exc


@tool("read_clipboard", "Ler texto da área de transferência", category="clipboard", risk=RiskLevel.SAFE)
def read_clipboard() -> ToolResult:
    try:
        text = _with_tk(lambda root: root.clipboard_get())
    except RuntimeError as exc:
        return ToolResult.fail(str(exc), "CLIPBOARD_UNAVAILABLE")
    if len(text) > 5_000:
        return ToolResult.ok("O conteúdo é longo; exibindo somente o início.", {"text": text[:5_000], "truncated": True})
    return ToolResult.ok(text or "A área de transferência está vazia.", {"text": text})


@tool("write_clipboard", "Escrever texto na área de transferência", category="clipboard", risk=RiskLevel.LOW)
def write_clipboard(text: str) -> ToolResult:
    if len(text) > 1_000_000:
        return ToolResult.fail("Conteúdo grande demais para a área de transferência.", "CONTENT_TOO_LARGE")

    def write(root):
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()

    _with_tk(write)
    return ToolResult.ok("Copiado.", {"characters": len(text)})


@tool("clear_clipboard", "Limpar a área de transferência", category="clipboard", risk=RiskLevel.MEDIUM)
def clear_clipboard() -> ToolResult:
    _with_tk(lambda root: (root.clipboard_clear(), root.update()))
    return ToolResult.ok("Área de transferência limpa.")

