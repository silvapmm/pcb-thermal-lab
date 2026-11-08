#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation: one cut cell with the quantities of the Robin term (fig 03) and the two chains compared (fig 04). No data, no program.
@details Run from the repository root: `.venv/bin/python research/bochkov-robin-check/scripts/make_diagrams.py`.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")


def fig_cell():
    """!
    @brief Figure 03: a cell cut by a curved edge, the centre, the foot r_G, the distance d, the piece length L, the cut face lengths, and the centre outside case.
    @return None
    """
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.6))
    for k, (bx0, title) in enumerate(((0.30, "centre inside the domain: d < 0, 1 - alpha d / mu > 1"), (-0.18, "centre outside (sliver cell): d > 0, 1 - alpha d / mu can reach 0"))):
        a = axs[k]
        a.set_aspect("equal")
        a.add_patch(plt.Rectangle((-0.5, -0.5), 1, 1, fill=False, lw=1.5))
        th = np.linspace(-0.6, 0.6, 100)
        R0 = 1.4
        xc = bx0 - R0
        a.fill_between(xc + R0 * np.cos(th), R0 * np.sin(th), -2, color="none")
        t = np.linspace(-0.7, 0.7, 200)
        bx, by = xc + R0 * np.cos(t), R0 * np.sin(t)
        a.fill_betweenx(by, -2, bx, color="#ffe9a8", alpha=0.6, zorder=0)
        a.plot(bx, by, color="#1f5fa8", lw=2)
        a.set_xlim(-1.0, 1.0); a.set_ylim(-0.8, 0.8)
        a.plot(0, 0, "ko")
        a.text(0.03, -0.06, "r_ij", fontsize=9)
        # foot of the perpendicular on the circle (centre at (xc, 0))
        fx = bx0
        a.plot([0, fx], [0, 0], "r-", lw=1.5)
        a.plot(fx, 0, "ro")
        a.text(fx + 0.02, 0.05, "r_G", color="r", fontsize=9)
        a.text(fx / 2, -0.1, "|d|", color="r", fontsize=10)
        a.annotate("L (piece in the cell)", xy=(bx[np.argmin(abs(by - 0.3))], 0.3), xytext=(0.2, 0.62), arrowprops=dict(arrowstyle="->"), fontsize=9)
        a.set_title(title, fontsize=9)
        a.set_xticks([]); a.set_yticks([])
    fig.suptitle("One cut cell: u at the centre r_ij, the boundary value at r_G, u_ij = u(r_G) + d du/dn (thesis eq. 1.11)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_cut_cell_robin.png"), dpi=130)
    plt.close(fig)


def fig_chain():
    """!
    @brief Figure 04: the thermal chain of the two forms (the same series film) and the floor.
    @return None
    """
    fig, ax = plt.subplots(figsize=(9, 2.6))
    ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 3)

    def box(x, y, w, h, txt, col):
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=col, ec="k"))
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=8)
    box(0.2, 1.0, 1.4, 1.0, "node u_ij\n(cell centre)", "#dde7f5")
    box(2.6, 1.0, 2.6, 1.0, "conduction over |d|\nR = |d| / (mu L)", "#ffe9a8")
    box(6.2, 1.0, 2.2, 1.0, "film 1/(alpha L)", "#ffd0d0")
    box(9.0, 1.0, 0.9, 1.0, "u_amb\n= g / alpha", "#dde7f5")
    for x0, x1 in ((1.6, 2.6), (5.2, 6.2), (8.4, 9.0)):
        ax.annotate("", xy=(x1, 1.5), xytext=(x0, 1.5), arrowprops=dict(arrowstyle="-"))
    ax.text(5, 0.35, "g_eff = alpha L / (1 + alpha d / mu)  (thesis eq. 1.14 = Barrett and others eq. 12 to 14);  d > 0 (centre outside) can make 1 + alpha d / mu <= 0 in eq. 1.14 with d signed as in the thesis", ha="center", fontsize=7)
    fig.savefig(os.path.join(FIG, "fig_04_series_film_chain.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_cell()
    fig_chain()
