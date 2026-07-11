from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CubeCompileResult:
    succeeded: bool
    command: list[str]
    return_code: int
    stdout: str
    stderr: str


class CubeCompiler:
    """Runs the project-specific Cube recompilation command.

    The MVP environment may use docker compose, cube dev, or another wrapper.
    Keeping the command configurable avoids baking deployment details into the
    semantic layer editor.
    """

    def __init__(self, command: list[str], cwd: str | Path | None = None) -> None:
        if not command:
            raise ValueError("Cube compile command cannot be empty.")
        self.command = command
        self.cwd = Path(cwd) if cwd is not None else None

    def compile(self) -> CubeCompileResult:
        completed = subprocess.run(
            self.command,
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        return CubeCompileResult(
            succeeded=completed.returncode == 0,
            command=self.command,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
