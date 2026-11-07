#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_estimator.py
@brief Questions 1 to 3: the attribution of the error (copper through-thickness, laminate discretisation, lateral spreading, face term), the decision errors of the program and the closed-form estimator E3 over the sweep.

@details Reads out/sweep.json (study_fast_wave_sweep.py) and prints the tables of the README: (A) attribution by ablation on the 20 Hz, 30 %, 10 W wave of a 10 mm part and
over frequency; (B) the decision of the program and of the program with the floor max(program, E3) against the reference, for powers of the part from 0.5 to 20 W and
the budget of 1 K; (C) the cost of E3. Run from the repository root after the sweep.
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import numpy as np                                                   # noqa: E402

import axisym_stack as A                                             # noqa: E402
import columns as Cn                                                 # noqa: E402
import impedance as I                                                # noqa: E402

OUT = os.path.join(HERE, "..", "out")
W, H = 60e-3, 40e-3


def attribution():
    """!
    @brief Ablation of the discretisation of the stack on the 1D column of a 10 mm part (2 layers, h 10), and 1D against 2D.
    @return Dict of printed tables.
    """
    st = A.Stack(layers=2)
    area = 1e-4
    a = A.part_radius(10e-3)
    res = {}
    f, duty = 20.0, 0.3
    ref2d = A.Reference(st, a, A.rectangle_radius(W, H), 10, 10)
    mx, mn = ref2d.square_wave(1 / f, duty, "center")
    res["ref2d_20Hz"] = (mx - mn) * 10.0
    ex = Cn.exact_column(st, area, 10, 10)
    mx, mn = ex.square_wave(1 / f, duty, "top")
    res["exact1d_20Hz"] = (mx - mn) * 10.0
    res["lumped1d_20Hz"] = (lambda r: (r[0] - r[1]) * 10.0)(Cn.lumped_column(st, area, 10, 10).square_wave(1 / f, duty, "top"))
    rows = []
    for n_cu in (1, 4):
        for n_gap in (1, 2, 4, 8, 16):
            m = Cn.exact_column(st, area, 10, 10, n_cu=n_cu, n_gap=n_gap)
            r = m.square_wave(1 / f, duty, "top")
            rows.append((n_cu, n_gap, 2 * n_gap, (r[0] - r[1]) * 10.0))
    res["graded"] = rows
    # Uniform sub-gaps (the laminate rule): one copper node per layer and n equal sub-gaps of the 1.53 mm gap, as the program with the laminate cut into nodes everywhere
    uni = []
    for n in (1, 2, 4, 8, 16, 64, 256):
        dz = np.concatenate([[st.t_cu], np.full(n, (st.thickness - 2 * st.t_cu) / n), [st.t_cu]])
        kz = np.concatenate([[st.k_cu], np.full(n, st.kz), [st.k_cu]])
        rc = np.concatenate([[st.rho_cp_cu], np.full(n, st.rho_cp_lam), [st.rho_cp_cu]])
        C, K = Cn._chain(dz, kz, rc, area, 10, 10)
        q = np.zeros(len(dz)); q[0] = 1
        m = Cn.Modal(C, K, q, {"top": q.copy()})
        r = m.square_wave(1 / f, duty, "top")
        uni.append((n, (r[0] - r[1]) * 10.0))
    res["uniform"] = uni
    # 1D against 2D over frequency and size
    cmp = []
    for side in (2.0, 5.0, 10.0):
        aa = A.part_radius(side * 1e-3)
        ref = A.Reference(st, aa, A.rectangle_radius(W, H), 10, 10)
        col = Cn.exact_column(st, (side * 1e-3) ** 2, 10, 10)
        lum = Cn.lumped_column(st, (side * 1e-3) ** 2, 10, 10)
        for fr in (0.1, 1, 10, 100, 1000):
            r2 = ref.square_wave(1 / fr, 0.3, "center")
            r1 = col.square_wave(1 / fr, 0.3, "top")
            rl = lum.square_wave(1 / fr, 0.3, "top")
            cmp.append((side, fr, r2[0] - r2[1], r1[0] - r1[1], rl[0] - rl[1]))
    res["one_vs_two_d"] = cmp
    return res


def decisions():
    """!
    @brief Decision errors of the program and of the floor max(program, E3) over the sweep (full copper).
    @return Dict of counts.
    """
    d = [r for r in json.load(open(os.path.join(OUT, "sweep.json"))) if not r["bare"]]
    cache = {}
    t0 = time.time()
    n_e3 = 0
    for r in d:
        key = (r["layers"], r["side"], r["h"], r["f"], r["duty"])
        st = A.Stack(layers=r["layers"])
        r["e3"] = I.square_swing(st, 1.0 / r["f"], r["duty"], A.part_radius(r["side"] * 1e-3), r["h"], r["h"])
        n_e3 += 1
    cost = (time.time() - t0) / n_e3
    json.dump(d, open(os.path.join(OUT, "sweep_e3.json"), "w"))
    out = {"cost_ms": cost * 1e3}
    powers = [0.5, 1, 2, 5, 10, 20]
    for name, key in (("program", lambda r: r["prog_decision"]), ("floor", lambda r: max(r["prog_decision"], r["e3"]))):
        wa = wr = tot = 0
        wa_f = {}
        worst = 0.0
        for r in d:
            for P in powers:
                tot += 1
                est, true = P * key(r), P * r["ref_center"]
                if est <= 1.0 < true:
                    wa += 1
                    wa_f[r["f"]] = wa_f.get(r["f"], 0) + 1
                    worst = max(worst, true)
                if true <= 1.0 < est:
                    wr += 1
        out[name] = {"total": tot, "wrong_average": wa, "wrong_resolve": wr, "worst_true_swing_when_averaged": worst, "by_f": wa_f}
    e = np.array([r["e3"] / r["ref_center"] for r in d])
    out["e3_ratio_percentiles"] = np.percentile(e, [0, 5, 50, 95, 100]).tolist()
    pr = np.array([r["prog_decision"] / r["ref_center"] for r in d if r["ref_center"] > 0.01])
    out["prog_ratio_percentiles"] = np.percentile(pr, [0, 5, 50, 95, 100]).tolist()
    return out


def main():
    """!
    @brief Print the tables.
    @return None.
    """
    a = attribution()
    print("== attribution (10 mm part, 2 layers, h 10, 20 Hz, 30 %, 10 W: swing in K) ==")
    for k in ("ref2d_20Hz", "exact1d_20Hz", "lumped1d_20Hz"):
        print(f"{k}: {a[k]:.3f}")
    print("graded laminate cells per side of the gap, copper cells per layer: swing")
    for n_cu, n_gap, tot, s in a["graded"]:
        print(f"  n_cu={n_cu} cells/gap={tot}: {s:.3f}")
    print("uniform sub-gaps of the gap, one copper node per layer:")
    for n, s in a["uniform"]:
        print(f"  {n}: {s:.3f}")
    print("1D against 2D (K/W, duty 0.3): side, f, 2D ref, 1D exact, 1D lumped")
    for row in a["one_vs_two_d"]:
        print("  %4.0f %7.1f %10.5f %10.5f %10.5f" % row)
    dd = decisions()
    print("== decisions ==")
    print(json.dumps(dd, indent=1))


if __name__ == "__main__":
    main()
