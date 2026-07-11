from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from metisone_ai_platform.semantic_layer.cube_yaml import CubeSemanticLayerEditor
from metisone_ai_platform.semantic_layer.cube_yaml.editor import SemanticEditResult


Operation = Literal["create", "modify", "delete"]
MemberKind = Literal["measure", "dimension", "join"]


@dataclass(frozen=True)
class SemanticEditCommand:
    operation: Operation
    cube: str
    member_kind: MemberKind
    member_name: str
    sql: str | None = None
    member_type: str | None = None
    relationship: str | None = None
    fields: dict[str, Any] = field(default_factory=dict)


class RuleBasedSemanticEditAgent:
    """MVP natural-language agent for Cube semantic layer edits.

    This intentionally supports a constrained command style so the file-editing
    service remains deterministic and easy to debug before adding an LLM parser.
    """

    def __init__(self, editor: CubeSemanticLayerEditor) -> None:
        self.editor = editor

    def handle(self, message: str) -> tuple[SemanticEditCommand, SemanticEditResult]:
        command = self.parse(message)
        result = self.execute(command)
        return command, result

    def parse(self, message: str) -> SemanticEditCommand:
        text = message.strip()
        lowered = text.lower()

        operation = self._parse_operation(lowered)
        member_kind = self._parse_member_kind(lowered)
        cube = self._parse_cube(text)
        member_name = self._parse_member_name(text, member_kind)
        sql = self._parse_value(text, "sql")
        member_type = self._parse_value(text, "type")
        relationship = self._parse_value(text, "relationship")
        fields = self._parse_fields(text)

        if operation == "create":
            if member_kind in ("measure", "dimension") and not sql:
                raise ValueError("Create measure/dimension requires `sql ...`.")
            if member_kind in ("measure", "dimension") and not member_type:
                raise ValueError("Create measure/dimension requires `type ...`.")
            if member_kind == "join" and not relationship:
                raise ValueError("Create join requires `relationship ...`.")

        if operation == "modify" and not fields:
            raise ValueError(
                "Modify requires at least one field, for example `title Revenue`."
            )

        return SemanticEditCommand(
            operation=operation,
            cube=cube,
            member_kind=member_kind,
            member_name=member_name,
            sql=sql,
            member_type=member_type,
            relationship=relationship,
            fields=fields,
        )

    def execute(self, command: SemanticEditCommand) -> SemanticEditResult:
        if command.member_kind == "measure":
            return self._execute_measure(command)
        if command.member_kind == "dimension":
            return self._execute_dimension(command)
        return self._execute_join(command)

    def _execute_measure(self, command: SemanticEditCommand) -> SemanticEditResult:
        if command.operation == "create":
            assert command.sql is not None
            assert command.member_type is not None
            return self.editor.create_measure(
                command.cube,
                command.member_name,
                command.sql,
                command.member_type,
                **command.fields,
            )
        if command.operation == "modify":
            return self.editor.modify_measure(
                command.cube,
                command.member_name,
                **command.fields,
            )
        return self.editor.delete_measure(command.cube, command.member_name)

    def _execute_dimension(self, command: SemanticEditCommand) -> SemanticEditResult:
        if command.operation == "create":
            assert command.sql is not None
            assert command.member_type is not None
            return self.editor.create_dimension(
                command.cube,
                command.member_name,
                command.sql,
                command.member_type,
                **command.fields,
            )
        if command.operation == "modify":
            return self.editor.modify_dimension(
                command.cube,
                command.member_name,
                **command.fields,
            )
        return self.editor.delete_dimension(command.cube, command.member_name)

    def _execute_join(self, command: SemanticEditCommand) -> SemanticEditResult:
        if command.operation == "create":
            assert command.sql is not None
            assert command.relationship is not None
            return self.editor.create_join(
                command.cube,
                command.member_name,
                command.sql,
                command.relationship,
                **command.fields,
            )
        if command.operation == "modify":
            return self.editor.modify_join(
                command.cube,
                command.member_name,
                **command.fields,
            )
        return self.editor.delete_join(command.cube, command.member_name)

    def _parse_operation(self, text: str) -> Operation:
        if self._contains_any(text, ("create", "add", "新增", "创建", "添加")):
            return "create"
        if self._contains_any(text, ("modify", "update", "change", "修改", "更新")):
            return "modify"
        if self._contains_any(text, ("delete", "remove", "drop", "删除", "移除")):
            return "delete"
        raise ValueError("Could not identify operation: create, modify, or delete.")

    def _parse_member_kind(self, text: str) -> MemberKind:
        if self._contains_any(text, ("measure", "metric", "指标", "度量")):
            return "measure"
        if self._contains_any(text, ("dimension", "维度")):
            return "dimension"
        if self._contains_any(text, ("join", "关联", "连接")):
            return "join"
        raise ValueError("Could not identify member kind: measure, dimension, or join.")

    def _parse_cube(self, text: str) -> str:
        patterns = (
            r"\b(?:cube|model|on|in|for)\s+([A-Za-z_][A-Za-z0-9_]*)\b",
            r"在\s*([A-Za-z_][A-Za-z0-9_]*)",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        raise ValueError("Could not identify cube, for example `on payment`.")

    def _parse_member_name(self, text: str, kind: MemberKind) -> str:
        explicit = re.search(
            r"\b(?:name|named|called)\s+([A-Za-z_][A-Za-z0-9_]*)\b",
            text,
            flags=re.IGNORECASE,
        )
        if explicit:
            return explicit.group(1)

        after_kind = re.search(
            rf"\b(?:{kind}|metric)\s+([A-Za-z_][A-Za-z0-9_]*)\b",
            text,
            flags=re.IGNORECASE,
        )
        if after_kind:
            return after_kind.group(1)

        chinese = re.search(r"(?:名为|叫)\s*([A-Za-z_][A-Za-z0-9_]*)", text)
        if chinese:
            return chinese.group(1)

        raise ValueError(f"Could not identify {kind} name.")

    def _parse_fields(self, text: str) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for key in ("sql", "type", "title", "description", "relationship"):
            value = self._parse_value(text, key)
            if value is not None:
                fields[key] = value
        return fields

    def _parse_value(self, text: str, key: str) -> str | None:
        pattern = rf"\b{key}\s*(?:=|:)?\s*(\"[^\"]+\"|'[^']+'|[^\s]+)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None

        value = match.group(1).strip()
        if len(value) >= 2 and value[0] in ("'", '"') and value[-1] == value[0]:
            return value[1:-1]
        return value

    def _contains_any(self, text: str, needles: tuple[str, ...]) -> bool:
        return any(needle in text for needle in needles)
