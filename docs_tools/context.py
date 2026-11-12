"""Build context shared by all chapters: figure numbering, cross-references, TOC registry, tables.

The document is rendered twice. Pass 1 only collects labels ("Figure 3-2") and section titles;
pass 2 renders with those labels known, in strict mode, so a cross-reference to an unknown
figure or section raises immediately instead of producing a dead link.
"""
from __future__ import annotations

from html import escape

from . import data, theme


CHAPTERS = [(1, "Technical Architecture"), (2, "GUI Implementation"), (3, "Engine & Integration"),
            (4, "Expert System"), (5, "Testing & Validation"), (6, "Deployment & Usage"),
            (7, "Performance Metrics"), (8, "Troubleshooting & Configuration")]


class Raw(str):
    """Marks a string as trusted HTML so `table()` does not escape it."""


def code_inline(text: str) -> Raw:
    return Raw(f"<code>{escape(text)}</code>")


_INLINE = ("code", "b", "i", "em")


def rich(text: str) -> str:
    """Escape `text`, then restore a small whitelist of inline tags (<code>, <b>, <i>, <em>)."""
    out = escape(text)
    for t in _INLINE:
        out = out.replace(f"&lt;{t}&gt;", f"<{t}>").replace(f"&lt;/{t}&gt;", f"</{t}>")
    return out


def table(headers: list[str], rows: list[list], *, num_cols: tuple[int, ...] = (), caption: str = "") -> str:
    """HTML table. Cells are escaped unless they are `Raw`. `num_cols` right-aligns numeric columns."""
    def cell(tag: str, i: int, v) -> str:
        cls = ' class="n"' if i in num_cols else ""
        return f"<{tag}{cls}>{v if isinstance(v, Raw) else rich(str(v))}</{tag}>"
    head = "".join(cell("th", i, h) for i, h in enumerate(headers))
    body = "".join("<tr>" + "".join(cell("td", i, v) for i, v in enumerate(r)) + "</tr>" for r in rows)
    cap = f"<caption>{escape(caption)}</caption>" if caption else ""
    return f"<table>{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def kpis(items: list[tuple[str, str]]) -> str:
    """Row of KPI tiles: (big value, small label)."""
    return '<div class="kpis">' + "".join(
        f'<div class="kpi"><b>{escape(v)}</b><span>{escape(label)}</span></div>' for v, label in items) + "</div>"


def grid2(*figures: str) -> str:
    return '<div class="grid2">' + "".join(figures) + "</div>"


def legend_key() -> str:
    """Explains the five figure styles used throughout the document."""
    items = [("DIAGRAM", "var(--k-diagram)", "technical structure / flow"),
             ("SCREENSHOT", "var(--k-shot)", "real capture of the running GUI, numbered pins"),
             ("TERMINAL CAPTURE", "#30363d", "verbatim command output"),
             ("MEASURED DATA", "var(--k-chart)", "charts drawn from benchmark.json"),
             ("CONCEPT", "var(--k-concept)", "explanatory graphic (not telemetry)")]
    return '<div class="legend-key">' + "".join(
        f'<span style="background:{c}">{escape(n)}</span><em style="margin-right:12px">{escape(d)}</em>'
        for n, c, d in items) + "</div>"


class Ctx:
    def __init__(self, labels: dict[str, str] | None = None, strict: bool = False,
                 titles: dict[str, str] | None = None) -> None:
        self.labels = labels or {}
        self.titles = titles or {}      # section anchor -> title, collected in pass 1
        self.strict = strict
        self.new_labels: dict[str, str] = {}
        self.captions: dict[str, str] = {}
        self.sections: list[tuple[int, str, str]] = []   # (chapter, anchor id, title)
        self.chapter = 0
        self._n = 0

    # ------------------------------------------------------------------ structure
    def start(self, chapter: int) -> None:
        self.chapter, self._n = chapter, 0

    def h3(self, key: str, title: str) -> str:
        anchor = f"s{self.chapter}-{key}"
        self.sections.append((self.chapter, anchor, title))
        return f'<h3 id="{anchor}">{self.chapter}.{sum(1 for c, _, _ in self.sections if c == self.chapter)} {escape(title)}</h3>'

    def head(self, n: int, lead: str) -> str:
        title = dict(CHAPTERS)[n]
        return (f'<div class="crumb">Chapter {n} of {len(CHAPTERS)}</div>'
                f'<h2 class="chapter" id="ch{n}"><span class="cn">{n}</span>{escape(title)}</h2>'
                f'<p class="lead">{lead}</p>')

    # ------------------------------------------------------------------ references
    def xref(self, target: str, text: str | None = None) -> str:
        """Link to a figure id (`fig-...`), a section anchor (`s3-...`) or a chapter (`ch3`)."""
        if target.startswith("ch"):
            label = text or f"Chapter {target[2:]}"
        elif target.startswith("fig-"):
            label = text or self.labels.get(target)
            if label is None:
                if self.strict:
                    raise KeyError(f"unknown figure reference: {target}")
                label = target
        else:
            titles = {**self.titles, **{a: t for _, a, t in self.sections}}
            label = text or titles.get(target)
            if label is None:
                if self.strict:
                    raise KeyError(f"unknown section reference: {target}")
                label = target
        return Raw(f'<a class="xref" href="#{escape(target)}">{escape(label)}</a>')

    # ------------------------------------------------------------------ figures
    def _label(self, fig_id: str, caption: str = "") -> str:
        self._n += 1
        self.captions[fig_id] = caption
        label = f"Figure {self.chapter}-{self._n}"
        if fig_id in self.new_labels:
            raise ValueError(f"duplicate figure id: {fig_id}")
        self.new_labels[fig_id] = label
        return label

    def fig(self, kind: str, fig_id: str, caption: str, body: str) -> str:
        return theme.figure(kind, fig_id, caption, body, label=self._label(fig_id, caption))

    def term(self, fig_id: str, caption: str, title: str, text: str) -> str:
        return self.fig("term", fig_id, caption, theme.term_block(title, text))

    def shot(self, fig_id: str, caption: str, filename: str, pins=None, boxes=None, url: str | None = None) -> str:
        src = data.image_data_uri(str(data.shot_path(filename)))
        return theme.shot(fig_id, caption, src, pins, boxes, url=url, alt=caption, label=self._label(fig_id, caption))

    def evidence(self, name: str) -> str:
        """Raw text of a captured command output (Docs/assets/data/<name>)."""
        text = data.read_text(data.DATA / name)
        return text if text else f"(capture {name} not found - run scripts/capture_evidence.sh)\n"
