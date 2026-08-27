from __future__ import annotations

import json
from dataclasses import dataclass

from jarvis.ai.prompt_manager import PromptManager
from jarvis.ai.provider import AIMessage, AIProvider
from jarvis.core.executor import ExecutionPlan, PlanStep
from jarvis.core.intent_router import Intent, IntentType
from jarvis.tools.registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class PlanningOutcome:
    plan: ExecutionPlan | None = None
    response: str | None = None


class AIPlanner:
    def __init__(self, provider: AIProvider, registry: ToolRegistry, prompts: PromptManager) -> None:
        self.provider = provider
        self.registry = registry
        self.prompts = prompts

    async def plan(self, text: str, context: dict) -> PlanningOutcome:
        tools = [
            {
                "name": spec.name,
                "description": spec.description,
                "risk": spec.risk.name,
                "parameters": [name for name in spec.parameters],
            }
            for spec in self.registry.list()
            if spec.risk.name != "CRITICAL"
        ]
        prompt = self.prompts.planner_prompt(tools, text, context)
        response = await self.provider.chat([AIMessage("system", prompt)], json_mode=True)
        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError:
            return PlanningOutcome(response=response.content or "Não consegui interpretar isso com segurança.")
        if payload.get("kind") != "plan":
            return PlanningOutcome(response=str(payload.get("response", "Não tenho uma ação segura para isso.")))
        raw_steps = payload.get("steps")
        if not isinstance(raw_steps, list) or not 1 <= len(raw_steps) <= 8:
            return PlanningOutcome(response="O plano proposto não passou pela validação de segurança.")
        steps: list[PlanStep] = []
        try:
            for raw_step in raw_steps:
                if not isinstance(raw_step, dict) or not isinstance(raw_step.get("arguments", {}), dict):
                    raise ValueError("Passo inválido")
                spec = self.registry.require(str(raw_step.get("tool", "")))
                arguments = spec.validate_arguments(raw_step.get("arguments", {}))
                steps.append(PlanStep(spec.name, arguments, spec.description))
        except (KeyError, ValueError) as exc:
            return PlanningOutcome(response=f"Recusei um plano inválido: {exc}")
        return PlanningOutcome(ExecutionPlan(tuple(steps), str(payload.get("summary", text))))


class DeterministicPlanner:
    """Converte intents conhecidos em planos sem consultar um modelo."""

    _SIMPLE: dict[IntentType, str] = {
        IntentType.OPEN_APP: "open_app",
        IntentType.CLOSE_APP: "close_app",
        IntentType.MINIMIZE_APP: "minimize_app",
        IntentType.MAXIMIZE_APP: "maximize_app",
        IntentType.RESTORE_APP: "restore_app",
        IntentType.SWITCH_WINDOW: "switch_window",
        IntentType.MOVE_WINDOW: "move_window",
        IntentType.RESIZE_WINDOW: "resize_window",
        IntentType.SET_VOLUME: "set_volume",
        IntentType.VOLUME_UP: "volume_up",
        IntentType.VOLUME_DOWN: "volume_down",
        IntentType.MUTE: "mute",
        IntentType.UNMUTE: "unmute",
        IntentType.SET_BRIGHTNESS: "set_brightness",
        IntentType.TYPE_TEXT: "type_text",
        IntentType.PRESS_KEY: "press_key",
        IntentType.HOTKEY: "hotkey",
        IntentType.MOVE_MOUSE: "move_mouse",
        IntentType.CLICK: "click",
        IntentType.DOUBLE_CLICK: "double_click",
        IntentType.RIGHT_CLICK: "right_click",
        IntentType.SCROLL: "scroll",
        IntentType.READ_CLIPBOARD: "read_clipboard",
        IntentType.WRITE_CLIPBOARD: "write_clipboard",
        IntentType.OPEN_URL: "open_url",
        IntentType.WEB_SEARCH: "google_search",
        IntentType.SCREENSHOT: "take_screenshot",
        IntentType.CPU_USAGE: "get_cpu_usage",
        IntentType.RAM_USAGE: "get_ram_usage",
        IntentType.DISK_USAGE: "get_disk_usage",
        IntentType.BATTERY: "get_battery",
        IntentType.LIST_PROCESSES: "list_processes",
        IntentType.SEARCH_FILE: "search_file",
        IntentType.OPEN_FILE: "open_file",
        IntentType.OPEN_FOLDER: "open_folder",
        IntentType.CREATE_FOLDER: "create_folder",
        IntentType.COPY_FILE: "copy_file",
        IntentType.MOVE_FILE: "move_file",
        IntentType.RENAME_FILE: "rename_file",
        IntentType.PLAY_PAUSE: "play_pause_media",
        IntentType.NEXT_MEDIA: "next_media",
        IntentType.PREVIOUS_MEDIA: "previous_media",
        IntentType.LOCK_PC: "lock_pc",
        IntentType.SLEEP_PC: "sleep_pc",
        IntentType.SHUTDOWN_PC: "shutdown_pc",
        IntentType.RESTART_PC: "restart_pc",
        IntentType.ORGANIZE_WINDOWS: "organize_windows",
    }

    def plan(self, intent: Intent) -> ExecutionPlan | None:
        if intent.type is IntentType.TILE_WINDOW:
            side = intent.arguments.get("side")
            name = "tile_window_left" if side == "esquerda" else "tile_window_right"
            return ExecutionPlan((PlanStep(name, {"title": intent.arguments["title"]}),), intent.raw_text)
        if intent.type is IntentType.SYSTEM_STATUS:
            return ExecutionPlan((
                PlanStep("get_cpu_usage"), PlanStep("get_ram_usage"),
                PlanStep("get_disk_usage"), PlanStep("get_battery"),
            ), "Status do sistema")
        tool_name = self._SIMPLE.get(intent.type)
        if tool_name:
            return ExecutionPlan((PlanStep(tool_name, dict(intent.arguments)),), intent.raw_text)
        return None
