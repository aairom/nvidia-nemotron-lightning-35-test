"""UI-independent generation logic: parameters -> Ollama request -> live metrics.

Keeping this separate from Streamlit makes it unit-testable against a stub Ollama server.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterator

from .metrics import RunMetrics, from_stats
from .ollama_client import OllamaClient

THINK_MODES = ("Auto (per category)", "Off", "On", "Medium")


def build_options(temperature: float, top_p: float, num_ctx: int, num_predict: int) -> dict:
    """Map UI values to Ollama `options`. These are re-read on every request, so changing a
    slider affects the very next message."""
    if not 0.0 <= temperature <= 2.0:
        raise ValueError("temperature must be within 0..2")
    if not 0.0 < top_p <= 1.0:
        raise ValueError("top_p must be within (0, 1]")
    if num_ctx < 512:
        raise ValueError("num_ctx must be at least 512")
    return {"temperature": temperature, "top_p": top_p, "num_ctx": int(num_ctx),
            "num_predict": int(num_predict)}


def resolve_think(mode: str, category_think: str) -> bool | str:
    """Translate the UI reasoning selector into the value of Ollama's `think` field.

    The model accepts False, True or "medium" (see `ollama show`)."""
    chosen = category_think if mode.startswith("Auto") else mode.lower()
    if chosen == "off":
        return False
    if chosen == "medium":
        return "medium"
    if chosen == "on":
        return True
    raise ValueError(f"unknown reasoning mode: {mode!r}")


def build_messages(system_prompt: str, history: list[dict], prompt: str,
                   use_history: bool, max_turns: int = 6) -> list[dict]:
    """System prompt + (optionally) the last `max_turns` turns of the conversation + new prompt."""
    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if use_history:
        for m in history[-max_turns * 2:]:
            if m["role"] in ("user", "assistant") and m.get("content"):
                messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": prompt})
    return messages


@dataclass
class LiveUpdate:
    """Snapshot yielded while streaming."""
    content: str
    thinking: str
    chunks: int                 # streamed chunks ~ tokens (live approximation)
    elapsed: float
    ttft: float
    live_tps: float             # approximate until the final exact metrics arrive
    final: RunMetrics | None = None


def stream_answer(client: OllamaClient, model: str, messages: list[dict], options: dict,
                  think: bool | str, keep_alive: str) -> Iterator[LiveUpdate]:
    """Stream a reply and yield LiveUpdate objects; the last one carries exact `final` metrics."""
    start = time.perf_counter()
    first: float | None = None
    content, thinking, chunks = "", "", 0
    for ev in client.chat_stream(model, messages, options=options, think=think, keep_alive=keep_alive):
        now = time.perf_counter()
        if ev.kind in ("content", "thinking"):
            if first is None:
                first = now - start
            chunks += 1
            if ev.kind == "content":
                content += ev.text
            else:
                thinking += ev.text
            gen_time = max(now - start - (first or 0), 1e-6)
            yield LiveUpdate(content, thinking, chunks, now - start, first or 0.0,
                             chunks / gen_time if chunks > 1 else 0.0)
        elif ev.kind == "done":
            wall = now - start
            final = from_stats(ev.stats, ttft=first or wall, wall=wall)
            yield LiveUpdate(content, thinking, chunks, wall, first or wall, final.tokens_per_second, final)


def reasoning_share(thinking: str, content: str) -> float:
    """Fraction of streamed characters that belong to the reasoning trace (0..1)."""
    total = len(thinking) + len(content)
    return len(thinking) / total if total else 0.0
