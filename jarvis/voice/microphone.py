from __future__ import annotations

import asyncio
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any

from jarvis.voice.audio_detector import VoiceActivityDetector


@dataclass(frozen=True, slots=True)
class MicrophoneDevice:
    index: int
    name: str
    channels: int
    default_samplerate: float


class Microphone:
    def __init__(
        self,
        device: str | int | None = None,
        sample_rate: int = 16_000,
        sensitivity: float = 0.55,
        silence_seconds: float = 1.1,
        max_seconds: float = 15.0,
    ) -> None:
        self.device = device
        self.sample_rate = sample_rate
        self.detector = VoiceActivityDetector(sensitivity)
        self.silence_seconds = silence_seconds
        self.max_seconds = max_seconds
        self._cancel = threading.Event()
        self.level = 0.0

    @staticmethod
    def devices() -> list[MicrophoneDevice]:
        try:
            import sounddevice as sd  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Instale requirements-voice.txt para usar o microfone") from exc
        return [
            MicrophoneDevice(index, str(item["name"]), int(item["max_input_channels"]), float(item["default_samplerate"]))
            for index, item in enumerate(sd.query_devices()) if int(item["max_input_channels"]) > 0
        ]

    def cancel(self) -> None:
        self._cancel.set()

    async def capture_utterance(self, initial_timeout: float = 20.0) -> Any | None:
        return await asyncio.to_thread(self._capture_sync, initial_timeout)

    async def wait_for_wake_word(self, detector: Any) -> None:
        await asyncio.to_thread(self._wait_for_wake_word_sync, detector)

    def _wait_for_wake_word_sync(self, detector: Any) -> None:
        try:
            import numpy as np  # type: ignore
            import sounddevice as sd  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Instale requirements-voice.txt para usar wake word") from exc
        self._cancel.clear()
        chunks: queue.Queue[Any] = queue.Queue()
        # openWakeWord trabalha em janelas de 80 ms a 16 kHz.
        block_size = 1280

        def callback(indata, frames, timing, status) -> None:
            chunks.put(indata[:, 0].copy())

        with sd.InputStream(
            samplerate=self.sample_rate, blocksize=block_size, device=self.device,
            channels=1, dtype="float32", callback=callback,
        ):
            while not self._cancel.is_set():
                try:
                    chunk = chunks.get(timeout=0.25)
                except queue.Empty:
                    continue
                self.level = min(1.0, self.detector.rms(chunk) * 15.0)
                pcm16 = (np.clip(chunk, -1.0, 1.0) * 32767).astype(np.int16)
                if detector.process(pcm16):
                    self.level = 1.0
                    detector.reset()
                    return

    def _capture_sync(self, initial_timeout: float) -> Any | None:
        try:
            import numpy as np  # type: ignore
            import sounddevice as sd  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Instale requirements-voice.txt para usar reconhecimento de voz") from exc

        self._cancel.clear()
        chunks: queue.Queue[Any] = queue.Queue()
        block_size = int(self.sample_rate * 0.03)

        def callback(indata, frames, timing, status) -> None:
            if status:
                # Overflow isolado não invalida a captura inteira.
                self.level *= 0.5
            chunks.put(indata[:, 0].copy())

        frames: list[Any] = []
        speech_started = False
        started_at = time.monotonic()
        last_voice = started_at
        with sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=block_size,
            device=self.device,
            channels=1,
            dtype="float32",
            callback=callback,
        ):
            while not self._cancel.is_set():
                now = time.monotonic()
                if not speech_started and now - started_at >= initial_timeout:
                    return None
                if speech_started and now - started_at >= self.max_seconds:
                    break
                try:
                    chunk = chunks.get(timeout=0.2)
                except queue.Empty:
                    continue
                self.level = min(1.0, self.detector.rms(chunk) * 15.0)
                voice = self.detector.has_voice(chunk)
                if voice:
                    if not speech_started:
                        speech_started = True
                        started_at = now
                    last_voice = now
                if speech_started:
                    frames.append(chunk)
                    if not voice and now - last_voice >= self.silence_seconds:
                        break
        self.level = 0.0
        return np.concatenate(frames).astype(np.float32) if frames else None
