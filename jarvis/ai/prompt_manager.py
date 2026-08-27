from __future__ import annotations

import json
from typing import Any

from jarvis.core.config import AppSettings


class PromptManager:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def system_prompt(self, context: dict[str, Any] | None = None) -> str:
        p = self.settings.personality
        return (
            f"Você é {self.settings.assistant_name}, um assistente digital local para Windows. "
            "Responda em português do Brasil com calma, objetividade e elegância. "
            "Você não é consciente e não deve afirmar emoções reais. Seus estados são comportamentais. "
            "Nunca solicite senhas, tokens ou dados bancários. Nunca afirme ter executado uma ação sem resultado de tool. "
            f"Perfil: formalidade={p.formality}, sarcasmo={p.sarcasm}, humor={p.humor}, verbosidade={p.verbosity}. "
            f"Contexto disponível: {json.dumps(context or {}, ensure_ascii=False, default=str)}"
        )

    @staticmethod
    def planner_prompt(tools: list[dict[str, Any]], text: str, context: dict[str, Any]) -> str:
        return (
            "Classifique a solicitação. Responda SOMENTE JSON válido no formato "
            '{"kind":"chat","response":"..."} ou '
            '{"kind":"plan","summary":"...","steps":[{"tool":"nome","arguments":{}}]}. '
            "Use exclusivamente tools fornecidas, no máximo 8 passos. Não invente argumentos, não gere shell, código, CMD ou PowerShell. "
            "Se a solicitação for conversa, dúvida ou não puder ser cumprida pelas tools, use kind=chat. "
            f"Tools: {json.dumps(tools, ensure_ascii=False)}. Contexto: {json.dumps(context, ensure_ascii=False, default=str)}. "
            f"Solicitação: {text}"
        )

