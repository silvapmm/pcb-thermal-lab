"""!
@file make_diagrams.py
@brief Schematic diagram of the check of the nets against a CAD file (README 4.33): where the nets come from, what is compared and what came out.
@details Pure drawing, no data and no program; the numbers are those of README section 4.33 (Stormduino, KiCad 5). Writes figures/fig_06_nets_check_schematic.png and figures/fig_07_what_the_files_draw.png.
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


def main():
    """!
    @brief Draw and save the diagrams of this folder.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    nets_check(OUT / "fig_06_nets_check_schematic.png")
    what_the_files_draw(OUT / "fig_07_what_the_files_draw.png")


if __name__ == "__main__":
    main()
