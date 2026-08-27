from __future__ import annotations

import base64
from pathlib import Path


def encode_image(path: Path | str, max_bytes: int = 12_000_000) -> str:
    target = Path(path)
    data = target.read_bytes()
    if len(data) > max_bytes:
        raise ValueError("Imagem grande demais para análise")
    return base64.b64encode(data).decode("ascii")

