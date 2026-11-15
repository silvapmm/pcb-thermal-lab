#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_fig_fem_mesh.py
@brief Picture for `docs/theory.md` 4a: the plan mesh that `pcbthermal/femmesh.py` builds from a small drawn board, with its break lines, the refined zone around the part, a conforming via patch and a rod via.
@details fig_50, left: the plan mesh of the whole board as the program builds it (the board of the picture has a rectilinear outline with a notch, a copper zone, a part, a block, one via
         with room, one via on a break line); the tensor quads are drawn in grey, the quads of the via patch in colour by material (open core white, barrel copper, board), the elements removed by the
         outline absent. Right: the via patch zoomed, the circles of the O-grid (inner radius, the two rings across the plating, the drill) drawn over it. The picture is made by the program's own
         `femmesh._layout`, so it is what the mesh really is. Run: .venv/bin/python research/theory/scripts/make_fig_fem_mesh.py (from the repository root; a few seconds). Writes figures/fig_50_fem_plan_mesh.png.
"""

import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
import numpy as np                                                 # noqa: E402
from matplotlib.collections import PolyCollection                  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
OUT = Path(__file__).resolve().parents[1] / "figures"

from pcbthermal import femmesh                                     # noqa: E402
from pcbthermal.model import Problem                               # noqa: E402
import diagram_kit as dk                                           # noqa: E402


def picture_problem():
    """!
    @brief The board of the picture: 30 x 20 mm, a notch cut out of a corner, a copper zone with an unaligned slanted edge, a part, a block and two vias.
    @return Problem.
    """
    p = Problem.new(30.0, 20.0, layers=2, h_side=20.0)
    p.set_outline([(0, 0), (30, 0), (30, 12), (24, 12), (24, 20), (0, 20)])
    p.add_zone(1, polygon=[(2, 2), (22, 2), (22, 14), (14, 18), (2, 18)])
    p.add_zone(2, rect=(1, 1, 29, 11))
    p.add_heater(1, 1.0, rect=(8, 6, 12, 10))
    p.add_heatsink(2, 0.0, rect=(15, 3, 21, 9), thickness_mm=2.0)
    p.add_via(5.0, 14.0, diameter=0.4)              # room for a conforming barrel
    p.add_via(14.0, 7.0, diameter=0.4)              # its window would hold the heater's break lines: a rod
    return p


def draw(path):
    """!
    @brief Draw the plan mesh of the picture board and the zoom on its via patch.
    @param path Output file.
    @return None.
    """
    p = picture_problem()
    lay = femmesh._layout(p, 2.0, 6, 2.0)
    plan = lay.plan
    pts = plan.xy[plan.quads] * 1e3
    fig, axs = dk.canvas(15.5, 6.4, 1, 2, ratios=[1.45, 1.0])
    a = axs[0]
    on = plan.active
    cols = np.where(plan.tag == 2, "#c97a2b", np.where(plan.tag == 1, "#ffffff", np.where(plan.via >= 0, "#cfe3f5", "#f1f1f1")))
    a.add_collection(PolyCollection(pts[on], facecolors=cols[on], edgecolors="#555555", linewidths=0.35))
    for x in plan.xn * 1e3:
        a.plot([x, x], [0, 0], lw=0)
    o = np.asarray(p.board.outline) * 1e3
    a.plot(*np.vstack([o, o[:1]]).T, "k-", lw=1.6)
    for z in p.zones:
        q = np.asarray(z.polygon) * 1e3
        a.plot(*np.vstack([q, q[:1]]).T, color="#c97a2b", ls="--", lw=1.2)
    for h in p.heaters:
        q = np.asarray(h.polygon) * 1e3
        a.add_patch(plt.Polygon(q, fc="#e63946", alpha=0.45, ec="#e63946", lw=1.2))
    for s in p.heatsinks:
        q = np.asarray(s.polygon) * 1e3
        a.add_patch(plt.Polygon(q, fc="none", ec="#1f77b4", lw=1.8))
    a.set_xlim(-1, 31)
    a.set_ylim(-1, 21)
    a.set_aspect("equal")
    a.text(0.0, 21.2, "plan mesh from the Problem", fontsize=9, fontweight="bold")
    a.text(15.0, -0.9, "break lines at the aligned edges (outline, block, part); the slanted zone edge is not one: element fill",
           fontsize=7.5, ha="center", va="top")
    for v in p.vias:
        a.plot(v.x * 1e3, v.y * 1e3, "o", mfc="white", mec="k", ms=5, zorder=5)
    bb = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85)
    a.annotate("part: elements refined around it", (10, 10), (11.0, 19.3), fontsize=8, color="#b02a37", arrowprops=dict(arrowstyle="->", color="#b02a37"), bbox=bb)
    a.annotate("via with room: conforming\nhollow cylinder (O-grid patch)", (5, 14), (0.6, 19.3), fontsize=8, arrowprops=dict(arrowstyle="->"), va="top", bbox=bb)
    a.annotate("via on a break line: a rod of the\nbarrel area (no patch)", (14, 7), (6.0, 3.6), fontsize=8, arrowprops=dict(arrowstyle="->"), bbox=bb)
    a.text(27, 16, "removed by\nthe outline", fontsize=8, ha="center", va="center")
    a.annotate("block (partial slabs)", (21, 9), (22.0, 6.0), fontsize=8, color="#1f77b4", arrowprops=dict(arrowstyle="->", color="#1f77b4"), bbox=bb)
    # the zoom on the patch
    b = axs[1]
    w = lay.windows[0]
    half = w["half"] * 1e3
    sel = on & (plan.via >= 0)
    b.add_collection(PolyCollection(pts[sel], facecolors=cols[sel], edgecolors="#333333", linewidths=0.6))
    v = p.vias[w["via"]]
    r = 0.5 * v.diameter * 1e3
    r_in = r - p.board.via_plating * 1e3
    t = np.linspace(0, 2 * math.pi, 200)
    for rr, ls in ((r, "-"), (r_in, "--"), (r_in + 0.5 * (r - r_in), ":")):
        b.plot(w["cx"] * 1e3 + rr * np.cos(t), w["cy"] * 1e3 + rr * np.sin(t), "k" + ls, lw=0.9)
    zoom = 0.45 * half                                              # close enough to see the rings across the plating
    b.set_xlim(w["cx"] * 1e3 - zoom, w["cx"] * 1e3 + zoom)
    b.set_ylim(w["cy"] * 1e3 - zoom, w["cy"] * 1e3 + zoom)
    b.set_aspect("equal")
    b.set_title("the via patch, zoomed: the open core, two rings across the plating,\nthe drill circle (solid), the inner radius (dashed), blended rings outwards", fontsize=8.5)
    b.text(w["cx"] * 1e3, w["cy"] * 1e3 - zoom * 0.96, "white: the hole (drawn here, no element in 3D); copper: the plating ring; blue: board material",
           fontsize=7.5, ha="center", va="bottom", bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9))
    dk.save(fig, path, "The plan mesh of the finite-element model (as built by femmesh.py)")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    draw(OUT / "fig_50_fem_plan_mesh.png")
