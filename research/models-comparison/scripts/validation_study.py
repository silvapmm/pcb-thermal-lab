#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file validation_study.py
@brief The same scenarios solved by every model, printed as the tables of docs/validation.md.

Usage: python research/models-comparison/scripts/validation_study.py [--fem]    (--fem adds the 3D finite-element solid; needs scikit-fem, several minutes)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

from pcbthermal import analytic, check_problem, fdm, fvm, lumped, solid3d  # noqa: E402
from pcbthermal.examples import example_board                           # noqa: E402
import accuracy_study                                                    # noqa: E402
import stress_study                                                      # noqa: E402


def error(result, reference):
    """!
    @brief Error of a model on the temperature rise, against a reference result.
    @param result SteadyResult of the model.
    @param reference SteadyResult of the reference.
    @return Percentage.
    """
    ref_dt = reference.delta_t
    return 100.0 * (result.delta_t / ref_dt - 1.0)


def scenario_table(cell_mm=1.0):
    """!
    @brief Every scenario with the maximum temperature of the four models and their error against the FVM.
    @param cell_mm Cell size for the FVM and the FDM.
    @return Markdown text.
    """
    lines = ["| Scenario | FVM [°C] | FDM | 3D solid | Lumped | Analytic | Input check |", "| :-- | --: | --: | --: | --: | --: | :-: |"]
    for name, p in accuracy_study.cases() + stress_study.cases():
        f = fvm.solve_steady(p, cell_mm)
        d = fdm.solve_steady(p, cell_mm)
        s3 = solid3d.solve_steady(p, cell_mm)
        l = lumped.solve_steady(p)
        a = analytic.solve_steady(p)
        warn = "warns" if (check_problem(p, cell_mm) + a.warnings) else "-"
        lines.append(f"| {name} | {f.t_max:.2f} | {d.t_max:.2f} ({error(d, f):+.1f} %) | {s3.t_max:.2f} ({error(s3, f):+.1f} %) | {l.t_max:.2f} ({error(l, f):+.1f} %) | "
                     f"{a.t_max:.2f} ({error(a, f):+.1f} %) | {warn} |")
    return "\n".join(lines)


def _solid(p, cell):
    """!
    @brief Maximum temperature of the 3D solid as text, or "-" when the model is too large for the cell size.
    @param p Problem.
    @param cell Cell size in mm.
    @return String.
    """
    try:
        return f"{solid3d.solve_steady(p, cell).t_max:.2f}"
    except ValueError:
        return "-"


def mesh_table(cells=(4.0, 2.0, 1.0, 0.5, 0.25)):
    """!
    @brief Maximum temperature of the example board against the grid spacing, FVM and FDM.
    @param cells Grid spacings in millimetres.
    @return Markdown text.
    """
    p = example_board()
    lines = ["| Spacing [mm] | FVM | FDM (area sampling) | FDM (point sampling, classic) | 3D solid |", "| --: | --: | --: | --: | --: |"]
    for c in cells:
        lines.append(f"| {c:g} | {fvm.solve_steady(p, c).t_max:.2f} | {fdm.solve_steady(p, c).t_max:.2f} | "
                     f"{fdm.solve_steady(p, c, sampling='point').t_max:.2f} | {_solid(p, c)} |")
    return "\n".join(lines)


def fem_table():
    """!
    @brief Boards solved as a 3D solid, with the error of every model on the temperature rise.
    @return Markdown text.
    """
    # The finite-element solid lives in the solid3d-verification folder since the studies moved out of examples/ (the import failed before)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "solid3d-verification", "scripts"))
    import fem3d_validation as f3
    rows = ["| Board | 3D FEM [°C] | FVM | FDM | 3D solid (FV) | Lumped | Analytic |", "| :-- | --: | --: | --: | --: | --: | --: |"]
    cases = (("4 layers, full copper", f3.board_full_copper()), ("2 layers, 40 mm top pad", f3.board_partial_copper()),
             ("2 layers, 20 mm top pad", f3.board_small_pad()), ("example board (partial copper, 9 vias, bottom heatsink)", example_board()))
    for name, p in cases:
        ref = f3.solve_fem(p, 1.0)["t_max"]
        res = {"fvm": fvm.solve_steady(p, 0.5), "fdm": fdm.solve_steady(p, 0.5), "solid3d": solid3d.solve_steady(p, 0.5), "lumped": lumped.solve_steady(p),
               "analytic": analytic.solve_steady(p)}
        cells = " | ".join(f"{r.t_max:.1f} ({100 * (r.t_max - 25) / (ref - 25) - 100:+.1f} %)" for r in res.values())
        rows.append(f"| {name} | {ref:.1f} | {cells} |")
    return "\n".join(rows)


def main(with_fem=False):
    """!
    @brief Print the tables.
    @param with_fem True to include the 3D solid.
    """
    # The scenario table has a 36-slab stress case (360 000 unknowns at 1 mm) and the 0.5 mm columns of the 3D solid have about 512 000 unknowns on the
    # 4-layer boards: both are above the application's limit (solid3d.MAX_CELLS, 250 000). The study accepts solves of several minutes and GB, so it
    # raises the limit to the old 2 million for the whole run, and only here (the limit is restored afterwards)
    with solid3d.size_limit(2_000_000):
        print("## Scenarios, 1 mm cells (error on the temperature rise against the FVM)\n")
        print(scenario_table())
        print("\n## Example board against the grid\n")
        print(mesh_table())
        if with_fem:
            print("\n## Against an independent 3D solid\n")
            print(fem_table())


if __name__ == "__main__":
    main("--fem" in sys.argv)
