from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from jarvis.core.paths import log_path as default_log_path


_SENSITIVE = re.compile(
    r"(?i)(password|senha|token|secret|authorization|api[_-]?key)"
    r"(\s*(?:[=:]\s*|\bé\s+|\bis\s+)|\s+)([^\s,;]+)"
)
_CARD_LIKE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


def redact(value: Any) -> str:
    text = str(value)
    text = _SENSITIVE.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text)
    return _CARD_LIKE.sub("[REDACTED]", text)


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {key: redact(value) for key, value in record.args.items()}
            else:
                record.args = tuple(redact(value) for value in record.args)
        return True


def configure_logging(level: str = "INFO", log_path: Path | str | None = None) -> logging.Logger:
    target = Path(log_path) if log_path else default_log_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("jarvis")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    redaction = RedactionFilter()
    file_handler = RotatingFileHandler(
        target, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redaction)
    logger.addHandler(file_handler)
    if sys.stderr is not None:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(redaction)
        logger.addHandler(stream_handler)
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"jarvis.{name}")
