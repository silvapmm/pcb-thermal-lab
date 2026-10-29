#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file program_patch.py
@brief Run the program's finned metal block with the channel effect, on a copy kept in memory (the program is not edited): `blocks.exposed_h` is replaced for the duration of a run.

@details The program gives the exposed face of a finned block the coefficient `h_face x fin_ratio(h_face) + h_extra`. Here that function is replaced by the channel
         coefficient of `channel.exposed_h_channel` (composite correlation of Bar-Cohen and Rohsenow by default), which depends on the temperature of the block, so the run is
         repeated with the block excess temperature of the previous run until it changes by less than 0.05 K (two to eight solves in the studies, counting the first uniform one). Everything else (the board, the block plate,
         the contact, the side walls) is the program's code unchanged; FVM, FDM, Lumped, Analytic and the 3D solid all reach `blocks.exposed_h` through `blocks.extra_layers`.
"""

import contextlib
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pcbthermal import blocks, fvm, solid3d          # noqa: E402

import channel as ch                                  # noqa: E402

MODELS = {"fvm": fvm, "solid3d": solid3d}


@contextlib.contextmanager
def channel_effect(theta_b, length, nu_fun=ch.nu_bcr, h_extra_scale=1.0):
    """!
    @brief Context in which `blocks.exposed_h` gives the exposed-face coefficient with the channel effect.
    @param theta_b Excess temperature of the block over the ambient air in K (the base of the fins).
    @param length Length of the channels in the flow direction in m.
    @param nu_fun Composite correlation Nu_b(Ra_b).
    @param h_extra_scale Unused factor (kept at 1) so that a caller can scale the extra coefficient while testing.
    @return Context manager (yields a dict that receives the last values: h_ch, eta, ra_b, theta_wall, h_exp).
    """
    original = blocks.exposed_h
    last = {}

    def patched(s, h_face):
        """!
        @brief Replacement of `blocks.exposed_h`: channel coefficient per unit of base area plus the extra coefficient.
        @param s A Heatsink (block).
        @param h_face Coefficient of the board face (unused for a finned block; a plain plate keeps the program's value).
        @return W/m2K.
        """
        if not s.has_fins():
            return original(s, h_face)
        r = ch.exposed_h_channel(theta_b, s.fin_pitch - s.fin_thickness, s.fin_thickness, s.fin_height, length, s.k, last.get("ambient", 20.0), nu_fun)
        last.update(r)
        return r["h_exp"] + s.h_extra * h_extra_scale

    blocks.exposed_h = patched
    try:
        yield last
    finally:
        blocks.exposed_h = original


@contextlib.contextmanager
def phi_effect(theta_b, length):
    """!
    @brief Context in which `blocks.exposed_h` scales the coefficient of the fins by the channel fraction phi(Ra_b) and keeps the rest of the program's fin model.
    @details h_fin = phi h_face (both faces of the fins and the free base between them), h_exp = h_fin x fin_ratio(h_fin) + h_extra; phi comes from `channel.phi` at the
             Rayleigh number of the channel at the block temperature. This is the form proposed in INTEGRATION.md because it keeps the coefficient the user typed or the program computed
             (radiation included) where the channel is open, and never gives more than the program gives today.
    @param theta_b Excess temperature of the block over the ambient air in K.
    @param length Channel length in m.
    @return Context manager (yields a dict that receives phi and the ambient).
    """
    original = blocks.exposed_h
    last = {}

    def patched(s, h_face):
        """!
        @brief Replacement of `blocks.exposed_h` with the channel fraction.
        @param s A Heatsink (block).
        @param h_face Coefficient of the board face in W/m2K.
        @return W/m2K.
        """
        if not s.has_fins():
            return original(s, h_face)
        ra = ch.ra_channel(theta_b, s.fin_pitch - s.fin_thickness, length, last.get("ambient", 20.0))
        f = ch.phi(ra)
        last["phi"], last["ra_b"] = f, ra
        h_fin = f * h_face
        return h_fin * blocks.fin_ratio(h_fin, s) + s.h_extra

    blocks.exposed_h = patched
    try:
        yield last
    finally:
        blocks.exposed_h = original


def solve_phi(problem, length, cell_mm=1.0, max_pass=8, tol=0.05):
    """!
    @brief The same problem with the scaled coefficient (phi form), repeated until the block temperature settles (FVM).
    @param problem Problem with a finned block.
    @param length Channel length in m.
    @param cell_mm Cell size in mm.
    @param max_pass Maximum number of solves.
    @param tol Tolerance of the block excess temperature in K.
    @return Dict with rise, block_excess, passes, phi, ra_b.
    """
    theta = solve_program(problem, "fvm", cell_mm)["block_excess"]
    for k in range(max_pass):
        with phi_effect(theta, length) as last:
            last["ambient"] = float(problem.board.ambient)
            r = fvm.solve_steady(problem, cell_mm=cell_mm)
        new = block_excess(r)
        done = abs(new - theta) < tol
        theta = new
        if done:
            break
    return {"rise": r.delta_t, "block_excess": new, "passes": k + 1, "phi": last["phi"], "ra_b": last["ra_b"]}


def block_excess(result):
    """!
    @brief Mean excess temperature of the block over the ambient air from a steady result.
    @param result SteadyResult with `arrays["block_T"]` and `arrays["block_cov"]`.
    @return Mean excess in K, weighted by the covered area.
    """
    bt, cov = np.asarray(result.arrays["block_T"])[0], np.asarray(result.arrays["block_cov"])[0]
    w = cov > 0
    return float(np.sum((bt[w] - result.ambient) * cov[w]) / np.sum(cov[w]))


def solve_program(problem, model="fvm", cell_mm=1.0):
    """!
    @brief The program as it is: uniform coefficient on the fins.
    @param problem Problem with a finned block.
    @param model "fvm" or "solid3d".
    @param cell_mm Cell size in mm.
    @return Dict with rise (K, hottest point), block_excess (K), result.
    """
    r = MODELS[model].solve_steady(problem, cell_mm=cell_mm)
    return {"rise": r.delta_t, "block_excess": block_excess(r), "result": r}


def effective_pitch(s, h_face, h_target):
    """!
    @brief Fin pitch that makes the program's uniform-coefficient fin model give a target exposed coefficient (used for the 3D solid, which has its own copy of the fin ratio
           that `blocks.exposed_h` does not reach).
    @details `h_face x ratio(h_face, p) = h_target` with ratio = (1 - t/p) + 2 Hc eta / p decreasing with p from a large value to 1; the side walls of the plate keep
             h_face + h_extra, as in the program, so only the exposed face changes. Needs h_target > h_face (otherwise the fins cannot be made worse than a plate).
    @param s A finned Heatsink.
    @param h_face Face coefficient in W/m2K.
    @param h_target Exposed coefficient wanted, per unit of base area, in W/m2K.
    @return Pitch in m.
    @throws ValueError If the target is not above the plain plate.
    """
    from scipy.optimize import brentq
    if h_target <= h_face * 1.0001:
        raise ValueError("the target coefficient is not above the plain plate; the effective-pitch emulation does not apply")
    t = s.fin_thickness
    hc = s.fin_height + 0.5 * t
    m = np.sqrt(2.0 * h_face / (s.k * t))
    eta = np.tanh(m * hc) / (m * hc)

    def f(p):
        """!
        @brief Exposed coefficient minus target for a pitch.
        @param p Pitch in m.
        @return W/m2K.
        """
        return h_face * ((1.0 - t / p) + 2.0 * hc * eta / p) - h_target
    return brentq(f, t * 1.0000001, 1e3)


def solve_channel(problem, length, model="fvm", cell_mm=1.0, nu_fun=ch.nu_bcr, max_pass=8, tol=0.05):
    """!
    @brief The same problem with the channel coefficient on the exposed face of the block (repeated until the block temperature settles).
    @details The FVM (and FDM, Lumped, Analytic) reach `blocks.exposed_h` and are patched in memory; the 3D solid has its own copy of the fin ratio, so for it the pitch of the
             fins is replaced on a copy of the problem by the one that gives the same exposed coefficient (`effective_pitch`).
    @param problem Problem with a finned block.
    @param length Length of the channels in the flow direction in m.
    @param model "fvm" or "solid3d".
    @param cell_mm Cell size in mm.
    @param nu_fun Composite correlation.
    @param max_pass Maximum number of solves.
    @param tol Tolerance of the block excess temperature in K.
    @return Dict with rise, block_excess, passes, h_exp, h_ch, eta, ra_b.
    """
    theta = None
    for k in range(max_pass):
        if theta is None:
            theta = solve_program(problem, model, cell_mm)["block_excess"]          # the first guess is the block temperature of the uniform model
        if model == "solid3d":
            import copy
            q = copy.deepcopy(problem)
            s = next(x for x in q.heatsinks if x.has_fins())
            h_face = q.board.h_bottom if (s.layer != 0 and q.board.layers > 1) else q.board.h_top
            last = ch.exposed_h_channel(theta, s.fin_pitch - s.fin_thickness, s.fin_thickness, s.fin_height, length, s.k, float(problem.board.ambient), nu_fun)
            # The 3D solid adds h_extra itself (h_face x ratio + h_extra), so the target of the pitch is the finned-face part alone; passing h_exp + h_extra here
            # counted the extra coefficient twice (found by the review; no effect on the studies, whose blocks have h_extra = 0)
            s.fin_pitch = effective_pitch(s, h_face, last["h_exp"])
            r = MODELS[model].solve_steady(q, cell_mm=cell_mm)
        else:
            with channel_effect(theta, length, nu_fun) as last:
                last["ambient"] = float(problem.board.ambient)
                r = MODELS[model].solve_steady(problem, cell_mm=cell_mm)
        new = block_excess(r)
        if abs(new - theta) < tol:
            theta = new
            break
        theta = new
    return {"rise": r.delta_t, "block_excess": new, "passes": k + 1, **{key: last[key] for key in ("h_exp", "h_ch", "eta", "ra_b") if key in last}}
