"""Stylesheet and small HTML primitives for the documentation.

Visual language (so readers can tell the figure types apart at a glance):
  * Technical diagram   - blue left border, label "DIAGRAM"      (`figure.diagram`)
  * Functional screenshot - green border + browser chrome, "SCREENSHOT" (`figure.shot`)
  * Terminal capture    - dark block, "TERMINAL CAPTURE"          (`figure.term`)
  * Data chart (measured) - amber border, "MEASURED DATA"          (`figure.chart`)
  * Explanatory graphic - purple border, "CONCEPT"                 (`figure.concept`)
"""
from __future__ import annotations

import re
from html import escape

CSS = r"""
:root{--font:-apple-system,"Segoe UI",Inter,system-ui,sans-serif;--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
--bg:#fff;--surface:#f6f8fa;--border:#d8dee4;--ink:#1f2328;--muted:#59636e;--grid:#e3e7eb;--accent:#0f62fe;
--c0:#0f62fe;--c1:#8a3ffc;--c2:#d02670;--c3:#198038;--c4:#b28600;--c5:#005d5d;--c6:#fa4d56;--c7:#6f6f6f;
--k-diagram:#0f62fe;--k-shot:#198038;--k-term:#161b22;--k-chart:#b28600;--k-concept:#8a3ffc}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font:15px/1.65 var(--font);color:var(--ink);background:var(--bg)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
code,pre,kbd{font-family:var(--mono)}code{background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:0 4px;font-size:.88em}
.layout{display:grid;grid-template-columns:290px minmax(0,1fr)}
nav.side{position:sticky;top:0;height:100vh;overflow:auto;padding:22px 18px;background:var(--surface);border-right:1px solid var(--border);font-size:13.5px}
nav.side .brand{font-weight:700;font-size:15px;margin-bottom:2px}nav.side .sub{color:var(--muted);font-size:12px;margin-bottom:16px}
nav.side ol{list-style:none;margin:0;padding:0}nav.side li a{display:block;padding:5px 8px;border-radius:6px;color:var(--ink)}
nav.side li a:hover{background:#e8eef9;text-decoration:none}nav.side li.sec a{margin-left:14px;color:var(--muted);font-size:12.5px;padding:2px 8px}
nav.side .num{display:inline-block;width:22px;color:var(--accent);font-weight:700}
main{padding:0 56px 80px;max-width:1120px;width:100%}
.cover{min-height:92vh;display:flex;flex-direction:column;justify-content:center;border-bottom:3px solid var(--accent);margin:0 -56px 40px;padding:40px 56px;
background:linear-gradient(135deg,#0b1f4d 0%,#0f62fe 100%);color:#fff}
.cover h1{font-size:2.5rem;line-height:1.15;margin:0 0 8px}.cover .tag{font-size:1.1rem;opacity:.9;margin-bottom:28px}
.cover .kicker{letter-spacing:.14em;text-transform:uppercase;font-size:.78rem;opacity:.8;margin-bottom:12px}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin:18px 0;max-width:860px}
.meta div{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:8px;padding:8px 12px}
.meta b{display:block;font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;opacity:.75;font-weight:600}
.cover a.btn{display:inline-block;margin-top:22px;background:#fff;color:#0f62fe;padding:9px 18px;border-radius:8px;font-weight:600}
h2.chapter{margin:64px 0 8px;font-size:1.9rem;padding-top:20px;border-top:2px solid var(--border)}
h2.chapter .cn{color:var(--accent);margin-right:10px}
h3{margin:34px 0 8px;font-size:1.25rem}h4{margin:20px 0 6px}
.lead{font-size:1.05rem;color:var(--muted);margin-top:0}
.pager{display:flex;justify-content:space-between;gap:12px;margin:46px 0 0;font-size:13.5px}
.pager a{border:1px solid var(--border);border-radius:8px;padding:6px 12px;background:var(--surface)}
.crumb{font-size:12.5px;color:var(--muted)}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:14px}
th,td{border:1px solid var(--border);padding:6px 10px;text-align:left;vertical-align:top}th{background:var(--surface)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
pre{background:#0d1117;color:#e6edf3;border-radius:8px;padding:14px 16px;overflow:auto;font-size:12.8px;line-height:1.5;margin:10px 0}
pre code{background:none;border:0;border-radius:0;padding:0;font-size:inherit;color:inherit}
pre .k{color:#ff7b72}pre .s{color:#a5d6ff}pre .c{color:#8b949e}pre .f{color:#d2a8ff}pre .n{color:#79c0ff}
.codecap{font-size:12px;color:var(--muted);margin:14px 0 -4px;font-family:var(--mono)}
.callout{border-left:4px solid var(--accent);background:#eef4ff;padding:10px 14px;border-radius:0 8px 8px 0;margin:16px 0}
.callout.warn{border-color:#b28600;background:#fff8e1}.callout.ok{border-color:#198038;background:#eaf7ee}.callout.bad{border-color:#da1e28;background:#fff1f1}
.callout b.t{display:block;font-size:.78rem;letter-spacing:.06em;text-transform:uppercase}
figure{margin:22px 0;border:1px solid var(--border);border-radius:10px;overflow:hidden;background:#fff}
figure figcaption{padding:9px 14px;font-size:13px;color:var(--muted);background:var(--surface);border-top:1px solid var(--border)}
figure figcaption b{color:var(--ink)}
figure .badge{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.09em;padding:1px 7px;border-radius:4px;color:#fff;margin-right:8px;vertical-align:1px}
figure.diagram{border-left:5px solid var(--k-diagram)}figure.diagram .badge{background:var(--k-diagram)}
figure.shot{border:2px solid var(--k-shot)}figure.shot .badge{background:var(--k-shot)}
figure.term{border:1px solid #30363d}figure.term .badge{background:#30363d}
figure.chart{border-left:5px solid var(--k-chart)}figure.chart .badge{background:var(--k-chart)}
figure.concept{border-left:5px solid var(--k-concept);border-style:dashed dashed dashed solid}figure.concept .badge{background:var(--k-concept)}
.fig-body{padding:14px;overflow:auto}.fig-body svg.chart,.fig-body svg{max-width:100%;height:auto;display:block;margin:auto}
svg .ct{font-size:13px;font-weight:700;fill:var(--ink)}svg .ax{font-size:11px;fill:var(--muted)}svg .vl{font-size:11px;font-weight:600;fill:var(--ink)}
svg .gl{stroke:var(--grid);stroke-width:1;fill:none}svg .edge{stroke:var(--muted);stroke-width:1.5;fill:none}svg .el{font-size:10.5px;fill:var(--muted)}
svg .n{stroke-width:1.5}svg .nt{font-size:12px;font-weight:700;fill:var(--ink)}svg .ns{font-size:10.5px;fill:var(--muted)}
svg .n-ui{fill:#e5f0ff;stroke:#0f62fe}svg .n-logic{fill:#f3ecff;stroke:#8a3ffc}svg .n-ext{fill:#fff4e0;stroke:#b28600}
svg .n-data{fill:#e8f6ec;stroke:#198038}svg .n-model{fill:#ffe9ef;stroke:#d02670}svg .n-test{fill:#e3f6f4;stroke:#005d5d}
.browser{border-bottom:1px solid var(--border);background:#eceff3;padding:7px 12px;display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}
.browser i{width:10px;height:10px;border-radius:50%;background:#ff5f57;display:inline-block}.browser i:nth-child(2){background:#febc2e}.browser i:nth-child(3){background:#28c840}
.browser span{margin-left:10px;background:#fff;border:1px solid var(--border);border-radius:5px;padding:1px 10px;flex:1;font-family:var(--mono)}
.shotwrap{position:relative;line-height:0;background:#111}.shotwrap img{width:100%;height:auto;display:block}
.pin{position:absolute;transform:translate(-50%,-50%);width:26px;height:26px;border-radius:50%;background:#da1e28;color:#fff;font:700 13px/26px var(--font);
text-align:center;border:2px solid #fff;box-shadow:0 0 0 2px #da1e28}
.box{position:absolute;border:2px solid #fa4d56;border-radius:6px;background:rgba(250,77,86,.07)}
ol.legend{margin:10px 0 0;padding:0 0 0 0;list-style:none;font-size:13.5px;line-height:1.5}
ol.legend li{display:flex;gap:8px;margin:3px 0}ol.legend li b.p{flex:none;width:22px;height:22px;border-radius:50%;background:#da1e28;color:#fff;text-align:center;font-size:12px;line-height:22px}
.term .bar{background:#21262d;color:#8b949e;padding:6px 12px;font:12px var(--mono);display:flex;gap:6px;align-items:center}
.term .bar i{width:10px;height:10px;border-radius:50%;background:#ff5f57;display:inline-block}.term .bar i:nth-child(2){background:#febc2e}.term .bar i:nth-child(3){background:#28c840}
.term pre{margin:0;border-radius:0;max-height:560px}.term .ok{color:#3fb950}.term .bad{color:#ff7b72}.term .dim{color:#8b949e}.term .cmd{color:#79c0ff}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}.grid2 figure{margin:10px 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:16px 0}
.kpi{border:1px solid var(--border);border-radius:10px;padding:10px 12px;background:var(--surface)}
.kpi b{display:block;font-size:1.5rem;line-height:1.2}.kpi span{font-size:.78rem;color:var(--muted)}
.legend-key{display:flex;flex-wrap:wrap;gap:8px;font-size:12.5px;margin:10px 0}
.legend-key span{border-radius:5px;padding:2px 9px;color:#fff;font-weight:600}
details{border:1px solid var(--border);border-radius:8px;padding:6px 12px;margin:10px 0;background:var(--surface)}summary{cursor:pointer;font-weight:600}
.xref{white-space:nowrap}
footer{margin-top:60px;padding-top:14px;border-top:1px solid var(--border);color:var(--muted);font-size:12.5px;text-align:center}
@media(max-width:980px){.layout{grid-template-columns:1fr}nav.side{position:static;height:auto}main{padding:0 20px 60px}.cover{margin:0 -20px 30px;padding:30px 20px}}
@media print{nav.side,.pager{display:none}.layout{display:block}figure,pre,table{break-inside:avoid}main{padding:0}.cover{min-height:auto}}
"""

_KINDS = {"diagram": "DIAGRAM", "shot": "SCREENSHOT", "term": "TERMINAL CAPTURE",
          "chart": "MEASURED DATA", "concept": "CONCEPT"}


def figure(kind: str, fig_id: str, caption: str, body: str, *, url: str | None = None,
           label: str | None = None) -> str:
    """Wrap `body` (already-safe HTML) in a typed, captioned figure. `caption` is plain text.

    `label` is the visible number, e.g. "Figure 3-2" (defaults to the id)."""
    if kind not in _KINDS:
        raise ValueError(f"unknown figure kind: {kind}")
    chrome = ""
    if kind == "shot":
        chrome = f'<div class="browser"><i></i><i></i><i></i><span>{escape(url or "http://localhost:8501")}</span></div>'
    inner = body if kind in ("shot", "term") else f'<div class="fig-body">{body}</div>'
    return (f'<figure class="{kind}" id="{escape(fig_id)}">{chrome}{inner}'
            f'<figcaption><span class="badge">{_KINDS[kind]}</span><b>{escape(label or fig_id)}.</b> '
            f'{escape(caption)}</figcaption></figure>')


def callout(kind: str, title: str, text_html: str) -> str:
    cls = {"note": "", "warn": " warn", "ok": " ok", "bad": " bad"}[kind]
    return f'<div class="callout{cls}"><b class="t">{escape(title)}</b>{text_html}</div>'


_GOOD = re.compile(r"\b(PASSED|passed|PASS|OK|ok|HTTP 200|exit 0|EXIT=0)\b")
_BAD = re.compile(r"\b(FAILED|FAIL|failed|Error|ERROR|UNTESTED|VIOLATION)\b")


def term_block(title: str, text: str) -> str:
    """Terminal capture body from raw command output. Colours pass/fail words; everything is escaped first."""
    out = []
    for line in text.rstrip("\n").splitlines():
        e = escape(line)
        if line.startswith("$ "):
            e = f'<span class="cmd">{e}</span>'
        elif _BAD.search(line):
            e = f'<span class="bad">{e}</span>'
        elif _GOOD.search(line):
            e = f'<span class="ok">{e}</span>'
        out.append(e)
    return (f'<div class="bar"><i></i><i></i><i></i><span>{escape(title)}</span></div>'
            f'<pre>{chr(10).join(out)}</pre>')


def shot(fig_id: str, caption: str, img_src: str, pins: list[tuple[float, float, str]] | None = None,
         boxes: list[tuple[float, float, float, float]] | None = None, url: str | None = None,
         alt: str = "", label: str | None = None) -> str:
    """Screenshot with numbered pins (x%, y%, text) and optional highlight boxes (x%, y%, w%, h%)."""
    overlay = "".join(f'<div class="box" style="left:{x}%;top:{y}%;width:{w}%;height:{h}%"></div>' for x, y, w, h in boxes or [])
    overlay += "".join(f'<div class="pin" style="left:{x}%;top:{y}%">{i}</div>' for i, (x, y, _) in enumerate(pins or [], 1))
    body = f'<div class="shotwrap"><img src="{escape(img_src)}" alt="{escape(alt or caption)}" loading="lazy">{overlay}</div>'
    legend = ""
    if pins:
        legend = ('<div class="fig-body"><ol class="legend">' +
                  "".join(f'<li><b class="p">{i}</b><span>{t}</span></li>' for i, (_, _, t) in enumerate(pins, 1)) +
                  "</ol></div>")
    return figure("shot", fig_id, caption, body + legend, url=url, label=label)


def highlight_python(src: str) -> str:
    """Very small, safe Python highlighter (keywords, strings, comments) for code listings."""
    kw = r"\b(def|class|return|if|elif|else|for|while|in|not|and|or|import|from|as|try|except|finally|raise|with|yield|None|True|False|lambda|pass|continue|break|is)\b"
    tok = re.compile(r'(?P<c>#[^\n]*)|(?P<s>"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"\n]*"|\'[^\'\n]*\')|(?P<k>' + kw + r')|(?P<n>\b\d[\d_.]*\b)')
    out, pos = [], 0
    for m in tok.finditer(src):
        out.append(escape(src[pos:m.start()]))
        cls = m.lastgroup if m.lastgroup in ("c", "s", "n") else "k"
        out.append(f'<span class="{cls}">{escape(m.group(0))}</span>')
        pos = m.end()
    out.append(escape(src[pos:]))
    return "".join(out)


def code(src: str, caption: str = "", lang: str = "python") -> str:
    body = highlight_python(src) if lang == "python" else escape(src)
    cap = f'<div class="codecap">{escape(caption)}</div>' if caption else ""
    return f'{cap}<pre><code>{body}</code></pre>'
