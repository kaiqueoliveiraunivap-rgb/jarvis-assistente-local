from __future__ import annotations

from dataclasses import dataclass

from jarvis.computer.processes import get_battery, get_cpu_usage, get_disk_usage, get_ram_usage, get_uptime


@dataclass(frozen=True, slots=True)
class HardwareSnapshot:
    cpu_percent: float | None
    ram_percent: float | None
    disk_percent: float | None
    battery_percent: float | None
    plugged: bool | None
    uptime_seconds: int | None


def snapshot() -> HardwareSnapshot:
    cpu, ram, disk, battery, uptime = get_cpu_usage(0.05), get_ram_usage(), get_disk_usage(), get_battery(), get_uptime()
    return HardwareSnapshot(
        cpu.data.get("percent") if cpu.success else None,
        ram.data.get("percent") if ram.success else None,
        disk.data.get("percent") if disk.success else None,
        battery.data.get("percent") if battery.success and battery.data.get("available") else None,
        battery.data.get("plugged") if battery.success and battery.data.get("available") else None,
        uptime.data.get("seconds") if uptime.success else None,
    )

