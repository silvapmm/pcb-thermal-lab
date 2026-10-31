#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_board_effect.py
@brief How much does the natural-convection level of the HORIZONTAL faces change the rise of a board and of the finned block with fins down? The program's computed-h mode run with other levels on a copy in memory.

@details Question: the program gives a horizontal board `Nu = 0.54 Ra^(1/4)` (then 0.15 Ra^(1/3) above 1e7) on the upper face and `0.27 Ra^(1/4)` on the lower, with L = A/P.
         Jaffer (2023) fits the measurements of several authors with other forms (`lib/correlations.py`); the 2D and axisymmetric solutions of `study_plate_h2d.py` show how the
         upper face of a thin board with both faces hot differs from an isolated face. The study runs the program's own FVM (the program is not edited:
         `correlations.use_horizontal` replaces `convection.h_natural_horizontal` in memory) with

         * `program`: the program's levels (the reference of the table);
         * `jaffer`: Jaffer's equation 30 above and his downward formula 56 below (with the shape metric L_R of the board);
         * `jaffer down`: the program's upper face, Jaffer's lower face (the effect of the lower face alone; added by the review);
         * `R&H up`: Raithby and Hollands' upper face as printed by Lienhard (8.37a/b), the program's lower face (the other published upper face, below the program's; added by the review);
         * `up x0.6`, `down x1.3`, `up x0.6 down x1.3`, `up x1.2`, `down x0.7`: sensitivity runs, the program's levels with a factor on one or both faces
           (the factors are NOT a result: they bracket what the numerical solutions and the literature suggest, section 6 of the README).

         on the two example boards (horizontal, computed h, layer 1 up), square two-layer boards of 40 to 200 mm with one 10 x 10 mm part, and the finned block of
         `research/fin-channel` (60 x 40 mm board, 3 W, aluminium block with fins on the bottom face, so the fins hang down) with the program's uniform fin coefficient.
         Radiation (emissivity 0.9, the program's default) is included, and repeated with emissivity zero (convection only) for the boards. Results go to out/board_effect.json.

Usage: .venv/bin/python research/horizontal-plate-h/scripts/study_board_effect.py   (about 2 minutes)
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(ROOT, "research", "block-and-fins", "scripts"))

import correlations as C                                 # noqa: E402
from pcbthermal import api, project                       # noqa: E402
from pcbthermal.model import Problem                      # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")


def scaled(fn, factor):
    """!
    @brief A Nusselt function multiplied by a constant factor.
    @param fn Function of Ra.
    @param factor Multiplier.
    @return Function of Ra.
    """
    return lambda ra: factor * fn(ra)


def levels_for(q):
    """!
    @brief The levels of the study for a board whose downward metric of Jaffer's formula (half the shorter side) is q times its A/P.
    @param q Ratio L_R / (A/P): 2 for a square, 1.8 for a 100 x 80 mm rectangle.
    @return dict level name -> (Nu_up(Ra), Nu_down(Ra)).
    """
    return {
        "program": (C.program_up, C.program_down),
        "jaffer": (C.jaffer_up, lambda ra: C.jaffer_down_shape(ra, q)),
        "jaffer down": (C.program_up, lambda ra: C.jaffer_down_shape(ra, q)),
        "R&H up": (C.raithby_hollands_up, C.program_down),
        "up x0.6": (scaled(C.program_up, 0.6), C.program_down),
        "down x1.3": (C.program_up, scaled(C.program_down, 1.3)),
        "up x0.6 down x1.3": (scaled(C.program_up, 0.6), scaled(C.program_down, 1.3)),
        "up x1.2": (scaled(C.program_up, 1.2), C.program_down),
        "down x0.7": (C.program_up, scaled(C.program_down, 0.7)),
    }


LEVELS = levels_for(2.0)                                  # keys only; the functions are chosen per board in run()


def shape_q(problem):
    """!
    @brief L_R / (A/P) of the board outline: half the shorter side over the area-to-perimeter ratio of the rectangle.
    @param problem Problem.
    @return float.
    """
    w, h = problem.board.width, problem.board.height
    return 0.5 * min(w, h) / (w * h / (2.0 * (w + h)))


def run(problem, level, cell=2.0):
    """!
    @brief The program's FVM with the computed coefficients of a horizontal board at the given level.
    @param problem Problem (modified: horizontal, computed).
    @param level Key of LEVELS.
    @param cell Cell size in mm.
    @return dict with rise (K, hottest point minus ambient) and h used on the two faces (W/m2K, convection plus radiation).
    """
    problem.board.h_mode = "computed"
    problem.board.orientation = "horizontal"
    with C.use_horizontal(*levels_for(shape_q(problem))[level]):
        sim = api.simulate(problem, api.SolverOptions(models=("fvm",), cell_mm=cell))
    r = sim.results["fvm"]
    hh = sim.h_used.get("fvm")
    return {"rise": float(r.delta_t), "h": [float(v) for v in hh[:2]] if hh is not None else None}


def synthetic(size_mm, power):
    """!
    @brief Square two-layer board with full copper and a 10 x 10 mm part in the centre.
    @param size_mm Side in mm.
    @param power Power in W.
    @return Problem.
    """
    p = Problem.new(size_mm, size_mm, 2)
    p.add_zone(1, rect=(1, 1, size_mm - 1, size_mm - 1))
    p.add_zone(2, rect=(1, 1, size_mm - 1, size_mm - 1))
    c = size_mm / 2.0
    p.add_heater(1, power, rect=(c - 5, c - 5, c + 5, c + 5), name="U1")
    return p


def finned(power=3.0, gap=6.5):
    """!
    @brief The finned block of research/fin-channel on a horizontal board: the aluminium block with fins on the bottom face (the fins hang down).
    @param power Power in W.
    @param gap Gap between the fins in mm.
    @return Problem.
    """
    from study_finned_block_all_models import board
    p = board((15.0, 1.5, gap + 1.5))
    p.heaters[0].power = power
    return p


def table(make, label, results, eps_zero=True):
    """!
    @brief Run every level on a problem (and, optionally, again with zero emissivity) and print the rises.
    @param make Function that builds a fresh Problem.
    @param label Name of the case.
    @param results List that receives the row.
    @param eps_zero Also run with the emissivity at zero (convection only).
    @return None.
    """
    row = {"case": label}
    for eps0 in ((False, True) if eps_zero else (False,)):
        for lv in LEVELS:
            p = make()
            if eps0:
                p.board.emissivity_top = p.board.emissivity_bottom = 0.0
            row[("conv_" if eps0 else "") + lv] = run(p, lv)
    ref = row["program"]["rise"]
    print(f"{label:34s} " + "  ".join(f"{lv}:{row[lv]['rise']:6.2f} ({100 * (row[lv]['rise'] / ref - 1):+5.1f}%)" for lv in LEVELS))
    if eps_zero:
        refc = row["conv_program"]["rise"]
        print(f"{'  convection only':34s} " + "  ".join(f"{lv}:{row['conv_' + lv]['rise']:6.2f} ({100 * (row['conv_' + lv]['rise'] / refc - 1):+5.1f}%)" for lv in LEVELS))
    print(f"{'  h (top, bottom) program':34s} {row['program']['h']}   jaffer {row['jaffer']['h']}")
    results.append(row)


def main():
    """!
    @brief Run the cases and write out/board_effect.json.
    @return None.
    """
    results = []
    print("rise of the hottest point (K) and difference to the program's levels")
    for name in ("example_board", "reference_board"):
        path = os.path.join(ROOT, "examples", name + ".pcbt.json")
        table(lambda path=path: project.load_project(path).problem, name + " (horizontal)", results)
    for size, powers in ((40, (0.2, 0.8)), (60, (0.4, 1.5)), (100, (1.0, 3.0)), (150, (2.0, 6.0)), (200, (3.0, 10.0))):
        for pw in powers:
            table(lambda size=size, pw=pw: synthetic(size, pw), f"{size} mm square, {pw} W", results)
    print("\nfinned block, fins down (convection and radiation, uniform fin coefficient of the program)")
    for gap in (3.5, 6.5, 14.5):
        table(lambda gap=gap: finned(3.0, gap), f"finned block gap {gap} mm", results, eps_zero=False)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "board_effect.json"), "w") as f:
        json.dump(results, f, indent=1)


if __name__ == "__main__":
    main()
