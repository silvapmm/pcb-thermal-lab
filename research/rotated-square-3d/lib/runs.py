#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file runs.py
@brief One call per model: the maximum temperature of a problem in the FVM, the FDM, the program's 3D solid or a variant of the 3D solid, plus a small JSON cache for the studies.
@details The studies print markdown tables and keep the numbers in `out/*.json` (git-ignored) so that `make_figures.py` can draw them without
         solving again. Nothing here changes the program.
"""

import json
import os

import rotsq
from pcbthermal import SolverOptions, simulate, solid3d

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def tmax(problem, model, cell_mm):
    """!
    @brief Maximum board temperature of a problem in one model.
    @param problem Problem.
    @param model "fvm", "fdm", "solid3d" (the program) or a key of `rotsq.VARIANTS` (a variant of the 3D solid, built from a copy of the source).
    @param cell_mm Cell size in mm.
    @return Maximum temperature in degrees Celsius.
    """
    if model in ("fvm", "fdm"):
        return float(simulate(problem, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model].t_max)
    mod = rotsq.variant_solid3d("program" if model == "solid3d" else model)
    # The finest cells of a ladder pass the application's 250 000-unknown limit: the study lifts it on the copy and on the program alike
    with solid3d.size_limit(600000), mod.size_limit(600000):
        return float(mod.solve_steady(problem, cell_mm=cell_mm).t_max)


def save(name, data):
    """!
    @brief Write a JSON file in out/.
    @param name File name.
    @param data Serialisable object.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)


def load(name):
    """!
    @brief Read a JSON file of out/.
    @param name File name.
    @return The object, or None when the file does not exist.
    """
    path = os.path.join(OUT, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
