"""Deterministic, dependency-free SVG assets generated only from committed public data.

Every asset is rendered twice (light and dark) from the same geometry. Charts plot
observed snapshots on a date-scaled axis; stepped lines hold the last observed
value and never interpolate. Run ``--check`` to confirm the committed assets
match the committed data.
"""

import argparse
import csv
import math
from datetime import date
from html import escape
from pathlib import Path

from synthetic_scene import findings, scenes

ROOT = Path(__file__).resolve().parents[1]
WIDTH = 900
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

PALETTES = {
    "dark": dict(
        bg="#0B1020", panel="#111A2E", panel2="#0E1527", edge="#243149", grid="#182338",
        text="#F8FAFC", muted="#A9B6CB", faint="#94A3B8",
        accent="#7C83FF", mint="#5EEBC4", cyan="#6DD5FA", rose="#FB7185",
    ),
    "light": dict(
        bg="#F8FAFC", panel="#FFFFFF", panel2="#F1F5F9", edge="#CBD5E1", grid="#E2E8F0",
        text="#0B1020", muted="#475569", faint="#59677B",
        accent="#4F46E5", mint="#087A64", cyan="#036D9E", rose="#E11D48",
    ),
}


def text_width(value, size):
    """Rough width of a sans-serif string; used only for chip sizing."""
    return len(str(value)) * size * 0.58


class Canvas:
    """Tiny SVG builder. Colours are palette keys, never literals, so both themes agree."""

    def __init__(self, theme, height, title, desc):
        self.p = PALETTES[theme]
        self.theme = theme
        self.height = height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
            f'viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(desc)}</desc>',
            f'<g font-family="{FONT}">',
        ]
        self.rect(0, 0, WIDTH, height, "bg", radius=18)

    # -- primitives -------------------------------------------------------
    def raw(self, fragment):
        self.parts.append(fragment)

    def text(self, x, y, value, size=14, color="text", weight=400, anchor="start", mono=False, spacing=None, opacity=None):
        extra = f' font-family="{MONO}"' if mono else ""
        if spacing is not None:
            extra += f' letter-spacing="{spacing}"'
        if opacity is not None:
            extra += f' opacity="{opacity}"'
        self.parts.append(
            f'<text x="{fmt(x)}" y="{fmt(y)}" fill="{self.p[color]}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}"{extra}>{escape(str(value))}</text>'
        )

    def rect(self, x, y, w, h, fill="panel", stroke=None, radius=8, width=1, dash=None, opacity=None):
        attrs = f' stroke="{self.p[stroke]}" stroke-width="{width}"' if stroke else ""
        if dash:
            attrs += f' stroke-dasharray="{dash}"'
        if opacity is not None:
            attrs += f' opacity="{opacity}"'
        fill_value = "none" if fill is None else self.p[fill]
        self.parts.append(
            f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{radius}" fill="{fill_value}"{attrs}/>'
        )

    def path(self, d, color="grid", width=1, dash=None, fill=None, opacity=None, cap="round"):
        attrs = f' stroke-dasharray="{dash}"' if dash else ""
        if opacity is not None:
            attrs += f' opacity="{opacity}"'
        fill_value = "none" if fill is None else self.p[fill]
        self.parts.append(
            f'<path d="{d}" stroke="{self.p[color]}" stroke-width="{width}" fill="{fill_value}" '
            f'stroke-linecap="{cap}" stroke-linejoin="round"{attrs}/>'
        )

    def line(self, x1, y1, x2, y2, color="grid", width=1, dash=None, opacity=None):
        self.path(f"M {fmt(x1)} {fmt(y1)} L {fmt(x2)} {fmt(y2)}", color, width, dash, opacity=opacity)

    def dot(self, x, y, r=4, color="accent", stroke=None, width=2, opacity=None):
        attrs = f' stroke="{self.p[stroke]}" stroke-width="{width}"' if stroke else ""
        if opacity is not None:
            attrs += f' opacity="{opacity}"'
        self.parts.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{r}" fill="{self.p[color]}"{attrs}/>')

    # -- composites -------------------------------------------------------
    def graph_paper(self, x, y, w, h, step=30, opacity=0.55):
        """Thin coordinate grid: the 'laboratory notebook' substrate."""
        d = []
        gx = x + step
        while gx < x + w:
            d.append(f"M {fmt(gx)} {fmt(y)} V {fmt(y + h)}")
            gx += step
        gy = y + step
        while gy < y + h:
            d.append(f"M {fmt(x)} {fmt(gy)} H {fmt(x + w)}")
            gy += step
        self.path(" ".join(d), "grid", 1, opacity=opacity, cap="butt")

    def header(self, title, subtitle, chip=None, chip_color="mint"):
        self.text(36, 44, title, 22, "text", 650)
        self.text(36, 68, subtitle, 13, "muted")
        if chip:
            self.chip(WIDTH - 36, 33, chip, chip_color, anchor="end")

    def chip(self, x, y, label, color="mint", anchor="start", size=11):
        w = len(str(label)) * size * 0.64 + 34
        cx = x - w if anchor == "end" else x
        self.rect(cx, y, w, 22, "panel2", stroke="edge", radius=11)
        self.dot(cx + 11, y + 11, 3, color)
        self.text(cx + 19, y + 15, label, size, "muted", 600, mono=True)

    def eyebrow(self, x, y, label, color="muted"):
        self.text(x, y, label.upper(), 11, color, 700, spacing=1.6)

    def arrow(self, x1, y1, x2, y2, color="accent", width=1.6, dash=None):
        self.line(x1, y1, x2, y2, color, width, dash)
        angle = math.atan2(y2 - y1, x2 - x1)
        size = 7
        ax = x2 - size * math.cos(angle - 0.5)
        ay = y2 - size * math.sin(angle - 0.5)
        bx = x2 - size * math.cos(angle + 0.5)
        by = y2 - size * math.sin(angle + 0.5)
        self.path(f"M {fmt(ax)} {fmt(ay)} L {fmt(x2)} {fmt(y2)} L {fmt(bx)} {fmt(by)}", color, width)

    def footer(self, y, note):
        self.line(36, y - 18, WIDTH - 36, y - 18, "grid", 1)
        self.text(36, y, note, 12.5, "faint")

    def output(self):
        return "\n".join(self.parts + ["</g>", "</svg>", ""])


def fmt(number):
    """Stable, compact numeric formatting for coordinates."""
    if isinstance(number, float):
        text = f"{number:.2f}".rstrip("0").rstrip(".")
        return text if text not in ("", "-0") else "0"
    return str(number)


def rows(root, name):
    with (root / "data" / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def nice_ceiling(value):
    """Round up to a tidy axis maximum (1, 2, 2.5, 5 × 10^n)."""
    if value <= 0:
        return 1
    exponent = math.floor(math.log10(value))
    for mult in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        candidate = mult * 10 ** exponent
        if candidate >= value:
            return candidate
    return 10 ** (exponent + 1)


# ---------------------------------------------------------------------------
# Hero: a systems map around BUILD → VERIFY → MEASURE → LEARN.
# ---------------------------------------------------------------------------
def hero(theme):
    s = Canvas(
        theme, 300,
        "Build. Verify. Measure. Learn.",
        "Systems map: build with explicit intent, verify independently, measure persisted evidence, learn through reviewed constraints. A repair path returns from verify to build; learned constraints return to the next build.",
    )
    s.graph_paper(0, 0, WIDTH, 300, step=30, opacity=0.5)

    # Background motif, top right: a convergence curve (residual decaying toward a floor).
    curve = []
    for i in range(0, 41):
        x = 684 + i * 4.8
        y = 96 - 62 * math.exp(-i / 9) - 5 * math.sin(i / 1.7) * math.exp(-i / 12)
        curve.append(f"{'M' if i == 0 else 'L'} {fmt(x)} {fmt(y)}")
    s.path(" ".join(curve), "cyan", 1.4, opacity=0.5)
    s.line(684, 96, 876, 96, "faint", 1, dash="2 4", opacity=0.7)
    s.text(876, 110, "residual → floor", 10, "faint", anchor="end", mono=True)

    # Background motif, bottom left: a sparse matrix.
    cells = [(0, 0), (0, 3), (1, 1), (1, 4), (2, 2), (2, 5), (3, 0), (3, 3), (4, 1), (4, 4), (5, 2), (5, 5), (2, 0), (5, 3)]
    for r, c in cells:
        s.rect(40 + c * 13, 196 + r * 13, 9, 9, "accent", radius=2, opacity=0.18 if (r + c) % 2 else 0.32)

    s.eyebrow(36, 46, "Product engineering · Agentic evaluation · Scientific computing", "muted")
    s.text(36, 84, "Build systems whose evidence can be inspected.", 24, "text", 650)
    s.text(36, 108, "Generated work has to survive independent evaluation, deterministic gates and real failure modes.", 13, "muted")

    # Node spine.
    nodes = [("BUILD", "explicit intent", "accent"), ("VERIFY", "independent checks", "mint"),
             ("MEASURE", "persisted evidence", "cyan"), ("LEARN", "reviewed constraints", "accent")]
    xs = [200, 380, 560, 740]
    y = 206
    s.line(xs[0], y, xs[-1], y, "edge", 1.5)
    for i, ((name, note, color), x) in enumerate(zip(nodes, xs)):
        if i:
            s.arrow(x - 60, y, x - 32, y, color, 1.6)
        s.dot(x, y, 14, "panel", stroke=color, width=2)
        s.dot(x, y, 4.5, color)
        s.text(x, y - 24, name, 12.5, "text", 700, anchor="middle", spacing=1.4)
        s.text(x, y + 34, note, 11, "muted", anchor="middle")
    # Recovery path: VERIFY back to BUILD (bounded repair), above the spine.
    s.path(f"M {xs[1]} {y - 14} C {xs[1]} {y - 58}, {xs[0]} {y - 58}, {xs[0]} {y - 14}", "rose", 1.3, dash="4 4", opacity=0.9)
    s.text((xs[0] + xs[1]) / 2, y - 48, "bounded repair", 10.5, "rose", anchor="middle", mono=True)
    # Learning path: LEARN back to BUILD (constraints for the next iteration), below the spine.
    s.path(f"M {xs[3]} {y + 14} C {xs[3]} {y + 78}, {xs[0]} {y + 78}, {xs[0]} {y + 14}", "mint", 1.3, dash="4 4", opacity=0.9)
    s.text((xs[0] + xs[3]) / 2, y + 70, "learned constraints shape the next build", 10.5, "mint", anchor="middle", mono=True)
    return s.output()


# ---------------------------------------------------------------------------
# Growth charts: stepped line over observed snapshots.
# ---------------------------------------------------------------------------
def growth(root, theme, filename, field, title, unit, caveat, series_color="accent"):
    data = rows(root, filename)
    dates = [date.fromisoformat(r["date"]) for r in data]
    values = [int(r[field]) for r in data]
    snapshot = dates[-1].isoformat()

    s = Canvas(theme, 430, title, f"{title}. {unit}. Observed snapshots from {dates[0]} to {snapshot}: " + ", ".join(f"{d} = {v}" for d, v in zip(dates, values)) + ".")
    s.header(title, f"{unit} · observed snapshots · stepped line holds the last observed value", f"snapshot {snapshot}")
    s.text(36, 128, f"{values[0]:,} → {values[-1]:,}", 40, "mint", 700)
    s.text(36, 152, f"{dates[0].strftime('%b %Y')} → {dates[-1].strftime('%b %Y')} · {len(values)} observations", 13, "muted")

    left, right, top, bottom = 76, WIDTH - 40, 182, 356
    cap = nice_ceiling(max(values) * 1.08)
    s.rect(left, top, right - left, bottom - top, "panel2", radius=6)
    s.graph_paper(left, top, right - left, bottom - top, step=29, opacity=0.5)

    ticks = 4
    for i in range(ticks + 1):
        value = cap * i / ticks
        y = bottom - (bottom - top) * i / ticks
        s.line(left, y, right, y, "edge", 1, opacity=0.9)
        s.text(left - 10, y + 4, f"{int(round(value)):,}", 11, "faint", anchor="end", mono=True)

    start = dates[0].toordinal()
    span = max(1, dates[-1].toordinal() - start)
    px = lambda d: left + 8 + (d.toordinal() - start) / span * (right - left - 16)
    py = lambda v: bottom - v / cap * (bottom - top - 12)

    # Month ticks on the x-axis.
    month = date(dates[0].year, dates[0].month, 1)
    while month <= dates[-1]:
        if month >= dates[0]:
            x = px(month)
            s.line(x, bottom, x, bottom + 5, "edge", 1)
            s.text(x, bottom + 19, month.strftime("%b"), 11, "faint", anchor="middle", mono=True)
        month = date(month.year + (month.month // 12), month.month % 12 + 1, 1)

    # Stepped path: hold each observed value until the next observation.
    d = [f"M {fmt(px(dates[0]))} {fmt(py(values[0]))}"]
    for prev_v, day, value in zip(values, dates[1:], values[1:]):
        d.append(f"H {fmt(px(day))} V {fmt(py(value))}")
    area = " ".join(d) + f" V {fmt(bottom)} H {fmt(px(dates[0]))} Z"
    s.path(area, series_color, 0, fill=series_color, opacity=0.10, cap="butt")
    s.path(" ".join(d), series_color, 2.2, cap="butt")

    # Labels stack upward when observations are too close together to sit side by side.
    last_label_x, level = -1e9, 0
    for i, (day, value) in enumerate(zip(dates, values)):
        x, y = px(day), py(value)
        s.dot(x, y, 5, "panel", stroke="mint", width=2)
        s.dot(x, y, 2.2, "mint")
        level = level + 1 if x - last_label_x < 44 else 0
        last_label_x = x
        anchor, lx, ly = "middle", x, y - 12 - level * 15
        if i == 0:
            anchor, lx, ly = "start", x + 8, y - 8
        elif i == len(values) - 1:
            anchor, lx = "end", x - 10
        if level:
            s.line(x, y - 8, x, ly + 3, "faint", 1, opacity=0.8)
        s.text(lx, ly, f"{value:,}", 11.5, "text", 600, anchor=anchor, mono=True)

    s.text(left, 396, dates[0].strftime("%d %b %Y"), 11.5, "muted", mono=True)
    s.text(right, 396, dates[-1].strftime("%d %b %Y"), 11.5, "muted", anchor="end", mono=True)
    s.footer(418, caveat)
    return s.output()


# ---------------------------------------------------------------------------
# Startup benchmark: before/after bars with the mechanism.
# ---------------------------------------------------------------------------
def benchmark(root, theme):
    before, after = [int(r["milliseconds"]) for r in rows(root, "production-sync-benchmark.csv")]
    speedup = before / after
    reduction = (1 - after / before) * 100
    s = Canvas(theme, 330, "Recorded local unchanged-content startup benchmark",
               f"Before {before} milliseconds, after {after} milliseconds; {speedup:.1f} times faster, {reduction:.1f} percent reduction, derived from the recorded values. Recorded local benchmark, not production latency.")
    s.header("Recorded local unchanged-content startup benchmark",
             "commit-recorded measurement · raw benchmark log unavailable · not production latency", "completed case study", "cyan")
    s.text(36, 128, f"{before / 1000:.3f} s → {after / 1000:.3f} s", 40, "mint", 700)
    s.text(36, 152, f"{speedup:.1f}× faster · {reduction:.1f}% reduction (derived)", 13, "muted")

    bar_left, bar_w = 130, 600
    for i, (label, value, color) in enumerate((("before", before, "accent"), ("after", after, "mint"))):
        y = 186 + i * 46
        s.eyebrow(36, y + 20, label, "muted")
        s.rect(bar_left, y, bar_w, 28, "panel2", radius=4)
        w = max(3, bar_w * value / before)
        s.rect(bar_left, y, w, 28, color, radius=4)
        s.text(bar_left + bar_w + 14, y + 19, f"{value:,} ms", 13, "text", 600, mono=True)

    # Mechanism strip.
    steps = ["fingerprint source state", "persist marker only after success", "skip redundant work when unchanged"]
    x = 36
    for i, step in enumerate(steps):
        w = text_width(step, 11.5) + 24
        s.rect(x, 282, w, 24, "panel", stroke="edge", radius=12)
        s.text(x + 12, 298, step, 11.5, "muted", 500)
        if i < len(steps) - 1:
            s.arrow(x + w + 4, 294, x + w + 20, 294, "faint", 1.2)
        x += w + 26
    return s.output()


# ---------------------------------------------------------------------------
# Frame-gate calibration: two interventions with different meanings.
# ---------------------------------------------------------------------------
def calibration(root, theme):
    data = rows(root, "video-gate-calibration.csv")
    raw, genuine, final = [int(r["findings"]) for r in data]
    s = Canvas(theme, 392, "First calibrate the instrument. Then correct the output.",
               f"Stage one, detector calibration: {raw} raw findings became {genuine} genuine blocking defects. Stage two, content correction: {genuine} trusted defects became {final} blocking findings. Stage counts have different meanings.")
    s.header("First calibrate the instrument. Then correct the output.",
             "completed case study · the three counts measure different things; this is not one defect-reduction trend", "completed case study", "cyan")

    panels = [
        (36, raw, "raw signal", "detector findings", "text"),
        (324, genuine, "calibrated signal", "genuine blocking defects", "accent"),
        (612, final, "corrected output", "blocking findings", "mint"),
    ]
    for x, value, head, detail, color in panels:
        s.rect(x, 96, 252, 140, "panel", stroke="edge", radius=10)
        s.eyebrow(x + 20, 122, head, "muted")
        s.text(x + 20, 178, f"{value:,}", 44, color, 700)
        s.text(x + 20, 212, detail, 13, "muted")
    for x in (288, 576):
        s.arrow(x + 2, 166, x + 32, 166, "faint", 1.4)

    s.line(36, 262, WIDTH - 36, 262, "grid", 1)
    columns = [
        (36, "accent", "1 · detector calibration",
         ("Registration and gate-policy assumptions were corrected", "at their source, not weakened to obtain a pass.")),
        (470, "mint", "2 · content correction",
         ("The forty trusted, viewer-visible defects were fixed", "until blocking findings reached zero.")),
    ]
    for x, color, head, lines in columns:
        s.text(x, 290, head, 15, color, 700)
        for j, line in enumerate(lines):
            s.text(x, 312 + j * 18, line, 12.5, "muted")
    s.footer(378, "A green gate is meaningful only after the measurement itself has earned trust.")
    return s.output()


# ---------------------------------------------------------------------------
# Generalised evaluation architecture.
# ---------------------------------------------------------------------------
def architecture(theme):
    s = Canvas(theme, 610, "The creator is not the only judge.",
               "Generalized evaluation architecture: generate, independently verify, adversarially measure, deterministic gates, human review, batch oversight and persisted learning. Bounded repair returns from gates to generation; persisted learning feeds future generation.")
    s.header("The creator is not the only judge.",
             "architecture / design · generalized roles · private prompts, thresholds and anti-gaming rules excluded", "architecture", "accent")
    s.graph_paper(0, 82, WIDTH, 490, step=30, opacity=0.35)

    stages = [
        ("GENERATE", "a builder proposes a candidate", "builder", "accent"),
        ("INDEPENDENT VERIFY", "re-solve the problem; challenge every assumption", "evaluator", "mint"),
        ("ADVERSARIAL MEASURE", "probe known failure modes and exploits", "evaluator", "mint"),
        ("DETERMINISTIC GATES", "check objective contracts in code", "policy", "cyan"),
        ("HUMAN REVIEW", "ratify subjective judgments", "human", "text"),
        ("BATCH OVERSIGHT", "inspect patterns across accepted and rejected artifacts", "human", "text"),
        ("PERSISTED LEARNING", "turn reviewed failures into constraints", "system", "accent"),
    ]
    box_x, box_w, first_y, pitch, box_h = 214, 468, 100, 64, 50
    spine_x = box_x + 22
    ys = [first_y + i * pitch for i in range(len(stages))]
    for i, ((name, note, role, color), y) in enumerate(zip(stages, ys)):
        s.rect(box_x, y, box_w, box_h, "panel", stroke="edge", radius=9)
        s.dot(spine_x, y + box_h / 2, 5, color)
        s.text(box_x + 42, y + 22, name, 12.5, "text", 700, spacing=1.2)
        s.text(box_x + 42, y + 39, note, 11.5, "muted")
        s.chip(box_x + box_w - 14, y + 14, role, color, anchor="end", size=10)
        if i < len(stages) - 1:
            s.arrow(spine_x, y + box_h, spine_x, y + pitch - 1, "faint", 1.2)

    # Bounded repair / reroute: gates back to generation, on the right.
    gx, gy = box_x + box_w, ys[3] + box_h / 2
    s.path(f"M {gx} {fmt(gy)} H {gx + 44} V {fmt(ys[0] + box_h / 2)} H {gx}", "rose", 1.4, dash="5 4")
    s.arrow(gx + 12, ys[0] + box_h / 2, gx + 1, ys[0] + box_h / 2, "rose", 1.4)
    s.text(gx + 56, gy - 4, "bounded", 11.5, "rose", 600, mono=True)
    s.text(gx + 56, gy + 12, "repair / reroute", 11.5, "rose", 600, mono=True)

    # Persisted learning: constraints for future generation, on the left.
    ly = ys[6] + box_h / 2
    s.path(f"M {box_x} {fmt(ly)} H {box_x - 60} V {fmt(ys[0] + box_h / 2)} H {box_x}", "mint", 1.4, dash="5 4")
    s.arrow(box_x - 12, ys[0] + box_h / 2, box_x - 1, ys[0] + box_h / 2, "mint", 1.4)
    for j, word in enumerate(("future", "generation", "inherits", "constraints")):
        s.text(box_x - 72, ys[3] + 10 + j * 16, word, 11.5, "mint", 600, anchor="end", mono=True)

    s.footer(596, "Evidence → reviewed generalization → deterministic checks where objective, reviewed guidance where subjective → future work.")
    return s.output()


# ---------------------------------------------------------------------------
# Synthetic layout fixture: broken → gate overlay → corrected.
# ---------------------------------------------------------------------------
def synthetic(theme):
    broken, fixed = scenes()
    s = Canvas(theme, 700, "Synthetic layout lab: detect, explain, repair",
               "Original fictional scheduling fixture with three synthetic slots and a caption. Panel one shows a broken composition; panel two overlays the geometry gate; panel three shows the corrected composition with no findings.")
    s.header("Synthetic layout lab · detect, explain, repair",
             "original fictional scheduling fixture · illustrative geometry checks, not private production rules", "synthetic fixture", "rose")

    panels = [("01 · broken composition", broken, False, 96), ("02 · gate overlay", broken, True, 290), ("03 · corrected composition", fixed, True, 484)]
    kinds = {"off-canvas": "object extends beyond the canvas", "overlap": "task cards collide", "safe-zone": "object leaves the safe zone", "caption-collision": "caption collides with content"}
    for index, (label, items, overlay, y) in enumerate(panels):
        found = findings(items)
        s.text(36, y + 22, label, 16, "text", 700)
        s.text(36, y + 44, "synthetic schedule · Aster, Birch, Cedar", 12, "muted")
        if found:
            present = [k for k in kinds if any(f["kind"] == k for f in found)]
            for j, kind in enumerate(present):
                s.dot(42, y + 72 + j * 22, 3.5, "rose")
                s.text(54, y + 76 + j * 22, kinds[kind], 12.5, "rose")
        else:
            for j, note in enumerate(("all objects inside the safe zone", "no rectangle collisions", "caption has a dedicated region")):
                s.dot(42, y + 72 + j * 22, 3.5, "mint")
                s.text(54, y + 76 + j * 22, note, 12.5, "mint")

        # Display panel: 400×240 fixture geometry scaled to a 396×176 frame.
        fx, fy, sx, sy = 470, y + 4, 0.99, 0.735
        s.rect(fx - 1, fy - 1, 398, 178, "panel2", stroke="edge", radius=8)
        s.raw(f'<defs><clipPath id="frame-{index}"><rect x="{fx}" y="{fy}" width="396" height="176"/></clipPath></defs>')
        s.raw(f'<g clip-path="url(#frame-{index})"><g transform="translate({fx} {fy}) scale({sx} {sy})">')
        s.graph_paper(0, 0, 400, 240, step=40, opacity=0.6)
        if overlay:
            s.rect(20, 20, 360, 200, None, stroke="mint", radius=2, dash="6 4", width=1.5)
        flagged = {name for issue in found for name in issue["ids"]} if overlay else set()
        for item in items:
            bad = item["id"] in flagged
            s.rect(item["x"], item["y"], item["w"], item["h"], "panel", stroke="rose" if bad else "edge", radius=6, width=2 if bad else 1)
            s.text(item["x"] + 12, item["y"] + item["h"] / 2 + 6, item["label"], 15, "rose" if bad else "text", 600)
        s.raw("</g></g>")
        if overlay:
            status = "0 findings · safe zone" if not found else f"{len(found)} findings"
            s.text(fx - 14, y + 22, status, 10.5, "mint" if not found else "rose", anchor="end", mono=True)

    s.footer(684, "Original synthetic fixture · geometry checks only; subjective visual quality still requires human review.")
    return s.output()


# ---------------------------------------------------------------------------
# Profile cards: one row per case study.
# ---------------------------------------------------------------------------
def cards(root, theme):
    prod = rows(root, "production-test-growth.csv")
    agent = rows(root, "agentic-verification-growth.csv")
    gate = rows(root, "video-gate-calibration.csv")
    bench = rows(root, "production-sync-benchmark.csv")
    definitions = [
        ("production-card", "01 · production systems", "accent",
         f"{int(prod[0]['test_files']):,} → {int(prod[-1]['test_files']):,} automated test files",
         f"{int(bench[0]['milliseconds']) / 1000:.3f} s → {bench[1]['milliseconds']} ms recorded local startup benchmark",
         f"snapshot {prod[-1]['date']}"),
        ("agentic-card", "02 · agentic reasoning", "mint",
         f"{int(agent[0]['passing_tests']):,} → {int(agent[-1]['passing_tests']):,} passing verification tests",
         "independent evaluation · deterministic gates · persisted learning loop",
         f"snapshot {agent[-1]['date']}"),
        ("video-card", "03 · video quality gates", "cyan",
         f"{int(gate[0]['findings']):,} raw findings → {gate[1]['findings']} genuine defects → {gate[2]['findings']} blockers",
         "detector calibration first · content correction second",
         "completed case study"),
    ]
    result = {}
    for name, label, color, metric, desc, snap in definitions:
        s = Canvas(theme, 132, label, f"{metric}. {desc}. {snap}.")
        s.graph_paper(0, 0, WIDTH, 132, step=30, opacity=0.35)
        s.rect(0, 22, 5, 88, color, radius=2)
        s.eyebrow(36, 40, label, "muted")
        s.chip(WIDTH - 36, 24, snap, color, anchor="end")
        s.text(36, 80, metric, 24, color, 700)
        s.text(36, 106, desc, 13, "muted")
        s.text(WIDTH - 36, 108, "open case study →", 11.5, "faint", anchor="end", mono=True)
        result[name] = s.output()
    return result


def generate(root=ROOT):
    """Render every asset for both themes. Keys are repository-relative paths."""
    result = {}
    for theme in PALETTES:
        assets = {
            "hero": hero(theme),
            "production-test-growth": growth(
                root, theme, "production-test-growth.csv", "test_files",
                "Automated test surface over time", "TypeScript / TSX unit + browser test files",
                "File counts describe regression surface, not coverage, assertions or a claim that every file runs in CI.",
            ),
            "agentic-verification-growth": growth(
                root, theme, "agentic-verification-growth.csv", "passing_tests",
                "Verification-suite growth", "recorded passing tests",
                "Accumulated failure modes and contracts, recorded in development evidence; test count alone does not equal correctness.",
                series_color="mint",
            ),
            "production-sync-benchmark": benchmark(root, theme),
            "video-gate-calibration": calibration(root, theme),
            "agentic-architecture": architecture(theme),
            "video-synthetic-before-after": synthetic(theme),
            **cards(root, theme),
        }
        result.update({f"assets/{theme}/{name}.svg": svg for name, svg in assets.items()})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if committed assets differ from data")
    args = parser.parse_args()
    result = generate()
    stale = []
    for rel, content in result.items():
        target = ROOT / rel
        if args.check:
            if not target.exists() or target.read_text() != content:
                stale.append(rel)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
    if stale:
        parser.exit(1, "Stale generated assets: " + ", ".join(stale) + "\n")
    print("Generated assets match public data." if args.check else f"Rendered {len(result)} light/dark SVG assets.")


if __name__ == "__main__":
    main()
