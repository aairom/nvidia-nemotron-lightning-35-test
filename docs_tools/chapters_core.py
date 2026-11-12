"""Chapters 1-4: architecture, GUI, engine/integration, expert system.

Every number comes from `data` (source files, benchmark.json, the live router simulation); every code listing is
extracted from the real source, so the documentation cannot drift silently from the application.
"""
from __future__ import annotations

import dataclasses
from html import escape

from moe_demo import categories, config, engine, metrics, ollama_client, router_sim
from moe_demo.categories import CATEGORIES, EXPERT_GROUPS

from . import charts, data, theme
from .context import Ctx, Raw, code_inline, grid2, kpis, table

C = code_inline


def _mod_role(rel: str) -> str:
    return {
        "app.py": "Streamlit script: sidebar, three tabs, chat loop, glue between everything below",
        "moe_demo/categories.py": "5 task categories, 15 examples, 8 expert groups, keyword classifier",
        "moe_demo/config.py": "Reads .env / environment into an immutable Settings object",
        "moe_demo/engine.py": "UI-independent: Ollama options, reasoning mode, message list, streaming + live metrics",
        "moe_demo/help_text.py": "Tooltips, MoE guide and parameter guide (text only)",
        "moe_demo/metrics.py": "RunMetrics from Ollama's final chunk (ns to s), sparsity fractions",
        "moe_demo/ollama_client.py": "HTTP client, streaming NDJSON, typed errors",
        "moe_demo/router_sim.py": "Deterministic simulation of top-6-of-128 routing (illustrative)",
        "moe_demo/ui_components.py": "HTML for metric cards, heatmap, group bars, chips",
        "moe_demo/__init__.py": "Package marker",
    }[rel]


# =============================================================================================== 1
def chapter1(ctx: Ctx) -> str:
    ctx.start(1)
    stats = data.source_stats()
    total = sum(stats.values())
    out = [ctx.head(1, "How the pieces fit together: a thin Streamlit front end over a UI-independent engine, "
                       "an HTTP client for the local Ollama server, and an explicitly labelled routing simulation.")]
    out.append(kpis([(str(total), "lines of application code"), (str(len(stats) - 1), "Python modules + app.py"),
                     ("0", "cloud services"), ("2", "runtime dependencies (streamlit, requests)")]))

    out.append(ctx.h3("components", "Component map"))
    out.append("<p>The application is split so that everything testable is independent of Streamlit. "
               f"Only <code>app.py</code> and <code>ui_components.py</code> know about the GUI; "
               f"{ctx.xref('fig-component-map')} shows the dependency direction (arrows point from caller to callee).</p>")
    nodes = {
        "config": (20, 40, 130, 56, f"config.py\n.env → Settings", "data"),
        "ui": (220, 40, 160, 56, "ui_components.py\nHTML cards, heatmap", "ui"),
        "router": (440, 40, 160, 56, "router_sim.py\nsimulated top-6 / 128", "logic"),
        "browser": (20, 150, 130, 60, "Browser\nStreamlit client", "ui"),
        "app": (220, 150, 160, 60, f"app.py\n{stats['app.py']} lines", "ui"),
        "engine": (440, 150, 160, 60, "engine.py\noptions · think · stream", "logic"),
        "client": (660, 150, 170, 60, "ollama_client.py\nHTTP + typed errors", "logic"),
        "help": (20, 270, 130, 56, "help_text.py\ntooltips · guide", "ui"),
        "cats": (220, 270, 160, 56, "categories.py\n5 tasks · classify", "logic"),
        "metrics": (440, 270, 160, 56, "metrics.py\nRunMetrics", "data"),
        "ollama": (660, 270, 170, 60, "Ollama 0.40.16\nMLX runner", "ext"),
        "model": (660, 360, 170, 56, "Nemotron 3.5 Lightning\n30B-A3B (MoE)", "model"),
    }
    edges = [("browser", "app", "WebSocket"), ("config", "app", ""), ("app", "ui", ""), ("app", "router", ""),
             ("app", "engine", ""), ("app", "cats", ""), ("app", "help", ""), ("engine", "client", ""),
             ("engine", "metrics", ""), ("client", "ollama", "HTTP /api/*"), ("ollama", "model", "")]
    out.append(ctx.fig("diagram", "fig-component-map",
                       "Component map. Blue = GUI, purple = logic, green = data/config, amber = external process, pink = model.",
                       charts.diagram(nodes, edges, width=860, height=430, title="Component map")))

    out.append(ctx.h3("modules", "Modules and responsibilities"))
    rows = [[C(f), _mod_role(f), stats[f]] for f in data.SOURCE_FILES]
    rows.append([Raw("<b>Total</b>"), "", Raw(f"<b>{total}</b>")])
    out.append(table(["File", "Responsibility", "Lines"], rows, num_cols=(2,)))
    out.append(ctx.fig("term", "fig-tree", "Project layout as it exists on disk (generated from the file system at build time).",
                       theme.term_block("tree", data.project_tree())))

    out.append(ctx.h3("flow", "Request lifecycle"))
    out.append("<p>A click on an example and a typed prompt take the same path: both are written to "
               f"{C('st.session_state.pending')} and consumed once, at the end of the next script run.</p>")
    actors = ["User", "app.py", "engine.py", "ollama_client", "Ollama"]
    msgs = [(0, 1, "click example / type prompt"), (1, 1, "queue_example → ss.pending"),
            (1, 1, "classify() + build_options()"), (1, 2, "stream_answer(...)"), (2, 3, "chat_stream(...)"),
            (3, 4, "POST /api/chat (stream)"), (4, 3, "NDJSON thinking / content"), (3, 2, "StreamEvent"),
            (2, 1, "LiveUpdate (live tok/s, TTFT)"), (1, 0, "redraw answer + cards (≤ 8 Hz)"),
            (4, 3, "final chunk: eval_count, durations"), (2, 1, "LiveUpdate.final = RunMetrics"),
            (1, 0, "heatmap from router_sim.simulate()")]
    out.append(ctx.fig("diagram", "fig-sequence", "Sequence of one request, from click to final metrics.",
                       charts.sequence_diagram(actors, msgs, title="Request lifecycle", width=900)))

    out.append(ctx.h3("model", "Data model"))
    out.append("<p>Seven small dataclasses carry all state between the layers. Field lists below are read with "
               f"{C('dataclasses.fields')} from the running code.</p>")
    classes = [(categories.Category, "categories.py", "Static description of a task type"),
               (categories.Example, "categories.py", "One clickable example prompt"),
               (metrics.RunMetrics, "metrics.py", "Measured numbers of one request"),
               (ollama_client.StreamEvent, "ollama_client.py", "One piece of a streamed reply"),
               (engine.LiveUpdate, "engine.py", "Snapshot yielded while streaming"),
               (router_sim.RoutingResult, "router_sim.py", "Aggregated simulated routing"),
               (config.Settings, "config.py", "Immutable configuration")]
    rows = [[C(c.__name__), mod, Raw(", ".join(f"<code>{escape(f.name)}</code>" for f in dataclasses.fields(c))), purpose]
            for c, mod, purpose in classes]
    out.append(table(["Dataclass", "Module", "Fields", "Purpose"], rows))

    out.append(ctx.h3("state", "Session state"))
    out.append(table(["Key", "Type", "Meaning"], [
        [C("ss.messages"), "list[dict]", "Chat history (role, content, thinking, badge, category)"],
        [C("ss.pending"), "dict | None", "Prompt queued by a click or by the chat box; consumed once per run"],
        [C("ss.last"), "dict | None", "Last finished run: drives the metric cards and expert panel"],
        [C("ss.runs"), "list[dict]", "Every finished run: feeds the measured table on the Compare tab"]]))
    out.append(theme.callout("note", "Design decision",
                             "<p>Sampling parameters are <b>not</b> stored in session state. Streamlit widgets are read on every "
                             "script run and passed to <code>build_options()</code> per request, which is why a slider change "
                             "takes effect on the very next message (requirement 8) with no extra plumbing.</p>"))
    out.append(ctx.fig("term", "fig-requirements", "The two runtime dependencies (requirements.txt) and the development set.",
                       theme.term_block("requirements", "$ cat requirements.txt\n" + data.read_text("requirements.txt")
                                        + "\n$ cat requirements-dev.txt\n" + data.read_text("requirements-dev.txt"))))
    return "\n".join(out)


# =============================================================================================== 2
def chapter2(ctx: Ctx) -> str:
    ctx.start(2)
    out = [ctx.head(2, "A tour of the running interface. Every screenshot is a real capture of the live app against the "
                       "local Ollama server; the red pins are explained under each image.")]
    out.append("<p>The GUI is a single Streamlit page with a persistent sidebar and three tabs. It runs entirely on "
               f"localhost; nothing is loaded from a CDN. Layout: sidebar (connection, model, parameters), "
               f"<b>Demo</b> (examples, chat, metrics, expert panel), <b>Compare tasks</b>, <b>MoE guide</b>.</p>")

    out.append(ctx.h3("home", "Home screen and pre-loaded examples"))
    out.append(ctx.shot("fig-home", "Idle state with the model resident in memory (requirements 5, 9, 10).", "01_home_online.png", pins=[
        (19.6, 30, "<b>Connection</b>: green when Ollama answers <code>/api/version</code>; shows the server version."),
        (19.6, 57.5, "<b>Model status</b>: from <code>/api/ps</code>: resident size (22.2 GB), loaded context and the keep-alive expiry time."),
        (19.6, 72.4, "<b>Load now / Unload</b>: pre-load or evict the model (<code>keep_alive</code> 0). Load is disabled while loaded."),
        (44.5, 31.4, "<b>Tabs</b>: Demo, Compare tasks, MoE guide."),
        (95.7, 46.2, "<b>15 pre-loaded examples</b> in five columns, one per task type; one click runs the prompt."),
        (39.7, 87, "<b>Conversation</b> pane (left)."),
        (86.8, 87, "<b>Inference metrics</b> and <b>Expert panel</b> (right), filled while streaming.")],
        boxes=[(1, 27, 18, 6), (25, 29, 18, 4), (25, 46, 70, 31)]))

    out.append(ctx.h3("run", "Running a task: conversation, metrics, experts"))
    out.append(ctx.shot("fig-run", "Coding example after completion: streamed answer, six measured cards and the simulated expert panel.",
                        "03_conversation_metrics_experts.png", pins=[
        (45, 24, "<b>Chat input</b>: any custom query; it gets the same pipeline as the examples (requirement 6)."),
        (62, 32, "<b>User bubble</b>."),
        (47.5, 42, "<b>Detected task type</b>: the example's own category, else the sidebar choice, else the keyword classifier."),
        (28, 70, "<b>Streamed answer</b> with syntax-highlighted code."),
        (94, 13, "<b>Six measured cards</b>: tokens/s, time to first token, response time, load time, prompt tokens, generated tokens."),
        (82, 47, "<b>Task type for the panel</b>: Auto-detect or force a category to compare profiles."),
        (89, 58, "<b>Group chips</b>: the groups that receive most simulated selections."),
        (82, 86, "<b>8 × 16 heatmap</b>: 128 experts, one row per group (illustrative).")],
        boxes=[(69, 13, 25, 22)]))

    out.append(ctx.h3("panel", "Expert panel in detail"))
    out.append(ctx.shot("fig-panel", "Expert panel: chips, rationale text, heatmap and per-group share bars (requirement 7).",
                        "04_expert_panel_groups.png", pins=[
        (88.6, 11.4, "<b>Chips</b> with percentage of simulated selections."),
        (97.5, 23.7, "<b>Why</b>: the category's rationale (<code>Category.why</code>)."),
        (97.5, 39.5, "<b>Heatmap</b>: brighter cell = expert chosen by more tokens; hover shows the count."),
        (97.5, 51.3, "<b>Honesty caption</b>: states that Ollama does not expose the real router."),
        (92.5, 68, "<b>Per-group share bars</b> (expander).")]))

    out.append(ctx.h3("live", "Live streaming"))
    out.append(ctx.shot("fig-live", "Mid-stream capture of the Logic puzzle: cards switch to live values while the model is still generating.",
                        "05_live_streaming.png", pins=[
        (84.5, 3, "Streamlit's <b>Stop</b> control is visible, so this is a genuine mid-run capture."),
        (78.9, 17, "<b>Tokens / second (live)</b>: approximated from streamed chunks until the exact figure arrives."),
        (91.6, 17, "<b>Time to first token</b>: 1.33 s (client-side)."),
        (78.9, 24.7, "<b>Elapsed</b> 21.0 s and <b>streamed chunks</b> 857."),
        (78.9, 32.2, "<b>Reasoning share</b>: 100 % of the text so far is the thinking trace."),
        (97.2, 78, "The <b>expert panel</b> is already drawn from the prompt, before the first token arrives.")]))

    out.append(ctx.h3("reasoning", "Reasoning traces and the token limit"))
    out.append("<p>With the default <b>Max new tokens = 2048</b> the Logic puzzle can spend the entire budget thinking "
               "and never write an answer. The GUI detects this and says so instead of showing an empty reply.</p>")
    out.append(ctx.shot("fig-limit", "Reasoning exhausted the budget: collapsed trace plus an explicit warning.",
                        "06_reasoning_trace_limit.png", pins=[
        (45, 42, "<b>Reasoning trace</b> expander (the full trace is kept; the live view shows only the last 500 characters)."),
        (66.8, 50, "<b>Warning</b>: raise Max new tokens or set Reasoning mode to Off."),
        (96.6, 22, "<b>Metrics</b> still reported: 2048 generated tokens, reasoning share 100 %.")]))

    out.append(ctx.h3("compare", "Compare tab"))
    out.append(ctx.shot("fig-compare", "Compare tasks: simulated routing profile per category, then measured speed per category for this session.",
                        "07_compare_measured.png", pins=[
        (45, 31.4, "<b>Compare tasks</b> tab."),
        (62.5, 47.3, "Five <b>simulated profiles</b> (first example of each category)."),
        (51.0, 58.6, "Known cosmetic flaw: long group names are truncated with “…” in narrow columns."),
        (97.3, 85.2, "<b>Measured table</b>: grows with every run in this session (n = 1 per row here).")]))

    out.append(ctx.h3("help", "Documentation inside the application"))
    out.append(ctx.shot("fig-tooltip", "Sidebar parameters with an open help tooltip (requirements 8 and 11).", "08_sidebar_parameters_tooltip.png", pins=[
        (64.3, 22.9, "<b>Tooltip</b>: text from <code>help_text.TOOLTIPS</code>."),
        (22.2, 31.3, "<b>Temperature</b> 0–2, step 0.05, default 1.0 (NVIDIA recommendation)."),
        (22.2, 40.3, "<b>Top-p</b> 0.05–1.0, default 0.95."),
        (22.2, 49.3, "<b>Context window</b> 2048 … 65536 tokens, default 8192."),
        (22.2, 58.2, "<b>Max new tokens</b> −1 (unlimited) … 4096, default 2048."),
        (22.2, 67.2, "<b>Reasoning mode</b>: Auto (per category), Off, On, Medium."),
        (22.2, 74.5, "<b>History / system prompt</b> switches."),
        (22.2, 81.6, "<b>About these settings</b> expander."),
        (22.2, 87.6, "<b>Clear conversation</b>.")]))
    out.append(ctx.shot("fig-offline", "Connection failure handled gracefully: red banner with the fix, controls stay usable (requirement 10).",
                        "11_offline_error.png", pins=[
        (22.5, 29.6, "<b>Ollama offline</b> banner."),
        (22.5, 38.8, "Actionable message: start <code>ollama serve</code> and check <code>OLLAMA_BASE_URL</code>."),
        (22.5, 54.3, "Model falls back to a free-text field when the model list cannot be fetched."),
        (22.5, 66.3, "Model status shows <b>Unknown</b> instead of guessing."),
        (60, 75.5, "Examples remain visible; a click then reports the error inside the chat.")], url="http://localhost:8502"))
    out.append(ctx.shot("fig-guide", "MoE guide tab (captured in the offline instance; the tab does not need Ollama).", "13_guide_tab.png", pins=[
        (46, 31.4, "<b>MoE guide</b> tab."),
        (22.5, 38.3, "Concept section: dense vs sparse, router, top-k."),
        (22.5, 53.3, "Numbered router steps: score, select top-k, combine."),
        (22.5, 77, "Model-specific facts: hybrid Mamba-2 + MoE + attention, MTP, optional reasoning.")]))

    out.append(ctx.h3("widgets", "Widget reference"))
    out.append(table(["Control", "Streamlit call", "Range / default", "Effect"], [
        ["Model", C("selectbox / text_input"), "installed models; env default", "Model used for the next request"],
        ["Suggested temperature", C("checkbox"), "off", "Overrides the slider with the category value"],
        ["Temperature", C("slider"), "0–2, 1.0", "Sampling randomness"],
        ["Top-p", C("slider"), "0.05–1.0, 0.95", "Nucleus sampling"],
        ["Context window", C("select_slider"), "2048–65536, 8192", "Ollama <code>num_ctx</code>; changing it reloads the model"],
        ["Max new tokens", C("select_slider"), "−1–4096, 2048", "<code>num_predict</code>; includes reasoning tokens"],
        ["Reasoning mode", C("selectbox"), "Auto, Off, On, Medium", "Ollama <code>think</code> field"],
        ["Send history", C("checkbox"), "on", "Last 6 turns are sent; inflates prompt tokens"],
        ["Category system prompt", C("checkbox"), "on", "Short role prompt per category"]]))

    out.append(ctx.h3("click", "From click to run"))
    out.append("<p>Example buttons use Streamlit's <code>on_click</code> callback so the prompt is queued <em>before</em> the script reruns:</p>")
    out.append(theme.code(data.snippet("app.py", "def queue_example", "# -----"), "app.py: callback"))
    out.append(theme.code(data.snippet("app.py", "st.button(ex.title", "st.divider", 4), "app.py: one button per example"))
    out.append(theme.code(data.snippet("app.py", "pending, ss.pending = ss.pending, None", 'with st.chat_message("user")', 9),
                          "app.py: the pending prompt is consumed exactly once"))
    out.append("<p>Redraws are throttled to about 8 per second (<code>now - last_draw &lt; 0.12</code>) so a fast stream "
               "does not make Streamlit re-render hundreds of times.</p>")
    return "\n".join(out)


# =============================================================================================== 3
def chapter3(ctx: Ctx) -> str:
    ctx.start(3)
    out = [ctx.head(3, "How the application talks to Ollama, turns timings into metrics, and degrades gracefully. "
                       "This layer has no Streamlit imports, so it is tested against a stub server.")]
    out.append(ctx.h3("endpoints", "Ollama endpoints used"))
    out.append(table(["Method", "Endpoint", "Client method", "Used for"], [
        ["GET", C("/api/version"), C("version() / is_alive()"), "Connection banner"],
        ["GET", C("/api/tags"), C("list_models()"), "Model selector"],
        ["GET", C("/api/ps"), C("running_models() / loaded_info()"), "Loaded status, size, context, expiry"],
        ["POST", C("/api/generate"), C("preload() / unload()"), "Load now / Unload (<code>keep_alive</code> 0)"],
        ["POST", C("/api/chat"), C("chat_stream()"), "Streaming completion with <code>think</code>"]]))
    out.append(ctx.fig("term", "fig-ollama-live", "Real responses from the local server used for the screenshots (trimmed).",
                       theme.term_block("ollama", ctx.evidence("ollama_list.txt") + "\n" + ctx.evidence("ollama_api.txt"))))
    out.append(ctx.fig("term", "fig-ollama-show", "What Ollama reports about the model: architecture, quantisation and the three thinking levels.",
                       theme.term_block("ollama show", ctx.evidence("ollama_show.txt"))))
    out.append(theme.callout("note", "Numbers to keep apart",
                             "<p>Ollama reports <b>32.9B</b> parameters and a <b>262 144</b>-token context for this build (nvfp4 weights), "
                             "while the model card names it <b>30B-A3B</b> (about 30B total, about 3B active). The GUI uses the "
                             "model-card figures for the sparsity caption and the 8192-token window is a runtime choice, not a model limit.</p>"))

    out.append(ctx.h3("stream", "Streaming and live metrics"))
    flow = {
        "a": (20, 60, 150, 56, "chat_stream()\nNDJSON lines", "logic"),
        "b": (220, 60, 150, 56, "kind?\nthinking · content · done", "logic"),
        "c": (420, 10, 190, 56, "append to thinking / content\nchunks += 1", "data"),
        "d": (420, 110, 190, 56, "first token?\nttft = now − start", "data"),
        "e": (660, 60, 190, 56, "yield LiveUpdate\nlive_tps = chunks / gen_time", "ui"),
        "f": (420, 210, 190, 56, "done chunk\nfrom_stats(...)", "model"),
        "g": (660, 210, 190, 56, "yield LiveUpdate\nfinal = RunMetrics", "ui"),
    }
    out.append(ctx.fig("diagram", "fig-stream-flow", "Control flow of stream_answer().",
                       charts.diagram(flow, [("a", "b", ""), ("b", "c", "content / thinking"), ("c", "d", ""), ("d", "e", ""),
                                             ("b", "f", "done"), ("f", "g", "")], width=880, height=290, title="stream_answer")))
    out.append(theme.code(data.source_of(engine.stream_answer), "moe_demo/engine.py"))
    out.append("<p>Live tokens/s is <em>chunks per second</em>: Ollama streams roughly one token per chunk, so it is an "
               "approximation that is replaced by the exact figure as soon as the <code>done</code> chunk arrives.</p>")

    out.append(ctx.h3("mapping", "From Ollama fields to GUI cards"))
    out.append(table(["Ollama field / client timer", "RunMetrics field", "GUI card", "Unit conversion"], [
        [C("prompt_eval_count"), C("prompt_tokens"), "Prompt tokens", "-"],
        [C("eval_count"), C("generated_tokens"), "Generated tokens", "includes reasoning tokens"],
        [C("eval_count / eval_duration"), C("tokens_per_second"), "Tokens / second", "ns → s"],
        [C("load_duration"), C("load_seconds"), "Model load time", "ns → s"],
        [C("prompt_eval_duration"), C("prompt_eval_seconds"), "(prefill speed in Chapter 7)", "ns → s"],
        ["client: first streamed token", C("ttft_seconds"), "Time to first token", "perf_counter"],
        ["client: end of stream", C("wall_seconds"), "Response time", "perf_counter"]]))
    out.append(theme.code(data.snippet("moe_demo/metrics.py", "def from_stats", "def active_fractions", 14), "moe_demo/metrics.py"))

    out.append(ctx.h3("think", "Reasoning mode mapping"))
    rows = []
    for mode in engine.THINK_MODES:
        row = [mode]
        for k, c in CATEGORIES.items():
            row.append(repr(engine.resolve_think(mode, c.think)))
        rows.append(row)
    out.append("<p>Table generated by calling <code>resolve_think()</code> for every mode and category. "
               "The value is exactly what is placed in the <code>think</code> field of the chat request.</p>")
    out.append(table(["Reasoning mode"] + [CATEGORIES[k].name for k in CATEGORIES], rows))
    out.append(theme.code(data.source_of(engine.build_options) + "\n\n" + data.source_of(engine.resolve_think), "moe_demo/engine.py"))

    out.append(ctx.h3("errors", "Error handling"))
    out.append(table(["Situation", "Exception", "Message shown to the user", "Where handled"], [
        ["Server not running", C("OllamaConnectionError"), "Cannot reach Ollama at … Start it with ollama serve", "sidebar banner / chat"],
        ["Model not pulled", C("OllamaModelNotFound"), "Model '…' is not installed. Run: ollama pull …", "sidebar + chat"],
        ["No answer in time", C("OllamaTimeout"), "Ollama did not answer within …s", "chat"],
        ["Connection lost mid-stream", C("OllamaConnectionError"), "Connection to Ollama was lost", "chat (partial text kept, marked interrupted)"],
        ["Error object in the stream", C("OllamaError"), "the server's own text", "chat"],
        ["Bad slider combination", C("ValueError"), "Invalid settings: …", "chat"],
        ["Token budget spent thinking", "(no exception)", "The token limit was reached during reasoning …", "warning under the trace"]]))
    out.append(theme.code(data.snippet("moe_demo/ollama_client.py", "def _request", "@staticmethod", 12), "moe_demo/ollama_client.py"))
    out.append(theme.code(data.snippet("moe_demo/ollama_client.py", "payload: dict", "# (connect timeout", 10)
                          + "\n        ...\n" + data.snippet("moe_demo/ollama_client.py", "resp = self._request(\"POST\", \"/api/chat\"", None, 1),
                          "moe_demo/ollama_client.py: request payload; the read timeout covers a cold load"))

    out.append(ctx.h3("router", "Routing simulation"))
    out.append(theme.callout("warn", "Measured vs illustrative",
                             "<p><b>Measured</b>: tokens/s, time to first token, response time, load time, prompt and generated tokens, "
                             "reasoning share. <b>Illustrative</b>: which experts fire. Ollama's API has no field for the router's per-token "
                             "choices, so <code>router_sim</code> <i>simulates</i> top-6-of-128 routing. The GUI says so next to every heatmap.</p>"))
    rf = {
        "t": (20, 60, 140, 56, "token\n(word / punctuation)", "ui"),
        "s": (210, 60, 190, 56, "score every expert e = 0…127\n0.5·affinity(group(e)) + noise", "logic"),
        "n": (210, 160, 190, 56, "noise = blake2b(token|e) / 2³²\ndeterministic, in [0, 1)", "data"),
        "k": (450, 60, 170, 56, "sort descending\ntake TOP_K = 6", "logic"),
        "a": (670, 60, 180, 56, "aggregate 200 tokens max\ncounts per expert and group", "model"),
    }
    out.append(ctx.fig("diagram", "fig-router-flow", "Algorithm of router_sim.simulate().",
                       charts.diagram(rf, [("t", "s", ""), ("n", "s", ""), ("s", "k", ""), ("k", "a", "")], width=880, height=240, title="router_sim")))
    out.append(theme.code(data.source_of(router_sim.route_token) + "\n\n" + data.source_of(router_sim.simulate), "moe_demo/router_sim.py"))
    out.append("<p>Properties verified by unit tests: the result is deterministic (same prompt → same picture), always exactly 6 "
               "distinct experts per token inside 0…127, and different categories produce different group profiles.</p>")
    return "\n".join(out)


# =============================================================================================== 4
def chapter4(ctx: Ctx) -> str:
    ctx.start(4)
    out = [ctx.head(4, "What the application teaches about Mixture-of-Experts, how the five task types differ, and where the "
                       "line between fact and illustration is drawn.")]
    out.append(ctx.h3("idea", "The MoE idea"))
    out.append("<p>A dense transformer applies every weight to every token. A Mixture-of-Experts layer holds many "
               "small feed-forward <em>experts</em> and a <em>router</em> that picks a few per token. Nemotron 3.5 Lightning "
               f"keeps about 30B parameters of knowledge but computes with about 3B per token: {router_sim.TOP_K} of "
               f"{router_sim.N_EXPERTS} experts ({router_sim.TOP_K / router_sim.N_EXPERTS:.1%}).</p>")
    cf = {
        "tok": (20, 100, 120, 56, "token", "ui"),
        "rt": (190, 100, 130, 56, "router\nscores 128", "logic"),
        "ex": (370, 20, 230, 100, "128 experts\n6 selected (top-6)\nothers stay idle", "model"),
        "mix": (650, 100, 190, 56, "weighted sum\nof the 6 outputs", "data"),
        "dense": (370, 170, 230, 56, "dense model would run all 128", "ext"),
    }
    out.append(ctx.fig("concept", "fig-moe-concept", "Concept: sparse routing. Only the selected experts do work for a token.",
                       charts.diagram(cf, [("tok", "rt", ""), ("rt", "ex", "top-6"), ("ex", "mix", ""), ("rt", "dense", "")],
                                      width=880, height=250, title="MoE concept")))
    out.append(theme.callout("note", "Hybrid architecture", "<p>According to the model card, the network interleaves Mamba-2 state-space layers, "
                             "MoE layers and a few attention layers; Multi-Token-Prediction heads support speculative decoding. "
                             "Those facts explain flat per-token cost on long inputs and are summarised in the app's MoE guide.</p>"))

    out.append(ctx.h3("groups", "Eight expert groups and five task types"))
    out.append("<p>To make the idea visible without real router telemetry, the 128 experts are drawn as <b>8 groups of 16</b>. "
               "Each category has an <em>affinity</em> for some groups (0–1). These weights encode a plausible, widely reported "
               "tendency (code → symbols and structure, narrative → style and grammar) and are <b>an educational assumption</b>.</p>")
    rows, cols, mat = data.affinity_matrix()
    out.append(ctx.fig("concept", "fig-affinity", "Configured affinity of each task type for each expert group (percent).",
                       charts.matrix_heatmap(rows, cols, mat, title="Category affinity (illustrative input to the simulation)")))
    radars = []
    for i, (k, c) in enumerate(CATEGORIES.items()):
        vals = [c.expert_affinity.get(g, 0.0) for g in EXPERT_GROUPS]
        radars.append(charts.radar_chart([g.split(" & ")[0] for g in EXPERT_GROUPS], vals, title=f"{c.icon} {c.name}",
                                         color=f"var(--c{i})", size=300))
    out.append(ctx.fig("concept", "fig-radars", "The same affinities as radar charts: each category has a distinct silhouette.",
                       '<div class="grid2">' + "".join(radars) + "</div>"))
    out.append(table(["Task type", "Suggested temp.", "Reasoning", "System prompt", "Keywords (sample)"],
                     [[f"{c.icon} {c.name}", c.temperature, c.think, c.system_prompt, ", ".join(c.keywords[:5])]
                      for c in CATEGORIES.values()], num_cols=(1,)))

    out.append(ctx.h3("sim", "What the simulation produces"))
    shares = data.simulated_shares()
    names = [CATEGORIES[k].name for k in CATEGORIES]
    segs = [[shares[k][g] * 100 for g in EXPERT_GROUPS] for k in CATEGORIES]
    out.append(ctx.fig("chart", "fig-sim-shares", "Share of simulated expert selections per group for the first example of every category (percent). Computed live from router_sim.",
                       charts.hbar_stacked(names, segs, EXPERT_GROUPS, title="Simulated group shares", unit="%", width=900)))
    conc = {k: data.concentration(v) for k, v in shares.items()}
    out.append(table(["Task type", "Top group", "Share", "Top-2 share"],
                     [[CATEGORIES[k].name, max(shares[k], key=shares[k].get), f"{max(shares[k].values()):.0%}", f"{conc[k]:.0%}"]
                      for k in CATEGORIES], num_cols=(2, 3)))
    sweep = data.strength_sweep()
    out.append(ctx.h3("tuning", "Why AFFINITY_STRENGTH = 0.5"))
    out.append("<p>The strength balances category bias against token-level randomness. At 1.6 one group took about 92 % of the "
               "selections, which looks like a hard switch rather than a soft router. 0.5 keeps a clear dominant group while still "
               "mixing in others, like real MoE traces. The sweep is recomputed at build time:</p>")
    out.append(ctx.fig("chart", "fig-strength", "Mean share of the dominant group across the five categories as a function of AFFINITY_STRENGTH.",
                       charts.bar_chart([f"{s:g}" for s, _, _ in sweep], [t * 100 for _, t, _ in sweep], title="Dominant-group share vs strength (%)",
                                        unit="%", colors=["var(--c7)", "var(--c7)", "var(--c0)", "var(--c7)", "var(--c7)"])))
    out.append(table(["AFFINITY_STRENGTH", "Mean top group", "Mean top-2 groups"],
                     [[f"{s:g}" + ("  ← used" if s == router_sim.AFFINITY_STRENGTH else ""), f"{t:.0%}", f"{t2:.0%}"] for s, t, t2 in sweep], num_cols=(1, 2)))

    out.append(ctx.h3("token", "One token, six experts"))
    tok = "interval"
    picks = {k: router_sim.route_token(tok, k) for k in ("coding", "creative")}
    out.append(f"<p>The same token <code>{tok}</code> routed under two categories. Highlighted cells are the six selected experts; "
               "notice that the coding profile favours rows 0 and 6 (code, structure) while the creative profile favours rows 2 and 4 (narrative, grammar).</p>")
    out.append(ctx.fig("concept", "fig-token-coding", "Top-6 experts for one token under the Coding profile (simulated).",
                       charts.expert_grid(picks["coding"], EXPERT_GROUPS, title=f"“{tok}” → coding")))
    out.append(ctx.fig("concept", "fig-token-creative", "Top-6 experts for the same token under the Creative profile (simulated).",
                       charts.expert_grid(picks["creative"], EXPERT_GROUPS, title=f"“{tok}” → creative")))

    out.append(ctx.h3("classifier", "Classifying custom queries"))
    res = data.classifier_accuracy()
    ok = sum(1 for k, _, p in res if k == p)
    out.append(f"<p>Free-text prompts are assigned to a category by a transparent keyword score (<code>classify()</code>), "
               f"so custom queries also get an explanation panel. On the {len(res)} built-in examples it picks the intended category "
               f"{ok}/{len(res)} times. That is a sanity check on curated prompts, not a general accuracy claim; ambiguous prompts "
               "fall back to <em>factual</em>, and the sidebar lets the user override the guess.</p>")
    out.append(theme.code(data.snippet("moe_demo/categories.py", "def classify", None, 20), "moe_demo/categories.py"))

    out.append(ctx.h3("measured", "Do categories really behave differently? (measured)"))
    pc = data.per_category(data.load_benchmark())
    out.append("<p>What <em>is</em> measurable is how the workload differs: generation length, speed and latency per task type "
               f"(benchmark in {ctx.xref('ch7')}). Reasoning produces by far the most tokens because of the thinking trace; "
               "short factual answers finish in about a second.</p>")
    out.append(ctx.fig("chart", "fig-cat-tokens", "Mean generated tokens per task type (3 examples each, reasoning mode as in the GUI defaults).",
                       charts.bar_chart(names, [pc[k]["gen"] for k in CATEGORIES], title="Mean generated tokens", colors=[f"var(--c{i})" for i in range(5)])))
    out.append(ctx.fig("chart", "fig-cat-tps", "Mean decode speed per task type (tokens/s).",
                       charts.bar_chart(names, [pc[k]["tps"] for k in CATEGORIES], title="Mean tokens / second", unit="", colors=[f"var(--c{i})" for i in range(5)])))
    out.append(theme.callout("warn", "How to read this",
                             "<p>Speed differences between categories are small and partly driven by answer length, sampling and system "
                             "noise; they are <b>not</b> evidence that different experts run at different speeds. The honest conclusion "
                             "is: the <i>workload</i> differs per task type (measured), the <i>expert routing</i> picture is a teaching aid (simulated).</p>"))
    return "\n".join(out)
