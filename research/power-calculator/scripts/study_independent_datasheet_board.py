"""!
@file study_independent_datasheet_board.py
@brief Does the board model that the calculator runs backwards give the right board resistance on the CSD17308Q3 datasheet board, checked against a solver that shares none of the program's code?

@details The calculator's answer on the datasheet board (README 4.1) is P = rise / R, so its error is the error of the board resistance R = (T_max under the part - T_amb) / P
         plus theta. This study checks R on the CSD17308Q3 board (38.1 x 38.1 x 1.52 mm, a 25.4 mm pad of 71 um copper on the top, nothing on the bottom) with the
         face coefficients fixed at the values the computed convection converges to at 1 W in calculator_validation.py, so that every solver sees the same films:
         (1) the program's FVM on the board as calculator_validation.py draws it (two layers, the bottom one without copper),
         (2) the program's FVM on the same board drawn as a one-layer board (laminate nodes of pcbthermal/laminate.py),
         (3) the program's 3D solid, and
         (4) the independent 3D solver research/solid3d-verification/lib/layered3d.py (patterned copper slab, 8 laminate slabs).
         The independent solver is isotropic, so the comparison is made with FR-4 isotropic at 0.3 W/mK in every solver (and once with the program's 0.3 / 0.9 W/mK
         for the program's own models), no edge loss (as calculator_validation.py). The second part checks the affine-in-power assumption of inverse.py: with
         constant coefficients T(P) at the measured point must be exactly linear; with computed coefficients the deviation from the two-run line is printed.

Usage: .venv/bin/python research/power-calculator/scripts/study_independent_datasheet_board.py   (from the repository root; about 1 minute)
"""

import copy
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "research", "solid3d-verification", "lib"))

import calculator_validation as cv                                          # noqa: E402
import layered3d as L3                                                      # noqa: E402
from pcbthermal import Problem, SolverOptions                               # noqa: E402
from pcbthermal.analysis import heater_stats                                # noqa: E402
from pcbthermal.api import _run_model, _solve_computed_h                    # noqa: E402

K_ISO = 0.3          # Isotropic FR-4 conductivity shared by every solver of part 1, W/mK
CELL_MM = 0.3        # 38.1 mm = 127 cells: the 3.3 mm footprint and its centre lie on cell edges


def converged_h():
    """!
    @brief Face coefficients the computed convection converges to on the datasheet board at 1 W.
    @return Tuple (h_top, h_bottom) in W/m2K.
    """
    res = _solve_computed_h(cv.csd17308q3_board(), "fvm", SolverOptions(models=("fvm",), cell_mm=0.5))[0]
    return res.extras["h_top"], res.extras["h_bottom"]


def board(h_top, h_bottom, layers=2, iso=True):
    """!
    @brief The datasheet board of calculator_validation.py with fixed face coefficients.
    @param h_top Top coefficient in W/m2K.
    @param h_bottom Bottom coefficient in W/m2K.
    @param layers 2 (as the validation draws it, bottom layer bare) or 1 (one-layer board).
    @param iso True for isotropic FR-4 at K_ISO.
    @return Problem.
    """
    if layers == 1:
        # The same board built as a one-layer board from the start (no copy of a two-layer stack-up)
        p = Problem.new(38.1, 38.1, 1)
        p.board.thickness, p.board.copper_thickness, p.board.h_side = 1.52e-3, [71e-6], None
        p.add_zone(1, rect=(19.05 - 12.7, 19.05 - 12.7, 19.05 + 12.7, 19.05 + 12.7))
        p.add_heater(1, 1.0, rect=(17.4, 17.4, 20.7, 20.7), name="Q1", theta=4.5)
    else:
        p = cv.csd17308q3_board()
    b = p.board
    b.h_mode, b.h_top, b.h_bottom = "manual", h_top, h_bottom
    if iso:
        b.materials.k_fr4_through = b.materials.k_fr4_inplane = K_ISO
    return p


def rise_program(p, model):
    """!
    @brief Board resistance seen by the hottest point under the part (rise per watt) in a model of the program.
    @param p Problem (1 W part).
    @param model Model key.
    @return float K/W.
    """
    res = _run_model(p, model, SolverOptions(models=(model,), cell_mm=CELL_MM))
    return heater_stats(res, p)[0]["t_max"] - p.board.ambient


def rise_independent(h_top, h_bottom, n_gap=8):
    """!
    @brief The same board resistance in the independent solver (copper slab patterned with the pad, the laminate isotropic).
    @param h_top Top coefficient in W/m2K.
    @param h_bottom Bottom coefficient in W/m2K.
    @param n_gap Sub-slabs of the laminate.
    @return float K/W.
    """
    n = int(round(38.1 / CELL_MM))
    xs = (np.arange(n) + 0.5) * CELL_MM
    # Fraction of every cell covered by the 25.4 mm pad (edges at 6.35 and 31.75 mm fall inside cells): area-weighted conductivity
    lo, hi = 19.05 - 12.7, 19.05 + 12.7
    f1 = np.clip((np.minimum(xs + CELL_MM / 2, hi) - np.maximum(xs - CELL_MM / 2, lo)) / CELL_MM, 0.0, 1.0)
    frac = f1[None, :] * f1[:, None]
    k_top = frac * 385.0 + (1.0 - frac) * K_ISO
    t_cu = 71e-6
    slabs = [(t_cu, k_top, 1), (1.52e-3 - 2 * t_cu, K_ISO, n_gap), (t_cu, K_ISO, 1)]     # The bottom copper slab of the drawn board is bare: laminate
    src = (17.4e-3, 17.4e-3, 20.7e-3, 20.7e-3)
    r = L3.solve(CELL_MM * 1e-3, n, n, slabs, src, 1.0, h_top, h_bottom, film_under_source=True)
    return r["cell_max_source"]


def main():
    """!
    @brief Print the board-resistance table and the linearity check.
    @return None.
    """
    ht, hb = converged_h()
    print(f"Converged coefficients at 1 W (computed convection and radiation): top {ht:.2f}, bottom {hb:.2f} W/m2K\n")
    ref = rise_independent(ht, hb)
    print(f"Part 1: board resistance at the hottest point under the part, FR-4 isotropic {K_ISO} W/mK, cell {CELL_MM} mm (K/W; RthetaJA = this + theta 4.5)\n")
    print("| Solver | R board (K/W) | RthetaJA (K/W) | against the independent solver |")
    print("| :-- | --: | --: | --: |")
    print(f"| independent 3D solver (lib/layered3d.py) | {ref:.2f} | {ref + 4.5:.1f} | reference |")
    for label, p, model in (("FVM, two layers, bottom bare (as calculator_validation.py)", board(ht, hb, 2), "fvm"),
                            ("FVM, one-layer board (laminate nodes)", board(ht, hb, 1), "fvm"),
                            ("3D solid, two layers, bottom bare", board(ht, hb, 2), "solid3d")):
        r = rise_program(p, model)
        print(f"| {label} | {r:.2f} | {r + 4.5:.1f} | {100 * (r / ref - 1):+.1f} % |", flush=True)
    print("\nThe program's own FR-4 (0.3 through, 0.9 in-plane), same coefficients:\n")
    print("| Solver | R board (K/W) | RthetaJA (K/W) |")
    print("| :-- | --: | --: |")
    for label, p, model in (("FVM, two layers, bottom bare", board(ht, hb, 2, iso=False), "fvm"),
                            ("FVM, one-layer board", board(ht, hb, 1, iso=False), "fvm"),
                            ("3D solid, two layers, bottom bare", board(ht, hb, 2, iso=False), "solid3d")):
        r = rise_program(p, model)
        print(f"| {label} | {r:.2f} | {r + 4.5:.1f} |", flush=True)

    print("\nPart 2: is the measured point affine in the power? T(P) at the junction against the two-run line through P = 0 and 1 W (cell 0.5 mm)\n")
    print("| Coefficients | P (W) | T_j model (degC) | T_j from the line (degC) | difference (K) |")
    print("| :-- | --: | --: | --: | --: |")
    for mode in ("manual", "computed"):
        p = board(ht, hb, 2, iso=False) if mode == "manual" else cv.csd17308q3_board()
        opts = SolverOptions(models=("fvm",), cell_mm=0.5)

        def tj(power):
            """!
            @brief Junction temperature at a given power.
            @param power W.
            @return degC.
            """
            q = copy.deepcopy(p)
            q.heaters[0].power = power
            res = _solve_computed_h(q, "fvm", opts)[0] if mode == "computed" else _run_model(q, "fvm", opts)
            return heater_stats(res, q)[0]["t_junction"]
        t0, t1 = p.board.ambient, tj(1.0)
        for power in (0.5, 2.0, 3.0):
            t = tj(power)
            line = t0 + (t1 - t0) * power
            print(f"| {mode} | {power:g} | {t:.2f} | {line:.2f} | {t - line:+.2f} |", flush=True)


if __name__ == "__main__":
    main()
