"""Nemotron 3.5 Lightning - Mixture-of-Experts explorer (Streamlit GUI, fully local via Ollama).

Run:  scripts/start.sh      (or: .venv/bin/streamlit run app.py)

Layout
  Sidebar : Ollama connection + model status, load/unload, sampling parameters, help.
  Tab 1   : "Demo"   - example tasks, chat, live metrics and the expert panel.
  Tab 2   : "Compare tasks" - routing profile of every category + measured speed per category.
  Tab 3   : "MoE guide"     - concepts and what is measured vs. illustrative.

MoE demonstration logic (summary)
  * Measured : Ollama returns token counts and timings -> tokens/s, TTFT, load time, ...
  * Illustrative : Ollama cannot expose router decisions, so `router_sim` simulates top-6-of-128
    routing biased by the task category's expert affinity (see moe_demo/categories.py).
"""
from __future__ import annotations

import time

import streamlit as st

from moe_demo import ui_components as ui
from moe_demo.categories import CATEGORIES, EXPERT_GROUPS, classify
from moe_demo.config import get_settings
from moe_demo.engine import (THINK_MODES, build_messages, build_options, reasoning_share,
                             resolve_think, stream_answer)
from moe_demo.help_text import MOE_GUIDE, PARAM_GUIDE, TOOLTIPS
from moe_demo.ollama_client import OllamaClient, OllamaError
from moe_demo.router_sim import simulate

st.set_page_config(page_title="Nemotron 3.5 Lightning - MoE explorer", page_icon="🧩", layout="wide")
SETTINGS = get_settings()
AUTO = "Auto-detect"


@st.cache_resource
def get_client(base_url: str, timeout: float) -> OllamaClient:
    return OllamaClient(base_url, timeout)


client = get_client(SETTINGS.base_url, SETTINGS.request_timeout)

# ----------------------------------------------------------------------------- session state
ss = st.session_state
ss.setdefault("messages", [])      # chat history (dicts: role, content, thinking, category, ...)
ss.setdefault("pending", None)     # {"prompt": str, "category": key|None} queued by a click
ss.setdefault("last", None)        # last finished run -> drives metrics + expert panel
ss.setdefault("runs", [])          # every finished run (for the comparison tab)


def queue_example(prompt: str, category: str) -> None:
    ss.pending = {"prompt": prompt, "category": category}


# ----------------------------------------------------------------------------- connection / model status
def probe() -> dict:
    """Collect connection + model state; never raises (errors become a status message)."""
    info = {"online": False, "version": "", "installed": [], "loaded": None, "error": ""}
    try:
        info["version"] = client.version()
        info["online"] = True
        info["installed"] = client.list_models()
    except OllamaError as exc:
        info["error"] = str(exc)
    return info


status = probe()

with st.sidebar:
    st.title("🧩 MoE explorer")
    st.caption("NVIDIA Nemotron 3.5 Lightning 30B-A3B · local via Ollama")

    # --- connection ---------------------------------------------------------------------
    st.subheader("Connection")
    if status["online"]:
        st.success(f"Ollama online · v{status['version']}")
    else:
        st.error("Ollama offline")
        st.caption(status["error"])
    if st.button("🔄 Refresh status", use_container_width=True):
        st.rerun()

    installed = status["installed"]
    if installed:
        idx = installed.index(SETTINGS.model) if SETTINGS.model in installed else 0
        model = st.selectbox("Model", installed, index=idx)
    else:
        model = st.text_input("Model", SETTINGS.model)

    # --- model loading status -----------------------------------------------------------
    st.subheader("Model status")
    if not status["online"]:
        st.warning("⚪ Unknown (Ollama offline)")
    elif model not in installed:
        st.error(f"❌ Not installed. Run: `ollama pull {model}`")
    else:
        try:
            loaded = client.loaded_info(model)
        except OllamaError:
            loaded = None
        if loaded:
            gb = loaded.get("size", 0) / 1e9
            st.success(f"🟢 Loaded in memory ({gb:.1f} GB)")
            if loaded.get("context_length"):
                st.caption(f"Loaded context: {loaded['context_length']} tokens")
            if loaded.get("expires_at"):
                st.caption(f"Unloads at {loaded['expires_at'][11:19]} (keep-alive {SETTINGS.keep_alive})")
        else:
            st.info("⚪ Installed, not loaded yet. The first request loads it (can take ~1 min).")
        c1, c2 = st.columns(2)
        if c1.button("Load now", use_container_width=True, disabled=bool(loaded)):
            t0 = time.perf_counter()
            try:
                with st.spinner("Loading model into memory..."):
                    client.preload(model, SETTINGS.keep_alive)
                st.toast(f"Model loaded in {time.perf_counter() - t0:.1f}s")
            except OllamaError as exc:
                st.error(str(exc))
            st.rerun()
        if c2.button("Unload", use_container_width=True, disabled=not loaded):
            try:
                client.unload(model)
            except OllamaError as exc:
                st.error(str(exc))
            st.rerun()

    # --- sampling parameters ------------------------------------------------------------
    st.subheader("Parameters")
    st.caption("Read on every request: change them and send the next message.")
    use_cat_temp = st.checkbox("Use the category's suggested temperature", value=False,
                               help="Overrides the slider with a per-task default (e.g. 1.0 creative, 0.2 coding).")
    temperature = st.slider("Temperature", 0.0, 2.0, 1.0, 0.05, help=TOOLTIPS["temperature"],
                            disabled=use_cat_temp)
    top_p = st.slider("Top-p", 0.05, 1.0, 0.95, 0.01, help=TOOLTIPS["top_p"])
    num_ctx = st.select_slider("Context window (tokens)", [2048, 4096, 8192, 16384, 32768, 65536],
                               value=8192, help=TOOLTIPS["num_ctx"])
    num_predict = st.select_slider("Max new tokens", [-1, 256, 512, 1024, 2048, 4096], value=2048,
                                   help=TOOLTIPS["num_predict"])
    think_mode = st.selectbox("Reasoning mode", THINK_MODES, help=TOOLTIPS["think"])
    use_history = st.checkbox("Send conversation history", value=True, help=TOOLTIPS["history"])
    use_sys = st.checkbox("Use category system prompt", value=True)

    with st.expander("ℹ️ About these settings"):
        st.markdown(PARAM_GUIDE)

    if st.button("🗑️ Clear conversation", use_container_width=True):
        ss.messages, ss.last, ss.pending = [], None, None
        st.rerun()

# ----------------------------------------------------------------------------- header
st.title("Nemotron 3.5 Lightning · Mixture-of-Experts explorer")
st.caption(ui.sparsity_caption().replace("**", ""))
tab_demo, tab_compare, tab_guide = st.tabs(["🚀 Demo", "📊 Compare tasks", "📖 MoE guide"])

# ============================================================================= TAB 1: DEMO
with tab_demo:
    # ---- example tasks ---------------------------------------------------------------
    st.subheader("Pre-loaded examples")
    st.caption("Click an example to run it instantly. Each task type sends tokens to a different mix of experts.")
    cols = st.columns(len(CATEGORIES))
    for col, (key, cat) in zip(cols, CATEGORIES.items()):
        with col:
            st.markdown(f"**{cat.icon} {cat.name}**")
            st.caption(cat.blurb)
            for i, ex in enumerate(cat.examples):
                st.button(ex.title, key=f"ex_{key}_{i}", use_container_width=True,
                          help=ex.prompt[:300], on_click=queue_example, args=(ex.prompt, key))

    st.divider()
    left, right = st.columns([3, 2], gap="large")

    # ---- right: metrics + expert panel (placeholders are filled during streaming) -----
    with right:
        st.subheader("📈 Inference metrics")
        metrics_ph = st.empty()
        st.subheader("🧩 Expert panel")
        task_choice = st.selectbox("Task type shown in the panel", [AUTO] + [ui.category_label(k) for k in CATEGORIES],
                                   help=TOOLTIPS["category"])
        expert_ph = st.empty()

    forced_key = None if task_choice == AUTO else next(
        k for k in CATEGORIES if ui.category_label(k) == task_choice)

    def render_experts(key: str | None, text: str, note: str = "") -> None:
        """Render the explanation + simulated routing for `key` (illustrative, see router_sim)."""
        with expert_ph.container():
            if key is None:
                st.info("Pick a task type or run a prompt to see which experts are likely involved.")
                return
            cat = CATEGORIES[key]
            res = simulate(text, key)
            st.markdown(f"**{cat.icon} {cat.name}** — {note}" if note else f"**{cat.icon} {cat.name}**")
            st.markdown(ui.top_group_chips(res), unsafe_allow_html=True)
            st.write(cat.why)
            st.markdown(ui.expert_heatmap(res), unsafe_allow_html=True)
            st.caption(f"128 experts (8 groups × 16). Simulated top-6 routing over {res.n_tokens} tokens. "
                       "**Illustrative**: Ollama does not expose the real router.")
            with st.expander("Share of expert selections per group"):
                st.markdown(ui.group_bars(res), unsafe_allow_html=True)

    last = ss.last
    metrics_ph.markdown(ui.metric_cards(last["metrics"] if last else None,
                                        reasoning_pct=last["reasoning"] if last else None),
                        unsafe_allow_html=True)
    if last:
        render_experts(last["category"], last["prompt"], "category of the last request")
    else:
        render_experts(forced_key, CATEGORIES[forced_key].examples[0].prompt if forced_key else "",
                       "preview using the first example")

    # ---- left: conversation -----------------------------------------------------------
    with left:
        st.subheader("💬 Conversation")
        for m in ss.messages:
            with st.chat_message(m["role"]):
                if m.get("thinking"):
                    with st.expander("💭 Reasoning trace"):
                        st.text(m["thinking"])
                st.markdown(m["content"])
                if m.get("badge"):
                    st.caption(m["badge"])
        if not ss.messages:
            st.info("Start with an example above, or type your own question below.")

        # Queue a typed prompt (chat_input is pinned to the page bottom).
        typed = st.chat_input("Ask Nemotron anything…")
        if typed:
            ss.pending = {"prompt": typed, "category": None}

        pending, ss.pending = ss.pending, None
        if pending:
            prompt = pending["prompt"]
            # Category precedence: example's own > sidebar/panel choice > keyword heuristic.
            cat_key = pending["category"] or forced_key or classify(prompt)[0]
            cat = CATEGORIES[cat_key]
            history = list(ss.messages)
            ss.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                st.caption(f"Detected task type: {cat.icon} {cat.name}")
                think_ph, answer_ph = st.empty(), st.empty()
                error: str | None = None
                content = thinking = ""
                final = None
                try:
                    opts = build_options(cat.temperature if use_cat_temp else temperature, top_p,
                                         num_ctx, num_predict)
                    messages = build_messages(cat.system_prompt if use_sys else "", history, prompt, use_history)
                    think = resolve_think(think_mode, cat.think)
                    render_experts(cat_key, prompt, "routing for this request")
                    last_draw = 0.0
                    answer_ph.markdown("_Waiting for the model (a cold start loads ~19 GB)…_")
                    for upd in stream_answer(client, model, messages, opts, think, SETTINGS.keep_alive):
                        content, thinking, final = upd.content, upd.thinking, upd.final
                        now = time.perf_counter()
                        if final is None and now - last_draw < 0.12:   # throttle UI redraws
                            continue
                        last_draw = now
                        if thinking and not content:
                            think_ph.markdown("💭 *reasoning…*\n\n> " + thinking[-500:].replace("\n", "\n> "))
                        else:
                            think_ph.empty()
                        answer_ph.markdown(content + ("" if final else " ▌"))
                        metrics_ph.markdown(
                            ui.metric_cards(final, upd.live_tps, upd.chunks, upd.elapsed, upd.ttft,
                                            reasoning_share(thinking, content) if thinking else None),
                            unsafe_allow_html=True)
                except ValueError as exc:
                    error = f"Invalid settings: {exc}"
                except OllamaError as exc:
                    error = str(exc)

                think_ph.empty()
                if thinking:
                    with think_ph.expander("💭 Reasoning trace"):
                        st.text(thinking)
                if error:
                    st.error(error)
                    if content:
                        answer_ph.markdown(content + "\n\n_(interrupted)_")
                if final is not None and not content and thinking:
                    answer_ph.warning("The token limit was reached during reasoning. Raise 'Max new tokens' "
                                      "or set Reasoning mode to Off.")

            badge = ""
            if final is not None:
                badge = (f"{final.tokens_per_second:.1f} tok/s · {final.generated_tokens} tokens · "
                         f"{final.wall_seconds:.1f}s")
                share = reasoning_share(thinking, content) if thinking else 0.0
                ss.last = {"category": cat_key, "prompt": prompt, "metrics": final, "reasoning": share if thinking else None}
                ss.runs.append({"category": cat_key, "tps": final.tokens_per_second,
                                "ttft": final.ttft_seconds, "gen": final.generated_tokens,
                                "prompt_tokens": final.prompt_tokens, "wall": final.wall_seconds})
            ss.messages.append({"role": "assistant", "content": content or (f"⚠️ {error}" if error else ""),
                                "thinking": thinking, "badge": badge, "category": cat_key})
            if error:
                ss.messages[-1]["content"] = (content + "\n\n" if content else "") + f"⚠️ {error}"

# ============================================================================= TAB 2: COMPARE
with tab_compare:
    st.subheader("How different tasks light up different experts")
    st.caption("Simulated routing profile (share of expert selections per group) for each category's first example. "
               "Illustrative: the shape comes from the category affinity, not from model telemetry.")
    ccols = st.columns(len(CATEGORIES))
    for col, (key, cat) in zip(ccols, CATEGORIES.items()):
        with col:
            res = simulate(cat.examples[0].prompt, key)
            st.markdown(f"**{cat.icon} {cat.name}**")
            st.markdown(ui.group_bars(res), unsafe_allow_html=True)

    st.subheader("Measured on your machine this session")
    if ss.runs:
        rows: dict[str, dict] = {}
        for r in ss.runs:
            agg = rows.setdefault(r["category"], {"n": 0, "tps": 0.0, "ttft": 0.0, "gen": 0, "wall": 0.0})
            agg["n"] += 1
            agg["tps"] += r["tps"]; agg["ttft"] += r["ttft"]; agg["gen"] += r["gen"]; agg["wall"] += r["wall"]
        table = [{"Task type": ui.category_label(k), "Runs": a["n"],
                  "Avg tok/s": round(a["tps"] / a["n"], 1), "Avg TTFT (s)": round(a["ttft"] / a["n"], 2),
                  "Avg generated tokens": round(a["gen"] / a["n"]), "Avg response (s)": round(a["wall"] / a["n"], 1)}
                 for k, a in rows.items()]
        st.dataframe(table, use_container_width=True, hide_index=True)
    else:
        st.info("Run a few examples from different categories to fill this table.")

# ============================================================================= TAB 3: GUIDE
with tab_guide:
    st.markdown(MOE_GUIDE)
    st.markdown("**Expert groups used for visualisation:** " + ", ".join(EXPERT_GROUPS) + ".")
