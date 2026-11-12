"""Runtime configuration. Values come from the environment / `.env` (see `.env.example`)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from `.env` into os.environ without overriding real env vars.

    A tiny parser is used on purpose so the app has no extra dependency and also works
    when started with `streamlit run app.py` instead of `scripts/start.sh`.
    """
    path = path or ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


@dataclass(frozen=True)
class Settings:
    base_url: str
    model: str
    keep_alive: str
    request_timeout: float


def get_settings() -> Settings:
    """Build settings from the environment (defaults only for non-sensitive values)."""
    load_env_file()
    return Settings(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        model=os.environ.get("OLLAMA_MODEL", "nemotron-3.5-lightning:30b-a3b-mlx"),
        keep_alive=os.environ.get("OLLAMA_KEEP_ALIVE", "15m"),
        request_timeout=float(os.environ.get("OLLAMA_TIMEOUT", "600")),
    )
