from __future__ import annotations

from pathlib import Path

from jarvis.ai.provider import AIMessage, AIProvider
from jarvis.vision.image_utils import encode_image


class ScreenAnalyzer:
    def __init__(self, provider: AIProvider, vision_model: str | None) -> None:
        self.provider = provider
        self.vision_model = vision_model

    async def analyze(self, path: Path | str, question: str = "Descreva o que está na tela e destaque erros visíveis.") -> str:
        if not self.vision_model:
            raise RuntimeError("Configure ai.vision_model para analisar capturas de tela")
        encoded = encode_image(path)
        prompt = (
            "Analise esta captura de tela local. Não transcreva nem repita senhas, tokens, chaves ou dados bancários. "
            "Se houver dados sensíveis, diga apenas que há conteúdo sensível. Seja objetivo. " + question
        )
        response = await self.provider.chat([AIMessage("user", prompt, (encoded,))], model=self.vision_model)
        return response.content

