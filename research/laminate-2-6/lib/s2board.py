#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file s2board.py
@brief The thick-laminate cases of research/paper-case-studies (a source S x S on a W x W board, two layers, base film h) run by the program with a given laminate rule, and their references.
@details References: equation 50 of Muzychka, Yovanovich and Culham (2004) on the bare board (`closed_form`, through the library of paper-case-studies), and the extrapolated 3D numbers of
         paper-case-studies README 16.4 for S = 2 mm, h = 1e3 (REF_EXTRAP, copied with their source: bare 389.12 / 419.08, pad 316.37 / 347.39 K/W at 1.6 / 3.2 mm; the first of them was re-run
         here: 389.117). The quantity is R' = mean rise of the part at the face per watt minus the film term of the base, K/W.
"""

import time

import numpy as np

import study_thick_laminate as S2

REF_EXTRAP = {(2.0, 1.6, False): 389.12, (2.0, 1.6, True): 316.37, (2.0, 3.2, False): 419.08, (2.0, 3.2, True): 347.39}    # (S mm, t mm, pad) at W = 20 mm, h = 1e3, FR-4 0.9 / 0.3


def case(S, t, W=20.0, h=1.0e3, kxy=0.9, kz=0.3):
    """!
    @brief One case dict as the paper-case-studies library wants it.
    @param S Source side in mm.
    @param t Board thickness in mm.
    @param W Board side in mm.
    @param h Base film in W/m2K.
    @param kxy In-plane conductivity of the FR-4.
    @param kz Through conductivity of the FR-4.
    @return dict.
    """
    return {"S": S, "W": W, "t": t, "kxy": kxy, "kz": kz, "h": h}


def reference(c, pad):
    """!
    @brief Reference R' in K/W: the extrapolated 3D number when it is on record, else equation 50 for the bare board (None under a pad).
    @param c A case.
    @param pad True for the pad board.
    @return Tuple (value or None, source text).
    """
    key = (c["S"], c["t"], pad)
    if c["W"] == 20.0 and c["h"] == 1.0e3 and c["kxy"] == 0.9 and key in REF_EXTRAP:
        return REF_EXTRAP[key], "3D extrapolated (paper-case-studies 16.4)"
    if not pad:
        return S2.closed_form(c)[2], "equation 50"
    return None, "none"


def problem_of(c, pad):
    """!
    @brief The Problem of a case (what study_thick_laminate.run_program builds).
    @param c A case.
    @param pad True for the copper pad under the source on layer 1.
    @return Problem.
    """
    from pcbthermal import Problem
    from pcbthermal.model import Materials
    s, w = c["S"], c["W"]
    p = Problem.new(w, w, layers=2, thickness_mm=c["t"], copper_um=S2.T_CU * 1e6, ambient=0.0, h_top=0.0, h_bottom=c["h"], h_side=0.0,
                    materials=Materials(k_copper=385.0, k_fr4_through=c["kz"], k_fr4_inplane=c["kxy"]))
    x0, x1 = (w - s) / 2.0, (w + s) / 2.0
    if pad:
        p.add_zone(1, rect=(x0, x0, x1, x1))
    p.add_heater(1, 4.0, rect=(x0, x0, x1, x1), name="U")
    return p


def run(c, pad, cell_mm, model="fvm", s_max=0.4, n_max=4, local=None):
    """!
    @brief Run a case and return R' with the unknown count and the wall time.
    @param c A case.
    @param pad True for the pad board.
    @param cell_mm Cell in mm.
    @param model "fvm" or "fdm".
    @param s_max laminate_s_max_mm.
    @param n_max laminate_n_max.
    @param local None for the program's rule, or a dict of options of local_laminate.make_plan_gaps for the local rule.
    @return Tuple (R' in K/W, unknowns, seconds).
    """
    from pcbthermal import SolverOptions, analysis, laminate, simulate
    import local_laminate as LL
    p = problem_of(c, pad)
    opts = SolverOptions(models=(model,), cell_mm=cell_mm, laminate_s_max_mm=s_max, laminate_n_max=n_max)
    from pcbthermal import fvm
    t0 = time.time()
    if local is None:
        with laminate.using(s_max * 1e-3, n_max):
            nunk = fvm.unknowns(p, cell_mm)[0]
        res = simulate(p, opts).results[model]
    else:
        with LL.local_rule(p, **local):
            with laminate.using(s_max * 1e-3, n_max):
                nunk = fvm.unknowns(p, cell_mm)[0]
            res = simulate(p, opts).results[model]
    dt = time.time() - t0
    mean_src = analysis.heater_stats(res, p)[0]["t_mean"] - p.board.ambient
    r = mean_src / 4.0 - 1.0 / (c["h"] * (c["W"] * 1e-3) ** 2)
    return r, int(nunk), dt
