#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file plates.py
@brief The plates of the study (case 2 of Muzychka and others, five thick plates, a two-layer board with a thick top copper, with and without a via) as Problems of the program and as the independent 3D solution.
@details Every plate is 50 x 50 mm, one square source centred on the top face, the top face adiabatic outside the source, the sides insulated, a film h under the bottom face. The independent
         reference is tests/helpers/layered3d.py (imports nothing from pcbthermal), 0.5 mm in the plane, 8 sub-slabs through every thick metal layer, 4 through the laminate; the surface is its extrapolated
         top face, the column read-out the thickness-weighted mean of the top copper layer, both taken as the MAXIMUM over the cells of the source (the program's part rows read the maximum under the part).
         All temperatures here are in degC with the ambient at 25.
"""

import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
for p in (ROOT, os.path.join(ROOT, "tests", "helpers")):
    if p not in sys.path:
        sys.path.insert(0, p)
import layered3d as L3  # noqa: E402
from pcbthermal import Problem  # noqa: E402
from pcbthermal.model import Dielectric, Materials  # noqa: E402

AMB = 25.0
W_MM = 50.0
K_CU = 385.0
K_LAM = 0.3
T_LAM_MM = 1.0
T_BOT_UM = 35.0

# name, kind, thickness of the thick layer in mm, its conductivity, source side in mm, power in W, bottom film in W/m2K, via
PLATES = [
    ("case 2 (10 mm k150, a 10, h 400)", "one", 10.0, 150.0, 10.0, 25.0, 400.0, False),
    ("1 mm Cu, a 2, h 10", "one", 1.0, K_CU, 2.0, 1.0, 10.0, False),
    ("3 mm Cu, a 5, h 100", "one", 3.0, K_CU, 5.0, 10.0, 100.0, False),
    ("10 mm Al, a 10, h 1000", "one", 10.0, 200.0, 10.0, 100.0, 1000.0, False),
    ("10 mm Cu, a 10, h 400", "one", 10.0, K_CU, 10.0, 40.0, 400.0, False),
    ("5 mm Al, a 2, h 400", "one", 5.0, 200.0, 2.0, 2.0, 400.0, False),
    ("2 mm Cu + 1 mm FR-4, a 4, h 50", "two", 2.0, K_CU, 4.0, 5.0, 50.0, False),
    ("2 mm Cu + 1 mm FR-4, a 4, h 50, via", "two", 2.0, K_CU, 4.0, 5.0, 50.0, True),
]
VIA_DRILL_MM = 0.6


def rect_mm(a):
    """!
    @brief The square source of side a centred on the plate.
    @param a Side in mm.
    @return Tuple (x0, y0, x1, y1) in mm.
    """
    c = W_MM / 2.0
    return (c - a / 2.0, c - a / 2.0, c + a / 2.0, c + a / 2.0)


def problem(spec):
    """!
    @brief The plate as a Problem of the program.
    @param spec One entry of PLATES.
    @return Problem with one heater named S on the top copper.
    """
    name, kind, t, k, a, P, h, via = spec
    if kind == "one":
        # One layer of thickness t and conductivity k with a 1e-4 t laminate (the mapping of research/muzychka-case2-analytic/lib/case2.py)
        p = Problem.new(W_MM, W_MM, layers=1, thickness_mm=1.0001 * t, copper_um=t * 1e3, ambient=AMB, h_top=1e-6, h_bottom=h, h_side=None, materials=Materials(k_copper=k))
    else:
        p = Problem.new(W_MM, W_MM, layers=2, thickness_mm=t + T_LAM_MM + T_BOT_UM * 1e-3, copper_um=T_BOT_UM, ambient=AMB, h_top=1e-6, h_bottom=h, h_side=None,
                        materials=Materials(k_copper=k, k_fr4_through=K_LAM, k_fr4_inplane=K_LAM))
        p.board.copper_thickness = [t * 1e-3, T_BOT_UM * 1e-6]
        p.board.dielectrics = [Dielectric(thickness=T_LAM_MM * 1e-3, name="FR-4", k_through=K_LAM, k_inplane=K_LAM, rho=1850.0, cp=1100.0)]
    p.add_full_copper(layers=None)
    p.add_heater(1, P, rect=rect_mm(a), name="S")
    if via:
        c = W_MM / 2.0
        p.add_via(c, c, diameter=VIA_DRILL_MM)
    return p


def reference(spec, dx_mm=0.5, n_sub=8, n_lam=4):
    """!
    @brief The independent 3D solution of the plate.
    @param spec One entry of PLATES.
    @param dx_mm Plan cell in mm.
    @param n_sub Sub-slabs through each thick metal layer.
    @param n_lam Sub-slabs through the laminate.
    @return dict with surf (the hottest surface cell of the source, degC), col (the hottest cell of the top copper layer mean, degC), bottom (mean of the bottom face of the stack, degC), and q (the source flux in W/m2).
    """
    name, kind, t, k, a, P, h, via = spec
    n = int(round(W_MM / dx_mm))
    if kind == "one":
        slabs = [(t * 1e-3, k, n_sub)]
    else:
        kz = np.full((n, n), K_LAM)
        if via:
            # The barrel is a copper area much smaller than a cell: the cell of the via carries the same k_z A (the barrel copper in parallel with the laminate), isotropic in the cell
            prob = problem(spec)
            a_via = prob.vias[0].thermal_area(prob.board.via_plating, k)
            a_cell = (dx_mm * 1e-3) ** 2
            i = n // 2
            kz[i - 1:i + 1, i - 1:i + 1] = K_LAM + (k - K_LAM) * a_via / (4.0 * a_cell)       # a 2 x 2 block of cells around the centre
        slabs = [(t * 1e-3, k, n_sub), (T_LAM_MM * 1e-3, kz, n_lam), (T_BOT_UM * 1e-6, k, 2)]
    r = L3.solve(dx_mm * 1e-3, n, n, slabs, tuple(v * 1e-3 for v in rect_mm(a)), P, 0.0, h)
    dz = np.array(r["dz"])
    nt = n_sub
    w = dz[:nt] / dz[:nt].sum()
    col_map = np.tensordot(w, r["T"][:nt], axes=(0, 0))
    m = r["mask_source"]
    return {"surf": AMB + float(r["surface_top"][m].max()), "col": AMB + float(col_map[m].max()), "bottom": AMB + float(r["mean_wall"]), "q": P / (a * 1e-3) ** 2}
