from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from jarvis.core.paths import settings_path


class ScreenAwareness(StrEnum):
    OFF = "OFF"
    ON_DEMAND = "ON_DEMAND"
    ACTIVE = "ACTIVE"


class ProactivityLevel(StrEnum):
    OFF = "OFF"
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


@dataclass(slots=True)
class VoiceSettings:
    enabled: bool = True
    microphone: str | None = None
    wake_word: str = "jarvis"
    wake_model_path: str | None = None
    whisper_model: str = "small"
    language: str = "pt"
    sensitivity: float = 0.55
    silence_seconds: float = 1.1
    max_recording_seconds: float = 15.0
    conversation_timeout_seconds: float = 35.0
    tts_enabled: bool = True
    piper_executable: str | None = None
    piper_model: str | None = None
    voice_name: str | None = None
    speed: float = 0.92
    volume: int = 85


@dataclass(slots=True)
class AISettings:
    provider: str = "ollama"
    model: str = "qwen3:4b"
    vision_model: str | None = None
    endpoint: str = "http://127.0.0.1:11434"
    temperature: float = 0.35
    request_timeout_seconds: float = 90.0


@dataclass(slots=True)
class PersonalitySettings:
    formality: int = 70
    sarcasm: int = 20
    verbosity: int = 35
    initiative: int = 50
    humor: int = 20


@dataclass(slots=True)
class PrivacySettings:
    screen_awareness: ScreenAwareness = ScreenAwareness.ON_DEMAND
    camera_enabled: bool = False
    save_history: bool = True
    memory_enabled: bool = True


@dataclass(slots=True)
class AutomationSettings:
    proactivity: ProactivityLevel = ProactivityLevel.NORMAL
    alert_threshold: int = 70
    monitor_interval_seconds: float = 30.0
    cooldown_seconds: int = 900


@dataclass(slots=True)
class AppSettings:
    user_name: str = "Usuário"
    assistant_name: str = "J.A.R.V.I.S."
    start_with_windows: bool = False
    start_minimized: bool = False
    first_run_complete: bool = False
    mode: str = "NORMAL"
    log_level: str = "INFO"
    app_aliases: dict[str, str] = field(default_factory=lambda: {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "spotify": "spotify.exe",
        "discord": "discord.exe",
        "vs code": "code.cmd",
        "vscode": "code.cmd",
        "explorador": "explorer.exe",
        "explorer": "explorer.exe",
        "bloco de notas": "notepad.exe",
        "notepad": "notepad.exe",
        "calculadora": "calc.exe",
    })
    project_aliases: dict[str, str] = field(default_factory=dict)
    voice: VoiceSettings = field(default_factory=VoiceSettings)
    ai: AISettings = field(default_factory=AISettings)
    personality: PersonalitySettings = field(default_factory=PersonalitySettings)
    privacy: PrivacySettings = field(default_factory=PrivacySettings)
    automation: AutomationSettings = field(default_factory=AutomationSettings)


class ConfigManager:
    """Carrega configurações JSON, aplica ambiente e grava de forma atômica."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else settings_path()
        self.settings = AppSettings()

    def load(self) -> AppSettings:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("A raiz da configuração deve ser um objeto JSON")
                self.settings = self._from_dict(raw)
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                backup = self.path.with_suffix(".invalid.json")
                try:
                    self.path.replace(backup)
                except OSError:
                    backup = self.path
                self.settings = AppSettings()
                self.save()
                raise ValueError(f"Configuração inválida; uma nova foi criada: {exc}") from exc
        else:
            self.save()
        self._apply_environment()
        self._validate()
        return self.settings

    def save(self, settings: AppSettings | None = None) -> None:
        if settings is not None:
            self.settings = settings
        self._validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(self.settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def _from_dict(self, raw: dict[str, Any]) -> AppSettings:
        defaults = AppSettings()
        scalar_names = {
            "user_name", "assistant_name", "start_with_windows", "start_minimized",
            "first_run_complete", "mode", "log_level", "app_aliases", "project_aliases",
        }
        scalar = {name: raw[name] for name in scalar_names if name in raw}
        privacy_data = self._known(raw.get("privacy"), PrivacySettings)
        automation_data = self._known(raw.get("automation"), AutomationSettings)
        if "screen_awareness" in privacy_data:
            privacy_data["screen_awareness"] = ScreenAwareness(privacy_data["screen_awareness"])
        if "proactivity" in automation_data:
            automation_data["proactivity"] = ProactivityLevel(automation_data["proactivity"])
        return AppSettings(
            **scalar,
            voice=VoiceSettings(**self._known(raw.get("voice"), VoiceSettings)),
            ai=AISettings(**self._known(raw.get("ai"), AISettings)),
            personality=PersonalitySettings(**self._known(raw.get("personality"), PersonalitySettings)),
            privacy=PrivacySettings(**privacy_data),
            automation=AutomationSettings(**automation_data),
        ) if raw else defaults

    @staticmethod
    def _known(value: Any, data_class: type[Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        allowed = data_class.__dataclass_fields__.keys()
        return {key: item for key, item in value.items() if key in allowed}

    def _apply_environment(self) -> None:
        mapping = {
            "JARVIS_USER_NAME": (self.settings, "user_name"),
            "JARVIS_ASSISTANT_NAME": (self.settings, "assistant_name"),
            "JARVIS_AI_PROVIDER": (self.settings.ai, "provider"),
            "JARVIS_AI_MODEL": (self.settings.ai, "model"),
            "JARVIS_OLLAMA_ENDPOINT": (self.settings.ai, "endpoint"),
            "JARVIS_LOG_LEVEL": (self.settings, "log_level"),
        }
        for variable, (target, attribute) in mapping.items():
            if value := os.getenv(variable):
                setattr(target, attribute, value)

    def _validate(self) -> None:
        for field_name in ("formality", "sarcasm", "verbosity", "initiative", "humor"):
            value = getattr(self.settings.personality, field_name)
            if not isinstance(value, int) or not 0 <= value <= 100:
                raise ValueError(f"personality.{field_name} precisa estar entre 0 e 100")
        if not 0 <= self.settings.voice.volume <= 100:
            raise ValueError("voice.volume precisa estar entre 0 e 100")
        if not 0.5 <= self.settings.voice.speed <= 1.5:
            raise ValueError("voice.speed precisa estar entre 0.5 e 1.5")
        if not 0.0 <= self.settings.voice.sensitivity <= 1.0:
            raise ValueError("voice.sensitivity precisa estar entre 0 e 1")
        if not 0 <= self.settings.automation.alert_threshold <= 100:
            raise ValueError("automation.alert_threshold precisa estar entre 0 e 100")
        endpoint = self.settings.ai.endpoint.rstrip("/")
        if not endpoint.startswith(("http://127.0.0.1", "http://localhost", "https://")):
            raise ValueError("O endpoint de IA deve ser local ou usar HTTPS")
        self.settings.ai.endpoint = endpoint
