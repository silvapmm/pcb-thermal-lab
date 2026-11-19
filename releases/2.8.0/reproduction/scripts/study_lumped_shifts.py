#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_lumped_shifts.py
@brief Which 2.8.0 item moves the Lumped column of copper_dissipation and the no-via row of calculator_validation, by how much, and which version is closer to a reference?

@details Run from the repository root against one program tree (a `git archive <commit> pcbthermal` extracted into a scratch folder, or the repository itself):

    .venv/bin/python releases/2.8.0/reproduction/scripts/study_lumped_shifts.py --tree <folder holding pcbthermal/> --case <case> [--cell MM]

Cases (each prints one JSON line):
  * `lumped`: the Lumped peak of the six top pads of research/solid3d-verification/scripts/copper_dissipation.py (100 x 80 mm, 2 layers, 5 W on a 10 mm heater),
    as the program runs it (SolverOptions, 10 rings, `lumped.cell_for`) and as the study calls it (`lumped.solve_steady(p, 1.0)`: the 1.0 is the positional `rings`).
  * `fem`: the program's finite-element model on the 10, 20 and 80 mm pads (needs the tree of 2.8.0; cell `--cell`, default 1 mm).
  * `calc`: the no-via row of research/power-calculator/scripts/calculator_validation.py (JEDEC 2s2p board without the thermal vias, FVM 0.5 mm, computed h), in K/W.
  * `jedec`: one FVM run of that board at 1 W with the fixed default coefficients (`--cell`, default 0.5 mm): the part peak rise.
  * `window`: a 41 x 40 cell window of the JEDEC grid at 0.5 mm (20.46441 x 20.05263 mm, the same 3.15 mm pad on its 4.15 mm land at the centre, the inner planes over the window,
    fixed coefficients): the part peak rise at `--cell`, for the grid convergence of the cut land (about 1.4 GB at 0.1 mm).
  * `aligned`: the control, 20 x 20 mm with the same stack, a 3 mm pad on a 5 mm land centred at 10.125 mm (edges at 1/4 and 3/4 of a 0.5 mm cell, on the lines of a 0.125 mm grid).
  `--variant` (case `jedec` only): `asis` (default), `fullplanes` (inner planes over the whole board), `noland` (no top land).
Memory: `calc` 1.45 GB, `jedec` 1.3 GB, `window` 0.1 to 1.4 GB, `lumped` and `fem` below 0.8 GB.
"""

import argparse
import json
import logging
import os
import sys


def pads_board(problem_cls, pad_mm=None):
    """!
    @brief The board of copper_dissipation.board (no heatsink): 100 x 80 mm, 2 layers, 5 W on a 10 x 10 mm heater, an optional square top pad centred on it.
    @param problem_cls The Problem class of the tree under test.
    @param pad_mm Side of the top copper pad in mm (None: only the heater's own 10 mm pad).
    @return Problem.
    """
    p = problem_cls.new(100, 80, 2)
    if pad_mm:
        p.add_zone(1, rect=(50 - pad_mm / 2, 40 - pad_mm / 2, 50 + pad_mm / 2, 40 + pad_mm / 2))
    else:
        p.add_zone(1, rect=(45, 35, 55, 45))
    p.add_heater(1, 5.0, rect=(45, 35, 55, 45))
    return p


def aligned_board(problem_cls):
    """!
    @brief The aligned control: 20 x 20 mm, the JEDEC stack with inner planes over the board, 1 W on a 3 mm pad over a 5 mm land centred at (10.125, 10.125) mm.
    @param problem_cls The Problem class of the tree under test.
    @return Problem.
    """
    p = problem_cls.new(20.0, 20.0, 4)
    b = p.board
    b.thickness, b.copper_thickness, b.h_side = 1.6e-3, [70e-6, 35e-6, 35e-6, 70e-6], None
    for layer in (2, 3):
        p.add_zone(layer, rect=(0.0, 0.0, 20.0, 20.0))
    p.add_zone(1, rect=(7.625, 7.625, 12.625, 12.625))
    p.add_heater(1, 1.0, rect=(8.625, 8.625, 11.625, 11.625), name="U1")
    return p


def jedec_board(problem_cls, width=114.3, height=76.2, computed=False, variant="asis"):
    """!
    @brief The JEDEC 2s2p board of calculator_validation.jedec_2s2p_board(vias=False), or a window of it with the same pad and land at its centre and the planes over the window.
    @param problem_cls The Problem class of the tree under test.
    @param width Board width in mm (114.3 for the whole board).
    @param height Board height in mm (76.2 for the whole board).
    @param computed True for the computed heat transfer coefficients of the calculator study, False for the fixed defaults.
    @param variant "asis", "fullplanes" (inner planes over the whole board) or "noland" (no top land).
    @return Problem.
    """
    p = problem_cls.new(width, height, 4)
    b = p.board
    b.thickness, b.copper_thickness, b.h_side = 1.6e-3, [70e-6, 35e-6, 35e-6, 70e-6], None
    if computed:
        b.h_mode = "computed"
    cx, cy, pad = width / 2, height / 2, 3.15
    whole = abs(width - 114.3) < 1e-9
    for layer in (2, 3):
        # The whole board keeps the planes of the study (74.2 mm square); the window has them over its whole area (their edges do not move the shift: 8.83 against 8.83 K)
        p.add_zone(layer, rect=(cx - 37.1, cy - 37.1, cx + 37.1, cy + 37.1) if whole and variant != "fullplanes" else (0.0, 0.0, width, height))
    if variant != "noland":
        p.add_zone(1, rect=(cx - pad / 2 - 0.5, cy - pad / 2 - 0.5, cx + pad / 2 + 0.5, cy + pad / 2 + 0.5))      # The land of the pad
    p.add_heater(1, 1.0, rect=(cx - pad / 2, cy - pad / 2, cx + pad / 2, cy + pad / 2), name="U1", theta=1.7)
    return p


def main():
    """!
    @brief Parse the arguments, import the program of the tree and print the case as one JSON line.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--case", required=True, choices=("lumped", "fem", "calc", "jedec", "window", "aligned"))
    ap.add_argument("--variant", default="asis", choices=("asis", "fullplanes", "noland"))
    ap.add_argument("--cell", type=float, default=None)
    a = ap.parse_args()
    logging.disable(logging.CRITICAL)
    sys.path.insert(0, os.path.abspath(a.tree))                    # The program of the tree, before anything else
    import pcbthermal
    from pcbthermal import Problem, fvm, lumped
    from pcbthermal.analysis import heater_stats
    from pcbthermal.api import SolverOptions, simulate
    out = {"tree": os.path.dirname(pcbthermal.__file__), "case": a.case}
    if a.case == "lumped":
        for pad in (None, 20, 30, 40, 60, 80):
            key = pad or 10
            out[f"program_{key}"] = round(float(simulate(pads_board(Problem, pad), SolverOptions(models=("lumped",), cell_mm=1.0)).results["lumped"].t_max), 1)
            try:
                out[f"study_rings1_{key}"] = round(float(lumped.solve_steady(pads_board(Problem, pad), 1.0).t_max), 1)   # rings = 1.0, as the study passed it
            except ValueError as exc:                                                       # Trees with the rings guard refuse it, which is the point of the guard
                out[f"study_rings1_{key}"] = f"refused: {exc}"
    elif a.case == "fem":
        for pad in (None, 20, 80):
            out[f"fem_{pad or 10}"] = round(float(simulate(pads_board(Problem, pad), SolverOptions(models=("fem",), cell_mm=a.cell or 1.0)).results["fem"].t_max), 1)
    elif a.case == "calc":
        from pcbthermal.inverse import power_from_temperature
        p = jedec_board(Problem, computed=True)
        r = power_from_temperature(p, 0, p.board.ambient + 32.5, point="junction", cell_mm=0.5)
        out["model_theta_ja_k_per_w"] = round(32.5 / r["power_w"], 2)
    else:
        if a.case == "jedec":
            p = jedec_board(Problem, variant=a.variant)
        elif a.case == "window":
            p = jedec_board(Problem, 20.46441, 20.05263)
        else:
            p = aligned_board(Problem)
        r = fvm.solve_steady(p, a.cell or 0.5)
        out["cell_mm"], out["variant"] = a.cell or 0.5, a.variant
        out["part_peak_rise_k"] = round(heater_stats(r, p)[0]["t_max"] - p.board.ambient, 4)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
