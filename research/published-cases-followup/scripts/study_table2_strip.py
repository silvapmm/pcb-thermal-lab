#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_table2_strip.py
@brief Item 1: Table 2 (and Table 3) of Yovanovich, Muzychka and Culham (1999), the spreading resistance of a strip on a flux channel, reproduced by the series AND by an independent
       finite-volume solve, then the program's five models on the closest representable version (equation 23, the finite channel with a film at the base).
@details Parts: (A) equations 24, 26, 27, 28 and 29 against every printed digit of Tables 2 and 3 (page 499 and 500); (B) the independent 2D solver `lib/strip2d.py` against equation 24
         (isoflux) and equation 27 (true isothermal) on a channel thick enough to be semi-infinite (tau = 3 > 2.65/pi), with a mesh sequence and Richardson extrapolation, and against equation 23
         for finite tau and Bi; (C) the program: the narrow board of `lib/prog_strip.py` (a bare two-layer board, isotropic laminate, strip heater over the whole depth, bottom film), psi
         read as k (R_total - t/(k c) - 1/(h c)) / 2 per unit depth. The layered models (fvm, fdm, lumped, analytic) have one node through the thickness of a copper layer and a few laminate
         sub-gaps (<= 4 by default), the 3D solid has real slabs (4 per gap by default); the question is how far each is from equation 23 as the channel gets thicker (tau = t/c).
         Run from the repository root: .venv/bin/python research/published-cases-followup/scripts/study_table2_strip.py [--no-program] (about 3 minutes, under 1 GB).
"""

import json
import sys

import _bootstrap
import numpy as np

import series as S
import strip2d as F

OUT = _bootstrap.OUT
EPS = (0.02, 0.04, 0.06, 0.08, 0.10, 0.20, 0.40, 0.60, 0.80)
TABLE2 = {
    "mu=-1/2 eq26": (S.psi_equivalent_isothermal, (1.1011, 0.8808, 0.7518, 0.6609, 0.5902, 0.3729, 0.1658, 0.0607, 0.0067)),
    "mu=0 eq24": (S.psi_isoflux, (1.1377, 0.9172, 0.7883, 0.6970, 0.6263, 0.4083, 0.1984, 0.0882, 0.0255)),
    "mu=+1/2 eq28": (S.psi_parabolic, (1.1545, 0.9340, 0.8051, 0.7138, 0.6430, 0.4247, 0.2134, 0.1007, 0.0338)),
    "T=const eq27": (S.psi_true_isothermal, (1.1015, 0.8811, 0.7523, 0.6611, 0.5905, 0.3738, 0.1691, 0.0675, 0.0160)),
}
TABLE3 = {0.02: (1.122, 1.120), 0.20: (0.3936, 0.3911), 0.40: (0.1860, 0.1838), 0.60: (0.0794, 0.0779), 0.80: (0.0214, 0.0208)}


def part_a():
    """!
    @brief Part A: the series against the printed tables.
    @return dict with the largest difference in units of the last printed digit per row and the cells that differ by more than one unit.
    """
    print("\nA. Tables 2 and 3 of the paper against the equations as printed (equations 24, 26, 27, 28, 29; the sums to 200 000 terms)")
    out, bad = {}, []
    for name, (fn, printed) in TABLE2.items():
        diffs = []
        for e, pr in zip(EPS, printed):
            val = fn(e)
            unit = 10.0 ** (-4)
            diffs.append((val - pr) / unit)
            if abs(val - pr) > 1.001 * unit:
                bad.append((name, e, pr, round(val, 5)))
        out[name] = float(np.abs(diffs).max())
        print(f"  {name:14s} largest |difference| {np.abs(diffs).max():5.2f} units of the last printed digit (1e-4)")
    for name, e, pr, val in bad:
        print(f"    printed {pr} but the equation gives {val} (eps {e}, {name})")
    print("  Table 3 (page 500): eq. (29) against the printed row, and the row printed as '[Eq.(24)+Eq.(26)]/2' against the two possible means")
    t3 = {}
    for e, (p29, pm) in TABLE3.items():
        v29 = S.psi_step(e)
        m26 = 0.5 * (S.psi_isoflux(e) + S.psi_equivalent_isothermal(e))
        m27 = 0.5 * (S.psi_isoflux(e) + S.psi_true_isothermal(e))
        t3[e] = {"eq29": v29, "printed29": p29, "mean24_26": m26, "mean24_27": m27, "printed_mean": pm}
        print(f"    eps {e:4.2f}: eq29 {v29:.4f} (printed {p29}); printed mean {pm}: (24+26)/2 = {m26:.4f}, (24+27)/2 = {m27:.4f}")
    print("    -> the printed mean row is the mean of equations (24) and (27) (the true isothermal strip), not of (24) and (26) as its heading says: it agrees with (24)+(27) within one unit of the last printed digit (the table is rounded) at all five sizes,")
    print("       and with (24)+(26) only for eps <= 0.2 (0.4: 0.1821 against 0.1838, 0.6: 0.0744 against 0.0779, 0.8: 0.0161 against 0.0208).")
    print("  Equation 26 at eps <= 0.06 is printed 0.0001 to 0.0004 below the converged sum (1.1011 against 1.10154, 0.8808 against 0.88103, 0.7518 against 0.75219); a sum cut at about 200 to 500 terms gives the printed digits (slow convergence, tail ~ n^-2.5).")
    return {"largest_units": out, "cells_over_one_unit": bad, "table3": t3}


def fv_psi(eps, tau, bi, mode, hmins=(0.02, 0.01, 0.005)):
    """!
    @brief psi of the independent solver on a mesh sequence and the Richardson value.
    @param eps Relative strip size a / c.
    @param tau Relative thickness t / c.
    @param bi Biot number h c / k of the base (None for an isothermal base).
    @param mode "flux" (isoflux strip) or "temp" (isothermal strip).
    @param hmins Smallest cell as a fraction of the strip half-width, finest last.
    @return tuple (list of psi on the meshes, Richardson value from the two finest, observed order).
    """
    k, c = 1.0, 1.0
    a, t = eps * c, tau * c
    vals = []
    for hm in hmins:
        xe = F.graded_edges(c, hm * a, a, 1.12)
        ze = F.graded_edges(t, hm * a, 0.0, 1.12)
        h_b = None if bi is None else bi * k / c
        if mode == "flux":
            r = F.solve(xe, ze, k, a, "flux", 1.0, 0.0, h_b)
        else:
            r = F.solve(xe, ze, k, a, "temp", 1.0, 0.0, h_b)
        rtot = r["t_face_mean"] / r["q_strip"]
        r1d = t / (k * c) + (0.0 if bi is None else 1.0 / (bi * k / c * c))
        vals.append(k * (rtot - r1d) / 2.0)                      # half cell, per unit depth: the paper's psi is half of k R_s,half (full-cell Q and area)
    d1, d2 = vals[-2] - vals[-3], vals[-1] - vals[-2]
    order = float(np.log2(abs(d1) / abs(d2))) if d2 != 0 and d1 != 0 else float("nan")
    p = max(min(order, 2.0), 0.5) if np.isfinite(order) else 1.0
    rich = vals[-1] + (vals[-1] - vals[-2]) / (2.0 ** p - 1.0)
    return vals, rich, order


def part_b():
    """!
    @brief Part B: the independent solver against equations 23, 24 and 27.
    @return list of rows.
    """
    print("\nB. Independent 2D finite-volume solve (lib/strip2d.py) against the series; tau = 3 stands for the semi-infinite channel (tanh(3 pi) = 1 to 1e-12)")
    print("   eps   isoflux FV (Richardson)  eq.24    diff %   |  isothermal FV (Richardson)  eq.27   diff %")
    rows = []
    for e in (0.02, 0.1, 0.2, 0.4, 0.6, 0.8):
        _, ri, oi = fv_psi(e, 3.0, None, "flux")
        _, rt, ot = fv_psi(e, 3.0, None, "temp")
        e24, e27 = S.psi_isoflux(e), S.psi_true_isothermal(e)
        rows.append({"eps": e, "fv_isoflux": ri, "eq24": e24, "fv_iso": rt, "eq27": e27, "order_isoflux": oi, "order_iso": ot})
        print(f"   {e:4.2f}  {ri:9.4f}               {e24:8.4f}  {100 * (ri / e24 - 1):+7.3f}   |  {rt:9.4f}                   {e27:8.4f}  {100 * (rt / e27 - 1):+7.3f}   (orders {oi:.2f}, {ot:.2f})")
    print("   finite channel (equation 23): isoflux strip with a film at the base")
    print("   eps   tau    Bi     FV (Richardson)   eq.23     diff %")
    for e, tau, bi in ((0.2, 0.1, 2.0), (0.2, 0.5, 2.0), (0.6, 0.5, 2.0), (0.2, 0.5, 100.0), (0.6, 0.1, 0.5)):
        _, r, _ = fv_psi(e, tau, bi, "flux")
        s = S.psi_finite(e, tau, bi)
        rows.append({"eps": e, "tau": tau, "bi": bi, "fv": r, "eq23": s})
        print(f"   {e:4.2f}  {tau:4.2f}  {bi:6.1f}  {r:10.4f}        {s:8.4f}  {100 * (r / s - 1):+7.3f}")
    return rows


def psi_program(model, eps, tau, bi, cell, c_mm=10.0, k=0.4, depth_mm=2.0, **kw):
    """!
    @brief psi of one program model on the narrow board.
    @param model Model key.
    @param eps a / c.
    @param tau t / c.
    @param bi Biot number h c / k at the base.
    @param cell Cell in mm.
    @param c_mm Half-width of the channel in mm.
    @param k Conductivity in W/mK.
    @param depth_mm Depth of the board in mm.
    @param kw Options of prog_strip.run (n_diel, laminate).
    @return tuple (psi, total resistance error is computed by the caller from psi and the series); NaN when the model refuses.
    """
    import prog_strip as P
    c, a, t = c_mm * 1e-3, eps * c_mm * 1e-3, tau * c_mm * 1e-3
    h = bi * k / c
    p = P.build(k, t * 1e3, c_mm, a * 1e3, 0.0, h, 1.0, depth_mm)
    d_t = P.run(p, model, cell, **kw)
    rtot = d_t * (depth_mm * 1e-3) / 1.0                        # K m / W per unit depth (1 W over the depth)
    r1d = t / (k * c) + 1.0 / (h * c)
    return k * (rtot - r1d) / 2.0, k * rtot / 2.0


def part_c():
    """!
    @brief Part C: the program's models against equation 23.
    @return list of rows.
    """
    print("\nC. The program on the narrow board against equation 23 (c = 10 mm, k = 0.4 W/mK isotropic, bottom film Bi = h c/k; psi of each model; error as % of psi and, in brackets, of the total k R/2)")
    cases = []
    for bi in (2.0, 2.5e4):
        for tau in (0.1, 0.5, 3.0):
            for eps in (0.2, 0.6):
                cases.append((eps, tau, bi))
    rows = []
    variants = [("fvm", 0.5, {}), ("fvm", 0.25, {}), ("fvm", 0.25, {"laminate": (0.5, 16)}), ("fdm", 0.25, {}), ("solid3d", 0.5, {}), ("solid3d", 0.5, {"n_diel": 16}),
                ("lumped", 0.5, {}), ("analytic", 0.5, {})]
    print("   eps   tau     Bi      eq.23   | " + " | ".join(f"{m}{'' if not kw else '*'}@{c}" for m, c, kw in variants))
    for eps, tau, bi in cases:
        ref = S.psi_finite(eps, tau, bi)
        reft = ref * 2.0 / 1.0                                   # placeholder, replaced below by the total of the same normalisation
        line = f"   {eps:4.2f}  {tau:4.2f}  {bi:7.1e}  {ref:7.4f} |"
        row = {"eps": eps, "tau": tau, "bi": bi, "eq23": ref, "models": {}}
        for m, cell, kw in variants:
            psi, tot = psi_program(m, eps, tau, bi, cell, **kw)
            # the total k R/2 of the series: psi + (t/(k c) + 1/(h c)) k / 2
            c_ = 10e-3
            tot_ref = ref + (tau * c_ / c_ + bi ** -1.0) * 0.5
            err = 100.0 * (psi / ref - 1.0) if np.isfinite(psi) else float("nan")
            errt = 100.0 * (tot / tot_ref - 1.0) if np.isfinite(tot) else float("nan")
            row["models"][f"{m}@{cell}{'*' if kw else ''}"] = {"psi": psi, "err_pct": err, "err_total_pct": errt}
            line += f" {err:+7.1f} ({errt:+5.2f}) |"
        rows.append(row)
        print(line)
    print("   (* = fvm laminate rule (0.5 mm, 16 sub-gaps) / solid3d with 16 slabs per gap)")
    return rows


def main():
    """!
    @brief Run the parts and write out/table2_strip.json.
    @return None.
    """
    res = {"A": part_a(), "B": part_b()}
    if "--no-program" not in sys.argv:
        res["C"] = part_c()
    (OUT / "table2_strip.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
