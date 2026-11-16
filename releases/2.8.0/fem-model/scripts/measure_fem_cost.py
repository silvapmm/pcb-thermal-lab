#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file measure_fem_cost.py
@brief Measures the cost (unknowns, seconds, peak resident memory) of the research finite-element tool and of the program's 3D solid on the same plain boards, each solve in a
       fresh process, for the memory law of the planned `fem` model (`releases/2.8.0/fem-model/DESIGN.md`, section 5.3).
@details The finite-element side is `research/independent-fem-edge/lib` (`board.Board` on a uniform tensor plan, six graded elements per laminate gap, full copper on every
         layer, a 10 x 10 mm source of 1 W at the centre, films 10 / 10 / 10 W/m2K); it solves directly up to the `direct_max` given in the case, else by conjugate gradients
         with a pyamg preconditioner, so the runs that use it need the scratch environment `.venv-research` (pyamg 5.4.1). The 3D solid side is `pcbthermal.simulate` with
         the same board (h_bottom set to 10 W/m2K: `Problem.new` defaults to 15). The peak is `ru_maxrss` of the child process (bytes on macOS); it includes the interpreter.
         Usage, from the repository root (one heavy job; the largest case peaks near 2.7 GB):

         .venv-research/bin/python releases/2.8.0/fem-model/scripts/measure_fem_cost.py           # every case, a table
         .venv-research/bin/python releases/2.8.0/fem-model/scripts/measure_fem_cost.py --one fem 60 40 4 1 0   # one case, one JSON line
"""

import json
import os
import resource
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# (model, width mm, height mm, layers, plan size mm, direct_max): direct_max 1e6 forces the direct solve, 0 forces conjugate gradients with pyamg
CASES = [
    ("fem", 60, 40, 2, 1.0, 1_000_000),
    ("fem", 60, 40, 4, 1.0, 1_000_000),
    ("fem", 100, 80, 4, 2.0, 1_000_000),
    ("fem", 60, 40, 4, 1.0, 0),
    ("fem", 100, 80, 4, 2.0, 0),
    ("fem", 100, 80, 4, 1.0, 0),
    ("fem", 100, 80, 2, 0.5, 0),
    ("solid3d", 60, 40, 4, 1.0, 0),
    ("solid3d", 100, 80, 4, 1.0, 0),
    ("solid3d", 100, 80, 2, 0.5, 0),
]


def run_one(kind, width, height, layers, size, direct_max):
    """!
    @brief Solve one case in this process and return its cost.
    @param kind "fem" (the research tool) or "solid3d" (the program).
    @param width Board width in mm.
    @param height Board height in mm.
    @param layers Copper layers.
    @param size Plan element (finite elements) or cell (3D solid) size in mm.
    @param direct_max Largest unknown count of a direct solve of the finite elements (0: always conjugate gradients).
    @return dict with n (unknowns), rise (hottest rise, K), solver, sec (wall time), peak_gb (peak resident memory, 1e9 bytes).
    """
    t0 = time.time()
    if kind == "fem":
        # The research tool is imported from its folder, unchanged
        sys.path.insert(0, os.path.join(ROOT, "research", "independent-fem-edge", "lib"))
        import numpy as np
        import board
        import mesh2d
        xn = np.linspace(0.0, width, int(round(width / size)) + 1) * 1e-3
        yn = np.linspace(0.0, height, int(round(height / size)) + 1) * 1e-3
        cx, cy = width / 2e3, height / 2e3
        src = np.array([[cx - 5e-3, cy - 5e-3], [cx + 5e-3, cy - 5e-3], [cx + 5e-3, cy + 5e-3], [cx - 5e-3, cy + 5e-3]])
        b = board.Board(mesh2d.tensor(xn, yn), layers, board_t=1.6e-3, h_top=10.0, h_bottom=10.0, h_side=10.0, heaters=[(src, 1.0)], n_gap=6)
        r = b.solve(direct_max=direct_max)
        out = {"n": int(r["n"]), "rise": float(r["tmax"]), "solver": r["solver"]}
    else:
        sys.path.insert(0, ROOT)
        from pcbthermal import Problem, SolverOptions, simulate, solid3d
        p = Problem.new(width, height, layers, h_side=10.0)
        p.board.h_bottom = 10.0                                    # the same films as the finite-element case
        p.add_heater(1, 1.0, rect=(width / 2 - 5, height / 2 - 5, width / 2 + 5, height / 2 + 5), name="U")
        for layer in range(1, layers + 1):
            p.add_zone(layer, polygon=[(0, 0), (width, 0), (width, height), (0, height)])
        n = solid3d.unknowns(p, size)[0]
        res = simulate(p, SolverOptions(models=("solid3d",), cell_mm=size)).results["solid3d"]
        out = {"n": int(n), "rise": float(res.t_max - res.ambient), "solver": "solid3d"}
    out["sec"] = time.time() - t0
    out["peak_gb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1e9 if sys.platform == "darwin" else 1e6)
    return out


def main():
    """!
    @brief Run every case in a child process (or one case with --one) and print the table.
    @return None.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "--one":
        a = sys.argv[2:]
        print(json.dumps(run_one(a[0], float(a[1]), float(a[2]), int(a[3]), float(a[4]), int(a[5]))))
        return
    print("| model | board | layers | size mm | solver | unknowns | rise K | s | peak GB | kB per unknown |")
    print("| :-- | :-- | --: | --: | :-- | --: | --: | --: | --: | --: |")
    for case in CASES:
        # A fresh process per case, so that the peak is that of one solve
        line = subprocess.run([sys.executable, __file__, "--one"] + [str(v) for v in case], capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
        r = json.loads(line)
        print(f"| {case[0]} | {case[1]} x {case[2]} | {case[3]} | {case[4]} | {r['solver']} | {r['n']} | {r['rise']:.3f} | {r['sec']:.1f} | {r['peak_gb']:.2f} | "
              f"{r['peak_gb'] * 1e6 / r['n']:.1f} |")


if __name__ == "__main__":
    main()
