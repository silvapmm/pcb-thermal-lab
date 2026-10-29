#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Schematic figures of the channel effect between close fins: the boundary layers that merge, the orientations of a finned block and what is known for each, and where a correction would enter the program.
@details No data is computed except the closed-form growth of a boundary layer (delta ~ sqrt(x), only to draw its shape) and the geometry of the sketches.
         Writes figures/fig_01_boundary_layers_in_the_channel.png, figures/fig_04_orientations_of_the_block.png and figures/fig_10_where_the_correction_enters.png
         (the numbers 02, 03, 05 to 09 belong to `make_figures.py`, one numbering for both).
         Run: .venv/bin/python research/fin-channel/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

from matplotlib.patches import Polygon, Rectangle                 # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"
HOT = "#e07b6a"
HOT_LIGHT = "#f6c9c0"


def channel_panel(ax, gap, title, note, merge_height):
    """!
    @brief One vertical channel between two hot fins: the thermal boundary layers that grow up the walls, the velocity profile at the entrance and at the exit.
    @param ax Axes.
    @param gap Width of the channel in drawing units.
    @param title Panel title.
    @param note Text under the panel.
    @param merge_height Fraction of the channel height at which the boundary layers meet (1 = they never meet, 0 = already at the entrance).
    @return None.
    """
    height, t = 10.0, 1.0
    x0 = 4.0
    ax.set_xlim(0, 12)
    ax.set_ylim(-5.0, 12.0)
    # the two fins (side view of two plates) and the base at the back is not drawn: the channel is seen from the side of the flow
    ax.add_patch(Rectangle((x0 - t, 0), t, height, facecolor=HOT, edgecolor="k", linewidth=0.8))
    ax.add_patch(Rectangle((x0 + gap, 0), t, height, facecolor=HOT, edgecolor="k", linewidth=0.8))
    ax.text(x0 - t / 2, height + 0.3, "fin", ha="center", fontsize=7)
    ax.text(x0 + gap + t / 2, height + 0.3, "fin", ha="center", fontsize=7)
    # boundary layer thickness: delta(x) = c sqrt(x), c chosen so that it reaches half the gap at merge_height * height
    xs = np.linspace(0.0, height, 120)
    c = (gap / 2.0) / np.sqrt(max(merge_height, 1e-3) * height)
    delta = np.minimum(c * np.sqrt(xs), gap / 2.0)
    ax.add_patch(Polygon(np.vstack([[x0, 0], [x0, height], np.column_stack([x0 + delta[::-1], xs[::-1]])]), closed=True, facecolor=HOT_LIGHT, edgecolor="none"))
    ax.add_patch(Polygon(np.vstack([[x0 + gap, 0], [x0 + gap, height], np.column_stack([x0 + gap - delta[::-1], xs[::-1]])]), closed=True, facecolor=HOT_LIGHT, edgecolor="none"))
    ax.plot(x0 + delta, xs, color=dk.HEAT, linewidth=1.0)
    ax.plot(x0 + gap - delta, xs, color=dk.HEAT, linewidth=1.0)
    # velocity profiles drawn as curves whose distance from the channel mouth is proportional to the speed: entrance (nearly flat, below) and exit (above)
    y = np.linspace(0, gap, 60)
    wall_dist = np.minimum(y, gap - y)
    d_exit = delta[-1]
    if d_exit < gap / 2.0 - 1e-6:
        r = np.clip(wall_dist / d_exit, 0, 1)
        u_exit = 0.55 + 0.45 * 0.0 + (r * (2 - r)) * 0.45 * (wall_dist < d_exit) + 0.45 * (wall_dist >= d_exit) * 0.0
        u_exit = np.where(wall_dist < d_exit, r * (2 - r) * 0.9, 0.9 * 0.6 + 0.0 * r)
    else:
        u_exit = 4.0 * (y / gap) * (1.0 - y / gap)
    u_in = np.where((wall_dist / (gap / 2.0)) < 0.08, wall_dist / (gap / 2.0) / 0.08, 1.0) * 0.55
    ax.plot(x0 + y, -1.4 * u_in, color=dk.BLUE, linewidth=1.3)
    ax.plot(x0 + y, height + 1.2 * u_exit, color=dk.BLUE, linewidth=1.3)
    for xa in np.linspace(x0 + gap * 0.25, x0 + gap * 0.75, 3):
        dk.arrow(ax, xa, -2.1, xa, -1.5, color=dk.BLUE, width=1.0)
    ax.text(x0 + gap / 2, -2.2, "air at ambient temperature", ha="center", fontsize=6.5, color=dk.BLUE)
    ax.set_title(title, fontsize=9)
    ax.text(6.0, -3.0, note, fontsize=7, va="top", ha="center")


def boundary_layers():
    """!
    @brief Figure 1: three channels (wide, near the optimum, narrow) with the boundary layers of the two walls and the velocity profile at the exit.
    @return None.
    """
    fig, axs = dk.canvas(10.6, 4.6, 1, 3)
    channel_panel(axs[0], 7.0, "a. wide gap: two separate boundary layers", "each wall behaves like an\nisolated plate: h of the plate", 1.6)
    channel_panel(axs[1], 3.6, "b. near the optimum: the layers just meet at the exit", "Ra_b about 50:\nmost heat for the volume", 1.0)
    channel_panel(axs[2], 1.4, "c. narrow gap: merged from near the entrance", "fully developed, parabolic profile:\nNu = Ra_b / 24, h falls with b^3", 0.12)
    dk.save(fig, OUT / "fig_01_boundary_layers_in_the_channel.png", "Channel between two hot vertical fins: thermal boundary layers (pink), velocity profiles at entrance and exit (blue)")


def orientation_panel(ax, kind):
    """!
    @brief One orientation of a finned block with the flow of air between the fins and a statement of what is known.
    @param ax Axes.
    @param kind "vertical", "up" or "down".
    @return None.
    """
    ax.set_xlim(0, 12)
    ax.set_ylim(-0.5, 10.5)
    if kind == "vertical":
        dk.layer(ax, 1.5, 1.0, 0.5, 8.0, dk.FR4, "")
        dk.layer(ax, 2.0, 2.0, 0.6, 6.0, dk.METAL, "")
        for k in range(5):
            dk.layer(ax, 2.6, 2.2 + k * 1.25, 3.5, 0.3, dk.METAL)
        ax.text(1.75, 9.3, "board", ha="center", fontsize=7)
        ax.text(4.3, 8.4, "fins stand out horizontally;\nthe channels between them are vertical", fontsize=7)
        for k in range(4):
            dk.arrow(ax, 5.0, 2.5 + k * 1.25, 5.0, 3.35 + k * 1.25, color=dk.BLUE, width=1.2)
        ax.annotate("", (6.7, 7.6), (6.7, 2.2), arrowprops={"arrowstyle": "<->", "color": "k"})
        ax.text(6.9, 4.8, "L", fontsize=9)
        ax.text(0.3, -0.2, "VERTICAL BOARD: Elenbaas channels.\nRead, reproduced: shape of Q(s) for s >= 6 mm,\nthe optimum spacing (README 4, 5)", fontsize=6.8, va="top")
    elif kind == "up":
        dk.layer(ax, 1.0, 1.0, 10.0, 0.5, dk.FR4, "board")
        dk.layer(ax, 2.0, 1.5, 8.0, 0.6, dk.METAL, "")
        for k in range(6):
            dk.layer(ax, 2.2 + k * 1.4, 2.1, 0.3, 3.0, dk.METAL)
        for k in range(3):
            dk.arrow(ax, 3.0 + k * 2.8, 5.2, 3.0 + k * 2.8, 6.4, color=dk.BLUE, width=1.2)
        dk.arrow(ax, 0.6, 3.3, 2.1, 3.3, color=dk.BLUE, width=1.0)
        dk.arrow(ax, 11.4, 3.3, 9.9, 3.3, color=dk.BLUE, width=1.0)
        ax.text(6, 7.4, "air comes in at the ends of the fins and rises:\nopen top, short vertical path (the fin height)", ha="center", fontsize=7)
        ax.text(0.3, -0.2, "HORIZONTAL BOARD, fins up.\nNo channel formula was read for it; only plot data\n(Dogan and Dogan 2017) exist, not reproduced", fontsize=6.8, va="top")
    else:
        dk.layer(ax, 1.0, 8.0, 10.0, 0.5, dk.FR4, "board")
        dk.layer(ax, 2.0, 7.4, 8.0, 0.6, dk.METAL, "")
        for k in range(6):
            dk.layer(ax, 2.2 + k * 1.4, 4.4, 0.3, 3.0, dk.METAL)
        ax.text(6, 3.0, "warm air is trapped under the base (closed top): it can\nonly leave sideways along the fins", ha="center", fontsize=7)
        dk.arrow(ax, 0.6, 5.2, 2.1, 5.2, color=dk.BLUE, width=1.0)
        dk.arrow(ax, 11.4, 5.2, 9.9, 5.2, color=dk.BLUE, width=1.0)
        ax.text(0.3, -0.2, "HORIZONTAL BOARD, fins down (the block of the\nprogram's examples). Not covered by any source read", fontsize=6.8, va="top")


def orientations():
    """!
    @brief Figure 4: the three ways a finned block hangs on a board and what the investigation can say about each.
    @return None.
    """
    fig, axs = dk.canvas(10.6, 4.4, 1, 3)
    for ax, kind, title in zip(axs, ("vertical", "up", "down"), ("a. vertical board", "b. horizontal board, block on top", "c. horizontal board, block underneath")):
        orientation_panel(ax, kind)
        ax.set_title(title, fontsize=9)
    dk.save(fig, OUT / "fig_04_orientations_of_the_block.png", "Which flow is between the fins depends on how the board hangs; the sources read cover case a")


def where_it_enters():
    """!
    @brief Figure 10: how the channel coefficient would enter the program: a loop around the existing solve, on the temperature of the block.
    @return None.
    """
    fig, ax = dk.canvas(10.6, 4.6)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6.6)
    dk.box(ax, 0.2, 4.6, 2.6, 1.2, "Problem\nblock with fins\n(gap, height, k)", dk.AIR)
    dk.box(ax, 3.6, 4.6, 2.8, 1.2, "block temperature\n(first guess: the\nuniform-h solve)", dk.AIR)
    dk.box(ax, 7.2, 4.6, 2.8, 1.2, "Ra_b = g beta theta b^4 Pr\n/ (nu^2 L)", "#f2e394")
    dk.box(ax, 10.8, 4.6, 3.0, 1.2, "Nu_b (composite) ->\nh_ch = Nu_b k / b\nfin efficiency, h_exp", "#f2e394")
    dk.box(ax, 10.8, 2.4, 3.0, 1.2, "blocks.exposed_h\n(used by the FVM, FDM,\nLumped and Analytic)", dk.COPPER, bold=True)
    dk.box(ax, 7.2, 2.4, 2.8, 1.2, "the existing solve\n(FVM, FDM, Lumped,\nAnalytic, 3D solid)", dk.AIR)
    dk.box(ax, 3.6, 2.4, 2.8, 1.2, "new block temperature\nchanged by < 0.05 K?", "#d9ead3")
    dk.box(ax, 0.2, 2.4, 2.6, 1.2, "result + warning\n(channel loss of the\nfinned face)", "#d9ead3", bold=True)
    for a, b in ((2.8, 3.6), (6.4, 7.2), (10.0, 10.8)):
        dk.arrow(ax, a, 5.2, b, 5.2)
    dk.arrow(ax, 12.3, 4.6, 12.3, 3.6)
    dk.arrow(ax, 10.8, 3.0, 10.0, 3.0)
    dk.arrow(ax, 7.2, 3.0, 6.4, 3.0)
    dk.arrow(ax, 3.6, 3.0, 2.8, 3.0, label="yes")
    dk.arrow(ax, 5.0, 3.6, 5.0, 4.6, label="no: repeat (3 to 5 solves)")
    ax.text(7.0, 0.9, "Measured on a copy (lib/program_patch.py): `blocks.exposed_h` replaced in memory; the program's files are untouched.\n"
                     "The 3D solid has its own copy of the fin ratio: the same effect is obtained there with the equivalent fin pitch.\n"
                     "Vertical board only (the validated case); orientation and channel length L are inputs the program does not have yet.", ha="center", fontsize=7.5)
    dk.save(fig, OUT / "fig_10_where_the_correction_enters.png", "A loop around the existing solve on the temperature of the block: the proposal of INTEGRATION.md")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    boundary_layers()
    orientations()
    where_it_enters()
