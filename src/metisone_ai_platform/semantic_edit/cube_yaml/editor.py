from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from metisone_ai_platform.semantic_edit.cube_yaml.repository import (
    CubeYamlDocument,
    CubeYamlRepository,
)


MemberKind = Literal["measure", "dimension", "join"]


@dataclass(frozen=True)
class SemanticEditResult:
    success: bool
    message: str
    file_path: str
    cube: str
    member_kind: MemberKind
    member_name: str


class CubeSemanticLayerEditor:
    def __init__(self, repository: CubeYamlRepository) -> None:
        self.repository = repository

    def create_measure(
        self,
        cube: str,
        name: str,
        sql: str,
        measure_type: str,
        **extra_fields: Any,
    ) -> SemanticEditResult:
        return self._create_member(
            cube,
            "measure",
            {"name": name, "sql": sql, "type": measure_type, **extra_fields},
        )

    def modify_measure(
        self,
        cube: str,
        name: str,
        **updates: Any,
    ) -> SemanticEditResult:
        return self._modify_member(cube, "measure", name, updates)

    def delete_measure(self, cube: str, name: str) -> SemanticEditResult:
        return self._delete_member(cube, "measure", name)

    def create_dimension(
        self,
        cube: str,
        name: str,
        sql: str,
        dimension_type: str,
        **extra_fields: Any,
    ) -> SemanticEditResult:
        return self._create_member(
            cube,
            "dimension",
            {"name": name, "sql": sql, "type": dimension_type, **extra_fields},
        )

    def modify_dimension(
        self,
        cube: str,
        name: str,
        **updates: Any,
    ) -> SemanticEditResult:
        return self._modify_member(cube, "dimension", name, updates)

    def delete_dimension(self, cube: str, name: str) -> SemanticEditResult:
        return self._delete_member(cube, "dimension", name)

    def create_join(
        self,
        cube: str,
        name: str,
        sql: str,
        relationship: str,
        **extra_fields: Any,
    ) -> SemanticEditResult:
        return self._create_member(
            cube,
            "join",
            {
                "name": name,
                "sql": sql,
                "relationship": relationship,
                **extra_fields,
            },
        )

    def modify_join(self, cube: str, name: str, **updates: Any) -> SemanticEditResult:
        return self._modify_member(cube, "join", name, updates)

    def delete_join(self, cube: str, name: str) -> SemanticEditResult:
        return self._delete_member(cube, "join", name)

    def _create_member(
        self,
        cube: str,
        kind: MemberKind,
        payload: dict[str, Any],
    ) -> SemanticEditResult:
        document = self.repository.find_by_cube(cube)
        collection = self._collection(document, cube, kind)
        name = payload["name"]

        if self._find_index(collection, name) is not None:
            raise ValueError(f"{kind.title()} already exists in {cube}: {name}")

        collection.append(payload)
        self.repository.save(document)
        return self._result(True, f"{kind.title()} {name} created.", document, cube, kind, name)

    def _modify_member(
        self,
        cube: str,
        kind: MemberKind,
        name: str,
        updates: dict[str, Any],
    ) -> SemanticEditResult:
        document = self.repository.find_by_cube(cube)
        collection = self._collection(document, cube, kind)
        index = self._find_index(collection, name)

        if index is None:
            raise ValueError(f"{kind.title()} not found in {cube}: {name}")

        collection[index].update({key: value for key, value in updates.items() if value is not None})
        self.repository.save(document)
        return self._result(True, f"{kind.title()} {name} modified.", document, cube, kind, name)

    def _delete_member(
        self,
        cube: str,
        kind: MemberKind,
        name: str,
    ) -> SemanticEditResult:
        document = self.repository.find_by_cube(cube)
        collection = self._collection(document, cube, kind)
        index = self._find_index(collection, name)

        if index is None:
            raise ValueError(f"{kind.title()} not found in {cube}: {name}")

        del collection[index]
        self.repository.save(document)
        return self._result(True, f"{kind.title()} {name} deleted.", document, cube, kind, name)

    def _collection(
        self,
        document: CubeYamlDocument,
        cube: str,
        kind: MemberKind,
    ) -> list[dict[str, Any]]:
        key = self._collection_key(kind)
        target = self._cube_data(document, cube)
        value = target.setdefault(key, [])
        if value is None:
            value = []
            target[key] = value
        if not isinstance(value, list):
            raise ValueError(f"Cube YAML field must be a list: {key}")
        return value

    def _cube_data(self, document: CubeYamlDocument, cube_name: str) -> dict[str, Any]:
        cubes = document.data.get("cubes")
        if isinstance(cubes, list):
            for cube in cubes:
                if isinstance(cube, dict) and cube.get("name") == cube_name:
                    return cube
            raise ValueError(f"Cube not found in YAML document: {cube_name}")

        return document.data

    def _collection_key(self, kind: MemberKind) -> str:
        return {
            "measure": "measures",
            "dimension": "dimensions",
            "join": "joins",
        }[kind]

    def _find_index(
        self,
        collection: list[dict[str, Any]],
        name: str,
    ) -> int | None:
        for index, item in enumerate(collection):
            if item.get("name") == name:
                return index
        return None

    def _result(
        self,
        success: bool,
        message: str,
        document: CubeYamlDocument,
        cube: str,
        kind: MemberKind,
        name: str,
    ) -> SemanticEditResult:
        return SemanticEditResult(
            success=success,
            message=message,
            file_path=str(document.path),
            cube=cube,
            member_kind=kind,
            member_name=name,
        )
