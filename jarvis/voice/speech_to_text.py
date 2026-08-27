from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Transcription:
    text: str
    language: str
    probability: float
    duration: float


class FasterWhisperSTT:
    def __init__(self, model_name: str = "small", language: str = "pt", device: str = "auto") -> None:
        self.model_name = model_name
        self.language = language
        self.device = device
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel  # type: ignore
            except ImportError as exc:
                raise RuntimeError("Instale requirements-voice.txt para usar o Whisper") from exc
            actual_device = self.device
            if actual_device == "auto":
                actual_device = "cuda" if self._cuda_available() else "cpu"
            compute_type = "float16" if actual_device == "cuda" else "int8"
            self._model = WhisperModel(self.model_name, device=actual_device, compute_type=compute_type)
        return self._model

    async def transcribe(self, audio: Any) -> Transcription:
        return await asyncio.to_thread(self._transcribe_sync, audio)

    def _transcribe_sync(self, audio: Any) -> Transcription:
        model = self._load()
        segments, info = model.transcribe(
            audio,
            language=self.language,
            vad_filter=True,
            beam_size=3,
            condition_on_previous_text=False,
        )
        materialized = list(segments)
        text = " ".join(segment.text.strip() for segment in materialized).strip()
        duration = max((float(segment.end) for segment in materialized), default=0.0)
        probability = float(getattr(info, "language_probability", 1.0))
        return Transcription(text, str(getattr(info, "language", self.language)), probability, duration)

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import ctranslate2  # type: ignore
            return "cuda" in ctranslate2.get_supported_compute_types("cuda")
        except Exception:
            return False

