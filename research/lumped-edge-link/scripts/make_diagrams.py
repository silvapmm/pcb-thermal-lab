#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawing of the situation: a part near a side of the board, the rings of the Lumped network cut by the board, the heat paths and the mirror image of the side.
@details Figure 1 is computed from the program's own ring construction (pcbthermal.lumped.ring_edges and the distance transform on a 100 x 80 mm raster at 0.5 mm, a 6 mm part, gap
         5 mm from the left side): left, the rings with their number; right, the same part on an infinite sheet with its image (the potential that the first link lacks). No data of a study.
         Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-edge-link/scripts/make_diagrams.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import tree  # noqa: E402,F401
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from scipy import ndimage  # noqa: E402

from pcbthermal import lumped  # noqa: E402

FIG = Path(__file__).resolve().parents[1] / "figures"


def rings(W=100.0, H=80.0, side=6.0, gap=5.0, cell=0.5):
    """!
    @brief The ring index of every cell, as the program builds it.
    @param W Board width in mm.
    @param H Board height in mm.
    @param side Part side in mm.
    @param gap Gap from the part to the left side in mm.
    @param cell Cell in mm.
    @return (index array, footprint mask, edges in mm).
    """
    nx, ny = int(W / cell), int(H / cell)
    x = (np.arange(nx) + 0.5) * cell
    y = (np.arange(ny) + 0.5) * cell
    cx, cy = gap + side / 2, H / 2
    foot = (abs(x[None, :] - cx) < side / 2) & (abs(y[:, None] - cy) < side / 2)
    dist = ndimage.distance_transform_edt(~foot, sampling=(cell, cell))
    a_eq = np.sqrt(foot.sum() * cell * cell / np.pi)
    edges = lumped.ring_edges(float(dist.max()), cell, cell, 10, a_eq=a_eq)
    idx = np.where(foot, 0, 1 + np.minimum(np.searchsorted(edges[1:], dist, side="left"), len(edges) - 2))
    return idx, foot, edges


def fig_01():
    """!
    @brief Figure 1: the rings of the Lumped network around a part near a side, and the part with its image.
    @return None.
    """
    W, H, side, gap = 100.0, 80.0, 6.0, 5.0
    idx, foot, edges = rings(W, H, side, gap)
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw={"width_ratios": [1.25, 1]})
    a = ax[0]
    a.imshow(np.ma.masked_where(foot, idx % 2), origin="lower", extent=(0, W, 0, H), cmap="Blues", alpha=0.5, vmin=-0.5, vmax=2)
    a.add_patch(Rectangle((gap, H / 2 - side / 2), side, side, fc="#c0392b", ec="k"))
    a.contour(np.linspace(0, W, idx.shape[1]), np.linspace(0, H, idx.shape[0]), idx, levels=np.arange(0.5, 11, 1.0), colors="k", linewidths=0.6)
    a.add_patch(Rectangle((0, 0), W, H, fc="none", ec="k", lw=2))
    for k in (1, 2, 3, 4):
        a.text(gap + side + 1 + 2.2 * k ** 1.2, H / 2 + 0.5, str(k), fontsize=8)
    a.annotate("", xy=(0.3, H / 2), xytext=(gap - 0.2, H / 2), arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.5, ls="--"))
    a.annotate("", xy=(gap + side + 18, H / 2), xytext=(gap + side + 0.3, H / 2), arrowprops=dict(arrowstyle="->", color="#c0392b", lw=2))
    a.text(0.6, H / 2 + 9.5, "the side sends the heat back", fontsize=8, color="#c0392b")
    a.set_title("rings of the Lumped network (distance from the footprint), cut by the board", fontsize=9)
    a.set_xlabel("x (mm)")
    a.set_ylabel("y (mm)")
    a.set_aspect("equal")
    a.set_xlim(-2, 60)
    a.set_ylim(15, 65)
    b = ax[1]
    b.clear()
    b.set_xlim(-30, 30)
    b.set_ylim(-18, 18)
    b.set_aspect("equal")
    xc = gap + side / 2
    b.add_patch(Rectangle((xc - side / 2, -side / 2), side, side, fc="#c0392b", ec="k"))
    b.add_patch(Rectangle((-xc - side / 2, -side / 2), side, side, fc="none", ec="#c0392b", ls="--"))
    b.plot([0, 0], [-18, 18], "k", lw=2)
    for r in (8, 13, 19):
        t = np.linspace(-np.pi, np.pi, 200)
        b.plot(xc + r * np.cos(t), r * np.sin(t), color="#2471a3", lw=0.7)
    for r in (8, 13, 19):
        t = np.linspace(-np.pi, np.pi, 200)
        b.plot(-xc + r * np.cos(t), r * np.sin(t), color="#2471a3", lw=0.7, ls="--")
    b.text(xc, -side / 2 - 2.5, "part", ha="center", fontsize=8)
    b.text(-xc, -side / 2 - 2.5, "image", ha="center", fontsize=8)
    b.text(0.5, 15.5, "side", fontsize=8)
    b.set_title("the part and its image (insulated side = mirror):\nthe image doubles the potential beyond the side", fontsize=9)
    b.set_xlabel("x (mm)")
    fig.tight_layout()
    fig.savefig(FIG / "fig_01_rings_near_a_side.png", dpi=130)


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    fig_01()
