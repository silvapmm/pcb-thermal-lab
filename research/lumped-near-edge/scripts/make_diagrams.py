#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the thing itself: the rings of the Lumped network on a board when the part is near a side, and the equipotentials of the part with its mirror image.
@details Figures 1 and 2 of figures/. The rings are the program's own (same cell, same edges, same membership as lumped._one_node_network), drawn on a 100 x 80 mm board with a 5 mm part.
         The equipotentials are the contours of the total log potential of the part and its 8 images (lib/variants.py, _total_potential). Run from the repository root with PCBT_TREE set.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import variants as V  # noqa: E402
from pcbthermal.fvm import Network  # noqa: E402

FIG = Path(__file__).resolve().parents[1] / "figures"


def ring_map(p, cell):
    """!
    @brief Ring index of every cell and the footprint, as the program's one-node network builds them.
    @param p Problem with one heater.
    @param cell Cell in mm.
    @return (index array (ny, nx) with -1 on the footprint, net).
    """
    m = V.load("program")
    b = p.board
    nx, ny = int(round(b.width * 1000 / cell)), int(round(b.height * 1000 / cell))
    net = Network(p, nx, ny, assemble=False, with_blocks=True, ladder=False, cut_cells=False)
    cov = m._footprint_coverage(net, p.heaters[0])
    from scipy import ndimage
    foot = cov > 0
    dist = ndimage.distance_transform_edt(~foot, sampling=(net.dy, net.dx))
    edges = m.ring_edges(float(dist.max()), net.dx, net.dy, 10, a_eq=m._equivalent_radius(foot, net.dx, net.dy))
    idx = 1 + np.minimum(np.searchsorted(edges[1:], dist, side="left"), len(edges) - 2)
    idx[foot] = 0
    return idx, net


def fig_rings():
    """!
    @brief Figure 1: rings of the network for a part at a gap of 0, 5 and 40 mm from the left side.
    @return None.
    """
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    for a, gap in zip(ax, (0.0, 5.0, 40.0)):
        p = B.board(100, 80, 5, (gap + 2.5, 40.0))
        idx, net = ring_map(p, 0.5)
        a.imshow(idx, origin="lower", extent=(0, 100, 0, 80), cmap="Blues_r", vmin=-2, vmax=12, interpolation="nearest")
        a.contour(np.linspace(0.25, 99.75, idx.shape[1]), np.linspace(0.25, 79.75, idx.shape[0]), idx, levels=np.arange(0.5, 11), colors="k", linewidths=0.5)
        a.add_patch(plt.Rectangle((gap, 37.5), 5, 5, fc="#d6342c", ec="k"))
        if gap < 20:
            a.add_patch(plt.Rectangle((-gap - 5, 37.5), 5, 5, fc="none", ec="#d6342c", ls="--"))
            a.annotate("image", (-gap - 2.5, 43), (-8, 52), color="#d6342c", fontsize=8, arrowprops=dict(arrowstyle="->", color="#d6342c"))
        a.axvline(0, color="k", lw=3)
        a.set_xlim(-12, 100)
        a.set_title(f"gap {gap:g} mm: rings clipped by the board (white = outside)", fontsize=9)
        a.set_xlabel("x (mm)")
    ax[0].set_ylabel("y (mm)")
    fig.tight_layout()
    fig.savefig(FIG / "fig_01_rings_clipped_by_the_edge.png", dpi=130)


def fig_potentials():
    """!
    @brief Figure 2: distance contours (the rings) against the equipotentials of the part with its image, for a part 5 mm from the side.
    @return None.
    """
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    cell = 0.5
    p = B.board(100, 80, 5, (7.5, 40.0))
    idx, net = ring_map(p, cell)
    m = V.load("potlinks")
    cov = np.zeros((net.ny, net.nx))
    cov[int(37.5 / cell):int(42.5 / cell), int(5 / cell):int(10 / cell)] = 1.0
    xs, ys = (np.arange(net.nx) + 0.5) * cell, (np.arange(net.ny) + 0.5) * cell
    for a, images, title in ((ax[0], False, "one source: circles around the part (the program's rings)"), (ax[1], True, "source and its image: the flow is pushed away from the side")):
        U = m._total_potential(cov, net.dx, net.dy, net.ny, net.nx, images=images)
        a.contour(xs, ys, U, levels=14, cmap="viridis", linewidths=0.9)
        a.add_patch(plt.Rectangle((5, 37.5), 5, 5, fc="#d6342c", ec="k"))
        a.axvline(0, color="k", lw=3)
        a.set_xlim(0, 60)
        a.set_ylim(10, 70)
        a.set_aspect("equal")
        a.set_title(title, fontsize=9)
        a.set_xlabel("x (mm)")
    fig.tight_layout()
    fig.savefig(FIG / "fig_02_equipotentials_with_image.png", dpi=130)


def main():
    """!
    @brief Draw the figures.
    @return None.
    """
    FIG.mkdir(exist_ok=True)
    fig_rings()
    fig_potentials()


if __name__ == "__main__":
    main()
