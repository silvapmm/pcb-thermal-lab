#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Diagrams of the through-thickness investigation: fig_01 the section of a thick plate under a source with the temperature profile, the film term and the three levels (surface, column mean,
       bound); fig_02 the four options (A read-out, B sub-layers, C slabs in the 3D solid, D finite elements) drawn as the nodes they keep through the thickness; fig_06 the expand-and-collapse
       design of option B in the program (a flow of the Problem through the models and back).
@details No data and no program: the profile of fig_01 is the parabola of `lib/surface_readout.py` drawn with illustrative numbers (the caption says so).
         Run from the repository root: .venv/bin/python research/through-thickness-readout/scripts/make_diagrams.py
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import diagram_kit as D  # noqa: E402

FIG = os.path.join(HERE, "..", "figures")


def fig_01_section():
    """!
    @brief Section through a thick plate under a source: heat paths, the profile T(z), the film term, the column mean and the bound (illustrative numbers).
    """
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.6), gridspec_kw={"width_ratios": [1.25, 1]})
    a1.axis("off")
    a1.set_xlim(0, 10)
    a1.set_ylim(-1.3, 4.6)
    D.layer(a1, 0.5, 0.0, 9.0, 3.0, D.METAL)
    a1.text(9.3, 2.6, "plate, k, t", ha="right", fontsize=8)
    D.layer(a1, 3.5, 3.0, 3.0, 0.18, D.HEAT)
    a1.text(5.0, 3.55, "source  q'' = P / A", ha="center", fontsize=8, color=D.HEAT)
    for x in (3.9, 4.5, 5.0, 5.5, 6.1):
        D.arrow(a1, x, 3.6, x, 3.2, color=D.HEAT, width=1.2)
    for xe in (2.0, 8.0):                                          # heat spreading sideways inside the plate
        D.arrow(a1, 5.0, 2.6, xe, 2.0, color=D.HEAT, width=0.9)
    for x in (2.5, 4.0, 5.0, 6.0, 7.5):
        D.arrow(a1, x, 0.0, x, -0.7, color=D.BLUE, width=1.2)
    a1.text(5.0, -1.1, "bottom face, film h  (q_bot leaves)", ha="center", fontsize=8, color=D.BLUE)
    a1.plot([0.5, 9.5], [1.5, 1.5], "k:", lw=0.9)
    a1.text(9.4, 1.2, "node of a layered model = column mean (mid-thickness)", fontsize=7.5, ha="right")
    a1.annotate("", xy=(0.3, 3.0), xytext=(0.3, 1.5), arrowprops=dict(arrowstyle="<->", color="k"))
    a1.text(0.22, 2.25, "t/2", ha="right", fontsize=8)
    a1.set_title("Section under the source: the node is the column mean, the surface is hotter", fontsize=9)
    # Profile T(z): illustrative parabola, z downwards
    z = np.linspace(0, 1, 100)
    q_top, q_bot = 1.0, -0.35                                      # fluxes entering (illustrative, in units of q t / k)
    T = -q_top * z + (q_top + q_bot) * z * z / 2
    Tm = T.mean()
    a2.plot(T - Tm, z, color=D.HEAT, lw=2, label="T(z)  (parabola, illustrative)")
    a2.axvline(0, color="k", ls=":", lw=1)
    a2.invert_yaxis()
    d_top = T[0] - Tm
    a2.plot([d_top], [0], "o", color=D.HEAT)
    a2.annotate("surface", (d_top, 0.0), (d_top - 0.02, 0.12), fontsize=8, ha="right")
    a2.plot([0], [0.5], "s", color="k")
    a2.annotate("node = column mean", (0, 0.5), (0.03, 0.56), fontsize=8)
    a2.axvline(0.5, color="gray", ls="--", lw=0.8)
    a2.text(0.5, 0.95, "bound q''t/2k", rotation=90, fontsize=7.5, color="gray", ha="right", va="bottom")
    a2.annotate("", xy=(d_top, 0.02), xytext=(0, 0.02), arrowprops=dict(arrowstyle="<->", color=D.HEAT))
    a2.text(d_top / 2, 0.075, "t (2 q_top - q_bot) / 6k", ha="center", fontsize=8, color=D.HEAT)
    a2.set_ylabel("depth z / t (down)")
    a2.set_xlabel("T - column mean (units q'' t / k)")
    a2.set_xlim(-0.35, 0.62)
    a2.set_title("Profile through the thickness", fontsize=9)
    a2.legend(loc="lower left", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_01_section_profile.png"), dpi=105)
    plt.close(fig)


def _stack(ax, title, n, nodes, note, surface=False, hex_mesh=False):
    """!
    @brief One panel: a section of a plate with `n` nodes through the thickness.
    @param ax Axes.
    @param title Panel title.
    @param n Number of nodes (or rows of elements) through the plate.
    @param nodes True to draw the nodes at mid-slab, False to draw the elements' corner nodes.
    @param note Text under the panel.
    @param surface True to mark the surface read-out point.
    @param hex_mesh True to draw element boundaries as a mesh.
    """
    ax.axis("off")
    ax.set_xlim(0, 6)
    ax.set_ylim(-1.3, 4.3)
    h = 3.0 / n
    for i in range(n):
        D.layer(ax, 0.5, 3.0 - (i + 1) * h, 5.0, h, D.METAL if not hex_mesh else "#dfe6ea")
        if nodes:
            for x in (1.2, 2.2, 3.2, 4.2, 5.0):
                ax.plot([x], [3.0 - (i + 0.5) * h], "ko", ms=4)
        else:
            for x in np.linspace(0.5, 5.5, 6):
                ax.plot([x], [3.0 - i * h], "ko", ms=3.5)
    if not nodes:
        for x in np.linspace(0.5, 5.5, 6):
            ax.plot([x], [0.0], "ko", ms=3.5)
    D.layer(ax, 2.2, 3.0, 2.0, 0.12, D.HEAT)
    for x in (2.5, 3.2, 3.9):
        D.arrow(ax, x, 3.6, x, 3.2, color=D.HEAT, width=1.1)
    if surface:
        ax.plot([3.2], [3.0], "r^", ms=7)
        ax.annotate("surface value", (3.2, 3.0), (4.1, 3.95), fontsize=7.5, color="r", arrowprops=dict(arrowstyle="->", color="r"))
    ax.set_title(title, fontsize=9)
    ax.text(3.0, -0.4, note, ha="center", va="top", fontsize=7.5)


def fig_02_options():
    """!
    @brief The four options drawn as the nodes they keep through a thick plate.
    """
    fig, axs = plt.subplots(1, 5, figsize=(14.5, 3.9))
    _stack(axs[0], "today: one node", 1, True, "node = column mean\n(face film through t/2)")
    _stack(axs[1], "A: read-out", 1, True, "same solve; surface =\nnode + t(2q_top - q_bot)/6k", surface=True)
    _stack(axs[2], "B: sub-layers (FVM, FDM,\nLumped, Analytic)", 4, True, "N nodes, links (t/N)/(kA);\nsurface = top node + q t/(2Nk)", surface=True)
    _stack(axs[3], "C: 3D solid, N slabs", 4, True, "N copper slabs per layer\n(laminate slabs as today)", surface=True)
    _stack(axs[4], "D: finite elements", 4, False, "hexahedra through the copper;\ntop-face nodes ARE the surface", surface=True, hex_mesh=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_02_options.png"), dpi=105)
    plt.close(fig)


def fig_06_design():
    """!
    @brief Option B in the program: expand a thick layer into sub-layers before the solve and collapse the result after it.
    """
    fig, ax = D.canvas(11.5, 3.6)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    steps = [(0.1, "Problem\n(thick layers\nas drawn)", "#cfe3f5"), (2.2, "expand\n(new module):\nN sub-layers,\nmetal links,\nheater to sub-layer 1", "#f9e0b0"),
             (4.5, "solver\nFVM / FDM /\nAnalytic / Lumped\n(unchanged)", "#d9ead3"), (6.8, "collapse:\nlayer mean = mean\nof sub-layers;\nsurface = sub-layer 1\n+ q t / 2Nk", "#f9e0b0"),
             (9.1, "SteadyResult\n(L layers as before;\nnew array\n'surface')", "#cfe3f5")]
    for x, text, col in steps:
        D.box(ax, x, 1.2, 2.0, 1.9, text, color=col, size=7.5)
    for x in (2.1, 4.4, 6.7, 9.0):
        D.arrow(ax, x, 2.15, x + 0.1, 2.15)
    ax.text(6.0, 0.55, "rules: only layers with fill = 1 and thickness above a limit are expanded; the rest of the program sees L layers as before", ha="center", fontsize=8)
    D.save(fig, os.path.join(FIG, "fig_06_expand_collapse.png"))


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_01_section()
    fig_02_options()
    fig_06_design()
    print("figures written")
