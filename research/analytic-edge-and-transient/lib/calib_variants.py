#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file calib_variants.py
@brief Copies of the calibration of the Analytic transient (analytic._calibrated_dynamics) with other rules, to measure them without touching the program.

@details The program calibrates ONE factor: on the smeared via conductance when the board has vias, otherwise on the smeared heatsink coefficient, so that the steady
         maximum of the smeared modal model equals that of the locally corrected steady solution. Variants (selected by `install(name)`, which replaces
         analytic._calibrated_dynamics at run time):

         * "program": the program's rule (for the check that the copy is the program).
         * "two": two factors, s_h on the heatsinks so that the smeared model extracts the heat the locally corrected solution sends into the heatsinks, and s_v on the vias
           so that the steady maximum equals the local one (alternating bisections, three rounds); without vias only s_h (extraction).
         * "two_max": two factors as "two", but with no vias the heatsink factor matches the steady maximum (as the program does).
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import analytic_v251 as analytic   # noqa: E402  (frozen v2.5.1 text: 2.6.0 replaced the one-factor calibration by the local modal system, so the variants are built on the old module)
from pcbthermal import analytic as _live   # noqa: E402
from pcbthermal.geometry import polygon_area   # noqa: E402

_ORIGINAL = analytic._calibrated_dynamics
_LIVE_STEP = _live.step_responses


def _smeared(problem, sh, n_terms, sv, shs):
    """!
    @brief Steady maximum and heatsink extraction of the smeared modal model with the two factors.
    @param problem A Problem.
    @param sh Dict from analytic._effective_sheet.
    @param n_terms Modes per direction.
    @param sv Factor on the smeared via conductance.
    @param shs Factor on the smeared heatsink coefficient.
    @return Tuple (maximum rise in K, heat into the heatsinks in W).
    """
    A = analytic._modal_matrix(problem, sh, n_terms, sv, shs)
    mx = analytic._smeared_steady_max(problem, sh, A, n_terms)
    bx, by = analytic._bases(sh, n_terms)
    q = sum(h.power * s for h, s in zip(problem.heaters, analytic._heater_unit_sources(problem, bx, by)))
    a = np.linalg.solve(A, q[..., None])[..., 0]
    W, H, L = sh["W"], sh["H"], sh["L"]
    ext = 0.0
    for s in problem.heatsinks:
        if s.is_block():
            continue
        ext += shs * s.h_extra * polygon_area(s.polygon) * analytic._plan_mean(bx, by, a[:, :, s.layer])
    return mx, ext


def _bisect(f, target, lo=-6.0, hi=math.log(1.0e4), rising=True):
    """!
    @brief Bisection on the logarithm of a factor.
    @param f Function of the factor.
    @param target Value to reach.
    @param lo Lower log bound.
    @param hi Upper log bound.
    @param rising True if f increases with the factor.
    @return float The factor.
    """
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        above = f(math.exp(mid)) > target
        if above == rising:
            hi = mid
        else:
            lo = mid
        if hi - lo < 0.005:
            break
    return math.exp(0.5 * (lo + hi))


def calibrated(variant):
    """!
    @brief Build a replacement for analytic._calibrated_dynamics.
    @param variant "two" or "two_max".
    @return Function (problem, cell_mm, n_terms) -> dict.
    """
    def fn(problem, cell_mm, n_terms):
        """!
        @brief Modal dynamics with the two-factor calibration.
        @param problem A Problem.
        @param cell_mm Cell in mm.
        @param n_terms Modes per direction.
        @return Dict from analytic._modal_dynamics with the keys of the program's calibration.
        """
        d = analytic._modal_dynamics(problem, cell_mm, n_terms)
        d["local_max"], d["scaled"] = None, None
        if not (problem.vias or problem.heatsinks) or problem.total_power() <= 0:
            return d
        local_res = analytic.solve_steady(problem, cell_mm=cell_mm, n_terms=n_terms)
        local = local_res.t_max - problem.board.ambient
        ext_local = local_res.power_out.get("heatsinks", 0.0)
        sh = analytic._effective_sheet(problem, cell_mm)
        sv, shs = 1.0, 1.0
        has_v, has_s = bool(problem.vias), bool(problem.heatsinks)
        if has_s and has_v:
            for _ in range(3):
                shs = _bisect(lambda x: _smeared(problem, sh, n_terms, sv, x)[1], ext_local)
                sv = _bisect(lambda x: _smeared(problem, sh, n_terms, x, shs)[0], local, rising=False)
        elif has_s:
            if variant == "two_max":
                shs = _bisect(lambda x: _smeared(problem, sh, n_terms, 1.0, x)[0], local, rising=False)
            else:
                shs = _bisect(lambda x: _smeared(problem, sh, n_terms, 1.0, x)[1], ext_local)
        else:
            if _smeared(problem, sh, n_terms, 1.0, 1.0)[0] > local:
                sv = _bisect(lambda x: _smeared(problem, sh, n_terms, x, 1.0)[0], local, rising=False)
        d = analytic._modal_dynamics(problem, cell_mm, n_terms, sv, shs)
        d["local_max"] = local + problem.board.ambient
        d["scaled"] = "vias" if has_v and not has_s else ("heatsinks" if has_s and not has_v else "both")
        d["heatsink_scale"], d["via_scale"] = shs, sv
        return d
    return fn


def install(name):
    """!
    @brief Choose the Analytic step response that the program entry point runs.
    @param name "program" (the v2.5.1 one-factor calibration, the program of the study), "two" or "two_max" (variants built on it) or "current" (the live 2.6.0 program,
           which has the local modal system instead of a calibration).
    @return None.
    """
    if name == "current":
        _live.step_responses = _LIVE_STEP
        return
    analytic._calibrated_dynamics = _ORIGINAL if name == "program" else calibrated(name)
    _live.step_responses = analytic.step_responses
