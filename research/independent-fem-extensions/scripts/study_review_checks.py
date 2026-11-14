#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_checks.py
@brief The checks of the review of the results (README 9): where the -2.5 % of the 20 Hz swing of the disc board against the axisymmetric reference comes from (the plan
       mesh at the edge of the source), the checkerboard sheet under plan refinement, the step response of the study-2 plate read at the hottest node (the program's
       step responses read the hottest cell), and the program's rows of study 2 on another program tree (the Lumped part read-out of `fix/lumped-part-readout`).
@details Run from the repository root, one mode at a time (each under 2 GB):
         `research/independent-fem-edge/.venv-research/bin/python research/independent-fem-extensions/scripts/study_review_checks.py disc_edge` (about 5 minutes),
         `... checker` (seconds), `... plate_hot` (about 2 minutes), and with the program's interpreter
         `.venv/bin/python research/independent-fem-extensions/scripts/study_review_checks.py cluster_prog <repository root of the program to test>` (seconds).
         Nothing is cached; every number of README 9 is printed here.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "independent-fem-edge", "lib"))
sys.path.insert(0, os.path.join(ROOT, "research", "fast-wave-oscillation", "lib"))
sys.path.insert(0, HERE)
import numpy as np                                                       # noqa: E402


def disc_board(n_side, radii_out, inside=(), n_gap=24, ratio=1.3):
    """!
    @brief The disc board of `study_transient.disc_source_board` with chosen circle levels around the edge of the source.
    @param n_side Intervals per side of the inner square of the O-grid.
    @param radii_out Circle levels outside the source radius `a`, m (increasing, the last below the rim).
    @param inside Distances inside `a` of extra circle levels, m.
    @param n_gap Elements across a laminate gap.
    @param ratio Grading ratio of the gap elements.
    @return board.Board.
    """
    import axisym_stack as A
    import board as B
    import mesh2d
    a = A.part_radius(4e-3)
    radii = [a - d for d in sorted(inside, reverse=True)] + [a] + list(radii_out)
    plan = mesh2d.ogrid(0, 0, 0.7 * (a - max(inside, default=0.0)) / np.sqrt(2), radii, n_side, ("circle", 10e-3), n_inner=max(n_side // 3, 1))
    ang = np.linspace(0, 2 * np.pi, 721)[:-1]
    poly = np.column_stack([a * 1.0001 * np.cos(ang), a * 1.0001 * np.sin(ang)])          # the quads inside the source circle carry the source
    return B.Board(plan, 2, board_t=1.6e-3, k_xy=0.9, k_z=0.3, n_gap=n_gap, gap_ratio=ratio, n_cu=1, h_top=10.0, h_bottom=10.0, h_side=0.0, heaters=[(poly, 1.0)])


def graded(n, first):
    """!
    @brief Circle levels from the source radius to the 10 mm rim, the first ring `first` wide and the widths growing geometrically.
    @param n Number of rings.
    @param first Width of the first ring, m.
    @return list of radii, m (the last one is the rim).
    """
    import axisym_stack as A
    a = A.part_radius(4e-3)
    L = 10e-3 - a
    lo, hi = 1.0 + 1e-9, 3.0
    for _ in range(200):                                                 # bisection on the growth factor
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if first * (mid ** n - 1) / (mid - 1) < L else (lo, mid)
    r = 0.5 * (lo + hi)
    w = first * r ** np.arange(n)
    w *= L / w.sum()
    return list(a + np.cumsum(w))


def disc_edge():
    """!
    @brief The 20 Hz, 30 % swing and the step response of the disc board against `axisym_stack.Reference` for plan meshes that differ only around the edge of the source
           (n_gap 24, consistent mass, 0.25 ms steps), and the frequency-domain swing on two of them (time stepping and frequency domain must agree if the residual is spatial).
    @return None.
    """
    import axisym_stack as A
    import transient
    from study_transient import board_rho_c
    a = A.part_radius(4e-3)
    ref = A.Reference(A.Stack(layers=2), a, 10e-3, 10.0, 10.0)
    mx, mn = ref.square_wave(0.05, 0.3, "mean")
    sw_ref = mx - mn
    cases = [
        ("6 uniform rings", 8, list(a + (10e-3 - a) * np.arange(1, 7) / 6), (), False),
        ("6 rings, first 0.1 mm", 8, graded(6, 0.1e-3), (), False),
        ("12 rings, first 0.05 mm", 8, graded(12, 0.05e-3), (), True),
        ("18 rings, first 0.025 mm", 8, graded(18, 0.025e-3), (), False),
        ("levels at +-0.05 / 0.15 / 0.35 mm", 8, [a + 0.05e-3, a + 0.15e-3, a + 0.35e-3] + graded(8, 0.6e-3)[1:], (0.05e-3, 0.15e-3, 0.35e-3), False),
        ("levels at +-0.025 ... 0.55 mm", 8, [a + 0.025e-3, a + 0.075e-3, a + 0.15e-3, a + 0.3e-3, a + 0.55e-3] + graded(8, 0.9e-3)[1:],
         (0.025e-3, 0.075e-3, 0.15e-3, 0.3e-3, 0.55e-3), True),
        ("levels at +-0.05 / 0.15 / 0.35 mm, n_side 12", 12, [a + 0.05e-3, a + 0.15e-3, a + 0.35e-3] + graded(8, 0.6e-3)[1:], (0.05e-3, 0.15e-3, 0.35e-3), False),
    ]
    print(f"axisym reference swing {sw_ref:.5f} K/W", flush=True)
    for name, n_side, ro, ins, freq in cases:
        t0 = time.time()
        m, info = disc_board(n_side, ro, ins).build()
        tr = transient.Transient(m, board_rho_c(m), consistent=True)
        w = tr.reduce_weights(transient.face_weights(m, np.vstack(info["heater_faces"])))
        run = tr.march(tr.steady(0.3), transient.square_segments(0.05, 0.3, 60, 140, 8), transient.square_power(0.05, 0.3), {"m": w})
        s, t = run["series"]["m"], run["t"]
        sw = s[t > 7 * 0.05].max() - s[t > 7 * 0.05].min()
        st = tr.step_response({"m": w}, 1.5, dt0=1e-4, per_level=6, factor=2.0)
        e = [100 * (float(np.interp(tt, st["t"], st["series"]["m"])) / float(ref.step(np.array([tt]), "mean")[0]) - 1) for tt in (0.01, 0.1, 1.0)]
        line = f"{name}: {tr.n} unknowns, swing {sw:.5f} ({100 * (sw / sw_ref - 1):+.2f} %); step at 0.01 / 0.1 / 1 s {e[0]:+.2f} / {e[1]:+.2f} / {e[2]:+.2f} %"
        if freq:
            fr = np.logspace(-0.5, 4.5, 41)
            _, Tb = transient.periodic_wave(fr, transient.harmonic_response(tr, w, fr), float(w @ tr.steady()), 0.05, 0.3)
            line += f"; frequency domain {Tb.max() - Tb.min():.5f} ({100 * ((Tb.max() - Tb.min()) / sw_ref - 1):+.2f} %)"
        print(line + f" ({time.time() - t0:.0f} s)", flush=True)


def checker():
    """!
    @brief The checkerboard sheet (8 x 8 squares of 1 mm, copper 385 and laminate 0.9 W/mK, 35 um) with 4 to 64 elements per square: S_eff / sqrt(S1 S2).
    @return None.
    """
    import sheets
    k1, k2, t, a, N = 385.0, 0.9, 35e-6, 1e-3, 8
    for m in (4, 8, 16, 32, 64):
        xn = np.linspace(0, N * a, m * N + 1)
        g = sheets.conductance(xn, xn, lambda c: ((np.floor(c[:, 0] / a).astype(int) + np.floor(c[:, 1] / a).astype(int)) % 2 == 0), k1, k2, t)
        print(f"checkerboard N={N}, {m} elements per square: S_eff / sqrt(S1 S2) = {g / (np.sqrt(k1 * k2) * t):.4f}", flush=True)


def plate_hot():
    """!
    @brief Step response of the study-2 plate at 0.2 mm (variant A, 6 mm part), read at the footprint mean and at the hottest top node of the footprint.
    @return None.
    """
    import cluster
    import transient
    from study_transient import t_at
    st, hd = cluster.build("A", 6.0, 0.2)
    m, info = st.build()
    tr = transient.Transient(m, info["rho_c"], consistent=True)
    qs = np.nonzero(hd["inside"](info["c"]))[0]
    faces = st.level_nodes(info, 0, qs)
    w = tr.reduce_weights(transient.face_weights(m, faces))
    Ts = tr.full(tr.steady())
    nodes = np.unique(faces)
    wh = np.zeros(m.nodes.shape[0])
    wh[nodes[np.nanargmax(Ts[nodes])]] = 1.0
    wh = tr.reduce_weights(wh)
    r = tr.step_response({"mean": w, "hot": wh}, 2500.0, dt0=0.05, per_level=6, factor=2.0)
    for label, key, wt in (("footprint mean", "mean", w), ("hottest node", "hot", wh)):
        ss = float(wt @ tr.steady())
        print(f"{label}: steady {ss:.5f} K/W, t63 {t_at(r['t'], r['series'][key], (1 - np.exp(-1)) * ss):.3f} s", flush=True)


def cluster_prog(root):
    """!
    @brief The program's rows of study 2 (6 and 4 mm parts, full copper) from the program tree at `root`, against the cached finite-element variant A at 0.1 mm (`out/s2.json`).
    @param root Repository root whose `pcbthermal` is imported.
    @return None.
    """
    import logging
    sys.path.insert(0, root)
    import pcbthermal
    from pcbthermal import SolverOptions, analysis, simulate
    import study_cluster as sc
    logging.disable(logging.WARNING)
    print("program:", pcbthermal.__file__, flush=True)
    fe = json.load(open(os.path.join(HERE, "..", "out", "s2.json")))
    for tab in (6, 4):
        A = fe[f"A|{float(tab)}|0.1|full"]
        E = fe[f"A|{float(tab)}|0.1|full|novia"]["part_mean"] - A["part_mean"]
        for model, cell in (("lumped", 0.5), ("analytic", 0.5), ("fvm", 0.25), ("fdm", 0.25)):
            o = {}
            for nov in (False, True):
                p = sc.program_problem(tab, False, nov)
                r = simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model]
                row = analysis.heater_stats(r, p)[0]
                o[nov] = (row["t_mean"] - 25.0, row["t_max"] - 25.0)
            print(f"part {tab} mm, {model} at {cell} mm: mean {100 * (o[False][0] / A['part_mean'] - 1):+.2f} %, hottest {100 * (o[False][1] / A['part_max'] - 1):+.2f} %, "
                  f"via effect (mean) {100 * ((o[True][0] - o[False][0]) / E - 1):+.1f} %", flush=True)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "disc_edge":
        disc_edge()
    elif mode == "checker":
        checker()
    elif mode == "plate_hot":
        plate_hot()
    elif mode == "cluster_prog":
        cluster_prog(sys.argv[2] if len(sys.argv) > 2 else ROOT)
