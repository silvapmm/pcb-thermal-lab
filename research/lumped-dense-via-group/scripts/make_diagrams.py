#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Figures of the situation: the cross-section of a part over a via group with the two nodes C and A and the heat paths, and the plan view of the core on the 0.5 mm raster.
@details fig_01: section through the part (to scale in the layer order, not in the thickness): the copper planes, the FR-4, the part, the vias, the node A (outside the vias), the node C (over the
         vias) and the paths (A to C link, C to the lower planes through the barrels, A to ring 1, the film to the air). fig_02: the footprint of an 8 mm part over a 5 x 5 array at 1 mm pitch on the
         Lumped raster of 0.5 mm: the vias, the core mask of the program (cells within CORE_R d_nn of the CELL that holds each via) and the core mask from the via positions.
Usage: python research/lumped-dense-via-group/scripts/make_diagrams.py   (from the repository root)
"""

import os
import sys

import matplotlib
import matplotlib.colors
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                               # noqa: E402
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle             # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
OUT = os.path.join(os.path.dirname(HERE), "figures")


def fig_section():
    """!
    @brief Figure 1: the cross-section with the nodes and the heat paths.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.set_xlim(0, 20); ax.set_ylim(0, 10); ax.axis("off")
    ax.add_patch(Rectangle((1, 5.6), 18, 0.3, color="#b87333"))        # top plane
    ax.add_patch(Rectangle((1, 2.6), 18, 0.3, color="#b87333"))        # bottom plane
    ax.add_patch(Rectangle((1, 2.9), 18, 2.7, color="#c8d9a0"))        # FR-4
    ax.add_patch(Rectangle((5, 5.9), 10, 0.9, color="#444"))           # part
    ax.text(10, 6.35, "part (power P)", color="w", ha="center", va="center", fontsize=9)
    for x in (7.5, 8.75, 10, 11.25, 12.5):
        ax.add_patch(Rectangle((x - 0.12, 2.6), 0.24, 3.3, color="#d9a066"))
    ax.annotate("", xy=(5, 7.4), xytext=(15, 7.4), arrowprops=dict(arrowstyle="<->"))
    ax.text(10, 7.55, "footprint", ha="center", fontsize=9)
    ax.add_patch(Rectangle((7.2, 5.55), 5.6, 0.45, fill=False, ec="#c0392b", lw=2))
    ax.text(10, 8.4, "node C: core, the cells within 0.7071 d_nn of the vias\n(wells of the vias, own share of P)", ha="center", color="#c0392b", fontsize=9)
    ax.add_patch(Rectangle((5, 5.55), 2.2, 0.45, fill=False, ec="#2c6fb0", lw=2)); ax.add_patch(Rectangle((12.8, 5.55), 2.2, 0.45, fill=False, ec="#2c6fb0", lw=2))
    ax.text(3.0, 8.4, "node A: the rest of\nthe footprint (its share of P)", ha="center", color="#2c6fb0", fontsize=9)
    ax.add_patch(FancyArrowPatch((6.0, 5.3), (7.3, 5.3), arrowstyle="->", mutation_scale=14, color="#2c6fb0"))
    ax.text(5.6, 4.7, "A-C link (eq. 5.7)", ha="center", fontsize=8, color="#2c6fb0")
    for x in (8.75, 11.25):
        ax.add_patch(FancyArrowPatch((x + 0.4, 5.3), (x + 0.4, 3.2), arrowstyle="->", mutation_scale=14, color="#c0392b"))
    ax.text(10.0, 3.6, "barrels + wells (through the gap, d + 0.5 t_cu)", ha="center", fontsize=8, color="#c0392b")
    ax.add_patch(FancyArrowPatch((4.8, 5.75), (2.0, 5.75), arrowstyle="->", mutation_scale=14, color="#2c6fb0"))
    ax.text(2.9, 6.25, "A to ring 1\n(eq. 5.8) and rings", ha="center", fontsize=8, color="#2c6fb0")
    ax.text(10, 1.8, "bottom plane: C and A nodes again, then rings; film to the air on both faces", ha="center", fontsize=9)
    ax.text(10, 0.7, "Peak of the part = largest of: hottest point of A (field of A), C + micro peak, C + micro peak + bump (eq. 5.9 and text)", ha="center", fontsize=8.5)
    fig.savefig(os.path.join(OUT, "fig_01_part_over_via_group_section.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_core():
    """!
    @brief Figure 2: the core on the Lumped raster, program mask against the position-based mask.
    @return None.
    """
    import numpy as np
    import viastudy as v
    import variants as var
    from pcbthermal import lumped, viaconstriction
    from pcbthermal.lumped import Network
    p = v.board(2, 5, 1.0, 0.3, 8.0)
    b = p.board
    nx, ny = int(round(b.width * 1000 / 0.5)), int(round(b.height * 1000 / 0.5))
    net = Network(p, nx, ny, assemble=False, with_blocks=True, ladder=False, cut_cells=False)
    vias = viaconstriction.ViaSet(p)
    cov = lumped._footprint_coverage(net, p.heaters[0])
    prog = lumped._core_mask(net, cov, vias)
    true = var._true_core_mask(net, cov, vias)
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.8))
    sub = (slice(70, 90), slice(90, 110))
    for ax, m, t in zip(axs, (prog, true), ("core of the program", "core from the via positions (a copy)")):
        img = np.zeros(m.shape); img[cov > 0] = 1; img[m] = 2
        ax.imshow(img[sub], origin="lower", cmap=matplotlib.colors.ListedColormap(["white", "#b5cfe6", "#e67e22"]), extent=(90 * 0.5, 110 * 0.5, 70 * 0.5, 90 * 0.5), vmin=0, vmax=2)
        for x, y in zip(vias.x * 1000, vias.y * 1000):
            ax.add_patch(Circle((x, y), 0.15, fc="k"))
        ax.set_xlim(45, 55); ax.set_ylim(35, 45); ax.set_aspect("equal"); ax.set_title(f"{t}: {int(m.sum())} of {int((cov>0).sum())} cells", fontsize=9)
        ax.set_xlabel("x (mm)")
    fig.suptitle("8 mm part over 5 x 5 vias at 1 mm pitch, raster 0.5 mm (blue: footprint (node A); orange: core C; dots: vias)", fontsize=9)
    fig.savefig(os.path.join(OUT, "fig_02_core_mask_on_the_raster.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_section()
    fig_core()
