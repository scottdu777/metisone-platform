from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path

from metisone_ai_platform.semantic_layer.env import load_project_env

load_project_env()


@dataclass(frozen=True)
class EditServiceConfig:
    cube_model_dir: Path
    api_token: str | None = None
    compile_command: list[str] | None = None
    compile_cwd: Path | None = None


def load_config_from_env() -> EditServiceConfig:
    cube_model_dir = os.getenv("METISONE_CUBE_MODEL_DIR")
    if not cube_model_dir:
        raise RuntimeError("METISONE_CUBE_MODEL_DIR is required.")

    compile_command_raw = os.getenv("METISONE_CUBE_COMPILE_COMMAND")
    compile_command = (
        shlex.split(compile_command_raw) if compile_command_raw else None
    )

    compile_cwd_raw = os.getenv("METISONE_CUBE_COMPILE_CWD")
    compile_cwd = Path(compile_cwd_raw) if compile_cwd_raw else None

    return EditServiceConfig(
        cube_model_dir=Path(cube_model_dir),
        api_token=os.getenv("METISONE_SEMANTIC_EDIT_TOKEN"),
        compile_command=compile_command,
        compile_cwd=compile_cwd,
    )
