#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Figure 1: the footprint of a part over a via array on the 0.5 mm Lumped raster with the core mask of the program and of the candidate, at two placements (no data files, computed from the program's own functions).
@details Four panels: columns the program's mask (`lumped._core_mask`: each via moved to the centre of its cell) and the candidate's (`placement._vote`: area vote of a 0.1 mm sub-grid against the via positions), rows the
         placements 0 and 0.1875 mm along the diagonal. Grey cells: footprint (cells touched by the part); blue: core; dots: vias; red line: the part outline; dashed circle: the core radius of one via.
Usage: python research/lumped-zone-placement/scripts/make_diagrams.py   (from the repository root)
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                               # noqa: E402
from matplotlib.patches import Circle, Rectangle                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import placement as pl                                                        # noqa: E402
import viastudy as v                                                          # noqa: E402
from pcbthermal import lumped, viaconstriction                                # noqa: E402


def panel(ax, shift, rule, title):
    """!
    @brief Draw one panel.
    @param ax Matplotlib axes.
    @param shift Translation of the part and the array along the diagonal in mm.
    @param rule 'program' or 'vote'.
    @param title Panel title.
    @return None.
    """
    p = pl.shifted(v.board(n=5, pitch=1.0, part=8.0), shift, shift)
    with pl.patched(**({"mask": "vote", "member_tol": True} if rule == "vote" else {})):
        g = pl.geometry(p)
    net, cov, core = g["net"], g["cov"], g["mask"]
    dx = net.dx * 1e3
    x0, y0 = 50.0 - 6.5, 40.0 - 6.5
    for i in range(net.ny):
        for j in range(net.nx):
            x, y = j * dx, i * dx
            if x < x0 or x > x0 + 13 or y < y0 or y > y0 + 13:
                continue
            if cov[i, j] > 0:
                ax.add_patch(Rectangle((x, y), dx, dx, fc="#5a7fb0" if core is not None and core[i, j] else "#d0d0d0", ec="white", lw=0.6))
    h = p.heaters[0].polygon * 1e3
    ax.add_patch(Rectangle((h[:, 0].min(), h[:, 1].min()), h[:, 0].max() - h[:, 0].min(), h[:, 1].max() - h[:, 1].min(), fill=False, ec="#c03030", lw=1.4))
    vs = viaconstriction.ViaSet(p)
    ax.plot(vs.x * 1e3, vs.y * 1e3, "k.", ms=4)
    ax.add_patch(Circle((vs.x[12] * 1e3, vs.y[12] * 1e3), lumped.CORE_R * float(vs.d_nn[12]) * 1e3, fill=False, ls="--", ec="k", lw=0.8))
    ax.set_xlim(x0, x0 + 13)
    ax.set_ylim(y0, y0 + 13)
    ax.set_aspect("equal")
    ax.set_title(f"{title}\nfootprint {g['n_foot']} cells, core {g['n_core']}, share {g['share_coarse']:.2f} (exact {g['share_exact']:.2f})", fontsize=8)
    ax.tick_params(labelsize=7)


def main():
    """!
    @brief Draw figure 1 into figures/.
    @return None.
    """
    fig, axs = plt.subplots(2, 2, figsize=(9, 9))
    for r, sh in enumerate((0.0, 0.1875)):
        for c, rule in enumerate(("program", "vote")):
            panel(axs[r, c], sh, rule, f"{'program mask (via moved to its cell)' if rule == 'program' else 'candidate: area vote on positions'}, shift {sh} mm")
    fig.suptitle("5 x 5 vias at 1.0 mm under an 8 mm part, 0.5 mm Lumped raster: footprint (grey), core (blue), vias (dots), part (red)", fontsize=9)
    fig.tight_layout()
    out = os.path.join(os.path.dirname(HERE), "figures", "fig_01_core_mask_two_placements.png")
    fig.savefig(out, dpi=130)
    print(out)


if __name__ == "__main__":
    main()
