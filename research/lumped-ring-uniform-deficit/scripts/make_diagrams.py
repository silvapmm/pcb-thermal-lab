#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation: the rings of the Lumped network around a 1 mm part on a small and on a large board, and the half ring that the strip formula replaces by a straight strip.
@details Writes figures/fig_01_rings_small_and_large_board.png (the rings as lumped.ring_edges builds them for the program and for the proposal, to scale, centred part, 0.5 mm cell, ten rings;
         only the program's function is called, nothing is solved) and figures/fig_02_half_ring_strip_and_annulus.png (a wide first ring around a small footprint: the strip the program uses
         against the annulus that the heat really crosses); figures/fig_08_source_near_an_edge.png (review: the rings of a source near a straight insulated edge are cut by the edge,
         and the true isotherms, drawn from the source and its mirror image, are not the distance contours that the network keeps at one temperature each). Run: .venv/bin/python research/lumped-ring-uniform-deficit/scripts/make_diagrams.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent / "lib"))

import diagram_kit as dk  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

import lumped_log as LL  # noqa: E402

FIG = HERE.parent / "figures"


def fig_rings():
    """!
    @brief The rings around a 1 mm part for a 60 x 40 mm board and a 200 x 150 mm board, program against proposal, to scale in the first 12 mm.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 5.4, 2, 2)
    cases = [("60 x 40 mm board", 60, 40), ("200 x 150 mm board", 200, 150)]
    dx = 0.5e-3
    for j, (name, w, h) in enumerate(cases):
        rho_max = float(np.hypot(w / 2 - 0.5, h / 2 - 0.5)) * 1e-3          # farthest cell from a centred 1 mm part
        for i, (label, cap) in enumerate((("program: first ring 0.04 x farthest distance", None), ("capped: first ring at most a_eq, at least 1.5 cells (1.5 cells here)", 1.0))):
            LL.configure("strip", 0.04, 1.5, cap)
            a_eq = np.sqrt(4 * dx * dx / np.pi)                              # the 1 mm part touches 2 x 2 cells of 0.5 mm
            edges = LL.MOD.ring_edges(rho_max, dx, dx, 10, a_eq=a_eq) * 1e3
            ax = axs[i, j]
            ax.set_xlim(-12, 12)
            ax.set_ylim(-12, 12)
            ax.set_aspect("equal")
            for k, e in enumerate(edges[1:], start=1):
                if e <= 12.5:
                    ax.add_patch(Circle((0, 0), e + 0.5, fill=(k == 1), facecolor="#f4d8a8" if k == 1 else "none", edgecolor="#555555", linewidth=0.8))
            ax.add_patch(Rectangle((-0.5, -0.5), 1.0, 1.0, facecolor=dk.HEAT, edgecolor="k"))
            ax.text(-11.5, 10.4, f"{name}\n{label}", fontsize=7, va="top")
            ax.text(-11.5, -11.6, f"first ring {edges[1]:.2f} mm wide, part half side 0.5 mm", fontsize=7)
    dk.save(fig, FIG / "fig_01_rings_small_and_large_board.png")
    LL.configure("strip", 0.04, 1.5, None)


def fig_half_ring():
    """!
    @brief Sketch of the first ring around a small footprint: the heat crosses an annulus whose contour grows with the radius, the strip has a constant length.
    @return None.
    """
    fig, axs = dk.canvas(10.0, 4.2, 1, 2, ratios=[1, 1])
    a, t = 0.56, 1.44
    ax = axs[0]
    ax.set_xlim(-2.6, 2.6); ax.set_ylim(-2.6, 2.6); ax.set_aspect("equal")
    ax.add_patch(Circle((0, 0), a + t, facecolor="#f4d8a8", edgecolor="#555555"))
    ax.add_patch(Circle((0, 0), a, facecolor=dk.HEAT, edgecolor="k"))
    for ang in np.linspace(0, 2 * np.pi, 9)[:-1]:
        ax.annotate("", xy=((a + t) * 1.05 * np.cos(ang), (a + t) * 1.05 * np.sin(ang)), xytext=(a * np.cos(ang), a * np.sin(ang)), arrowprops=dict(arrowstyle="->", color=dk.BLUE))
    ax.text(0, -2.55, "what the heat crosses: an annulus,\ncontour 2 pi r grows from 2 pi a to 2 pi (a + t)", ha="center", fontsize=7, va="bottom")
    ax = axs[1]
    ax.set_xlim(-0.5, 5.0); ax.set_ylim(-2.6, 2.6); ax.set_aspect("equal")
    ax.add_patch(Rectangle((0, -1.9), t, 3.8, facecolor="#f4d8a8", edgecolor="#555555"))
    for y in np.linspace(-1.6, 1.6, 7):
        ax.annotate("", xy=(t * 1.05, y), xytext=(0, y), arrowprops=dict(arrowstyle="->", color=dk.BLUE))
    ax.text(t / 2, -2.55, "what the program's formula uses:\na strip of constant length area / t", ha="center", fontsize=7, va="bottom")
    ax.text(2.4, 0.0, "the mean temperature of a wide ring\nsits far from the footprint, but the strip\nhas no narrowing of the path towards\nthe footprint: its resistance is too small\n(0.79 of the annulus for t = a,\n0.43 for t = 10 a)", fontsize=7, va="center")
    dk.save(fig, FIG / "fig_02_half_ring_strip_and_annulus.png")


def fig_near_edge():
    """!
    @brief Figure 8 (review): a source near a straight insulated edge. Left, the rings of the network (distance contours, cut by the edge), each held at one temperature; right,
           the isotherms of the source with its mirror image (the exact field of a point source beside an insulated edge on an infinite sheet, illustrative, no vertical loss),
           which bunch on the side away from the edge and spread along it.
    @return None.
    """
    fig, axs = dk.canvas(10.0, 4.6, 1, 2, ratios=[1, 1])
    d, s = 3.0, 3.0                                                          # source edge 3 mm from the board edge, 3 mm source
    cx = d + s / 2
    for ax in axs:
        ax.set_xlim(-1.0, 22.0); ax.set_ylim(-11.0, 11.0); ax.set_aspect("equal")
        ax.add_patch(Rectangle((-1.0, -11.0), 1.0, 22.0, facecolor="#dddddd", edgecolor="none"))
        ax.plot([0, 0], [-11, 11], color="k", lw=1.5)
        ax.add_patch(Rectangle((cx - s / 2, -s / 2), s, s, facecolor=dk.HEAT, edgecolor="k", zorder=3))
        ax.text(-0.8, 10.3, "board edge\n(insulated)", fontsize=6, va="top")
    ax = axs[0]
    yy, xx = np.mgrid[-11:11:400j, 0:22:400j]
    dist = np.hypot(np.maximum(np.abs(xx - cx) - s / 2, 0), np.maximum(np.abs(yy) - s / 2, 0))
    ax.contour(xx, yy, dist, levels=[1.5, 2.5, 4.0, 6.0, 9.0], colors="#555555", linewidths=0.8)
    ax.text(10.5, -10.5, "the network's rings: contours of the distance to the footprint,\ncut by the edge, each ring one temperature", fontsize=6.5, ha="center")
    ax = axs[1]
    r1 = np.hypot(xx - cx, yy)
    r2 = np.hypot(xx + cx, yy)                                               # mirror image across x = 0
    theta = -np.log(np.maximum(r1, 0.3)) - np.log(np.maximum(r2, 0.3))
    ax.contour(xx, yy, theta, levels=np.linspace(theta.max() - 4.0, theta.max() - 1.2, 6), colors=dk.BLUE, linewidths=0.8, linestyles="solid")
    ax.text(10.5, -10.5, "the field: isotherms of the source and its image (illustrative);\nthe ring cells next to the edge are hotter than the ring mean", fontsize=6.5, ha="center")
    dk.save(fig, FIG / "fig_08_source_near_an_edge.png")


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    fig_rings()
    fig_half_ring()
    fig_near_edge()
