#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file harness.py
@brief Shared helpers of the studies: the boards (reused from research/point-via-convergence/lib, read only), the independent fine-grid references, and the variants of Lumped and
       Analytic (the program and the in-memory patches) that are compared.
@details The via effect E = T_max(no via) - T_max(with vias) (K) is the metric. For every case the reference E is computed by the layered fine-grid solver `sheets2d` (the
         layered model of the program with every barrel drawn at its real size on a 1/16 mm grid; no program imported) from the numbers that the program's own network gives for
         a board without vias (`program_cases.layer_parameters`). A second reference, the 3D solver with the barrels drawn (`layered3d`), is available for the uniform boards.
         `VARIANTS` lists the models compared: the program (`off`), the constriction patches of `lumped_patch` and `analytic_patch`, the FVM at 1 and 0.5 mm for scale.
"""

import contextlib
import copy
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "research", "point-via-convergence", "lib"))
sys.path.insert(0, os.path.join(ROOT, "research", "solid3d-verification", "lib"))
sys.path.insert(0, HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import analytic_patch as ap                                                  # noqa: E402
import lumped_patch as lp                                                    # noqa: E402
import program_cases as pc                                                   # noqa: E402
import program_patch as pp                                                   # noqa: E402
import resolved_boards as rb                                                 # noqa: E402
from constriction import ETA                                                 # noqa: E402

# name -> (model key, context-manager factory). The factories take no argument and return a fresh context.
VARIANTS = {
    "FVM": ("fvm", lambda: contextlib.nullcontext()),
    "FVM_fix": ("fvm", lambda: pp.patched("mw_disc", eta=ETA)),
    "L_prog": ("lumped", lambda: contextlib.nullcontext()),
    "L_ring": ("lumped", lambda: lp.patched("krogh", cell="ring")),
    "L_nn": ("lumped", lambda: lp.patched("krogh", cell="nn")),
    "L_grp0": ("lumped", lambda: lp.patched("krogh", cell="nn", cluster=True)),
    "L_grp": ("lumped", lambda: lp.patched("krogh", cell="nn", cluster=True, macro_cap=0.75)),
    "A_prog": ("analytic", lambda: contextlib.nullcontext()),
    "A_on": ("analytic", lambda: ap.patched("on")),
    "A_bil": ("analytic", lambda: ap.patched("on", spread="bilinear")),
    "A_fin": ("analytic", lambda: ap.patched("on", spread="bilinear", tile_cap=1.0)),
}


def reference_uniform(problem, dx_mm=1.0 / 16, rect=None, power=None):
    """!
    @brief Via effect of a board of full copper planes (any layers, square, insulated edges) by the fine-grid layered solver.
    @param problem A Problem whose layers are full copper, with a single heater on layer 1 (its power is the source) and vias of one radius.
    @param dx_mm Cell of the solver in mm (must divide the side, the source and the via coordinates for the exactness of the symmetry; the barrels are drawn by area).
    @param rect Source rectangle (x0, y0, x1, y1) in metres (default: the polygon of the heater) .
    @param power Power in W (default: the heater's).
    @return tuple (E, T_with, T_without) in K.
    """
    par = pc.layer_parameters(problem)
    h = problem.heaters[0]
    xs = [p[0] for p in h.polygon]
    ys = [p[1] for p in h.polygon]
    r = rect if rect is not None else (min(xs), min(ys), max(xs), max(ys))
    pw = power if power is not None else h.power
    dx = dx_mm * 1e-3
    vias = [(x, y, k) for k, (x, y) in enumerate(par["xy"])]
    t_with = rb.full_board_2d(par, dx, vias, pw, r)
    t_without = rb.full_board_2d(par, dx, [], pw, r)
    return t_without - t_with, t_with, t_without


def reference_field(problem, dx_mm=1.0 / 16, with_vias=True):
    """!
    @brief Temperature field of a uniform square board by the fine-grid layered solver (all layers).
    @param problem Problem as in reference_uniform.
    @param dx_mm Cell in mm.
    @param with_vias False: the board without vias.
    @return tuple (T, dx) with T of shape (layers, n, n) in K over the ambient and dx in m.
    """
    import numpy as np
    import sheets2d
    par = pc.layer_parameters(problem)
    h = problem.heaters[0]
    xs = [p[0] for p in h.polygon]
    ys = [p[1] for p in h.polygon]
    dx = dx_mm * 1e-3
    n = int(round(par["width"] / dx))
    vias = [(x, y, k) for k, (x, y) in enumerate(par["xy"])] if with_vias else []
    S, gz, g_amb = rb._arrays(par, n, dx, vias, par["r_via"][0], 0.0, None)
    L = len(par["S"])
    Q = np.zeros((L, n, n))
    j0, j1, i0, i1 = (int(round(min(xs) / dx)), int(round(max(xs) / dx)), int(round(min(ys) / dx)), int(round(max(ys) / dx)))
    Q[0, i0:i1, j0:j1] = h.power / ((i1 - i0) * (j1 - j0))
    return sheets2d.solve(S, gz, g_amb, Q, dx), dx


def reference_3d_uniform(problem, dx_mm=1.0 / 16, n_sub=4):
    """!
    @brief Via effect of the same board by the 3D solver with the barrels drawn at their real size (a check of the layered idealisation, not of the models).
    @param problem Problem as in reference_uniform.
    @param dx_mm Cell in mm.
    @param n_sub Sub-slabs per gap.
    @return float E in K.
    """
    par = pc.layer_parameters(problem)
    h = problem.heaters[0]
    xs = [p[0] for p in h.polygon]
    ys = [p[1] for p in h.polygon]
    rect = (min(xs), min(ys), max(xs), max(ys))
    dx = dx_mm * 1e-3
    vias = [(x, y, k) for k, (x, y) in enumerate(par["xy"])]
    t_with = rb.full_board_3d(par, dx, vias, h.power, rect, n_sub)
    t_without = rb.full_board_3d(par, dx, [], h.power, rect, n_sub)
    return t_without - t_with


def no_vias(problem):
    """!
    @brief A copy of a problem without vias.
    @param problem The Problem.
    @return Problem.
    """
    q = copy.deepcopy(problem)
    q.vias = []
    return q


def effect(problem, model, ctx, cell_mm, p_without=None):
    """!
    @brief Via effect of one model/variant on a problem.
    @param problem Problem with vias.
    @param model Model key.
    @param ctx Context-manager factory (a patch or a null context) applied to the run with vias AND to the run without (the patches do not change a board without vias).
    @param cell_mm Cell in mm.
    @param p_without The problem without vias (made if None).
    @return float E in K.
    """
    q0 = p_without if p_without is not None else no_vias(problem)
    with ctx():
        return pc.max_rise(q0, model, cell_mm) - pc.max_rise(problem, model, cell_mm)


def errors(problem, e_ref, cell_mm=0.5, names=None):
    """!
    @brief Error of every variant against the reference via effect, in percent of E.
    @param problem Problem with vias.
    @param e_ref Reference via effect in K.
    @param cell_mm Cell of the models in mm (the FVM gets 0.5 as well).
    @param names Names of the variants (default all).
    @return dict name -> error in percent.
    """
    pc.load_libraries()
    q0 = no_vias(problem)
    out = {}
    for name in names or VARIANTS:
        model, ctx = VARIANTS[name]
        out[name] = 100.0 * (effect(problem, model, ctx, cell_mm, q0) / e_ref - 1.0)
    return out


__all__ = ["VARIANTS", "reference_uniform", "reference_3d_uniform", "no_vias", "effect", "errors", "ETA", "math"]
