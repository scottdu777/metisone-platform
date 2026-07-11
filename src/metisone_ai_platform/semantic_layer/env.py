from __future__ import annotations


def load_project_env() -> None:
    """Load local .env values when python-dotenv is installed."""

    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv()
