#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_transient.py
@brief The surface read-out in time: the parabola on a frame of the program's FVM network against an independent one-dimensional solution, for a power step and for square waves, on four boards.
@details The board is one-dimensional (the part covers the whole face of an insulated board), so the independent column solver (lib/column1d.py, imports nothing from the program) is exact. For every case:
         (1) step responses read at the Fourier numbers Fo = alpha t / t_layer^2 of the thick layer (0.003 to 10): the exact surface minus the exact layer mean, the program's node (column) error, the parabola
         read from the program's frame and its error against the exact surface, and the bound q t / 2k (q the source flux, which is the exact upper bound only when no heat has left the face);
         (2) square waves of 50 % duty with the period T from 0.1 to 1000 times t_layer^2/alpha: the peak surface of the last of six periods, exact and by the parabola.
         Usage: .venv/bin/python research/surface-readout-models/scripts/study_transient.py (about 1 min, under 0.3 GB).
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import transient as TR  # noqa: E402

POWER = 40.0                                                 # W over the whole 20 x 20 mm face (100 kW/m2); the results are linear in it
FO = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0)
STEPS = 400


def alpha_of(case):
    """!
    @brief Thermal diffusivity of the thick layer.
    @param case Entry of TR.CASES.
    @return m2/s.
    """
    return case[3] / case[4]


def step_rows(case):
    """!
    @brief Step response at the Fourier numbers FO.
    @param case Entry of TR.CASES.
    @return list of dicts.
    """
    t_l = case[2] * 1e-3
    a = alpha_of(case)
    fr = TR.Frames(TR.problem(case))
    rows = []
    for fo in FO:
        tau = fo * t_l * t_l / a
        dt = tau / STEPS
        ref = TR.reference(case, lambda s: 1.0, dt, STEPS, POWER)
        pr = fr.run(lambda s: POWER * 1.0, dt, STEPS)
        # the program drives its network with the part's watts of the one-cell share: scale to the same flux
        r_surf, r_mean = ref["surf"][-1], ref["mean"][0][-1]
        row = {"case": case[0], "Fo": fo, "tau": tau, "ref_surf": r_surf, "ref_mean": r_mean, "ref_off": r_surf - r_mean, "col_err": pr["col"][-1] - r_mean,
               "par_off": pr["d"][-1], "par_surf_err": pr["surf"][-1] - r_surf, "bound": pr["bound"][-1], "q_bot_over_q": pr["q_bot"][-1] / pr["q_top"][-1] if pr["q_top"][-1] else float("nan")}
        rows.append(row)
    return rows


def wave_rows(case, periods_in_tau=(0.1, 1.0, 10.0, 100.0, 1000.0)):
    """!
    @brief Square waves (50 % duty) of several periods, six periods, the last one read.
    @param case Entry of TR.CASES.
    @param periods_in_tau Periods in units of t_layer^2 / alpha.
    @return list of dicts.
    """
    t_l = case[2] * 1e-3
    a = alpha_of(case)
    fr = TR.Frames(TR.problem(case))
    rows = []
    for pt in periods_in_tau:
        T = pt * t_l * t_l / a
        steps = 6 * 400
        dt = 6 * T / steps
        sq = lambda s: 1.0 if (s % T) < T / 2.0 else 0.0                  # noqa: E731
        ref = TR.reference(case, sq, dt, steps, POWER)
        pr = fr.run(lambda s: POWER * sq(s), dt, steps)
        last = slice(5 * 400, steps + 1)
        rows.append({"case": case[0], "T_over_tau": pt, "T": T, "ref_peak_surf": float(ref["surf"][last].max()), "ref_peak_off": float((ref["surf"][last] - ref["mean"][0][last]).max()),
                     "par_peak_surf_err": float(pr["surf"][last].max() - ref["surf"][last].max()), "col_peak_err": float(pr["col"][last].max() - ref["mean"][0][last].max()),
                     "par_peak_off": float(pr["d"][last].max()), "bound_peak": float(pr["bound"][last].max())})
    return rows


def analytic_rows(case, fo_end=10.0, n_ref=20000):
    """!
    @brief The Analytic model's own transient frames read with rule F (the field and the uniform conductances), against the exact column solution at the same times.
    @param case Entry of TR.CASES.
    @param fo_end Fourier number of the last frame.
    @param n_ref Steps of the reference.
    @return list of dicts at the frames whose Fourier number is close to 0.1, 1 and 10.
    """
    from pcbthermal import analytic
    sys.path.insert(0, os.path.join(HERE, "..", "lib"))
    import rules
    t_l = case[2] * 1e-3
    a = alpha_of(case)
    t_end = fo_end * t_l * t_l / a
    prob = TR.problem(case)
    prob.heaters[0].power = POWER
    res = analytic.solve_transient(prob, t_end, n_out=40, cell_mm=10.0)
    dt = t_end / n_ref
    ref = TR.reference(case, lambda s: 1.0, dt, n_ref, POWER)
    cy, cx = res.frames.shape[2] // 2, res.frames.shape[3] // 2
    rows = []
    for target in (0.1, 1.0, 10.0):
        i = int(np.argmin(np.abs(res.times * a / (t_l * t_l) - target)))
        j = int(round(res.times[i] / dt))
        f = rules.field_rule(prob, res.frames[i], 10.0)
        rows.append({"case": case[0], "Fo": float(res.times[i] * a / (t_l * t_l)), "ref_off": float(ref["surf"][j] - ref["mean"][0][j]), "F_off": float(f["d_top"][cy, cx]),
                     "F_surf_err": float(f["top"][cy, cx] - 25.0 - ref["surf"][j]), "node_err": float(res.frames[i, 0, cy, cx] - 25.0 - ref["mean"][0][j])})
    return rows


def main():
    """!
    @brief Run the four cases, print the tables and write out/transient.json.
    """
    allrows = {"step": [], "wave": [], "analytic": []}
    for case in TR.CASES:
        print(f"\n=== {case[0]} (t {case[2]} mm, alpha {alpha_of(case):.2e} m2/s, t^2/alpha {(case[2] * 1e-3) ** 2 / alpha_of(case):.3g} s, h {case[5]}) ===")
        print("step: Fo | exact surf-mean (K) | parabola (K) | parabola/exact | surface error (K) | node error (K) | bound/exact | q_bot/q")
        for r in step_rows(case):
            allrows["step"].append(r)
            print(f"  {r['Fo']:6.3f} | {r['ref_off']:9.4f} | {r['par_off']:9.4f} | {r['par_off'] / r['ref_off'] if r['ref_off'] > 1e-12 else float('nan'):6.2f} | {r['par_surf_err']:+9.4f} | {r['col_err']:+9.4f} | "
                  f"{r['bound'] / r['ref_off'] if r['ref_off'] > 1e-12 else float('nan'):6.2f} | {r['q_bot_over_q']:6.2f}")
        print("square wave 50 %: T/(t^2/alpha) | exact peak surface (K) | exact peak surf-mean | parabola surface error (K) | node error (K) | bound peak")
        for r in wave_rows(case):
            allrows["wave"].append(r)
            print(f"  {r['T_over_tau']:8.1f} | {r['ref_peak_surf']:9.4f} | {r['ref_peak_off']:9.4f} | {r['par_peak_surf_err']:+9.4f} | {r['col_peak_err']:+9.4f} | {r['bound_peak']:9.4f}")
    print("\nAnalytic transient frames with rule F (power step): case | Fo | exact surf-mean | rule F | surface error | node error (K)")
    for case in TR.CASES[:3]:
        for r in analytic_rows(case):
            allrows["analytic"].append(r)
            print(f"  {r['case'][:30]:30s} {r['Fo']:7.3f} | {r['ref_off']:8.4f} | {r['F_off']:8.4f} | {r['F_surf_err']:+8.4f} | {r['node_err']:+8.4f}")
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    with open(os.path.join(HERE, "..", "out", "transient.json"), "w") as f:
        json.dump(allrows, f, indent=1, default=float)


if __name__ == "__main__":
    main()
