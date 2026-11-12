"""Dependency-free inline-SVG chart and diagram helpers for the HTML documentation.

Every function returns an SVG string. Text is HTML-escaped. Colours use CSS custom properties
(--c0..--c7, --ink, --muted, --grid) defined by the page stylesheet so charts follow the theme.
"""
from __future__ import annotations

import math
from html import escape

PALETTE = [f"var(--c{i})" for i in range(8)]
FONT = "font-family:var(--font);"


def _nice_max(v: float) -> float:
    """Round `v` up to a 'nice' axis maximum (1, 2, 2.5, 5 x 10^n)."""
    if v <= 0:
        return 1.0
    exp = math.floor(math.log10(v))
    for m in (1, 2, 2.5, 5, 10):
        if v <= m * 10 ** exp:
            return m * 10 ** exp
    return 10 ** (exp + 1)


def _fmt(v: float) -> str:
    return f"{v:.0f}" if abs(v) >= 100 or v == int(v) else f"{v:.1f}"


def _svg(w: int, h: int, body: str, label: str) -> str:
    return (f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}" '
            f'xmlns="http://www.w3.org/2000/svg" style="{FONT}">{body}</svg>')


def bar_chart(labels: list[str], values: list[float], *, title: str, unit: str = "",
              colors: list[str] | None = None, width: int = 640, height: int = 300,
              note_values: list[str] | None = None) -> str:
    """Vertical bars with value labels. `colors` may supply one colour per bar."""
    mr, mt = 14, 34
    longest = max((len(lab) for lab in labels), default=0)
    n = max(len(values), 1)
    rotate = (width - 52 - mr) / n < 6.2 * max((len(w) for lab in labels for w in lab.split(" ")), default=0)  # labels would collide
    # A rotated label ends under its bar and extends left by ~0.77 x its length (cos 40 deg x 6 px/char);
    # keep the left margin large enough that the first one stays inside the canvas.
    ml = max(52, int(0.77 * 5.4 * len(labels[0])) - 8) if rotate and labels else 52
    slot = (width - ml - mr) / n
    mb = max(96, int(longest * 4.6) + 24) if rotate else 62   # rotated text needs ~0.64 x its length of vertical room
    pw, ph = width - ml - mr, height - mt - mb
    top = _nice_max(max(values) if values else 1)
    bw = min(slot * 0.62, 70)
    out = [f'<text x="{ml}" y="20" class="ct">{escape(title)}</text>']
    for i in range(5):
        y = mt + ph - ph * i / 4
        out.append(f'<line x1="{ml}" x2="{width - mr}" y1="{y:.1f}" y2="{y:.1f}" class="gl"/>'
                   f'<text x="{ml - 6}" y="{y + 4:.1f}" class="ax" text-anchor="end">{_fmt(top * i / 4)}</text>')
    for i, (lab, v) in enumerate(zip(labels, values)):
        x = ml + slot * i + (slot - bw) / 2
        bh = ph * v / top
        col = (colors or PALETTE)[i % len(colors or PALETTE)]
        out.append(f'<rect x="{x:.1f}" y="{mt + ph - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="3" fill="{col}"/>')
        vt = note_values[i] if note_values else f"{_fmt(v)}{unit}"
        out.append(f'<text x="{x + bw / 2:.1f}" y="{mt + ph - bh - 5:.1f}" class="vl" text-anchor="middle">{escape(vt)}</text>')
        if rotate:    # one rotated line, right-aligned under the bar so it never leaves the canvas
            cx, cy = x + bw / 2, mt + ph + 12
            out.append(f'<text x="{cx:.1f}" y="{cy}" class="ax" text-anchor="end" '
                       f'transform="rotate(-40 {cx:.1f} {cy})">{escape(lab)}</text>')
            continue
        words = lab.split(" ")
        mid = len(words) // 2 if len(words) > 2 else len(words)
        for j, line in enumerate([" ".join(words[:mid]), " ".join(words[mid:])] if mid < len(words) else [lab]):
            out.append(f'<text x="{x + bw / 2:.1f}" y="{mt + ph + 16 + 13 * j}" class="ax" text-anchor="middle">{escape(line)}</text>')
    return _svg(width, height, "".join(out), title)


def hbar_stacked(labels: list[str], segments: list[list[float]], seg_names: list[str], *, title: str,
                 unit: str = "s", width: int = 720, row_h: int = 26) -> str:
    """Horizontal stacked bars: one row per label, one coloured segment per `seg_names`."""
    ml, mr = 190, 24
    per = max(1, (width - 24) // 175)                 # legend entries per line (wraps for many segments)
    legend_rows = -(-len(seg_names) // per)
    mt = 36 + 16 * legend_rows + 12
    height = mt + row_h * len(labels) + 34
    pw = width - ml - mr
    top = _nice_max(max((sum(s) for s in segments), default=1))
    out = [f'<text x="12" y="20" class="ct">{escape(title)}</text>']
    for k, name in enumerate(seg_names):
        lx, ly = 12 + (k % per) * 175, 30 + 16 * (k // per)
        out.append(f'<rect x="{lx}" y="{ly}" width="11" height="11" rx="2" fill="{PALETTE[k % len(PALETTE)]}"/>'
                   f'<text x="{lx + 16}" y="{ly + 10}" class="ax">{escape(name)}</text>')
    for i in range(5):
        x = ml + pw * i / 4
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{mt - 4}" y2="{height - 28}" class="gl"/>'
                   f'<text x="{x:.1f}" y="{height - 12}" class="ax" text-anchor="middle">{_fmt(top * i / 4)}{unit}</text>')
    for r, (lab, segs) in enumerate(zip(labels, segments)):
        y = mt + r * row_h
        out.append(f'<text x="{ml - 8}" y="{y + 15}" class="ax" text-anchor="end">{escape(lab)}</text>')
        x = ml
        for k, v in enumerate(segs):
            w = pw * v / top
            if w > 0:
                out.append(f'<rect x="{x:.1f}" y="{y + 3}" width="{w:.1f}" height="{row_h - 8}" fill="{PALETTE[k % len(PALETTE)]}"/>')
            x += w
    return _svg(width, height, "".join(out), title)


def line_chart(series: list[tuple[str, list[float], list[float]]], *, title: str, xlabel: str, ylabel: str,
               width: int = 720, height: int = 300, markers: bool = False, ymax: float | None = None) -> str:
    """Multi-series line chart. series = [(name, xs, ys), ...]."""
    ml, mr, mt, mb = 56, 20, 46, 44
    pw, ph = width - ml - mr, height - mt - mb
    xs_all = [x for _, xs, _ in series for x in xs] or [0, 1]
    ys_all = [y for _, _, ys in series for y in ys] or [0, 1]
    xmax = _nice_max(max(xs_all)) if max(xs_all) > 0 else 1
    ytop = ymax or _nice_max(max(ys_all))
    out = [f'<text x="{ml}" y="20" class="ct">{escape(title)}</text>']
    for k, (name, _, _) in enumerate(series):
        out.append(f'<rect x="{ml + k * 170}" y="28" width="11" height="3" fill="{PALETTE[k]}"/>'
                   f'<text x="{ml + 16 + k * 170}" y="33" class="ax">{escape(name)}</text>')
    for i in range(5):
        y = mt + ph - ph * i / 4
        x = ml + pw * i / 4
        out.append(f'<line x1="{ml}" x2="{width - mr}" y1="{y:.1f}" y2="{y:.1f}" class="gl"/>'
                   f'<text x="{ml - 6}" y="{y + 4:.1f}" class="ax" text-anchor="end">{_fmt(ytop * i / 4)}</text>'
                   f'<text x="{x:.1f}" y="{mt + ph + 16}" class="ax" text-anchor="middle">{_fmt(xmax * i / 4)}</text>')
    out.append(f'<text x="{ml + pw / 2}" y="{height - 6}" class="ax" text-anchor="middle">{escape(xlabel)}</text>'
               f'<text x="14" y="{mt + ph / 2}" class="ax" text-anchor="middle" transform="rotate(-90 14 {mt + ph / 2})">{escape(ylabel)}</text>')
    for k, (_, xs, ys) in enumerate(series):
        pts = " ".join(f"{ml + pw * x / xmax:.1f},{mt + ph - ph * min(y, ytop) / ytop:.1f}" for x, y in zip(xs, ys))
        if pts:
            out.append(f'<polyline points="{pts}" fill="none" stroke="{PALETTE[k]}" stroke-width="2" stroke-linejoin="round"/>')
        if markers:
            for x, y in zip(xs, ys):
                out.append(f'<circle cx="{ml + pw * x / xmax:.1f}" cy="{mt + ph - ph * min(y, ytop) / ytop:.1f}" r="3.5" fill="{PALETTE[k]}"/>')
    return _svg(width, height, "".join(out), title)


def radar_chart(axes: list[str], values: list[float], *, title: str, color: str = "var(--c0)", size: int = 300) -> str:
    """Radar/spider chart, values in 0..1."""
    pad = 45                                  # side padding so long axis labels ("World knowledge") fit
    width = size + 2 * pad
    cx, cy = width / 2, size / 2
    r = size / 2 - 62
    n = len(axes)
    ang = lambda i: -math.pi / 2 + 2 * math.pi * i / n  # noqa: E731
    out = [f'<text x="{cx}" y="16" class="ct" text-anchor="middle">{escape(title)}</text>']
    for ring in (0.25, 0.5, 0.75, 1.0):
        pts = " ".join(f"{cx + r * ring * math.cos(ang(i)):.1f},{cy + r * ring * math.sin(ang(i)):.1f}" for i in range(n))
        out.append(f'<polygon points="{pts}" fill="none" class="gl"/>')
    for i, a in enumerate(axes):
        x, y = cx + r * math.cos(ang(i)), cy + r * math.sin(ang(i))
        lx, ly = cx + (r + 12) * math.cos(ang(i)), cy + (r + 12) * math.sin(ang(i))
        anchor = "middle" if abs(math.cos(ang(i))) < 0.3 else ("start" if math.cos(ang(i)) > 0 else "end")
        short = a if len(a) < 16 else a.split(" & ")[0]
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" class="gl"/>'
                   f'<text x="{lx:.1f}" y="{ly + 4:.1f}" class="ax" text-anchor="{anchor}">{escape(short)}</text>')
    pts = " ".join(f"{cx + r * v * math.cos(ang(i)):.1f},{cy + r * v * math.sin(ang(i)):.1f}" for i, v in enumerate(values))
    out.append(f'<polygon points="{pts}" fill="{color}" fill-opacity="0.28" stroke="{color}" stroke-width="2"/>')
    return _svg(width, size, "".join(out), title)


def matrix_heatmap(rows: list[str], cols: list[str], data: list[list[float]], *, title: str,
                   width: int = 760, cell_h: int = 30) -> str:
    """Heat-map matrix with value text; data in 0..1 (opacity scale)."""
    ml, mt, mr = 150, 112, 70                 # mt leaves room for rotated headers below the title; mr for the last one
    cw = (width - ml - mr) / len(cols)
    height = mt + cell_h * len(rows) + 10
    out = [f'<text x="12" y="20" class="ct">{escape(title)}</text>']
    for j, c in enumerate(cols):
        x = ml + cw * j + cw / 2
        out.append(f'<text x="{x:.1f}" y="{mt - 8}" class="ax" text-anchor="start" '
                   f'transform="rotate(-40 {x:.1f} {mt - 8})">{escape(c)}</text>')
    for i, rname in enumerate(rows):
        y = mt + cell_h * i
        out.append(f'<text x="{ml - 8}" y="{y + cell_h / 2 + 4}" class="ax" text-anchor="end">{escape(rname)}</text>')
        for j, v in enumerate(data[i]):
            out.append(f'<rect x="{ml + cw * j + 1:.1f}" y="{y + 1}" width="{cw - 2:.1f}" height="{cell_h - 2}" rx="3" '
                       f'fill="var(--c0)" fill-opacity="{0.06 + 0.94 * v:.2f}"/>'
                       f'<text x="{ml + cw * j + cw / 2:.1f}" y="{y + cell_h / 2 + 4}" class="vl" text-anchor="middle" '
                       f'style="fill:{"#fff" if v > 0.55 else "var(--ink)"}">{v * 100:.0f}</text>')
    return _svg(width, height, "".join(out), title)


# ----------------------------------------------------------------------------- block diagrams
def diagram(nodes: dict[str, tuple[float, float, float, float, str, str]],
            edges: list[tuple[str, str, str]], *, width: int, height: int, title: str,
            kinds: dict[str, str] | None = None) -> str:
    """Block diagram.

    nodes: id -> (x, y, w, h, label, kind); label may contain '\\n' for line breaks.
    edges: (from_id, to_id, label). Edges connect the closest sides; drawn as straight arrows.
    kind selects the fill: ui | logic | ext | data | model | test (see CSS .n-<kind>).
    """
    out = ['<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"/></marker></defs>']

    def anchor(n, other):
        x, y, w, h = n[:4]
        ox, oy, ow, oh = other[:4]
        dx, dy = (ox + ow / 2) - (x + w / 2), (oy + oh / 2) - (y + h / 2)
        if abs(dx) * h > abs(dy) * w:
            return (x + w, y + h / 2) if dx > 0 else (x, y + h / 2)
        return (x + w / 2, y + h) if dy > 0 else (x + w / 2, y)

    for a, b, lab in edges:
        na, nb = nodes[a], nodes[b]
        (x1, y1), (x2, y2) = anchor(na, nb), anchor(nb, na)
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="edge" marker-end="url(#ah)"/>')
        if lab:
            out.append(f'<text x="{(x1 + x2) / 2:.1f}" y="{(y1 + y2) / 2 - 4:.1f}" class="el" text-anchor="middle">{escape(lab)}</text>')
    for nid, (x, y, w, h, label, kind) in nodes.items():
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" class="n n-{kind}"/>')
        lines = label.split("\n")
        y0 = y + h / 2 - (len(lines) - 1) * 7 + 4
        for i, ln in enumerate(lines):
            cls = "nt" if i == 0 else "ns"
            out.append(f'<text x="{x + w / 2}" y="{y0 + i * 14:.1f}" class="{cls}" text-anchor="middle">{escape(ln)}</text>')
    return _svg(width, height, "".join(out), title)


def sequence_diagram(actors: list[str], messages: list[tuple[int, int, str]], *, title: str,
                     width: int = 860, step: int = 34) -> str:
    """Simple sequence diagram. messages = (from_idx, to_idx, text); dashed when from > to (return)."""
    n = len(actors)
    top, height = 52, 52 + step * (len(messages) + 1) + 20
    xs = [width / n * (i + 0.5) for i in range(n)]
    out = ['<defs><marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"/></marker></defs>']
    for i, a in enumerate(actors):
        out.append(f'<rect x="{xs[i] - 70:.1f}" y="10" width="140" height="28" rx="6" class="n n-logic"/>'
                   f'<text x="{xs[i]:.1f}" y="29" class="nt" text-anchor="middle">{escape(a)}</text>'
                   f'<line x1="{xs[i]:.1f}" x2="{xs[i]:.1f}" y1="38" y2="{height - 8}" class="gl" stroke-dasharray="4 4"/>')
    for k, (a, b, text) in enumerate(messages):
        y = top + step * (k + 1) - 6
        dash = ' stroke-dasharray="5 4"' if a > b else ""
        if a == b:
            out.append(f'<path d="M{xs[a]:.1f},{y - 8} h30 v16 h-30" fill="none" class="edge" marker-end="url(#ah2)"/>'
                       f'<text x="{xs[a] + 36:.1f}" y="{y + 4}" class="el">{escape(text)}</text>')
        else:
            out.append(f'<line x1="{xs[a]:.1f}" y1="{y}" x2="{xs[b]:.1f}" y2="{y}" class="edge"{dash} marker-end="url(#ah2)"/>'
                       f'<text x="{(xs[a] + xs[b]) / 2:.1f}" y="{y - 5}" class="el" text-anchor="middle">{escape(text)}</text>')
    return _svg(width, height, "".join(out), title)


def expert_grid(selected: list[int], groups: list[str], *, title: str, n_experts: int = 128,
                per_row: int = 16, width: int = 760, cell_h: int = 24) -> str:
    """The 128 experts as an 8 x 16 grid (one row per group); `selected` ids are filled and numbered."""
    ml, mt = 160, 34
    cw = (width - ml - 10) / per_row
    rows = n_experts // per_row
    height = mt + cell_h * rows + 10
    out = [f'<text x="12" y="20" class="ct">{escape(title)}</text>']
    chosen = set(selected)
    for r in range(rows):
        y = mt + r * cell_h
        out.append(f'<text x="{ml - 8}" y="{y + cell_h / 2 + 4}" class="ax" text-anchor="end">{escape(groups[r % len(groups)])}</text>')
        for c in range(per_row):
            e = r * per_row + c
            x = ml + c * cw
            if e in chosen:
                out.append(f'<rect x="{x + 1:.1f}" y="{y + 1}" width="{cw - 2:.1f}" height="{cell_h - 2}" rx="3" '
                           f'fill="{PALETTE[r % len(PALETTE)]}"/><text x="{x + cw / 2:.1f}" y="{y + cell_h / 2 + 4}" '
                           f'class="vl" text-anchor="middle" style="fill:#fff">{e}</text>')
            else:
                out.append(f'<rect x="{x + 1:.1f}" y="{y + 1}" width="{cw - 2:.1f}" height="{cell_h - 2}" rx="3" '
                           f'fill="var(--grid)" fill-opacity=".7"/>')
    return _svg(width, height, "".join(out), title)
