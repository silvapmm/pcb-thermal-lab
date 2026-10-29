"""!
@file make_diagrams.py
@brief The drawings of the zone-union investigation: a cell with two zones and its sample points, the rules at a point, what a hatched pour is and how two of them can combine, the cases compared, the CAD semantics, and where the fill enters the program.
@details Pure drawing from the geometry of lib/cases.py and the rules of lib/zone_rules.py (no solver runs). Writes to figures/ with the numbering shared with make_figures.py:
         fig_01_cell_two_zones, fig_02_rules_at_a_point, fig_03_hatched_pour, fig_04_cases_compared, fig_05_cad_semantics, fig_06_where_the_fill_enters.
         Run from the repository root: .venv/bin/python research/zone-union/scripts/make_diagrams.py
"""

import _bootstrap  # noqa: F401  (import paths)

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MPoly

import diagram_kit as dk
import variant
from paths import FIGURES

variant.use(False)
import cases                                         # noqa: E402
import zone_rules as zr                              # noqa: E402
from types import SimpleNamespace                    # noqa: E402


def zone(x0, y0, x1, y1, fill=1.0):
    """!
    @brief A zone-like object on a unit cell grid (metres = grid units).
    @param x0 Left.
    @param y0 Bottom.
    @param x1 Right.
    @param y1 Top.
    @param fill Fill.
    @return SimpleNamespace.
    """
    return SimpleNamespace(polygon=np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=float), fill=fill, layer=0)


def cell_panel(ax, zones, colors, title, s=4):
    """!
    @brief One cell with its zones, the sample lattice, and the fill each rule gives.
    @param ax Axes.
    @param zones List of zones inside the unit cell.
    @param colors Face colours per zone.
    @param title Panel title.
    @param s Samples per side.
    @return None.
    """
    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.55, 1.15)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, edgecolor="k", linewidth=1.6))
    for z, c in zip(zones, colors):
        ax.add_patch(Rectangle(z.polygon[0], z.polygon[2][0] - z.polygon[0][0], z.polygon[2][1] - z.polygon[0][1], facecolor=c, alpha=0.55, edgecolor="k", linewidth=0.8))
    sub = (np.arange(s) + 0.5) / s
    for x in sub:
        for y in sub:
            inside = [z for z in zones if z.polygon[0][0] <= x <= z.polygon[2][0] and z.polygon[0][1] <= y <= z.polygon[2][1]]
            ax.plot(x, y, "o", ms=3.2, color="k" if inside else "#bbbbbb")
    ax.set_title(title, fontsize=8)
    txt = []
    for rule, label in (("max_cell", "old (max per cell)"), ("max_point", "per point (prototype)"), ("additive", "additive")):
        f = zr.combine(zones, 1, 1, 1, 1.0, 1.0, s, rule)[0, 0, 0]
        txt.append(f"{label}: {f:.2f}")
    ax.text(0.5, -0.08, "\n".join(txt), ha="center", va="top", fontsize=7)


def fig_01():
    """!
    @brief The cell with two zones: the zones meet inside the cell; overlap; a clearance between two tracks in one cell.
    @return None.
    """
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 4.2))
    cell_panel(axs[0], [zone(0, 0, 0.4, 1), zone(0.4, 0, 1, 1)], ["#4c9be8", "#e8944c"], "zones meet inside the cell (shares 0.40 and 0.60)")
    cell_panel(axs[1], [zone(0, 0, 1, 1, 0.5), zone(0, 0, 1, 1, 0.5)], ["#4c9be8", "#e8944c"], "two zones of fill 0.5 on the same area")
    cell_panel(axs[2], [zone(0.05, 0, 0.35, 1), zone(0.55, 0, 0.85, 1)], ["#4c9be8", "#e8944c"], "two tracks 0.2 apart in one cell (0.3 wide each, the lattice sees 0.25)")
    dk.save(fig, FIGURES / "fig_01_cell_two_zones.png", "A cell of the grid with two zones: black dots are sample points inside a zone, grey dots outside; the fill each rule gives")


def fig_02():
    """!
    @brief The rules at one sample point covered by two zones of different fills.
    @return None.
    """
    pairs = [(0.5, 0.5), (0.8, 0.4), (1.0, 0.5), (0.3, 0.3)]
    rules = [("max_point", "largest fill"), ("prob", "1-(1-a)(1-b)"), ("sum_clip", "a+b, at most 1"), ("priority", "last zone wins")]
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    w = 0.2
    for i, (a, b) in enumerate(pairs):
        z = [zone(0, 0, 1, 1, a), zone(0, 0, 1, 1, b)]
        for j, (r, lab) in enumerate(rules):
            f = zr.combine(z, 1, 1, 1, 1.0, 1.0, 2, r)[0, 0, 0]
            ax.bar(i + (j - 1.5) * w, f, w * 0.92, color=["#1f77b4", "#2ca02c", "#d62728", "#9467bd"][j], label=lab if i == 0 else None)
            ax.text(i + (j - 1.5) * w, f + 0.015, f"{f:.2f}", ha="center", fontsize=7)
    ax.set_xticks(range(len(pairs)))
    ax.set_xticklabels([f"fills {a} and {b}" for a, b in pairs], fontsize=8)
    ax.set_ylabel("fill of the point")
    ax.set_ylim(0, 1.15)
    ax.legend(fontsize=7, ncol=4, loc="upper center")
    ax.set_title("A point covered by two zones: what each rule gives (the rules differ only where a fill is below 1)", fontsize=9)
    dk.save(fig, FIGURES / "fig_02_rules_at_a_point.png")


def hatch_plan(ax, vertical_a, shift_a, vertical_b, shift_b, title, both=True):
    """!
    @brief A square of hatching (stripes of 0.5 pitch 1) from two zones.
    @param ax Axes.
    @param vertical_a True if the stripes of the first zone are vertical.
    @param shift_a Shift of the first zone's stripes.
    @param vertical_b True if the second zone's stripes are vertical.
    @param shift_b Shift of the second zone's stripes.
    @param title Panel title.
    @param both Draw the second zone.
    @return None.
    """
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 4, 4, fill=False, edgecolor="k"))
    for vertical, shift, col in ((vertical_a, shift_a, "#4c9be8"), (vertical_b, shift_b, "#e8944c")):
        if not both and col == "#e8944c":
            continue
        for k in range(4):
            lo = k + shift
            ax.add_patch(Rectangle((lo, 0) if vertical else (0, lo), 0.5 if vertical else 4, 4 if vertical else 0.5, facecolor=col, alpha=0.6, edgecolor="none"))
    ax.set_title(title, fontsize=8)


def fig_03():
    """!
    @brief What a hatched pour is, and three ways two hatched zones of fill 0.5 can overlap.
    @return None.
    """
    fig = plt.figure(figsize=(11, 6.2))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.0, 1.05])
    # Section of a hatched pour: copper lines on the laminate, with the heat spreading along the lines
    ax = fig.add_subplot(gs[0, :2])
    ax.set_xlim(0, 8)
    ax.set_ylim(-1.6, 1.8)
    ax.axis("off")
    ax.add_patch(Rectangle((0, -1.4), 8, 1.2, facecolor=dk.FR4, edgecolor="k"))
    ax.text(4, -0.8, "laminate", ha="center", fontsize=8)
    for k in range(4):
        ax.add_patch(Rectangle((0.25 + 2 * k, -0.2), 1.0, 0.35, facecolor=dk.COPPER, edgecolor="k"))
    ax.annotate("", (8, 0.55), (0, 0.55), arrowprops={"arrowstyle": "<->"})
    ax.text(4, 0.7, "pitch 1 mm of the drawing below, line 0.5 mm: a zone of 'fill 0.5' in the program", ha="center", fontsize=7)
    ax.text(4, 1.35, "Section of a hatched pour: the fill is a share of the area, the pattern is not stored", ha="center", fontsize=8, weight="bold")
    ax2 = fig.add_subplot(gs[0, 2:])
    ax2.axis("off")
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 5)
    ax2.text(0, 4.5, "In the CAD tools a hatched zone is a pattern of tracks:", fontsize=8, weight="bold")
    ax2.text(0, 3.5, "KiCad: hatch width, hatch gap, orientation, smoothing", fontsize=8)
    ax2.text(0, 2.7, "Altium: track width below the grid size, hatch mode 90 / 45 / horizontal / vertical", fontsize=8)
    ax2.text(0, 1.5, "The program stores one number, the share of copper.\nWhat two such zones make together depends on the patterns:", fontsize=8)
    for i, (t, v) in enumerate((("identical", "fill 0.5"), ("shifted half a pitch", "fill 1.0"), ("crossed", "fill 0.75 of area"))):
        pass
    for i, (title, fn) in enumerate((("identical patterns:\nunion = the same pattern, area 0.5", lambda a: hatch_plan(a, True, 0, True, 0, "identical patterns:\nunion = one pattern, area 0.5")),
                                    ("", lambda a: hatch_plan(a, True, 0, True, 0.5, "shifted by half a pitch:\nunion = solid, area 1.0")),
                                    ("", lambda a: hatch_plan(a, True, 0, False, 0, "crossed:\nunion = a grid, area 0.75")),
                                    ("", lambda a: hatch_plan(a, True, 0, True, 0, "one zone alone (area 0.5)", both=False)))):
        fn(fig.add_subplot(gs[1, i]))
    dk.save(fig, FIGURES / "fig_03_hatched_pour.png")


def fig_04():
    """!
    @brief The cases of the study drawn on the board (resolved copper, the zones' outlines, the heater).
    @return None.
    """
    C = cases.make_cases()
    names = [n for n in C if C[n]["resolved"] is not None or n.startswith("fills") or "fill 0.5" in n]
    names = [n for n in names if not n.startswith("hatch: a hatched") and "two layers" not in n][:16]
    fig, axs = plt.subplots(4, 4, figsize=(11, 11.5))
    pal = ["#4c9be8", "#e8944c", "#6cc070", "#c070c0", "#d4c34a", "#c0c0c0"]
    for ax, n in zip(axs.ravel(), names):
        ax.set_xlim(-0.5, 20.5)
        ax.set_ylim(-0.5, 20.5)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.add_patch(Rectangle((0, 0), 20, 20, fill=False, edgecolor="k"))
        zs = C[n]["zones"]
        if len(zs) > 6:                                  # the strips: draw alternately two colours
            for k, z in enumerate(zs):
                ax.add_patch(MPoly(z["poly"], facecolor=pal[k % 2], alpha=0.6, edgecolor="none"))
        else:
            for k, z in enumerate(zs):
                ax.add_patch(MPoly(z["poly"], facecolor=pal[k % len(pal)], alpha=0.25 + 0.6 * z["fill"] if z["fill"] < 1 else 0.6, edgecolor="k", linewidth=0.6))
        ax.add_patch(Rectangle((8, 8), 4, 4, facecolor="#444444", alpha=0.8))
        ax.set_title(n.replace("two zones meeting along a line at", "two zones, joint at").replace("frame with a hole and an island 0.3 mm inside it", "frame, hole, island 0.3 mm in it"), fontsize=7)
    for ax in axs.ravel()[len(names):]:
        ax.axis("off")
    dk.save(fig, FIGURES / "fig_04_cases_compared.png", "The boards of the study (20 x 20 mm, the grey square is the 4 x 4 mm heater of 1 W; colours distinguish zones, paler = fill below 1)")


def fig_05():
    """!
    @brief What the CAD tools and the Gerber format say about overlapping copper (from the sources in the README).
    @return None.
    """
    fig, ax = dk.canvas(11.5, 5.8)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    cols = [
        ("Gerber (Ucamco spec 2026.05, pages 14, 96, 98)", dk.BLUE,
         ["The image is the stack of levels in file order.", "A dark object darkens, a clear object clears the levels below.",
          "Objects may overlap; within a level the order does not matter.", "A region is filled; contours of one G36/G37 pair:",
          "'the overall filled area is the union of the filled areas'.", "=> overlapping dark copper = geometric union.", "A copper layer may carry the label type Hatched (a file attribute);", "the copper itself is still objects: there is no density."]),
        ("KiCad (manual 9.0, zone_filler.cpp)", "#2ca02c",
         ["Zone priority orders the fill of overlapping zones.", "Lower priority keeps clearance to the fill of higher priority.",
          "Same priority, same net: the zones overlap and are one copper.", "Different nets: one keeps clearance to the other.",
          "Same net, higher priority: its outline is cut from the lower zone", "(source: it is 'in charge of the fill parameters' there).",
          "Fill types: solid or hatch pattern (width, gap, orientation).", "=> solid copper of one net: the union; a hatched zone of higher", "priority keeps its own pattern inside its outline."]),
        ("Altium (polygon pour properties page)", "#d62728",
         ["Overlapping polygons: the pour order decides who owns the area.", "'Bring to front' makes a polygon pour over the others.",
          "Pour Over Same Net Polygons Only (default) pours over same-net polygons.", "Hatched: track width below the grid size; modes 90, 45, horizontal, vertical.",
          "=> the higher order owns the shared area; for solid copper", "of one net the result is the union."]),
    ]
    for i, (head, color, lines) in enumerate(cols):
        x = 0.1 + 4.0 * i
        dk.box(ax, x, 4.9, 3.8, 0.8, head, color=color, bold=True, size=8)
        for j, t in enumerate(lines):
            ax.text(x + 0.05, 4.55 - 0.45 * j, t, fontsize=6.8, va="top", wrap=True)
    ax.text(6, 0.25, "None of the three says that a hatched zone is a density: it is a pattern. Solid copper that overlaps is the geometric union in all three;\n"
                     "where hatched zones overlap, KiCad and Altium give the area to one zone (priority, pour order). Sources read in their text: README, sections 2 and 12.", ha="center", fontsize=7.2, style="italic")
    dk.save(fig, FIGURES / "fig_05_cad_semantics.png")


def fig_06():
    """!
    @brief Where the fill of the zones enters the program (the five places that combine zones and what each uses the fill for).
    @return None.
    """
    fig, ax = dk.canvas(11.5, 5.2)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.5)
    dk.box(ax, 0.1, 2.2, 1.9, 1.1, "Problem.zones\n(polygon, layer, fill)", color=dk.COPPER)
    dk.box(ax, 2.7, 2.2, 2.3, 1.1, "combine the zones of\nevery layer into one\nfill (L, ny, nx)", color="#fff2b3", bold=True)
    dk.arrow(ax, 2.0, 2.75, 2.7, 2.75)
    uses = [("fvm.py:74-78  sheet conductance S,\nheat capacity C", 4.6), ("fdm.py:134-136  at the nodes\n(cells averaged to nodes)", 3.7), ("solid3d.py:158-160  conductivity of\nthe copper slab", 2.8),
            ("analytic.py:132-135 and 215-217\nlayer sheets and tiles", 1.9), ("checks.py:61-63  input warnings", 1.0)]
    for t, y in uses:
        dk.box(ax, 6.0, y - 0.35, 3.2, 0.75, t, color="#cfe3f5", size=7)
        dk.arrow(ax, 5.0, 2.75, 6.0, y)
    dk.box(ax, 9.8, 2.2, 2.0, 1.1, "Lumped: reads the fill\nfrom fvm.Network", color="#e4e4e4", size=7)
    dk.arrow(ax, 9.2, 4.6, 9.8, 3.1)
    ax.text(0.1, 0.35, "The same loop with np.maximum(fill, coverage * z.fill) is written six times in five files. The change is one function (geometry.zone_fill) called from the six places.\n"
                       "Not touched: coverage_fraction of heaters, vias, heatsinks, the statistics per zone (analysis.py:78) and the zone check (checks.py:112), which look at one polygon at a time.", fontsize=7.2, style="italic")
    dk.save(fig, FIGURES / "fig_06_where_the_fill_enters.png")


if __name__ == "__main__":
    FIGURES.mkdir(parents=True, exist_ok=True)
    for f in (fig_01, fig_02, fig_03, fig_04, fig_05, fig_06):
        f()
        print("drawn", f.__name__)
