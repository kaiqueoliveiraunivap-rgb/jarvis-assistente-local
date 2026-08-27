from __future__ import annotations

import os
import shutil
from collections import deque
from pathlib import Path

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


_FOLDER_ALIASES = {
    "downloads": "Downloads",
    "documentos": "Documents",
    "documents": "Documents",
    "imagens": "Pictures",
    "pictures": "Pictures",
    "desktop": "Desktop",
    "area de trabalho": "Desktop",
    "músicas": "Music",
    "musicas": "Music",
}


def resolve_user_path(value: str) -> Path:
    cleaned = value.strip().strip('"')
    alias = _FOLDER_ALIASES.get(cleaned.casefold())
    if alias:
        candidates = [Path.home() / alias]
        localized = {"Documents": "Documentos", "Pictures": "Imagens"}.get(alias, alias)
        for variable in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            if root := os.getenv(variable):
                candidates.extend((Path(root) / alias, Path(root) / localized))
        return next((path.resolve() for path in candidates if path.exists()), candidates[0].resolve())
    expanded = Path(os.path.expandvars(os.path.expanduser(cleaned)))
    if not expanded.is_absolute():
        expanded = Path.home() / expanded
    return expanded.resolve()


def _open(path: Path) -> ToolResult:
    if not path.exists():
        return ToolResult.fail(f"Não encontrei {path}.", "PATH_NOT_FOUND")
    os.startfile(str(path))  # type: ignore[attr-defined]
    return ToolResult.ok(f"Abrindo {path.name or path}.", {"path": str(path)})


@tool("search_file", "Pesquisar arquivos e pastas em locais do usuário", category="files")
def search_file(query: str, root: str | None = None, limit: int = 20) -> ToolResult:
    needle = query.casefold().strip()
    if len(needle) < 2:
        return ToolResult.fail("Use ao menos dois caracteres na busca.", "QUERY_TOO_SHORT")
    limit = max(1, min(int(limit), 100))
    if root:
        roots = [resolve_user_path(root)]
    else:
        home = Path.home()
        roots = [home / name for name in ("Desktop", "Documents", "Downloads", "Pictures")]
        for variable in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            if cloud := os.getenv(variable):
                cloud_root = Path(cloud)
                roots.extend((cloud_root, cloud_root / "Documentos", cloud_root / "Documents"))
        roots = list(dict.fromkeys(path.resolve() for path in roots))
    queue = deque(path for path in roots if path.exists())
    results: list[str] = []
    visited = 0
    max_directories = 25_000
    while queue and len(results) < limit and visited < max_directories:
        directory = queue.popleft()
        visited += 1
        try:
            for entry in os.scandir(directory):
                if entry.name.startswith((".", "$")):
                    continue
                if needle in entry.name.casefold():
                    results.append(str(Path(entry.path)))
                    if len(results) >= limit:
                        break
                if entry.is_dir(follow_symlinks=False) and entry.name.casefold() not in {"node_modules", ".git", "appdata", "onedrivetemp"}:
                    queue.append(Path(entry.path))
        except (OSError, PermissionError):
            continue
    if not results:
        return ToolResult.ok(f"Não encontrei nada com “{query}”.", {"results": [], "scanned_directories": visited})
    return ToolResult.ok(f"Encontrei {len(results)} resultado(s).", {"results": results, "scanned_directories": visited})


@tool("open_file", "Abrir um arquivo", category="files", risk=RiskLevel.LOW)
def open_file(path: str) -> ToolResult:
    resolved = resolve_user_path(path)
    if resolved.exists() and not resolved.is_file():
        return ToolResult.fail("O caminho indicado não é um arquivo.", "NOT_A_FILE")
    return _open(resolved)


@tool("open_folder", "Abrir uma pasta", category="files", risk=RiskLevel.LOW)
def open_folder(path: str) -> ToolResult:
    resolved = resolve_user_path(path)
    if resolved.exists() and not resolved.is_dir():
        return ToolResult.fail("O caminho indicado não é uma pasta.", "NOT_A_FOLDER")
    return _open(resolved)


@tool("create_folder", "Criar uma pasta", category="files", risk=RiskLevel.MEDIUM)
def create_folder(path: str) -> ToolResult:
    resolved = resolve_user_path(path)
    if resolved.anchor == str(resolved):
        return ToolResult.fail("Não é permitido criar ou alterar a raiz do disco.", "PROTECTED_PATH")
    resolved.mkdir(parents=True, exist_ok=True)
    return ToolResult.ok(f"Pasta {resolved.name} pronta.", {"path": str(resolved)})


def _require_file(path: str) -> Path | ToolResult:
    resolved = resolve_user_path(path)
    if not resolved.is_file():
        return ToolResult.fail(f"Arquivo não encontrado: {resolved}", "FILE_NOT_FOUND")
    return resolved


@tool("copy_file", "Copiar um arquivo", category="files", risk=RiskLevel.MEDIUM)
def copy_file(source: str, destination: str) -> ToolResult:
    src = _require_file(source)
    if isinstance(src, ToolResult):
        return src
    dst = resolve_user_path(destination)
    if dst.is_dir():
        dst = dst / src.name
    if dst.exists():
        return ToolResult.fail("O destino já existe; não vou sobrescrevê-lo.", "DESTINATION_EXISTS")
    dst.parent.mkdir(parents=True, exist_ok=True)
    copied = shutil.copy2(src, dst)
    return ToolResult.ok("Arquivo copiado.", {"path": copied})


@tool("move_file", "Mover um arquivo", category="files", risk=RiskLevel.MEDIUM)
def move_file(source: str, destination: str) -> ToolResult:
    src = _require_file(source)
    if isinstance(src, ToolResult):
        return src
    dst = resolve_user_path(destination)
    if dst.is_dir():
        dst = dst / src.name
    if dst.exists():
        return ToolResult.fail("O destino já existe; não vou sobrescrevê-lo.", "DESTINATION_EXISTS")
    dst.parent.mkdir(parents=True, exist_ok=True)
    moved = shutil.move(str(src), str(dst))
    return ToolResult.ok("Arquivo movido.", {"path": moved})


@tool("rename_file", "Renomear um arquivo", category="files", risk=RiskLevel.MEDIUM)
def rename_file(path: str, new_name: str) -> ToolResult:
    src = _require_file(path)
    if isinstance(src, ToolResult):
        return src
    if Path(new_name).name != new_name or new_name in {".", ".."}:
        return ToolResult.fail("Forneça somente o novo nome, sem caminho.", "INVALID_NAME")
    destination = src.with_name(new_name)
    if destination.exists():
        return ToolResult.fail("Já existe um arquivo com esse nome.", "DESTINATION_EXISTS")
    src.rename(destination)
    return ToolResult.ok("Arquivo renomeado.", {"path": str(destination)})


@tool("get_file_info", "Consultar informações de um arquivo", category="files")
def get_file_info(path: str) -> ToolResult:
    target = resolve_user_path(path)
    if not target.exists():
        return ToolResult.fail("Caminho não encontrado.", "PATH_NOT_FOUND")
    stat = target.stat()
    data = {"path": str(target), "name": target.name, "is_file": target.is_file(), "size": stat.st_size, "modified": stat.st_mtime}
    return ToolResult.ok(f"{target.name}: {stat.st_size} bytes.", data)


@tool("delete_file", "Enviar um arquivo para a Lixeira", category="files", risk=RiskLevel.HIGH, confirmation_required=True)
def delete_file(path: str) -> ToolResult:
    target = _require_file(path)
    if isinstance(target, ToolResult):
        return target
    try:
        from send2trash import send2trash  # type: ignore
    except ImportError:
        return ToolResult.fail("Instale send2trash para exclusões recuperáveis.", "DEPENDENCY_MISSING")
    send2trash(str(target))
    return ToolResult.ok("Arquivo enviado para a Lixeira.")


@tool("delete_folder", "Enviar uma pasta para a Lixeira", category="files", risk=RiskLevel.HIGH, confirmation_required=True)
def delete_folder(path: str) -> ToolResult:
    target = resolve_user_path(path)
    protected = {Path.home().resolve()}
    for name in _FOLDER_ALIASES:
        protected.add(resolve_user_path(name))
    for variable in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        if root := os.getenv(variable):
            protected.add(Path(root).resolve())
    if not target.is_dir() or target in protected or target.parent == target:
        return ToolResult.fail("Pasta inexistente ou protegida.", "PROTECTED_PATH")
    try:
        from send2trash import send2trash  # type: ignore
    except ImportError:
        return ToolResult.fail("Instale send2trash para exclusões recuperáveis.", "DEPENDENCY_MISSING")
    send2trash(str(target))
    return ToolResult.ok("Pasta enviada para a Lixeira.")
