#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the three situations of research/laminate-2-6 (no data, no solver): the sub-layers under a small part (default and local rule), the laminate at the board edge (one film on
       the copper node, laminate nodes at the edge), and the slabs of the 3D solid (4 per gap and by thickness).
@details Figures 01 to 03 and 07 (the transition of the chains, drawn in the review) of figures/ (the data figures 04 on are drawn by make_figures.py; one numbering). Vertical scales are exaggerated; the only numbers on the drawings are rules
         stated in the README. Usage: .venv/bin/python research/laminate-2-6/scripts/make_diagrams.py   (from the repository root).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402
from matplotlib.patches import Rectangle                         # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"
OUT.mkdir(exist_ok=True)
CU, FR4, PART = "#d9a441", "#cfe3c3", "#c0504d"


def stack(ax, x0, x1, ztop, d, n, node_x=None, label=True):
    """!
    @brief Draw a copper layer on top, a laminate gap cut into n sub-gaps with a node line each, and a copper layer below.
    @param ax Axes.
    @param x0 Left end.
    @param x1 Right end.
    @param ztop Height of the top of the gap.
    @param d Thickness of the gap (drawing units).
    @param n Sub-gaps.
    @param node_x Optional (xa, xb) range where the interior node lines are drawn (default: all).
    @param label True to write the number of sub-gaps.
    @return None
    """
    ax.add_patch(Rectangle((x0, ztop - d), x1 - x0, d, color=FR4))
    xa, xb = node_x if node_x else (x0, x1)
    for k in range(1, n):
        ax.plot([xa, xb], [ztop - d * k / n] * 2, color="#2f6f2f", lw=0.8)
    if label and n > 1:
        ax.text((xa + xb) / 2, ztop - d * 0.5, f"{n}", ha="center", va="center", fontsize=7, color="#1b4d1b")


def fig_small_part():
    """!
    @brief Figure 01: sub-layers under a small part, the default rule and the local rule side by side.
    @return None
    """
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, local in zip(axes, (False, True)):
        ax.set_xlim(0, 20)
        ax.set_ylim(-1.0, 8)
        ax.axis("off")
        zt, d = 6.0, 4.0
        ax.add_patch(Rectangle((0, zt), 20, 0.3, color=CU))
        ax.add_patch(Rectangle((0, zt - d - 0.3), 20, 0.3, color=CU))
        ax.add_patch(Rectangle((9, zt + 0.3), 2, 0.6, color=PART))
        ax.text(10, zt + 1.15, "small part (side S)", ha="center", fontsize=8)
        if not local:
            stack(ax, 0, 20, zt, d, 4)
            ax.set_title("default rule: 4 sub-gaps of d/4 everywhere the copper is absent", fontsize=9)
            ax.annotate("", xy=(10, zt - d / 4), xytext=(10, zt), arrowprops=dict(arrowstyle="<->"))
            ax.text(10.4, zt - d / 8, "d/4 > 0.05 S:\nheat spreads\nin the first sub-gap", fontsize=7, va="center")
        else:
            z = 1
            for (x0, x1, n), ytxt in (((0, 20, 4), zt - d - 0.9), ((4.5, 15.5, 8), zt - d - 1.5), ((7, 13, 16), zt - d - 2.1)):
                ax.add_patch(Rectangle((x0, zt - d), x1 - x0, d, color=FR4, zorder=z))     # the finer zone covers the coarser lines
                for k in range(1, n):
                    ax.plot([x0, x1], [zt - d * k / n] * 2, color="#2f6f2f", lw=0.8, zorder=z + 1)
                ax.text(x0 + 0.2 if n < 16 else 10, ytxt, f"{n} sub-gaps" + (" (elsewhere)" if n == 4 else ""), ha="left" if n < 16 else "center", fontsize=7)
                z += 2
            ax.set_title("local rule: 16 under the part, 8 around, 4 elsewhere (nested depths)", fontsize=9)
        ax.text(0.2, zt + 0.55, "copper", fontsize=7)
        ax.text(0.2, zt - d - 0.25, "copper (absent in the window or the other layer)", fontsize=7)
    fig.suptitle("Fig. 1  Sub-layers under a small part over a thick laminate (section, vertical scale exaggerated)", fontsize=10)
    fig.savefig(OUT / "fig_01_small_part_sublayers.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_edge():
    """!
    @brief Figure 02: the board edge, the film of the whole slab on the copper node against laminate nodes at the edge.
    @return None
    """
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, nodes in zip(axes, (False, True)):
        ax.set_xlim(0, 12)
        ax.set_ylim(0, 7)
        ax.axis("off")
        zt, d = 5.5, 4.0
        ax.add_patch(Rectangle((0, zt), 10, 0.3, color=CU))
        ax.add_patch(Rectangle((0, zt - d - 0.3), 10, 0.3, color=CU))
        ax.add_patch(Rectangle((0, zt - d), 10, d, color=FR4))
        for yy in (zt + 0.15, zt - d - 0.15):
            ax.plot([9.9], [yy], "ko", ms=4)
        if nodes:
            for k in range(1, 4):
                ax.plot([8.5, 9.9], [zt - d * k / 4] * 2, color="#2f6f2f", lw=0.8)
                ax.plot([9.9], [zt - d * k / 4], "o", color="#2f6f2f", ms=3)
            ax.set_title("laminate nodes in the cells at the edge: the laminate loses heat at its own temperature", fontsize=9)
            for k in range(0, 5):
                ax.annotate("", xy=(11.2, zt - d * k / 4 + (0.15 if k == 0 else (-0.15 if k == 4 else 0))), xytext=(10, zt - d * k / 4 + (0.15 if k == 0 else (-0.15 if k == 4 else 0))),
                            arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1.0 + (0.6 if k in (0, 4) else 0)))
        else:
            ax.set_title("default: the film h_side x (whole slab) acts on the copper node temperature", fontsize=9)
            for yy, w in ((zt + 0.15, 1.0), (zt - d - 0.15, 1.0)):
                ax.annotate("", xy=(11.2, yy), xytext=(10, yy), arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1.6))
            ax.add_patch(Rectangle((10, zt - d - 0.3), 0.15, d + 0.6, fill=False, ec="#1f77b4", ls="--", lw=0.8))
            ax.text(10.4, zt - d / 2, "film on the\nwhole slab\nat the copper\ntemperature", fontsize=7, va="center")
        ax.text(0.2, zt + 0.5, "copper node", fontsize=7)
        ax.text(0.2, zt - d / 2, "laminate (k_z 0.3 W/mK between the copper layers)", fontsize=7)
    fig.suptitle("Fig. 2  The edge of a laminated board (section): why a large h_side reads low", fontsize=10)
    fig.savefig(OUT / "fig_02_edge_film.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_solid():
    """!
    @brief Figure 03: slabs of the 3D solid, 4 per gap against slabs by thickness, and the face term.
    @return None
    """
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, n, title in zip(axes, (4, 16), ("as built: 4 equal slabs per gap", "proposed: clip(ceil(d / 0.2 mm), 4, 16) slabs, and the face term")):
        ax.set_xlim(0, 12)
        ax.set_ylim(0, 8)
        ax.axis("off")
        zt, d = 6.0, 4.5
        ax.add_patch(Rectangle((0, zt), 12, 0.3, color=CU))
        ax.add_patch(Rectangle((0, zt - d - 0.3), 12, 0.3, color=CU))
        ax.add_patch(Rectangle((5, zt + 0.3), 2, 0.6, color=PART))
        ax.add_patch(Rectangle((0, zt - d), 12, d, color=FR4))
        for k in range(1, n):
            ax.plot([0, 12], [zt - d * k / n] * 2, color="#2f6f2f", lw=0.7)
        ax.set_title(title, fontsize=9)
        ax.text(0.2, zt - d / 2, f"gap d = 1.6 mm: {n} slabs of {1.6 / n:.2f} mm", fontsize=8, bbox=dict(fc="white", ec="none", alpha=0.8))
        if n == 16:
            ax.annotate("face term\nq'' t_cu / (2 k_z)", xy=(6, zt), xytext=(8.5, zt + 1.2), fontsize=7, arrowprops=dict(arrowstyle="->"))
    fig.suptitle("Fig. 3  Slabs of the 3D solid across an insulating gap (section, vertical scale exaggerated)", fontsize=10)
    fig.savefig(OUT / "fig_03_solid_slabs.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_transition():
    """!
    @brief Figure 07 (review): the lateral links of the laminate across the face between a cell with a fine chain and one with a coarser chain (local rule, left) and between a flagged
           cell and one without interior nodes (the program's rule and the edge band, right). The ratios are the ones measured in README 7.2.
    @return None
    """
    import numpy as np
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    cases = ((8, 4, "level 8 | level 4 (local rule)", "lateral laminate conductance across the face:\n0.68 of the slab's (harmonic mean of s and 2s)"),
             (4, 1, "flagged, 4 sub-gaps | not flagged (edge band, program's rule)", "lateral laminate conductance across the face:\n0.40 of the slab's (d/8 against d/2)"))
    for ax, (nf, nc, title, note) in zip(axes, cases):
        ax.set_xlim(0, 10)
        ax.set_ylim(-1.6, 7.2)
        ax.axis("off")
        zt, d = 6.0, 5.0
        ax.add_patch(Rectangle((0, zt), 10, 0.3, color=CU))
        ax.add_patch(Rectangle((0, zt - d - 0.3), 10, 0.3, color=CU))
        ax.add_patch(Rectangle((0, zt - d), 10, d, color=FR4))
        ax.plot([5, 5], [zt - d - 0.3, zt + 0.3], color="k", lw=1.0, ls=":")
        zf = [zt - d * k / nf for k in range(nf + 1)]
        zc = [zt - d * k / nc for k in range(nc + 1)]
        for z in zf:
            ax.plot(2.5, z, "o", color="#2f6f2f", ms=5)
        for z in zc:
            ax.plot(7.5, z, "o", color="#2f6f2f", ms=5)
        for z in zf:
            if any(abs(z - y) < 1e-9 for y in zc):
                ax.plot([2.6, 7.4], [z, z], color="#1f77b4", lw=1.6)
            else:
                ax.plot([2.6, 4.9], [z, z], color="#c0504d", lw=1.0, ls="--")
                ax.text(4.95, z, "x", color="#c0504d", va="center", fontsize=9)
        ax.text(2.5, zt + 0.7, f"{nf} sub-gaps", ha="center", fontsize=8)
        ax.text(7.5, zt + 0.7, f"{nc} sub-gap{'s' if nc > 1 else ''}" + (" (copper nodes hold d/2)" if nc == 1 else ""), ha="center", fontsize=8)
        ax.text(5, -0.9, note, ha="center", fontsize=8)
        ax.set_title(title, fontsize=9)
    fig.suptitle("Fig. 7  Lateral links of the laminate at a change of chain (blue: link at a common depth; red: a node with no neighbour)", fontsize=10)
    fig.savefig(OUT / "fig_07_level_transition.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_small_part()
    fig_edge()
    fig_solid()
    fig_transition()
