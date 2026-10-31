#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Schematic figures of the horizontal plate: the flow paths above and below a thin hot board, the three situations whose coefficients are compared, the numerical domains of the strip and the disc, and the characteristic length A/P of the shapes.
@details No data is computed (the curves and arrows are drawings of the mechanism). Writes figures/fig_01_flow_paths_of_a_horizontal_board.png, fig_02_three_situations.png,
         fig_03_numerical_domains.png and fig_04_characteristic_length.png (the numbers 05 and above belong to `make_figures.py`, one numbering for both).
         Run: .venv/bin/python research/horizontal-plate-h/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

from matplotlib.patches import Circle, Polygon, Rectangle         # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"
HOT = "#e07b6a"
HOT_LIGHT = "#f6c9c0"


def curve(ax, xs, ys, color, width=1.4, arrow=True):
    """!
    @brief A polyline with an arrow head at its end (streamline).
    @param ax Axes.
    @param xs x coordinates.
    @param ys y coordinates.
    @param color Line colour.
    @param width Line width.
    @param arrow Draw the arrow head.
    @return None.
    """
    ax.plot(xs, ys, color=color, linewidth=width, solid_capstyle="round")
    if arrow:
        ax.annotate("", (xs[-1], ys[-1]), (xs[-2], ys[-2]), arrowprops={"arrowstyle": "-|>", "color": color, "linewidth": width})


def board_section(ax, x0=0.0, x1=8.0, y=0.0, hot_up=True, hot_down=True, t=0.18):
    """!
    @brief Draw a thin board as a grey slab with a hot (red) skin on the faces that dissipate.
    @param ax Axes.
    @param x0 Left end.
    @param x1 Right end.
    @param y Mid height.
    @param hot_up Hot upper face.
    @param hot_down Hot lower face.
    @param t Thickness of the drawing.
    @return None.
    """
    ax.add_patch(Rectangle((x0, y - t), x1 - x0, 2 * t, facecolor="#9aa5b1", edgecolor="k", linewidth=0.8))
    if hot_up:
        ax.add_patch(Rectangle((x0, y + t), x1 - x0, 0.07, facecolor=HOT, edgecolor="none"))
    if hot_down:
        ax.add_patch(Rectangle((x0, y - t - 0.07), x1 - x0, 0.07, facecolor=HOT, edgecolor="none"))


def flow_paths():
    """!
    @brief Figure 1: the real section of a thin horizontal board with both faces hot: the air drawn in along the upper face towards the centre and up in a plume, the air that meets the lower face at its centre and flows out to the edges, and the warm air of the lower face that rises round the edge into the inflow of the upper face.
    @return None.
    """
    fig, ax = dk.canvas(12.4, 6.0)
    ax.set_xlim(-6.6, 14.6)
    ax.set_ylim(-3.6, 5.2)
    board_section(ax, 0.0, 8.0, 0.0)
    cx = 4.0
    # Upper face: thin hot layer thickest at the centre, inflow from both sides, plume
    xs = np.linspace(0, 8, 100)
    top = 0.25 + 0.55 * (1 - np.abs(xs - cx) / cx) ** 0.8
    ax.fill_between(xs, 0.25, top, color=HOT_LIGHT, alpha=0.9)
    curve(ax, [cx, cx, cx], [0.9, 2.6, 4.4], dk.HEAT, 2.2)
    ax.text(cx + 0.2, 4.5, "plume", color=dk.HEAT, fontsize=8)
    for sgn in (-1, 1):
        xe = cx + sgn * 4.0
        curve(ax, [xe + sgn * 2.2, xe + sgn * 0.8, cx + sgn * 2.6, cx + sgn * 0.7], [2.0, 1.3, 0.55, 0.55], dk.BLUE)
        curve(ax, [xe + sgn * 2.2, xe + sgn * 1.0, cx + sgn * 3.0, cx + sgn * 1.4], [3.2, 2.2, 1.45, 1.1], dk.BLUE, 1.0)
    ax.text(-6.4, 3.4, "air drawn in from the sides\nof the upper face, heated\nin a layer that thickens\ntowards the centre", fontsize=7, color=dk.BLUE, va="center")
    ax.text(cx + 0.35, 1.25, "centre of the upper\nface: thickest layer,\nlowest local h", fontsize=6.8, ha="left")
    # Lower face: stagnation, thin layer at the centre, outflow, rise at the edges
    for sgn in (-1, 1):
        curve(ax, [cx, cx + sgn * 1.2, cx + sgn * 2.6, cx + sgn * 3.7], [-1.0, -0.55, -0.5, -0.5], dk.HEAT, 1.8, arrow=False)
        curve(ax, [cx + sgn * 3.7, cx + sgn * 4.25, cx + sgn * 4.55, cx + sgn * 4.6], [-0.5, -0.75, -1.6, -2.6], dk.HEAT, 1.8, arrow=False)
        curve(ax, [cx + sgn * 4.6, cx + sgn * 4.4, cx + sgn * 4.0, cx + sgn * 3.8], [-2.6, -1.0, 0.8, 1.3], dk.HEAT, 1.2)
    curve(ax, [cx, cx, cx], [-3.3, -2.2, -0.9], dk.BLUE, 1.6)
    ax.text(cx + 0.25, -3.1, "cold air meets the lower\nface at its centre", fontsize=7, color=dk.BLUE)
    ax.text(-6.4, -1.9, "lower face: the thinnest layer at the centre\n(stagnation) and the highest local h; the\nwarm layer leaves at the edges and rises", fontsize=7, va="center")
    ax.text(13.0, 2.3, "the warm air of the\nlower face joins the\ninflow of the upper\nface: it is not\nambient air", fontsize=7, color=dk.HEAT, ha="center", va="center")
    ax.annotate("", (8.0, 0.0), (0.0, 0.0), arrowprops={"arrowstyle": "<->", "color": "k", "linewidth": 0.6}, zorder=5)
    ax.text(cx, -0.04, "board, width 2a", fontsize=6.5, ha="center", va="center", color="w")
    ax.text(-6.4, 4.8, "Thin horizontal board, both faces hot (the situation of the program's examples)", fontsize=8, weight="bold")
    dk.save(fig, OUT / "fig_01_flow_paths_of_a_horizontal_board.png")


def three_situations():
    """!
    @brief Figure 2: the three situations compared in this study: an isolated upper face (the plate of Lloyd and Moran, Goldstein and others: heated on the top only, flush in an insulating surround), an isolated lower face (Schulenberg, Aihara, Faw and Dullforce) and a thin free board with both faces hot.
    @return None.
    """
    fig, axs = dk.canvas(11.0, 4.6, 1, 3)
    titles = ("a. isolated upper face\n(back insulated, or flush in\nan insulating surround)", "b. isolated lower face\n(upper side insulated)", "c. thin free board,\nboth faces hot")
    for k, ax in enumerate(axs):
        ax.set_xlim(-1.2, 9.2)
        ax.set_ylim(-3.4, 4.2)
        ax.text(4.0, 3.9, titles[k], ha="center", va="top", fontsize=7.5)
        hot_up, hot_down = (k in (0, 2)), (k in (1, 2))
        board_section(ax, 0.0, 8.0, 0.0, hot_up=hot_up, hot_down=hot_down)
        if k == 0:                                                                     # insulating surround
            ax.add_patch(Rectangle((-1.2, -0.18), 1.2, 0.36, facecolor="#d9d9d9", edgecolor="k", linewidth=0.5))
            ax.add_patch(Rectangle((8.0, -0.18), 1.2, 0.36, facecolor="#d9d9d9", edgecolor="k", linewidth=0.5))
        if hot_up:
            curve(ax, [4, 4, 4], [0.6, 1.6, 2.4], dk.HEAT, 2.0)
            for sgn in (-1, 1):
                curve(ax, [4 + sgn * 4.6, 4 + sgn * 2.8, 4 + sgn * 0.8], [1.4, 0.7, 0.5], dk.BLUE)
        if hot_down:
            for sgn in (-1, 1):
                curve(ax, [4, 4 + sgn * 2.2, 4 + sgn * 3.8], [-0.55, -0.45, -0.45], dk.HEAT, 1.6)
            curve(ax, [4, 4, 4], [-2.8, -1.8, -0.8], dk.BLUE, 1.3)
        if k == 2:
            for sgn in (-1, 1):
                curve(ax, [4 + sgn * 4.0, 4 + sgn * 4.4, 4 + sgn * 4.0, 4 + sgn * 3.4], [-0.6, -1.4, 0.4, 0.9], dk.HEAT, 1.1)
        ax.text(4.0, -3.3, ["measured: Lloyd and Moran (electrochemical), Goldstein et al. (naphthalene), Fujii and Imura (water)",
                            "Schulenberg (theory), Aihara et al. and Faw and Dullforce (air)",
                            "the program's board; solved here (2D strip, axisymmetric disc)"][k], ha="center", va="top", fontsize=5.8, wrap=True)
    dk.save(fig, OUT / "fig_02_three_situations.png")


def numerical_domains():
    """!
    @brief Figure 3: the numerical domains of the strip (planar, half domain x >= 0) and the disc (axisymmetric, x = radius): the plate across the buoyancy direction, the symmetry axis, the boundary conditions of every edge.
    @return None.
    """
    fig, axs = dk.canvas(10.6, 5.0, 1, 2)
    for k, ax in enumerate(axs):
        ax.set_xlim(-1.2, 10.4)
        ax.set_ylim(-4.6, 9.8)
        ax.add_patch(Rectangle((0, -3.5), 9.0, 12.2, facecolor="#f3f7fb", edgecolor="k", linewidth=0.8))
        ax.plot([0, 2.2], [0, 0], color=HOT, linewidth=5, solid_capstyle="butt")
        ax.text(1.1, 0.35, "plate (both faces T = Tw)", ha="center", fontsize=6.8, color=HOT)
        ax.plot([0, 0], [-3.5, 8.7], color=dk.BLUE, linewidth=1.2, linestyle="--")
        ax.text(-0.15, 4.2, "axis x = 0:\npsi = 0, omega = 0,\ndT/dx = 0", fontsize=6.5, ha="right", va="center", color=dk.BLUE)
        ax.text(4.5, 9.0, "top: dT/dy = 0, d omega/dy = 0, d psi/dy = 0 (plume leaves)", fontsize=6.5, ha="center")
        ax.text(9.15, 2.6, "side: T = 0, omega = 0,\nd psi/dx = 0\n(air enters freely)", fontsize=6.5, ha="left", va="center")
        ax.text(4.5, -3.9, "bottom: T = 0, omega = 0, d psi/dy = 0 (air enters freely)", fontsize=6.5, ha="center")
        ax.annotate("", (0, -1.3), (2.2, -1.3), arrowprops={"arrowstyle": "<->", "color": "k"})
        ax.text(1.1, -1.9, "a = 1 (the length scale L)" if k == 0 else "R = 1", ha="center", fontsize=6.8)
        ax.text(4.5, 6.2, "free air: Boussinesq,\nno-slip on the plate,\ngravity along -y", fontsize=7, ha="center")
        ax.text(-1.1, 9.7, ["a. strip: planar flow, both faces, half domain", "b. disc: axisymmetric flow about x = 0 (x is the radius)"][k], fontsize=7.5, weight="bold", va="top")
        ax.text(4.5, -2.6, ["Nu = integral of -dT/dn over the plate; L = a = A/P", "Nu_R = (2 / R^2) integral of -dT/dn r dr; L = A/P = R/2: Nu_L = Nu_R / 2, Ra_L = Ra_R / 8"][k], fontsize=6.3, ha="center")
    dk.save(fig, OUT / "fig_03_numerical_domains.png")


def characteristic_length():
    """!
    @brief Figure 4: the characteristic length L = A/P (area over perimeter of one face) of the shapes the program meets: a long strip, a square and a disc, with the Rayleigh number scaled by L cubed.
    @return None.
    """
    fig, axs = dk.canvas(10.6, 4.2, 1, 3)
    ax = axs[0]
    ax.set_xlim(-1, 11); ax.set_ylim(-2.2, 6.2)
    ax.add_patch(Rectangle((0, 1), 10, 3, facecolor="#cfe3f5", edgecolor="k"))
    ax.annotate("", (0, 0.5), (10, 0.5), arrowprops={"arrowstyle": "<->"}); ax.text(5, -0.2, "length l (long)", ha="center", fontsize=7)
    ax.annotate("", (10.5, 1), (10.5, 4), arrowprops={"arrowstyle": "<->"}); ax.text(10.7, 2.5, "w", fontsize=8)
    ax.text(5, 5.7, "a. strip: A/P -> w/2\n(l >> w)", ha="center", va="top", fontsize=7.5)
    ax.text(5, 2.5, "A = w l,  P = 2 (w + l)", ha="center", fontsize=7)
    ax = axs[1]
    ax.set_xlim(-1, 11); ax.set_ylim(-2.2, 6.2)
    ax.add_patch(Rectangle((1.5, 0.5), 5, 5, facecolor="#cfe3f5", edgecolor="k"))
    ax.annotate("", (1.5, 0.0), (6.5, 0.0), arrowprops={"arrowstyle": "<->"}); ax.text(4, -0.7, "s", ha="center", fontsize=8)
    ax.text(4, 3.0, "A = s^2\nP = 4 s\nA/P = s/4", ha="center", fontsize=7.5)
    ax.text(4, 6.1, "b. square: A/P = s/4", ha="center", va="top", fontsize=7.5)
    ax.text(4, -1.5, "100 mm board: L = 25 mm", ha="center", fontsize=7)
    ax = axs[2]
    ax.set_xlim(-1, 11); ax.set_ylim(-2.2, 6.2)
    ax.add_patch(Circle((4, 3), 2.5, facecolor="#cfe3f5", edgecolor="k"))
    ax.plot([4, 6.5], [3, 3], color="k"); ax.text(5.25, 3.2, "R", fontsize=8, ha="center")
    ax.text(4, 3.0, "", fontsize=7)
    ax.text(4, 6.1, "c. disc: A/P = R/2", ha="center", va="top", fontsize=7.5)
    ax.text(4, -0.9, "Ra_R = 8 Ra_L,  Nu_R = 2 Nu_L\n(the solver works in R)", ha="center", fontsize=7)
    for a in axs:                                                                      # true shapes: the square is square and the disc round
        a.set_aspect("equal", adjustable="box")
    dk.save(fig, OUT / "fig_04_characteristic_length.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    flow_paths()
    three_situations()
    numerical_domains()
    characteristic_length()
