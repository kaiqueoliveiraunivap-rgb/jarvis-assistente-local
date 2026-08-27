from __future__ import annotations

import math
from array import array
from typing import Any


class VoiceActivityDetector:
    def __init__(self, sensitivity: float = 0.55) -> None:
        if not 0 <= sensitivity <= 1:
            raise ValueError("Sensibilidade deve estar entre 0 e 1")
        self.sensitivity = sensitivity
        self.threshold = max(0.003, 0.045 * (1.0 - sensitivity))

    def rms(self, audio: Any) -> float:
        try:
            import numpy as np  # type: ignore
            values = np.asarray(audio, dtype=np.float32)
            return float(np.sqrt(np.mean(np.square(values)))) if values.size else 0.0
        except ImportError:
            values = array("f", audio)
            return math.sqrt(sum(value * value for value in values) / len(values)) if values else 0.0

    def has_voice(self, audio: Any) -> bool:
        return self.rms(audio) >= self.threshold

