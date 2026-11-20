#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_default_stepping.py
@brief Question: how large is the time-step error of the FVM/FDM power-step run at the program's defaults, and what do a first stage in quarter steps and Crank-Nicolson with the
       Rannacher start (`fix/transient-default-stepping`) change, against the same network without its time-step error?
@details The reference is the network of the run integrated with implicit Euler at 128 and 256 substeps between consecutive frames, Richardson-extrapolated (the
         `reference_in_time` of `research/transient-published-case`; it reproduces the 5.93 % against the exact series on the plate). Error = relative difference of the peak rise
         (hottest cell) of the run from that reference at every frame. Settings: the old default (Euler, one step for the first frame), Euler with the first stage in quarter steps,
         Crank-Nicolson without a start, Crank-Nicolson with the start, and the new default (quarter steps + start). Boards: the example board, the reference board, the plate with
         held edges (`research/transient-published-case`), and the two-layer and disc boards of `research/transient-reference-boards`. Frames: the Animation tab (60 frames, 5
         estimated time constants), the command line (40 frames, 600 s) and 20 frames. Prints the table and the run time of every setting.
         Run from the repository root: `.venv/bin/python releases/2.9.0/transient-stepping/scripts/study_default_stepping.py [--quick]`. SI units inside; the tables are in K and %.
"""

import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research", "transient-reference-boards", "lib"))
from pcbthermal import fvm  # noqa: E402
from pcbthermal.fvm import Network, transient_from_network  # noqa: E402
from pcbthermal.model import load_problem  # noqa: E402

## Settings: label, theta, first-stage split, Rannacher start
SETTINGS = [("Euler, 1 step (old default)", 1.0, 1, False),
            ("Euler, quarter steps", 1.0, 4, False),
            ("CN, no start", 0.5, 1, False),
            ("CN + start", 0.5, 1, True),
            ("CN + start + quarter steps (new default)", 0.5, 4, True)]


def reference_in_time(net, times, m=128):
    """!
    @brief The same network integrated with implicit Euler at m and 2m substeps between consecutive output times, Richardson-extrapolated.
    @param net fvm.Network (K, C, Q).
    @param times Output times in s, starting at 0.
    @param m Substeps per interval of the coarse run (count).
    @return numpy.ndarray (len(times), unknowns) rise above ambient in K.
    """
    import scipy.sparse as sp
    from scipy.sparse.linalg import splu
    kk, cc, q = net.K.tocsc(), net.C.ravel(), net.Q.ravel()

    def run(mm):
        x, out, lu, key = np.zeros(kk.shape[0]), [np.zeros(kk.shape[0])], None, None
        for a, b in zip(times[:-1], times[1:]):
            dt = (b - a) / mm
            if key != round(dt, 12):
                lu, key = splu((sp.diags(cc / dt) + kk).tocsc()), round(dt, 12)
            for _ in range(mm):
                x = lu.solve(cc / dt * x + q)
            out.append(x.copy())
        return np.array(out)

    return 2.0 * run(2 * m) - run(m)


def plate_problem():
    """!
    @brief The 0.1 m square copper-like plate of `research/transient-published-case` with a uniform 10 W heater and held edges (h 1e5 W/m2K), one 1 mm layer.
    @return pcbthermal.Problem.
    """
    from pcbthermal import Problem
    from pcbthermal.model import Materials
    mat = Materials(k_copper=35.0, rho_copper=7200.0, cp_copper=440.5)
    p = Problem.new(100.0, 100.0, layers=1, thickness_mm=1.0001, copper_um=1000.0, ambient=0.0, h_top=1e-6, h_bottom=1e-6, h_side=1e5, materials=mat)
    p.add_full_copper(layers=None)
    p.add_heater(1, 10.0, rect=(0.0, 0.0, 100.0, 100.0), name="U")
    return p


def boards(quick):
    """!
    @brief The boards of the study with the cell in mm.
    @param quick True for the two small boards only.
    @return list of (name, Problem, cell in mm).
    """
    import refboards
    out = []
    if not quick:
        out.append(("example board", load_problem(os.path.join(ROOT, "examples", "example_board.pcbt.json")), 2.0))
        out.append(("reference board", load_problem(os.path.join(ROOT, "examples", "reference_board.pcbt.json")), 2.0))
        out.append(("plate, held edges", plate_problem(), 2.5))
    out.append(("two-layer board (two2)", refboards.program_problem("two2"), 2.0))
    out.append(("disc board", refboards.program_problem("disc"), 2.0))
    return out


def measure(name, prob, cell, runs, results):
    """!
    @brief Run every setting at every (t_end, frames) of a board and print the error against the reference.
    @param name Board name.
    @param prob pcbthermal.Problem.
    @param cell Cell in mm.
    @param runs list of (label, t_end s or None for five estimated time constants, frames).
    @param results dict filled with (board, run, setting) -> (worst %, first frame %, worst after t63/3 %, end %, seconds).
    @return None.
    """
    b = prob.board
    net = Network(prob, max(int(round(b.width * 1e3 / cell)), 2), max(int(round(b.height * 1e3 / cell)), 2))
    tau = fvm.estimate_time_constant(prob)
    print(f"{name}: {net.K.shape[0]} unknowns, estimated time constant {tau:.1f} s")
    for rlabel, t_end, n_out in runs:
        t_end = 5 * tau if t_end is None else t_end
        tr0 = transient_from_network(net, b.ambient, t_end, n_out, theta_scheme=1.0, first_stage_split=1)
        ref = reference_in_time(net, tr0.times)
        nb = tr0.frames.shape[1]
        want = ref.reshape(len(tr0.times), net.nl, net.ny, net.nx)[:, :nb].reshape(len(tr0.times), -1).max(axis=1)[1:]
        ts = tr0.times[1:]
        t63 = ts[np.argmax(want >= 0.632 * want[-1])]
        late = ts > t63 / 3.0
        print(f"  {rlabel}: {n_out} frames, {t_end:.1f} s")
        for label, theta, split, ran in SETTINGS:
            t0 = time.perf_counter()
            tr = transient_from_network(net, b.ambient, t_end, n_out, theta_scheme=theta, first_stage_split=split, rannacher=ran)
            sec = time.perf_counter() - t0
            got = (tr.frames - b.ambient).reshape(len(tr.times), -1).max(axis=1)[1:]
            rel = 100.0 * (got / want - 1.0)
            w = int(np.argmax(np.abs(rel)))
            results[(name, rlabel, label)] = (rel[w], rel[0], float(np.max(np.abs(rel[late]))), rel[-1], sec)
            print(f"    {label:42s} worst {rel[w]:+7.2f} % at {ts[w]:8.3g} s | first {rel[0]:+7.2f} % | late max {np.max(np.abs(rel[late])):5.2f} % | end {rel[-1]:+6.2f} % | {sec:5.2f} s")


def ringing():
    """!
    @brief Ringing of the default stepping (Crank-Nicolson with the start and the quarter steps): the largest step back of the peak and its overshoot over the steady value, as % of
           the rise, for the small boards at 20, 40 and 60 frames and three run lengths (five estimated time constants, 600 s, 3000 s).
    @return None.
    """
    import refboards
    print("ringing of the default stepping (min step of the peak as % of the rise; overshoot over steady in K)")
    for name in ("two2", "disc", "simple4"):
        p = refboards.program_problem(name)
        tau = fvm.estimate_time_constant(p)
        for n in (20, 40, 60):
            row = []
            for te in (5 * tau, 600.0, 3000.0):
                tr = fvm.solve_transient(p, te, n, 2.0)
                d = np.diff(tr.t_max)
                row.append(f"{te:7.1f} s: {100 * min(d.min(), 0.0) / (tr.t_max[-1] - tr.t_max[0]):+.4f} % / {tr.t_max.max() - tr.steady_t_max:+.3f} K")
            print(f"  {name:8s} {n} frames: " + " | ".join(row))


def main():
    """!
    @brief Run the study.
    @return None.
    """
    quick = "--quick" in sys.argv
    ringing()
    res = {}
    for name, prob, cell in boards(quick):
        runs = [("Animation tab", None, 60), ("command line", 600.0, 40), ("20 frames", None, 20)]
        if name.startswith("plate"):
            runs[0] = ("Animation tab", 32.0, 60)
            runs.append(("20 frames, 92 s", 92.0, 20))
        measure(name, prob, cell, runs, res)
    return res


if __name__ == "__main__":
    main()
