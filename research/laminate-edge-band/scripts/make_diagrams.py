#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of research/laminate-edge-band: the real section of a board edge with the paths of the heat (fig_01), the temperature field of the laminate half-gap at the edge from the independent
       solver (fig_02), and the cells of the layered network with the edge band and the half-cell film (fig_03).
@details No program is run except the independent half-gap solver of lib/halfgap_fd.py. Run (repository root): .venv/bin/python research/laminate-edge-band/scripts/make_diagrams.py
"""

import sys

import _bootband

import halfgap_fd as HG
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
import numpy as np                                                 # noqa: E402
from matplotlib.patches import Rectangle                           # noqa: E402

sys.path.insert(0, str(_bootband.R))
import diagram_kit as K                                            # noqa: E402

COPPER, FR4, HEAT, BLUE = K.COPPER, K.FR4, K.HEAT, K.BLUE


def fig_01():
    """!
    @brief Section of the board edge: the heat paths of the real board and of the program's cell.
    @return None
    """
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.4))
    for ax, which in zip(axs, ("real", "model")):
        ax.set_xlim(-0.6, 8.6)
        ax.set_ylim(-0.4, 5.0)
        ax.axis("off")
        ax.add_patch(Rectangle((0, 3.9), 8, 0.22, facecolor=COPPER, edgecolor="k"))
        ax.add_patch(Rectangle((0, 0.4), 8, 0.22, facecolor=COPPER, edgecolor="k"))
        ax.add_patch(Rectangle((0, 0.62), 8, 3.28, facecolor=FR4, edgecolor="k"))
        ax.text(7.6, 4.3, "copper (isothermal)", ha="right", fontsize=8)
        ax.text(7.6, 1.2, "laminate, $k_z = 0.3$, $k_{xy} = 0.9$ W/mK", ha="right", fontsize=8)
        ax.annotate("", (0, 0.1), (0, 4.4), arrowprops={"arrowstyle": "-", "color": BLUE, "lw": 3})
        ax.text(-0.15, 4.65, "edge film $h_s$", color=BLUE, fontsize=8, ha="center")
    ax = axs[0]
    ax.set_title("Real board: the laminate near the edge is cooler than the copper", fontsize=9)
    for z in (1.0, 1.7, 2.4, 3.1, 3.6):                                  # heat leaving the laminate sideways, shorter deeper inside the gap
        L = 0.9 * (1 - abs(z - 2.25) / 2.4) + 0.2
        ax.annotate("", (-0.55, z), (0.0, z), arrowprops={"arrowstyle": "-|>", "color": HEAT, "lw": 1.2})
    for z, x in ((3.75, 0.9), (0.75, 0.9)):                              # copper feeds the laminate through k_z
        ax.annotate("", (x, z - 0.9 if z > 2 else z + 0.9), (x, z), arrowprops={"arrowstyle": "-|>", "color": HEAT, "lw": 1.4, "ls": "--"})
        ax.annotate("", (x + 1.2, z - 0.9 if z > 2 else z + 0.9), (x + 1.2, z), arrowprops={"arrowstyle": "-|>", "color": HEAT, "lw": 1.4, "ls": "--"})
    ax.text(2.0, 2.25, "dashed: vertical feed\nthrough $k_z$ over about\n$d / 2$ from the edge", fontsize=8, color=HEAT)
    ax = axs[1]
    ax.set_title("The program's cell on full copper: whole slab at the copper temperature", fontsize=9)
    for x0 in (0.0, 1.6, 3.2):
        for y0, yh in ((3.9, 0.22), (0.4, 0.22)):
            ax.add_patch(Rectangle((x0, y0), 1.6, yh, facecolor="none", edgecolor="k", ls=":", lw=0.8))
    ax.add_patch(Rectangle((0, 0.4), 1.6, 3.72, facecolor="none", edgecolor="k", lw=1.5))
    ax.plot([0.8, 0.8], [4.0, 4.0], "ko")
    ax.plot([0.8, 0.8], [0.5, 0.5], "ko")
    ax.text(1.0, 4.35, "node", fontsize=8)
    for z in (4.0, 3.5, 3.0, 2.25, 1.5, 1.0, 0.5):                       # film on the whole slab at the copper temperature
        ax.annotate("", (-0.55, z), (0.0, z), arrowprops={"arrowstyle": "-|>", "color": HEAT, "lw": 1.2})
    ax.text(2.0, 2.6, "film $h_s \\times$ slab $\\times$ edge on the copper node:\nthe laminate loses as much as the copper\nwould, the board reads cold\n(-14 % at $h_s$ = 200, 3.2 mm)", fontsize=8, color=HEAT)
    K.save(fig, _bootband.FIGURES / "fig_01_edge_section_heat_paths.png")
    plt.close(fig)


def fig_02():
    """!
    @brief The laminate half-gap at the edge from the independent solver: temperature field and efficiency against the edge coefficient.
    @return None
    """
    d, kxy, kz = 3.2e-3, 0.9, 0.3
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1.3, 1]})
    ax = axs[0]
    xc, zc, th, eta = HG.solve(200.0, d, kxy, kz)
    X, Z = np.meshgrid(xc * 1e3, zc * 1e3)
    cs = ax.contourf(X, Z, th, levels=np.linspace(0.3, 1.0, 15), cmap="inferno")
    ax.contour(X, Z, th, levels=[0.5, 0.7, 0.9], colors="w", linewidths=0.7)
    ax.set_xlim(0, 8)
    ax.set_xlabel("distance from the edge (mm)")
    ax.set_ylabel("depth below the copper (mm)")
    ax.set_title(f"Half-gap d = 3.2 mm, $h_s$ = 200: efficiency {eta:.3f}", fontsize=9)
    ax.invert_yaxis()
    fig.colorbar(cs, ax=ax, label="$\\theta / \\theta_{Cu}$")
    ax = axs[1]
    h = np.logspace(0, 4, 40)
    import edge_rules as ER
    for dd, c in ((0.8, "tab:green"), (1.6, "tab:blue"), (3.2, "tab:red")):
        ax.semilogx(h, [ER.eta_laminate(x, dd * 1e-3, kxy, kz) for x in h], color=c, label=f"closed form, d = {dd} mm")
        hh = [10, 100, 1000]
        ax.plot(hh, [HG.solve(x, dd * 1e-3, kxy, kz)[3] for x in hh], "o", color=c, mfc="none")
    ax.set_xlabel("edge coefficient $h_s$ (W/m2K)")
    ax.set_ylabel("efficiency of the laminate edge film $\\eta$")
    ax.set_title("Closed form (lines) and independent finite volumes (circles)", fontsize=9)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(_bootband.FIGURES / "fig_02_halfgap_field_and_efficiency.png", dpi=105)
    plt.close(fig)


def fig_03():
    """!
    @brief The cells at the edge: the program's rule, the band of nodes, and the half-cell series film.
    @return None
    """
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 4.2))
    titles = ("as is: nodes only where copper is absent", "band: nodes in the cells within one margin of the edge", "band + half-cell film on the laminate nodes")
    for k, (ax, ttl) in enumerate(zip(axs, titles)):
        ax.set_xlim(-0.8, 6.4)
        ax.set_ylim(-0.3, 4.8)
        ax.axis("off")
        ax.set_title(ttl, fontsize=9)
        for i in range(5):
            for lay, y0 in (("top", 3.7), ("bot", 0.3)):
                ax.add_patch(Rectangle((i * 1.2, y0), 1.2, 0.2, facecolor=COPPER, edgecolor="k", lw=0.6))
            ax.add_patch(Rectangle((i * 1.2, 0.5), 1.2, 3.2, facecolor=FR4, edgecolor="k", lw=0.5, alpha=0.55 if (k > 0 and i < 3) else 0.25))
            if k > 0 and i < 3:
                for y in (1.3, 2.1, 2.9):
                    ax.plot(i * 1.2 + 0.6, y, "ko", ms=3)
                    ax.plot([i * 1.2 + 0.6] * 2, [y, y - 0.8], "k-", lw=0.6)
                if i == 2:
                    ax.text(i * 1.2 + 0.6, 4.35, "band", ha="center", fontsize=8)
            ax.plot(i * 1.2 + 0.6, 3.8, "ko", ms=3)
            ax.plot(i * 1.2 + 0.6, 0.4, "ko", ms=3)
        ax.annotate("", (0, 0.2), (0, 4.0), arrowprops={"arrowstyle": "-", "color": BLUE, "lw": 3})
        if k == 0:
            ax.text(3.0, 2.1, "one link per gap;\nlaminate film on the\ncopper node", ha="center", fontsize=8)
            for z in (0.6, 1.5, 2.4, 3.3):
                ax.annotate("", (-0.7, z), (0.0, z), arrowprops={"arrowstyle": "-|>", "color": HEAT, "lw": 1.1})
        if k >= 1:
            for z in (1.3, 2.1, 2.9):
                ax.annotate("", (-0.7, z), (0.0, z), arrowprops={"arrowstyle": "-|>", "color": HEAT, "lw": 1.1})
        if k == 2:
            ax.text(0.35, 4.55, "$g = g_0 / (1 + h_s\\,dx / 2k_{xy})$", fontsize=8, color=BLUE)
            ax.text(4.2, 2.1, "film behind half a cell\nof laminate", fontsize=8, ha="center")
    fig.tight_layout()
    fig.savefig(_bootband.FIGURES / "fig_03_cells_band_and_halfcell.png", dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    fig_01()
    fig_02()
    fig_03()
