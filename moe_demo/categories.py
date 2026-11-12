"""Task categories, example prompts and the (heuristic) category classifier.

IMPORTANT - what is real and what is illustrative
-------------------------------------------------
Ollama does NOT expose the MoE router's per-token expert choices, so no application on top of
Ollama can read "expert #17 fired". What this module provides is an *educational model*:

* `expert_affinity` - the expert *groups* that research on MoE models suggests are most
  involved in this kind of work (expert specialisation is soft and mostly syntactic/lexical,
  not neatly "one expert = one subject"). These weights are an illustration, not telemetry.
* `classify()` - a keyword heuristic that guesses which category a free-text prompt belongs to,
  so custom queries also get an explanation panel.

Everything that is measured (tokens/s, latency, token counts, load state, share of reasoning
tokens) comes from Ollama and is real.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Eight conceptual expert groups. The real model has 128 routed experts per MoE layer
# (6 active per token); we map them to 8 groups of 16 purely for visualisation.
EXPERT_GROUPS: list[str] = [
    "Code & syntax",
    "Math & formal logic",
    "Narrative & style",
    "World knowledge & facts",
    "Language & grammar",
    "Salience & compression",
    "Structure & formatting",
    "Instruction & dialogue",
]


@dataclass(frozen=True)
class Example:
    title: str
    prompt: str


@dataclass(frozen=True)
class Category:
    key: str
    name: str
    icon: str
    blurb: str
    why: str                                  # explanation shown in the expert panel
    expert_affinity: dict[str, float]         # group name -> relative weight (0..1), illustrative
    keywords: tuple[str, ...]
    temperature: float                        # suggested sampling temperature
    think: str                                # suggested reasoning mode: "off" | "on" | "medium"
    system_prompt: str
    examples: tuple[Example, ...] = field(default_factory=tuple)


CATEGORIES: dict[str, Category] = {
    "creative": Category(
        key="creative",
        name="Creative writing",
        icon="✍️",
        blurb="Stories, poems, marketing copy: open-ended generation where style matters.",
        why=(
            "Open-ended generation leans on experts that handle tone, rhythm and vocabulary "
            "variety. A higher temperature lets the router and sampler explore more diverse "
            "token paths, so different runs reach different expert combinations."
        ),
        expert_affinity={"Narrative & style": 1.0, "Language & grammar": 0.8,
                         "Instruction & dialogue": 0.5, "World knowledge & facts": 0.3,
                         "Structure & formatting": 0.3},
        keywords=("story", "poem", "write a", "haiku", "lyrics", "narrative", "character",
                  "fiction", "slogan", "tagline", "imagine", "creative", "metaphor", "novel"),
        temperature=1.0,
        think="off",
        system_prompt="You are a vivid, original writer. Keep answers under 250 words.",
        examples=(
            Example("Haiku about sparse computing",
                    "Write three haiku about a city where only a few lights switch on at a time, "
                    "as a metaphor for sparse neural networks."),
            Example("Micro-story",
                    "Write a 150-word science-fiction micro-story about a librarian who discovers "
                    "that every book secretly has a specialist author living inside it."),
            Example("Product tagline",
                    "Give me 5 playful taglines for a coffee shop run entirely by a team of "
                    "specialist robots."),
        ),
    ),
    "coding": Category(
        key="coding",
        name="Coding & technical",
        icon="💻",
        blurb="Write, debug and explain code; precise syntax and API knowledge.",
        why=(
            "Code has rigid syntax and long-range structure (brackets, indentation, types). "
            "MoE models tend to route code tokens to experts that specialise in symbols and "
            "formal structure, with low temperature keeping the choice stable."
        ),
        expert_affinity={"Code & syntax": 1.0, "Structure & formatting": 0.8,
                         "Math & formal logic": 0.6, "Instruction & dialogue": 0.4},
        keywords=("code", "python", "function", "bug", "debug", "java", "javascript", "sql",
                  "regex", "algorithm", "class ", "compile", "api", "script", "refactor",
                  "stack trace", "def ", "return"),
        temperature=0.2,
        think="off",
        system_prompt="You are a senior software engineer. Reply with concise, correct code and a short explanation.",
        examples=(
            Example("Write a function",
                    "Write a Python function `merge_intervals(intervals)` that merges overlapping "
                    "intervals. Include type hints and two doctests."),
            Example("Find the bug",
                    "Find and fix the bug:\n```python\ndef avg(xs):\n    total = 0\n    for x in xs:\n"
                    "        total += x\n    return total / len(xs) + 1\n```\nAlso make it safe for an empty list."),
            Example("SQL query",
                    "Write a SQL query that returns the top 3 customers by total order value per "
                    "country from tables customers(id, name, country) and orders(id, customer_id, amount)."),
        ),
    ),
    "factual": Category(
        key="factual",
        name="Factual Q&A",
        icon="📚",
        blurb="Retrieve and state well-known facts accurately and briefly.",
        why=(
            "Factual recall relies on the knowledge stored in the experts' feed-forward weights. "
            "Only a few experts need to fire per token, which is why a 30B-parameter model "
            "answers with the compute cost of ~3B parameters."
        ),
        expert_affinity={"World knowledge & facts": 1.0, "Language & grammar": 0.6,
                         "Instruction & dialogue": 0.5, "Salience & compression": 0.3},
        keywords=("who ", "what is", "what are", "when did", "where is", "capital of", "define",
                  "history of", "how many", "which country", "explain what", "founded", "invented"),
        temperature=0.2,
        think="off",
        system_prompt="You are a precise encyclopedia. Answer factually and briefly; say so if unsure.",
        examples=(
            Example("Science fact",
                    "What is the difference between nuclear fission and nuclear fusion? Answer in 4 sentences."),
            Example("History",
                    "Who was Ada Lovelace and why is she considered an early computing pioneer?"),
            Example("Geography",
                    "What is the longest river in Europe, which countries does it flow through, and where does it end?"),
        ),
    ),
    "reasoning": Category(
        key="reasoning",
        name="Analytical reasoning",
        icon="🧠",
        blurb="Multi-step logic, math word problems, trade-off analysis.",
        why=(
            "Multi-step reasoning chains benefit from experts handling arithmetic and formal "
            "logic, and from the model's optional reasoning trace (\"thinking\"). The metrics "
            "panel shows how many generated tokens went into that trace."
        ),
        expert_affinity={"Math & formal logic": 1.0, "Instruction & dialogue": 0.5,
                         "Language & grammar": 0.5, "Structure & formatting": 0.4,
                         "World knowledge & facts": 0.4},
        keywords=("why", "reason", "prove", "calculate", "puzzle", "riddle", "logic", "compare",
                  "trade-off", "pros and cons", "analyze", "analyse", "probability", "how many",
                  "if ", "deduce", "step by step", "solve", "explain your reasoning", "catch up",
                  "km/h", "recommendation", "memory, speed"),
        temperature=0.4,
        think="medium",
        system_prompt="You are a careful analyst. Work step by step and state your final answer clearly.",
        examples=(
            Example("Logic puzzle",
                    "Alice, Bob and Carol each own a different pet: cat, dog, parrot. Alice is allergic "
                    "to fur. Bob's pet can talk. Who owns which pet? Explain your reasoning."),
            Example("Math word problem",
                    "A train leaves at 09:00 at 80 km/h. A second train leaves the same station at "
                    "10:00 at 120 km/h on the same track. At what time does the second catch up?"),
            Example("Trade-off analysis",
                    "Compare a dense 30B model with a sparse MoE 30B-A3B model for a laptop deployment: "
                    "memory, speed and quality. Give a recommendation."),
        ),
    ),
    "summarization": Category(
        key="summarization",
        name="Summarization",
        icon="🗜️",
        blurb="Condense long text into the essentials.",
        why=(
            "Summarising needs salience detection (what matters) and faithful compression. The "
            "input is long, so prompt-processing speed (prefill) dominates and the hybrid "
            "Mamba-2 layers keep long inputs cheap compared with pure attention."
        ),
        expert_affinity={"Salience & compression": 1.0, "Language & grammar": 0.7,
                         "Structure & formatting": 0.6, "World knowledge & facts": 0.4,
                         "Instruction & dialogue": 0.4},
        keywords=("summarize", "summarise", "summary", "tl;dr", "tldr", "condense", "shorten",
                  "key points", "in one sentence", "abstract", "bullet points"),
        temperature=0.3,
        think="off",
        system_prompt="You are an expert editor. Be faithful to the source; add nothing that is not in it.",
        examples=(
            Example("3-bullet summary",
                    "Summarize in exactly 3 bullet points:\n\nMixture-of-experts (MoE) models replace the "
                    "dense feed-forward block of a transformer with many smaller expert networks and a "
                    "learned router. For each token, the router scores all experts and sends the token only "
                    "to the top few. Because only a fraction of the parameters are used per token, the model "
                    "can store far more knowledge than a dense model of the same compute cost. The trade-off "
                    "is memory: all experts must be resident even though few are active, and training needs "
                    "load-balancing so that experts are used evenly and none collapses."),
            Example("One-sentence TL;DR",
                    "Give a one-sentence TL;DR:\n\nThe city council voted 7-2 on Tuesday to extend the "
                    "tram line by four kilometres to the northern suburbs. Construction will begin next "
                    "spring, cost an estimated 120 million euros, and is expected to cut commute times by "
                    "about 15 minutes. Opponents raised concerns about noise and the loss of a small park; "
                    "the council promised to replant twice as many trees nearby."),
            Example("Meeting notes",
                    "Condense these notes into Decisions and Action items:\n\nWe discussed the launch date. "
                    "Priya thinks March is too early because QA is understaffed. Marco proposed hiring two "
                    "contractors. Everyone agreed to move the launch to April. Priya will post the contractor "
                    "job ad by Friday. Marco will update the roadmap. Dana will tell the customers."),
        ),
    ),
}


def classify(prompt: str) -> tuple[str, dict[str, int]]:
    """Guess the category of a free-text prompt with a transparent keyword score.

    Returns (category_key, scores). Falls back to 'factual' when nothing matches,
    since it is the most generic Q&A shape.
    """
    text = prompt.lower()
    scores = {k: 0 for k in CATEGORIES}
    for key, cat in CATEGORIES.items():
        for kw in cat.keywords:
            if kw in text:
                scores[key] += 1
    # Structural hints: code fences / long pasted text are strong signals.
    if "```" in prompt or re.search(r"\b(def|class|function|SELECT|import)\b", prompt):
        scores["coding"] += 2
    if len(prompt) > 600:
        scores["summarization"] += 1
    best = max(scores, key=lambda k: scores[k])
    return (best if scores[best] > 0 else "factual"), scores
