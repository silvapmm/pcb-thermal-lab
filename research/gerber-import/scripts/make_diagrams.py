"""!
@file make_diagrams.py
@brief Schematic diagram of the check of the nets against a CAD file (README 4.33): where the nets come from, what is compared and what came out.
@details Pure drawing, no data and no program; the numbers are those of README section 4.33 (Stormduino, KiCad 5). Writes figures/fig_06_nets_check_schematic.png.
         Run: .venv/bin/python research/gerber-import/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

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


def main():
    """!
    @brief Draw and save the diagrams of this folder.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    nets_check(OUT / "fig_06_nets_check_schematic.png")


if __name__ == "__main__":
    main()
