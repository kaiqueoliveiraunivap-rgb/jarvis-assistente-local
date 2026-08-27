from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from jarvis.core.config import VoiceSettings
from jarvis.voice.base_voice import BaseVoice
from jarvis.voice.microphone import Microphone
from jarvis.voice.piper_voice import PiperVoice
from jarvis.voice.speech_to_text import FasterWhisperSTT, Transcription
from jarvis.voice.text_to_speech import SilentVoice, WindowsSapiVoice
from jarvis.voice.wake_word import TranscriptWakeWord


TextHandler = Callable[[str], Awaitable[str]]


class VoiceManager:
    def __init__(self, settings: VoiceSettings) -> None:
        self.settings = settings
        self.microphone = Microphone(
            settings.microphone, sensitivity=settings.sensitivity,
            silence_seconds=settings.silence_seconds, max_seconds=settings.max_recording_seconds,
        )
        self.stt = FasterWhisperSTT(settings.whisper_model, settings.language)
        self.wake_word = TranscriptWakeWord(settings.wake_word)
        self.dedicated_wake_word = self._dedicated_wake_backend(settings)
        self.tts = self._voice_backend(settings)
        self._running = False
        self._conversation_until = 0.0

    @staticmethod
    def _dedicated_wake_backend(settings: VoiceSettings):
        if settings.wake_word.casefold().strip() != "jarvis" and not settings.wake_model_path:
            return None
        try:
            from jarvis.voice.wake_word import OpenWakeWordDetector
            return OpenWakeWordDetector(settings.wake_model_path, settings.sensitivity)
        except Exception:
            return None

    @staticmethod
    def _voice_backend(settings: VoiceSettings) -> BaseVoice:
        if not settings.tts_enabled:
            return SilentVoice()
        if settings.piper_model:
            return PiperVoice(settings.piper_model, settings.piper_executable, settings.volume)
        return WindowsSapiVoice(settings.voice_name, settings.speed, settings.volume)

    @property
    def conversation_active(self) -> bool:
        return time.monotonic() < self._conversation_until

    def activate_conversation(self) -> None:
        self._conversation_until = time.monotonic() + self.settings.conversation_timeout_seconds

    async def listen_once(self, timeout: float = 20.0) -> Transcription | None:
        audio = await self.microphone.capture_utterance(timeout)
        return await self.stt.transcribe(audio) if audio is not None else None

    async def speak(self, text: str) -> None:
        if text.strip():
            await self.tts.speak(text.strip())

    async def speak_with_barge_in(self, text: str) -> bool:
        """Fala e, quando há modelo dedicado, permite interrupção imediata por “Jarvis”."""
        if not text.strip():
            return False
        if self.dedicated_wake_word is None:
            await self.speak(text)
            return False
        speech_task = asyncio.create_task(self.speak(text))
        wake_task = asyncio.create_task(self.microphone.wait_for_wake_word(self.dedicated_wake_word))
        done, _ = await asyncio.wait({speech_task, wake_task}, return_when=asyncio.FIRST_COMPLETED)
        interrupted = wake_task in done and not wake_task.cancelled() and wake_task.exception() is None
        if interrupted:
            self.stop_speaking()
            self.activate_conversation()
        else:
            self.microphone.cancel()
        await asyncio.gather(speech_task, wake_task, return_exceptions=True)
        return interrupted

    def stop_speaking(self) -> None:
        self.tts.stop()

    def stop(self) -> None:
        self._running = False
        self.microphone.cancel()
        self.stop_speaking()

    async def run_forever(
        self,
        on_text: TextHandler,
        *,
        on_wake: Callable[[], Awaitable[None]] | None = None,
        on_transcription: Callable[[str], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self._running = True
        while self._running:
            try:
                dedicated_activation = self.dedicated_wake_word is not None and not self.conversation_active
                if dedicated_activation:
                    await self.microphone.wait_for_wake_word(self.dedicated_wake_word)
                    self.activate_conversation()
                    if on_wake:
                        await on_wake()
                    transcription = await self.listen_once(timeout=6.0)
                    if transcription is None or not transcription.text:
                        await self.speak("Estou ouvindo.")
                        continue
                else:
                    transcription = await self.listen_once(timeout=20.0)
                if transcription is None or not transcription.text:
                    continue
                if on_transcription:
                    on_transcription(transcription.text)
                woke, remainder = self.wake_word.extract(transcription.text)
                if dedicated_activation:
                    woke, remainder = True, transcription.text
                if not woke and not self.conversation_active:
                    continue
                if woke:
                    self.activate_conversation()
                    if on_wake:
                        await on_wake()
                command = remainder if woke else transcription.text
                if not command:
                    await self.speak("Estou ouvindo.")
                    continue
                response = await on_text(command)
                self.activate_conversation()
                interrupted = await self.speak_with_barge_in(response)
                if interrupted and on_wake:
                    await on_wake()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                if on_error:
                    on_error(exc)
                await asyncio.sleep(2.0)
