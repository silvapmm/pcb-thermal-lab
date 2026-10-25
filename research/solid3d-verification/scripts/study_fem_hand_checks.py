"""!
@file study_fem_hand_checks.py
@brief Do the finite-element checks of README section 4.2 (element size, elements per gap, example board) reproduce from a script?

@details The review ran these cases by hand with fem3d_validation.solve_fem; this script prints them. Cases (maximum temperature of
         the top face, degC):
         (a) 4 layers, full copper (board_full_copper): 1 mm with 4 elements per gap, and 1 mm and 0.5 mm with 2 per gap (the "90.63 to 90.57" check),
             and 1 mm with 2 elements per gap instead of 4 (the 0.001 degC check);
         (b) the example board (pcbthermal.examples.example_board): 1 mm with 4 per gap, and 0.5 mm with 2 per gap (85.57 and 85.59).
         The mesh is never finer than 0.5 mm, and 0.5 mm with 4 elements per gap (about 1.1 million nodes) was killed for memory, so 0.5 mm
         always uses 2 per gap.

Usage: .venv/bin/python research/solid3d-verification/scripts/study_fem_hand_checks.py   (from the repository root; needs scikit-fem; about 11 minutes)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

import fem3d_validation as f3                                          # noqa: E402
from pcbthermal.examples import example_board                           # noqa: E402


def run(label, problem, dxy_mm, n_diel):
    """!
    @brief Solve one case with the finite-element solid and print its line.
    @param label Name of the case.
    @param problem Problem to solve.
    @param dxy_mm Element size in the board plane (mm).
    @param n_diel Elements across every dielectric gap.
    @return float Maximum temperature of the top face (degC).
    """
    r = f3.solve_fem(problem, dxy_mm, n_diel=n_diel)
    print(f"  {label:34s} {dxy_mm:4.1f} mm, {n_diel} per gap: {r['t_max']:.3f} degC ({r['nodes']} nodes, {r['seconds']:.0f} s)", flush=True)
    return r["t_max"]


def main():
    """!
    @brief Run the cases and print the differences quoted in README 4.2.
    @return None.
    """
    print("(a) 4 layers, full copper")
    p = f3.board_full_copper()
    a1 = run("1 mm elements", p, 1.0, 4)
    a1n2 = run("1 mm elements, 2 per gap", p, 1.0, 2)
    # 0.5 mm with 4 per gap is about 1.1 million nodes and the process was killed (memory), so 2 per gap is used here
    a05 = run("0.5 mm elements, 2 per gap", p, 0.5, 2)
    print(f"  4 -> 2 per gap at 1 mm: {a1n2 - a1:+.4f} degC; element size 1 -> 0.5 mm at 2 per gap: {a1n2:.2f} -> {a05:.2f} degC (change {a05 - a1n2:+.3f})")
    print("(b) example board")
    p = example_board()
    b1 = run("example board", p, 1.0, 4)
    b05 = run("example board", p, 0.5, 2)
    print(f"  1 mm, 4 per gap {b1:.2f} degC; 0.5 mm, 2 per gap {b05:.2f} degC (difference {b05 - b1:+.3f})")


if __name__ == "__main__":
    main()
