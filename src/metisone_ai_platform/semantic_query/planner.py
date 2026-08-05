from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from metisone_ai_platform.semantic_query.contracts import DataQueryPlanner
from metisone_ai_platform.semantic_query.llm_logging import LLMTraceLogger
from metisone_ai_platform.semantic_query.models import (
    CubeFilter,
    CubeQuery,
    DataQueryPlan,
    DataQueryRequest,
)
from metisone_ai_platform.core.env import load_project_env

load_project_env()

DEFAULT_CUBE_ALIASES = {
    "film": {"movie", "movies", "films"},
}


class OpenAIDataQueryPlanner(DataQueryPlanner):
    """OpenAI planner that emits Cube REST /v1/load query JSON."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 60,
        trace_logger: LLMTraceLogger | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.trace_logger = trace_logger or LLMTraceLogger()

    def plan(
        self,
        request: DataQueryRequest,
        cube_metadata: dict[str, Any],
    ) -> DataQueryPlan:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIDataQueryPlanner.")
        content, request_payload = self._call_openai(
            request, self._compact_metadata(cube_metadata)
        )
        payload = self._parse_json(content)
        plan = self._to_plan(payload, request.limit, cube_metadata, request.question)
        self._write_trace(
            request=request,
            openai_request=request_payload,
            openai_response_content=content,
            parsed_payload=payload,
            plan=plan,
        )
        return plan

    def _call_openai(
        self,
        request: DataQueryRequest,
        compact_metadata: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        request_payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You convert natural-language data questions into Cube REST "
                        "/v1/load query JSON. Use Cube REST docs rules: queries are "
                        "plain JSON objects with measures, dimensions, filters, "
                        "timeDimensions, segments, limit, order, and timezone. Member "
                        "names must use cube_name.member_name, and must come only from "
                        "the provided Cube /v1/meta metadata. Copy each full member name "
                        "exactly as it appears in metadata. Metadata member names are "
                        "already cube-qualified, so never prepend the cube name again. "
                        "Never create a measure, dimension, segment, or time dimension "
                        "that is not listed in metadata. If a measure that sounds useful "
                        "does not exist, choose the closest existing measure from metadata "
                        "instead of inventing one. "
                        "Filters use member, "
                        "operator, and optional string values. Preserve spelling and "
                        "capitalization from the user's question. Prefer operator equals "
                        "for dimensions that represent exact labels, names, codes, "
                        "statuses, categories, locations, or other business values. Use "
                        "contains only when the user clearly asks for partial text "
                        "search. When filtering by a dimension that should be visible in "
                        "the answer, include that filter member in dimensions too. For "
                        "questions like 'how many X', choose the count measure from the "
                        "cube whose name, title, or description best matches X in the "
                        "current metadata; do not choose the event/action table merely "
                        "because the question uses a verb like rented, ordered, paid, or "
                        "used. Return only JSON "
                        "with this shape: "
                        "{\"query\":{...},\"response_hint\":\"short message\"}. "
                        "Do not include SQL. Do not include joins. Cube REST /load "
                        "does not accept a joins field; joins are inferred from the "
                        "semantic model. Do not invent members. When the question "
                        "can be answered from one cube, use members from that cube only. "
                        "Use members from multiple cubes only when the provided joins "
                        "show a path connecting every selected cube. "
                        "If the question asks whether a record exists, select "
                        "identifying dimensions and limit 1."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": request.question,
                            "default_limit": request.limit,
                            "cube_metadata": compact_metadata,
                            "examples": [
                                "Use only members present in cube_metadata.",
                                "For existence questions, select identifying dimensions and limit 1.",
                                "For how-many questions, use the most relevant count measure.",
                                "For exact business labels, use equals and preserve the user's value.",
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        data = json.dumps(request_payload).encode("utf-8")
        http_request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI data query planner failed with HTTP {exc.code}: {detail}") from exc

        try:
            content = response_payload["choices"][0]["message"]["content"]
            return content, request_payload
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"OpenAI returned an unexpected payload: {response_payload}") from exc

    def _write_trace(
        self,
        request: DataQueryRequest,
        openai_request: dict[str, Any],
        openai_response_content: str,
        parsed_payload: dict[str, Any],
        plan: DataQueryPlan,
    ) -> None:
        self.trace_logger.write(
            {
                "event": "semantic_query_llm_plan",
                "question": request.question,
                "model": self.model,
                "openai_base_url": self.base_url,
                "openai_request": openai_request,
                "openai_response_content": openai_response_content,
                "parsed_payload": parsed_payload,
                "parsed_plan": {
                    "cube_query": plan.cube_query.to_cube_payload(),
                    "response_hint": plan.response_hint,
                },
            }
        )

    def _compact_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        cubes = []
        for cube in metadata.get("cubes", []):
            if not isinstance(cube, dict):
                continue
            cubes.append(
                {
                    "name": cube.get("name"),
                    "title": cube.get("title"),
                    "measures": self._members(cube.get("measures")),
                    "dimensions": self._members(cube.get("dimensions")),
                    "segments": self._members(cube.get("segments")),
                    "joins": self._joins(cube.get("joins")),
                }
            )
        return {"cubes": cubes}

    def _members(self, items: Any) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        return [
            {
                "name": item.get("name"),
                "title": item.get("title"),
                "type": item.get("type"),
                "description": item.get("description"),
            }
            for item in items
            if isinstance(item, dict) and item.get("name")
        ]

    def _joins(self, items: Any) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        return [
            {
                key: item.get(key)
                for key in ("name", "cube", "to", "relationship")
                if item.get(key) is not None
            }
            for item in items
            if isinstance(item, dict)
        ]

    def _parse_json(self, content: str) -> dict[str, Any]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAI did not return valid JSON: {content}") from exc
        if not isinstance(payload, dict):
            raise ValueError("OpenAI data query planner JSON must be an object.")
        return payload

    def _to_plan(
        self,
        payload: dict[str, Any],
        default_limit: int,
        metadata: dict[str, Any],
        question: str = "",
    ) -> DataQueryPlan:
        raw_query = payload.get("query")
        if not isinstance(raw_query, dict):
            raise ValueError("OpenAI data query planner must return a query object.")

        known_members = self._known_members(metadata)

        filters = [
            CubeFilter(
                member=self._canonical_member(str(item["member"]), known_members),
                operator=str(item["operator"]),
                values=[str(value) for value in item.get("values", [])],
            )
            for item in raw_query.get("filters", [])
            if isinstance(item, dict) and item.get("member") and item.get("operator")
        ]
        query = CubeQuery(
            measures=[
                self._canonical_member(str(item), known_members)
                for item in raw_query.get("measures", [])
            ],
            dimensions=[
                self._canonical_member(str(item), known_members)
                for item in raw_query.get("dimensions", [])
            ],
            filters=filters,
            time_dimensions=self._canonical_time_dimensions(
                raw_query.get("timeDimensions", []), known_members
            ),
            segments=[
                self._canonical_member(str(item), known_members)
                for item in raw_query.get("segments", [])
            ],
            limit=int(raw_query.get("limit") or default_limit),
            order={
                self._canonical_member(str(member), known_members): str(direction)
                for member, direction in dict(raw_query.get("order", {})).items()
            },
        )
        query = self._normalize_query(query, question, metadata)
        response_hint = payload.get("response_hint")
        return DataQueryPlan(
            cube_query=query,
            response_hint=response_hint if isinstance(response_hint, str) else None,
        )

    def _normalize_query(
        self,
        query: CubeQuery,
        question: str,
        metadata: dict[str, Any],
    ) -> CubeQuery:
        known_members = self._members_by_kind(metadata)
        question = question.lower()
        dimensions = list(dict.fromkeys(query.dimensions))
        filters = [
            self._normalize_location_filter(
                self._normalize_filter(item, metadata),
                question,
                metadata,
            )
            for item in query.filters
        ]

        filter_dimensions: list[str] = []
        for item in filters:
            if item.member in known_members["dimensions"]:
                filter_dimensions.append(item.member)
        for member in dict.fromkeys(filter_dimensions):
            if member not in dimensions:
                dimensions.append(member)

        measures = self._normalize_count_measures(
            measures=query.measures,
            question=question,
            metadata=metadata,
        )

        return CubeQuery(
            measures=list(dict.fromkeys(measures)),
            dimensions=dimensions,
            filters=filters,
            time_dimensions=query.time_dimensions,
            segments=query.segments,
            limit=query.limit,
            order=query.order,
        )

    def _normalize_filter(
        self,
        item: CubeFilter,
        metadata: dict[str, Any],
    ) -> CubeFilter:
        if self._is_exact_label_dimension(item.member, metadata) and item.operator == "contains":
            return CubeFilter(
                member=item.member,
                operator="equals",
                values=[self._normalize_label_value(value) for value in item.values],
            )
        return item

    def _normalize_location_filter(
        self,
        item: CubeFilter,
        question: str,
        metadata: dict[str, Any],
    ) -> CubeFilter:
        if not item.values or not self._value_looks_like_location_phrase(item.values, question):
            return item
        current_score = self._location_dimension_score(item.member, metadata)
        best_member = item.member
        best_score = current_score
        for member in self._dimension_members(metadata):
            score = self._location_dimension_score(member, metadata)
            if score > best_score:
                best_member = member
                best_score = score
        if best_member == item.member:
            return item
        return self._normalize_filter(
            CubeFilter(
                member=best_member,
                operator=item.operator,
                values=item.values,
            ),
            metadata,
        )

    def _value_looks_like_location_phrase(
        self,
        values: list[str],
        question: str,
    ) -> bool:
        question = question.lower()
        markers = ("in", "at", "from", "near")
        for value in values:
            if not value:
                continue
            pattern = r"\b(" + "|".join(markers) + r")\s+" + re.escape(value.lower()) + r"\b"
            if re.search(pattern, question):
                return True
        return False

    def _location_dimension_score(
        self,
        member: str,
        metadata: dict[str, Any],
    ) -> int:
        dimension = self._member_metadata(member, "dimensions", metadata)
        if dimension is None:
            return 0
        terms = self._terms(
            " ".join(
                str(value or "")
                for value in (
                    dimension.get("name"),
                    dimension.get("title"),
                    dimension.get("description"),
                )
            )
        )
        priority = {
            "city": 6,
            "town": 6,
            "region": 5,
            "state": 5,
            "province": 5,
            "country": 5,
            "location": 4,
            "market": 4,
            "territory": 4,
            "area": 4,
            "address": 1,
        }
        return max((priority.get(term, 0) for term in terms), default=0)

    def _dimension_members(self, metadata: dict[str, Any]) -> list[str]:
        members: list[str] = []
        for cube in metadata.get("cubes", []):
            if not isinstance(cube, dict):
                continue
            for item in cube.get("dimensions") or []:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    members.append(item["name"])
        return members

    def _normalize_count_measures(
        self,
        *,
        measures: list[str],
        question: str,
        metadata: dict[str, Any],
    ) -> list[str]:
        result = list(measures)
        if not result or not any(self._looks_like_count_measure(measure) for measure in result):
            return result

        known_measures = self._members_by_kind(metadata)["measures"]
        best_count = self._best_count_measure(question, metadata)
        if best_count is None:
            return result

        return [
            best_count
            if self._looks_like_count_measure(measure) and measure not in known_measures
            else best_count
            if self._looks_like_count_measure(measure)
            else measure
            for measure in result
        ]

    def _looks_like_count_measure(self, member: str) -> bool:
        return member.endswith(".count") or member.endswith("_count")

    def _best_count_measure(
        self,
        question: str,
        metadata: dict[str, Any],
    ) -> str | None:
        best_name = None
        best_score = 0
        for cube in metadata.get("cubes", []):
            if not isinstance(cube, dict):
                continue
            count_measure = self._count_measure(cube)
            if count_measure is None:
                continue
            score = self._cube_relevance_score(question, cube)
            if score > best_score:
                best_name = count_measure
                best_score = score
        return best_name

    def _count_measure(self, cube: dict[str, Any]) -> str | None:
        for measure in cube.get("measures") or []:
            if isinstance(measure, dict) and measure.get("name", "").endswith(".count"):
                return measure["name"]
        return None

    def _cube_relevance_score(self, question: str, cube: dict[str, Any]) -> int:
        question_terms = self._terms(question)
        terms = self._terms(
            " ".join(
                str(value or "")
                for value in (
                    cube.get("name"),
                    cube.get("title"),
                    cube.get("description"),
                )
            )
        )
        score = 0
        for term in terms:
            variants = self._term_variants(term)
            if variants & question_terms:
                score += 3 if term == str(cube.get("name", "")).lower() else 1
            if term == str(cube.get("name", "")).lower() and variants & question_terms:
                score += 2
        return score

    def _term_variants(self, term: str) -> set[str]:
        variants = {term}
        if term.endswith("s") and len(term) > 1:
            variants.add(term[:-1])
        else:
            variants.add(f"{term}s")
        if term.endswith("y") and len(term) > 1:
            variants.add(f"{term[:-1]}ies")
        if term.endswith("ies") and len(term) > 3:
            variants.add(f"{term[:-3]}y")
        variants.update(DEFAULT_CUBE_ALIASES.get(term, set()))
        variants.update(self._configured_cube_aliases().get(term, set()))
        return variants

    def _configured_cube_aliases(self) -> dict[str, set[str]]:
        raw = os.getenv("METISONE_CUBE_ALIASES_JSON")
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        aliases: dict[str, set[str]] = {}
        for cube_name, values in payload.items():
            if isinstance(cube_name, str) and isinstance(values, list):
                aliases[cube_name.lower()] = {
                    str(value).lower()
                    for value in values
                    if str(value).strip()
                }
        return aliases

    def _is_exact_label_dimension(self, member: str, metadata: dict[str, Any]) -> bool:
        dimension = self._member_metadata(member, "dimensions", metadata)
        if dimension is None:
            return False
        text = " ".join(
            str(value or "")
            for value in (
                dimension.get("name"),
                dimension.get("title"),
                dimension.get("description"),
            )
        ).lower()
        label_tokens = {
            "name",
            "title",
            "label",
            "category",
            "type",
            "status",
            "city",
            "country",
            "state",
            "region",
            "code",
            "rating",
        }
        return any(token in self._terms(text) for token in label_tokens)

    def _member_metadata(
        self,
        member: str,
        kind: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        for cube in metadata.get("cubes", []):
            if not isinstance(cube, dict):
                continue
            for item in cube.get(kind) or []:
                if isinstance(item, dict) and item.get("name") == member:
                    return item
        return None

    def _normalize_label_value(self, value: str) -> str:
        if any(char.isupper() for char in value):
            return value
        return " ".join(part[:1].upper() + part[1:].lower() for part in value.split())

    def _terms(self, text: str) -> set[str]:
        return {
            part
            for part in text.lower().replace("_", " ").replace(".", " ").split()
            if part
        }

    def _members_by_kind(self, metadata: dict[str, Any]) -> dict[str, set[str]]:
        result = {"measures": set(), "dimensions": set(), "segments": set()}
        for cube in metadata.get("cubes", []):
            if not isinstance(cube, dict):
                continue
            for key in result:
                for item in cube.get(key) or []:
                    if isinstance(item, dict) and isinstance(item.get("name"), str):
                        result[key].add(item["name"])
        return result

    def _known_members(self, metadata: dict[str, Any]) -> set[str]:
        names: set[str] = set()
        for cube in metadata.get("cubes", []):
            if not isinstance(cube, dict):
                continue
            for key in ("measures", "dimensions", "segments"):
                for item in cube.get(key) or []:
                    if isinstance(item, dict) and isinstance(item.get("name"), str):
                        names.add(item["name"])
        return names

    def _canonical_member(self, member: str, known_members: set[str]) -> str:
        if member in known_members:
            return member
        parts = member.split(".")
        if len(parts) >= 3 and parts[0] == parts[1]:
            candidate = ".".join(parts[1:])
            if candidate in known_members:
                return candidate
        return member

    def _canonical_time_dimensions(
        self,
        items: Any,
        known_members: set[str],
    ) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        result: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            normalized = dict(item)
            if isinstance(normalized.get("dimension"), str):
                normalized["dimension"] = self._canonical_member(
                    normalized["dimension"], known_members
                )
            result.append(normalized)
        return result
