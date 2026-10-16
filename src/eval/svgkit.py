"""
svgkit.py - dependency-free SVG drawing for Phase 4.3.

WHY SVG AND NOT PNG

The plan asks for matplotlib charts. matplotlib is not installed, numpy is not
installed, and none of them can be. That rules out PNG for a practical reason as
well as a technical one: a raster chart needs a font rasteriser to draw text, and
every PNG path here would mean implementing one.

SVG needs neither. It is text, so the renderer draws the type, the output stays
crisp at any size, it diffs and greps, and GitHub renders it directly in a
README. The file is inspectable, which matters here for a reason beyond taste:
a chart in a benchmark submission should be something a reader can check.

The trade-off is that some video tools want raster input. If that bites, the
fix is a browser source, not reimplementing a text rasteriser.

WHAT THIS MODULE DELIBERATELY DOES NOT DO

No colour scales. A heatmap of 36 per-category scores is a machine for
manufacturing false signal: at n=6 a category scoring 0% has a 95% interval of
[0, 39] and one scoring 100% has [61, 100], so a red-to-green ramp would render
indistinguishable-from-anything as a confident gradient. Bars here carry their
intervals, and anything that cannot support an interval is not drawn as a
finding.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field

# Swiss-inspired: red for the smaller model, blue for the larger, neutral greys
# for everything that is not a claim.
RED = "#E63946"
RED_LIGHT = "#F4A6AB"
BLUE = "#457B9D"
BLUE_LIGHT = "#A8C8DA"
INK = "#1F2933"
MUTED = "#7B8794"
GRID = "#E4E7EB"
WARN = "#B45309"
BAND = "#FDF6E3"

FONT = ("ui-sans-serif, -apple-system, 'Segoe UI', Roboto, "
        "'Helvetica Neue', Arial, sans-serif")
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


@dataclass
class Canvas:
    """An SVG document built by appending elements. Units are pixels."""
    width: int
    height: int
    title: str = ""
    desc: str = ""
    body: list[str] = field(default_factory=list)

    # ------------------------------------------------------------ primitives
    def rect(self, x, y, w, h, fill="none", stroke="none", rx=0,
             opacity=1.0, sw=1) -> "Canvas":
        self.body.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(0, w):.2f}" '
            f'height="{max(0, h):.2f}" rx="{rx}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}" opacity="{opacity}"/>')
        return self

    def line(self, x1, y1, x2, y2, stroke=GRID, sw=1, dash=None, cap="butt") -> "Canvas":
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.body.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}"{d}/>')
        return self

    def text(self, x, y, s, size=12, fill=INK, weight="normal", anchor="start",
             family=FONT, opacity=1.0, style="") -> "Canvas":
        st = f' font-style="{style}"' if style != "normal" else ""
        self.body.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-family="{family}" '
            f'font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" opacity="{opacity}"{st}>{esc(s)}</text>')
        return self

    def text_rot(self, x, y, s, size=12, fill=INK, weight="normal",
                 angle=-90) -> "Canvas":
        """Rotated text, for axis titles.

        Done here rather than by rewriting the element string after the fact,
        which is how the first version of the y-label worked and which would
        break silently the moment the attribute order changed.
        """
        self.body.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FONT}" '
            f'font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="middle" transform="rotate({angle} {x:.2f} {y:.2f})">'
            f'{esc(s)}</text>')
        return self

    def path(self, d, fill="none", stroke=INK, sw=2, cap="round", join="round",
             dash=None) -> "Canvas":
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.body.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-linecap="{cap}" stroke-linejoin="{join}"{da}/>')
        return self

    def circle(self, cx, cy, r, fill=INK, stroke="none", sw=1, opacity=1.0) -> "Canvas":
        self.body.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>')
        return self

    def group(self, inner: str, transform: str = "", opacity: float = 1.0) -> "Canvas":
        t = f' transform="{transform}"' if transform else ""
        self.body.append(f'<g{t} opacity="{opacity}">{inner}</g>')
        return self

    # ------------------------------------------------------------- rendering
    def render(self) -> str:
        a11y = ""
        if self.title:
            a11y += f"<title>{esc(self.title)}</title>"
        if self.desc:
            a11y += f"<desc>{esc(self.desc)}</desc>"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
            f'height="{self.height}" viewBox="0 0 {self.width} {self.height}" '
            f'role="img" aria-labelledby="t" font-family="{FONT}">'
            f'<title id="t">{esc(self.title)}</title>'
            f'{f"<desc>{esc(self.desc)}</desc>" if self.desc else ""}'
            f'<rect width="{self.width}" height="{self.height}" fill="#FFFFFF"/>'
            f'{"".join(self.body)}</svg>\n')

    def save(self, path) -> str:
        """
        Write the SVG and return the path as a string.

        Returns a path, not self. Chaining `.save()` and expecting a Canvas back
        reads fine until something asks for the filename, which is what the
        index generator does - and it failed with a confusing attribute error
        rather than at the call site.
        """
        target = str(path)
        if not target.endswith(".svg"):
            target = target.replace(".png", "") + ".svg"
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(self.render())
        return target


# ============================================================== scale + axes
@dataclass
class Scale:
    """Map a data value to a pixel coordinate."""
    d0: float
    d1: float
    p0: float
    p1: float

    def __call__(self, v: float) -> float:
        span = self.d1 - self.d0
        if span == 0:
            return (self.p0 + self.p1) / 2
        return self.p0 + (v - self.d0) / span * (self.p1 - self.p0)

    def invert(self, px: float) -> float:
        span = self.p1 - self.p0
        if span == 0:
            return self.d0
        return self.d0 + (px - self.p0) / span * (self.d1 - self.d0)


class Plot:
    """A framed plotting area with a linear y-axis."""

    def __init__(self, c: Canvas, x0, y0, x1, y1, ymin, ymax, ticks=None,
                 ylabel="", ytick_fmt="{:.0f}"):
        self.c, self.x0, self.y0, self.x1, self.y1 = c, x0, y0, x1, y1
        self.ys = Scale(ymin, ymax, y1, y0)          # data y -> pixels (inverted)
        self.xs = Scale(0, 1, x0, x1)
        self.ymin, self.ymax = ymin, ymax
        self.ytick_fmt = ytick_fmt
        self.ylabel = ylabel

        for t in (ticks if ticks is not None else self._default_ticks()):
            py = self.ys(t)
            if not (y0 - 1 <= py <= y1 + 1):
                continue
            c.line(x0, py, x1, py, GRID, 1)
            c.text(x0 - 8, py + 4, ytick_fmt.format(t), 11, MUTED, anchor="end")
        c.line(x0, y0, x0, y1, INK, 1.2)
        c.line(x0, y1, x1, y1, INK, 1.2)
        if ylabel:
            c.text_rot(x0 - 52, (y0 + y1) / 2, ylabel, 11, MUTED)

    def _default_ticks(self) -> list[float]:
        span = self.ymax - self.ymin
        step = 10 if span <= 100 else 20
        out, t = [], self.ymin
        while t <= self.ymax + 1e-9:
            out.append(round(t, 6))
            t += step
        return out

    # ------------------------------------------------------------- elements
    def hline(self, value: float, label: str = "", color: str = WARN,
              dash: str = "4 3") -> None:
        py = self.ys(value)
        self.c.line(self.x0, py, self.x1, py, color, 1.4, dash)
        if label:
            self.c.text(self.x1 - 4, py - 6, label, 11, color, "bold", anchor="end")

    def band(self, lo: float, hi: float, color: str = BAND) -> None:
        """A shaded region - used for 'cannot be distinguished' spans."""
        self.c.rect(self.x0, self.ys(hi), self.x1 - self.x0,
                    self.ys(lo) - self.ys(hi), fill=color, stroke="none")

    def bar(self, centre: float, value: float, width: float, fill: str,
            lo: float | None = None, hi: float | None = None,
            outline: str | None = None) -> None:
        """A bar, with its interval drawn as a capped whisker if supplied."""
        top, bot = self.ys(value), self.ys(0)
        self.c.rect(centre - width / 2, top, width, bot - top, fill=fill,
                    stroke=outline or "none", sw=1.4, rx=2)
        if lo is not None and hi is not None:
            cx = centre
            ylo, yhi = self.ys(lo), self.ys(hi)
            self.c.line(cx, yhi, cx, ylo, INK, 1.3)
            cap = width * 0.32
            self.c.line(cx - cap, yhi, cx + cap, yhi, INK, 1.3)
            self.c.line(cx - cap, ylo, cx + cap, ylo, INK, 1.3)

    def dot(self, centre: float, value: float, r: float = 5, fill: str = INK) -> None:
        self.c.circle(centre, self.ys(value), r, fill=fill, stroke="#FFFFFF", sw=1.5)

    def xlabels(self, items, size=11, dy=18) -> None:
        for px, label, *rest in items:
            weight = rest[0] if rest else "normal"
            self.c.text(px, self.y1 + dy, label, size, INK, weight, anchor="middle")

    def legend(self, entries, x=None, y=None, gap=150) -> None:
        """entries: [(colour, label), ...]"""
        x = self.x0 + 8 if x is None else x
        y = self.y0 + 4 if y is None else y
        for i, (colour, label) in enumerate(entries):
            self.c.rect(x + i * gap, y, 11, 11, fill=colour, rx=2)
            self.c.text(x + i * gap + 17, y + 10, label, 11, INK)


def header(c: Canvas, title: str, subtitle: str = "", n_note: str = "") -> None:
    c.text(48, 40, title, 19, INK, "bold")
    if subtitle:
        c.text(48, 62, subtitle, 12.5, MUTED)
    if n_note:
        c.text(48, 80, n_note, 11, MUTED, family=MONO)


def caveat(c: Canvas, lines, y=None, width=1000) -> None:
    """
    The honesty block that belongs on the chart itself.

    A caveat in a caption is read after the number. A caveat drawn into the
    figure is read with it. At n=6 a category scoring 0% and one scoring 100%
    have intervals that overlap almost everything, so a chart that omits this
    is not merely incomplete - it inverts what the reader takes away.
    """
    y = c.height - 20 - 16 * len(lines) if y is None else y
    for i, line in enumerate(lines):
        c.text(48, y + 16 * i, line, 10.5, WARN if i == 0 else MUTED,
               "bold" if i == 0 else "normal")


def watermark(c: Canvas, msg: str) -> None:
    """A diagonal stamp, for artefacts generated from unusable data."""
    body = (f'<g transform="rotate(-24 {c.width / 2} {c.height / 2})" '
            f'opacity="0.10">'
            f'<text x="{c.width / 2}" y="{c.height / 2}" font-family="{FONT}" '
            f'font-size="64" font-weight="bold" fill="{RED}" '
            f'text-anchor="middle">{esc(msg)}</text></g>')
    c.body.append(body)
