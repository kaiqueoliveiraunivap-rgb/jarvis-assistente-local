from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
import winsound
from pathlib import Path

from jarvis.voice.base_voice import BaseVoice


class PiperVoice(BaseVoice):
    def __init__(self, model_path: str, executable: str | None = None, volume: int = 85) -> None:
        self.model_path = Path(model_path)
        self.executable = executable or shutil.which("piper") or "piper"
        self.volume = volume
        self._process: subprocess.Popen[bytes] | None = None
        self._stopped = False

    async def speak(self, text: str) -> None:
        await asyncio.to_thread(self._speak_sync, text)

    def _speak_sync(self, text: str) -> None:
        if not self.model_path.is_file():
            raise RuntimeError(f"Modelo Piper não encontrado: {self.model_path}")
        self._stopped = False
        with tempfile.TemporaryDirectory(prefix="jarvis_tts_") as directory:
            wav = Path(directory) / "speech.wav"
            self._process = subprocess.Popen(
                [self.executable, "--model", str(self.model_path), "--output_file", str(wav)],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            _, stderr = self._process.communicate(text.encode("utf-8"))
            return_code = self._process.returncode
            self._process = None
            if self._stopped:
                return
            if return_code != 0:
                raise RuntimeError(stderr.decode("utf-8", errors="replace").strip() or "Piper falhou")
            winsound.PlaySound(str(wav), winsound.SND_FILENAME)

    def stop(self) -> None:
        self._stopped = True
        winsound.PlaySound(None, winsound.SND_PURGE)
        if self._process and self._process.poll() is None:
            self._process.terminate()

