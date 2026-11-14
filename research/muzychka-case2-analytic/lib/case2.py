#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file case2.py
@brief Case 2 of Muzychka, Culham and Yovanovich (2003) (baseplate 50 x 50 x 10 mm, k 150, four 10 x 10 mm sources) as an independent 3D solution and as a project of the program.
@details Shared by the studies of this folder. The independent solver is tests/helpers/layered3d.py (imports nothing from pcbthermal); the program side builds the plate exactly as
         research/theory-sources/scripts/study_muzychka_more_cases.py does (one copper layer of 10 mm with the plate conductivity, top face adiabatic, bottom h, no side loss).
"""

import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
for p in (ROOT, os.path.join(ROOT, "tests", "helpers")):
    if p not in sys.path:
        sys.path.insert(0, p)
import layered3d as L  # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate  # noqa: E402
from pcbthermal.model import Materials  # noqa: E402

AMB = 25.0
W_MM, T_MM, K_PLATE, H_PAPER = 50.0, 10.0, 150.0, 400.0
POWERS = [10.0, 25.0, 20.0, 15.0]
CENTRES = [(12.5, 12.5), (37.5, 12.5), (12.5, 37.5), (37.5, 37.5)]
PAPER_CENTROID = [97.40, 103.82, 101.28, 99.94]
PAPER_MEAN = [96.85, 102.33, 100.10, 99.07]


def rect(c, side=10.0):
    """!
    @brief Square source rectangle.
    @param c Centre (x, y) in mm.
    @param side Side in mm.
    @return Tuple (x0, y0, x1, y1) in mm.
    """
    return (c[0] - side / 2, c[1] - side / 2, c[0] + side / 2, c[1] + side / 2)


def corner_value(field, dx, cx, cy):
    """!
    @brief Mean of the four cells around a point that falls on a cell corner (the centroid of a source).
    @param field Array (ny, nx).
    @param dx Cell size in mm.
    @param cx X in mm.
    @param cy Y in mm.
    @return float The value.
    """
    i, j = int(round(cx / dx)), int(round(cy / dx))
    return float(field[j - 1:j + 1, i - 1:i + 1].mean())


def reference3d(dx_mm=0.5, n_sub=16, h=H_PAPER, k=K_PLATE, h_top=0.0):
    """!
    @brief The independent 3D solution of the plate.
    @param dx_mm Plan cell in mm.
    @param n_sub Sub-slabs through the thickness.
    @param h Bottom film coefficient in W/m2K.
    @param k Plate conductivity in W/mK.
    @param h_top Top film coefficient outside the sources in W/m2K (the paper: 0).
    @return dict with, per source, the surface centroid and mean (the paper's quantities), the through-thickness mean (layer mean) centroid and mean, and the bottom mean, all in degC.
    """
    n = int(round(W_MM / dx_mm))
    rects = [tuple(v * 1e-3 for v in rect(c)) for c in CENTRES]
    res = L.solve(dx_mm * 1e-3, n, n, [(T_MM * 1e-3, k, n_sub)], rects, POWERS, h_top, h)
    dz = np.array(res["dz"])
    layer = np.tensordot(dz / dz.sum(), res["T"], axes=(0, 0))      # thickness-weighted mean of the column
    out = {"surf_c": [], "surf_m": [], "lay_c": [], "lay_m": [], "max": []}
    xs = (np.arange(n) + 0.5) * dx_mm
    for r, c in zip(CENTRES, rects):
        x0, y0, x1, y1 = rect(r)
        m = (xs[None, :] > x0) & (xs[None, :] < x1) & (xs[:, None] > y0) & (xs[:, None] < y1)
        out["surf_c"].append(AMB + corner_value(res["surface_top"], dx_mm, *r))
        out["surf_m"].append(AMB + float(res["surface_top"][m].mean()))
        out["lay_c"].append(AMB + corner_value(layer, dx_mm, *r))
        out["lay_m"].append(AMB + float(layer[m].mean()))
        out["max"].append(AMB + float(res["surface_top"][m].max()))
    out["bottom_mean"] = AMB + res["mean_wall"]
    return out


def problem(h=H_PAPER, k=K_PLATE, h_top=1e-6):
    """!
    @brief The plate as a Problem of the program (the mapping of study_muzychka_more_cases.py).
    @param h Bottom coefficient in W/m2K.
    @param k Plate conductivity in W/mK.
    @param h_top Top coefficient in W/m2K (1e-6: adiabatic, as in the paper).
    @return Problem.
    """
    p = Problem.new(W_MM, W_MM, layers=1, thickness_mm=1.0001 * T_MM, copper_um=T_MM * 1e3, ambient=AMB, h_top=h_top, h_bottom=h, h_side=None, materials=Materials(k_copper=k))
    p.add_full_copper(layers=None)
    for i, (c, pw) in enumerate(zip(CENTRES, POWERS)):
        p.add_heater(1, pw, rect=rect(c), name=f"S{i}")
    return p


def readout(res, cell_mm_nominal=None):
    """!
    @brief Centroid and mean of the layer temperature over each source, and the program's own heater rows.
    @param res A SteadyResult.
    @param cell_mm_nominal Unused, kept for the signature of the callers.
    @return dict with cen, mean (lists in degC).
    """
    t_map = np.asarray(res.T)[0]
    ny, nx = t_map.shape
    dxm = W_MM / nx
    xs = (np.arange(nx) + 0.5) * dxm
    cens, means = [], []
    for c in CENTRES:
        x0, y0, x1, y1 = rect(c)
        m = (xs[None, :] > x0) & (xs[None, :] < x1) & (xs[:, None] > y0) & (xs[:, None] < y1)
        means.append(float(t_map[m].mean()))
        cens.append(corner_value(t_map, dxm, *c))
    return {"cen": cens, "mean": means}


def run(model, cell_mm, h=H_PAPER, k=K_PLATE, h_top=1e-6, prob=None, **opt):
    """!
    @brief Run one model of the program on the plate.
    @param model Model key.
    @param cell_mm Cell in mm.
    @param h Bottom coefficient in W/m2K.
    @param k Plate conductivity in W/mK.
    @param h_top Top coefficient in W/m2K.
    @param prob A prepared Problem (overrides h, k, h_top) or None.
    @param opt Extra SolverOptions fields.
    @return tuple (readout dict or None, Simulation or None).
    """
    p = prob if prob is not None else problem(h, k, h_top)
    try:
        sim = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm, **opt))
    except Exception as exc:                                       # reported, never hidden
        print(f"  {model}@{cell_mm}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None, None
    r = readout(sim.results[model])
    return r, sim
