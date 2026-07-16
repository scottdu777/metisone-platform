from __future__ import annotations

import os

from metisone_ai_platform.core.env import load_project_env
from metisone_ai_platform.semantic_edit.llm.contracts import SemanticEditPlanner
from metisone_ai_platform.semantic_edit.llm.openai_planner import OpenAISemanticPlanner
from metisone_ai_platform.semantic_edit.llm.rule_based_planner import (
    RuleBasedSemanticPlanner,
)

load_project_env()


class LLMPlannerFactory:
    @staticmethod
    def mode_from_env() -> str:
        return (os.getenv("SEMANTIC_AGENT_MODE") or "auto").lower()

    @staticmethod
    def model_from_env() -> str:
        return os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"

    @staticmethod
    def has_api_key() -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    @staticmethod
    def create(mode: str | None = None) -> SemanticEditPlanner:
        resolved_mode = (mode or LLMPlannerFactory.mode_from_env()).lower()

        if resolved_mode == "rule":
            return RuleBasedSemanticPlanner()

        api_key = os.getenv("OPENAI_API_KEY")
        if resolved_mode == "openai" and not api_key:
            raise ValueError("OPENAI_API_KEY is required when SEMANTIC_AGENT_MODE=openai.")

        if api_key:
            return OpenAISemanticPlanner(api_key=api_key)

        return RuleBasedSemanticPlanner()
