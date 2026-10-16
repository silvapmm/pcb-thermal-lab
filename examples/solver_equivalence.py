"""!
@file solver_equivalence.py
@brief Do the sparse-matrix solvers and SOR give the same temperatures? One table over several boards.

Usage: python examples/solver_equivalence.py [--markdown docs/solver_equivalence.md]
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pcbthermal import Problem, fvm                      # noqa: E402
from pcbthermal.examples import example_board             # noqa: E402
from pcbthermal.model import reference_problem            # noqa: E402

SOLVERS = [("direct (sparse LU)", dict(method="direct")),
           ("cg (Jacobi)", dict(method="cg")),
           ("SOR, residual 1e-9, auto omega", dict(method="sor", sor_tol=1e-9)),
           ("SOR, step 0.01 K, omega 1.5 (original rule)", dict(method="sor", sor_omega=1.5, sor_tol=0.01,
                                                                sor_criterion="step"))]


def boards():
    """!
    @brief The boards of the study.
    @return List of (name, Problem, cell_mm).
    """
    weak = Problem.new(200, 200, layers=2).add_full_copper().add_heater(1, 1.0, rect=(90, 90, 110, 110))
    weak.board.h_top = weak.board.h_bottom = 2.0
    weak.board.h_side = None
    plain = reference_problem()
    plain.board.h_side = None
    return [("reference, 2 layers", reference_problem(), 2.0),
            ("reference, 8 layers", reference_problem(layers=8), 2.0),
            ("example board (vias, sink, 2 heaters)", example_board(), 1.0),
            ("weak cooling (h = 2 W/m²K, 200 mm)", weak, 2.0),
            ("reference, insulated edges", plain, 1.0)]


def run():
    """!
    @brief Solve every board with every solver.
    @return Markdown table.
    """
    lines = ["| Board | Solver | Tmax [°C] | max abs diff to direct [K] | Residual | Sweeps | Time [s] |",
             "| :-- | :-- | --: | --: | --: | --: | --: |"]
    for name, prob, cell in boards():
        ref = None
        for sname, kw in SOLVERS:
            t0 = time.time()
            r = fvm.solve_steady(prob, cell_mm=cell, **kw)
            dt = time.time() - t0
            ref = r if ref is None else ref
            sweeps = f"{int(r.extras['iterations'])}" if "iterations" in r.extras else "-"
            lines.append(f"| {name} | {sname} | {r.t_max:.4f} | {float(abs(r.T - ref.T).max()):.1e} | "
                         f"{r.residual:.0e} | {sweeps} | {dt:.2f} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown")
    a = ap.parse_args()
    md = run()
    print(md)
    if a.markdown:
        open(a.markdown, "w", encoding="utf-8").write(md)
