#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file prog_strip.py
@brief The program's five models on the strip cases of the papers: a narrow board (the two-dimensional cell of the paper made three-dimensional by a depth of a few cells with insulated sides).
@details The cell of Lemczyk and others and of Yovanovich and others is a slab of half-width L1 with a strip of width w at the corner of its top face (the ends are symmetry planes). The program
         runs it as a board L1 x depth with the heater on x in [0, w] over the whole depth and insulated edges, a bare two-layer board (nothing drawn: the slab is the laminate between two copper
         nodes of 35 um, the geometry of research/paper-case-studies S2), isotropic laminate of conductivity k, a film on the bottom (h_bottom) and optionally on the top (h_top). A strip held at a
         temperature is approximated by a copper strip of very high conductivity under the heater (`iso_k`). The result is the mean temperature of the footprint as the program reports it
         (`analysis.heater_stats`, face term included), per watt, as a thermal resistance per unit depth (K m / W).
"""

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.append(str(REPO))


def build(k, t_mm, l1_mm, w_mm, h_top, h_bottom, power, depth_mm, copper_strip=False, k_strip=385.0, cu_um=35.0, layer=1):
    """!
    @brief The strip cell as a program Problem.
    @param k Isotropic laminate conductivity in W/mK (through and in plane).
    @param t_mm Total thickness of the slab in mm (copper layers included, as in paper-case-studies).
    @param l1_mm Half-width of the cell (length of the board) in mm.
    @param w_mm Width of the strip (the heater) in mm.
    @param h_top Film on the top face in W/m2K (applied under the heater too, as the program does).
    @param h_bottom Film on the bottom face in W/m2K.
    @param power Power of the heater in W.
    @param depth_mm Depth of the board in mm (the third dimension of the narrow board).
    @param copper_strip True: a copper zone under the heater (the isothermal trace of Lemczyk and others), False: bare laminate (the isoflux strip).
    @param k_strip Conductivity of the copper of the strip in W/mK (385 or very high to approach an isothermal strip).
    @param cu_um Thickness of each copper layer in micrometres.
    @param layer Layer of the heater and of the copper strip, 1 = top, 2 = bottom.
    @return pcbthermal.model.Problem.
    """
    from pcbthermal import Problem
    from pcbthermal.model import Materials
    p = Problem.new(l1_mm, depth_mm, layers=2, thickness_mm=t_mm, copper_um=cu_um, ambient=0.0, h_top=h_top, h_bottom=h_bottom, h_side=0.0,
                    materials=Materials(k_copper=k_strip, k_fr4_through=k, k_fr4_inplane=k))
    if copper_strip:
        p.add_zone(layer, rect=(0.0, 0.0, w_mm, depth_mm))
    p.add_heater(layer, power, rect=(0.0, 0.0, w_mm, depth_mm), name="U")
    return p


def run(p, model, cell_mm, n_diel=None, laminate=None):
    """!
    @brief Mean temperature rise of the heater footprint in one model.
    @param p Problem of build().
    @param model "fvm", "fdm", "solid3d", "lumped" or "analytic".
    @param cell_mm Cell in mm.
    @param n_diel Slabs of every gap of the 3D solid (None: the program's default 4).
    @param laminate Optional (s_max_mm, n_max) of the laminate rule for the FVM and FDM.
    @return float Rise in K, NaN when the model refuses the board (the reason is printed to stderr).
    """
    from pcbthermal import SolverOptions, simulate, analysis, solid3d
    try:
        if model == "solid3d" and n_diel is not None:
            res = solid3d.solve_steady(p, cell_mm=cell_mm, n_diel=n_diel)
        else:
            kw = {}
            if laminate is not None:
                kw = {"laminate_s_max_mm": laminate[0], "laminate_n_max": laminate[1]}
            res = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm, **kw)).results[model]
        return float(analysis.heater_stats(res, p)[0]["t_mean"] - p.board.ambient)
    except Exception as exc:                                     # a model that refuses a board is reported, not hidden
        print(f"  [{model}] {type(exc).__name__}: {str(exc)[:110]}", file=sys.stderr)
        return float("nan")
