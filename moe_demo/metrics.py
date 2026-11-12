"""Inference metrics derived from Ollama's final streaming chunk plus client-side timing.

Ollama reports durations in nanoseconds. All values here are *measured*, not estimated.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

NS = 1_000_000_000.0


@dataclass
class RunMetrics:
    prompt_tokens: int = 0
    generated_tokens: int = 0          # includes reasoning ("thinking") tokens
    load_seconds: float = 0.0          # time spent loading the model into memory
    prompt_eval_seconds: float = 0.0
    generation_seconds: float = 0.0
    total_seconds: float = 0.0         # server-side total
    ttft_seconds: float = 0.0          # client-side time to first streamed token
    wall_seconds: float = 0.0          # client-side end-to-end

    @property
    def tokens_per_second(self) -> float:
        """Generation speed (decode phase)."""
        return self.generated_tokens / self.generation_seconds if self.generation_seconds > 0 else 0.0

    @property
    def prompt_tokens_per_second(self) -> float:
        return self.prompt_tokens / self.prompt_eval_seconds if self.prompt_eval_seconds > 0 else 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.generated_tokens

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tokens_per_second"] = round(self.tokens_per_second, 2)
        d["prompt_tokens_per_second"] = round(self.prompt_tokens_per_second, 2)
        d["total_tokens"] = self.total_tokens
        return d


def from_stats(stats: dict[str, Any], ttft: float = 0.0, wall: float = 0.0) -> RunMetrics:
    """Build RunMetrics from the `done` chunk of /api/chat."""
    return RunMetrics(
        prompt_tokens=int(stats.get("prompt_eval_count") or 0),
        generated_tokens=int(stats.get("eval_count") or 0),
        load_seconds=(stats.get("load_duration") or 0) / NS,
        prompt_eval_seconds=(stats.get("prompt_eval_duration") or 0) / NS,
        generation_seconds=(stats.get("eval_duration") or 0) / NS,
        total_seconds=(stats.get("total_duration") or 0) / NS,
        ttft_seconds=ttft,
        wall_seconds=wall,
    )


def active_fractions(total_params_b: float = 30.0, active_params_b: float = 3.0,
                     n_experts: int = 128, top_k: int = 6) -> dict[str, float]:
    """Sparsity facts from the published model card: share of weights / experts used per token."""
    return {
        "active_param_fraction": active_params_b / total_params_b,
        "active_expert_fraction": top_k / n_experts,
    }
