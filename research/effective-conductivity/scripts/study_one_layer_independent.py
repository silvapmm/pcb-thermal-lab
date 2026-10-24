"""!
@file study_one_layer_independent.py
@brief Do the corrected models of the program agree with the independent solver on a one-layer board, and how far were they before the corrections?

@details A review of the models found that the 3D solid had no laminate on a one-layer board (no dielectric gap, so the board was its copper alone); the
         program now builds the laminate of the layered models as four FR-4 slabs under the copper. This study runs a 60 x 60 mm one-layer board with full 35 um
         copper and a 6 x 6 mm part of 1 W, FR-4 isotropic at 0.3 W/mK (so that the independent solver, which has isotropic slabs, represents the same board),
         the film coefficients of a new board (10 W/m2K on the top face, under the part as well, and 15 on the bottom), for board thicknesses of 0.8, 1.6 and
         3.2 mm, in the independent solver (`lib/layered3d.py`), the 3D solid, the FVM and the 3D solid without its laminate (a board whose laminate is 1 um, what
         it used to see), the FVM with the laminate nodes switched off (laminate.LAMINATE_NODES = 0 in memory: one node with both films on it, the FVM before
         the correction of 0ea5f07) and the FDM, Lumped and Analytic models as they are now; then the 1.6 mm board with a 20 x 20 mm copper pad instead of full copper (the copper slab of the independent solver is copper in the pad
         and FR-4 elsewhere, the volume average the 3D solid uses on cells that the pad covers or not), the case where the laminate matters. The metric is the rise
         of the hottest copper cell. An earlier version had a column "FVM, laminate in series under the bottom film (candidate)", which typed
         1 / (1/h + t_lam/k) as the bottom coefficient; once the program has laminate nodes that counts the laminate twice, so it was replaced by the FVM before
         the correction. Run: .venv/bin/python research/effective-conductivity/scripts/study_one_layer_independent.py
         (from the repository root; about 1 minute).
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "lib"))
import layered3d as L                                          # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate        # noqa: E402
from pcbthermal import laminate                                # noqa: E402
from pcbthermal.model import Materials                         # noqa: E402

K_FR4, CU, H_TOP, H_BOTTOM, CELL = 0.3, 35e-6, 10.0, 15.0, 0.5
THICKNESSES_MM = (0.8, 1.6, 3.2)


def board(thickness_mm, pad=False):
    """!
    @brief The one-layer board of the study.
    @param thickness_mm Board thickness in mm.
    @param pad True for a 20 x 20 mm copper pad at the centre, False for full copper.
    @return Problem.
    """
    p = Problem.new(60.0, 60.0, layers=1, thickness_mm=thickness_mm, copper_um=CU * 1e6, ambient=25.0, h_top=H_TOP, h_bottom=H_BOTTOM, h_side=None,
                    materials=Materials(k_fr4_through=K_FR4, k_fr4_inplane=K_FR4))
    if pad:
        p.add_zone(1, rect=(20, 20, 40, 40))
    else:
        p.add_full_copper()
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    return p


def independent(thickness_mm, pad=False):
    """!
    @brief Rise of the hottest top copper cell in the independent solver.
    @param thickness_mm Board thickness in mm.
    @param pad True for a 20 x 20 mm copper pad at the centre, False for full copper.
    @return float Rise in K.
    """
    k_cu = Materials().k_copper
    if pad:
        xs = (np.arange(120) + 0.5) * CELL
        inside = (np.abs(xs[None, :] - 30.0) < 10.0) & (np.abs(xs[:, None] - 30.0) < 10.0)
        k_top = np.where(inside, k_cu, K_FR4)                     # copper in the pad, laminate elsewhere in the copper slab
    else:
        k_top = k_cu
    res = L.solve(CELL * 1e-3, 120, 120, [(CU, k_top, 1), (thickness_mm * 1e-3 - CU, K_FR4, 8)], (27e-3, 27e-3, 33e-3, 33e-3), 1.0, H_TOP, H_BOTTOM, film_under_source=True)
    return res["cell_max_source"]


def program(thickness_mm, model, pad=False):
    """!
    @brief Rise of the hottest point in one model of the program.
    @param thickness_mm Board thickness in mm.
    @param model Model key.
    @param pad True for a 20 x 20 mm copper pad at the centre, False for full copper.
    @return float Rise in K.
    """
    return simulate(board(thickness_mm, pad), SolverOptions(models=(model,), cell_mm=CELL)).results[model].t_max - 25.0


def program_before(thickness_mm, pad=False):
    """!
    @brief The FVM before the correction of the one-layer boards: the laminate nodes switched off in memory, so the copper node carries the laminate and both films.
    @param thickness_mm Board thickness in mm.
    @param pad True for a 20 x 20 mm copper pad at the centre, False for full copper.
    @return float Rise in K.
    """
    saved = laminate.LAMINATE_NODES
    laminate.LAMINATE_NODES = 0                                    # nodes() returns None: the one-node board of the program before 0ea5f07
    try:
        return program(thickness_mm, "fvm", pad)
    finally:
        laminate.LAMINATE_NODES = saved


def main():
    """!
    @brief Print the table and write out/one_layer_independent.json for the figures.
    @return None.
    """
    rows = {}
    others = ("fdm", "lumped", "analytic")
    print("| copper | board thickness (mm) | independent 3D (K) | 3D solid | 3D solid without the laminate (before) | FVM | FVM before (one node) | " + " | ".join(o.upper() if o == "fdm" else o.capitalize() for o in others) + " |")
    print("| :-- | --: | --: | --: | --: | --: | --: | " + " | ".join("--:" for _ in others) + " |")
    for pad, ts in ((False, THICKNESSES_MM), (True, (1.6,))):
        for t in ts:
            ref = independent(t, pad)
            s3, fv = program(t, "solid3d", pad), program(t, "fvm", pad)
            old = simulate(board(CU * 1e3 + 0.001, pad), SolverOptions(models=("solid3d",), cell_mm=CELL)).results["solid3d"].t_max - 25.0
            fv_old = program_before(t, pad)
            rest = {o: program(t, o, pad) for o in others}
            label = "20 mm pad" if pad else "full"
            rows[f"{label} {t:g}"] = {"pad": pad, "thickness_mm": t, "independent": ref, "solid3d": s3, "solid3d_before": old, "fvm": fv, "fvm_before": fv_old, **rest}
            cell = lambda v: f"{v:.2f} ({100 * (v / ref - 1):+.1f} %)"
            print(f"| {label} | {t:g} | {ref:.2f} | {cell(s3)} | {cell(old)} | {cell(fv)} | {cell(fv_old)} | " + " | ".join(cell(rest[o]) for o in others) + " |", flush=True)
    (HERE.parent / "out").mkdir(exist_ok=True)
    (HERE.parent / "out" / "one_layer_independent.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
