from __future__ import annotations

import re
from typing import Any


def format_query_answer(
    rows: list[dict[str, Any]],
    *,
    question: str | None = None,
    response_hint: str | None = None,
) -> str:
    if not rows:
        return "I couldn't find matching data for that question."

    if len(rows) == 1 and len(rows[0]) == 1:
        value = next(iter(rows[0].values()))
        return _format_single_value_answer(
            value,
            question=question,
            response_hint=response_hint,
        )

    rendered_rows = [_format_row(row) for row in rows[:20]]
    answer = "I found these results:\n" + "\n".join(rendered_rows)
    if len(rows) > 20:
        answer += f"\n{len(rows) - 20} more rows were not shown."
    return answer


def _format_single_value_answer(
    value: Any,
    *,
    question: str | None,
    response_hint: str | None,
) -> str:
    normalized_question = (question or "").strip().lower()
    normalized_hint = _clean_sentence(response_hint)

    if _asks_for_count(normalized_question):
        subject = _infer_count_subject(normalized_question)
        if subject:
            return f"There are {value} {subject}."
        return f"The count is {value}."

    if normalized_hint:
        return f"{normalized_hint}: {value}."

    return f"The answer is {value}."


def _asks_for_count(question: str) -> bool:
    return bool(
        re.search(r"\bhow many\b", question)
        or re.search(r"\bcount\b", question)
        or re.search(r"\bnumber of\b", question)
    )


def _infer_count_subject(question: str) -> str | None:
    if "action" in question and ("actor" in question or "actors" in question):
        return "actors who appeared in Action movies"
    if "action" in question and (
        "movie" in question or "movies" in question or "film" in question
    ):
        return "Action movies"
    if "actor" in question or "actors" in question:
        return "actors"
    if "movie" in question or "movies" in question:
        return "movies"
    if "film" in question or "films" in question:
        return "films"
    if "city" in question or "cities" in question:
        return "cities"
    if "customer" in question or "customers" in question:
        return "customers"
    return None


def _clean_sentence(text: str | None) -> str | None:
    if not text:
        return None
    return text.strip().rstrip(".")


def _format_row(row: dict[str, Any]) -> str:
    values = [f"{_short_name(name)}: {value}" for name, value in row.items()]
    return ", ".join(values)


def _short_name(member: str) -> str:
    return member.rsplit(".", 1)[-1].replace("_", " ")
