from __future__ import annotations

from typing import Any


def format_query_answer(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No matching data was found."

    if len(rows) == 1 and len(rows[0]) == 1:
        value = next(iter(rows[0].values()))
        return f"Query result: {value}"

    rendered_rows = [_format_row(row) for row in rows[:20]]
    answer = "Query results:\n" + "\n".join(rendered_rows)
    if len(rows) > 20:
        answer += f"\n{len(rows) - 20} more rows were not shown."
    return answer


def _format_row(row: dict[str, Any]) -> str:
    values = [f"{_short_name(name)}: {value}" for name, value in row.items()]
    return ", ".join(values)


def _short_name(member: str) -> str:
    return member.rsplit(".", 1)[-1].replace("_", " ")
