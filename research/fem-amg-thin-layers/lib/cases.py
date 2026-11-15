#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cases.py
@brief The test matrices of research/fem-amg-thin-layers: the assembled finite-element system (A, rhs) of the boards named in README section 3, built with the program's own mesher and assembly.
@details The program is imported, never edited. A case is a name plus a plan cell in mm; `build` returns the SPD matrix of the unknowns and the right-hand side exactly as `femcore.Model.solve`
         sees them (`Model.assemble`). Written, not run.
"""

import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if os.path.join(ROOT, "tests", "regression") not in sys.path:
    sys.path.insert(1, os.path.join(ROOT, "tests", "regression"))

#: Named cases: (builder key, default cell in mm). 'frozen:<board>' is a board of tests/regression/regress_boards.py.
CASES = {
    "example_1mm": ("example_board", 1.0),
    "example_2mm": ("example_board", 2.0),
    "plate_vias_1mm": ("frozen:plate_vias", 1.0),
    "case2_plate_1mm": ("case2_plate", 1.0),
    "thin4_1mm": ("thin4", 1.0),
    "big_cap": ("example_board", None),          # cell chosen by `cell_for_unknowns` to sit near the target unknown count
}


def thin4():
    """!
    @brief A thin four-layer board, 100 x 80 mm, 1.6 mm, 35 um copper on every layer, one 4 W part: the plainest thin-layer matrix (no vias, no partial copper).
    @return A Problem.
    """
    from pcbthermal import Problem
    p = Problem.new(width_mm=100, height_mm=80, layers=4, name="thin4")
    p.add_full_copper()
    p.add_heater(1, 4.0, rect=(45, 35, 55, 45), name="U")
    return p


def case2_plate():
    """!
    @brief Case 2 of Muzychka, Culham and Yovanovich (2003): a 50 x 50 x 10 mm copper plate (k 150), four 10 x 10 mm sources of 10, 25, 20 and 15 W, h 400 W/m2K on the bottom (as tests/test_fem_gui.py).
    @return A Problem.
    """
    from pcbthermal.model import Materials, Problem
    p = Problem.new(50, 50, layers=1, thickness_mm=10.001, copper_um=1e4, ambient=25.0, h_top=1e-6, h_bottom=400.0, h_side=None, materials=Materials(k_copper=150.0))
    p.add_full_copper()
    for i, (c, pw) in enumerate(zip([(12.5, 12.5), (37.5, 12.5), (12.5, 37.5), (37.5, 37.5)], [10.0, 25.0, 20.0, 15.0])):
        p.add_heater(1, pw, rect=(c[0] - 5, c[1] - 5, c[0] + 5, c[1] + 5), name=f"S{i}")
    return p


def problem_of(key):
    """!
    @brief The Problem of a builder key.
    @param key 'example_board', 'thin4', 'case2_plate' or 'frozen:<board name>'.
    @return A Problem.
    @throws KeyError If the key is unknown.
    """
    if key == "example_board":
        from pcbthermal.examples import example_board
        return example_board()
    if key == "thin4":
        return thin4()
    if key == "case2_plate":
        return case2_plate()
    if key.startswith("frozen:"):
        import regress_boards
        return regress_boards.build(key.split(":", 1)[1])
    raise KeyError(key)


def cell_for_unknowns(problem, target, lo=0.3, hi=4.0):
    """!
    @brief The plan cell (mm) whose FEM unknown count is nearest below `target` (bisection on `femmesh.unknowns`, which builds nothing heavy).
    @param problem A Problem.
    @param target Wanted unknown count (for the cap-size board, about 800 000).
    @param lo Finest cell tried in mm.
    @param hi Coarsest cell tried in mm.
    @return float Cell in mm.
    """
    from pcbthermal import femmesh
    a, b = lo, hi
    for _ in range(14):
        mid = 0.5 * (a + b)
        if femmesh.unknowns(problem, mid)[0] > target:
            a = mid
        else:
            b = mid
    return round(b, 3)


def build(name, cell_mm=None, target=800_000):
    """!
    @brief Assemble the system of a named case.
    @param name A key of CASES.
    @param cell_mm Plan cell in mm, or None for the case's default.
    @param target Unknown count for the 'big_cap' case.
    @return dict with A (scipy CSR, SPD), rhs (n,), n, cell_mm, label and model (the femcore.Model, kept for the reuse studies).
    """
    from pcbthermal import femmesh
    key, cell = CASES[name]
    problem = problem_of(key)
    cell = cell_mm if cell_mm is not None else cell
    if cell is None:
        cell = cell_for_unknowns(problem, target)
    mesh = femmesh.build(problem, cell, 6, 2.0)                    # gap_elements 6 and refine 2.0: the program's defaults
    a = mesh.model.assemble()
    return {"A": a["A"].tocsr(), "rhs": np.asarray(a["rhs"], float), "n": int(a["rhs"].size), "cell_mm": float(cell), "label": f"{name}@{cell}", "model": mesh.model, "mesh": mesh}


def frozen_fem_keys():
    """!
    @brief The 29 (board, cell) pairs of the frozen finite-element records (`tests/regression/data/pending/fem-records.json`, key 'board|fem|cell').
    @return list of (board name, cell in mm).
    """
    import json
    path = os.path.join(ROOT, "tests", "regression", "data", "pending", "fem-records.json")
    with open(path) as fh:
        recs = json.load(fh)["records"]
    out = []
    for k in recs:
        board, model, cell = k.split("|")
        if model == "fem":
            out.append((board, float(cell)))
    return out
