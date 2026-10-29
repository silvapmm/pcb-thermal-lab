#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_board_effect.py
@brief How much does the natural-convection level of a vertical face change the rise of a board? The program's computed-h mode run with each level on boards 40 to 200 mm tall.

@details Question: the computed coefficient of a vertical face (`Board.orientation = "vertical"`, `h_mode = "computed"`) uses Churchill and Chu; the laminar boundary-layer
         theory, the laminar form of the same authors and the 0.59 Ra^(1/4) of the composite of Bar-Cohen and Rohsenow differ by 0 to 13 % in Nu. The study runs the program's own FVM
         (the program is not edited: `lib/levels.use_level` replaces `convection.h_natural_vertical` in memory) on

         * the two example boards of the program (`examples/example_board.pcbt.json`, `reference_board.pcbt.json`) set vertical and computed;
         * a two-layer board with full copper on both layers and one 10 x 10 mm part, square, 40 / 60 / 100 / 150 / 200 mm tall, at powers that give rises of about 10 to 60 K.

         The radiation to the surroundings (emissivity 0.9 on both faces, the program's default) is included, as the program does, and the same runs are repeated with the
         emissivity set to zero (convection only) to show how much radiation dilutes the choice. The horizontal board does not use these correlations, and is not affected.
         The results go to out/board_effect.json for make_figures.py.

Usage: .venv/bin/python research/plate-h-level/scripts/study_board_effect.py   (about 1 minute)
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import levels as L                                      # noqa: E402
from pcbthermal import api, project                     # noqa: E402
from pcbthermal.model import Problem                    # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
LEVELS = ("general", "laminar", "bl", "bl_le", "mcadams")


def run(problem, level, cell=2.0):
    """!
    @brief The program's FVM with the computed coefficient of the given level.
    @param problem Problem (modified: vertical, computed).
    @param level One of levels.LEVELS.
    @param cell Cell size in mm.
    @return dict with rise (K, hottest point minus ambient), h_top and h_bottom used (W/m2K, convection plus radiation).
    """
    problem.board.h_mode = "computed"
    problem.board.orientation = "vertical"
    with L.use_level(level):
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


def table(make, label, results):
    """!
    @brief Run every level on a problem and, with the emissivity at zero, again.
    @param make Function that builds a fresh Problem.
    @param label Name of the case.
    @param results List that receives the row.
    @return None.
    """
    row = {"case": label}
    for eps0 in (False, True):
        for lv in LEVELS:
            p = make()
            if eps0:
                p.board.emissivity_top = p.board.emissivity_bottom = 0.0
            r = run(p, lv)
            row[("conv_" if eps0 else "") + lv] = r
    ref = row["general"]["rise"]
    refc = row["conv_general"]["rise"]
    line = f"{label:34s} " + "  ".join(f"{lv}:{row[lv]['rise']:6.2f} ({100*(row[lv]['rise']/ref-1):+5.1f}%)" for lv in LEVELS)
    print(line)
    print(f"{'  convection only':34s} " + "  ".join(f"{lv}:{row['conv_'+lv]['rise']:6.2f} ({100*(row['conv_'+lv]['rise']/refc-1):+5.1f}%)" for lv in LEVELS))
    print(f"{'  h (top, bottom) general':34s} {row['general']['h']}")
    results.append(row)


def main():
    """!
    @brief Run the cases and write out/board_effect.json.
    @return None.
    """
    results = []
    print("rise of the hottest point (K) and difference to the program's general form")
    for name in ("example_board", "reference_board"):
        path = os.path.join(ROOT, "examples", name + ".pcbt.json")
        table(lambda path=path: project.load_project(path).problem, name + " (vertical)", results)
    for size, powers in ((40, (0.2, 0.8)), (60, (0.4, 1.5)), (100, (1.0, 3.0)), (150, (2.0, 6.0)), (200, (3.0, 10.0))):
        for pw in powers:
            table(lambda size=size, pw=pw: synthetic(size, pw), f"{size} mm square, {pw} W", results)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "board_effect.json"), "w") as f:
        json.dump(results, f, indent=1)


if __name__ == "__main__":
    main()
