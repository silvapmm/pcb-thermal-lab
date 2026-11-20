#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_compare_t1.py
@brief Row T1 of the FEM campaign (validation 57.1): the unit-step response of every part in the five models that run in time (FVM, FDM, Lumped, Analytic, FEM), the plateau
       (steady resistance), the time to 63 % and the response at fixed times, against the FEM, and the time-stepping error of each model against itself with finer steps.
@details The response is `api.step_response` (the route of the Animation tab and of the profile decision, cell of the step response at least 2 mm, the 2.9.0 default stepping:
         Crank-Nicolson with the Rannacher start, first stage in quarter steps), read at the hottest column cell of each part, in K/W. The Lumped and Analytic have no time
         simulation with an outline or a metal block: those cells are '-'. Part B repeats the FVM, FDM and FEM with the finer stepping `per_stage` 16 instead of 4 on the same mesh,
         so that a difference between models is not mistaken for a stepping error (the same network without its time-step error is the reference of
         `research/transient-published-case`). Part C repeats the plate at the 1 mm cell (module functions, not `api`, which keeps the 2 mm response cell).
         Run from the repository root, ONE job at a time:
         `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_compare_t1.py [--boards a,b] [--dry-run]` (output also in out/t1.txt; the example board takes about 3 min).
         Read-out of every number: column ('the hottest column cell under the part'); differences signed, model minus FEM, in percent of the FEM value.
"""

import argparse
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "regression"))

BOARDS = ("plate_uniform", "plate_vias", "one_layer_pad", "part_top_path", "finned_block", "reference_board", "example_board")
MODELS = ("fem", "fvm", "fdm", "lumped", "analytic")
LABEL = {"fvm": "FVM", "fdm": "FDM", "lumped": "Lumped", "analytic": "Analytic", "fem": "FEM"}
TIMES = (0.3, 1.0, 3.0, 10.0, 30.0, 100.0)          # s, where the responses are compared


def t63(resp, i):
    """!
    @brief Time to 63.2 % of the steady resistance of part i (bisection on the monotone interpolation of the response).
    @param resp A StepResponse.
    @param i Part index.
    @return float time in s, or None when the response does not reach the level.
    """
    target = (1.0 - math.exp(-1.0)) * float(resp.rth[i])
    lo, hi = float(resp.times[0]) * 0.01, float(resp.times[-1])
    if float(resp.z_at(i, hi)) < target:
        return None
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if float(resp.z_at(i, mid)) < target:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def run_model(problem, model, cell):
    """!
    @brief The program's step response of one model on a copy of the problem (steady powers).
    @param problem A Problem.
    @param model Model key.
    @param cell Cell size in mm of the options.
    @return tuple (StepResponse or None, seconds, reason) with the reason empty when it ran.
    """
    from pcbthermal import SolverOptions
    from pcbthermal.api import step_response
    import regress_harness as H
    p = H.steady_problem(problem)
    t0 = time.perf_counter()
    try:
        return step_response(p, model, SolverOptions(models=(model,), cell_mm=cell)), time.perf_counter() - t0, ""
    except Exception as exc:                                     # a model that refuses a board is a result
        return None, time.perf_counter() - t0, f"{type(exc).__name__}: {str(exc)[:90]}"


def part_a(boards, cell):
    """!
    @brief Table of the five models on the boards: plateau, time to 63 % and the responses at fixed times, against the FEM.
    @param boards Board names.
    @param cell Cell size in mm of the options (the step response uses at least 2 mm).
    @return None.
    """
    import regress_boards as B
    print(f"## T1a. Step response at the program's default stepping, options cell {cell:g} mm (the response cell is at least 2 mm); hottest column cell of each part, K/W")
    for name in boards:
        problem = B.build(name)
        if not problem.heaters:
            continue
        res, sec = {}, {}
        for m in MODELS:
            r, s, why = run_model(problem, m, cell)
            res[m], sec[m] = r, s
            if r is None:
                print(f"   {name} {LABEL[m]}: not run ({why})")
        ref = res.get("fem")
        for i, h in enumerate(problem.heaters):
            print(f"\n{name}, part {h.name or i + 1}: the steady resistance (plateau) and the time to 63 %, then the response at fixed times")
            print("| model | plateau K/W | (vs FEM %) | t63 s | (vs FEM %) | " + " | ".join(f"z({t:g} s) %" for t in TIMES) + " | run s |")
            print("| :-- | --: | --: | --: | --: | " + " | ".join("--:" for _ in TIMES) + " | --: |")
            for m in MODELS:
                r = res[m]
                if r is None:
                    print(f"| {LABEL[m]} | - | - | - | - | " + " | ".join("-" for _ in TIMES) + f" | {sec[m]:.1f} |")
                    continue
                rt, tt = float(r.rth[i]), t63(r, i)
                if ref is None:
                    d1 = d2 = "-"
                else:
                    d1 = f"{100 * (rt / float(ref.rth[i]) - 1):+.1f}"
                    t_ref = t63(ref, i)
                    d2 = f"{100 * (tt / t_ref - 1):+.1f}" if tt and t_ref else "-"
                zs = []
                for t in TIMES:
                    v = float(r.z_at(i, t))
                    zs.append("-" if ref is None or m == "fem" else f"{100 * (v / float(ref.z_at(i, t)) - 1):+.1f}")
                print(f"| {LABEL[m]} | {rt:.4f} | {d1} | {tt:.3g} | {d2} | " + " | ".join(zs) + f" | {sec[m]:.1f} |" if tt else f"| {LABEL[m]} | {rt:.4f} | {d1} | - | - | " + " | ".join(zs) + f" | {sec[m]:.1f} |")
        print()


def part_b(boards, cell):
    """!
    @brief The time-stepping error of the FVM, FDM and FEM against themselves: the same mesh with four times more steps per stage.
    @param boards Board names.
    @param cell Cell size in mm of the mesh.
    @return None.
    """
    import regress_boards as B
    import regress_harness as H
    from pcbthermal import fdm, fem, fvm
    print(f"## T1b. Stepping error of each model against itself (per_stage 4 against 16 on the same {cell:g} mm mesh), largest difference of the response over the times, percent of the fine value")
    print("| board | model | t63 default s | t63 fine s | change of t63 % | largest change of z over " + ", ".join(f"{t:g}" for t in TIMES) + " s [%] |")
    print("| :-- | :-- | --: | --: | --: | --: |")
    from pcbthermal.profiles import StepResponse
    for name in boards:
        problem = H.steady_problem(B.build(name))
        if not problem.heaters:
            continue
        for label, fn in (("FVM", fvm.step_responses), ("FDM", fdm.step_responses), ("FEM", fem.step_responses)):
            out = {}
            for ps in (4, 16):
                try:
                    t, z, rth = fn(problem, cell_mm=cell, per_stage=ps)
                except Exception as exc:
                    out = None
                    print(f"| {name} | {label} | not run: {type(exc).__name__}: {str(exc)[:70]} | | | |")
                    break
                out[ps] = StepResponse(label, t, z, rth)
            if out is None:
                continue
            a, b = t63(out[4], 0), t63(out[16], 0)
            worst = max(abs(float(out[4].z_at(0, t)) / float(out[16].z_at(0, t)) - 1) for t in TIMES)
            print(f"| {name} | {label} | {a:.3g} | {b:.3g} | {100 * (a / b - 1):+.2f} | {100 * worst:.2f} |")
    print()


def part_c(cell):
    """!
    @brief The plate at a finer cell with the module functions: FVM, FDM and FEM, the response of the part against the FEM at the same cell.
    @param cell Cell size in mm.
    @return None.
    """
    import regress_boards as B
    import regress_harness as H
    from pcbthermal import fdm, fem, fvm
    from pcbthermal.profiles import StepResponse
    print(f"## T1c. plate_uniform at the {cell:g} mm cell (module functions, one element or cell per mm), part 1, K/W")
    problem = H.steady_problem(B.build("plate_uniform"))
    res = {}
    for label, fn in (("FEM", fem.step_responses), ("FVM", fvm.step_responses), ("FDM", fdm.step_responses)):
        t0 = time.perf_counter()
        t, z, rth = fn(problem, cell_mm=cell)
        res[label] = (StepResponse(label, t, z, rth), time.perf_counter() - t0)
    ref = res["FEM"][0]
    print("| model | plateau K/W | (vs FEM %) | t63 s | (vs FEM %) | " + " | ".join(f"z({t:g} s) %" for t in TIMES) + " | run s |")
    print("| :-- | --: | --: | --: | --: | " + " | ".join("--:" for _ in TIMES) + " | --: |")
    for label, (r, s) in res.items():
        tt, tr = t63(r, 0), t63(ref, 0)
        zs = ["-" if label == "FEM" else f"{100 * (float(r.z_at(0, t)) / float(ref.z_at(0, t)) - 1):+.1f}" for t in TIMES]
        print(f"| {label} | {float(r.rth[0]):.4f} | {100 * (float(r.rth[0]) / float(ref.rth[0]) - 1):+.1f} | {tt:.3g} | {100 * (tt / tr - 1):+.1f} | " + " | ".join(zs) + f" | {s:.1f} |")
    print()


def main():
    """!
    @brief Command line of the study.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--boards", default="", help="comma list (default: the seven boards of the table)")
    ap.add_argument("--cell", type=float, default=2.0)
    ap.add_argument("--dry-run", action="store_true", help="list the boards and the FEM unknown counts at the response cell, solve nothing")
    a = ap.parse_args()
    import regress_harness as H
    import regress_boards as B
    H.use_program(ROOT)
    boards = [b for b in a.boards.split(",") if b] or list(BOARDS)
    if a.dry_run:
        for b in boards:
            print(b, "FEM unknowns at", a.cell, "mm:", H.unknowns_of(H.steady_problem(B.build(b)), "fem", a.cell))
        return
    tree = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"tree {tree}, program {H.__name__ and sys.modules['pcbthermal'].__version__}, numpy {np.__version__}\n")
    part_a(boards, a.cell)
    part_b([b for b in boards if b in ("plate_uniform", "finned_block", "reference_board")], 2.0)
    part_c(1.0)


if __name__ == "__main__":
    main()
