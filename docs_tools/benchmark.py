"""Run the documentation benchmark against the real local Ollama model.

Writes Docs/assets/data/benchmark.json. Uses the same engine code path as the GUI
(`moe_demo.engine.stream_answer`), so the numbers describe exactly what the app shows.

Usage:  .venv/bin/python -m docs_tools.benchmark [--quick]
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from moe_demo.categories import CATEGORIES
from moe_demo.config import ROOT, get_settings
from moe_demo.engine import build_messages, build_options, resolve_think, stream_answer
from moe_demo.ollama_client import OllamaClient

from .sampling import Sampler

OUT = ROOT / "Docs" / "assets" / "data" / "benchmark.json"
NUM_CTX, TOP_P, NUM_PREDICT = 8192, 0.95, 2048   # same defaults as the GUI sidebar


def run_case(client: OllamaClient, model: str, *, system: str, prompt: str, temperature: float,
             think: bool | str, keep_alive: str, num_predict: int = NUM_PREDICT,
             sampler_interval: float = 0.5) -> dict:
    """Execute one request, return the measured record (metrics + resource samples)."""
    opts = build_options(temperature, TOP_P, NUM_CTX, num_predict)
    msgs = build_messages(system, [], prompt, False)
    last = None
    with Sampler(interval=sampler_interval) as smp:
        for upd in stream_answer(client, model, msgs, opts, think, keep_alive):
            last = upd
    m = last.final
    return {
        "prompt_tokens": m.prompt_tokens, "generated_tokens": m.generated_tokens,
        "tps": round(m.tokens_per_second, 2), "prompt_tps": round(m.prompt_tokens_per_second, 2),
        "ttft_s": round(m.ttft_seconds, 3), "wall_s": round(m.wall_seconds, 3),
        "load_s": round(m.load_seconds, 3), "prompt_eval_s": round(m.prompt_eval_seconds, 3),
        "generation_s": round(m.generation_seconds, 3),
        "reasoning_chars": len(last.thinking), "answer_chars": len(last.content),
        "answered": bool(last.content), "think": think,
        "peak_cpu_pct": round(smp.peak("cpu_pct"), 1), "peak_rss_mb": round(smp.peak("rss_mb"), 1),
        "peak_wired_gb": round(smp.peak("wired_gb"), 2), "samples": smp.samples,
    }


def host_info(client: OllamaClient, model: str) -> dict:
    def sysctl(k: str) -> str:
        try:
            return subprocess.run(["sysctl", "-n", k], capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            return ""
    mem = sysctl("hw.memsize")
    loaded = client.loaded_info(model) or {}
    return {"os": platform.platform(), "machine": platform.machine(), "python": platform.python_version(),
            "cpu": sysctl("machdep.cpu.brand_string"), "ram_gb": round(int(mem) / 2**30) if mem.isdigit() else None,
            "ollama_version": client.version(), "model": model,
            "model_size_gb": round(loaded.get("size", 0) / 1e9, 2), "loaded_context": loaded.get("context_length"),
            "runner": loaded.get("runner")}


def prefill_prompt(words: int) -> str:
    """Synthetic prompt of ~`words` words with a unique nonce first so no prefix cache can be reused."""
    body = " ".join(f"item{i % 97} alpha beta gamma delta" for i in range(words // 5 + 1))
    return f"[{uuid.uuid4().hex}] Read the text and reply with the single word OK.\n\n{body}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="1 example per category, shorter sweep")
    args = ap.parse_args(argv)
    s = get_settings()
    client = OllamaClient(s.base_url, s.request_timeout)
    model = s.model
    log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731

    result: dict = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "settings": {"num_ctx": NUM_CTX, "top_p": TOP_P, "num_predict": NUM_PREDICT}}
    log("cold start: unloading model")
    client.unload(model)
    time.sleep(3)
    first = True
    runs = []
    for key, cat in CATEGORIES.items():
        for ex in (cat.examples[:1] if args.quick else cat.examples):
            log(f"run {key} / {ex.title}")
            rec = run_case(client, model, system=cat.system_prompt, prompt=ex.prompt,
                           temperature=cat.temperature, think=resolve_think("Auto (per category)", cat.think),
                           keep_alive=s.keep_alive)
            rec.update(category=key, title=ex.title, temperature=cat.temperature, cold=first)
            first = False
            runs.append(rec)
            log(f"   {rec['tps']} tok/s, {rec['generated_tokens']} tok, ttft {rec['ttft_s']}s, answered={rec['answered']}")
    result["runs"] = runs
    result["host"] = host_info(client, model)

    log("reasoning on/off comparison")
    cmp_runs = []
    rcat = CATEGORIES["reasoning"]
    for ex in (rcat.examples[:1] if args.quick else rcat.examples):
        rec = run_case(client, model, system=rcat.system_prompt, prompt=ex.prompt,
                       temperature=rcat.temperature, think=False, keep_alive=s.keep_alive)
        rec.update(category="reasoning", title=ex.title, temperature=rcat.temperature, cold=False)
        cmp_runs.append(rec)
        log(f"   think=off {ex.title}: {rec['tps']} tok/s, {rec['generated_tokens']} tok")
    result["reasoning_off"] = cmp_runs

    log("prefill sweep")
    sweep = []
    for words in ((200, 1500) if args.quick else (200, 800, 2000, 4000)):
        rec = run_case(client, model, system="", prompt=prefill_prompt(words), temperature=0.0,
                       think=False, keep_alive=s.keep_alive, num_predict=8)
        sweep.append({"words": words, **{k: rec[k] for k in ("prompt_tokens", "prompt_eval_s", "prompt_tps", "ttft_s", "wall_s")}})
        log(f"   {words} words -> {rec['prompt_tokens']} tok @ {rec['prompt_tps']} tok/s")
    result["prefill_sweep"] = sweep

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")
    log(f"written {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
