from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jarvis.ai.model_manager import ModelManager
from jarvis.ai.planner import AIPlanner, DeterministicPlanner
from jarvis.ai.prompt_manager import PromptManager
from jarvis.automation.macros import MacroManager
from jarvis.automation.proactive_engine import ProactiveEngine
from jarvis.automation.routine_detector import RoutineDetector
from jarvis.context.context_engine import ContextEngine
from jarvis.context.temporal_context import current_temporal_context
from jarvis.core.brain import Brain
from jarvis.core.command_router import CommandRouter
from jarvis.core.config import AppSettings, ConfigManager
from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.core.executor import ExecutionPlan, ExecutionReport, Executor
from jarvis.core.intent_router import Intent, IntentRouter, IntentType
from jarvis.core.logger import get_logger, redact
from jarvis.core.permissions import PermissionManager
from jarvis.core.state_manager import AssistantState, StateManager
from jarvis.database.database import Database
from jarvis.memory.memory_manager import MemoryManager
from jarvis.personality.personality_engine import PersonalityEngine
from jarvis.tools.builtin_tools import build_registry
from jarvis.vision.screen_analyzer import ScreenAnalyzer
from jarvis.vision.vision_manager import VisionManager


@dataclass(frozen=True, slots=True)
class AssistantResponse:
    text: str
    success: bool = True
    intent: str = ""
    data: Any = None
    confirmation_required: bool = False


class JarvisAssistant:
    def __init__(
        self,
        settings: AppSettings,
        database: Database,
        config_manager: ConfigManager | None = None,
    ) -> None:
        self.settings = settings
        self.database = database
        self.config_manager = config_manager
        self.log = get_logger("assistant")
        self.events = EventBus()
        self.state = StateManager()
        self.memory = MemoryManager(database, settings.privacy.memory_enabled)
        self.context = ContextEngine(self.memory)
        self.registry = build_registry(settings)
        self.permissions = PermissionManager()
        self.executor = Executor(self.registry, self.permissions, self.events)
        self.intent_router = IntentRouter(settings.voice.wake_word)
        self.command_router = CommandRouter(self.intent_router, DeterministicPlanner())
        self.macros = MacroManager(self.registry)
        self.macros.load()
        self.personality = PersonalityEngine(settings.personality)
        self.models = ModelManager(settings.ai)
        self.prompts = PromptManager(settings)
        provider = self.models.provider()
        ai_planner = AIPlanner(provider, self.registry, self.prompts)
        self.brain = Brain(provider, ai_planner, self.prompts, self.context, self.memory.short_term)
        self.vision = VisionManager(
            settings.privacy.screen_awareness,
            ScreenAnalyzer(provider, settings.ai.vision_model),
            self.events,
        )
        self.proactive = ProactiveEngine(settings.automation, self.events)
        self.routines = RoutineDetector()
        self._pending_confirmation: ExecutionPlan | None = None
        self._started = False
        self.events.subscribe(None, self._persist_event)
        self.events.subscribe(EventType.APP_OPENED, self._observe_routine)

    async def start(self, *, background_monitor: bool = True) -> str:
        if self._started:
            return "J.A.R.V.I.S. já está online."
        await self.state.transition(AssistantState.STARTING, "Inicializando serviços")
        self.database.initialize()
        self._started = True
        await self.events.publish(Event(EventType.SYSTEM_STARTED, {"model": self.settings.ai.model}, 20))
        if background_monitor:
            self.proactive.start()
        await self.state.transition(AssistantState.STANDBY, "Inicialização concluída")
        period = current_temporal_context().period
        greeting = self.personality.greeting(period)
        self.log.info(greeting)
        return greeting

    async def stop(self) -> None:
        if not self._started:
            return
        self.executor.cancel()
        await self.proactive.stop()
        await self.events.publish(Event(EventType.SYSTEM_SHUTDOWN, {}, 20))
        await self.state.transition(AssistantState.OFFLINE, "Encerramento solicitado")
        self.database.close()
        self._started = False

    async def handle_text(self, text: str) -> AssistantResponse:
        started = time.perf_counter()
        raw = text.strip()
        if not raw:
            return AssistantResponse("Não ouvi nada.", False, IntentType.UNKNOWN.value)
        await self.events.publish(Event(EventType.COMMAND_RECEIVED, {"text": redact(raw)}, 5))
        await self.state.transition(AssistantState.THINKING, "Interpretando comando")
        self.memory.short_term.add("user", raw)
        intent = self.intent_router.route(raw)
        success = False
        try:
            response = await self._handle_intent(intent)
            success = response.success
            self.memory.short_term.add("assistant", response.text)
            return response
        except Exception as exc:
            self.log.exception("Erro ao processar comando")
            await self.events.publish(Event(EventType.ERROR_OCCURRED, {"source": "command", "error": str(exc)}, 50))
            return AssistantResponse(f"Encontrei um problema: {exc}", False, intent.type.value)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000)
            self._record_command(raw, intent.type.value, success, duration_ms)
            await self.events.publish(Event(EventType.COMMAND_FINISHED, {"intent": intent.type.value, "success": success, "duration_ms": duration_ms}, 5))
            if self.state.state not in {AssistantState.OFFLINE, AssistantState.SLEEPING}:
                await self.state.transition(AssistantState.STANDBY, "Comando concluído")

    async def _handle_intent(self, intent: Intent) -> AssistantResponse:
        if intent.type is IntentType.CANCEL:
            self.executor.cancel()
            self._pending_confirmation = None
            return AssistantResponse(self.personality.acknowledgement("cancel", intent.raw_text), True, intent.type.value)

        if self._pending_confirmation:
            if intent.type is IntentType.CONFIRM:
                plan = self._pending_confirmation
                self._pending_confirmation = None
                return await self._execute(plan, confirm_first=True, intent=intent.type.value)
            if intent.type is IntentType.DENY:
                self._pending_confirmation = None
                return AssistantResponse("Tudo bem, cancelado.", True, intent.type.value)
            self._pending_confirmation = None

        if intent.type is IntentType.WAKE:
            await self.events.publish(Event(EventType.WAKE_WORD_DETECTED, {}, 10))
            await self.state.transition(AssistantState.LISTENING, "Wake word detectada")
            return AssistantResponse(self.personality.acknowledgement("listen", intent.raw_text), True, intent.type.value)

        if intent.type in {IntentType.CONFIRM, IntentType.DENY}:
            return AssistantResponse("Não há nenhuma ação aguardando confirmação.", True, intent.type.value)

        if intent.type is IntentType.SET_MODE:
            return await self._set_mode(str(intent.arguments["mode"]), intent.type.value)
        if intent.type is IntentType.REMEMBER:
            stored, message, memory_id = self.memory.remember(
                str(intent.arguments["content"]), explicitly_requested=True, metadata={"source": "voice"}
            )
            return AssistantResponse(message, stored, intent.type.value, {"memory_id": memory_id})
        if intent.type is IntentType.RECALL:
            records = self.memory.recall(str(intent.arguments["query"]))
            if not records:
                return AssistantResponse("Não encontrei nenhuma memória relacionada.", True, intent.type.value)
            text = "Eu me lembro de: " + "; ".join(record.content for record in records)
            return AssistantResponse(text, True, intent.type.value, records)
        if intent.type is IntentType.ANALYZE_SCREEN:
            await self.state.transition(AssistantState.OBSERVING, "Análise de tela autorizada pelo comando")
            analysis, path = await self.vision.inspect_screen(intent.raw_text)
            return AssistantResponse(analysis, path is not None, intent.type.value, {"path": str(path) if path else None})
        if intent.type is IntentType.RUN_MACRO:
            plan = self.macros.plan(str(intent.arguments["name"]))
            if not plan:
                return AssistantResponse("Essa macro ainda não está configurada.", False, intent.type.value)
            return await self._execute(plan, intent=intent.type.value)
        if intent.type is IntentType.SET_ALIAS:
            self.macros.set_alias(str(intent.arguments["phrase"]), str(intent.arguments["replacement"]))
            return AssistantResponse("Entendido. Vou usar esse significado daqui em diante.", True, intent.type.value)
        if intent.type is IntentType.ADD_MACRO_TRIGGER:
            try:
                macro = self.macros.add_trigger(str(intent.arguments["name"]), str(intent.arguments["trigger"]))
            except KeyError as exc:
                return AssistantResponse(str(exc), False, intent.type.value)
            return AssistantResponse(f"Gatilho adicionado à macro {macro.name}.", True, intent.type.value)

        # Triggers personalizados têm precedência sobre interpretação por IA.
        macro = self.macros.match(intent.raw_text)
        if macro:
            return await self._execute(ExecutionPlan(macro.actions, macro.description), intent=IntentType.RUN_MACRO.value)

        intent = self._resolve_aliases(intent)
        plan = DeterministicPlanner().plan(intent)
        if plan:
            return await self._execute(plan, intent=intent.type.value)

        await self.state.transition(AssistantState.PLANNING, "Consultando modelo local")
        try:
            outcome = await self.brain.interpret(intent.raw_text)
        except (ConnectionError, TimeoutError) as exc:
            return AssistantResponse(
                "O núcleo local de IA está indisponível. Os comandos diretos continuam funcionando; verifique o Ollama. "
                f"Detalhe: {exc}", False, intent.type.value,
            )
        if outcome.plan:
            return await self._execute(outcome.plan, intent=intent.type.value)
        return AssistantResponse(outcome.response or "Não consegui formar uma resposta.", True, intent.type.value)

    def _resolve_aliases(self, intent: Intent) -> Intent:
        arguments = dict(intent.arguments)
        if "name" in arguments:
            name = self.macros.resolve_alias(str(arguments["name"]))
            project = self.settings.project_aliases.get(name.casefold())
            arguments["name"] = project or name
        return Intent(
            intent.type, arguments, intent.confidence, intent.raw_text,
            intent.normalized_text, intent.requires_ai, intent.addressed,
        )

    async def _execute(self, plan: ExecutionPlan, *, confirm_first: bool = False, intent: str) -> AssistantResponse:
        await self.state.transition(AssistantState.EXECUTING, plan.summary)
        report = await self.executor.execute(plan, confirm_first=confirm_first)
        if report.confirmation_required:
            self._pending_confirmation = report.remaining_plan
            return AssistantResponse(report.message, False, intent, confirmation_required=True)
        if report.cancelled:
            return AssistantResponse("Cancelado.", False, intent)
        text = self._format_report(report)
        self.context.activity.record("command", summary=plan.summary, success=report.success)
        if report.success:
            self.memory.add_episode(f"Concluído: {plan.summary}", importance=40)
        return AssistantResponse(text, report.success, intent, report)

    @staticmethod
    def _format_report(report: ExecutionReport) -> str:
        if not report.executions:
            return report.message
        if len(report.executions) == 1:
            return report.executions[0].result.message
        messages = [execution.result.message for execution in report.executions if execution.result.message]
        return " ".join(messages)

    async def _set_mode(self, mode: str, intent: str) -> AssistantResponse:
        allowed = {"NORMAL", "WORK", "GAMING", "FOCUS", "SILENT", "SLEEP"}
        if mode not in allowed:
            return AssistantResponse("Modo desconhecido.", False, intent)
        self.settings.mode = mode
        if self.config_manager:
            self.config_manager.save(self.settings)
        if mode == "SLEEP":
            await self.state.transition(AssistantState.SLEEPING, "Modo sono")
            return AssistantResponse("Entrando em modo de baixo consumo.", True, intent)
        if mode == "WORK":
            self.personality.mood.observe("WORK_STARTED")
            plan = self.macros.plan("modo_programacao")
            if plan:
                return await self._execute(plan, intent=intent)
        messages = {
            "NORMAL": "Modo normal.", "GAMING": "Modo jogo. Reduzindo atividades em segundo plano.",
            "FOCUS": "Modo foco. Só vou interromper por algo importante.",
            "SILENT": "Modo silencioso. Respostas apenas na tela.",
        }
        return AssistantResponse(messages.get(mode, f"Modo {mode}."), True, intent)

    def _record_command(self, text: str, intent: str, success: bool, duration_ms: int) -> None:
        if not self.settings.privacy.save_history:
            return
        safe_text = redact(text)
        self.database.execute(
            "INSERT INTO commands(text, intent, success, duration_ms, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (safe_text, intent, int(success), duration_ms),
        )

    def _persist_event(self, event: Event) -> None:
        payload = json.dumps(event.payload, ensure_ascii=False, default=str)
        self.database.execute(
            "INSERT INTO events(event_type, importance, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (event.type.value, event.importance, redact(payload), event.created_at.isoformat()),
        )

    async def _observe_routine(self, event: Event) -> None:
        suggestion = self.routines.record_app_opened(str(event.payload.get("name", "")))
        if suggestion:
            await self.events.publish(Event(
                EventType.ROUTINE_SUGGESTION,
                {"message": suggestion.message, "sequence": suggestion.sequence},
                55,
            ))


def create_assistant(config_path: Path | str | None = None, database_path: Path | str | None = None) -> JarvisAssistant:
    manager = ConfigManager(config_path)
    settings = manager.load()
    database = Database(database_path)
    database.initialize()
    return JarvisAssistant(settings, database, manager)
