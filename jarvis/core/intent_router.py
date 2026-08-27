from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class IntentType(StrEnum):
    WAKE = "WAKE"
    CANCEL = "CANCEL"
    CONFIRM = "CONFIRM"
    DENY = "DENY"
    OPEN_APP = "OPEN_APP"
    CLOSE_APP = "CLOSE_APP"
    MINIMIZE_APP = "MINIMIZE_APP"
    MAXIMIZE_APP = "MAXIMIZE_APP"
    RESTORE_APP = "RESTORE_APP"
    SWITCH_WINDOW = "SWITCH_WINDOW"
    MOVE_WINDOW = "MOVE_WINDOW"
    RESIZE_WINDOW = "RESIZE_WINDOW"
    TILE_WINDOW = "TILE_WINDOW"
    ORGANIZE_WINDOWS = "ORGANIZE_WINDOWS"
    SET_VOLUME = "SET_VOLUME"
    VOLUME_UP = "VOLUME_UP"
    VOLUME_DOWN = "VOLUME_DOWN"
    MUTE = "MUTE"
    UNMUTE = "UNMUTE"
    SET_BRIGHTNESS = "SET_BRIGHTNESS"
    TYPE_TEXT = "TYPE_TEXT"
    PRESS_KEY = "PRESS_KEY"
    HOTKEY = "HOTKEY"
    MOVE_MOUSE = "MOVE_MOUSE"
    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    SCROLL = "SCROLL"
    READ_CLIPBOARD = "READ_CLIPBOARD"
    WRITE_CLIPBOARD = "WRITE_CLIPBOARD"
    OPEN_URL = "OPEN_URL"
    WEB_SEARCH = "WEB_SEARCH"
    SCREENSHOT = "SCREENSHOT"
    ANALYZE_SCREEN = "ANALYZE_SCREEN"
    CPU_USAGE = "CPU_USAGE"
    RAM_USAGE = "RAM_USAGE"
    DISK_USAGE = "DISK_USAGE"
    BATTERY = "BATTERY"
    LIST_PROCESSES = "LIST_PROCESSES"
    SEARCH_FILE = "SEARCH_FILE"
    OPEN_FILE = "OPEN_FILE"
    OPEN_FOLDER = "OPEN_FOLDER"
    CREATE_FOLDER = "CREATE_FOLDER"
    COPY_FILE = "COPY_FILE"
    MOVE_FILE = "MOVE_FILE"
    RENAME_FILE = "RENAME_FILE"
    PLAY_PAUSE = "PLAY_PAUSE"
    NEXT_MEDIA = "NEXT_MEDIA"
    PREVIOUS_MEDIA = "PREVIOUS_MEDIA"
    LOCK_PC = "LOCK_PC"
    SLEEP_PC = "SLEEP_PC"
    SHUTDOWN_PC = "SHUTDOWN_PC"
    RESTART_PC = "RESTART_PC"
    SET_MODE = "SET_MODE"
    RUN_MACRO = "RUN_MACRO"
    SET_ALIAS = "SET_ALIAS"
    ADD_MACRO_TRIGGER = "ADD_MACRO_TRIGGER"
    REMEMBER = "REMEMBER"
    RECALL = "RECALL"
    SYSTEM_STATUS = "SYSTEM_STATUS"
    CONVERSATION = "CONVERSATION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Intent:
    type: IntentType
    arguments: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_text: str = ""
    normalized_text: str = ""
    requires_ai: bool = False
    addressed: bool = False


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents).strip(" .,!?:;")


class IntentRouter:
    """Roteador determinístico para comandos comuns em português."""

    def __init__(self, wake_word: str = "jarvis") -> None:
        self.wake_word = normalize_text(wake_word)

    def route(self, text: str) -> Intent:
        raw = text.strip()
        original_raw = raw
        normalized = normalize_text(raw)
        addressed = False
        wake = re.match(rf"^(?:ei\s+)?{re.escape(self.wake_word)}\b[\s,.:;-]*(.*)$", normalized)
        if wake:
            addressed = True
            normalized = wake.group(1).strip()
            if not normalized:
                return self._intent(IntentType.WAKE, original_raw, normalized, addressed=addressed)
            raw_wake = re.match(
                rf"^(?:ei\s+)?{re.escape(self.wake_word)}\b[\s,.:;-]*(.*)$",
                raw,
                re.IGNORECASE,
            )
            if raw_wake:
                raw = raw_wake.group(1).strip()

        if normalized in {"pare", "parar", "cancele", "cancelar", "cancela", "cancela isso", "espera"}:
            return self._intent(IntentType.CANCEL, raw, normalized, addressed=addressed)
        if normalized in {"sim", "confirmo", "pode", "pode fazer", "isso", "correto"}:
            return self._intent(IntentType.CONFIRM, raw, normalized, addressed=addressed)
        if normalized in {"nao", "negativo", "nao faca", "deixa", "deixa pra la"}:
            return self._intent(IntentType.DENY, raw, normalized, addressed=addressed)

        match = re.search(r"(?:coloque |defina |ajuste )?(?:o )?volume(?: em| para)?\s*(\d{1,3})(?:\s*%)?$", normalized)
        if match:
            return self._intent(IntentType.SET_VOLUME, raw, normalized, {"level": min(100, int(match.group(1)))}, addressed)
        if re.search(r"\b(desmute|desmutar|tire (?:do )?mudo)\b", normalized):
            return self._intent(IntentType.UNMUTE, raw, normalized, addressed=addressed)
        if re.search(r"\b(mute|mutar|mudo|silencie o (?:audio|som))\b", normalized):
            return self._intent(IntentType.MUTE, raw, normalized, addressed=addressed)
        if re.search(r"\b(aumente|suba) (?:o )?(?:volume|som)\b", normalized):
            return self._intent(IntentType.VOLUME_UP, raw, normalized, addressed=addressed)
        if re.search(r"\b(diminua|abaixe) (?:o )?(?:volume|som)\b", normalized):
            return self._intent(IntentType.VOLUME_DOWN, raw, normalized, addressed=addressed)
        match = re.search(r"(?:brilho)(?: em| para)?\s*(\d{1,3})(?:\s*%)?", normalized)
        if match:
            return self._intent(IntentType.SET_BRIGHTNESS, raw, normalized, {"level": min(100, int(match.group(1)))}, addressed)

        if re.search(r"\b(proxima (?:musica|faixa)|proxima)$", normalized):
            return self._intent(IntentType.NEXT_MEDIA, raw, normalized, addressed=addressed)
        if re.search(r"\b(musica anterior|faixa anterior|volta a musica|anterior)$", normalized):
            return self._intent(IntentType.PREVIOUS_MEDIA, raw, normalized, addressed=addressed)
        if re.search(r"\b(pause|pausar|continue a musica|play|reproduza)\b", normalized):
            return self._intent(IntentType.PLAY_PAUSE, raw, normalized, addressed=addressed)

        if re.search(r"\b(tire|faca|capture) (?:uma )?(?:screenshot|captura de tela)\b", normalized):
            return self._intent(IntentType.SCREENSHOT, raw, normalized, addressed=addressed)
        if re.search(r"\b(olha|olhe|analise|veja|o que (?:esta|tem))\b.*\b(tela|erro|isso|aparecendo)\b", normalized):
            return self._intent(IntentType.ANALYZE_SCREEN, raw, normalized, addressed=addressed)

        if re.search(r"\b(?:quanto|uso|consumo).*\bcpu\b|\bcpu.*(?:usando|uso)\b", normalized):
            return self._intent(IntentType.CPU_USAGE, raw, normalized, addressed=addressed)
        if re.search(r"\b(?:quanto|uso|consumo).*\b(?:ram|memoria)\b|\b(?:ram|memoria).*(?:usando|uso)\b", normalized):
            return self._intent(IntentType.RAM_USAGE, raw, normalized, addressed=addressed)
        if re.search(r"\b(?:quanto|uso|espaco).*\bdisco\b|\bdisco.*(?:usando|livre)\b", normalized):
            return self._intent(IntentType.DISK_USAGE, raw, normalized, addressed=addressed)
        if "bateria" in normalized:
            return self._intent(IntentType.BATTERY, raw, normalized, addressed=addressed)
        if re.search(r"\b(programas|processos).*(?:mais memoria|consumindo|usando)\b", normalized):
            return self._intent(IntentType.LIST_PROCESSES, raw, normalized, {"sort_by": "memory", "limit": 10}, addressed)
        if normalized in {"status", "status do sistema", "como esta o computador"}:
            return self._intent(IntentType.SYSTEM_STATUS, raw, normalized, addressed=addressed)

        if re.search(r"\b(bloqueie|bloquear|trave) (?:o )?(?:pc|computador|windows)\b", normalized):
            return self._intent(IntentType.LOCK_PC, raw, normalized, addressed=addressed)
        if re.search(r"\b(suspenda|suspender|coloque para dormir) (?:o )?(?:pc|computador)?\b", normalized):
            return self._intent(IntentType.SLEEP_PC, raw, normalized, addressed=addressed)
        if re.search(r"\b(desligue|desligar) (?:o )?(?:pc|computador|windows)\b", normalized):
            return self._intent(IntentType.SHUTDOWN_PC, raw, normalized, addressed=addressed)
        if re.search(r"\b(reinicie|reiniciar) (?:o )?(?:pc|computador|windows)\b", normalized):
            return self._intent(IntentType.RESTART_PC, raw, normalized, addressed=addressed)

        match = re.match(r"(?:pesquise|procure|busque)(?: por)?\s+(.+?)\s+(?:no google|na web|na internet)$", normalized)
        if match:
            return self._intent(IntentType.WEB_SEARCH, raw, normalized, {"query": match.group(1)}, addressed)
        match = re.match(r"(?:pesquise|procure|busque)(?: no google)?\s+(.+)$", normalized)
        if match and not any(word in normalized for word in ("arquivo", "pasta", "projeto")):
            return self._intent(IntentType.WEB_SEARCH, raw, normalized, {"query": match.group(1)}, addressed)
        match = re.match(r"(?:abra|abre|abrir|acesse|va para)\s+(https?://\S+|[\w.-]+\.(?:com|com\.br|org|net)(?:/\S*)?)$", normalized)
        if match:
            return self._intent(IntentType.OPEN_URL, raw, normalized, {"url": match.group(1)}, addressed)
        if re.search(r"\b(?:abra|abre|abrir|acesse) (?:o )?youtube\b", normalized):
            return self._intent(IntentType.OPEN_URL, raw, normalized, {"url": "https://www.youtube.com"}, addressed)

        match = re.match(r"(?:encontre|procure|busque|pesquise)(?: o arquivo| a pasta| meu projeto| o projeto)?\s+(.+)$", normalized)
        if match:
            return self._intent(IntentType.SEARCH_FILE, raw, normalized, {"query": match.group(1)}, addressed)
        match = re.match(r"(?:abra|abrir)\s+(?:a pasta\s+)?(downloads|documentos|imagens|desktop|area de trabalho)$", normalized)
        if match:
            return self._intent(IntentType.OPEN_FOLDER, raw, normalized, {"path": match.group(1)}, addressed)
        match = re.match(r"(?:abra|abrir)\s+(?:o arquivo\s+)(.+)$", normalized)
        if match:
            return self._intent(IntentType.OPEN_FILE, raw, normalized, {"path": match.group(1)}, addressed)
        match = re.match(r"(?:crie|criar)\s+(?:uma )?pasta(?: chamada)?\s+(.+)$", normalized)
        if match:
            return self._intent(IntentType.CREATE_FOLDER, raw, normalized, {"path": match.group(1)}, addressed)

        match = re.match(r"(?:escreva|digite)\s+(.+)$", raw, re.IGNORECASE)
        if match:
            return self._intent(IntentType.TYPE_TEXT, raw, normalized, {"text": match.group(1)}, addressed)
        match = re.match(r"(?:pressione|aperte)\s+(.+)$", normalized)
        if match:
            keys = self._parse_keys(match.group(1))
            kind = IntentType.HOTKEY if len(keys) > 1 else IntentType.PRESS_KEY
            args = {"keys": keys} if len(keys) > 1 else {"key": keys[0]}
            return self._intent(kind, raw, normalized, args, addressed)
        if re.fullmatch(r"(?:ctrl|alt|shift|win)(?:\s*\+?\s*[a-z0-9]+)+", normalized):
            return self._intent(IntentType.HOTKEY, raw, normalized, {"keys": self._parse_keys(normalized)}, addressed)

        if re.search(r"\bclique duas vezes\b", normalized):
            return self._intent(IntentType.DOUBLE_CLICK, raw, normalized, addressed=addressed)
        if re.search(r"\bclique (?:com o botao direito|direito)\b", normalized):
            return self._intent(IntentType.RIGHT_CLICK, raw, normalized, addressed=addressed)
        if re.search(r"\bclique\b", normalized):
            return self._intent(IntentType.CLICK, raw, normalized, addressed=addressed)
        match = re.search(r"\brole(?: a tela)? para (cima|baixo)(?:\s+(\d+))?", normalized)
        if match:
            amount = int(match.group(2) or 5) * (1 if match.group(1) == "cima" else -1)
            return self._intent(IntentType.SCROLL, raw, normalized, {"amount": amount}, addressed)
        if re.search(r"\bo que (?:eu )?copiei|leia (?:a )?area de transferencia\b", normalized):
            return self._intent(IntentType.READ_CLIPBOARD, raw, normalized, addressed=addressed)
        match = re.match(r"(?:copie para a area de transferencia|coloque no clipboard)\s+(.+)$", raw, re.IGNORECASE)
        if match:
            return self._intent(IntentType.WRITE_CLIPBOARD, raw, normalized, {"text": match.group(1)}, addressed)

        if re.search(r"\borganize (?:as|minhas|essas)?\s*janelas\b", normalized):
            return self._intent(IntentType.ORGANIZE_WINDOWS, raw, normalized, addressed=addressed)
        match = re.match(r"(?:mova|mover) (?:a janela )?(.+?) para (\d+)[, ]+(\d+)$", normalized)
        if match:
            if match.group(1) == "mouse":
                return self._intent(IntentType.MOVE_MOUSE, raw, normalized,
                                    {"x": int(match.group(2)), "y": int(match.group(3))}, addressed)
            return self._intent(IntentType.MOVE_WINDOW, raw, normalized,
                                {"title": match.group(1), "x": int(match.group(2)), "y": int(match.group(3))}, addressed)
        match = re.match(r"(?:redimensione|redimensionar) (?:a janela )?(.+?) para (\d+)[x ]+(\d+)$", normalized)
        if match:
            return self._intent(IntentType.RESIZE_WINDOW, raw, normalized,
                                {"title": match.group(1), "width": int(match.group(2)), "height": int(match.group(3))}, addressed)
        match = re.match(r"(?:coloque|mova) (?:o |a )?(.+?) (?:a|para a) (esquerda|direita)$", normalized)
        if match:
            return self._intent(IntentType.TILE_WINDOW, raw, normalized, {"title": match.group(1), "side": match.group(2)}, addressed)
        for verb, kind in (
            ("feche", IntentType.CLOSE_APP), ("encerre", IntentType.CLOSE_APP),
            ("minimize", IntentType.MINIMIZE_APP), ("maximize", IntentType.MAXIMIZE_APP),
            ("restaure", IntentType.RESTORE_APP), ("volte para", IntentType.SWITCH_WINDOW),
            ("altere para", IntentType.SWITCH_WINDOW), ("abra", IntentType.OPEN_APP),
            ("abre", IntentType.OPEN_APP), ("abrir", IntentType.OPEN_APP),
            ("inicie", IntentType.OPEN_APP),
        ):
            match = re.match(rf"{verb} (?:o |a )?(.+)$", normalized)
            if match:
                return self._intent(kind, raw, normalized, {"name": match.group(1)}, addressed)

        mode_match = re.search(r"\bmodo\s+(normal|trabalho|work|jogo|gaming|foco|focus|silencioso|silent|sono|sleep)\b", normalized)
        if mode_match:
            aliases = {"trabalho": "WORK", "work": "WORK", "jogo": "GAMING", "gaming": "GAMING",
                       "foco": "FOCUS", "focus": "FOCUS", "silencioso": "SILENT", "silent": "SILENT",
                       "sono": "SLEEP", "sleep": "SLEEP", "normal": "NORMAL"}
            return self._intent(IntentType.SET_MODE, raw, normalized, {"mode": aliases[mode_match.group(1)]}, addressed)
        if normalized in {"vamos trabalhar", "preparar ambiente", "prepare meu ambiente", "modo programacao"}:
            return self._intent(IntentType.RUN_MACRO, raw, normalized, {"name": "modo_programacao"}, addressed)

        match = re.match(r"quando eu (?:falar|disser) (.+?)[, ]+(?:quero dizer|significa) (.+)$", normalized)
        if match:
            return self._intent(IntentType.SET_ALIAS, raw, normalized,
                                {"phrase": match.group(1), "replacement": match.group(2)}, addressed)
        match = re.match(r"quando eu (?:falar|disser) (.+?)[, ]+(?:execute|rode) (?:a macro )?(.+)$", normalized)
        if match:
            return self._intent(IntentType.ADD_MACRO_TRIGGER, raw, normalized,
                                {"trigger": match.group(1), "name": match.group(2).replace(" ", "_")}, addressed)

        match = re.match(r"(?:o que voce lembra sobre|lembra de)\s+(.+)$", normalized)
        if match:
            return self._intent(IntentType.RECALL, raw, normalized, {"query": match.group(1)}, addressed)
        match = re.match(r"(?:lembre|lembra|memorize)(?:-se)? (?:que )?(.+)$", raw, re.IGNORECASE)
        if match:
            return self._intent(IntentType.REMEMBER, raw, normalized, {"content": match.group(1)}, addressed)

        return self._intent(IntentType.CONVERSATION, raw, normalized, confidence=0.35,
                            requires_ai=True, addressed=addressed)

    @staticmethod
    def _parse_keys(value: str) -> list[str]:
        aliases = {"control": "ctrl", "controle": "ctrl", "windows": "win", "espaco": "space",
                   "salvar": "s", "escape": "esc", "mais": "+"}
        parts = [part for part in re.split(r"\s*\+\s*|\s+", value) if part]
        return [aliases.get(part, part) for part in parts]

    @staticmethod
    def _intent(
        kind: IntentType,
        raw: str,
        normalized: str,
        arguments: dict[str, Any] | None = None,
        addressed: bool = False,
        confidence: float = 1.0,
        requires_ai: bool = False,
    ) -> Intent:
        return Intent(kind, arguments or {}, confidence, raw, normalized, requires_ai, addressed)
