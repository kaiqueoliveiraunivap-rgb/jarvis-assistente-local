from __future__ import annotations

from jarvis.tools.risk import RiskLevel
from jarvis.tools.tool import ToolResult, tool


def _psutil():
    try:
        import psutil  # type: ignore
        return psutil
    except ImportError as exc:
        raise RuntimeError("Instale psutil para monitorar o computador") from exc


@tool("get_cpu_usage", "Consultar o uso da CPU", category="system")
def get_cpu_usage(interval: float = 0.15) -> ToolResult:
    value = float(_psutil().cpu_percent(interval=max(0.0, min(interval, 1.0))))
    return ToolResult.ok(f"CPU em {value:.0f}%.", {"percent": value})


@tool("get_ram_usage", "Consultar o uso da memória RAM", category="system")
def get_ram_usage() -> ToolResult:
    memory = _psutil().virtual_memory()
    gib = 1024 ** 3
    data = {"percent": float(memory.percent), "used_gb": round(memory.used / gib, 2), "total_gb": round(memory.total / gib, 2)}
    return ToolResult.ok(f"RAM em {memory.percent:.0f}% — {data['used_gb']} de {data['total_gb']} GB.", data)


@tool("get_disk_usage", "Consultar o uso do disco", category="system")
def get_disk_usage(path: str = "C:\\") -> ToolResult:
    usage = _psutil().disk_usage(path)
    gib = 1024 ** 3
    data = {"percent": float(usage.percent), "free_gb": round(usage.free / gib, 2), "total_gb": round(usage.total / gib, 2)}
    return ToolResult.ok(f"Disco em {usage.percent:.0f}%; {data['free_gb']} GB livres.", data)


@tool("get_battery", "Consultar a bateria", category="system")
def get_battery() -> ToolResult:
    battery = _psutil().sensors_battery()
    if battery is None:
        return ToolResult.ok("Este computador não informou uma bateria.", {"available": False})
    remaining = None if battery.secsleft < 0 else int(battery.secsleft)
    data = {"available": True, "percent": float(battery.percent), "plugged": bool(battery.power_plugged), "seconds_left": remaining}
    state = "carregando" if battery.power_plugged else "na bateria"
    return ToolResult.ok(f"Bateria em {battery.percent:.0f}%, {state}.", data)


@tool("list_processes", "Listar processos por consumo", category="system")
def list_processes(sort_by: str = "memory", limit: int = 10) -> ToolResult:
    psutil = _psutil()
    limit = max(1, min(int(limit), 50))
    if sort_by not in {"memory", "cpu"}:
        return ToolResult.fail("Ordenação deve ser memory ou cpu.", "INVALID_SORT")
    rows: list[dict[str, object]] = []
    for process in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
        try:
            rows.append({
                "pid": process.info["pid"],
                "name": process.info["name"] or "desconhecido",
                "memory_percent": round(float(process.info["memory_percent"] or 0), 2),
                "cpu_percent": round(float(process.info["cpu_percent"] or 0), 2),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    key = "memory_percent" if sort_by == "memory" else "cpu_percent"
    rows.sort(key=lambda row: float(row[key]), reverse=True)
    selected = rows[:limit]
    summary = ", ".join(f"{row['name']} {row[key]}%" for row in selected[:5])
    return ToolResult.ok(f"Maiores consumos: {summary}.", selected)


@tool("get_uptime", "Consultar o tempo ligado", category="system")
def get_uptime() -> ToolResult:
    import time
    seconds = max(0, int(time.time() - _psutil().boot_time()))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    return ToolResult.ok(f"Ligado há {hours}h {minutes}min.", {"seconds": seconds})

