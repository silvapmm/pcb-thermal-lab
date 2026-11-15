#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_final_2b_runs.py
@brief Final review of 2.8.0, part 2b: re-run the light parts of `docs/validation.md` 1, 2, 2.1 and 3 on the tree.

The scenario table of section 2 (FVM, FDM, Lumped, Analytic at 1 mm), the grid table of section 2.1 (FVM, FDM area and
point sampling) and the program columns of section 3 (FVM and FDM at 0.5 mm, Lumped and Analytic with their defaults,
against the finite-element values printed in section 3). The 3D solid and the finite elements are left out (the 3D solid
did not change on these boards in 2.8.0; scikit-fem is not in the program's environment), so the run is about a minute;
its peak resident memory was 5.2 GB on the reviewer's machine (the FDM at 0.25 mm and the 36-slab stress case), so run
it alone.

Usage, from the repository root:
    PCBTHERMAL_CONFIG=<a private folder> .venv/bin/python releases/2.8.0/final-review/scripts/study_final_2b_runs.py [scen|mesh|fem|all]
"""

import os
import resource
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research", "models-comparison", "scripts"))

from pcbthermal import Problem, analytic, check_problem, fdm, fvm, lumped   # noqa: E402
from pcbthermal.examples import example_board                              # noqa: E402
import accuracy_study                                                       # noqa: E402
import stress_study                                                         # noqa: E402

# Finite-element maxima of validation.md 3 (1 mm mesh, four elements per gap; not re-run, printed there)
FEM_REFERENCE = {"full": 90.6, "pad40": 112.2, "pad20": 136.2, "example": 85.6}


def error(result, reference):
    """!
    @brief Error of a model on the temperature rise against a reference result.
    @param result SteadyResult of the model.
    @param reference SteadyResult of the reference.
    @return float Percentage of the reference rise.
    """
    return 100.0 * (result.delta_t / reference.delta_t - 1.0)


def scenario_rows():
    """!
    @brief Print the scenario table of validation 2 without the 3D solid column.
    """
    print("| Scenario | FVM | FDM | Lumped | Analytic | check |")
    for name, p in accuracy_study.cases() + stress_study.cases():
        f = fvm.solve_steady(p, 1.0)
        d = fdm.solve_steady(p, 1.0)
        lu = lumped.solve_steady(p)
        a = analytic.solve_steady(p)
        # Same rule for the last column as validation_study.py: any input warning or a warning of the Analytic
        warn = "warns" if (check_problem(p, 1.0) + a.warnings) else "-"
        print(f"| {name} | {f.t_max:.2f} | {d.t_max:.2f} ({error(d, f):+.1f} %) | {lu.t_max:.2f} ({error(lu, f):+.1f} %) | "
              f"{a.t_max:.2f} ({error(a, f):+.1f} %) | {warn} |", flush=True)


def mesh_rows():
    """!
    @brief Print the grid table of validation 2.1 (example board) without the 3D solid column.
    """
    p = example_board()
    for c in (4.0, 2.0, 1.0, 0.5, 0.25):
        print(f"| {c:g} | {fvm.solve_steady(p, c).t_max:.2f} | {fdm.solve_steady(p, c).t_max:.2f} | "
              f"{fdm.solve_steady(p, c, sampling='point').t_max:.2f} |", flush=True)


def _boards():
    """!
    @brief The four boards of validation 3 (the same as `fem3d_validation.py`, written here so that scikit-fem is not needed).
    @return list of (name, Problem).
    """
    full = Problem.new(100, 80, 4)
    full.add_full_copper()
    full.add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1")
    pad40 = Problem.new(100, 80, 2)
    pad40.add_zone(1, rect=(15, 20, 55, 60))
    pad40.add_zone(2, rect=(0, 0, 100, 80))
    pad40.add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1")
    pad20 = Problem.new(100, 80, 2)
    pad20.add_zone(1, rect=(25, 30, 45, 50))
    pad20.add_zone(2, rect=(0, 0, 100, 80))
    pad20.add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1")
    return [("full", full), ("pad40", pad40), ("pad20", pad20), ("example", example_board())]


def fem_rows():
    """!
    @brief Print the program columns of validation 3 against the printed finite-element maxima.
    """
    for name, p in _boards():
        ref = FEM_REFERENCE[name]
        results = [fvm.solve_steady(p, 0.5), fdm.solve_steady(p, 0.5), lumped.solve_steady(p), analytic.solve_steady(p)]
        cells = " | ".join(f"{r.t_max:.2f} ({100 * (r.t_max - 25) / (ref - 25) - 100:+.1f} %)" for r in results)
        print(f"{name} (FEM {ref}): FVM | FDM | Lumped | Analytic = {cells}", flush=True)


def main(part="all"):
    """!
    @brief Run the chosen parts and print the time and the peak resident memory of the process.
    @param part 'scen', 'mesh', 'fem' or 'all'.
    """
    t0 = time.time()
    if part in ("all", "scen"):
        scenario_rows()
    if part in ("all", "mesh"):
        mesh_rows()
    if part in ("all", "fem"):
        fem_rows()
    # ru_maxrss is in bytes on macOS (kilobytes on Linux): the figure is indicative only
    print("time", round(time.time() - t0, 1), "s, peak", round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**30, 2), "GB (macOS units)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
