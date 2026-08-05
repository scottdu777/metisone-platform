from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class YamlCodec:
    """Small YAML adapter with optional ruamel/PyYAML support.

    ruamel.yaml is preferred because it can preserve comments and formatting.
    The fallback intentionally supports only the simple Cube YAML shape used by
    the MVP: scalar fields and top-level lists of dictionaries.
    """

    def __init__(self) -> None:
        self._ruamel_yaml = None
        self._pyyaml = None

        try:
            from ruamel.yaml import YAML

            yaml = YAML()
            yaml.preserve_quotes = True
            self._ruamel_yaml = yaml
        except ImportError:
            try:
                import yaml

                self._pyyaml = yaml
            except ImportError:
                pass

    def load(self, text: str) -> dict[str, Any]:
        if self._ruamel_yaml is not None:
            data = self._ruamel_yaml.load(text) or {}
            return dict(data)

        if self._pyyaml is not None:
            data = self._pyyaml.safe_load(text) or {}
            return dict(data)

        return self._load_simple(text)

    def dump(self, data: dict[str, Any]) -> str:
        if self._ruamel_yaml is not None:
            import io

            self._force_block_style(data)
            stream = io.StringIO()
            self._ruamel_yaml.dump(data, stream)
            return stream.getvalue()

        if self._pyyaml is not None:
            return self._pyyaml.safe_dump(
                data,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )

        return self._dump_simple(data)

    def _force_block_style(self, value: Any) -> None:
        if hasattr(value, "fa"):
            value.fa.set_block_style()
        if isinstance(value, dict):
            for child in value.values():
                self._force_block_style(child)
        elif isinstance(value, list):
            for child in value:
                self._force_block_style(child)

    def _load_simple(self, text: str) -> dict[str, Any]:
        root: dict[str, Any] = {}
        current_list: list[dict[str, Any]] | None = None
        current_item: dict[str, Any] | None = None

        for raw_line in text.splitlines():
            if not raw_line.strip() or raw_line.lstrip().startswith("#"):
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" "))
            line = raw_line.strip()

            if indent == 0 and line.endswith(":"):
                key = line[:-1]
                root[key] = []
                current_list = root[key]
                current_item = None
                continue

            if indent == 0 and ":" in line:
                key, value = line.split(":", 1)
                root[key.strip()] = self._parse_scalar(value.strip())
                current_list = None
                current_item = None
                continue

            if current_list is None:
                continue

            if line.startswith("- "):
                current_item = {}
                current_list.append(current_item)
                remainder = line[2:]
                if ":" in remainder:
                    key, value = remainder.split(":", 1)
                    current_item[key.strip()] = self._parse_scalar(value.strip())
                continue

            if current_item is not None and ":" in line:
                key, value = line.split(":", 1)
                current_item[key.strip()] = self._parse_scalar(value.strip())

        return root

    def _dump_simple(self, data: dict[str, Any]) -> str:
        lines: list[str] = []

        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    if not isinstance(item, dict):
                        lines.append(f"  - {self._format_scalar(item)}")
                        continue
                    entries = list(item.items())
                    if not entries:
                        lines.append("  - {}")
                        continue
                    first_key, first_value = entries[0]
                    lines.append(f"  - {first_key}: {self._format_scalar(first_value)}")
                    for child_key, child_value in entries[1:]:
                        lines.append(
                            f"    {child_key}: {self._format_scalar(child_value)}"
                        )
            else:
                lines.append(f"{key}: {self._format_scalar(value)}")

        return "\n".join(lines) + "\n"

    def _parse_scalar(self, value: str) -> Any:
        if value in ("", "null", "Null", "NULL", "~"):
            return None
        if value in ("true", "True"):
            return True
        if value in ("false", "False"):
            return False
        if (
            len(value) >= 2
            and value[0] in ("'", '"')
            and value[-1] == value[0]
        ):
            return value[1:-1]
        return value

    def _format_scalar(self, value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
            return "[" + ", ".join(self._format_scalar(item) for item in value) + "]"

        text = str(value)
        if not text or any(char in text for char in ":{}[]#,&*?!|-<>=%@`"):
            return '"' + text.replace('"', '\\"') + '"'
        return text
