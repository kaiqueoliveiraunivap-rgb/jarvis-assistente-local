from __future__ import annotations

import re
from dataclasses import dataclass

from jarvis.database.models import MemoryKind


_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\b(senha|password|token|api key|chave de api|cvv|pin)\b"),
    re.compile(r"\b\d{13,19}\b"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._-]+"),
)


@dataclass(frozen=True, slots=True)
class MemoryEvaluation:
    should_store: bool
    kind: MemoryKind
    importance: int
    reason: str


class MemoryEvaluator:
    def evaluate(self, content: str, *, explicitly_requested: bool = False) -> MemoryEvaluation:
        cleaned = content.strip()
        if not cleaned:
            return MemoryEvaluation(False, MemoryKind.SHORT_TERM, 0, "Conteúdo vazio")
        if any(pattern.search(cleaned) for pattern in _SENSITIVE_PATTERNS):
            return MemoryEvaluation(False, MemoryKind.SHORT_TERM, 0, "Conteúdo possivelmente sensível")
        normalized = cleaned.casefold()
        preference = any(token in normalized for token in ("prefiro", "gosto de", "favorito", "principal", "quero dizer"))
        persistent = any(token in normalized for token in ("meu nome", "meu projeto", "trabalho com", "sempre", "normalmente"))
        if explicitly_requested:
            return MemoryEvaluation(True, MemoryKind.LONG_TERM if preference or persistent else MemoryKind.SEMANTIC, 80, "Pedido explícito")
        if preference:
            return MemoryEvaluation(True, MemoryKind.LONG_TERM, 70, "Preferência útil")
        if persistent:
            return MemoryEvaluation(True, MemoryKind.SEMANTIC, 60, "Informação persistente")
        return MemoryEvaluation(False, MemoryKind.SHORT_TERM, 20, "Sem valor persistente claro")

