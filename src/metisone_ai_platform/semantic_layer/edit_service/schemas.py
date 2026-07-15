from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MeasureCreateRequest(BaseModel):
    name: str
    sql: str
    type: str = Field(alias="measure_type")
    extra_fields: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class DimensionCreateRequest(BaseModel):
    name: str
    sql: str
    type: str = Field(alias="dimension_type")
    extra_fields: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class JoinCreateRequest(BaseModel):
    name: str
    sql: str
    relationship: str
    extra_fields: dict[str, Any] = Field(default_factory=dict)


class MemberUpdateRequest(BaseModel):
    fields: dict[str, Any]


class EditResponse(BaseModel):
    success: bool
    message: str
    file_path: str
    cube: str
    member_kind: str
    member_name: str


class CompileResponse(BaseModel):
    succeeded: bool
    command: list[str]
    return_code: int
    stdout: str
    stderr: str


class AutoCompleteRequest(BaseModel):
    schemas: list[str] = Field(default_factory=lambda: ["public"])
    apply: bool = False
    bidirectional_joins: bool = True


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    success: bool
    message: str
    command: dict[str, Any]
    edit_result: EditResponse
