#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review.py
@brief The checks of the review (README section 8): is the agreement of the via effect two errors cancelling, what does the user read in kelvin, what does the released program warn, and the explanations of the transient and of the decimation tested directly.
@details Parts (all on the program of the branch, every Lumped run inside or outside `zoned_lumped.patched` as in the studies; nothing of the program is edited):
         `absolute`: on the 36 + 26 boards, the maximum rise with the vias of the program and of the zones against the cached fine-grid reference (`t_with`), the
         no-via rise of the program against `t_without`, and the zone model with vias that conduct nothing (plating 1e-12 m, open) against the no-via reference: the
         offset that the cut of a uniform footprint into A and C makes by itself, and the via effect of the zones measured from that offset.
         `edge`: the across-the-edge, off-centre, elongated and outside boards of study 4 with the error of the effect in kelvin and in percent of the reference
         rise, and the warnings that the released program (`checks.check_model_limits`) gives on them.
         `transient`: the step responses of study 2 with the peak term removed (node means only), to test the explanation that the early excess is the quasi-steady
         peak applied to the instantaneous lateral flow, and the times to 10 % and 63 % of the steady value interpolated in log time.
         `stride`: the program's stride decimation of the footprint potentials against every cell on squares at the cells the program reaches (0.5 to 1.0 mm),
         and the change of the maximum rise of a four-layer board when the blocks replace the stride.
         `outside` (optional, `--outside`): a 3 x 3 group 1 to 12 mm outside a 6 mm footprint on a 50 mm board, reference at 1/8 mm in `out/refcache_review`
         (about 3 GB resident per solve, one at a time).
         Prints the tables and writes out/review.json.
Usage: python research/lumped-zones-adoption/scripts/study_review.py [--outside]   (from the repository root; minutes with the reference cache of the folder, plus about ten minutes with --outside)
"""

import argparse
import copy
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402
from pcbthermal import checks, fvm, lumped                                   # noqa: E402


def dead(problem):
    """!
    @brief A copy of a problem whose vias conduct nothing (plating 1e-12 m, open barrels).
    @param problem The Problem.
    @return Problem.
    """
    q = copy.deepcopy(problem)
    q.board.via_plating = 1e-12
    for v in q.vias:
        v.fill_k = 0.0
    return q


def part_absolute():
    """!
    @brief Maximum rise errors against the reference, and the dead-via offset of the zones, on the family and the held-out boards.
    @return dict per set of per-board rows and a summary.
    """
    import harness as hz
    import study_family
    import study_holdout
    out = {}
    for name, specs in (("family", [(f"family {i}", s) for i, s in enumerate(study_family.specs(False))]), ("holdout", study_holdout.holdout_specs())):
        rows = []
        for lab, s in specs:
            r = zref.refs.reference(s)
            p = zref.refs.make_problem(s)
            t_p = zref.lumped_tmax(p, "P245")
            t_z = zref.lumped_tmax(p, "Z_none")
            t_0 = zref.lumped_tmax(hz.no_vias(p), "P245")
            t_d = zref.lumped_tmax(dead(p), "Z_none")
            rows.append({"label": lab, "ref_with": r["t_with"], "ref_without": r["t_without"], "P245": t_p, "Z_none": t_z, "no_vias": t_0, "Z_dead": t_d})
        a = {k: np.array([x[k] for x in rows]) for k in ("ref_with", "ref_without", "P245", "Z_none", "no_vias", "Z_dead")}
        e_p = 100 * (a["P245"] / a["ref_with"] - 1)                          # positive: the model hotter than the reference (safe side)
        e_z = 100 * (a["Z_none"] / a["ref_with"] - 1)
        e_0 = 100 * (a["no_vias"] / a["ref_without"] - 1)
        e_d = 100 * (a["Z_dead"] / a["ref_without"] - 1)
        off = a["Z_dead"] - a["no_vias"]
        e_eff_own = 100 * ((a["Z_dead"] - a["Z_none"]) / (a["ref_without"] - a["ref_with"]) - 1)
        summ = {"tmax_P245": [float(abs(e_p).mean()), float(abs(e_p).max()), float(e_p.min()), float(e_p.max()), int((e_p < -2).sum())],
                "tmax_Z": [float(abs(e_z).mean()), float(abs(e_z).max()), float(e_z.min()), float(e_z.max()), int((e_z < -2).sum())],
                "novia_P245": [float(e_0.mean()), float(e_0.min()), float(e_0.max())],
                "dead_Z_vs_ref": [float(e_d.mean()), float(e_d.min()), float(e_d.max())],
                "offset_K": [float(off.mean()), float(off.min()), float(off.max())],
                "offset_pct_rise": [float((100 * off / a["no_vias"]).min()), float((100 * off / a["no_vias"]).max())],
                "effect_own_baseline": [float(abs(e_eff_own).mean()), float(abs(e_eff_own).max()), float(e_eff_own.min()), float(e_eff_own.max())]}
        # the zones with their own dead-via offset removed (a candidate correction): hottest temperature against the reference
        e_c = 100 * ((a["Z_none"] - off) / a["ref_with"] - 1)
        summ["tmax_Z_offset_removed"] = [float(abs(e_c).mean()), float(abs(e_c).max()), float(e_c.min()), float(e_c.max())]
        for x, ep, ez in zip(rows, e_p, e_z):
            x["err_P245"], x["err_Z"] = float(ep), float(ez)
        out[name] = {"rows": rows, "summary": summ}
        print(f"\n{name} ({len(rows)} boards), maximum rise against the reference, percent (positive: the model hotter, the safe side)")
        print("| quantity | value |\n| :-- | :-- |")
        print(f"| program, with vias: mean abs / max abs / signed range / boards cooler by more than 2 % | {summ['tmax_P245'][0]:.1f} / {summ['tmax_P245'][1]:.1f} / {summ['tmax_P245'][2]:+.1f} to {summ['tmax_P245'][3]:+.1f} / {summ['tmax_P245'][4]} |")
        print(f"| zones, with vias: same | {summ['tmax_Z'][0]:.1f} / {summ['tmax_Z'][1]:.1f} / {summ['tmax_Z'][2]:+.1f} to {summ['tmax_Z'][3]:+.1f} / {summ['tmax_Z'][4]} |")
        print(f"| program, no vias, against the no-via reference: mean / range | {summ['novia_P245'][0]:+.1f} / {summ['novia_P245'][1]:+.1f} to {summ['novia_P245'][2]:+.1f} |")
        print(f"| zones with vias that conduct nothing, against the no-via reference: mean / range | {summ['dead_Z_vs_ref'][0]:+.1f} / {summ['dead_Z_vs_ref'][1]:+.1f} to {summ['dead_Z_vs_ref'][2]:+.1f} |")
        print(f"| dead-via offset of the zones, K: mean / range; percent of the rise | {summ['offset_K'][0]:+.2f} / {summ['offset_K'][1]:+.2f} to {summ['offset_K'][2]:+.2f}; {summ['offset_pct_rise'][0]:+.1f} to {summ['offset_pct_rise'][1]:+.1f} |")
        print(f"| zones minus their dead-via offset, with vias: mean abs / max abs / signed range | {summ['tmax_Z_offset_removed'][0]:.1f} / {summ['tmax_Z_offset_removed'][1]:.1f} / {summ['tmax_Z_offset_removed'][2]:+.1f} to {summ['tmax_Z_offset_removed'][3]:+.1f} |")
        print(f"| via effect of the zones measured from their own dead-via state: mean abs / max abs / signed range | {summ['effect_own_baseline'][0]:.1f} / {summ['effect_own_baseline'][1]:.1f} / {summ['effect_own_baseline'][2]:+.1f} to {summ['effect_own_baseline'][3]:+.1f} |")
    return out


def part_edge():
    """!
    @brief The boards of study 4 in kelvin and in percent of the reference rise, with the warnings of the released program.
    @return list of dict rows.
    """
    import study_edge_and_offcentre as se
    rows = []
    print("\nBoards of study 4: error of the effect in K and in percent of the reference rise with the vias (positive: the part too cool), and the released program's warnings")
    print("| board | rise K | program K (% of rise) | zones K (% of rise) | warnings of 2.4.5 (Lumped) |\n| :-- | --: | --: | --: | :-- |")
    for lab, spec in se.boards():
        r = zref.refs.reference(spec)
        e = {n: zref.lumped_E(spec, n, 0.5) for n in ("P245", "Z_none")}
        p = zref.refs.make_problem(spec)
        w = checks.check_model_limits(p, ("lumped",), 0.5)
        kinds = sorted({"under the footprint" if "under the footprint" in str(x) else "outside every footprint" if "outside the footprint" in str(x) else "other" for x in w})
        d = {n: e[n] - r["E"] for n in e}
        rows.append({"label": lab, "rise": r["t_with"], "dK": d, "pct": {n: 100 * d[n] / r["t_with"] for n in d}, "warnings": kinds})
        print(f"| {lab} | {r['t_with']:.1f} | {d['P245']:+.2f} ({100 * d['P245'] / r['t_with']:+.1f}) | {d['Z_none']:+.2f} ({100 * d['Z_none'] / r['t_with']:+.1f}) | {', '.join(kinds)} |")
    return rows


def part_transient():
    """!
    @brief Step responses with and without the peak term, and interpolated characteristic times, on the boards of study 2.
    @return list of dict rows.
    """
    import study_transient as st

    def node_only(system, theta):
        # the hottest footprint node mean, without the peak term
        R, lay = system["R"], system["layer"]
        th = np.asarray(theta).reshape(-1, R)
        return float(th[lay, :system.get("nz", 1)].max())

    def t_frac(times, z, frac, r):
        # time to a fraction of the steady value, interpolated in log time
        z = np.asarray(z)
        k = int(np.nonzero(z >= frac * r)[0][0])
        if k == 0:
            return float(times[0])
        return float(np.exp(np.log(times[k - 1]) + (frac * r - z[k - 1]) / (z[k] - z[k - 1]) * (np.log(times[k]) - np.log(times[k - 1]))))
    rows = []
    print("\nStep response of the hottest point against the FVM at 0.5 mm, percent; 'node' = the peak term removed")
    print("| board | t s | program | program node | zones | zones node |\n| :-- | --: | --: | --: | --: | --: |")
    for label, spec in st.BOARDS:
        p = zref.refs.make_problem(spec)
        t_f, z_f, r_f = fvm.step_responses(p, cell_mm=0.5, t_end=st.T_END)
        t_p, z_p, r_p = lumped.step_responses(p, cell_mm=0.5, t_end=st.T_END)
        orig = lumped._own_point
        lumped._own_point = node_only
        try:
            t_pn, z_pn, _ = lumped.step_responses(p, cell_mm=0.5, t_end=st.T_END)
        finally:
            lumped._own_point = orig
        with zref.VARIANTS["Z_none"]():
            t_z, z_z, r_z = zl.step_responses_zoned(p, cell_mm=0.5, t_end=st.T_END)
            orig_z = zl._own_point
            zl._own_point = node_only
            try:
                t_zn, z_zn, _ = zl.step_responses_zoned(p, cell_mm=0.5, t_end=st.T_END)
            finally:
                zl._own_point = orig_z
        row = {"label": label, "times": {}, "t10": {}, "t63": {}}
        for tt in (0.01, 0.1, 1.0):
            f = st.sample(t_f, z_f[0], tt)
            v = [100 * (st.sample(t, z[0], tt) / f - 1) for t, z in ((t_p, z_p), (t_pn, z_pn), (t_z, z_z), (t_zn, z_zn))]
            row["times"][str(tt)] = v
            print(f"| {label} | {tt:g} | {v[0]:+.1f} | {v[1]:+.1f} | {v[2]:+.1f} | {v[3]:+.1f} |")
        for frac, key in ((0.1, "t10"), (0.632, "t63")):
            row[key] = {"FVM": t_frac(t_f, z_f[0], frac, r_f[0]), "P245": t_frac(t_p, z_p[0], frac, r_p[0]), "Z_none": t_frac(t_z, z_z[0], frac, r_z[0])}
        rows.append(row)
    print("\n| board | t10 FVM / program / zones, s | t63 FVM / program / zones, s |\n| :-- | :-- | :-- |")
    for r in rows:
        print(f"| {r['label']} | {r['t10']['FVM']:.3g} / {r['t10']['P245']:.3g} / {r['t10']['Z_none']:.3g} | {r['t63']['FVM']:.3g} / {r['t63']['P245']:.3g} / {r['t63']['Z_none']:.3g} |")
    return rows


def part_stride():
    """!
    @brief The program's stride against every cell at the cells the program reaches, and the effect on a board.
    @return dict with the potential rows and the board rows.
    """
    pots, boards = [], []
    print("\nStride decimation of the program against every cell (square footprints, cells the program reaches)")
    print("| square mm | cell mm | cells | step | link term | peak term |\n| --: | --: | --: | --: | --: | --: |")
    for side, cell in ((14, 0.5), (16, 0.5), (20, 0.5), (30, 0.5), (31, 0.5), (24, 0.75), (40, 0.75), (20, 1.0), (40, 1.0), (50, 1.0), (60, 1.0)):
        n = int(round(side / cell))
        cov = np.zeros((n + 20, n + 20))
        cov[10:10 + n, 10:10 + n] = 1.0
        dx = cell * 1e-3
        st = lumped._footprint_potentials(cov, dx, dx)
        ex = zl.footprint_potentials_exact(cov, dx, dx)
        link = 100 * ((st[1] - st[0]) / (ex[1] - ex[0]) - 1)
        peak = 100 * ((st[0] - st[2]) / (ex[0] - ex[2]) - 1)
        step = max(int(np.ceil(n * n / 900)), 1)
        pots.append({"side": side, "cell": cell, "cells": n * n, "step": step, "link": link, "peak": peak})
        print(f"| {side} | {cell:g} | {n * n} | {step} | {link:+.1f} % | {peak:+.1f} % |")
    print("\nMaximum rise of a 4-layer copper board with a square source, stride (program) and blocks\n| source mm | cell mm | stride K | blocks K | change |\n| --: | --: | --: | --: | --: |")
    for src, cell in ((16.0, 0.5), (24.0, 0.75), (40.0, 1.0), (60.0, 1.0)):
        spec = dict(layers=4, n=0, pitch=1.0, dia=0.3, fill=0.0, side=2.0 * src, src=src, power=10.0)
        prob = zref.refs.make_problem(spec)
        prob.vias = []
        res = {}
        for mode in ("stride", "block"):
            with zl.patched(zones=False, footprint=mode):
                res[mode] = zref.pc.max_rise(prob, "lumped", cell)
        boards.append({"src": src, "cell": cell, **res})
        print(f"| {src:g} | {cell:g} | {res['stride']:.3f} | {res['block']:.3f} | {res['block'] - res['stride']:+.3f} K ({100 * (res['block'] / res['stride'] - 1):+.2f} %) |")
    return {"potentials": pots, "boards": boards}


def part_outside():
    """!
    @brief A 3 x 3 group 1 to 12 mm outside a 6 mm footprint on a 50 mm board: the program's effect against a reference at 1/8 mm.
    @return list of dict rows.
    """
    old = zref.refs.CACHE
    zref.refs.CACHE = os.path.join(zref.OUT, "refcache_review")
    rows = []
    print("\n3 x 3 group at 3.5 mm outside a 6 mm footprint on a 50 mm board (reference 1/8 mm): effect, error of the program at 0.5 and 1.0 mm")
    print("| fill | nearest via outside, mm | E_ref K | E_ref, % of the rise | program 0.5 mm | program 1.0 mm | program 0.5 mm, K |\n| :-- | --: | --: | --: | --: | --: | --: |")
    try:
        for fill in (385.0, 0.0):
            for gap in (1.0, 4.0, 8.0, 12.0):
                spec = dict(layers=4, n=3, pitch=3.5, dia=0.3, fill=fill, side=50.0, src=6.0, offset=(6.5 + gap, 0.0), src_wh=(6.0, 6.0))
                r = zref.refs.reference(spec, dx_mm=0.125)
                e5, e10 = zref.lumped_E(spec, "P245", 0.5), zref.lumped_E(spec, "P245", 1.0)
                rows.append({"fill": fill, "gap": gap, "E_ref": r["E"], "rise": r["t_without"], "err05": zref.error_pct(e5, r["E"]), "err10": zref.error_pct(e10, r["E"]), "dK05": e5 - r["E"]})
                x = rows[-1]
                print(f"| {'Cu' if fill else 'open'} | {gap:g} | {x['E_ref']:.3f} | {100 * x['E_ref'] / x['rise']:.1f} | {x['err05']:+.1f} % | {x['err10']:+.1f} % | {x['dK05']:+.2f} |", flush=True)
        # the board of the symmetry check of study 6, which had no reference there: 25 copper-filled vias 1.5 mm off the centre of a 12 x 8 mm part
        spec = dict(n=5, pitch=1.2, src=10.0, fill=385.0, offset=(1.5, 0.0), src_wh=(12.0, 8.0))
        r = zref.refs.reference(spec, dx_mm=0.125)
        p = zref.refs.make_problem(spec)
        print("\nSymmetry board of study 6 (5x5 at 1.2 mm, Cu, 1.5 mm off the centre of a 12 x 8 mm part), reference 1/8 mm\n| variant | rise K | reference K | error of the rise | error of the effect |\n| :-- | --: | --: | --: | --: |")
        for n in ("P245", "Z_none", "Z_cap"):
            t = zref.lumped_tmax(p, n)
            e = zref.error_pct(zref.lumped_E(spec, n, 0.5), r["E"])
            rows.append({"board": "symmetry", "variant": n, "rise": t, "ref": r["t_with"], "err_rise": 100 * (t / r["t_with"] - 1), "err_E": e})
            print(f"| {n} | {t:.3f} | {r['t_with']:.3f} | {100 * (t / r['t_with'] - 1):+.1f} % | {e:+.1f} % |")
    finally:
        zref.refs.CACHE = old
    return rows


def main():
    """!
    @brief Run the parts and write out/review.json.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--outside", action="store_true", help="also the 50 mm board with the group outside the footprint (new references, about 3 GB each)")
    args = ap.parse_args()
    zref.pc.load_libraries()
    data = {"absolute": part_absolute(), "edge": part_edge(), "transient": part_transient(), "stride": part_stride()}
    if args.outside:
        data["outside"] = part_outside()
    else:
        # keep the rows of an earlier --outside run, so that the figures do not lose them
        path = os.path.join(zref.OUT, "review.json")
        if os.path.exists(path):
            import json
            old = json.load(open(path))
            if "outside" in old:
                data["outside"] = old["outside"]
    print("\nwritten", zref.save_json("review.json", data))


if __name__ == "__main__":
    main()
