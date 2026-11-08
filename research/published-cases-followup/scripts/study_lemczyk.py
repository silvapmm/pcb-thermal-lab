#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_lemczyk.py
@brief Item 3: Lemczyk, Mack, Culham and Yovanovich (1992), "PCB trace thermal analysis and effective conductivity": Tables 1 to 4 reproduced with an independent solver, then the program's models on the
       closest representable cases (the trace cells (a), (c), (d) and the 3-layer board of Table 4).
@details Parts: (1) Table 1 (dimensional, 16 rows x 4 cases: Q_a to Q_d for T_c = 90 K, h = 10 W/m2K, L2 = 1 m) by `lib/strip2d.py`; (2) Tables 2 and 3 (36 rows x 4 cases of Psi = k L2 R) by the same solver,
         the power of ten of each printed entry inferred (the blocks of the table are headed by a scale and the layout mixes them: the decade is the one that brings the entry within a factor 3 of the solver);
         (3) Table 4 (3-layer board, layers FR-4 0.778 mm / Cu 36 um, k 386 / FR-4 0.778 mm, h = 10 W/m2K, L1 = 10 mm, L2 = 20 mm, 0.4 W in the full cell): the layered independent solver
         `layered3d` (ny = 1) with the paper's boundary conditions and with the program's (film also under the source), and the three single-medium conductivities of the paper (k_S, k_P, k_H);
         (4) the program: the trace cells of the homogeneous slab on the narrow board (a copper strip of very high conductivity under the heater stands for the isothermal trace) and the 3-layer board.
         Run from the repository root: .venv/bin/python research/published-cases-followup/scripts/study_lemczyk.py [--no-program] (about 4 minutes, under 1 GB).
"""

import json
import sys

import _bootstrap
import numpy as np

import lemczyk as L

OUT = _bootstrap.OUT


def decade(printed, value):
    """!
    @brief The power of ten that brings a printed mantissa closest (in the logarithm) to the computed value.
    @param printed Printed number.
    @param value Computed number.
    @return float printed * 10^n.
    """
    n = np.round(np.log10(value / printed))
    return printed * 10.0 ** n


def part1():
    """!
    @brief Table 1 against the independent solver.
    @return list of rows.
    """
    print("\n1. Table 1 (T_c = 90 K, h1 = h2 = 10 W/m2K, L2 = 1 m): Q in W, printed / independent solver; case (c) with h1 = 0 as the text says and with Bi1 = 0.001")
    print("   k    w    t    L1 |   Qa printed  solver |   Qb printed  solver |   Qc printed  h1=0   Bi1=.001 |   Qd printed  solver")
    rows = []
    for k, w, t, l1, qa, qb, qc, qd in L.TABLE1:
        args = (k, t * 1e-6, l1 * 1e-6, w * 1e-6, 10.0, 90.0)
        sa, sb, sd = (L.q_case(c, *args) for c in "abd")
        sc0 = L.q_case("c", *args)
        sc1 = L.q_case("c", *args, bi1=0.001)
        rows.append({"k": k, "w": w, "t": t, "L1": l1, "printed": [qa, qb, qc, qd], "solver_abd": [sa, sb, sd], "qc_h1_0": sc0, "qc_bi1_001": sc1})
        print(f"  {k:4.1f} {w:4d} {t:4d} {l1:5d} |  {qa:6.3f} {sa:7.4f} |  {qb:6.3f} {sb:7.4f} |  {qc:6.3f} {sc0:7.4f} {sc1:7.4f} |  {qd:6.3f} {sd:7.4f}")

    def worst(ix, key):
        return max(abs(r[key] / r["printed"][ix] - 1) * 100 for r in rows)
    print(f"   largest |difference| with the printed (three digits, so +-0.5 % of 0.1 W): Q_a {max(abs(r['solver_abd'][0] / r['printed'][0] - 1) for r in rows) * 100:.1f} %, "
          f"Q_b {max(abs(r['solver_abd'][1] / r['printed'][1] - 1) for r in rows) * 100:.1f} %, Q_d {max(abs(r['solver_abd'][2] / r['printed'][3] - 1) for r in rows) * 100:.1f} %, "
          f"Q_c with h1 = 0 {worst(2, 'qc_h1_0'):.0f} %, Q_c with Bi1 = 0.001 {worst(2, 'qc_bi1_001'):.1f} %")
    return rows


def part2():
    """!
    @brief Tables 2 and 3 against the independent solver.
    @return list of rows.
    """
    print("\n2. Tables 2 and 3: Psi = k L2 R of the four cases, independent solver / printed mantissa (the decade inferred), difference in %")
    print("   Bi2    t/L1  w/L1 |   (a)             (b)             (c) h1=0 | (c) Bi1=.001   |   (d)")
    rows = []
    diffs = {"a": [], "b": [], "c0": [], "c1": [], "d": []}
    for bi, tau, wl, pa, pb, pc, pd in L.TABLE23:
        vals = {"a": L.psi_case("a", bi, tau, wl), "b": L.psi_case("b", bi, tau, wl), "c0": L.psi_case("c", bi, tau, wl), "c1": L.psi_case("c", bi, tau, wl, bi1=0.001), "d": L.psi_case("d", bi, tau, wl)}
        pr = {"a": pa, "b": pb, "c0": pc, "c1": pc, "d": pd}
        d = {key: (vals[key] / decade(pr[key], vals[key]) - 1) * 100 for key in vals}
        for key in d:
            diffs[key].append(d[key])
        rows.append({"bi": bi, "tau": tau, "wl": wl, "solver": vals, "printed_mantissa": pr, "diff_pct": d})
        print(f"  {bi:6.3f} {tau:5.2f} {wl:4.1f} | {d['a']:+7.2f} %      {d['b']:+7.2f} %      {d['c0']:+8.2f} %  | {d['c1']:+7.2f} %    | {d['d']:+7.2f} %")
    print("   summary of the differences (solver against printed), over 36 rows:")
    for key, name in (("a", "(a)"), ("b", "(b)"), ("c0", "(c) h1 = 0"), ("c1", "(c) Bi1 = 0.001"), ("d", "(d)")):
        v = np.array(diffs[key])
        print(f"     {name:16s} mean {v.mean():+6.2f} %, mean |.| {np.abs(v).mean():5.2f} %, largest |.| {np.abs(v).max():6.2f} %, rows beyond 2 %: {int((np.abs(v) > 2).sum()):2d}, beyond 5 %: {int((np.abs(v) > 5).sum()):2d}")
    return rows


def _r(res, nw):
    """!
    @brief The two candidate readings of the R of Table 4 from a layered solve: the mean over the heated strip and the mean over the whole top face (the n = 0 term of the cosine series).
    @param res Result of layered3d.solve.
    @param nw Cells of the strip.
    @return tuple (R_strip, R_face) in K/W, the rise over 0.4 W of the full cell.
    """
    st = np.asarray(res["surface_top"]).ravel()
    return float(st[:nw].mean() / 0.4), float(st.mean() / 0.4)


def three_layer(wl, film_under, dx=0.1e-3, n_sub=8, slabs=None):
    """!
    @brief Table 4 case by the independent layered solver (2D: one cell across the depth).
    @param wl w / L1.
    @param film_under True: the film also acts under the source (the program); False: the paper's condition.
    @param dx Cell in the plane in m.
    @param n_sub Sub-slabs of every FR-4 layer.
    @param slabs Slabs from the top (default: the 3-layer board of the paper; a single (t, k, n) list for a homogeneous medium).
    @return tuple (R_strip, R_face): the rise over 0.4 W of the full cell, for the mean over the heated strip and for the mean over the whole top face, K/W.
    """
    import layered3d as L3
    l1 = 10e-3
    nx = int(round(l1 / dx))
    nw = max(int(round(wl * nx)), 1)
    slabs = slabs or [(0.778e-3, 0.4, n_sub), (36e-6, 386.0, 1), (0.778e-3, 0.4, n_sub)]
    p_half = 0.2 * dx / 20e-3                                    # the depth is one cell: 0.2 W of the half cell of depth L2 = 20 mm scaled to the slice (the rise is the same)
    res = L3.solve(dx, nx, 1, slabs, (0.0, 0.0, nw * dx, dx), p_half, 10.0, 10.0, film_under_source=film_under)
    return _r(res, nw)


def part3():
    """!
    @brief Table 4 (3-layer board) and the effective conductivities.
    @return list of rows.
    """
    t = np.array([0.778e-3, 36e-6, 0.778e-3])
    k = np.array([0.4, 386.0, 0.4])
    k_p = float((k * t).sum() / t.sum())
    k_s = float(t.sum() / (t / k).sum())
    k_h = 2.0 / (1.0 / k_p + 1.0 / k_s)
    print(f"\n3. Table 4, the 3-layer board (k_S {k_s:.3f}, k_P {k_p:.3f}, k_H {k_h:.3f} W/mK; printed 0.41, 9.12, 0.78): R in K/W of the full cell")
    print("   Two readings of the paper's R by the independent solver (paper's conditions: the top film acts only outside the strip): the mean over the strip, and the mean over the whole top face")
    print("   w/L1 | printed |  strip mean  diff  | face mean  diff | R_S printed solver(strip) solver(face) | R_P printed (strip) (face) | R_H printed (strip) (face) | film under strip")
    rows = []
    for wl, r, rs, rp, rh in L.TABLE4:
        ra, rf = three_layer(wl, False)
        rb = three_layer(wl, True)[0]
        ss, sp_, sh = (three_layer(wl, False, slabs=[(1.592e-3, kk, 16)]) for kk in (k_s, k_p, k_h))
        rows.append({"wl": wl, "printed": [r, rs, rp, rh], "strip": ra, "face": rf, "film_under_source": rb, "single_strip": [ss[0], sp_[0], sh[0]], "single_face": [ss[1], sp_[1], sh[1]]})
        print(f"  {wl:5.2f} | {r:7.1f} | {ra:8.1f} {100 * (ra / r - 1):+6.1f} % | {rf:8.1f} {100 * (rf / r - 1):+6.1f} % | {rs:7.1f} {ss[0]:7.1f} {ss[1]:7.1f} | {rp:7.1f} {sp_[0]:7.1f} {sp_[1]:7.1f} | {rh:7.1f} {sh[0]:7.1f} {sh[1]:7.1f} | {rb:7.1f}")
    print("   The paper's claim that k_H gives the resistance of the board to 2 %, by the two readings (R_H against the 3-layer R of the same reading), %:")
    print("   w/L1:  " + "  ".join(f"{r['wl']:5.2f}" for r in rows))
    print("   strip: " + "  ".join(f"{100 * (r['single_strip'][2] / r['strip'] - 1):+5.1f}" for r in rows))
    print("   face:  " + "  ".join(f"{100 * (r['single_face'][2] / r['face'] - 1):+5.1f}" for r in rows))
    return rows


def psi_program(case, model, bi, tau, wl, cell, l1_mm=20.0, k=0.4, depth_mm=2.0, **kw):
    """!
    @brief Psi of a trace case in one model of the program.
    @param case "a", "c" (h1 = 0) or "d".
    @param model Model key.
    @param bi Bi2 = h L1 / k.
    @param tau t / L1.
    @param wl w / L1.
    @param cell Cell in mm.
    @param l1_mm Cell half-width in mm.
    @param k Conductivity in W/mK.
    @param depth_mm Depth of the narrow board in mm.
    @param kw Options of prog_strip.run.
    @return float Psi = k D (T_c / P) with T_c the mean temperature of the trace footprint (the copper strip of k = 1e5 W/mK is isothermal to 1e-3).
    """
    import prog_strip as P
    l1, t = l1_mm * 1e-3, tau * l1_mm * 1e-3
    h = bi * k / l1
    h_top, h_bot, layer = (h, h, 1) if case == "a" else ((h, 0.0, 1) if case == "c" else (h, 0.0, 2))
    p = P.build(k, t * 1e3, l1_mm, wl * l1_mm, h_top, h_bot, 1.0, depth_mm, copper_strip=True, k_strip=1.0e5, layer=layer)
    d_t = P.run(p, model, cell, **kw)
    return k * depth_mm * 1e-3 * d_t / 1.0


def part4(rows2):
    """!
    @brief The program on the trace cells (a), (c) and (d).
    @param rows2 Rows of part 2 (the independent values).
    @return list of rows.
    """
    print("\n4a. The program on the trace cells of the homogeneous slab (k = 0.4, L1 = 20 mm, depth 2 mm, copper strip k = 1e5 under the heater; error against the independent solver, %)")
    pick = [(0.01, 1.0, 0.1), (0.01, 1.0, 1.0), (1.0, 0.01, 0.1), (1.0, 1.0, 0.1), (1.0, 1.0, 1.0), (100.0, 0.01, 0.1), (100.0, 1.0, 0.1)]
    variants = [("fvm", 0.5, {}), ("fvm", 0.25, {}), ("fdm", 0.25, {}), ("solid3d", 0.5, {}), ("solid3d", 0.5, {"n_diel": 16}), ("lumped", 0.5, {}), ("analytic", 0.5, {})]
    ref = {(r["bi"], r["tau"], r["wl"]): r["solver"] for r in rows2}
    out = []
    print("   case Bi2    t/L1 w/L1 |  psi solver | " + " | ".join(f"{m}@{c}{'*' if kw else ''}" for m, c, kw in variants))
    for case in ("a", "c", "d"):
        for key in pick:
            if key not in ref:
                continue
            psi_ref = ref[key]["c0" if case == "c" else case]
            line = f"   ({case})  {key[0]:6.2f} {key[1]:5.2f} {key[2]:4.1f} | {psi_ref:10.4g} |"
            row = {"case": case, "key": key, "ref": psi_ref, "models": {}}
            for m, cell, kw in variants:
                psi = psi_program(case, m, *key, cell, **kw)
                err = 100 * (psi / psi_ref - 1) if np.isfinite(psi) else float("nan")
                row["models"][f"{m}@{cell}{'*' if kw else ''}"] = err
                line += f" {err:+7.1f} |"
            out.append(row)
            print(line)
    print("   (* = solid3d with 16 slabs per gap)")
    return out


def part4b(rows3):
    """!
    @brief The program on the 3-layer board of Table 4.
    @param rows3 Rows of part 3.
    @return list of rows.
    """
    from pcbthermal import Problem
    from pcbthermal.model import Materials
    import prog_strip as P
    print("\n4b. The program on the 3-layer board of Table 4 (FR-4 / Cu 36 um / FR-4, copper plane drawn on layer 2, heater on layer 1; R of the table; error against the independent solver with the film under the source)")
    models = [("fvm", 0.25, {}), ("fdm", 0.25, {}), ("solid3d", 0.25, {}), ("solid3d", 0.25, {"n_diel": 16}), ("lumped", 0.5, {}), ("analytic", 0.5, {})]
    print("   w/L1 | " + " | ".join(f"{m}@{c}{'*' if kw else ''}" for m, c, kw in models))
    out = []
    for r in rows3:
        wl = r["wl"]
        depth = 2.0
        p = Problem.new(10.0, depth, layers=3, thickness_mm=1.592, copper_um=36.0, ambient=0.0, h_top=10.0, h_bottom=10.0, h_side=0.0,
                        materials=Materials(k_copper=386.0, k_fr4_through=0.4, k_fr4_inplane=0.4))
        p.board.copper_thickness = [36e-6] * 3
        p.add_zone(2, rect=(0.0, 0.0, 10.0, depth))
        p_half = 0.2 * depth / 20.0
        p.add_heater(1, p_half, rect=(0.0, 0.0, wl * 10.0, depth), name="U")
        ref = r["film_under_source"]                              # R of the strip with the film under it, the program's condition
        line = f"  {wl:5.2f} |"
        row = {"wl": wl, "ref": ref, "models": {}}
        for m, cell, kw in models:
            d_t = P.run(p, m, cell, **kw)
            rr = d_t / 0.4
            row["models"][f"{m}@{cell}{'*' if kw else ''}"] = rr
            line += f" {100 * (rr / ref - 1):+6.1f} % |"
        out.append(row)
        print(line)
    print("   (* = solid3d with 16 slabs per gap)")
    return out


def main():
    """!
    @brief Run the parts and write out/lemczyk.json.
    @return None.
    """
    res = {"table1": part1()}
    r2 = part2()
    res["table23"] = r2
    r3 = part3()
    res["table4"] = r3
    if "--no-program" not in sys.argv:
        res["program_cells"] = part4(r2)
        res["program_3layer"] = part4b(r3)
    (OUT / "lemczyk.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
