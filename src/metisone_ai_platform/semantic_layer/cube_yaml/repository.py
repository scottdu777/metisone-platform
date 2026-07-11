from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from metisone_ai_platform.semantic_layer.cube_yaml.yaml_codec import YamlCodec


@dataclass(frozen=True)
class CubeYamlDocument:
    path: Path
    data: dict[str, Any]


class CubeYamlRepository:
    def __init__(
        self,
        root: str | Path,
        codec: YamlCodec | None = None,
    ) -> None:
        self.root = Path(root)
        self.codec = codec or YamlCodec()

    def list_files(self) -> list[Path]:
        if not self.root.exists():
            raise FileNotFoundError(f"Cube YAML directory does not exist: {self.root}")

        return sorted(
            [
                path
                for pattern in ("*.yml", "*.yaml")
                for path in self.root.rglob(pattern)
                if path.is_file()
            ]
        )

    def read_all(self) -> list[CubeYamlDocument]:
        return [self.read(path) for path in self.list_files()]

    def read(self, path: str | Path) -> CubeYamlDocument:
        resolved = self._resolve(path)
        text = resolved.read_text(encoding="utf-8")
        return CubeYamlDocument(path=resolved, data=self.codec.load(text))

    def save(self, document: CubeYamlDocument) -> None:
        resolved = self._resolve(document.path)
        resolved.write_text(self.codec.dump(document.data), encoding="utf-8")

    def find_by_cube(self, cube_name: str) -> CubeYamlDocument:
        for document in self.read_all():
            if document.data.get("cube") == cube_name or document.data.get("name") == cube_name:
                return document
            cubes = document.data.get("cubes")
            if isinstance(cubes, list):
                for cube in cubes:
                    if isinstance(cube, dict) and cube.get("name") == cube_name:
                        return document
            if document.path.stem == cube_name:
                return document

        raise ValueError(f"Cube YAML file not found for cube: {cube_name}")

    def _resolve(self, path: str | Path) -> Path:
        path = Path(path)
        resolved = path if path.is_absolute() else self.root / path
        resolved = resolved.resolve()
        root = self.root.resolve()

        if root != resolved and root not in resolved.parents:
            raise ValueError(f"Refusing to access file outside Cube YAML root: {path}")

        return resolved
