from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jarvis.core.intent_router import normalize_text


class TranscriptWakeWord:
    def __init__(self, keyword: str = "jarvis") -> None:
        self.keyword = normalize_text(keyword)

    def extract(self, text: str) -> tuple[bool, str]:
        normalized = normalize_text(text)
        match = re.match(rf"^(?:ei\s+)?{re.escape(self.keyword)}\b[\s,.:;-]*(.*)$", normalized)
        return (True, match.group(1).strip()) if match else (False, text.strip())


class OpenWakeWordDetector:
    """Detector opcional para um modelo .tflite/.onnx treinado com a palavra Jarvis."""

    def __init__(self, model_path: str | None = None, threshold: float = 0.55, model_name: str = "hey_jarvis") -> None:
        try:
            from openwakeword.model import Model  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Instale openwakeword para usar o modelo dedicado") from exc
        if model_path:
            path = Path(model_path)
            if not path.is_file():
                raise FileNotFoundError(f"Modelo de wake word não encontrado: {path}")
            framework = "onnx" if path.suffix.casefold() == ".onnx" else "tflite"
            self.model = Model(wakeword_models=[str(path)], inference_framework=framework)
            self.model_name = path.stem
        else:
            # O wheel para Windows não inclui tflite-runtime; ONNXRuntime é suportado no Python 3.12.
            self.model = Model(wakeword_models=[model_name], inference_framework="onnx")
            self.model_name = model_name
        self.threshold = threshold

    def process(self, pcm16: Any) -> bool:
        prediction = self.model.predict(pcm16)
        score = float(prediction.get(self.model_name, max(prediction.values(), default=0.0)))
        return score >= self.threshold

    def reset(self) -> None:
        reset = getattr(self.model, "reset", None)
        if callable(reset):
            reset()
