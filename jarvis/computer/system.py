from __future__ import annotations

import ctypes
import os
import subprocess

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


@tool("lock_pc", "Bloquear a sessão do Windows", category="system", risk=RiskLevel.MEDIUM)
def lock_pc() -> ToolResult:
    if not ctypes.windll.user32.LockWorkStation():
        return ToolResult.fail("O Windows recusou o bloqueio da sessão.", "WINDOWS_ERROR")
    return ToolResult.ok("Computador bloqueado.")


@tool("sleep_pc", "Suspender o computador", category="system", risk=RiskLevel.HIGH, confirmation_required=True)
def sleep_pc() -> ToolResult:
    result = ctypes.windll.powrprof.SetSuspendState(False, False, False)
    return ToolResult.ok("Suspendendo.") if result else ToolResult.fail("Não consegui suspender o computador.", "WINDOWS_ERROR")


@tool("shutdown_pc", "Desligar o computador", category="system", risk=RiskLevel.HIGH, confirmation_required=True)
def shutdown_pc(delay_seconds: int = 0) -> ToolResult:
    delay = max(0, min(int(delay_seconds), 3600))
    process = subprocess.run(["shutdown.exe", "/s", "/t", str(delay)], capture_output=True, text=True, check=False)
    if process.returncode != 0:
        return ToolResult.fail(process.stderr.strip() or "O Windows recusou o desligamento.", "WINDOWS_ERROR")
    return ToolResult.ok("Desligamento agendado.")


@tool("restart_pc", "Reiniciar o computador", category="system", risk=RiskLevel.HIGH, confirmation_required=True)
def restart_pc(delay_seconds: int = 0) -> ToolResult:
    delay = max(0, min(int(delay_seconds), 3600))
    process = subprocess.run(["shutdown.exe", "/r", "/t", str(delay)], capture_output=True, text=True, check=False)
    if process.returncode != 0:
        return ToolResult.fail(process.stderr.strip() or "O Windows recusou a reinicialização.", "WINDOWS_ERROR")
    return ToolResult.ok("Reinicialização agendada.")


@tool("open_settings", "Abrir as Configurações do Windows", category="system", risk=RiskLevel.LOW)
def open_settings() -> ToolResult:
    os.startfile("ms-settings:")  # type: ignore[attr-defined]
    return ToolResult.ok("Configurações abertas.")


@tool("open_task_manager", "Abrir o Gerenciador de Tarefas", category="system", risk=RiskLevel.LOW)
def open_task_manager() -> ToolResult:
    subprocess.Popen(["taskmgr.exe"], close_fds=True)
    return ToolResult.ok("Gerenciador de Tarefas aberto.")

