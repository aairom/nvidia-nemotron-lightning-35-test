"""Data access for the documentation build: everything shown in the HTML is read from here.

Nothing is typed in by hand that can be derived: line counts come from the source files, code
listings from `inspect`, test counts from the AST of the test modules, benchmark numbers from
`Docs/assets/data/benchmark.json`, simulated routing shares from `moe_demo.router_sim`.
"""
from __future__ import annotations

import ast
import base64
import inspect
import io
import json
from functools import lru_cache
from pathlib import Path
from statistics import mean

from moe_demo import categories, config, router_sim
from moe_demo.categories import CATEGORIES, EXPERT_GROUPS

ROOT = config.ROOT
DOCS = ROOT / "Docs"
ASSETS = DOCS / "assets"
SHOTS = ASSETS / "screenshots"
DATA = ASSETS / "data"

SOURCE_FILES = ["app.py"] + [f"moe_demo/{n}.py" for n in
                             ("__init__", "categories", "config", "engine", "help_text", "metrics",
                              "ollama_client", "router_sim", "ui_components")]
DOCS_TOOLS_FILES = [f"docs_tools/{n}.py" for n in
                    ("__init__", "sampling", "benchmark", "charts", "theme", "data", "context",
                     "chapters_core", "chapters_ops", "build_docs")]


# ----------------------------------------------------------------------------- files
def read_text(rel: str | Path, default: str = "") -> str:
    p = Path(rel) if Path(rel).is_absolute() else ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else default


def line_count(rel: str) -> int:
    p = ROOT / rel
    return len(p.read_text(encoding="utf-8").splitlines()) if p.exists() else 0


def source_stats(files: list[str] | None = None) -> dict[str, int]:
    return {f: line_count(f) for f in (files or SOURCE_FILES)}


@lru_cache(maxsize=None)
def image_data_uri(path: str, max_width: int = 1500) -> str:
    """Return a data: URI (JPEG, resized) so the HTML stays a single shareable file.

    The full-resolution PNG remains in Docs/assets/screenshots/."""
    from PIL import Image
    img = Image.open(path).convert("RGB")
    if img.width > max_width:
        img = img.resize((max_width, round(img.height * max_width / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=86, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def shot_path(name: str) -> Path:
    return SHOTS / name


# ----------------------------------------------------------------------------- code snippets
def source_of(obj) -> str:
    """Exact source text of a function/class, dedented as in the file."""
    return inspect.getsource(obj).rstrip("\n")


def snippet(rel: str, start_marker: str, end_marker: str | None = None, max_lines: int = 40) -> str:
    """Lines of `rel` from the first line containing `start_marker` up to (excluding) `end_marker`."""
    lines = read_text(rel).splitlines()
    try:
        a = next(i for i, ln in enumerate(lines) if start_marker in ln)
    except StopIteration as exc:  # pragma: no cover - guards against drift between code and docs
        raise KeyError(f"{start_marker!r} not found in {rel}") from exc
    b = len(lines)
    if end_marker:
        b = next((i for i in range(a + 1, len(lines)) if end_marker in lines[i]), len(lines))
    return "\n".join(lines[a:min(b, a + max_lines)]).rstrip()


# ----------------------------------------------------------------------------- tests
def count_tests(tests_dir: Path | None = None) -> dict[str, int]:
    """module -> number of test functions/methods (AST count, no execution)."""
    out: dict[str, int] = {}
    for p in sorted((tests_dir or ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        out[p.name] = sum(1 for n in ast.walk(tree)
                          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"))
    return out


# ----------------------------------------------------------------------------- benchmark
def load_benchmark(path: Path | None = None) -> dict:
    return json.loads((path or DATA / "benchmark.json").read_text(encoding="utf-8"))


def per_category(bench: dict) -> dict[str, dict[str, float]]:
    """Mean measured values per category over the benchmark runs (excluding the cold first run
    for latency-type metrics, because its TTFT is dominated by loading the model)."""
    out: dict[str, dict[str, float]] = {}
    for key in CATEGORIES:
        runs = [r for r in bench["runs"] if r["category"] == key]
        warm = [r for r in runs if not r.get("cold")] or runs
        out[key] = {"n": len(runs), "tps": mean(r["tps"] for r in runs),
                    "ttft": mean(r["ttft_s"] for r in warm), "gen": mean(r["generated_tokens"] for r in runs),
                    "wall": mean(r["wall_s"] for r in runs)}
    return out


def headline(bench: dict) -> dict[str, float]:
    runs = bench["runs"]
    cold = next((r for r in runs if r.get("cold")), runs[0])
    warm = [r for r in runs if not r.get("cold")]
    tps = [r["tps"] for r in runs]
    return {"runs": len(runs), "tps_mean": mean(tps), "tps_min": min(tps), "tps_max": max(tps),
            "ttft_warm_mean": mean(r["ttft_s"] for r in warm), "cold_ttft": cold["ttft_s"],
            "cold_load": cold["load_s"], "peak_cpu": max(r["peak_cpu_pct"] for r in runs),
            "peak_wired": max(r["peak_wired_gb"] for r in runs),
            "gen_total": sum(r["generated_tokens"] for r in runs)}


# ----------------------------------------------------------------------------- simulated routing
def affinity_matrix() -> tuple[list[str], list[str], list[list[float]]]:
    """rows = expert groups, cols = categories, values = configured affinity (0..1)."""
    cols = list(CATEGORIES)
    data = [[CATEGORIES[c].expert_affinity.get(g, 0.0) for c in cols] for g in EXPERT_GROUPS]
    return EXPERT_GROUPS, [CATEGORIES[c].name for c in cols], data


def simulated_shares() -> dict[str, dict[str, float]]:
    """Group shares the app shows for the first example of each category."""
    return {k: router_sim.simulate(c.examples[0].prompt, k).group_share for k, c in CATEGORIES.items()}


def strength_sweep(strengths=(0.0, 0.25, 0.5, 1.0, 1.6)) -> list[tuple[float, float, float]]:
    """For each AFFINITY_STRENGTH: (strength, mean top-group share, mean top-2 share) over the
    first example of every category. The module constant is restored afterwards."""
    original = router_sim.AFFINITY_STRENGTH
    rows = []
    try:
        for st in strengths:
            router_sim.AFFINITY_STRENGTH = st
            sh = simulated_shares()
            rows.append((st, mean(max(v.values()) for v in sh.values()), mean(concentration(v) for v in sh.values())))
    finally:
        router_sim.AFFINITY_STRENGTH = original
    return rows


def classifier_accuracy() -> list[tuple[str, str, str]]:
    """(category, example title, predicted category) for every pre-loaded example."""
    return [(k, ex.title, categories.classify(ex.prompt)[0]) for k, c in CATEGORIES.items() for ex in c.examples]


def concentration(shares: dict[str, float]) -> float:
    """Share of the top-2 groups: a simple 'how specialised is this profile' number."""
    return sum(sorted(shares.values(), reverse=True)[:2])



_TREE_SKIP = {".venv", "__pycache__", "node_modules", ".git", ".run", ".pytest_cache", ".coverage", "output", "input",
              ".playwright-mcp", ".bob", "screenshots", "AGENTS.md", ".env"}


def project_tree(root: Path | None = None, max_depth: int = 2) -> str:
    """Text tree of the project (hidden/ignored folders skipped), for the architecture chapter."""
    base = root or ROOT
    lines = [base.name + "/"]

    def walk(d: Path, prefix: str, depth: int) -> None:
        entries = sorted((p for p in d.iterdir() if p.name not in _TREE_SKIP and not p.name.startswith("_")
                          and not p.name.endswith((".pyc", ".html"))),
                         key=lambda p: (p.is_file(), p.name.lower()))
        for i, p in enumerate(entries):
            last = i == len(entries) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{p.name}{'/' if p.is_dir() else ''}")
            if p.is_dir() and depth < max_depth:
                walk(p, prefix + ("    " if last else "│   "), depth + 1)

    walk(base, "", 1)
    return "\n".join(lines)
