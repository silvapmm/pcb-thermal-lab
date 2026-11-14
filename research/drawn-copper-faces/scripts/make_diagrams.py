#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the drawn-copper study: (fig_01) how a zone sets the cell fill, 4 x 4 samples against the exact area, for a copper edge that cuts the cells; (fig_02) the two ways of
       forming the face between two cells, the harmonic mean of the cell sheets against the flow through a window of pixels. No program run: the numbers drawn are computed from the geometry.
@details Run: `.venv/bin/python research/drawn-copper-faces/scripts/make_diagrams.py`. Writes `figures/fig_01_fill_sampling.png` and `figures/fig_02_face_rules.png`.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                           # noqa: E402
import numpy as np                                                        # noqa: E402
from matplotlib.patches import Rectangle                                  # noqa: E402
from matplotlib.path import Path                                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", ".."))
from pcbthermal.geometry import exact_coverage                            # noqa: E402

FIG = os.path.join(HERE, "..", "figures")
CU, BARE, EDGE = "#c8803a", "#e8e4d8", "#333333"


def fig_fill():
    """!
    @brief Figure 1: a corner of copper turned by 22.5 degrees over a grid of 1 mm cells, the 4 x 4 sample points of each cut cell and the fill they give against the exact fill.
    @return None.
    """
    ang = np.radians(22.5)
    # a copper square turned about the origin; the corner region shown is 6 x 4 cells
    c, s = np.cos(ang), np.sin(ang)
    poly = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], float) - [5, 5]
    poly = np.array([[c * x - s * y, s * x + c * y] for x, y in poly]) + [4.2, -1.2]
    nx, ny = 6, 4
    ex = exact_coverage(poly * 1e-3, nx, ny, 1e-3, 1e-3)
    path = Path(poly)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
    a = ax[0]
    for i in range(nx):
        for j in range(ny):
            a.add_patch(Rectangle((i, j), 1, 1, fc="none", ec="#999999", lw=0.8))
    a.fill(poly[:, 0], poly[:, 1], fc=CU, alpha=0.55, ec=EDGE, lw=1.4)
    samp = np.zeros((ny, nx))
    for i in range(nx):
        for j in range(ny):
            pts = np.array([[i + (k + 0.5) / 4, j + (m + 0.5) / 4] for k in range(4) for m in range(4)])
            ins = path.contains_points(pts)
            samp[j, i] = ins.mean()
            a.scatter(pts[:, 0], pts[:, 1], s=7, c=np.where(ins, "#7a3d00", "#777777"), zorder=3)
            if 0 < ex[j, i] < 1:
                a.text(i + 0.5, j + 0.5, f"{samp[j, i]:.3f}\n{ex[j, i]:.3f}", ha="center", va="center", fontsize=7.5, bbox=dict(fc="white", ec="none", alpha=0.8, pad=1), zorder=4)
    a.set_xlim(0, nx)
    a.set_ylim(0, ny)
    a.set_aspect("equal")
    a.set_title("4 x 4 samples (dots) and the fill of each cut cell:\nupper number sampled, lower number exact", fontsize=10)
    a.set_xlabel("x, cells of 1 mm")
    cut = (ex > 0) & (ex < 1)
    b = ax[1]
    b.scatter(ex[cut], samp[cut], c="#7a3d00", s=18)
    b.plot([0, 1], [0, 1], color="#888888", lw=1)
    b.set_xlabel("exact fill of the cell")
    b.set_ylabel("fill of the program (4 x 4 samples)")
    b.set_title(f"cut cells of this corner: {cut.sum()}; sampled fill is a multiple of 1/16,\nlargest error {np.abs(samp[cut] - ex[cut]).max():.3f} of a cell", fontsize=10)
    b.set_aspect("equal")
    fig.suptitle("Figure 1. How a zone sets the cell fill (a 22.5 degree corner, 1 mm cells): quantised to 1/16, not the exact area", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_01_fill_sampling.png"), dpi=130)
    plt.close(fig)


def fig_faces():
    """!
    @brief Figure 2: heat across a stripe, the harmonic mean of the two cell sheets against the flow through the window of pixels between the cell centres.
    @details The stripes of the study (copper 1.2 mm, bare 1.2 mm) are cut by a 1 mm grid; the heat runs across them (up). Left, the program: every cell is one number (its
             mixed sheet) and a face is the harmonic mean of two cell numbers. Right, the imported rule: the window between the two centres is solved on its pixels (10 x 10), the
             copper pixels carry the heat and the bare ones almost none, so a bare stretch in the window is a resistance in series.
    @return None.
    """
    fig, ax = plt.subplots(1, 2, figsize=(12, 5.2))
    n = 10
    for k, a in enumerate(ax):
        a.set_xlim(0, 3)
        a.set_ylim(0, 4)
        a.set_aspect("equal")
        a.set_xlabel("x, cells of 1 mm")
        # stripes running along x: copper where (y - 1.2) mod 2.4 < 1.2 ; shown over 4 cells in y, from y0 = 0.5
        for yy in np.linspace(0, 4, 41)[:-1]:
            fc = CU if ((yy + 0.05 - 0.6) % 2.4) < 1.2 else BARE
            a.add_patch(Rectangle((0, yy), 3, 0.1, fc=fc, ec="none", alpha=0.85))
        for i in range(4):
            a.axhline(i, color="#666666", lw=0.8)
        for i in range(4):
            a.axvline(i, color="#666666", lw=0.8)
    # left: cell sheets
    sh = []
    for j in range(4):
        y = np.linspace(j, j + 1, 41)[:-1] + 0.0125
        fr = np.mean(((y - 0.6) % 2.4) < 1.2)
        sh.append(fr)
        ax[0].text(1.5, j + 0.5, f"cell fill {fr:.2f}", ha="center", va="center", fontsize=9, bbox=dict(fc="white", ec="none", alpha=0.85))
    ax[0].annotate("", xy=(2.6, 2.5), xytext=(2.6, 1.5), arrowprops=dict(arrowstyle="->", lw=2))
    ax[0].text(2.65, 2.0, "face =\nharmonic\nmean of the\ntwo cell\nsheets", fontsize=8.5, va="center")
    ax[0].set_title("Program, drawn copper: one fill per cell,\nface = harmonic mean of the two cell sheets", fontsize=10)
    # right: window pixels between centres of cells 1 and 2 (y 1.5 to 2.5)
    for j in range(n):
        for i in range(n):
            y0 = 1.5 + j * 0.1
            fc = CU if (((y0 + 0.05 - 0.6) % 2.4) < 1.2) else BARE
            ax[1].add_patch(Rectangle((1.0 + i * 0.1, y0), 0.1, 0.1, fc=fc, ec="#aaaaaa", lw=0.3, alpha=0.9))
    ax[1].add_patch(Rectangle((1.0, 1.5), 1.0, 1.0, fc="none", ec=EDGE, lw=2))
    for x in (1.2, 1.5, 1.8):
        ax[1].annotate("", xy=(x, 2.5), xytext=(x, 1.5), arrowprops=dict(arrowstyle="->", lw=1.5, color="#003366"))
    ax[1].set_title("Imported copper (the proposal for zones): the window between the two\ncentres is solved on 10 x 10 pixels, copper and bare stretches in series", fontsize=10)
    fig.suptitle("Figure 2. The face between two cells across a stripe: mixed cell sheets against the flow through the window", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_02_face_rules.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_fill()
    fig_faces()
