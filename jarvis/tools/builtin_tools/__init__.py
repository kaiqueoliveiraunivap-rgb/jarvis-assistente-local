from __future__ import annotations

from jarvis.computer.apps import close_app, configure_app_aliases, find_app, is_app_running, open_app
from jarvis.computer.audio import (
    get_volume, mute, next_media, play_pause_media, previous_media, set_volume, unmute,
    volume_down, volume_up,
)
from jarvis.computer.clipboard import clear_clipboard, read_clipboard, write_clipboard
from jarvis.computer.display import get_brightness, set_brightness
from jarvis.computer.files import (
    copy_file, create_folder, delete_file, delete_folder, get_file_info, move_file,
    open_file, open_folder, rename_file, search_file,
)
from jarvis.computer.keyboard import hotkey, press_key, type_text
from jarvis.computer.mouse import click, double_click, drag, move_mouse, right_click, scroll
from jarvis.computer.processes import (
    get_battery, get_cpu_usage, get_disk_usage, get_ram_usage, get_uptime, list_processes,
)
from jarvis.computer.system import lock_pc, open_settings, open_task_manager, restart_pc, shutdown_pc, sleep_pc
from jarvis.computer.windows import (
    list_windows, maximize_app, minimize_app, move_window, organize_windows, resize_window,
    restore_app, switch_window, tile_window_left, tile_window_right,
)
from jarvis.browser.web_actions import google_search, open_url
from jarvis.core.config import AppSettings, ScreenAwareness
from jarvis.tools.registry import ToolRegistry
from jarvis.vision.screenshot import configure_screenshots, take_screenshot


BUILTIN_HANDLERS = (
    open_app, close_app, find_app, is_app_running,
    list_windows, minimize_app, maximize_app, restore_app, switch_window, move_window,
    resize_window, tile_window_left, tile_window_right, organize_windows,
    set_volume, get_volume, volume_up, volume_down, mute, unmute,
    play_pause_media, next_media, previous_media, set_brightness, get_brightness,
    type_text, press_key, hotkey, move_mouse, click, double_click, right_click, scroll, drag,
    read_clipboard, write_clipboard, clear_clipboard,
    search_file, open_file, open_folder, create_folder, copy_file, move_file, rename_file,
    get_file_info, delete_file, delete_folder,
    get_cpu_usage, get_ram_usage, get_disk_usage, get_battery, list_processes, get_uptime,
    lock_pc, sleep_pc, shutdown_pc, restart_pc, open_settings, open_task_manager,
    open_url, google_search, take_screenshot,
)


def build_registry(settings: AppSettings) -> ToolRegistry:
    configure_app_aliases(settings.app_aliases)
    configure_screenshots(settings.privacy.screen_awareness is not ScreenAwareness.OFF)
    registry = ToolRegistry()
    registry.register_many(BUILTIN_HANDLERS)
    return registry

