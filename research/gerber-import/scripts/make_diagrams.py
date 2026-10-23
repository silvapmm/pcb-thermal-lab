"""!
@file make_diagrams.py
@brief Schematic diagram of the check of the nets against a CAD file (README 4.33): where the nets come from, what is compared and what came out.
@details Pure drawing, no data and no program; the numbers are those of README section 4.33 (Stormduino, KiCad 5). Writes figures/fig_06_nets_check_schematic.png figures/fig_07_what_the_files_draw.png figures/fig_08_excellon_zeros.png and figures/fig_16_outline_how.png.
         Run: .venv/bin/python research/gerber-import/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

from matplotlib.patches import Arc, Circle, Polygon, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def nets_check(path):
    """!
    @brief Draw the two independent sources (the Gerbers drawn by our reader, the CAD file read by its own small reader), the four questions and the results.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(14, 6.0)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6.0)
    dk.box(ax, 0.1, 3.9, 2.6, 1.3, "Gerber files\n(no net attributes)", dk.COPPER, size=9)
    dk.box(ax, 0.1, 0.8, 2.6, 1.3, ".kicad_pcb\n(nets, tracks, vias,\npads, zones)", "#cfe3f5", size=9)
    dk.box(ax, 3.3, 3.9, 2.6, 1.3, "independent reader:\ncopper pieces\n(8-connected)", "#e8e8e8", size=9)
    dk.box(ax, 3.3, 0.8, 2.6, 1.3, "small CAD reader:\nobjects with a net,\nposition, rotation", "#e8e8e8", size=9)
    dk.arrow(ax, 2.7, 4.55, 3.3, 4.55)
    dk.arrow(ax, 2.7, 1.45, 3.3, 1.45)
    dk.box(ax, 6.5, 2.2, 2.3, 1.6, "tie each object\nto the piece\nunder it", "#fbe3c2", bold=True, size=9)
    dk.arrow(ax, 5.9, 4.55, 6.6, 3.8)
    dk.arrow(ax, 5.9, 1.45, 6.6, 2.2)
    rows = [("objects lie on the copper (position, y axis,\nrotation, units)", "1380/1380 track points, 48/48 via points,\n281/281 pad points"),
            ("a piece holds objects of two nets\n(a short, or a reader error)", "0 of 170 pieces"),
            ("plated holes join a piece on both layers;\na joined group holds two nets", "109 of 109 join; 0 of 66 groups"),
            ("nets split into the same number of pieces", "55 of 56 equal (the one difference is\nmost probably the CAD-side overlap test)")]
    for i, (q, a) in enumerate(rows):
        y = 4.9 - i * 1.4
        dk.box(ax, 9.2, y - 0.55, 2.4, 1.1, q, "#ffffff", size=7)
        dk.arrow(ax, 11.6, y, 11.9, y, width=1.0)
        dk.box(ax, 11.9, y - 0.55, 2.0, 1.1, a, "#e3f1df", size=6.5)
        dk.arrow(ax, 8.8, 3.0, 9.2, y, width=0.8)
    dk.save(fig, path, "Are the polygons tied to the right nets? Two independent sources, four questions")


def what_the_files_draw(path):
    """!
    @brief Draw what a Gerber file is made of (flashes, draws, arcs, regions, clear polarity) and what a drill file adds (plated holes, which are vias and which are component holes).
    @param path Output file.
    @return None.
    """
    fig, (a1, a2) = dk.canvas(14, 5.2, 1, 2, ratios=[1.25, 1])
    a1.set_xlim(0, 12)
    a1.set_ylim(0, 8)
    a1.set_aspect("equal")
    a1.text(6, 7.7, "1. a copper layer is a list of operations", ha="center", fontsize=9, fontweight="bold")
    a1.add_patch(Circle((1.5, 6.0), 0.7, facecolor=dk.COPPER, edgecolor="k"))
    a1.text(1.5, 4.9, "flash (D03):\nround aperture", ha="center", va="top", fontsize=7)
    a1.add_patch(Rectangle((5.0, 5.4), 1.8, 1.2, facecolor=dk.COPPER, edgecolor="k"))
    a1.text(5.9, 4.9, "flash (D03):\nrectangular aperture", ha="center", va="top", fontsize=7)
    a1.plot([9.0, 11.0], [6.0, 6.0], color=dk.COPPER, linewidth=9, solid_capstyle="round")
    a1.add_patch(Circle((9.0, 6.0), 0.3, fill=False, linestyle="--", edgecolor="k"))
    a1.add_patch(Circle((11.0, 6.0), 0.3, fill=False, linestyle="--", edgecolor="k"))
    a1.text(10.0, 4.9, "move (D02), draw (D01):\nthe aperture swept,\nwidth = its diameter", ha="center", va="top", fontsize=7)
    a1.add_patch(Arc((1.9, 1.7), 2.6, 2.6, theta1=20, theta2=160, edgecolor=dk.COPPER, linewidth=8, capstyle="round"))
    a1.text(1.9, 0.5, "arc (G02 / G03):\na circular track", ha="center", va="top", fontsize=7)
    a1.add_patch(Polygon([(4.8, 1.0), (7.0, 0.9), (7.2, 2.6), (6.0, 3.1), (4.9, 2.4)], facecolor=dk.COPPER, edgecolor="k"))
    a1.text(6.0, 0.5, "region (G36 / G37):\na filled polygon", ha="center", va="top", fontsize=7)
    a1.add_patch(Rectangle((8.6, 0.9), 2.8, 2.2, facecolor=dk.COPPER, edgecolor="k"))
    a1.add_patch(Rectangle((9.4, 1.5), 1.2, 1.0, facecolor="white", edgecolor="k", linestyle="--"))
    a1.text(10.0, 0.5, "clear polarity (LPC):\nremoves copper again", ha="center", va="top", fontsize=7)
    # the drill file: two plated holes in cross-section
    a2.set_xlim(0, 10)
    a2.set_ylim(-0.6, 8)
    a2.text(5, 7.7, "2. a drill file adds plated holes", ha="center", fontsize=9, fontweight="bold")
    for x, lead in ((0.6, False), (5.4, True)):
        dk.layer(a2, x, 2.0, 4.0, 3.2, dk.FR4)
        dk.layer(a2, x, 5.2, 1.3, 0.25, dk.COPPER)
        dk.layer(a2, x + 2.7, 5.2, 1.3, 0.25, dk.COPPER)
        dk.layer(a2, x, 1.75, 1.3, 0.25, dk.COPPER)
        dk.layer(a2, x + 2.7, 1.75, 1.3, 0.25, dk.COPPER)
        a2.add_patch(Rectangle((x + 1.3, 1.75), 1.4, 3.7, facecolor="white", edgecolor="k"))
        a2.add_patch(Rectangle((x + 1.3, 1.75), 0.18, 3.7, facecolor=dk.COPPER, edgecolor="k"))
        a2.add_patch(Rectangle((x + 2.52, 1.75), 0.18, 3.7, facecolor=dk.COPPER, edgecolor="k"))
        if lead:
            a2.add_patch(Rectangle((x + 1.75, 0.7), 0.5, 5.6, facecolor="#8a8a8a", edgecolor="k"))
    a2.text(2.6, 6.5, "via\n(joins layers)", ha="center", fontsize=8)
    a2.text(7.4, 6.8, "component hole\n(a lead goes through)", ha="center", fontsize=8)
    a2.text(5, 0.7, "both are plated holes in the drill file;\nthe Gerber cannot tell which is a via,\nso the user confirms the kind", ha="center", va="top", fontsize=7.5, style="italic")
    dk.save(fig, path, "What the files draw: the operations of a Gerber layer and the holes of a drill file")


def excellon_zeros(path):
    """!
    @brief Draw how the same digits of a drill file give two different hole positions depending on which zeros the header says are omitted (README 4.19), and why comparing only the hole counts missed it.
    @param path Output file.
    @return None.
    """
    fig, (a1, a2) = dk.canvas(14, 5.0, 1, 2, ratios=[1.2, 1])
    a1.set_xlim(0, 12)
    a1.set_ylim(-0.6, 8)
    a1.text(6, 7.6, "one line of a drill file, two readings (format 3.3, mm)", ha="center", fontsize=9, fontweight="bold")
    dk.box(a1, 3.0, 5.6, 6.0, 1.0, "X1275  Y830", "#ffffff", size=11)
    dk.box(a1, 0.2, 2.4, 5.4, 2.0, "header says TZ:\ntrailing zeros are kept,\nleading ones omitted\n\ndigits padded on the left:\n001275 -> X = 1.275 mm\n000830 -> Y = 0.830 mm", "#e3f1df", size=7.5)
    dk.box(a1, 6.4, 2.4, 5.4, 2.0, "header says LZ:\nleading zeros are kept,\ntrailing ones omitted\n\ndigits padded on the right:\n127500 -> X = 127.500 mm\n830000 -> Y = 830.000 mm", "#f4b6b6", size=7.5)
    dk.arrow(a1, 5.0, 5.6, 2.9, 4.4)
    dk.arrow(a1, 7.0, 5.6, 9.1, 4.4)
    a1.text(6, 1.3, "the reader had the two options swapped: Excellon names the zeros that are KEPT,\nthe Gerber wording names the ones that are omitted", ha="center", va="top", fontsize=7.5, style="italic")
    # the board and where the holes land
    a2.set_xlim(-2, 14)
    a2.set_ylim(-3, 6)
    a2.set_aspect("equal")
    a2.add_patch(Rectangle((0, 0), 4.0, 3.0, facecolor=dk.FR4, edgecolor="k"))
    a2.plot([0.7], [0.7], "o", color="k", markersize=7)
    a2.text(2, 3.4, "right reading:\nthe hole is on the board", ha="center", fontsize=7.5)
    a2.add_patch(Rectangle((7.0, 0), 4.0, 3.0, facecolor=dk.FR4, edgecolor="k"))
    a2.annotate("", (13.3, 0.7), (11.1, 0.7), arrowprops={"arrowstyle": "->", "color": dk.HEAT})
    a2.text(9, 3.4, "wrong reading:\nthe hole lands far off the board", ha="center", fontsize=7.5, color=dk.HEAT)
    a2.text(6, -0.9, "the hole counts were the same, so a comparison of counts said\n\"identical\"; only comparing positions found it", ha="center", va="top", fontsize=7.5, style="italic")
    dk.save(fig, path, "Excellon zero suppression: the same digits, two positions (README 4.19)")


def outline_how(path):
    """!
    @brief Draw how the board outline is read from the profile layer: the stroke band and the cut along its centre line, the even-odd rule along a row (board, slot), and a closed contour against a contour with a gap.
    @param path Output file.
    @return None.
    """
    fig, (a1, a2, a3) = dk.canvas(15, 5.0, 1, 3)
    for a in (a1, a2, a3):
        a.set_xlim(0, 10)
        a.set_ylim(-1.6, 8.0)
        a.set_aspect("equal")
    # 1. the stroke and the cut
    a1.text(5, 7.5, "1. a stroke is a band; the cut is its centre line", ha="center", fontsize=9, fontweight="bold")
    a1.add_patch(Rectangle((1.0, 1.6), 7.8, 0.9, facecolor="#333333"))
    a1.add_patch(Rectangle((7.9, 1.6), 0.9, 4.6, facecolor="#333333"))
    a1.plot([1.0, 8.35, 8.35], [2.05, 2.05, 6.2], "--", color=dk.HEAT, linewidth=1.6)
    a1.text(4.5, 0.6, "profile layer: a thin aperture drawn along the contour\nthe fabricator routes along the middle of the line\nboard = what the strokes enclose", ha="center", va="top", fontsize=7.5)
    a1.text(3.0, 3.6, "board", ha="center", fontsize=9, color=dk.HEAT)
    # 2. even-odd along a row
    a2.text(5, 7.5, "2. which side is board: count the strokes along a row", ha="center", fontsize=9, fontweight="bold")
    a2.add_patch(Rectangle((0.8, 1.5), 8.4, 5.0, fill=False, edgecolor="#333333", linewidth=3))
    a2.add_patch(Rectangle((3.6, 3.3), 2.8, 1.4, fill=False, edgecolor="#333333", linewidth=3))
    a2.annotate("", (9.6, 4.0), (0.2, 4.0), arrowprops={"arrowstyle": "<-", "color": dk.BLUE, "linewidth": 1.2})
    for x, n, c in ((0.8, "1", dk.FR4), (3.6, "2", "white"), (6.4, "3", dk.FR4), (9.2, "4", "white")):
        a2.text(x, 4.35, n, ha="center", fontsize=8, color=dk.BLUE)
    a2.text(2.2, 5.3, "odd:\nboard", ha="center", fontsize=7.5)
    a2.text(5.0, 4.0, "even:\nslot", ha="center", va="center", fontsize=7.5)
    a2.text(7.8, 5.3, "odd:\nboard", ha="center", fontsize=7.5)
    a2.text(5, 0.6, "odd number of strokes to the left: inside the board\neven: outside, or a cut-out; columns give a second vote\n(a row that runs along a stroke is wrong, a column is not)", ha="center", va="top", fontsize=7.5)
    # 3. closed against open
    a3.text(5, 7.5, "3. is the contour closed? let the outside flow in", ha="center", fontsize=9, fontweight="bold")
    a3.add_patch(Rectangle((0.6, 2.6), 3.6, 3.6, fill=False, edgecolor="#333333", linewidth=3))
    a3.add_patch(Rectangle((0.6, 2.6), 3.6, 3.6, facecolor=dk.FR4, alpha=0.5))
    a3.text(2.4, 4.4, "closed:\nthe interior\nstays inside", ha="center", fontsize=7.5)
    a3.plot([5.8, 5.8, 9.4, 9.4, 8.1], [2.6, 6.2, 6.2, 2.6, 2.6], color="#333333", linewidth=3)
    a3.plot([6.9, 5.8], [2.6, 2.6], color="#333333", linewidth=3)
    a3.annotate("", (7.5, 4.4), (7.5, 1.6), arrowprops={"arrowstyle": "->", "color": dk.HEAT, "linewidth": 1.6})
    a3.text(7.5, 4.9, "gap: the outside\nreaches the board", ha="center", fontsize=7.5, color=dk.HEAT)
    a3.text(5, 0.6, "board pixels connected to the outside = a leak:\nthe contour is flagged, and the board not trusted", ha="center", va="top", fontsize=7.5)
    dk.save(fig, path, "Reading the board outline from the profile layer: centre line, even-odd rule, closed contour (README 4.47)")


def main():
    """!
    @brief Draw and save the diagrams of this folder.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    nets_check(OUT / "fig_06_nets_check_schematic.png")
    what_the_files_draw(OUT / "fig_07_what_the_files_draw.png")
    excellon_zeros(OUT / "fig_08_excellon_zeros.png")
    outline_how(OUT / "fig_16_outline_how.png")


if __name__ == "__main__":
    main()
