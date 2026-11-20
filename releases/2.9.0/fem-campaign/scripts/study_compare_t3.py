#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_compare_t3.py
@brief Row T3 of the FEM campaign (validation 57.3): the first seconds of a step on a plain two-layer board in every model that runs in time, against the FEM with a finer gap mesh,
       and, on a board without copper, against the closed form of a flux switched on at the face of a semi-infinite solid (Lienhard, eqn (5.56): T = 2 q sqrt(t/pi)/e).
@details The row is the stated limit of 2.7.0 and not a pass criterion (COMPARE_PLAN.md): the layered models carry one node per copper layer, the FEM resolves the thickness.
         Part A: `plate_uniform` (60 x 60 mm, two layers of copper, an 8 mm part of 5 W), `api.step_response` of the five models at the 2 mm response cell (the program's default
         stepping) at the sample times of the step response nearest 0.1, 0.3, 1, 3 and 10 s, K/W of the hottest column cell under the part, difference to the FEM with the default
         mesh (6 elements across a gap) and to the FEM with 12 elements across a gap (the mesh limit of docs/theory.md 4b). Part B: the same board without any copper (laminate
         only, 1.6 mm), FEM (6 and 12 gap elements), FVM and FDM against the closed form with the laminate of the program (`Board.materials`, the through-thickness conductivity
         and the volumetric heat capacity of the dielectric between the layers); the closed form holds while the heat has not crossed the board (about t < 0.3 x thickness^2 / alpha)
         and while the penetration is below the source size.
         Run from the repository root: `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_compare_t3.py`.
"""

import math
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "regression"))
LABEL = {"fvm": "FVM", "fdm": "FDM", "lumped": "Lumped", "analytic": "Analytic", "fem": "FEM"}
SAMPLES = (0.1, 0.3, 1.0, 3.0, 10.0)           # s


def at(resp, t):
    """!
    @brief Response of part 1 at the sample time nearest to t (no interpolation between samples).
    @param resp StepResponse.
    @param t Time in s.
    @return tuple (sample time in s, z in K/W).
    """
    k = int(np.argmin(np.abs(np.log(np.asarray(resp.times) / t))))
    return float(resp.times[k]), float(resp.z[0][k])


def part_a():
    """!
    @brief Part A: the five models on `plate_uniform` against the FEM at the default mesh and with 12 gap elements.
    @return None.
    """
    import regress_boards as B
    import regress_harness as H
    from pcbthermal import SolverOptions, fem
    from pcbthermal.api import step_response
    from pcbthermal.profiles import StepResponse
    problem = H.steady_problem(B.build("plate_uniform"))
    res = {m: step_response(problem, m, SolverOptions(models=(m,), cell_mm=2.0)) for m in ("fem", "fvm", "fdm", "lumped", "analytic")}
    t, z, rth = fem.step_responses(problem, cell_mm=2.0, gap_elements=12)
    fine = StepResponse("fem12", t, z, rth)
    print("### T3a. plate_uniform, 8 mm part of 5 W, response cell 2 mm; hottest column cell under the part, K/W at the sample time nearest to the nominal time; % = model against the FEM (6 gap elements)")
    print("| nominal t s | sample t s (FEM) | FEM 6 gap elements | FEM 12 gap elements (% vs 6) | " + " | ".join(f"{LABEL[m]} (%)" for m in ("fvm", "fdm", "lumped", "analytic")) + " |")
    print("| --: | --: | --: | --: | " + " | ".join("--:" for _ in range(4)) + " |")
    for tn in SAMPLES:
        ts, zf = at(res["fem"], tn)
        zz = float(fine.z_at(0, ts))
        cols = []
        for m in ("fvm", "fdm", "lumped", "analytic"):
            v = float(res[m].z_at(0, ts))
            cols.append(f"{v:.3f} ({100 * (v / zf - 1):+.1f})")
        print(f"| {tn:g} | {ts:.3g} | {zf:.3f} | {zz:.3f} ({100 * (zz / zf - 1):+.1f}) | " + " | ".join(cols) + " |")
    print(f"\nplateau K/W: " + ", ".join(f"{LABEL[m]} {float(res[m].rth[0]):.3f}" for m in res) + f", FEM 12 gap elements {float(fine.rth[0]):.3f}\n")


def bare_board():
    """!
    @brief A 60 x 60 mm two-layer board without copper and an 8 mm part of 5 W on the top layer.
    @return Problem.
    """
    from pcbthermal import Problem
    p = Problem.new(60.0, 60.0, layers=2)
    p.add_heater(1, 5.0, rect=(26.0, 26.0, 34.0, 34.0))
    return p


def part_b():
    """!
    @brief Part B: the bare board against the semi-infinite closed form.
    @return None.
    """
    from pcbthermal import fdm, fem, fvm
    from pcbthermal.profiles import StepResponse
    p = bare_board()
    # The laminate between the two layers: the through-thickness conductivity and the volumetric heat capacity of the program, for the closed form
    kz, _, rc = p.board.dielectric_arrays()
    k, rho_c = float(kz[0]), float(rc[0])
    eff = math.sqrt(k * rho_c)
    area = 0.008 * 0.008
    q = 1.0 / area                                                   # W/m2 per watt of the part
    thick = float(p.board.thickness) if hasattr(p.board, "thickness") else 1.6e-3
    alpha = k / rho_c
    print(f"### T3b. board without copper (60 x 60 mm, laminate k {k:.3g} W/mK, rho c {rho_c:.4g} J/m3K, thickness {thick * 1e3:.2f} mm, 8 mm part), surface of the part, K/W")
    print(f"closed form z(t) = 2 sqrt(t/pi) / (e A), e = {eff:.1f} W s^0.5/m2K, A = {area * 1e6:.0f} mm2; holds for t below about 0.3 thickness^2/alpha = {0.3 * thick ** 2 / alpha:.1f} s and while the penetration sqrt(alpha t) is below the source size")
    runs = {}
    for label, fn, kw in (("FEM 6", fem.step_responses, {}), ("FEM 12", fem.step_responses, {"gap_elements": 12}), ("FVM", fvm.step_responses, {}), ("FDM", fdm.step_responses, {})):
        t, z, rth = fn(p, cell_mm=1.0, **kw)
        runs[label] = StepResponse(label, t, z, rth)
    print("| nominal t s | sample t s | closed form | " + " | ".join(f"{k} (%)" for k in runs) + " |")
    print("| --: | --: | --: | " + " | ".join("--:" for _ in runs) + " |")
    for tn in SAMPLES:
        ts, _ = at(runs["FEM 6"], tn)
        exact = 2.0 * math.sqrt(ts / math.pi) / eff * q
        cols = [f"{float(r.z_at(0, ts)):.3f} ({100 * (float(r.z_at(0, ts)) / exact - 1):+.1f})" for r in runs.values()]
        print(f"| {tn:g} | {ts:.3g} | {exact:.3f} | " + " | ".join(cols) + " |")
    print()


def main():
    """!
    @brief Run both parts.
    @return None.
    """
    import regress_harness as H
    H.use_program(ROOT)
    tree = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"tree {tree}, program {sys.modules['pcbthermal'].__version__}\n")
    part_a()
    part_b()


if __name__ == "__main__":
    main()
