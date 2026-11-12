"""Chapters 5-8: testing, deployment, performance, troubleshooting.

Performance numbers are read from Docs/assets/data/benchmark.json (a real run through moe_demo.engine);
terminal output is read from Docs/assets/data/*.txt (verbatim captures). Nothing is invented here.
"""
from __future__ import annotations

from statistics import mean

from moe_demo.categories import CATEGORIES

from . import charts, data, theme
from .context import Ctx, Raw, code_inline, grid2, kpis, table

C = code_inline

# Runs read from the GUI screenshots (Chapter 2); the sidebar/metric cards are the source.
GUI_RUNS = [
    ("Write a function (coding)", 60, 294, 41.9, 0.10, 7.09, "03_conversation / 02_coding_run"),
    ("Micro-story (creative)", 395, 227, 42.2, 0.97, 6.28, "03_conversation (badge)"),
    ("Logic puzzle (reasoning), 3rd turn", 681, 2048, 60.3, 1.33, 35.18, "03_conversation / 07_compare"),
    ("Logic puzzle (reasoning), fresh session", 79, 2048, 102.7, 0.23, 20.12, "06_reasoning_trace_limit"),
]


# =============================================================================================== 5
def chapter5(ctx: Ctx) -> str:
    ctx.start(5)
    inv = data.count_tests()
    total = sum(inv.values())
    out = [ctx.head(5, "How correctness is established: unit tests against a stub Ollama server, a headless GUI smoke test, "
                       "a live end-to-end run against the real model, and the repository's policy gates.")]
    out.append(kpis([(str(total), "automated tests"), (str(len(inv)), "test modules"), ("0", "tests needing the real model"),
                     ("15 / 15", "pre-loaded examples run live")]))

    out.append(ctx.h3("strategy", "Test strategy"))
    out.append(table(["Layer", "What is tested", "How", "Needs Ollama?"], [
        ["Pure logic", "options, think mapping, messages, metrics, classifier, router simulation", "unittest/pytest, no I/O", "no"],
        ["HTTP client", "status calls, streaming, thinking events, HTTP errors, refused connection, error mid-stream", "in-process stub server (<code>tests/stub_ollama.py</code>)", "no"],
        ["Engine", "stream_answer against the stub, including final metrics", "stub server", "no"],
        ["GUI", "script runs offline without exception; example click and free text produce chat turns", "Streamlit <code>AppTest</code> + stub", "no"],
        ["Docs tooling", "parsers, chart helpers, figure kinds, link integrity of this document", "unit tests with fixtures", "no"],
        ["End to end", "all 15 examples, timing and resource capture", "<code>docs_tools.benchmark</code> on the real model", "yes (manual)"]]))

    out.append(ctx.h3("stub", "Stub Ollama server"))
    out.append("<p>Tests never download or run a 19 GB model. <code>tests/stub_ollama.py</code> is a ~70-line HTTP server that speaks "
               "just enough of the Ollama API (<code>/api/version</code>, <code>tags</code>, <code>ps</code>, <code>generate</code>, "
               "<code>chat</code> with NDJSON streaming, thinking chunks, errors and mid-stream failure), so the real client and engine code is exercised end to end.</p>")
    out.append(theme.code(data.snippet("tests/stub_ollama.py", 'if self.path == "/api/chat"', "return self._send(404", 22), "tests/stub_ollama.py: scripted streaming reply"))

    out.append(ctx.h3("inventory", "Test inventory"))
    out.append(ctx.fig("chart", "fig-test-counts", "Number of tests per module (counted from the AST of tests/test_*.py).",
                       charts.bar_chart([n.replace("test_", "").replace(".py", "") for n in inv], list(inv.values()),
                                        title=f"{total} tests in {len(inv)} modules", width=900)))
    out.append(table(["Module", "Tests", "Covers"], [[C(n), c, C(n.replace("test_", "").replace(".py", ""))] for n, c in inv.items()], num_cols=(1,)))

    out.append(ctx.h3("run", "Test run and coverage"))
    out.append(ctx.fig("term", "fig-pytest", "pytest -v with coverage, captured verbatim (all tests PASSED).", theme.term_block("pytest -v --cov", ctx.evidence("pytest_cov.txt"))))
    out.append("<p>Coverage is highest where the logic is: the engine, configuration, metrics, router simulation and UI components are at 100 %. "
               "The uncovered lines in <code>app.py</code> are the model Load/Unload buttons, the long-prompt branch and defensive error paths that need a real server in a particular state.</p>")

    out.append(ctx.h3("live", "Live end-to-end verification"))
    b = data.load_benchmark()
    rows = [[CATEGORIES[r["category"]].name, r["title"], "yes" if r["answered"] else "no (budget spent thinking)", f"{r['tps']:.1f}", r["generated_tokens"]]
            for r in b["runs"]]
    answered = sum(1 for r in b["runs"] if r["answered"])
    out.append(f"<p>All {len(b['runs'])} pre-loaded examples were executed against the real model through the same code path as the GUI "
               f"({C('moe_demo.engine.stream_answer')}). {answered} of {len(b['runs'])} produced an answer within the default 2048-token budget; "
               "the remaining one is the Logic puzzle with reasoning on, where the model keeps thinking (see "
               f"{ctx.xref('fig-limit')}). This is the application working as designed, not a defect.</p>")
    out.append(table(["Category", "Example", "Answered", "tok/s", "Generated"], rows, num_cols=(3, 4)))

    out.append(ctx.h3("gates", "Policy gates"))
    out.append(ctx.fig("term", "fig-gate", "test-gate: runs every detected test suite and flags code modules without a test file.", theme.term_block("test-gate", ctx.evidence("gate.txt"))))
    out.append(ctx.fig("term", "fig-audit", "project-audit: README, Docs, .gitignore, secrets, executable scripts and container policy.", theme.term_block("project-audit", ctx.evidence("audit.txt"))))
    out.append(ctx.fig("term", "fig-secrets", "Secret scan and git-hygiene check.", theme.term_block("secrets + git-hygiene", ctx.evidence("secrets.txt") + "\n" + ctx.evidence("git_hygiene.txt"))))
    return "\n".join(out)


# =============================================================================================== 6
def chapter6(ctx: Ctx) -> str:
    ctx.start(6)
    out = [ctx.head(6, "From a clean checkout to a running GUI: prerequisites, installation, configuration, start/stop scripts and daily use.")]
    out.append(ctx.h3("prereq", "Prerequisites"))
    out.append(table(["Requirement", "Version used here", "Notes"], [
        ["macOS on Apple silicon", "macOS 27.2.1, Apple M4 Max, 36 GB", "The MLX build of the model needs Apple silicon; ≥ 24 GB unified memory recommended (22–23 GB resident)"],
        ["Ollama", "0.40.16", "Model requires ≥ 0.40.5 (<code>ollama show</code>)"],
        ["Model", "nemotron-3.5-lightning:30b-a3b-mlx", "~19 GB download, nvfp4 quantisation"],
        ["Python", "3.13.9", "Virtual environment in <code>.venv</code>, managed with <code>uv</code>"],
        ["Browser", "any modern browser", "The GUI is served on localhost only"]]))

    out.append(ctx.h3("install", "Installation"))
    steps = ("# 1. Pull the model once (~19 GB)\nollama pull nemotron-3.5-lightning:30b-a3b-mlx\n\n"
             "# 2. Create the virtual environment (uv) and install dependencies\nbash .bob/skills/python-env/scripts/setup_env.sh .\n\n"
             "# 3. Configuration (already provided as a template)\ncp .env.example .env\n\n"
             "# 4. Start (detached) - prints the URL\nscripts/start.sh\n\n"
             "# 5. Open http://localhost:8501\n# 6. Stop\nscripts/stop.sh")
    out.append(theme.code(steps, "shell", lang="sh"))
    out.append(ctx.fig("term", "fig-startstop", "scripts/start.sh, health check and scripts/stop.sh, captured from a real run.", theme.term_block("start / health / stop", ctx.evidence("start_stop.txt"))))

    out.append(ctx.h3("config", "Configuration (.env)"))
    out.append("<p>No URL, model name or timeout is hard-coded in the application; everything comes from <code>.env</code> "
               "(ignored by git) with <code>.env.example</code> as the documented template.</p>")
    out.append(ctx.fig("term", "fig-env", ".env.example, the committed template.", theme.term_block(".env.example", ctx.evidence("env_example.txt"))))
    out.append(table(["Variable", "Default", "Effect"], [
        [C("APP_START_CMD"), "streamlit run app.py --server.port 8501 …", "Command used by <code>scripts/start.sh</code> (must stay quoted)"],
        [C("APP_HOST / APP_PORT"), "localhost / 8501", "URL printed by the script; port 5000 is refused on macOS (AirDrop)"],
        [C("OLLAMA_BASE_URL"), "http://localhost:11434", "Where Ollama listens"],
        [C("OLLAMA_MODEL"), "nemotron-3.5-lightning:30b-a3b-mlx", "Model preselected in the sidebar"],
        [C("OLLAMA_KEEP_ALIVE"), "15m", "How long the model stays resident after a request"],
        [C("OLLAMA_TIMEOUT"), "600", "Read timeout in seconds; must cover a cold ~19 GB load"]]))

    out.append(ctx.h3("scripts", "Lifecycle scripts"))
    out.append(table(["Script", "Purpose", "Behaviour"], [
        [C("scripts/start.sh"), "Start the GUI", "Loads .env, refuses port 5000 on macOS, starts detached, writes pid and log under <code>.run/</code>, prints URL"],
        [C("scripts/stop.sh"), "Stop it", "Graceful shutdown using the pid file"],
        [C("scripts/cleanup.sh"), "Remove generated folders", "Deletes node_modules, .venv, __pycache__"]]))

    out.append(ctx.h3("usage", "Using the application"))
    out.append("<ol><li>Open the URL and confirm the green <b>Ollama online</b> banner (" + ctx.xref("fig-home") + ").</li>"
               "<li>Click <b>Load now</b> once if the model is not resident; the first request otherwise takes about a minute (" + ctx.xref("s7-cold") + ").</li>"
               "<li>Click any pre-loaded example, or type a question into the chat box.</li>"
               "<li>Read the metric cards and the expert panel while the answer streams (" + ctx.xref("fig-live") + ").</li>"
               "<li>Change temperature, top-p, context window, max tokens or reasoning mode and send the next message; no restart is needed.</li>"
               "<li>Open <b>Compare tasks</b> to put routing profiles and measured speeds side by side (" + ctx.xref("fig-compare") + ").</li></ol>")
    out.append(ctx.h3("regen", "Regenerating this document"))
    out.append(theme.code("# measure again on your own machine (needs the model; ~5 minutes)\n.venv/bin/python -m docs_tools.benchmark\n\n"
                          "# rebuild the HTML from the data and screenshots\n.venv/bin/python -m docs_tools.build_docs\n", "shell", lang="sh"))
    out.append(theme.callout("note", "Screenshots", "<p>Screenshots are captures of the running GUI and are not regenerated by the build; "
                             "replace the files in <code>Docs/assets/screenshots/</code> after UI changes. Pin positions are percentages of the image.</p>"))
    return "\n".join(out)


# =============================================================================================== 7
def _series(run: dict, key: str) -> tuple[list[float], list[float]]:
    return [s["t"] for s in run["samples"] if key in s], [s[key] for s in run["samples"] if key in s]


def chapter7(ctx: Ctx) -> str:
    ctx.start(7)
    b = data.load_benchmark()
    h = data.headline(b)
    host = b["host"]
    runs = b["runs"]
    out = [ctx.head(7, "Measured on this machine with the real model: speed, latency, load and prefill behaviour, resource use and the effect of reasoning mode.")]
    out.append(theme.callout("ok", "Provenance",
                             f"<p>Captured {b['generated_at']} with <code>python -m docs_tools.benchmark</code> through the application's own engine. "
                             f"Host: {host['cpu']}, {host['ram_gb']} GB, {host['os']}, Python {host['python']}, Ollama {host['ollama_version']} "
                             f"({host['runner']} runner), context {host['loaded_context']}, top-p {b['settings']['top_p']}, max new tokens {b['settings']['num_predict']}. "
                             "Raw data: <code>Docs/assets/data/benchmark.json</code> (including every 0.5 s resource sample).</p>"))
    out.append(kpis([(f"{h['tps_mean']:.1f}", "mean tok/s (15 runs)"), (f"{h['tps_min']:.0f}–{h['tps_max']:.0f}", "tok/s range"),
                     (f"{h['ttft_warm_mean']:.2f} s", "warm time to first token"), (f"{h['cold_ttft']:.0f} s", "cold first token"),
                     (f"{h['cold_load']:.0f} s", "model load"), (f"{host['model_size_gb']:.1f} GB", "model in memory")]))

    out.append(ctx.h3("speed", "Generation speed per example"))
    labels = [f"{CATEGORIES[r['category']].icon} {r['title']}".replace("Haiku about sparse computing", "Haiku") for r in runs]
    cols = [f"var(--c{list(CATEGORIES).index(r['category'])})" for r in runs]
    out.append(ctx.fig("chart", "fig-tps", "Decode speed (tokens/s) of every example, coloured by task type.",
                       charts.bar_chart([r["title"][:20] for r in runs], [r["tps"] for r in runs], title="Tokens per second by example",
                                        colors=cols, width=980, height=350)))
    out.append(table(["Task type", "Example", "tok/s", "Generated", "TTFT (s)", "Wall (s)"],
                     [[CATEGORIES[r["category"]].name, r["title"] + (" (cold)" if r.get("cold") else ""), f"{r['tps']:.1f}", r["generated_tokens"],
                       f"{r['ttft_s']:.2f}", f"{r['wall_s']:.1f}"] for r in runs], num_cols=(2, 3, 4, 5)))

    out.append(ctx.h3("cold", "Cold start versus warm"))
    cold = next(r for r in runs if r.get("cold"))
    out.append(f"<p>The first request had to load the model: {cold['load_s']:.1f} s of loading plus {cold['prompt_eval_s']:.1f} s of prompt processing "
               f"(it also touches every weight once), so the first token arrived after {cold['ttft_s']:.0f} s. Afterwards the model stays resident for the keep-alive time "
               f"and the first token takes {h['ttft_warm_mean']:.2f} s on average.</p>")
    segs = [[r["load_s"], r["prompt_eval_s"], r["generation_s"]] for r in runs]
    out.append(ctx.fig("chart", "fig-breakdown", "Where the wall-clock time goes: load, prompt processing, generation (seconds). The cold run dwarfs the rest.",
                       charts.hbar_stacked([r["title"][:24] for r in runs], segs, ["Model load", "Prompt eval", "Generation"], title="Time breakdown per request", width=900)))
    warm_runs = [r for r in runs if not r.get("cold")]
    out.append(ctx.fig("chart", "fig-breakdown-warm", "Same breakdown without the cold run, so the warm requests are readable.",
                       charts.hbar_stacked([r["title"][:24] for r in warm_runs], [[r["load_s"], r["prompt_eval_s"], r["generation_s"]] for r in warm_runs],
                                           ["Model load", "Prompt eval", "Generation"], title="Warm requests", width=900)))
    out.append(ctx.h3("cold-note", "Reading the cold run"))
    out.append("<p>Prompt-processing speed of the cold run (~3 tok/s) is meaningless as a throughput figure: it includes the one-off cost of paging the weights in. "
               "Use the warm numbers and the prefill sweep below instead.</p>")

    out.append(ctx.h3("prefill", "Prompt processing (prefill)"))
    sw = b["prefill_sweep"]
    out.append(ctx.fig("chart", "fig-prefill", "Time to process prompts of increasing length (synthetic text, unique prefix so no cache is reused, 8 output tokens).",
                       charts.line_chart([("prefill time", [s["prompt_tokens"] for s in sw], [s["prompt_eval_s"] for s in sw]),
                                          ("time to first token", [s["prompt_tokens"] for s in sw], [s["ttft_s"] for s in sw])],
                                         title="Prefill time vs prompt length", xlabel="prompt tokens", ylabel="seconds", markers=True)))
    out.append(table(["Words", "Prompt tokens", "Prefill (s)", "Prefill speed (tok/s)", "TTFT (s)"],
                     [[s["words"], s["prompt_tokens"], f"{s['prompt_eval_s']:.2f}", f"{s['prompt_tps']:.0f}", f"{s['ttft_s']:.2f}"] for s in sw], num_cols=(0, 1, 2, 3, 4)))
    out.append("<p>Prefill runs at roughly 440–580 tokens/s and grows close to linearly with prompt length, which is why the conversation-history "
               "switch matters: each turn re-sends earlier turns (the GUI showed 60 → 395 → 681 prompt tokens over three turns).</p>")

    out.append(ctx.h3("reasoning", "Effect of reasoning mode"))
    off = {r["title"]: r for r in b["reasoning_off"]}
    on = {r["title"]: r for r in runs if r["category"] == "reasoning"}
    titles = list(on)
    out.append(ctx.fig("chart", "fig-think", "Wall-clock time of the three reasoning examples with thinking on (GUI default for this category) versus off.",
                       charts.bar_chart([f"{t[:12]} {m}" for t in titles for m in ("on", "off")],
                                        [v for t in titles for v in (on[t]["wall_s"], off[t]["wall_s"])], title="Response time (s)",
                                        unit="s", colors=["var(--c3)", "var(--c0)"] * 3, width=860)))
    out.append(table(["Example", "Mode", "Generated", "Reasoning chars", "Answer chars", "Answered", "Wall (s)", "tok/s"],
                     [[t, m, r["generated_tokens"], r["reasoning_chars"], r["answer_chars"], "yes" if r["answered"] else "no", f"{r['wall_s']:.1f}", f"{r['tps']:.1f}"]
                      for t in titles for m, r in (("medium", on[t]), ("off", off[t]))], num_cols=(2, 3, 4, 6, 7)))
    out.append("<p>Reasoning does not make tokens slower; it makes there <em>more</em> of them (the thinking trace is billed in generated tokens). "
               "With thinking on, the Logic puzzle used the entire 2048-token budget and never answered; with it off, the same puzzle was answered in the same budget. "
               "Quality of the answers was not graded here, only completion and cost.</p>")

    out.append(ctx.h3("resources", "Resource use"))
    long_run = max(runs, key=lambda r: r["wall_s"] if not r.get("cold") else 0)
    xs, cpu = _series(cold, "cpu_pct")
    xw, wired = _series(cold, "wired_gb")
    out.append(ctx.fig("chart", "fig-wired-cold", "System wired memory during the cold request: it rises by about 20 GB while the model loads.",
                       charts.line_chart([("wired memory (GB, system-wide)", xw, wired)], title="Wired memory, cold start", xlabel="seconds", ylabel="GB")))
    out.append(ctx.fig("chart", "fig-cpu", f"CPU load of the Ollama processes (sum over cores, 100 % = one core) during the cold run and a long warm run ({long_run['title']}).",
                       charts.line_chart([("cold start", *_series(cold, "cpu_pct")), (long_run["title"], *_series(long_run, "cpu_pct"))],
                                         title="Ollama CPU %", xlabel="seconds", ylabel="% of one core")))
    out.append(table(["Metric", "Value", "How it was measured"], [
        ["Peak Ollama CPU", f"{h['peak_cpu']:.0f} %", "summed <code>ps</code> %CPU of processes named ollama, every 0.5 s"],
        ["Peak system wired memory", f"{h['peak_wired']:.1f} GB", "<code>vm_stat</code> wired pages; <b>system-wide</b>, includes the OS"],
        ["Ollama resident set (warm)", f"{min(r['peak_rss_mb'] for r in runs[1:]):.0f}–{max(r['peak_rss_mb'] for r in runs[1:]):.0f} MB",
         "Weights live in wired GPU memory (MLX), not in the process RSS"],
        ["Model size reported by Ollama", f"{host['model_size_gb']:.2f} GB at benchmark time", "<code>/api/ps</code> (later captures: 22.2–22.7 GB incl. context)"]]))
    out.append(theme.callout("warn", "Caveats",
                             "<p>Wired memory is a whole-system counter, so the 24–25 GB figure is the model <i>plus</i> everything else the OS keeps wired. "
                             "RSS of the Ollama process is small because the MLX runner keeps weights in GPU-wired memory. GPU utilisation was not sampled (macOS exposes it only with elevated tools).</p>"))

    out.append(ctx.h3("gui", "Numbers seen in the GUI"))
    out.append(table(["Run in the GUI", "Prompt tokens", "Generated", "tok/s", "TTFT (s)", "Response (s)", "Source screenshot"],
                     [[a, b_, c, d, e, f, g] for a, b_, c, d, e, f, g in GUI_RUNS], num_cols=(1, 2, 3, 4, 5)))
    out.append(theme.callout("warn", "Run-to-run variance",
                             "<p>The same Logic puzzle (2048 generated tokens each time) ran at 45.9 tok/s in the benchmark, 60.3 tok/s in one GUI session and 102.7 tok/s in another. "
                             "Single runs on a laptop are noisy (thermal state, other processes, memory pressure, possibly speculative decoding with the MTP heads). "
                             "The benchmark is therefore n = 1 per cell and the figures are indicative, not a rating of the model; the 15-run mean (46 tok/s) is the steadier number.</p>"))

    out.append(ctx.h3("limits", "Limits of this measurement"))
    out.append("<ul><li>One machine, one model build, one run per example (no confidence intervals).</li>"
               "<li>Short prompts; long-context behaviour above ~5.6k tokens was not measured.</li>"
               "<li>Time to first token in the GUI includes network-free but non-zero Streamlit overhead; the benchmark measures the engine directly.</li>"
               "<li>Expert activity is never measured; see " + ctx.xref("s3-router") + ".</li></ul>")
    return "\n".join(out)


# =============================================================================================== 8
def chapter8(ctx: Ctx) -> str:
    ctx.start(8)
    out = [ctx.head(8, "Symptoms, causes and fixes; every configurable option in one place; diagnostic commands and known limitations.")]
    out.append(ctx.h3("issues", "Common problems"))
    out.append(table(["Symptom", "Cause", "Fix", "Evidence"], [
        ["Red “Ollama offline” banner", "Server not running or wrong <code>OLLAMA_BASE_URL</code>", "<code>ollama serve</code> (or open the app), fix .env, press Refresh", ctx.xref("fig-offline")],
        ["“Model … is not installed”", "Model not pulled", "<code>ollama pull nemotron-3.5-lightning:30b-a3b-mlx</code>", ctx.xref("s3-errors")],
        ["First answer takes about a minute", "Cold start: weights must be loaded (41 s load + prefill)", "Press <b>Load now</b> first, or raise keep-alive", ctx.xref("s7-cold")],
        ["Empty answer with a yellow warning", "Reasoning consumed the whole token budget", "Raise Max new tokens or set Reasoning mode to Off", ctx.xref("fig-limit")],
        ["Prompt tokens grow every turn", "Conversation history is re-sent (last 6 turns)", "Untick “Send conversation history” or press Clear conversation", ctx.xref("s7-gui")],
        ["Changing context window is slow once", "Ollama reloads the model for a new <code>num_ctx</code>", "Pick the window once, keep it", ctx.xref("fig-tooltip")],
        ["Group names end with “…”", "Narrow Compare-tab columns truncate labels (cosmetic)", "Widen the browser window; hover for full names", ctx.xref("fig-compare")],
        ["Start script exits immediately", "Port busy or <code>APP_START_CMD</code> unquoted in .env", "Check <code>.run/app.log</code>; keep the value in double quotes", ctx.xref("s6-config")],
        ["“Port 5000 is reserved”", "macOS AirDrop uses 5000", "Use another <code>APP_PORT</code> (default 8501)", ctx.xref("s6-scripts")],
        ["Heatmap looks the same for different models", "It is a simulation of the categories", "Expected; see the honesty caption", ctx.xref("s3-router")]]))
    out.append(ctx.shot("fig-diag-offline", "Diagnostic view 1: the offline banner names the URL that failed and the command to start the server.", "11_offline_error.png",
                        pins=[(22.5, 38.8, "Failed URL and remedy, taken straight from <code>OllamaConnectionError</code>.")], url="http://localhost:8502"))
    out.append(ctx.shot("fig-diag-limit", "Diagnostic view 2: the Compare tab on a fresh session. The measured table is empty until runs finish.", "12_compare_tab.png",
                        pins=[(50, 84, "No finished run yet, so no rows. A category missing from the table simply has no completed run in this browser session.")],
                        url="http://localhost:8502"))

    out.append(ctx.h3("options", "Configuration reference"))
    out.append(table(["Where", "Option", "Default", "When to change it"], [
        [".env", C("OLLAMA_BASE_URL"), "http://localhost:11434", "Ollama on another host/port"],
        [".env", C("OLLAMA_MODEL"), "nemotron-3.5-lightning:30b-a3b-mlx", "Try another installed model"],
        [".env", C("OLLAMA_KEEP_ALIVE"), "15m", "Longer sessions; “0” frees memory immediately"],
        [".env", C("OLLAMA_TIMEOUT"), "600", "Slow disks or very cold loads"],
        ["Sidebar", "Temperature", "1.0", "0.2 for code/facts, 1.0+ for creative"],
        ["Sidebar", "Top-p", "0.95", "Lower for more focused sampling"],
        ["Sidebar", "Context window", "8192", "Longer inputs (more memory, reload once)"],
        ["Sidebar", "Max new tokens", "2048", "Raise when reasoning is on"],
        ["Sidebar", "Reasoning mode", "Auto", "Off for speed, On/Medium for hard problems"],
        ["Code", C("router_sim.AFFINITY_STRENGTH"), "0.5", "How sharply categories separate in the simulation"]]))

    out.append(ctx.h3("diag", "Diagnostic commands"))
    out.append(theme.code("curl -s http://localhost:11434/api/version        # is Ollama up?\n"
                          "curl -s http://localhost:11434/api/ps             # is the model resident, how big, which context?\n"
                          "ollama list                                       # is the model installed?\n"
                          "ollama show nemotron-3.5-lightning:30b-a3b-mlx    # thinking levels, license, requirements\n"
                          "curl -s http://localhost:8501/_stcore/health      # is the GUI up? (prints ok)\n"
                          "tail -n 50 .run/app.log                           # GUI log written by scripts/start.sh\n"
                          "lsof -i :8501 -i :11434                           # who owns the ports?\n"
                          ".venv/bin/python -m pytest -q                     # run the whole test suite\n", "shell", lang="sh"))
    out.append(ctx.fig("term", "fig-diag-captured", "The first two diagnostics, captured from the machine used for this document.",
                       theme.term_block("diagnostics", ctx.evidence("ollama_api.txt"))))

    out.append(ctx.h3("limits", "Known limitations"))
    out.append("<ul><li><b>No real expert telemetry.</b> Ollama exposes no router output; the heatmap is a deterministic simulation.</li>"
               "<li><b>Category affinities are assumptions</b> chosen to illustrate soft specialisation, not measured from this model.</li>"
               "<li>Live tokens/s counts streamed chunks, an approximation until the final figure arrives.</li>"
               "<li>Metrics are per request; the Compare table is per browser session and is lost on reload.</li>"
               "<li>The keyword classifier is deliberately simple; use the sidebar to force a category.</li>"
               "<li>Benchmarks are single-run, single-machine (" + ctx.xref("s7-limits") + ").</li></ul>")
    out.append(theme.callout("note", "Licences", "<p>The application is MIT licensed. The model is distributed under the NVIDIA Open Model Agreement (see <code>ollama show</code>, "
                             + ctx.xref("fig-ollama-show") + "); check its terms before redistributing weights or outputs.</p>"))
    return "\n".join(out)
