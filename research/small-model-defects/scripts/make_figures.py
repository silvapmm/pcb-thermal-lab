#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of research/small-model-defects: fig_02 (the far via against its distance), fig_03 (the FDM across a gap against the cell), fig_05 (the 3D solid with the via moved
       across a cell). The drawings (fig_01, fig_04) are made by make_diagrams.py.
@details Usage: python research/small-model-defects/scripts/make_figures.py   (from the repository root; about 4 minutes). The numbers are those that the study scripts print.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(ROOT / "releases" / "regression-harness" / "lib"))

import matplotlib                                                           # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402

import solid_gridline                                                       # noqa: E402
import study_far_via as far                                                 # noqa: E402
import study_fdm_gap as gap                                                 # noqa: E402
from pcbthermal import fdm                                                  # noqa: E402
from pcbthermal.api import SolverOptions, simulate                          # noqa: E402

OUT = HERE.parent / "figures"


def fig_far_via():
    """!
    @brief Change of the hottest temperature against the distance of the added via, FVM, Lumped (program) and Lumped (candidate grouping).
    @return None.
    """
    base = far.tmax(far.array(16), 1.0)
    dists = [5, 8, 10, 12, 15, 20, 25]
    f, lp, lc = [], [], []
    for d in dists:
        v = far.array(16) + [(30.0 - d, 30.0)]
        a = far.tmax(v, 1.0, models=("fvm", "lumped"))
        c = far.tmax(v, 1.0, variant="min_inf", models=("lumped",))
        f.append(a["fvm"] - base["fvm"])
        lp.append(a["lumped"] - base["lumped"])
        lc.append(c["lumped"] - base["lumped"])
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(dists, lp, "o-", color="#d62728", label="Lumped, program")
    ax.plot(dists, lc, "s-", color="#1f77b4", label="Lumped, candidate grouping")
    ax.plot(dists, f, "^--", color="k", label="FVM")
    ax.set_xlabel("distance of the added via from the part centre (mm)")
    ax.set_ylabel("change of the hottest temperature (K)")
    ax.set_title("One via added to a 4 x 4 array under an 8 mm part (60 x 60 mm, 2 layers, 1 mm cell)", fontsize=8)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_far_via_distance.png", dpi=140)


def fig_gap():
    """!
    @brief Error of the FDM (arithmetic and harmonic mean) against the converged FVM across a 3 and a 6 mm gap, against the cell.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    for ax, g in zip(axs, (3.0, 6.0)):
        cells = [1.0, 0.5, 0.25]
        ref = float(simulate(gap.gap_board(g, 1.0), SolverOptions(models=("fvm",), cell_mm=0.25)).results["fvm"].t_max) - 25.0
        ea = [100 * (float(fdm.solve_steady(gap.gap_board(g, 1.0), c, "arithmetic").t_max) - 25.0 - ref) / ref for c in cells]
        eh = [100 * (float(fdm.solve_steady(gap.gap_board(g, 1.0), c, "harmonic").t_max) - 25.0 - ref) / ref for c in cells]
        ev = [100 * (float(simulate(gap.gap_board(g, 1.0), SolverOptions(models=("fvm",), cell_mm=c)).results["fvm"].t_max) - 25.0 - ref) / ref for c in cells]
        ax.plot(cells, ea, "o-", color="#d62728", label="FDM, arithmetic mean (program)")
        ax.plot(cells, eh, "s-", color="#1f77b4", label="FDM, harmonic mean")
        ax.plot(cells, ev, "^--", color="k", label="FVM")
        ax.set_xscale("log")
        ax.set_xlabel("cell (mm)")
        ax.set_title(f"copper cut by a {g:g} mm gap on all 4 layers", fontsize=8)
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("hottest rise against the FVM at 0.25 mm (%)")
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_fdm_gap.png", dpi=140)


def fig_solid():
    """!
    @brief Hottest temperature of the 3D solid for a lone via moved by a fraction of a cell, program and split footprint, with the FVM.
    @return None.
    """
    import regress_boards as rb
    fig, ax = plt.subplots(figsize=(6.5, 4))
    cell = 1.0
    ss = [0.0, 0.05, 0.1, 0.25, 0.5]
    fv, sp, sc = [], [], []
    for s in ss:
        def prob():
            p = rb.build("plate_lone_via")
            p.vias[0].x += s / 1000.0
            p.vias[0].y += s / 1000.0
            return p
        fv.append(float(simulate(prob(), SolverOptions(models=("fvm",), cell_mm=cell)).results["fvm"].t_max))
        sp.append(float(simulate(prob(), SolverOptions(models=("solid3d",), cell_mm=cell)).results["solid3d"].t_max))
        with solid_gridline.using():
            sc.append(float(simulate(prob(), SolverOptions(models=("solid3d",), cell_mm=cell)).results["solid3d"].t_max))
    ax.plot(ss, sp, "o-", color="#d62728", label="3D solid, program")
    ax.plot(ss, sc, "s-", color="#1f77b4", label="3D solid, split on the line")
    ax.plot(ss, fv, "^--", color="k", label="FVM")
    ax.set_xlabel("shift of the via from the grid line (mm; the cell is 1 mm)")
    ax.set_ylabel("hottest temperature (degC)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig_05_solid3d_via_shift.png", dpi=140)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_far_via()
    fig_gap()
    fig_solid()
