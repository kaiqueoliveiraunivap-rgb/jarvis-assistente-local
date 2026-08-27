from __future__ import annotations

from jarvis.core.intent_router import normalize_text


class BargeInDetector:
    INTERRUPTIONS = {"jarvis", "pare", "parar", "cancelar", "cancele", "espera", "espere"}

    def should_interrupt(self, transcript: str) -> bool:
        normalized = normalize_text(transcript)
        return normalized in self.INTERRUPTIONS or any(normalized.startswith(word + " ") for word in self.INTERRUPTIONS)

