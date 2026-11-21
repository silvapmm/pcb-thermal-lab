#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_exact_modal.py
@brief Review check of `fix/transient-default-stepping`: the power-step stepping (old and new defaults, the pieces alone, splits 2 to 16) and `fvm.step_responses` against the EXACT
       solution of the same network by its eigenmodes, and the Richardson reference of `study_default_stepping.py` against it.
@details The network `C dx/dt + K x = q` (x the rise, x(0) = 0) is symmetrised, `A = C^{-1/2} K C^{-1/2}` (dense `eigh`), and `x(t) = C^{-1/2} V diag((1 - e^{-lambda t}) / lambda)
         V^T C^{-1/2} q`, exact in time. The nodes with no capacity (unused laminate nodes and cells off an outline, pinned) are checked to be decoupled from the others and to carry
         no source, and stay at zero. Dense, so only boards up to a few thousand unknowns (the example board at 4 mm); the example and reference boards at 2 mm are compared with the
         Richardson reference at 128/256 and 256/512 substeps (`--large`, about 4 minutes). Prints, per board and run, the error of the hottest-cell rise in percent: first frame,
         worst frame, the largest after a third of the time to 63 %, the largest step back of the peak (as % of the end rise) and the largest positive error with its time.
         Run from the repository root: `.venv/bin/python releases/2.9.0/transient-stepping/scripts/check_exact_modal.py [--large]`.
"""

import os
import sys

import numpy as np
from scipy.linalg import eigh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "research", "transient-reference-boards", "lib"))
from pcbthermal import fvm  # noqa: E402
from pcbthermal.fvm import Network, transient_from_network  # noqa: E402
from pcbthermal.model import load_problem  # noqa: E402
import study_default_stepping as study  # noqa: E402

## Settings: label, theta, first-stage split, Rannacher start
SETTINGS = [("Euler, 1 step (old)", 1.0, 1, False), ("Euler, quarter steps", 1.0, 4, False), ("CN, no start", 0.5, 1, False), ("CN + start", 0.5, 1, True),
            ("CN + start, split 2", 0.5, 2, True), ("CN + start, split 4 (new)", 0.5, 4, True), ("CN + start, split 8", 0.5, 8, True), ("CN + start, split 16", 0.5, 16, True)]


def modal(net, loads):
    """!
    @brief Exact response of a network to constant loads switched on at t = 0, by its eigenmodes.
    @param net fvm.Network (K, C).
    @param loads numpy.ndarray (unknowns, k) of loads in W.
    @return Tuple (function t -> (unknowns, k) rise in K, largest eigenvalue in 1/s).
    @throws AssertionError If a node without capacity is coupled to one with capacity or carries a load.
    """
    c0 = net.C.ravel()
    dyn = c0 > 0
    kc = net.K.tocsr()
    assert kc[~dyn][:, dyn].nnz == 0 and not np.any(loads[~dyn])        # the nodes without capacity are pinned and decoupled: they stay at zero
    s = 1.0 / np.sqrt(c0[dyn])
    a = (s[:, None] * kc[dyn][:, dyn].toarray()) * s[None, :]
    lam, v = eigh(0.5 * (a + a.T))
    b = v.T @ (s[:, None] * loads[dyn])

    def at(t):
        """!
        @brief Rise at time t.
        @param t Time in s.
        @return numpy.ndarray (unknowns, k) in K.
        """
        out = np.zeros((c0.size, loads.shape[1]))
        out[dyn] = s[:, None] * (v @ (b / lam[:, None] * (-np.expm1(-lam * t))[:, None]))
        return out

    return at, float(lam.max())


def hottest(net, x, nb):
    """!
    @brief Hottest rise over the board layers of a stack of states.
    @param net fvm.Network.
    @param x numpy.ndarray (times, unknowns) in K.
    @param nb Board layers kept in the frames.
    @return numpy.ndarray (times,) in K.
    """
    n = x.shape[0]
    return x.reshape(n, net.nl, net.ny, net.nx)[:, :nb].reshape(n, -1).max(axis=1)


def stepping(name, prob, cell, runs, exact):
    """!
    @brief Every setting of SETTINGS at every run of a board against the exact (or the converged Richardson) reference; prints one line per setting.
    @param name Board name.
    @param prob pcbthermal.Problem.
    @param cell Cell in mm.
    @param runs list of (label, t_end s or None for five estimated time constants, frames).
    @param exact True for the modal reference, False for Richardson at 256/512 substeps (checked against 128/256).
    @return None.
    """
    b = prob.board
    net = Network(prob, max(int(round(b.width * 1e3 / cell)), 2), max(int(round(b.height * 1e3 / cell)), 2))
    tau = fvm.estimate_time_constant(prob)
    at = modal(net, net.Q.reshape(-1, 1))[0] if exact else None
    print(f"== {name}: {net.K.shape[0]} unknowns, estimated time constant {tau:.1f} s", flush=True)
    for label, t_end, n_out in runs:
        t_end = 5 * tau if t_end is None else t_end
        times = transient_from_network(net, b.ambient, t_end, n_out, theta_scheme=1.0, first_stage_split=1).times
        nb = transient_from_network(net, b.ambient, times[1], 1, theta_scheme=1.0, first_stage_split=1).frames.shape[1]
        rich = hottest(net, study.reference_in_time(net, times), nb)[1:]
        if exact:
            ref = hottest(net, np.array([at(t)[:, 0] for t in times]), nb)[1:]
            note = f"Richardson 128/256 against exact: {100 * np.max(np.abs(rich / ref - 1)):.4f} %"
        else:
            ref = hottest(net, study.reference_in_time(net, times, m=256), nb)[1:]
            note = f"Richardson 128/256 against 256/512: {100 * np.max(np.abs(rich / ref - 1)):.4f} %"
        ts = times[1:]
        late = ts > ts[np.argmax(ref >= 0.632 * ref[-1])] / 3.0
        print(f"  {label}: {n_out} frames, {t_end:.1f} s; {note}")
        for slabel, theta, split, start in SETTINGS:
            tr = transient_from_network(net, b.ambient, t_end, n_out, theta_scheme=theta, first_stage_split=split, rannacher=start)
            got = (tr.frames - b.ambient).reshape(len(tr.times), -1).max(axis=1)[1:]
            rel = 100.0 * (got / ref - 1.0)
            w, p = int(np.argmax(np.abs(rel))), int(np.argmax(rel))
            back = 100.0 * min(np.diff(np.concatenate([[0.0], got])).min(), 0.0) / got[-1]
            print(f"    {slabel:26s} first {rel[0]:+7.2f} | worst {rel[w]:+7.2f} at {ts[w]:7.3g} s | late {np.max(np.abs(rel[late])):5.2f} | step back {back:+.4f} | "
                  f"highest {rel[p]:+.2f} at {ts[p]:.3g} s | above steady {got.max() + b.ambient - tr.steady_t_max:+.4f} K", flush=True)


def step_responses(name, prob, cell):
    """!
    @brief `fvm.step_responses_from_network` (Crank-Nicolson and implicit Euler on its own grid) against the exact modal responses of every heater.
    @param name Board name.
    @param prob pcbthermal.Problem with heaters.
    @param cell Cell in mm.
    @return None.
    """
    b = prob.board
    net = Network(prob, max(int(round(b.width * 1e3 / cell)), 2), max(int(round(b.height * 1e3 / cell)), 2))
    at, lam_max = modal(net, net.Qw_matrix.toarray())
    for theta in (0.5, 1.0):
        times, z, rth = fvm.step_responses_from_network(net, theta_scheme=theta)
        ex = np.array([at(t).max(axis=0) for t in times]).T
        rel = 100.0 * (z / ex - 1.0)
        big = ex >= 0.01 * rth[:, None]
        back = 100.0 * (np.diff(z, axis=1).min(axis=1) / rth).min()
        print(f"  step responses {name}, theta {theta}: first step {times[0]:.3g} s, lambda_max dt0 {lam_max * times[0]:.3g}; first sample {np.abs(rel[:, 0]).max():.3f} %; "
              f"worst where Z >= 1 % of Rth {np.abs(rel[big]).max():.3f} %; least step {back:+.5f} % of Rth", flush=True)


def main():
    """!
    @brief Run the checks.
    @return None.
    """
    import refboards
    std = [("Animation tab", None, 60), ("command line", 600.0, 40), ("20 frames", None, 20)]
    example = load_problem(os.path.join(ROOT, "examples", "example_board.pcbt.json"))
    for nm in ("two2", "disc"):
        stepping(nm, refboards.program_problem(nm), 2.0, std, True)
    stepping("plate, held edges", study.plate_problem(), 2.5, [("Animation tab", 32.0, 60), ("command line", 600.0, 40), ("20 frames, 92 s", 92.0, 20)], True)
    stepping("example board 4 mm", example, 4.0, std, True)
    step_responses("example board 4 mm", example, 4.0)
    step_responses("profile board 4 mm", load_problem(os.path.join(ROOT, "examples", "profile_board.pcbt.json")), 4.0)
    for nm in ("two2", "disc"):
        step_responses(nm, refboards.program_problem(nm), 2.0)
    step_responses("plate", study.plate_problem(), 2.5)
    if "--large" in sys.argv:
        stepping("example board 2 mm", example, 2.0, std, False)
        stepping("reference board 2 mm", load_problem(os.path.join(ROOT, "examples", "reference_board.pcbt.json")), 2.0, std, False)


if __name__ == "__main__":
    main()
