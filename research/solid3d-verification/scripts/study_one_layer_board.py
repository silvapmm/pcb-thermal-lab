"""!
@file study_one_layer_board.py
@brief Does the 3D solid keep the laminate of a one-layer board?

@details A one-layer board has no dielectric gap, and the 3D solid built its slabs from the gaps only, so the board was its copper alone: no FR-4 to spread the
         heat sideways and nothing between the copper and the bottom face. The program now adds the laminate of the layered models (the slab minus the copper)
         as four dielectric slabs under the copper. The study runs a 60 x 60 x 1.6 mm board with 35 um copper (full copper and a 20 mm pad, a 6 mm part of 1 W)
         in the five models, and the 3D solid on a board whose laminate is reduced to 1 um (what the 3D solid used to see).

Usage: .venv/bin/python research/solid3d-verification/scripts/study_one_layer_board.py (from the repository root; about 30 seconds)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from pcbthermal import Problem, SolverOptions, simulate                # noqa: E402

MODELS = ("fvm", "fdm", "solid3d", "lumped", "analytic")


def board(pad, thickness_mm=1.6):
    """!
    @brief The one-layer board of the study.
    @param pad True for a 20 mm copper pad, False for full copper.
    @param thickness_mm Board thickness in mm.
    @return Problem.
    """
    p = Problem.new(60.0, 60.0, layers=1, thickness_mm=thickness_mm, copper_um=35)
    if pad:
        p.add_zone(1, rect=(20, 20, 40, 40))
    else:
        p.add_full_copper()
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    return p


def main():
    """!
    @brief Print the maximum temperature of every model and of the 3D solid without the laminate.
    @return None.
    """
    print("| copper | " + " | ".join(MODELS) + " | 3D solid without the laminate (old) |")
    print("| :-- | " + " | ".join("--:" for _ in MODELS) + " | --: |")
    for label, pad in (("full copper", False), ("20 mm pad", True)):
        r = simulate(board(pad), SolverOptions(models=MODELS, cell_mm=1.0)).results
        old = simulate(board(pad, thickness_mm=0.036), SolverOptions(models=("solid3d",), cell_mm=1.0)).results["solid3d"]
        print(f"| {label} | " + " | ".join(f"{r[m].t_max:.2f}" for m in MODELS) + f" | {old.t_max:.2f} |", flush=True)


if __name__ == "__main__":
    main()
