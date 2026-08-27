from __future__ import annotations

import asyncio
import re
import threading

from jarvis.voice.base_voice import BaseVoice


def list_installed_voices() -> list[str]:
    """Retorna descrições SAPI sem tornar pywin32 obrigatório para abrir a interface."""
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except ImportError:
        return []
    pythoncom.CoInitialize()
    try:
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        return [str(item.GetDescription()) for item in voice.GetVoices()]
    except Exception:
        return []
    finally:
        pythoncom.CoUninitialize()


class WindowsSapiVoice(BaseVoice):
    def __init__(self, voice_name: str | None = None, speed: float = 1.0, volume: int = 85) -> None:
        self.voice_name = voice_name
        self.speed = speed
        self.volume = volume
        self._voice = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    async def speak(self, text: str) -> None:
        await asyncio.to_thread(self._speak_sync, text)

    def _speak_sync(self, text: str) -> None:
        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Instale pywin32 ou configure o Piper para usar voz") from exc
        pythoncom.CoInitialize()
        try:
            self._stop_event.clear()
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            with self._lock:
                self._voice = voice
            voice.Volume = max(0, min(int(self.volume), 100))
            # Uma cadência levemente mais lenta reduz o aspecto metálico das
            # vozes SAPI tradicionais, mantendo o controle de velocidade útil.
            voice.Rate = max(-10, min(round((self.speed - 1.0) * 8) - 1, 10))
            if self.voice_name:
                for candidate in voice.GetVoices():
                    if self.voice_name.casefold() in candidate.GetDescription().casefold():
                        voice.Voice = candidate
                        break
            else:
                candidates = list(voice.GetVoices())
                preferred = max(candidates, key=self._voice_score, default=None)
                if preferred is not None and self._voice_score(preferred) > 0:
                    voice.Voice = preferred
            voice.Speak(self._naturalize(text), 1)  # assíncrono dentro da thread COM
            while not voice.WaitUntilDone(100):
                if self._stop_event.is_set():
                    voice.Speak("", 3)  # purga a fila de fala
                    break
            with self._lock:
                self._voice = None
        finally:
            pythoncom.CoUninitialize()

    def stop(self) -> None:
        self._stop_event.set()

    @staticmethod
    def _voice_score(candidate) -> int:
        description = str(candidate.GetDescription()).casefold()
        score = 0
        for token, weight in (
            ("francisca", 12), ("maria", 10), ("brasil", 9), ("brazil", 9),
            ("português", 7), ("portuguese", 7), ("natural", 5), ("desktop", -2),
        ):
            if token in description:
                score += weight
        return score

    @staticmethod
    def _naturalize(text: str) -> str:
        value = re.sub(r"\s+", " ", text.strip())
        value = re.sub(r"\s*([,;:!?])\s*", r"\1 ", value)
        value = re.sub(r"\.\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", ".  ", value)
        return value


class SilentVoice(BaseVoice):
    async def speak(self, text: str) -> None:
        return None

    def stop(self) -> None:
        return None
