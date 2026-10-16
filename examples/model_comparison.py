"""!
@file model_comparison.py
@brief The same boards solved by every model, to compare their values (FVM, FDM, Lumped, Analytic and, optionally, a 3D solid).

Usage: python examples/model_comparison.py [--fem]    (--fem adds the 3D finite-element solid; needs scikit-fem, about a minute)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pcbthermal import SolverOptions, fdm, fvm, simulate          # noqa: E402
from pcbthermal.examples import example_board                     # noqa: E402


def mesh_table(problem, cells=(4.0, 2.0, 1.0, 0.5, 0.25)):
    """!
    @brief Maximum temperature of the FVM and of the FDM (two kinds of face mean) for several grid spacings.
    @param problem A Problem.
    @param cells Grid spacings in millimetres.
    @return List of tuples (spacing, fvm, fdm arithmetic, fdm harmonic).
    """
    return [(c, fvm.solve_steady(problem, c).t_max, fdm.solve_steady(problem, c, "arithmetic").t_max,
             fdm.solve_steady(problem, c, "harmonic").t_max) for c in cells]


def main(with_fem=False):
    """!
    @brief Print the comparison tables in Markdown.
    @param with_fem True to add the 3D finite-element solid to the two boards it can represent.
    @return None.
    """
    p = example_board()
    print("### Example board (4 layers, partial top copper, 3 x 3 vias under U1, sink on the bottom; 4 W + 1.5 W)\n")
    print("Maximum temperature [°C] against the grid spacing:\n")
    print("| Spacing [mm] | FVM | FDM (arithmetic mean) | FDM (harmonic mean) |\n| --: | --: | --: | --: |")
    rows = mesh_table(p)
    for c, a, b, h in rows:
        print(f"| {c:g} | {a:.2f} | {b:.2f} | {h:.2f} |")
    sim = simulate(p, SolverOptions(models=("fvm", "lumped", "analytic", "fdm"), cell_mm=0.5))
    print("\nAll models at 0.5 mm (Lumped and Analytic do not depend on the grid in the same way):\n")
    print(sim.to_markdown().split("\n\n")[0])

    if with_fem:
        import fem3d_validation as f3
        print("\n### Boards that the 3D solid can represent (no vias or sinks): rise above ambient, error against the 3D solid\n")
        print("| Board | 3D solid [°C] | FVM | FDM | Lumped | Analytic |\n| :-- | --: | --: | --: | --: | --: |")
        for name, build in (("4 layers, full copper", f3.board_full_copper), ("2 layers, 40 mm pad", f3.board_partial_copper),
                            ("2 layers, 20 mm pad", f3.board_small_pad)):
            q = build()
            ref = f3.solve_fem(q, 1.0)["t_max"]
            s = simulate(q, SolverOptions(models=("fvm", "fdm", "lumped", "analytic"), cell_mm=0.5))
            cells = " | ".join(f"{s.results[k].t_max:.1f} ({100 * (s.results[k].t_max - 25) / (ref - 25) - 100:+.1f} %)"
                               for k in ("fvm", "fdm", "lumped", "analytic"))
            print(f"| {name} | {ref:.1f} | {cells} |")


if __name__ == "__main__":
    main("--fem" in sys.argv)
