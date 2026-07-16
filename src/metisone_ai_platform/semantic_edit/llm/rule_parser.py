from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal


Operation = Literal["create", "modify", "delete"]
MemberKind = Literal["measure", "dimension", "join"]


@dataclass(frozen=True)
class RuleBasedEditCommand:
    operation: Operation
    cube: str
    member_kind: MemberKind
    member_name: str
    sql: str | None = None
    member_type: str | None = None
    relationship: str | None = None
    fields: dict[str, Any] = field(default_factory=dict)


class RuleBasedSemanticParser:
    """Small deterministic parser used when no LLM API key is configured."""

    def parse(self, message: str) -> RuleBasedEditCommand:
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
            raise ValueError("Modify requires at least one field, for example `title Revenue`.")

        return RuleBasedEditCommand(
            operation=operation,
            cube=cube,
            member_kind=member_kind,
            member_name=member_name,
            sql=sql,
            member_type=member_type,
            relationship=relationship,
            fields=fields,
        )

    def _parse_operation(self, text: str) -> Operation:
        if self._contains_any(text, ("create", "add")):
            return "create"
        if self._contains_any(text, ("modify", "update", "change")):
            return "modify"
        if self._contains_any(text, ("delete", "remove", "drop")):
            return "delete"
        raise ValueError("Could not identify operation: create, modify, or delete.")

    def _parse_member_kind(self, text: str) -> MemberKind:
        if self._contains_any(text, ("measure", "metric")):
            return "measure"
        if "dimension" in text:
            return "dimension"
        if "join" in text:
            return "join"
        raise ValueError("Could not identify member kind: measure, dimension, or join.")

    def _parse_cube(self, text: str) -> str:
        pattern = r"\b(?:cube|model|on|in|for)\s+([A-Za-z_][A-Za-z0-9_]*)\b"
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

        raise ValueError(f"Could not identify {kind} name.")

    def _parse_fields(self, text: str) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for key in ("title", "description"):
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
