#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the edge band of an imported-copper board: the section of the board at the wall (copper held inside the edge, the laminate nodes, the film) and the plan of a turned edge with the three distances of the edge film.
@details No data and no program. fig_01: section of the 1.6 mm board along the normal to the wall, to scale (1.2 mm of bare laminate between the copper edge and the wall, 1 mm cells, the
         four sub-gaps of the laminate rule with their nodes), the heat paths (copper layer to laminate by k_z, laminate to the wall by the film) and the thermal boundary layer width.
         fig_02: plan of a 22.5 degree outline across a 1 mm grid with the cell centre, the centroid of the board part and the distances d used by the film on the node (none), the
         series film from the centre (signed) and the series film from the centroid.
         Written to `figures/`; `make_figures.py` draws the data figures with the next numbers.
Usage: .venv/bin/python research/imported-copper-edge-film/scripts/make_diagrams.py   (from the repository root)
"""

import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
import numpy as np                                    # noqa: E402
from matplotlib.patches import Polygon, Rectangle     # noqa: E402

FIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")
COPPER, LAM, HEAT, BLUE = "#e0a458", "#e8efe0", "#d62728", "#1f77b4"


def fig_section():
    """!
    @brief Figure 1: the section of the edge band, to scale.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(9.0, 4.6))
    x0, x1, wall, cu_edge = 6.5, 10.0, 10.0, 8.8
    t = 1.6
    tc = 0.035 * 6                                              # copper drawn six times thicker so that it can be seen
    ax.add_patch(Rectangle((x0, 0), wall - x0, t, color=LAM, ec="k", lw=0.8))
    ax.add_patch(Rectangle((x0, t - tc), cu_edge - x0, tc, color=COPPER, ec="k", lw=0.6))
    ax.add_patch(Rectangle((x0, 0), cu_edge - x0, tc, color=COPPER, ec="k", lw=0.6))
    for xc in np.arange(7.0, 10.0, 1.0):                         # the 1 mm cells
        ax.plot([xc, xc], [-0.05, t + 0.05], color="0.6", lw=0.7, ls=":")
    ax.text(7.5, t + 0.14, "cell 1 mm", ha="center", fontsize=8, color="0.35")
    ax.text(8.5, t + 0.14, "cell", ha="center", fontsize=8, color="0.35")
    ax.text(9.6, t + 0.14, "edge cell", ha="center", fontsize=8, color="0.35")
    zs = np.linspace(0.0, t, 5)                                  # n = 4 sub-gaps: nodes at the two copper layers and three inside
    for xn in (7.5, 8.5, 9.5):
        for z in zs:
            ax.plot(xn, z, "o", ms=3.5, color="k")
    ax.text(7.5, 0.80, "node", fontsize=7, ha="left", va="bottom", color="k")
    for z in (0.2, 0.6, 1.0, 1.4):
        ax.annotate("", xy=(wall + 0.25, z), xytext=(wall, z), arrowprops=dict(arrowstyle="->", color=HEAT, lw=1.3))
    ax.text(wall + 0.3, 0.8, "film\nh_side", fontsize=8, color=HEAT, va="center")
    ax.annotate("", xy=(9.4, 1.30), xytext=(8.85, 1.50), arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.5))
    ax.annotate("", xy=(9.4, 0.30), xytext=(8.85, 0.10), arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.5))
    ax.text(9.0, 0.82, "heat from the copper edge\ninto the laminate: in-plane 0.9,\nthrough 0.3 W/mK", fontsize=7.5, color=BLUE, ha="center")
    ax.annotate("", xy=(cu_edge, -0.28), xytext=(wall, -0.28), arrowprops=dict(arrowstyle="<->", lw=1.0))
    ax.text(9.4, -0.48, "1.2 mm of bare laminate", fontsize=8, ha="center")
    bl = math.sqrt(0.9 / 0.3) * 0.38
    ax.annotate("", xy=(cu_edge, 2.0), xytext=(cu_edge + bl, 2.0), arrowprops=dict(arrowstyle="<->", lw=1.0, color=BLUE))
    ax.text(cu_edge + bl / 2, 2.1, "sqrt(0.9/0.3) x 0.38 = 0.66 mm", fontsize=7.5, color=BLUE, ha="center")
    ax.text(x0 + 0.1, t - tc / 2, "top copper (35 um, drawn x6)", fontsize=7, va="center")
    ax.text(x0 + 0.1, tc / 2, "bottom copper", fontsize=7, va="center")
    ax.set_xlim(x0 - 0.2, wall + 1.1)
    ax.set_ylim(-0.7, 2.35)
    ax.set_aspect("equal")
    ax.set_xlabel("distance from the board centre (mm)")
    ax.set_yticks([0, 0.8, 1.6])
    ax.set_ylabel("height (mm)")
    ax.set_title("Edge band of an imported-copper board: copper held 1.2 mm inside the wall, laminate nodes of the rule (n = 4), film on the wall", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_01_edge_band_section.png"), dpi=140)
    plt.close(fig)


def fig_plan():
    """!
    @brief Figure 2: the plan of a turned edge with the distances of the three film treatments.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(7.0, 6.2))
    ang = math.radians(22.5)
    nrm = np.array([math.sin(ang), -math.cos(ang)])             # outward normal of the board (board is above the line)
    nrm = -nrm
    p0 = np.array([0.0, 0.62])
    tang = np.array([math.cos(ang), math.sin(ang)])
    for k in range(-1, 5):
        ax.axvline(k, color="0.75", lw=0.8)
        ax.axhline(k, color="0.75", lw=0.8)
    line = np.array([p0 - 2 * tang, p0 + 5 * tang])
    # the board lies below the outline (towards -normal)
    big = np.array([[-1, -1], [4, -1], [4, 3], [-1, 3]])
    xs = np.linspace(-1, 4, 60)
    yline = p0[1] + (xs - p0[0]) * math.tan(ang)
    ax.fill_between(xs, -1, yline, color="#f2f2f2")
    ax.plot(xs, yline, color="k", lw=1.8)
    ax.text(3.0, 2.3, "outside the board", fontsize=8, color="0.4")
    ax.text(0.2, -0.7, "board", fontsize=8, color="0.4")
    n = 60
    cells = [(1, 0), (1, 1), (2, 1)]
    for (i, j) in cells:
        cx, cy = i + 0.5, j + 0.5
        side = (cy - p0[1]) - (cx - p0[0]) * math.tan(ang)
        dist = -side * math.cos(ang)                              # signed distance, positive inside (board below the line)
        # centroid of the board part of the cell (sampled)
        gx, gy = np.meshgrid(np.linspace(i, i + 1, n), np.linspace(j, j + 1, n))
        inside = gy <= p0[1] + (gx - p0[0]) * math.tan(ang)
        if inside.any():
            cx2, cy2 = gx[inside].mean(), gy[inside].mean()
        dc = (p0[1] + (cx2 - p0[0]) * math.tan(ang) - cy2) * math.cos(ang)
        ax.plot(cx, cy, "o", color=BLUE, ms=7)
        ax.plot(cx2, cy2, "s", color=HEAT, ms=7)
        up = np.array([-math.sin(ang), math.cos(ang)])           # unit normal pointing out of the board (towards larger y)
        f1 = np.array([cx, cy]) + up * dist
        f2 = np.array([cx2, cy2]) + up * dc
        ax.plot([cx, f1[0]], [cy, f1[1]], color=BLUE, lw=1.3)
        ax.plot([cx2, f2[0]], [cy2, f2[1]], color=HEAT, lw=1.3)
        ax.text(cx + 0.06, cy + 0.04, f"d = {dist:+.2f}", color=BLUE, fontsize=8)
        ax.text(cx2 + 0.06, cy2 - 0.14, f"d_c = {dc:.2f}", color=HEAT, fontsize=8)
    ax.plot([], [], "o", color=BLUE, label="cell centre: the program's node (film on the node: d = 0; series film: signed distance, negative when the centre is off the board)")
    ax.plot([], [], "s", color=HEAT, label="centroid of the board part of the cell: the node the cell average belongs to (series film from the centroid, always d_c >= 0)")
    ax.legend(loc="lower right", fontsize=6.5, framealpha=0.95)
    ax.set_xlim(-0.5, 3.6)
    ax.set_ylim(-0.9, 2.6)
    ax.set_aspect("equal")
    ax.set_title("A 22.5 degree outline across the grid: the distance the edge film sees", fontsize=9)
    ax.set_xlabel("x (cells)")
    ax.set_ylabel("y (cells)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_02_turned_edge_distances.png"), dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_section()
    fig_plan()
