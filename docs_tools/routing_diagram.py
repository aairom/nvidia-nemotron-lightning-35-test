"""Generate the "token routing through sparse experts" technical diagram (SVG).

The picture is *illustrative*: Ollama does not expose the real router decisions, so the expert ids
come from the project's deterministic simulator (`moe_demo.router_sim.route_token`) and the gate
weights are fixed example values. Architecture facts used (30B total / ~3B active, 128 routed experts,
top-6, hybrid Mamba-2 + MoE + attention) are the ones stated in the project README.

Usage:  python -m docs_tools.routing_diagram [output.svg]
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from moe_demo.router_sim import N_EXPERTS, TOP_K, route_token

WIDTH, HEIGHT = 1920, 1580
CATEGORY = "coding"
TOKENS = ["write", "a", "python", "function", "now"]
TOKEN_A, TOKEN_B = "python", "function"          # the two tokens whose routing is drawn
GATES = [0.31, 0.22, 0.17, 0.12, 0.10, 0.08]     # illustrative, sums to 1.0

GREEN, PURPLE, GOLD, BLUE = "#76b900", "#b48cff", "#ffb52e", "#5b8cff"
MUTED, TEXT, PANEL, LINE = "#8b96a1", "#e8ecef", "#12161a", "#2d363d"
MONO = "'IBM Plex Mono', Menlo, monospace"

GRID_X, GRID_Y, CELL, GAP, COLS = 600, 540, 30, 6, 16


def t(x, y, s, size=18, fill=TEXT, weight=400, anchor="start", mono=False):
    """SVG text element."""
    fam = f' font-family="{MONO}"' if mono else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}"{fam}>{escape(s)}</text>')


def rect(x, y, w, h, fill="none", stroke="none", sw=2, rx=10, extra=""):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}" {extra}/>')


def arrow(x1, y1, x2, y2, color=GREEN, sw=3, head=11):
    """Line with a filled arrow head at (x2, y2)."""
    ang = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - head * math.cos(ang), y2 - head * math.sin(ang)
    px, py = -math.sin(ang) * head * 0.55, math.cos(ang) * head * 0.55
    return (f'<line x1="{x1}" y1="{y1}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{color}" stroke-width="{sw}"/>'
            f'<polygon points="{x2},{y2} {bx + px:.1f},{by + py:.1f} {bx - px:.1f},{by - py:.1f}" fill="{color}"/>')


def panel(x, y, w, h, title):
    return rect(x, y, w, h, PANEL, LINE, 2, 16) + t(x + 25, y + 35, title, 26, TEXT, 700)


def bob(x, y, scale):
    """The IBM Bob hard-hat mascot."""
    return f'''<g transform="translate({x},{y}) scale({scale})">
    <path d="M72 175 C72 80 130 50 197 50 C264 50 322 80 322 175 Z" fill="url(#hat)" stroke="#262626" stroke-width="9" stroke-linejoin="round"/>
    <rect x="163" y="14" width="68" height="84" rx="14" fill="url(#hat)" stroke="#262626" stroke-width="9"/>
    <rect x="42" y="160" width="310" height="32" rx="16" fill="url(#hat)" stroke="#262626" stroke-width="9"/>
    <path d="M100 150 Q197 135 294 150" fill="none" stroke="#262626" stroke-width="7" stroke-linecap="round"/>
    <rect x="40" y="215" width="40" height="80" rx="14" fill="#dedede" stroke="#262626" stroke-width="8"/>
    <rect x="314" y="215" width="40" height="80" rx="14" fill="#dedede" stroke="#262626" stroke-width="8"/>
    <rect x="72" y="195" width="250" height="160" rx="44" fill="#f2f2f2" stroke="#262626" stroke-width="9"/>
    <circle cx="140" cy="268" r="27" fill="#161616"/><circle cx="150" cy="259" r="8" fill="#fff"/>
    <circle cx="254" cy="268" r="27" fill="#161616"/><circle cx="264" cy="259" r="8" fill="#fff"/>
    <path d="M166 312 Q197 332 230 312" fill="none" stroke="#161616" stroke-width="8" stroke-linecap="round"/>
    <ellipse cx="68" cy="440" rx="40" ry="55" fill="#ececec" stroke="#262626" stroke-width="8"/>
    <ellipse cx="326" cy="440" rx="40" ry="55" fill="#ececec" stroke="#262626" stroke-width="8"/>
    <rect x="92" y="368" width="210" height="140" rx="30" fill="#f8f8f8" stroke="#262626" stroke-width="9"/>
    <text x="197" y="462" font-size="74" font-weight="800" fill="#2f66ff" text-anchor="middle" font-family="{MONO}">&lt;/&gt;</text>
    <path d="M92 400 L112 400 L106 520 L84 512 Z" fill="#ececec" stroke="#262626" stroke-width="6" stroke-linejoin="round"/>
    <path d="M302 400 L282 400 L288 520 L310 512 Z" fill="#ececec" stroke="#262626" stroke-width="6" stroke-linejoin="round"/>
  </g>'''


def selected(token: str) -> list[int]:
    """Expert ids chosen for `token`, best score first (simulated)."""
    return route_token(token, CATEGORY)


def left_column(a: list[int]) -> list[str]:
    out = [rect(40, 170, 410, 130, "#1b1f23", "#3a4048", 2, 18),
           f'<polygon points="190,300 224,332 258,300" fill="#1b1f23" stroke="#3a4048" stroke-width="2"/>',
           rect(193, 297, 62, 6, "#1b1f23", rx=0)]
    for i, line in enumerate(["I score all 128 experts, keep", "the best 6, and blend their", "outputs using the gate weights."]):
        out.append(t(245, 213 + i * 32, line, 21, TEXT, 400, "middle"))
    out.append(bob(70, 345, 0.8))
    out.append(t(235, 805, "IBM Bob", 28, "#cfd6ff", 700, "middle"))
    # legend
    out.append(rect(40, 840, 410, 330, PANEL, LINE, 2, 16))
    out.append(t(65, 878, "Legend", 24, TEXT, 700))
    items = [(GOLD, "circle", "Router (gate network)"),
             (GREEN, "rect", f"Active expert, token “{TOKEN_A}”"),
             (PURPLE, "rect", f"Active expert, token “{TOKEN_B}”"),
             ("#1a2126", "rect", "Idle expert: no compute"),
             (BLUE, "rect", "Always-on layers (Mamba-2, attention)")]
    for i, (col, shape, label) in enumerate(items):
        y = 912 + i * 38
        if shape == "circle":
            out.append(f'<circle cx="82" cy="{y}" r="11" fill="{col}"/>')
        else:
            stroke = "#3b4952" if col == "#1a2126" else col
            out.append(rect(71, y - 11, 22, 22, col, stroke, 2, 5))
        out.append(t(108, y + 6, label, 17, TEXT))
    out.append(t(65, 1118, "Expert ids come from moe_demo/router_sim.py;", 14, MUTED))
    out.append(t(65, 1138, "gate weights are example values. Ollama does", 14, MUTED))
    out.append(t(65, 1158, "not expose the model's real router output.", 14, MUTED))
    return out


def panel_routing(a: list[int]) -> list[str]:
    px, py = 500, 170
    out = [panel(px, py, 1380, 270, "① Routing mechanism: score → select → weight")]
    for i, tok in enumerate(TOKENS):
        x = 525 + i * 110
        stroke = GREEN if tok == TOKEN_A else PURPLE if tok == TOKEN_B else "#3b4952"
        out.append(rect(x, 225, 100, 34, "#171c20", stroke, 3 if stroke != "#3b4952" else 1.5, 8))
        out.append(t(x + 50, 248, tok, 17, TEXT, 600, "middle", True))
    out.append(t(1085, 248, "← every token is routed independently", 16, MUTED))
    out.append(arrow(795, 259, 795, 318, GREEN))
    out.append(rect(720, 320, 150, 50, "#171c20", GREEN, 2, 8))
    shades = ["#2f5d1a", "#4a8a1f", "#76b900", "#3f7a1a", "#9fe04a", "#5ea31c", "#2f5d1a", "#76b900"]
    for i, c in enumerate(shades):
        out.append(rect(730 + i * 16.5, 330, 12, 30, c, rx=3))
    out.append(t(795, 392, "h ∈ ℝᵈ", 16, TEXT, 600, "middle", True))
    out.append(t(795, 414, f"hidden state of “{TOKEN_A}”", 15, MUTED, 400, "middle"))
    out.append(arrow(870, 345, 933, 345, GOLD))
    out.append(rect(935, 300, 300, 110, "#2a1f08", GOLD, 3, 14))
    out.append(t(1085, 330, "ROUTER (gate)", 20, GOLD, 800, "middle"))
    out.append(t(1085, 357, "scores = h · W_r → 128 logits", 16, TEXT, 400, "middle", True))
    out.append(t(1085, 380, "top-6 → softmax over the 6", 16, TEXT, 400, "middle", True))
    out.append(t(1085, 400, "other 122 experts: weight 0", 14, MUTED, 400, "middle"))
    out.append(arrow(1235, 355, 1288, 355, GOLD))
    out.append(t(1300, 292, f"top-{TOP_K} experts & gate weights g (example), Σ g = 1.00", 16, MUTED))
    for i, (e, g) in enumerate(zip(a, GATES)):
        y = 302 + i * 21
        out.append(t(1300, y + 12, f"E{e}", 14, GREEN, 700, "start", True))
        out.append(rect(1352, y, g * 700, 14, GREEN, rx=4))
        out.append(t(1352 + g * 700 + 10, y + 12, f"{g:.2f}", 14, TEXT, 400, "start", True))
    return out


def panel_pattern(a: list[int], b: list[int]) -> list[str]:
    px, py = 500, 460
    out = [panel(px, py, 1380, 440, f"② Sparse pattern: {N_EXPERTS} experts per MoE layer, only {TOP_K} active per token")]
    rows = N_EXPERTS // COLS
    for r in range(rows):
        out.append(t(GRID_X - 12, GRID_Y + r * (CELL + GAP) + 20, f"{r * COLS}–{r * COLS + COLS - 1}", 12, MUTED, 400, "end", True))
    for e in range(N_EXPERTS):
        r, c = divmod(e, COLS)
        x, y = GRID_X + c * (CELL + GAP), GRID_Y + r * (CELL + GAP)
        if e in a:
            out.append(rect(x, y, CELL, CELL, GREEN, "#c8ff6b", 2, 6, 'filter="url(#glow)"'))
            out.append(t(x + CELL / 2, y + 20, f"E{e}", 10.5, "#0c1a04", 800, "middle", True))
        elif e in b:
            out.append(rect(x, y, CELL, CELL, PURPLE, "#e0ccff", 2, 6, 'filter="url(#glow)"'))
            out.append(t(x + CELL / 2, y + 20, f"E{e}", 10.5, "#1a0c33", 800, "middle", True))
        else:
            out.append(rect(x, y, CELL, CELL, "#1a2126", "#2b363d", 1.5, 6))
    out.append(t(GRID_X, 860, f"One cell = one routed expert (E0–E{N_EXPERTS - 1}). Green: “{TOKEN_A}”. Purple: “{TOKEN_B}”.", 15, MUTED))
    blocks = [
        (GREEN, f"{TOP_K} / {N_EXPERTS} experts = {TOP_K / N_EXPERTS:.1%} selected per token",
         ["Top-k selection makes the compute per token fixed,", "whatever the input is."]),
        (PURPLE, "Different tokens → different experts",
         [f"“{TOKEN_A}” and “{TOKEN_B}” share no expert here.", "Specialisation is soft, not hard-wired."]),
        (GOLD, f"{N_EXPERTS - TOP_K} idle experts cost no FLOPs",
         ["Their weights stay in memory (all 30B must be", "loaded) but are never multiplied."]),
        (BLUE, "Load balancing (typical MoE training)",
         ["An auxiliary objective spreads tokens over experts,", "so none is starved or a bottleneck."]),
    ]
    for i, (col, head, sub) in enumerate(blocks):
        y = 545 + i * 85
        out.append(rect(1215, y - 22, 6, 62, col, rx=3))
        out.append(t(1238, y, head, 21, TEXT, 700))
        for j, s in enumerate(sub):
            out.append(t(1238, y + 24 + j * 20, s, 16, MUTED))
    return out


def panel_params() -> list[str]:
    px, py = 500, 920
    out = [panel(px, py, 1380, 240, "③ Parameters: 30B stored, ≈3B computed per token")]
    x0, w = 720, 1100
    out.append(t(525, 1000, "Total (stored)", 17, TEXT, 700))
    out.append(t(525, 1020, "30B", 17, MUTED))
    slice_w = w / N_EXPERTS
    for i in range(N_EXPERTS):
        out.append(rect(x0 + i * slice_w, 980, slice_w - 1.2, 40, "#3a4650" if i % 2 else "#2d3841", rx=1.5))
    out.append(t(x0 + w / 2, 1000, "128 routed experts + always-on layers (all resident in memory)", 16, TEXT, 600, "middle"))
    out.append(t(525, 1075, "Active (computed)", 17, GREEN, 700))
    out.append(t(525, 1095, "≈3B per token", 17, MUTED))
    out.append(rect(x0, 1055, w * 0.10, 40, GREEN, "#c8ff6b", 2, 4, 'filter="url(#glow)"'))
    out.append(t(x0 + w * 0.10 + 20, 1081, "≈10% of the weights do the work for each token", 18, GREEN, 700))
    out.append(t(525, 1135, "active ≈ always-on layers (Mamba-2, attention, embeddings) + 6/128 of the expert weights ≈ 3B", 17, TEXT, 400, "start", True))
    return out


def panel_flow(a: list[int]) -> list[str]:
    px, py = 500, 1180
    out = [panel(px, py, 1380, 340, "④ Data flow through the active pathway (one MoE layer)")]
    cy, top, step, bh = 1349, 1250, 34, 28
    out.append(rect(525, cy - 30, 100, 60, "#171c20", BLUE, 2, 10))
    out.append(t(575, cy + 6, "h_in", 20, TEXT, 700, "middle", True))
    out.append(arrow(625, cy, 678, cy, GOLD))
    out.append(rect(680, cy - 30, 120, 60, "#2a1f08", GOLD, 3, 12))
    out.append(t(740, cy + 6, "Router", 20, GOLD, 800, "middle"))
    for i, (e, g) in enumerate(zip(a, GATES)):
        y = top + i * step
        out.append(arrow(800, cy, 876, y + bh / 2, GREEN, 2, 9))
        out.append(rect(880, y, 130, bh, "#10230a", GREEN, 2.5, 7, 'filter="url(#glow)"'))
        out.append(t(945, y + 19, f"E{e}  × {g:.2f}", 15, GREEN, 700, "middle", True))
        out.append(arrow(1010, y + bh / 2, 1068, cy, GREEN, 2, 9))
    out.append(t(945, 1472, f"+ {N_EXPERTS - TOP_K} other experts skipped (weight 0)", 14, MUTED, 400, "middle"))
    out.append(f'<circle cx="1100" cy="{cy}" r="34" fill="#10230a" stroke="{GREEN}" stroke-width="3"/>')
    out.append(t(1100, cy + 9, "Σ", 30, GREEN, 700, "middle"))
    out.append(t(1100, cy + 80, "Σ gᵢ · Eᵢ(h)", 15, TEXT, 400, "middle", True))
    out.append(arrow(1134, cy, 1236, cy, GREEN))
    out.append(f'<circle cx="1260" cy="{cy}" r="24" fill="#171c20" stroke="{BLUE}" stroke-width="3"/>')
    out.append(t(1260, cy + 9, "+", 28, BLUE, 700, "middle"))
    out.append(f'<path d="M575 {cy + 30} V1492 H1260 V{cy + 28}" fill="none" stroke="{BLUE}" stroke-width="3" stroke-dasharray="9 7"/>')
    out.append(f'<polygon points="1260,{cy + 25} 1253,{cy + 40} 1267,{cy + 40}" fill="{BLUE}"/>')
    out.append(t(910, 1512, "residual connection (h_in is added back)", 14, BLUE, 400, "middle"))
    out.append(arrow(1284, cy, 1328, cy, BLUE))
    out.append(rect(1330, cy - 30, 160, 60, "#171c20", BLUE, 2, 10))
    out.append(t(1410, cy + 6, "h_out", 20, TEXT, 700, "middle", True))
    out.append(t(1410, cy + 52, "→ next block", 14, MUTED, 400, "middle"))
    steps = ["1  Router scores 128 experts", "2  Keep top-6, softmax → gates", "3  Only those 6 FFNs run",
             "4  Blend: Σ gᵢ · Eᵢ(h)", "5  Add residual → next block"]
    for i, s in enumerate(steps):
        out.append(t(1530, 1275 + i * 34, s, 17, TEXT, 400, "start", True))
    out.append(t(1530, 1255, "Per-token execution", 16, MUTED, 700))
    return out


def build_svg() -> str:
    a, b = selected(TOKEN_A), selected(TOKEN_B)
    body: list[str] = []
    body.append(t(80, 90, "How Nemotron 3.5 Lightning routes tokens through sparse experts", 50, "#ffffff", 700))
    body.append(t(80, 135, "30B-A3B · hybrid Mamba-2 + MoE + attention · 128 routed experts, top-6 per token", 26, GREEN, 600))
    body += left_column(a) + panel_routing(a) + panel_pattern(a, b) + panel_params() + panel_flow(a)
    body.append(t(960, 1556, "Illustrative diagram: expert ids and gate weights are simulated (moe_demo/router_sim.py), not model telemetry.",
                  16, "#6b7680", 400, "middle"))
    defs = f'''<defs>
    <linearGradient id="hat" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2f66ff"/><stop offset="1" stop-color="#a66cff"/></linearGradient>
    <filter id="glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse"><path d="M48 0H0V48" fill="none" stroke="#fff" stroke-opacity="0.04"/></pattern>
  </defs>'''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" '
            f'font-family="\'IBM Plex Sans\', \'Helvetica Neue\', Arial, sans-serif">\n  {defs}\n'
            f'  <rect width="{WIDTH}" height="{HEIGHT}" fill="#0c0e10"/>\n  <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#grid)"/>\n  '
            + "\n  ".join(body) + "\n</svg>\n")


def main(argv: list[str]) -> None:
    out = Path(argv[1] if len(argv) > 1 else "Docs/images/token-routing.svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_svg(), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv)
