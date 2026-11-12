"""Deterministic *simulation* of top-k expert routing, for visualisation only.

Why a simulation?  Ollama gives no access to the router's per-token decisions. To still let users
*see* the idea of sparse routing we mimic it:

* 128 routed experts (as in the published Nemotron 3.5 Lightning card), 6 chosen per token.
* The experts are arranged in 8 groups of 16 (see `categories.EXPERT_GROUPS`).
* Each token gets a score for every expert = category affinity of the expert's group
  + a deterministic pseudo-random "token-specific" component (hash of token and expert id).
  The top-k scores win. That mimics a learned router: a soft preference for the right
  specialists, but with token-level variety, so several groups are used per category.

The result is reproducible (same prompt -> same picture) and is NOT telemetry from the model.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .categories import CATEGORIES, EXPERT_GROUPS

N_EXPERTS = 128
TOP_K = 6
GROUP_SIZE = N_EXPERTS // len(EXPERT_GROUPS)  # 16
AFFINITY_STRENGTH = 0.5   # how strongly category affinity biases the router vs. token noise
MAX_TOKENS = 200          # cap simulated tokens so very long prompts stay cheap


@dataclass
class RoutingResult:
    category: str
    n_tokens: int
    expert_counts: list[int]            # length 128: how many tokens selected each expert
    group_share: dict[str, float]       # group -> share of all expert selections (sums to 1)
    top_experts: list[tuple[int, int]]  # (expert id, count), most used first


def group_of(expert_id: int) -> int:
    return expert_id // GROUP_SIZE


def _noise(token: str, expert_id: int) -> float:
    """Deterministic pseudo-random value in [0, 1) for a (token, expert) pair."""
    digest = hashlib.blake2b(f"{token}|{expert_id}".encode(), digest_size=4).digest()
    return int.from_bytes(digest, "big") / 2**32


def tokenize(text: str) -> list[str]:
    """Cheap word/punctuation tokenizer; only used to size the simulation."""
    return re.findall(r"\w+|[^\w\s]", text.lower())[:MAX_TOKENS]


def route_token(token: str, category_key: str) -> list[int]:
    """Return the TOP_K expert ids chosen for one token under the given category."""
    affinity = CATEGORIES[category_key].expert_affinity
    scores = []
    for e in range(N_EXPERTS):
        group_name = EXPERT_GROUPS[group_of(e)]
        scores.append((AFFINITY_STRENGTH * affinity.get(group_name, 0.0) + _noise(token, e), e))
    scores.sort(reverse=True)
    return [e for _, e in scores[:TOP_K]]


def simulate(text: str, category_key: str) -> RoutingResult:
    """Simulate routing of every token of `text` and aggregate the selections."""
    if category_key not in CATEGORIES:
        raise ValueError(f"unknown category: {category_key}")
    tokens = tokenize(text) or ["<empty>"]
    counts = [0] * N_EXPERTS
    for tok in tokens:
        for e in route_token(tok, category_key):
            counts[e] += 1
    total = sum(counts)
    group_totals = [0] * len(EXPERT_GROUPS)
    for e, c in enumerate(counts):
        group_totals[group_of(e)] += c
    share = {EXPERT_GROUPS[i]: group_totals[i] / total for i in range(len(EXPERT_GROUPS))}
    top = sorted(((e, c) for e, c in enumerate(counts) if c), key=lambda x: (-x[1], x[0]))[:10]
    return RoutingResult(category_key, len(tokens), counts, share, top)
