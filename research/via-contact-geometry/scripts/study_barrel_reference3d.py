#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_barrel_reference3d.py
@brief Review check of the barrel rule: is the axisymmetric cell right, and is the constant a of d + a t_cu robust, against a second, independent reference?
@details The second reference is the independent Cartesian 3D solver `tests/helpers/layered3d.py` (imports nothing from the program; harmonic means, uniform plan cells),
         on a quarter of the square via unit cell (the via at the corner, the insulated sides are the symmetry planes): the plated wall is drawn as the plan cells
         whose centre lies in the annulus, their conductivity scaled so that the copper area of the wall is exact; the copper planes are continuous over the drill
         (the layered idealisation; `--holes` drills the inner planes, the outer ones stay whole because the flux covers the whole top); 1 W over the whole top, h_bottom 1e7 W/m2K on the bottom face (the program's board exactly, square, not
         the equal-area disc of the axisymmetric cell). The dielectric is isotropic (0.29 W/mK) in all three solvers so that they model the same board.
         Printed for each case: R of the 3D reference at two plan cells (25 and 50 across the quarter: 5 um for a 0.5 mm pitch), R of the axisymmetric cell, and the error of the FVM for (target ratio e^-1/4, a = 0, 0.5)
         and (target ratio 1, a = 0, 0.5, 1). Run from the repository root:
         `.venv/bin/python research/via-contact-geometry/scripts/study_barrel_reference3d.py [--holes] [--outliers]`; writes out/reference3d[_outliers][_holes].json.
"""

import argparse
import json
import logging
import math
import sys
import time

import _bootstrap  # noqa: F401  (paths)
import numpy as np

sys.path.insert(0, str(_bootstrap.REPO / "tests" / "helpers"))
import layered3d as L3  # noqa: E402

import axicell as AX  # noqa: E402
import barrel as BA  # noqa: E402
from pcbthermal import viawell as VW  # noqa: E402

logging.disable(logging.WARNING)


def _spd_solve(mat, rhs):
    """!
    @brief Sparse direct solve of the symmetric positive definite matrix of layered3d in SuperLU's symmetric mode (same answer as spsolve, a fraction of the memory).
    @param mat The matrix (CSC or CSR).
    @param rhs Right-hand side.
    @return numpy.ndarray solution.
    """
    lu = _SPLA.splu(mat.tocsc(), permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0, options=dict(SymmetricMode=True))
    return lu.solve(np.asarray(rhs, dtype=float))


import scipy.sparse.linalg as _SPLA  # noqa: E402
L3.spla = type("spla", (), {"spsolve": staticmethod(_spd_solve)})   # only the linear solve of the independent solver is replaced, not its discretisation
K_CU, K_D, T_PTH, H_BOT = 393.0, 0.29, 25e-6, 1.0e7
K_FILL = {"air": 0.026, "solder": 57.3}


def reference3d(n_layers, t_cu, gap, phi, pitch, k_fill, dx, holes=False):
    """!
    @brief R (K/W, mean top-face temperature over 1 W) of the via unit cell in the independent Cartesian 3D solver, on a quarter cell.
    @param n_layers Copper layers.
    @param t_cu Copper thickness in m.
    @param gap Dielectric gap in m.
    @param phi Drill (outer barrel diameter) in m.
    @param pitch Side of the square unit cell in m.
    @param k_fill Filler conductivity in W/mK.
    @param dx Plan cell in m (pitch / 2 must be a whole number of cells).
    @param holes True: the drill is cut through the inner copper planes too (filled with the filler; the outer planes stay whole, so that the flux over the whole top still lands on copper); False: planes continuous over the drill.
    @return float R in K/W.
    """
    half = pitch / 2
    n = int(round(half / dx))
    assert abs(n * dx - half) < 1e-9 * half
    c = (np.arange(n) + 0.5) * dx
    rr = np.hypot(c[None, :], c[:, None])
    r_bar, r_hole = phi / 2, phi / 2 - T_PTH
    hole = rr < r_hole
    wall = (rr >= r_hole) & (rr < r_bar)
    scale = (math.pi * (r_bar ** 2 - r_hole ** 2) / 4) / (wall.sum() * dx * dx)   # exact copper area of the quarter wall
    k_gap = np.full((n, n), K_D)
    k_gap[hole] = k_fill
    k_gap[wall] = K_CU * scale
    k_plane = np.full((n, n), K_CU)
    k_cu_full = k_plane.copy()
    if holes:
        k_plane[hole] = k_fill
    slabs = []
    for i in range(n_layers):
        outer = i in (0, n_layers - 1)                           # the outer planes stay whole (the flux covers the whole top, as in the program)
        slabs.append((t_cu, k_cu_full if outer else k_plane, 4))
        if i < n_layers - 1:                                     # graded through the gap: fine near the planes, where the wall meets them
            slabs += [(0.1 * gap, k_gap, 4), (0.8 * gap, k_gap, 4), (0.1 * gap, k_gap, 4)]
    res = L3.solve(dx, n, n, slabs, (0.0, 0.0, half, half), 0.25, 0.0, H_BOT)
    return res["mean_source"]                                    # a quarter at 0.25 W: the temperatures of the whole cell at 1 W


def program(n_layers, t_cu, gap, phi, pitch, k_fill, ratio, a, cell_mm=0.05):
    """!
    @brief R of the same board in the program's FVM, with a target ratio and a barrel rule installed in memory.
    @param n_layers Copper layers.
    @param t_cu Copper thickness in m.
    @param gap Dielectric gap in m.
    @param phi Drill in m.
    @param pitch Cell side in m.
    @param k_fill Filler conductivity in W/mK.
    @param ratio Target radius over drill radius (the program: e^-1/4).
    @param a Extra barrel length per gap in copper thicknesses.
    @param cell_mm Plan cell in mm (0.05, the smallest the program accepts; 8 to 16 cells across the pitch, converged by README 2.1).
    @return float K/W.
    """
    from pcbthermal import Problem, SolverOptions, analysis, simulate
    from pcbthermal.model import Materials
    side = pitch * 1e3
    t_board = n_layers * t_cu + (n_layers - 1) * gap
    p = Problem.new(side, side, n_layers, t_board * 1e3, t_cu * 1e6, ambient=0.0, h_top=0.0, h_bottom=H_BOT, h_side=0.0, via_plating=T_PTH,
                    materials=Materials(k_copper=K_CU, k_fr4_through=K_D, k_fr4_inplane=K_D))
    for layer in range(1, n_layers + 1):
        p.add_zone(layer, rect=(0.0, 0.0, side, side))
    p.add_heater(1, 1.0, rect=(0.0, 0.0, side, side))
    p.add_via(side / 2, side / 2, phi * 1e3, fill_k=k_fill)
    old = VW.TARGET_RATIO
    VW.TARGET_RATIO = ratio
    try:
        with BA.patched(a):
            res = simulate(p, SolverOptions(models=("fvm",), cell_mm=cell_mm)).results["fvm"]
    finally:
        VW.TARGET_RATIO = old
    return float(analysis.heater_stats(res, p)[0]["t_mean"])


CASES = [  # layers, t_cu um, gap mm, drill mm, filler
    (4, 18, 0.1, 0.3, "air"), (4, 18, 0.2, 0.3, "air"), (4, 18, 0.1, 0.6, "solder"),
    (4, 35, 0.1, 0.3, "air"), (4, 35, 0.2, 0.3, "air"), (4, 35, 0.4, 0.3, "air"), (4, 35, 0.2, 0.6, "air"),
    (4, 70, 0.1, 0.3, "air"), (4, 70, 0.2, 0.3, "air"), (4, 70, 0.4, 0.3, "air"), (4, 70, 0.2, 0.2, "air"), (4, 70, 0.2, 0.6, "air"),
    (2, 35, 0.2, 0.3, "air"), (2, 70, 0.1, 0.3, "air"), (6, 70, 0.2, 0.3, "air"),
]
OUTLIERS = [  # the cases where the axisymmetric sweep reads the program too RESISTIVE (README 2.2, positive branch): thin copper, thin gap, large or solder via
    (2, 18, 0.1, 0.5, "air"), (2, 18, 0.1, 0.3, "solder"), (2, 18, 0.2, 0.5, "solder"), (2, 35, 0.1, 0.5, "solder"), (4, 18, 0.1, 0.5, "solder"),
]
RULES = [("e-1/4", math.exp(-0.25), 0.0), ("e-1/4", math.exp(-0.25), 0.5), ("1", 1.0, 0.0), ("1", 1.0, 0.5), ("1", 1.0, 1.0)]


def main():
    """!
    @brief Run the sample and print the table.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--holes", action="store_true", help="drill the inner planes too")
    ap.add_argument("--only", type=int, default=None, help="run one case (index)")
    ap.add_argument("--outliers", action="store_true", help="run the positive-branch cases instead of the sample")
    args = ap.parse_args()
    rows = []
    base_cases = OUTLIERS if args.outliers else CASES
    cases = base_cases if args.only is None else [base_cases[args.only]]
    print("case | R3D(half/25) R3D(half/50) Rext | axicell err | FVM err: " + ", ".join(f"r={r} a={a}" for r, _, a in RULES))
    for nl, tcu_um, gap_mm, phi_mm, fill in cases:
        tcu, gap, phi = tcu_um * 1e-6, gap_mm * 1e-3, phi_mm * 1e-3
        pitch = phi + 0.2e-3
        kf = K_FILL[fill]
        t0 = time.time()
        r10 = reference3d(nl, tcu, gap, phi, pitch, kf, pitch / 50, args.holes)        # 25 and 50 plan cells across the quarter
        r5 = reference3d(nl, tcu, gap, phi, pitch, kf, pitch / 100, args.holes)
        rext = r5 + (r5 - r10) / 3.0                             # Richardson with order 1 (staircase): conservative, quoted beside r5
        stack = AX.equal_gap_stack(nl, nl * tcu + (nl - 1) * gap, tcu)
        rax = AX.unit_cell(pitch, phi, kf, stack, k_z=K_D, k_r=K_D) + 1.0 / (H_BOT * pitch * pitch)   # + the bottom film the axisymmetric cell leaves out
        rax_raw = rax - 1.0 / (H_BOT * pitch * pitch)
        errs = {f"{r}|{a}": 100.0 * (program(nl, tcu, gap, phi, pitch, kf, ratio, a) / r5 - 1.0) for r, ratio, a in RULES}
        row = dict(layers=nl, t_cu=tcu_um, gap=gap_mm, phi=phi_mm, fill=fill, r3d_10=r10, r3d_5=r5, r3d_ext=rext, axi=rax, axi_raw=rax_raw,
                   axi_err=100.0 * (rax / r5 - 1.0), axi_raw_err=100.0 * (rax_raw / r5 - 1.0), fvm_err=errs)
        rows.append(row)
        print(f"{nl}L {tcu_um:3d}um g{gap_mm:.2f} d{phi_mm:.1f} {fill:6s} | {r10:8.3f} {r5:8.3f} {rext:8.3f} | {row['axi_err']:+5.1f} (raw {row['axi_raw_err']:+5.1f}) | "
              + " ".join(f"{errs[f'{r}|{a}']:+6.1f}" for r, _, a in RULES) + f"   ({time.time() - t0:.0f} s)", flush=True)
    name = ("reference3d_outliers" if args.outliers else "reference3d") + ("_holes" if args.holes else "") + ".json"
    if args.only is None:
        with open(_bootstrap.OUT / name, "w") as fh:
            json.dump(rows, fh, indent=1)
        for key in [f"{r}|{a}" for r, _, a in RULES]:
            e = np.array([x["fvm_err"][key] for x in rows])
            thick = np.array([x["fvm_err"][key] for x in rows if x["t_cu"] >= 35])
            print(f"rule {key:9s}: all mean {e.mean():+6.2f} min {e.min():+6.2f} max {e.max():+6.2f} | >=35um mean {thick.mean():+6.2f} min {thick.min():+6.2f} max {thick.max():+6.2f}")


if __name__ == "__main__":
    sys.exit(main())
