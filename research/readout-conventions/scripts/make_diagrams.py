#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings without data: where each source reads the temperature (section of a board with a part), and the decision picture 'which temperature does my source report'.
@details Writes figures/fig_01_where_read.png and figures/fig_02_decision.png. Every number on the pictures is one that the README holds.
         Usage: .venv/bin/python research/readout-conventions/scripts/make_diagrams.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                # noqa: E402
from matplotlib.patches import Rectangle, FancyBboxPatch       # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")


def box(ax, x, y, w, h, text, fc="#eef2f7", ec="#33415c", fs=8.5):
    """!
    @brief A rounded text box.
    @param ax Axes.
    @param x Left.
    @param y Bottom.
    @param w Width.
    @param h Height.
    @param text Text.
    @param fc Face colour.
    @param ec Edge colour.
    @param fs Font size.
    @return None.
    """
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec=ec, lw=1.0))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def fig_where():
    """!
    @brief Figure 1: a section of a board with a part, and the temperature each source reads.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(0, 22)
    ax.set_ylim(-1.2, 11.5)
    ax.axis("off")
    ax.add_patch(Rectangle((6, 3.0), 10, 1.0, fc="#555", ec="k"))                     # package
    ax.text(11, 3.5, "package (die inside)", color="w", ha="center", va="center", fontsize=9)
    ax.add_patch(Rectangle((2, 2.7), 18, 0.18, fc="#c8782a", ec="k"))                 # top copper
    ax.add_patch(Rectangle((2, 1.2), 18, 1.5, fc="#b9d29a", ec="k"))                  # laminate
    ax.add_patch(Rectangle((2, 1.02), 18, 0.18, fc="#c8782a", ec="k"))                # bottom copper
    ax.text(21.0, 2.8, "copper 35 um", fontsize=8, va="center")
    ax.text(21.0, 1.95, "laminate", fontsize=8, va="center")
    ax.text(21.0, 1.1, "copper 35 um", fontsize=8, va="center")
    marks = [(11, 4.05, "psi_JT: top centre of the package surface (T_T)", "#1b4965", 6.8),
             (5.2, 2.9, "psi_JB: board temperature on the centre pin\nor the trace at the package edge (T_B)", "#7b2cbf", 8.6),
             (3.2, 2.9, "thermocouple / IR on the copper:\nthe SURFACE", "#c1121f", 6.0),
             (11, 2.7, "program node: the MEAN over the thickness\nof the copper layer (a thin layer: same value)", "#2a9d8f", -0.6)]
    for x, y, txt, c, ty in marks:
        ax.annotate(txt, xy=(x, y), xytext=(x if x > 6 else (x + 1.5 if x > 4 else x - 0.5), ty), fontsize=8.5, color=c, ha="center",
                    arrowprops=dict(arrowstyle="->", color=c, lw=1.4))
    ax.add_patch(Rectangle((15.0, 6.0), 6.8, 2.4, fc="white", ec="0.6"))
    ax.text(15.2, 8.2, "35 um copper: surface - mean", fontsize=8.5, va="top", weight="bold")
    ax.text(15.2, 7.6, "1.8 mK (3D, 2 W on 6 x 6 mm)\n0.6 to 3.8 mK on the 20 harness\nboards (bound)", fontsize=8.5, va="top")
    ax.text(11, 11.4, "Where the temperature is read: the surface of the board is what every probe touches;\nthe layered models carry the mean through the thickness of each layer", ha="center", fontsize=10, weight="bold", va="top")
    fig.savefig(os.path.join(OUT, "fig_01_where_read.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_decision():
    """!
    @brief Figure 2: the decision picture, which temperature does my source report and when does the choice matter.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 14)
    ax.axis("off")
    box(ax, 7.5, 12.2, 7, 1.3, "Which temperature do I need?", "#dde6f0", fs=11)
    box(ax, 0.3, 9.5, 6.4, 1.9, "Junction / case\n(datasheet theta, psi)\n=> board temperature +\npsi x P: psi_JB on the trace,\npsi_JT on the package top")
    box(ax, 7.8, 9.5, 6.4, 1.9, "A probe (thermocouple, IR)\non the copper or a\nmetal base\n=> the SURFACE value")
    box(ax, 15.3, 9.5, 6.4, 1.9, "Compare with a layered model\nor a fin => the layer MEAN;\nspreading resistance (Muzychka)\n=> SURFACE mean over the source")
    box(ax, 5.5, 6.0, 11, 2.2, "Is the layer thin for the heat?\n  Bi = h t / k  (h = film on the cooled face, t = thickness, k = metal)\n  and t / a (a = source side)", "#fff3d6", fs=10)
    box(ax, 0.3, 2.2, 6.4, 2.5, "Bi < 1e-3 and t / a < 0.1\n(35 to 105 um copper on FR-4,\nbusbars in air)\nsurface = mean within 0.1 %\n=> the choice does not matter", "#d9f0d9")
    box(ax, 7.8, 2.2, 6.4, 2.5, "t / a 0.1 to 0.5, Bi 1e-3 to 0.03\n(1.5 to 2 mm Cu / Al base,\nMCPCB base, spreader)\nsurface - mean 3 to 12 % of the rise\n=> show both; parabola read-out", "#ffe9b8")
    box(ax, 15.3, 2.2, 6.4, 2.5, "t / a >= 1 or Bi > 0.03\n(10 mm plate, cold plate,\ncase 2 plate of Muzychka)\n13 to 54 % of the rise\n=> surface is the headline of the probe;\nuse 3D / sub-layers, parabola over-reads", "#f6c7c0")
    for (x0, y0, x1, y1) in [(11, 12.2, 3.5, 11.4), (11, 12.2, 11, 11.4), (11, 12.2, 18.5, 11.4), (11, 9.5, 11, 8.2), (8, 6.0, 3.5, 4.7), (11, 6.0, 11, 4.7), (14, 6.0, 18.5, 4.7)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", color="0.3", lw=1.3))
    ax.text(11, 0.9, "Percentages: (surface - mean) / surface rise at the source centre; series of lib/plate_series.py, plates 5 to 12.5 a wide (a wider plate reads more; README 4.2, 4.3).", ha="center", fontsize=8.5)
    fig.savefig(os.path.join(OUT, "fig_02_decision.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_where()
    fig_decision()
