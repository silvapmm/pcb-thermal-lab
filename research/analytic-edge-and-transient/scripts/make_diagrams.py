#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Diagrams of the analytic-edge-and-transient investigation (no data, no program): fig_01 the edge of a board with unequal layers, fig_03 the smeared and the local heatsink in the transient.

@details Run from the repository root: .venv/bin/python research/analytic-edge-and-transient/scripts/make_diagrams.py
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
from matplotlib.patches import Rectangle   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(ROOT))

import diagram_kit as dk   # noqa: E402

FIG = os.path.join(ROOT, "figures")


def fig_01():
    """!
    @brief Cross-section at the board edge: thick copper layer, thin copper layer, the edge film of each slab, and the common beta against the per-layer beta.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 4.2, 1, 2, ratios=[1.3, 1])
    ax = axs[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    # Layer 1: full copper (high S, the edge film h s_1 is small compared with S_1); layer 2: copper at 20 % (low S)
    dk.layer(ax, 0.5, 3.6, 7.5, 0.7, dk.COPPER, "layer 1: full copper, S_1 large")
    dk.layer(ax, 0.5, 2.5, 7.5, 1.1, dk.FR4, "laminate gap (g)")
    dk.layer(ax, 0.5, 1.6, 7.5, 0.9, dk.FR4)
    ax.text(4.25, 2.3, "layer 2: copper 20 %, S_2 small", ha="center", va="center", fontsize=7)
    dk.layer(ax, 1.6, 1.85, 1.0, 0.35, dk.COPPER)
    dk.layer(ax, 4.2, 1.85, 1.0, 0.35, dk.COPPER)
    dk.layer(ax, 6.5, 1.85, 1.0, 0.35, dk.COPPER)
    for y0, y1, lab, col in ((3.6, 4.3, "h s_1", dk.HEAT), (1.6, 2.5, "h s_2", dk.HEAT)):
        dk.arrow(ax, 8.0, (y0 + y1) / 2, 9.2, (y0 + y1) / 2, color=col, label=lab)
    ax.text(8.6, 4.55, "edge film per layer\n(its own slab s_l)", ha="center", fontsize=8)
    dk.arrow(ax, 3.5, 4.8, 3.5, 4.35, color=dk.BLUE, label="")
    ax.text(3.9, 4.65, "heater on layer 1", fontsize=8, color=dk.BLUE)
    ax.text(0.5, 0.8, "true edge condition of each layer:  S_l dtheta_l/dn = -h s_l theta_l,   beta_l = h s_l / S_l\n"
                      "layer 1: beta_1 small (copper carries the heat inward)    layer 2: beta_2 large (the laminate loses it at the edge)", fontsize=7.5)
    ax.text(0.5, 0.15, "program: one beta for every layer, beta0 = h sum(s_l) / sum(S_l)  - exact only when s_l / S_l is the same in all layers", fontsize=7.5)
    ax = axs[1]
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 5)
    dk.box(ax, 0.2, 3.8, 5.5, 0.8, "common-beta modal solve  (program)\nA a = q  with the Robin eigenfunctions of beta0", dk.AIR)
    dk.box(ax, 0.2, 2.3, 5.5, 0.9, "edge mismatch source  qc = -S_l (beta_l - beta0) x\n(values of theta_l on the four sides, projected)", "#f7e3c4")
    dk.arrow(ax, 2.95, 3.8, 2.95, 3.2, label="")
    dk.arrow(ax, 4.9, 2.75, 4.9, 3.8, color=dk.HEAT, label="")
    ax.text(5.0, 3.35, "a = A^-1 (q + qc(a))", fontsize=7.5, ha="right", color=dk.HEAT)
    dk.box(ax, 0.2, 0.7, 5.5, 0.9, "GMRES on a:  5 to 9 matrix-vector products\n(= 5 to 9 modal solves), exact for the per-layer edge", "#d9ead3")
    dk.arrow(ax, 2.95, 2.3, 2.95, 1.6)
    dk.save(fig, os.path.join(FIG, "fig_01_edge_per_layer.png"))


def fig_03():
    """!
    @brief Plan view and modal sketch: a heatsink smeared over the board against the same heatsink kept local.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 3.6, 1, 3)
    titles = ("the board (60 x 40 mm)", "program, transient:\nsmeared, one factor", "proposal: local conductances\ncouple the lowest K x K modes")
    for ax, t in zip(axs, titles):
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 4)
        ax.set_title(t, fontsize=9)
        ax.add_patch(Rectangle((0.3, 0.4), 5.4, 3.2, facecolor="#f2f2f2", edgecolor="k"))
    ax = axs[0]
    ax.add_patch(Rectangle((2.5, 1.5), 0.9, 0.9, facecolor=dk.HEAT, alpha=0.8))
    ax.text(2.95, 1.95, "part", ha="center", va="center", fontsize=7, color="w")
    ax.add_patch(Rectangle((3.8, 0.4), 1.9, 3.2, facecolor=dk.METAL, alpha=0.8, hatch="//"))
    ax.text(4.75, 3.2, "heatsink", ha="center", fontsize=8)
    ax.add_patch(Rectangle((2.4, 1.4), 1.1, 1.1, fill=False, edgecolor=dk.BLUE, linestyle="--"))
    ax.text(2.95, 1.1, "vias", ha="center", fontsize=7, color=dk.BLUE)
    ax = axs[1]
    ax.add_patch(Rectangle((0.3, 0.4), 5.4, 3.2, facecolor=dk.METAL, alpha=0.35))
    ax.text(3.0, 2.0, "extra h spread evenly\nover the whole board\n\nvias: conductance scaled\nso that the STEADY maximum\nmatches (one number)", ha="center", va="center", fontsize=8)
    ax.text(3.0, 0.1, "dynamics: the board cools as a whole, too fast (sink) or too slow (both)", ha="center", fontsize=7)
    ax = axs[2]
    ax.add_patch(Rectangle((3.8, 0.4), 1.9, 3.2, facecolor=dk.METAL, alpha=0.8, hatch="//"))
    ax.add_patch(Rectangle((2.4, 1.4), 1.1, 1.1, fill=False, edgecolor=dk.BLUE, linestyle="--"))
    ax.text(1.4, 3.1, "C: tile conductances\n(the steady model's matrix)", fontsize=7.5)
    ax.text(0.5, 0.65, "eigenproblem  (A + D P^T s C P D / W H) c = lam Cap c\non K x K modes x L layers; the modes above K stay uniform", fontsize=7)
    dk.save(fig, os.path.join(FIG, "fig_03_local_transient.png"))


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_01()
    fig_03()
