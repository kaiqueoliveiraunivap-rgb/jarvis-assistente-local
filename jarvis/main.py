from __future__ import annotations

import argparse
import asyncio
import json
import multiprocessing
import os
import sys
from pathlib import Path

from jarvis.core.assistant import JarvisAssistant, create_assistant
from jarvis.core.config import ConfigManager
from jarvis.core.logger import configure_logging
from jarvis.core.paths import ensure_user_directories, resource_path
from jarvis.database.database import Database


VERSION = "1.0.0"


async def run_cli(assistant: JarvisAssistant) -> int:
    print(await assistant.start())
    print("Modo texto ativo. Digite /sair para encerrar.")
    try:
        while True:
            try:
                text = await asyncio.to_thread(input, "Você > ")
            except (EOFError, KeyboardInterrupt):
                break
            if text.strip().casefold() in {"/sair", "/exit", "sair"}:
                break
            response = await assistant.handle_text(text)
            print(f"J.A.R.V.I.S. > {response.text}")
    finally:
        await assistant.stop()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. — assistente digital local")
    parser.add_argument("--cli", action="store_true", help="Executar sem interface gráfica")
    parser.add_argument("--no-monitor", action="store_true", help="Desativar monitoramento nesta sessão")
    parser.add_argument("--background", action="store_true", help="Iniciar somente na bandeja")
    parser.add_argument("--config", type=Path, help="Usar arquivo de configuração alternativo")
    parser.add_argument("--database", type=Path, help="Usar banco SQLite alternativo")
    parser.add_argument("--check", action="store_true", help="Verificar inicialização e encerrar")
    parser.add_argument("--diagnostics", action="store_true", help="Executar diagnóstico completo")
    parser.add_argument("--prepare", action="store_true", help="Preparar diretórios, configuração e banco")
    parser.add_argument("--download-stt", metavar="MODEL", help="Baixar antecipadamente um modelo faster-whisper")
    parser.add_argument("--ui-smoke", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version", version=f"J.A.R.V.I.S. {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    multiprocessing.freeze_support()
    args = build_parser().parse_args(argv)
    if args.diagnostics:
        from jarvis.diagnostics import main as diagnostics_main
        forwarded = ["--config", str(args.config)] if args.config else []
        return diagnostics_main(forwarded)
    if args.download_stt:
        print(f"Preparando faster-whisper '{args.download_stt}'. O download pode levar alguns minutos...")
        from faster_whisper import WhisperModel  # type: ignore
        WhisperModel(args.download_stt, device="cpu", compute_type="int8")
        print("Modelo STT pronto.")
        return 0
    directories = ensure_user_directories()
    os.environ.setdefault("HF_HOME", str(directories["cache"] / "huggingface"))
    manager = ConfigManager(args.config)
    try:
        settings = manager.load()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        settings = manager.settings
    configure_logging(settings.log_level)
    database = Database(args.database)
    database.initialize()
    if args.prepare:
        manifest = {
            "version": VERSION,
            "directories": {key: str(value) for key, value in directories.items()},
            "settings": str(manager.path),
            "database": str(database.path),
            "resources": str(resource_path()),
        }
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    assistant = JarvisAssistant(settings, database, manager)
    if args.check:
        async def check() -> int:
            greeting = await assistant.start(background_monitor=False)
            print(greeting)
            print(f"Banco: {database.path}")
            print(f"Tools: {len(assistant.registry.list())}")
            available, status = await assistant.models.provider().health()
            print(f"IA: {'OK' if available else 'indisponível'} — {status}")
            await assistant.stop()
            return 0
        return asyncio.run(check())
    if args.cli:
        return asyncio.run(run_cli(assistant))
    try:
        from jarvis.ui.main_window import launch
    except ImportError as exc:
        print(f"PySide6 não está instalado ({exc}). Iniciando modo texto.", file=sys.stderr)
        return asyncio.run(run_cli(assistant))
    if args.ui_smoke:
        settings.first_run_complete = True
        settings.voice.enabled = False
    return launch(
        assistant,
        monitor=not args.no_monitor and not bool(args.ui_smoke),
        background=args.background,
        smoke_output=args.ui_smoke,
    )


if __name__ == "__main__":
    raise SystemExit(main())
