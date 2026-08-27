from __future__ import annotations

import hashlib

from jarvis.core.config import PersonalitySettings
from jarvis.personality.mood_engine import Mood, MoodEngine


class PersonalityEngine:
    def __init__(self, settings: PersonalitySettings) -> None:
        self.settings = settings
        self.mood = MoodEngine()

    def acknowledgement(self, action: str, seed: str = "") -> str:
        options = {
            "open": ("Abrindo.", "Claro.", "A caminho.", "De volta ao trabalho."),
            "done": ("Pronto.", "Feito.", "Tudo certo.", "Resolvido."),
            "listen": ("Estou ouvindo.", "Sim?", "Pode falar.", "À disposição."),
            "cancel": ("Cancelado.", "Tudo bem, parei.", "Interrompido."),
        }.get(action, ("Certo.",))
        digest = hashlib.sha256((action + seed).encode("utf-8")).digest()[0]
        return options[digest % len(options)]

    def greeting(self, period: str) -> str:
        prefix = {"manhã": "Bom dia", "tarde": "Boa tarde", "noite": "Boa noite", "madrugada": "Boa madrugada"}.get(period, "Olá")
        return f"{prefix}. J.A.R.V.I.S. online."

