from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jarvis.core.executor import ExecutionPlan, PlanStep
from jarvis.core.intent_router import normalize_text
from jarvis.core.paths import custom_commands_path, resource_path
from jarvis.tools.registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class Macro:
    name: str
    description: str
    triggers: tuple[str, ...]
    actions: tuple[PlanStep, ...]


class MacroManager:
    def __init__(self, registry: ToolRegistry, path: Path | str | None = None) -> None:
        self._uses_default_path = path is None
        self.path = Path(path) if path else custom_commands_path()
        self.registry = registry
        self.aliases: dict[str, str] = {}
        self.macros: dict[str, Macro] = {}

    def load(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            template = resource_path("data", "custom_commands.json")
            if self._uses_default_path and template.is_file() and template.resolve() != self.path.resolve():
                shutil.copyfile(template, self.path)
            else:
                self._write({"aliases": {}, "macros": {}})
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Arquivo de macros inválido")
        aliases = raw.get("aliases", {})
        self.aliases = {normalize_text(str(key)): str(value) for key, value in aliases.items()} if isinstance(aliases, dict) else {}
        self.macros.clear()
        for name, value in raw.get("macros", {}).items():
            if not isinstance(value, dict):
                continue
            actions: list[PlanStep] = []
            for action in value.get("actions", []):
                if not isinstance(action, dict) or not isinstance(action.get("args", {}), dict):
                    raise ValueError(f"Ação inválida na macro {name}")
                spec = self.registry.require(str(action.get("tool", "")))
                arguments = spec.validate_arguments(action.get("args", {}))
                actions.append(PlanStep(spec.name, arguments, spec.description))
            if not actions:
                continue
            self.macros[name] = Macro(
                name, str(value.get("description", name)),
                tuple(normalize_text(str(trigger)) for trigger in value.get("triggers", [])), tuple(actions),
            )

    def match(self, text: str) -> Macro | None:
        normalized = normalize_text(text)
        return next((macro for macro in self.macros.values() if normalized in macro.triggers), None)

    def plan(self, name: str) -> ExecutionPlan | None:
        macro = self.macros.get(name)
        return ExecutionPlan(macro.actions, macro.description) if macro else None

    def create(self, name: str, actions: list[dict[str, Any]], triggers: list[str], description: str = "") -> Macro:
        steps: list[PlanStep] = []
        serialized: list[dict[str, Any]] = []
        for action in actions:
            spec = self.registry.require(str(action.get("tool", "")))
            args = spec.validate_arguments(action.get("args", {}))
            steps.append(PlanStep(spec.name, args, spec.description))
            serialized.append({"tool": spec.name, "args": args})
        if not steps:
            raise ValueError("Uma macro precisa conter ao menos uma ação")
        raw = self._raw()
        raw.setdefault("macros", {})[name] = {
            "description": description or name,
            "triggers": triggers,
            "actions": serialized,
        }
        self._write(raw)
        self.load()
        return self.macros[name]

    def set_alias(self, phrase: str, replacement: str) -> None:
        raw = self._raw()
        raw.setdefault("aliases", {})[normalize_text(phrase)] = replacement
        self._write(raw)
        self.load()

    def add_trigger(self, name: str, trigger: str) -> Macro:
        raw = self._raw()
        macros = raw.get("macros", {})
        if name not in macros:
            raise KeyError(f"Macro não encontrada: {name}")
        triggers = macros[name].setdefault("triggers", [])
        normalized = normalize_text(trigger)
        if normalized not in {normalize_text(str(item)) for item in triggers}:
            triggers.append(trigger)
        self._write(raw)
        self.load()
        return self.macros[name]

    def delete(self, name: str) -> None:
        raw = self._raw()
        macros = raw.get("macros", {})
        if not isinstance(macros, dict) or name not in macros:
            raise KeyError(f"Macro não encontrada: {name}")
        del macros[name]
        self._write(raw)
        self.load()

    def resolve_alias(self, value: str) -> str:
        return self.aliases.get(normalize_text(value), value)

    def _raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"aliases": {}, "macros": {}}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {"aliases": {}, "macros": {}}

    def _write(self, raw: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
