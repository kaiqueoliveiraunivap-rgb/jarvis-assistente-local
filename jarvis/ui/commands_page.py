from __future__ import annotations

import inspect
import json
import re
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

from jarvis.automation.macros import MacroManager
from jarvis.tools.registry import ToolRegistry


class CommandsPage(QWidget):
    """Editor visual dos comandos personalizados persistidos pelo MacroManager."""

    command_created = Signal(str)
    command_deleted = Signal(str)

    def __init__(self, macros: MacroManager, registry: ToolRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.macros = macros
        self.registry = registry
        self._actions: list[dict[str, Any]] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        heading = QHBoxLayout()
        titles = QVBoxLayout()
        eyebrow = QLabel("AUTOMAÇÃO / BIBLIOTECA")
        eyebrow.setObjectName("sectionTitle")
        title = QLabel("Comandos personalizados")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Crie frases que executam uma ou várias ações locais.")
        subtitle.setObjectName("muted")
        titles.addWidget(eyebrow)
        titles.addWidget(title)
        titles.addWidget(subtitle)
        heading.addLayout(titles)
        heading.addStretch()
        self.new_button = QPushButton("＋  NOVO COMANDO")
        self.new_button.setObjectName("primary")
        self.new_button.clicked.connect(self.clear_form)
        heading.addWidget(self.new_button)
        layout.addLayout(heading)

        splitter = QSplitter()
        library = QFrame()
        library.setObjectName("panel")
        library_layout = QVBoxLayout(library)
        library_title = QLabel("COMANDOS CRIADOS")
        library_title.setObjectName("sectionTitle")
        self.command_list = QListWidget()
        self.command_list.setObjectName("commandList")
        self.command_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.command_list.currentItemChanged.connect(self._show_selected)
        self.empty_label = QLabel("Nenhum comando criado ainda.")
        self.empty_label.setObjectName("muted")
        self.empty_label.setWordWrap(True)
        library_layout.addWidget(library_title)
        library_layout.addWidget(self.command_list, 1)
        library_layout.addWidget(self.empty_label)

        editor = QFrame()
        editor.setObjectName("panel")
        editor_layout = QVBoxLayout(editor)
        editor_title = QLabel("CRIAR COMANDO")
        editor_title.setObjectName("sectionTitle")
        editor_layout.addWidget(editor_title)
        form = QFormLayout()
        form.setSpacing(11)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Ex.: iniciar_trabalho")
        self.description = QLineEdit()
        self.description.setPlaceholderText("O que este comando faz")
        self.triggers = QLineEdit()
        self.triggers.setPlaceholderText("Ex.: vamos trabalhar, iniciar meu dia")
        form.addRow("Nome", self.name)
        form.addRow("Descrição", self.description)
        form.addRow("Frases de ativação", self.triggers)
        editor_layout.addLayout(form)

        action_label = QLabel("AÇÕES DO COMANDO")
        action_label.setObjectName("sectionTitle")
        editor_layout.addWidget(action_label)
        action_row = QHBoxLayout()
        self.tool = QComboBox()
        for spec in sorted(self.registry.list(), key=lambda item: (item.category, item.name)):
            self.tool.addItem(f"{spec.description}  ·  {spec.name}", spec.name)
        self.tool.currentIndexChanged.connect(self._update_argument_hint)
        self.arguments = QLineEdit()
        self.arguments.setPlaceholderText('{"name": "chrome"}')
        self.add_action = QPushButton("ADICIONAR")
        self.add_action.clicked.connect(self._add_action)
        action_row.addWidget(self.tool, 2)
        action_row.addWidget(self.arguments, 2)
        action_row.addWidget(self.add_action)
        editor_layout.addLayout(action_row)
        self.argument_hint = QLabel()
        self.argument_hint.setObjectName("muted")
        self.argument_hint.setWordWrap(True)
        editor_layout.addWidget(self.argument_hint)
        self.action_list = QListWidget()
        self.action_list.setMaximumHeight(145)
        editor_layout.addWidget(self.action_list)

        controls = QHBoxLayout()
        remove_action = QPushButton("REMOVER AÇÃO")
        remove_action.clicked.connect(self._remove_action)
        self.delete_button = QPushButton("EXCLUIR COMANDO")
        self.delete_button.setObjectName("danger")
        self.delete_button.clicked.connect(self._delete_selected)
        save = QPushButton("SALVAR COMANDO")
        save.setObjectName("primary")
        save.clicked.connect(self._save)
        controls.addWidget(remove_action)
        controls.addStretch()
        controls.addWidget(self.delete_button)
        controls.addWidget(save)
        editor_layout.addLayout(controls)

        splitter.addWidget(library)
        splitter.addWidget(editor)
        splitter.setSizes([360, 680])
        layout.addWidget(splitter, 1)
        self._update_argument_hint()
        self.clear_form()

    def refresh(self, selected: str | None = None) -> None:
        self.macros.load()
        self.command_list.blockSignals(True)
        self.command_list.clear()
        for macro in sorted(self.macros.macros.values(), key=lambda item: item.name.casefold()):
            item = QListWidgetItem(f"{macro.description}\n  {'  •  '.join(macro.triggers) or 'sem frase de ativação'}")
            item.setData(256, macro.name)
            self.command_list.addItem(item)
            if macro.name == selected:
                self.command_list.setCurrentItem(item)
        self.command_list.blockSignals(False)
        self.empty_label.setVisible(self.command_list.count() == 0)
        if selected:
            self._load_macro(selected)

    def clear_form(self) -> None:
        self.command_list.clearSelection()
        self.name.clear()
        self.name.setReadOnly(False)
        self.description.clear()
        self.triggers.clear()
        self._actions.clear()
        self._render_actions()
        self.delete_button.setEnabled(False)
        self.name.setFocus()

    def _show_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current:
            self._load_macro(str(current.data(256)))

    def _load_macro(self, name: str) -> None:
        macro = self.macros.macros.get(name)
        if not macro:
            return
        self.name.setText(macro.name)
        self.name.setReadOnly(True)
        self.description.setText(macro.description)
        self.triggers.setText(", ".join(macro.triggers))
        self._actions = [{"tool": step.tool, "args": dict(step.arguments)} for step in macro.actions]
        self._render_actions()
        self.delete_button.setEnabled(True)

    def _update_argument_hint(self) -> None:
        spec = self.registry.get(str(self.tool.currentData() or ""))
        if not spec:
            self.argument_hint.clear()
            return
        parts = []
        for name, parameter in spec.parameters.items():
            required = parameter.default is inspect.Parameter.empty
            parts.append(f"{name}{'*' if required else ''}")
        suffix = ", ".join(parts) or "nenhum argumento"
        self.argument_hint.setText(f"Parâmetros: {suffix}. Use JSON; * indica obrigatório.")

    def _add_action(self) -> None:
        tool_name = str(self.tool.currentData() or "")
        try:
            raw = self.arguments.text().strip() or "{}"
            arguments = json.loads(raw)
            if not isinstance(arguments, dict):
                raise ValueError("Os argumentos precisam formar um objeto JSON.")
            arguments = self.registry.require(tool_name).validate_arguments(arguments)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Ação inválida", str(exc))
            return
        self._actions.append({"tool": tool_name, "args": arguments})
        self.arguments.clear()
        self._render_actions()

    def _remove_action(self) -> None:
        row = self.action_list.currentRow()
        if row >= 0:
            self._actions.pop(row)
            self._render_actions()

    def _render_actions(self) -> None:
        self.action_list.clear()
        for index, action in enumerate(self._actions, 1):
            args = json.dumps(action["args"], ensure_ascii=False)
            self.action_list.addItem(f"{index:02d}  {action['tool']}  {args}")

    def _save(self) -> None:
        name = re.sub(r"[^a-z0-9_]+", "_", self.name.text().strip().casefold()).strip("_")
        triggers = [item.strip() for item in self.triggers.text().split(",") if item.strip()]
        if not name or not triggers or not self._actions:
            QMessageBox.warning(self, "Campos incompletos", "Informe nome, ao menos uma frase e uma ação.")
            return
        try:
            self.macros.create(name, self._actions, triggers, self.description.text().strip())
        except (ValueError, KeyError) as exc:
            QMessageBox.warning(self, "Não foi possível salvar", str(exc))
            return
        self.refresh(name)
        self.command_created.emit(name)

    def _delete_selected(self) -> None:
        name = self.name.text().strip()
        if not name:
            return
        answer = QMessageBox.question(self, "Excluir comando", f"Excluir o comando “{name}”?" )
        if answer != QMessageBox.Yes:
            return
        try:
            self.macros.delete(name)
        except KeyError as exc:
            QMessageBox.warning(self, "Comando não encontrado", str(exc))
            return
        self.refresh()
        self.clear_form()
        self.command_deleted.emit(name)
