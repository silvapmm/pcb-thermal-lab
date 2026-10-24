"""!
@file study_outline_time_constant.py
@brief Does the time constant of a board with an outline, and the step response the power profiles use, leave out the cells off the board?

@details The FVM and the FDM pin every cell (node) off the board to the ambient with 1 W/K so that the matrix stays regular. Before the correction that pin was
         added to the conductance to the air in `C_total / G_total`, so a round board had a time constant of a fraction of a second, the step responses
         (ten time constants long) stopped long before the steady state, and the animation was offered one second. The study compares a square board and the
         round board inscribed in it, with the pin counted (the old rule) and left out (the program now), and the end of the step response against the steady
         resistance. It also gives the board mean of a transient, which used to count the cells off the board at the ambient.

Usage: .venv/bin/python research/outline/scripts/study_outline_time_constant.py (from the repository root; about 20 seconds)
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from pcbthermal import Problem, fdm, fvm                               # noqa: E402

ROUND = [[30 + 29.9 * math.cos(a), 30 + 29.9 * math.sin(a)] for a in np.linspace(0, 2 * math.pi, 64, endpoint=False)]


def board(outline=None):
    """!
    @brief A 60 x 60 mm two-layer board with full copper and a 6 mm part of 2 W at the centre, optionally cut to an outline.
    @param outline Outline polygon in mm, or None for the square.
    @return Problem.
    """
    p = Problem.new(60.0, 60.0, 2).add_full_copper()
    p.add_heater(1, 2.0, rect=(27, 27, 33, 33), name="U")
    if outline is not None:
        p.set_outline(outline)
    return p


def time_constants(p, cell_mm=2.0):
    """!
    @brief The board time constant with the pin of the off-board cells counted (the old rule) and left out (the program).
    @param p Problem.
    @param cell_mm Cell size in mm.
    @return Tuple (old, new) in seconds.
    """
    net = fvm.Network(p, int(round(60.0 / cell_mm)), int(round(60.0 / cell_mm)), assemble=False, with_blocks=False)
    return float(net.C.sum() / net.g_amb.sum()), fvm.board_time_constant(net)


def main():
    """!
    @brief Print the table of time constants, the end of the step responses and the transient mean.
    @return None.
    """
    print("| board | time constant, pin counted (old) | time constant (program) |")
    print("| :-- | --: | --: |")
    for name, p in (("square 60 x 60 mm", board()), ("round, 59.8 mm across", board(ROUND))):
        old, new = time_constants(p)
        print(f"| {name} | {old:.2f} s | {new:.1f} s |")
    disc = board(ROUND)
    print("\n| model | end of the step response (program) | steady resistance | end / steady |")
    print("| :-- | --: | --: | --: |")
    for name, f in (("FVM", fvm.step_responses), ("FDM", fdm.step_responses)):
        t, z, r = f(disc, cell_mm=2.0)
        print(f"| {name} | {t[-1]:.0f} s, {z[0, -1]:.3f} K/W | {r[0]:.3f} K/W | {z[0, -1] / r[0]:.4f} |")
    old_tend = 10.0 * time_constants(disc)[0]
    t, z, r = fvm.step_responses(disc, cell_mm=2.0, t_end=old_tend)
    print(f"| FVM with the old length ({old_tend:.1f} s) | {z[0, -1]:.3f} K/W | {r[0]:.3f} K/W | {z[0, -1] / r[0]:.4f} |")
    tr = fvm.solve_transient(disc, 600.0, n_out=10, cell_mm=2.0)
    last = tr.frames[-1]
    print(f"\nTransient of the round board at 600 s: board mean {tr.t_mean[-1]:.2f} C (program), plain mean over the box {last.mean():.2f} C (old), maximum {tr.t_max[-1]:.2f} C")


if __name__ == "__main__":
    main()
