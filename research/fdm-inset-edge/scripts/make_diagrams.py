#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation: a copper edge held inside the board, seen by the node-centred FDM (control volumes and the face between two nodes) and by the face-fill variant.
@details No data and no program: a cross-section of the strip between the wall and the copper (laminate strip, copper edge on a node), the control volumes of the nodes, the fill
         each node reads, and the sheet each face between two nodes reads in the program and in the variant. Writes `figures/fig_01_copper_edge_between_nodes.png`.
         Run from the repository root: `.venv/bin/python research/fdm-inset-edge/scripts/make_diagrams.py`.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                # noqa: E402
from matplotlib.patches import Rectangle                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "figures")


def fig_edge():
    """!
    @brief The copper edge on a node: control volumes, nodal fill and the two face rules.
    @return None.
    """
    fig, ax = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True, gridspec_kw={"height_ratios": [1.25, 1]})
    a = ax[0]
    x = [0, 1, 2, 3, 4, 5]
    edge = 2.0                                                  # the copper starts on node 2 (inset = two cells)
    a.add_patch(Rectangle((edge, 0.15), 3.6, 0.22, color="#c46f2c", ec="none"))
    a.text(3.6, 0.26, "copper (35 um)", ha="center", va="center", color="white", fontsize=9)
    a.add_patch(Rectangle((-0.2, -0.15), 5.8 + 0.0, 0.3, fc="#d9e3c7", ec="#7a8a60"))
    a.text(0.6, -0.0, "laminate strip", ha="center", va="center", fontsize=9, color="#3a4a20")
    for i in x:
        a.plot([i], [0.5], "o", color="#1f3a5f", ms=8)
        a.text(i, 0.68, f"node {i}", ha="center", fontsize=8)
        lo, hi = max(i - 0.5, 0), min(i + 0.5, 5.6)
        yy = 0.95 + 0.1 * (i % 2)
        a.plot([lo, hi], [yy, yy], "-", color="#1f3a5f", lw=2)
    a.axvline(edge, color="#b0261c", ls="--", lw=1)
    a.text(edge + 0.05, 1.28, "copper edge exactly on node 2", color="#b0261c", fontsize=9)
    a.text(-0.45, 0.95, "control\nvolume", fontsize=7, va="center", ha="right")
    a.annotate("wall (edge film)", xy=(0, 0), xytext=(-0.05, -0.55), arrowprops=dict(arrowstyle="->"), fontsize=8, ha="center")
    a.set_ylim(-0.7, 1.45)
    a.set_yticks([])
    a.set_title("Section along x through the strip between the wall and the copper (insulated top view of one layer)", fontsize=10)

    b = ax[1]
    fills = {0: 0.0, 1: 0.0, 2: 0.5, 3: 1.0, 4: 1.0, 5: 1.0}
    for i, f in fills.items():
        b.bar(i, f, width=0.9, color="#c46f2c", alpha=0.35)
        b.text(i, f + 0.03, f"{f:g}", ha="center", fontsize=8, color="#7a3a10")
    b.text(0.9, 0.42, "node 2 reads a half-copper sheet\n(its volume spans bare and copper)", ha="center", fontsize=8, color="#7a3a10")
    # sheet read by each face: program (harmonic of the nodal sheets) and variant (cell fill)
    faces = [(0.5, 0.0, 0.0), (1.5, 0.0, 0.0), (2.5, 0.667, 1.0), (3.5, 1.0, 1.0), (4.5, 1.0, 1.0)]
    for xf, prog, var in faces:
        b.plot([xf - 0.35, xf + 0.35], [prog] * 2, "-", color="#1f3a5f", lw=3, label="face sheet, program (harmonic mean of nodes)" if xf == 0.5 else None)
        b.plot([xf - 0.35, xf + 0.35], [var + 0.0] * 2, "--", color="#2a8a3a", lw=3, label="face sheet, variant (cell fill)" if xf == 0.5 else None)
    b.text(1.0, 0.12, "faces 0-1, 1-2 (bare cells): both read bare", fontsize=8, ha="center", color="#3a3a3a")
    b.text(3.2, 1.12, "face 2-3 (copper cell): program 0.67, variant 1", fontsize=8, ha="center", color="#2a6a30")
    b.set_ylim(-0.05, 1.28)
    b.set_ylabel("copper fraction / face sheet\n(1 = full copper)")
    b.set_xlabel("x (cells)")
    b.legend(loc="upper left", fontsize=8, frameon=False, bbox_to_anchor=(0.0, 0.93))
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_01_copper_edge_between_nodes.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_edge()
