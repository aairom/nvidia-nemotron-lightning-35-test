"""Small HTML renderers for the metric cards and the expert-activation panel.

Pure functions returning strings, so they are unit-testable and keep `app.py` short.
All dynamic text is HTML-escaped before it is interpolated.
"""
from __future__ import annotations

from html import escape

from .categories import CATEGORIES, EXPERT_GROUPS
from .help_text import TOOLTIPS
from .metrics import RunMetrics, active_fractions
from .router_sim import GROUP_SIZE, N_EXPERTS, TOP_K, RoutingResult

GROUP_COLORS = ["#0f62fe", "#8a3ffc", "#d02670", "#198038", "#b28600", "#005d5d", "#fa4d56", "#6f6f6f"]

CSS = """
<style>
.mcard{display:inline-block;box-sizing:border-box;width:48%;margin:0 1% 8px 0;padding:8px 10px;
  border:1px solid #8883;border-radius:8px;background:#8881;vertical-align:top}
.mcard .l{font-size:.72rem;opacity:.7;cursor:help}
.mcard .v{font-size:1.25rem;font-weight:600;line-height:1.3}
.mcard .u{font-size:.75rem;opacity:.7;font-weight:400}
.ehm{display:grid;grid-template-columns:130px repeat(16,1fr);gap:2px;align-items:center;font-size:.7rem}
.ehm .gl{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;opacity:.85}
.ehm .c{height:14px;border-radius:2px;background:#8882}
.gbar{display:flex;align-items:center;gap:6px;font-size:.78rem;margin:2px 0}
.gbar .n{width:150px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gbar .b{height:10px;border-radius:5px}
.gbar .p{opacity:.7;width:42px}
.chip{display:inline-block;padding:1px 8px;margin:1px 2px;border-radius:10px;font-size:.72rem;color:#fff}
</style>
"""


def _card(label: str, value: str, unit: str = "", tip: str = "") -> str:
    return (f'<div class="mcard"><div class="l" title="{escape(tip)}">{escape(label)}</div>'
            f'<div class="v">{escape(value)} <span class="u">{escape(unit)}</span></div></div>')


def metric_cards(m: RunMetrics | None, live_tps: float = 0.0, live_chunks: int = 0,
                 elapsed: float = 0.0, ttft: float = 0.0, reasoning_pct: float | None = None) -> str:
    """Cards for the latest run. While streaming pass `live_*`; afterwards pass the final `m`."""
    if m is None and not live_chunks:
        return CSS + "<i>No request yet. Run an example or type a question.</i>"
    if m is not None:
        cards = [
            _card("Tokens / second", f"{m.tokens_per_second:.1f}", "tok/s", TOOLTIPS["tps"]),
            _card("Time to first token", f"{m.ttft_seconds:.2f}", "s", TOOLTIPS["ttft"]),
            _card("Response time", f"{m.wall_seconds:.2f}", "s", TOOLTIPS["wall"]),
            _card("Model load time", f"{m.load_seconds:.2f}", "s", TOOLTIPS["load"]),
            _card("Prompt tokens", f"{m.prompt_tokens}", "", TOOLTIPS["prompt_tokens"]),
            _card("Generated tokens", f"{m.generated_tokens}", "", TOOLTIPS["gen_tokens"]),
        ]
    else:
        cards = [
            _card("Tokens / second (live)", f"{live_tps:.1f}", "tok/s", TOOLTIPS["tps"]),
            _card("Time to first token", f"{ttft:.2f}", "s", TOOLTIPS["ttft"]),
            _card("Elapsed", f"{elapsed:.1f}", "s", TOOLTIPS["wall"]),
            _card("Streamed chunks", f"{live_chunks}", "", "Approximate token count while streaming."),
        ]
    if reasoning_pct is not None:
        cards.append(_card("Reasoning share", f"{reasoning_pct * 100:.0f}", "% of text",
                           "Share of streamed characters that belong to the reasoning trace."))
    return CSS + "".join(cards)


def expert_heatmap(res: RoutingResult) -> str:
    """128 cells (8 groups x 16 experts). Opacity = how often the simulated router picked the expert."""
    peak = max(res.expert_counts) or 1
    rows = []
    for g, name in enumerate(EXPERT_GROUPS):
        color = GROUP_COLORS[g % len(GROUP_COLORS)]
        cells = []
        for i in range(GROUP_SIZE):
            e = g * GROUP_SIZE + i
            c = res.expert_counts[e]
            style = f"background:{color};opacity:{0.12 + 0.88 * c / peak:.2f}" if c else ""
            cells.append(f'<div class="c" style="{style}" title="expert {e}: {c} token(s)"></div>')
        rows.append(f'<div class="gl" title="{escape(name)}">{escape(name)}</div>' + "".join(cells))
    return CSS + '<div class="ehm">' + "".join(rows) + "</div>"


def group_bars(res: RoutingResult) -> str:
    """Share of expert selections per conceptual group."""
    out = []
    for g, name in enumerate(EXPERT_GROUPS):
        share = res.group_share[name]
        color = GROUP_COLORS[g % len(GROUP_COLORS)]
        out.append(f'<div class="gbar"><span class="n">{escape(name)}</span>'
                   f'<span class="b" style="width:{share * 180:.0f}px;background:{color}"></span>'
                   f'<span class="p">{share * 100:.0f}%</span></div>')
    return CSS + "".join(out)


def top_group_chips(res: RoutingResult, n: int = 3) -> str:
    ranked = sorted(res.group_share.items(), key=lambda kv: -kv[1])[:n]
    return CSS + "".join(
        f'<span class="chip" style="background:{GROUP_COLORS[EXPERT_GROUPS.index(name)]}">'
        f'{escape(name)} {share * 100:.0f}%</span>' for name, share in ranked)


def sparsity_caption() -> str:
    f = active_fractions()
    return (f"Per token the model runs **{TOP_K} of {N_EXPERTS} experts "
            f"({f['active_expert_fraction'] * 100:.1f}%)** and about "
            f"**3B of 30B parameters ({f['active_param_fraction'] * 100:.0f}%)**.")


def category_label(key: str) -> str:
    c = CATEGORIES[key]
    return f"{c.icon} {c.name}"
