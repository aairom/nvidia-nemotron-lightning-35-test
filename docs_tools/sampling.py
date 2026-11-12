"""Resource sampling for the documentation benchmark (macOS `ps` / `vm_stat`).

Pure parsers (testable) + a background sampler thread that records, every `interval` seconds:
  * cpu_pct   - summed %CPU of all processes whose command line contains "ollama"
  * rss_mb    - summed resident memory of those processes
  * wired_gb  - system-wide wired memory (on Apple silicon the MLX model weights live here)
"""
from __future__ import annotations

import re
import subprocess
import threading
import time
from dataclasses import dataclass, field


def parse_ps(text: str, needle: str = "ollama") -> tuple[float, float]:
    """Parse `ps -axo rss=,pcpu=,command=` output -> (summed rss in MB, summed %cpu)."""
    rss_kb, cpu = 0.0, 0.0
    for line in text.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3 or needle not in parts[2].lower():
            continue
        try:
            rss_kb += float(parts[0])
            cpu += float(parts[1])
        except ValueError:
            continue
    return rss_kb / 1024.0, cpu


def parse_vm_stat(text: str) -> dict[str, float]:
    """Parse `vm_stat` output -> {'wired_gb': ..., 'active_gb': ..., 'free_gb': ...}."""
    m = re.search(r"page size of (\d+) bytes", text)
    page = int(m.group(1)) if m else 4096

    def pages(label: str) -> float:
        mm = re.search(rf"{label}:\s+(\d+)\.", text)
        return int(mm.group(1)) * page / 1e9 if mm else 0.0

    return {"wired_gb": pages("Pages wired down"), "active_gb": pages("Pages active"),
            "free_gb": pages("Pages free")}


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout


def take_sample() -> dict[str, float]:
    rss_mb, cpu = parse_ps(_run(["ps", "-axo", "rss=,pcpu=,command="]))
    return {"cpu_pct": cpu, "rss_mb": rss_mb, **{k: v for k, v in parse_vm_stat(_run(["vm_stat"])).items()
                                                  if k == "wired_gb"}}


@dataclass
class Sampler:
    """Context manager that samples in a background thread. `sample_fn` is injectable for tests."""
    interval: float = 0.5
    sample_fn: object = take_sample
    samples: list[dict] = field(default_factory=list)
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    def __enter__(self) -> "Sampler":
        self._t0 = time.perf_counter()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                s = self.sample_fn()
            except Exception:  # sampling must never break a benchmark run
                s = None
            if s:
                self.samples.append({"t": round(time.perf_counter() - self._t0, 2), **s})
            self._stop.wait(self.interval)

    def __exit__(self, *exc) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def peak(self, key: str) -> float:
        return max((s[key] for s in self.samples if key in s), default=0.0)
