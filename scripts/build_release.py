from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path


VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
PYI_DIST = BUILD / "pyinstaller"
PYI_WORK = BUILD / "pyinstaller-work"
RELEASE = BUILD / "release"
DIST = ROOT / "dist"


def checked_remove(path: Path) -> None:
    resolved = path.resolve()
    if resolved.parent not in {ROOT.resolve(), BUILD.resolve()}:
        raise RuntimeError(f"Recusa ao limpar caminho fora do projeto: {resolved}")
    if resolved.exists():
        last_error: OSError | None = None
        for attempt in range(8):
            try:
                shutil.rmtree(resolved)
                return
            except OSError as exc:
                last_error = exc
                time.sleep(0.4 * (attempt + 1))
        if last_error:
            raise last_error


def fresh_build_directory(preferred: Path) -> Path:
    try:
        checked_remove(preferred)
        selected = preferred
    except OSError as exc:
        selected = preferred.with_name(f"{preferred.name}-{int(time.time())}")
        print(f"AVISO: OneDrive manteve um lock em {preferred}; usando {selected.name}: {exc}")
    selected.mkdir(parents=True, exist_ok=True)
    return selected


def run(command: list[str], **kwargs) -> None:
    print("+", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def copy_app(destination: Path) -> None:
    source = PYI_DIST / "JARVIS"
    if not (source / "JARVIS.exe").is_file() or not (source / "JARVIS-Debug.exe").is_file():
        raise RuntimeError("O build PyInstaller não produziu os dois executáveis")
    shutil.copytree(source, destination, dirs_exist_ok=True)


def copy_common(destination: Path) -> None:
    for filename in ("README.md", "requirements.txt", "requirements-voice.txt", "version.json"):
        shutil.copy2(ROOT / filename, destination / filename)
    shutil.copy2(ROOT / "packaging" / "README.txt", destination / "README.txt")
    shutil.copytree(ROOT / "assets", destination / "assets", dirs_exist_ok=True)
    for directory in ("config", "data", "models", "logs", "runtime"):
        (destination / directory).mkdir(parents=True, exist_ok=True)


def assemble_installer() -> Path:
    destination = RELEASE / f"JARVIS-Windows-v{VERSION}"
    copy_app(destination)
    copy_common(destination)
    for filename in ("install.bat", "uninstall.bat", "start_jarvis.bat", "start_debug.bat"):
        shutil.copy2(ROOT / "packaging" / filename, destination / filename)
    shutil.copytree(ROOT / "packaging" / "runtime", destination / "runtime", dirs_exist_ok=True)
    return destination


def assemble_portable() -> Path:
    destination = RELEASE / f"JARVIS-Portable-v{VERSION}"
    copy_app(destination)
    copy_common(destination)
    shutil.copy2(ROOT / "packaging" / "start_jarvis.bat", destination / "start_jarvis.bat")
    shutil.copy2(ROOT / "packaging" / "start_debug.bat", destination / "start_debug.bat")
    (destination / "portable.flag").write_text(
        "J.A.R.V.I.S. portable: configurações e dados permanecem nesta pasta.\n",
        encoding="utf-8",
    )
    return destination


EXCLUDED_PARTS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", "dist", "build", "logs", "cache", "models",
}
EXCLUDED_NAMES = {".env", "jarvis.db", "jarvis.db-shm", "jarvis.db-wal", "settings.json"}


def source_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if not path.is_file() or path.name in EXCLUDED_NAMES or path.suffix in {".pyc", ".log"}:
            continue
        files.append(path)
    return sorted(files)


def zip_tree(source: Path, destination: Path) -> None:
    prefix = source.name
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        directories = sorted(path for path in source.rglob("*") if path.is_dir())
        for directory in directories:
            relative = directory.relative_to(source).as_posix()
            if not any(directory.iterdir()):
                archive.writestr(f"{prefix}/{relative}/", b"")
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            archive.write(path, f"{prefix}/{path.relative_to(source).as_posix()}")


def zip_source(destination: Path) -> None:
    prefix = f"JARVIS-Source-v{VERSION}"
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for path in source_files():
            archive.write(path, f"{prefix}/{path.relative_to(ROOT).as_posix()}")


def verify_archive(path: Path, executable_required: bool) -> None:
    forbidden = ("/.git/", "/.venv/", "/__pycache__/", ".pyc", ".log", "jarvis.db")
    with zipfile.ZipFile(path) as archive:
        bad = []
        for name in archive.namelist():
            lowered = name.casefold()
            leaf = Path(name).name.casefold()
            if any(item in lowered for item in forbidden) or leaf == ".env":
                bad.append(name)
        if bad:
            raise RuntimeError(f"Arquivos proibidos em {path.name}: {bad[:5]}")
        corrupt = archive.testzip()
        if corrupt:
            raise RuntimeError(f"Arquivo corrompido em {path.name}: {corrupt}")
        if executable_required and not any(name.endswith("/JARVIS.exe") for name in archive.namelist()):
            raise RuntimeError(f"JARVIS.exe ausente em {path.name}")


def write_hashes(paths: list[Path]) -> None:
    lines = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    (DIST / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii")


def main(argv: list[str] | None = None) -> int:
    global PYI_DIST, PYI_WORK, RELEASE
    parser = argparse.ArgumentParser(description="Build da distribuição J.A.R.V.I.S.")
    parser.add_argument("--package-only", action="store_true", help="Reempacotar o build PyInstaller mais recente")
    args = parser.parse_args(argv)
    if sys.platform != "win32" or os.environ.get("PROCESSOR_ARCHITECTURE", "").casefold() not in {"amd64", "x86"}:
        raise RuntimeError("O pacote Windows deve ser compilado no Windows x64")
    run([sys.executable, "scripts/generate_icon.py"])
    if args.package_only:
        candidates = sorted(
            BUILD.glob("pyinstaller*/JARVIS/JARVIS.exe"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise RuntimeError("Nenhum build PyInstaller existente foi encontrado")
        PYI_DIST = candidates[0].parents[1]
        print(f"Reutilizando executável validado de {PYI_DIST}")
    else:
        PYI_DIST = fresh_build_directory(PYI_DIST)
        PYI_WORK = fresh_build_directory(PYI_WORK)
    RELEASE = fresh_build_directory(RELEASE)
    DIST.mkdir(parents=True, exist_ok=True)
    for old_archive in DIST.glob("JARVIS-*-v*.zip"):
        old_archive.unlink()
    (DIST / "SHA256SUMS.txt").unlink(missing_ok=True)
    if not args.package_only:
        run([
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--distpath", str(PYI_DIST), "--workpath", str(PYI_WORK), "jarvis.spec",
        ])
    installer = assemble_installer()
    portable = assemble_portable()
    archives = [
        DIST / f"JARVIS-Windows-v{VERSION}.zip",
        DIST / f"JARVIS-Portable-v{VERSION}.zip",
        DIST / f"JARVIS-Source-v{VERSION}.zip",
    ]
    zip_tree(installer, archives[0])
    zip_tree(portable, archives[1])
    zip_source(archives[2])
    for index, archive in enumerate(archives):
        verify_archive(archive, executable_required=index < 2)
    write_hashes(archives)
    print("\nDistribuição concluída:")
    for archive in archives:
        print(f"- {archive} ({archive.stat().st_size / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
