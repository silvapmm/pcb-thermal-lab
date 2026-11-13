#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_thin_laminate.py
@brief The thin-laminate boards of `docs/validation.md` 44 (`research/strong-edge-laminate/scripts/study_thin_laminate.py`: 10 x 10 mm, 2 to 8 copper layers in 1.0 to
       2.4 mm, full copper or a pad on the outer layers, h_side 200 / 500 / 1000 / 2000) solved by the finite elements, against that study's own 3D finite-volume
       reference and against the program (FVM and FDM, default laminate rule and 8 sub-gaps): what is the real error behind the edge-laminate warning numbers, and
       is the 'not reconciled' gap between sections 36 and 44 (-1.3 / -3.9 / -7.2 / -11.7 against -0.8 / -2.5 / -5.1 / -8.9 %) explained?
@details Run from the repository root: `research/independent-fem-edge/.venv-research/bin/python research/independent-fem-edge/scripts/study_thin_laminate.py fem` (the FEM sequences, cached in
         `research/independent-fem-edge/out/thin_fem.json`; CG + AMG above 60 000 unknowns, about 40 minutes, under 3 GB), then `.venv/bin/python ... prog` (program and reference, cached
         in `research/independent-fem-edge/out/thin_cache.jsonl` through the research script's own cache with THIN_OUT; the research folder is not written to), then `... report`.
         Read-outs: the FEM point maximum and the hottest cell mean on the 0.25 and 0.5 mm grids of the program (`board.cell_max`), the latter being the
         like-for-like comparison with the program's and the reference's hottest cell.
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(FOLDER, "..", ".."))
OUT = os.path.join(FOLDER, "out")
os.environ.setdefault("THIN_OUT", os.path.join(OUT, "thin_cache.jsonl"))
sys.path.insert(0, os.path.join(FOLDER, "lib"))
sys.path.insert(1, ROOT)
sys.path.insert(2, os.path.join(ROOT, "research", "strong-edge-laminate", "scripts"))
import numpy as np                                                       # noqa: E402

import board                                                             # noqa: E402
import cases                                                             # noqa: E402
import refine                                                            # noqa: E402

FEM_CACHE = os.path.join(OUT, "thin_fem.json")
HS = (200, 500, 1000, 2000)
CASES = [("full", 2, 1.0), ("full", 4, 1.0), ("full", 4, 1.6), ("full", 6, 1.6), ("full", 6, 1.0), ("full", 6, 2.4), ("full", 8, 1.0), ("full", 8, 1.6),
         ("pad", 4, 1.6), ("pad", 6, 1.6), ("pad", 8, 1.0)]
HF = (0.2, 0.1, 0.05)
MAX_UNKNOWNS = int(os.environ.get("FEM_MAX_UNKNOWNS", "340000"))


def load(path):
    """!
    @brief Read a JSON cache.
    @param path File.
    @return dict.
    """
    return json.load(open(path)) if os.path.exists(path) else {}


def fem(cache):
    """!
    @brief The FEM sequences: three plan meshes per board and film, plus a 12-elements-per-gap check at 1000 W/m2K on the middle mesh.
    @param cache dict (written after every solve).
    @return None.
    """
    for variant, L, total in CASES:
        for h in HS:
            for hf in HF:
                for n_gap in ((6, 12) if (hf == 0.1 and h == 1000) else (6,)):
                    key = f"{variant}|{L}|{total}|{h}|{hf}|{n_gap}"
                    if key in cache:
                        continue
                    b = cases.thin_board(L, total, float(h), variant, hf=hf, n_gap=n_gap)
                    n_est = b.plan.xy.shape[0] * (b.dz.size + 1)
                    if n_est > MAX_UNKNOWNS:
                        print(key, "skipped:", n_est, "unknowns", flush=True)
                        continue
                    t = time.time()
                    r = b.solve()
                    cache[key] = {"tmax": r["tmax"], "cell025": board.cell_max(r, 0.25e-3), "cell05": board.cell_max(r, 0.5e-3), "cell0125": board.cell_max(r, 0.125e-3),
                                  "heater_mean": r["heater_mean"], "n": r["n"], "balance": r["balance"], "peak_gb": r["peak_gb"], "seconds": time.time() - t}
                    json.dump(cache, open(FEM_CACHE, "w"), indent=1)
                    print(f"{key:28s} n {r['n']:7d} tmax {r['tmax']:.4f} cell0.25 {cache[key]['cell025']:.4f} bal {r['balance'] - 1:+.1e} peak {r['peak_gb']:.2f} GB {cache[key]['seconds']:.0f} s", flush=True)
                    if r["peak_gb"] > 2.9:
                        raise SystemExit("peak memory above 2.9 GB: stopped")


def prog_fdm(L, total, h_side, variant, cell_mm, n_sub):
    """!
    @brief The program's FDM (harmonic default) on the same board, advanced stack-up.
    @param L Copper layers.
    @param total Board thickness in m.
    @param h_side Edge coefficient W/m2K.
    @param variant 'full' or 'pad'.
    @param cell_mm Cell in mm.
    @param n_sub Sub-gaps per gap (None: the shipped rule).
    @return float rise in K.
    """
    import study_thin_laminate as st
    from pcbthermal import Problem, SolverOptions, simulate
    from pcbthermal import model as pmodel
    from pcbthermal.model import Materials
    pmodel.reload_libraries()
    w = st.W * 1e3
    p = Problem.new(w, w, L, total * 1e3, 35.0, h_top=st.HTOP, h_bottom=st.HBOT, h_side=h_side, materials=Materials(k_fr4_inplane=st.KFR))
    p.board.make_advanced()
    for layer in range(1, L + 1):
        if variant == "pad" and layer in (1, L):
            p.add_zone(layer, rect=(st.PAD[0] * 1e3, st.PAD[1] * 1e3, st.PAD[2] * 1e3, st.PAD[3] * 1e3))
        else:
            p.add_zone(layer, rect=(0, 0, w, w))
    p.add_heater(1, st.POWER, rect=(1, 4, 4, 6))
    opts = SolverOptions(models=("fdm",), cell_mm=cell_mm)
    if n_sub is not None:
        s = (total * 1e3 - L * 0.035) / (L - 1) / n_sub * 1.001 * 1e-3
        opts.laminate_params = lambda: (s, int(n_sub))
    return float(simulate(p, opts).results["fdm"].t_max - p.board.ambient)


def prog():
    """!
    @brief The program (FVM and FDM) and the research script's 3D reference on every board, through that script's cache (redirected to research/independent-fem-edge/out).
    @return None.
    """
    import study_thin_laminate as st
    for variant, L, total in CASES:
        tm = total * 1e-3
        for h in HS:
            row = {}
            for c, n in ((0.5, None), (0.5, 8), (0.25, None), (0.25, 8), (0.125, 8)):
                if c < 0.2 and L >= 8:
                    continue                                              # 8 layers at 0.125 mm with 8 sub-gaps: 410 000 program unknowns, beyond the memory limit here
                row[f"fvm{c}/{n}"] = st.cached("prog", [L, tm, h, variant, c, n], st.prog)
            for c, n in ((0.5, None), (0.25, None), (0.25, 8)):
                row[f"fdm{c}/{n}"] = st.cached("fdm", [L, tm, h, variant, c, n], prog_fdm)
            for dx, ns in ((0.25e-3, 8), (0.125e-3, 8)):
                nz = L + (L - 1) * ns
                if dx < 0.2e-3 and nz * 80 * 40 > 190000:
                    continue                                              # the finest reference of the 8-layer boards is beyond the memory limit here
                row[f"ref{dx * 1e3:g}/{ns}"] = st.cached("ref", [L, tm, h, variant, dx, ns], st.ref)["tmax"]
            import resource
            print(variant, L, total, h, {k: round(v, 4) for k, v in row.items()}, f"peak {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30:.2f} GB", flush=True)


def report():
    """!
    @brief Print the comparison table and write out/thin_report.json.
    @return None.
    """
    import study_thin_laminate as st
    cache = load(FEM_CACHE)
    rows = []
    print("| board | h | FEM point 0.2 / 0.1 / 0.05 | p | FEM ext (GCI) | z corr (12 vs 6) | FEM hottest cell 0.25 / 0.5 / 0.125 | ref 0.25 | ref 0.125 | FVM 0.5 def / 8 | FVM 0.25 def / 8 | FVM 0.125/8 | FDM 0.5 def | FDM 0.25 def / 8 |")
    print("| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |")
    for variant, L, total in CASES:
        tm = total * 1e-3
        for h in HS:
            keys = [f"{variant}|{L}|{total}|{h}|{hf}|6" for hf in HF]
            have = [k for k in keys if k in cache]
            if len(have) < 2:
                continue
            vals = [cache[k]["tmax"] for k in have]
            if len(have) == 3:
                r = refine.richardson(vals)
            else:                                                         # two meshes: second order assumed
                r = {"p": float("nan"), "ext": vals[-1] + (vals[-1] - vals[0]) / 3.0, "gci": 1.25 * abs(vals[-1] - vals[0]) / 3.0 / vals[-1]}
            k12 = f"{variant}|{L}|{total}|1000|0.1|12"
            k6 = f"{variant}|{L}|{total}|1000|0.1|6"
            zc = (cache[k12]["tmax"] - cache[k6]["tmax"]) / 3.0 if k12 in cache and k6 in cache else 0.0   # second order in the gap count: ext - v6 = (v12 - v6)/3
            zc_h = zc if h == 1000 else zc * (0.0 if h < 1000 else 1.0)    # measured only at 1000; applied there, and above it as the same amount (an under-estimate)
            ext = r["ext"] + zc_h
            fine = cache[have[-1]]
            ratio = {c: fine[c] / fine["tmax"] for c in ("cell025", "cell05", "cell0125")}   # cell-mean over point, from the finest mesh
            ext_cell = {c: ext * ratio[c] for c in ratio}

            def g(kind, args):
                """!
                @brief Cached program or reference value, or None.
                @param kind Cache kind.
                @param args Arguments.
                @return float or None.
                """
                key = kind + json.dumps(args)
                if not hasattr(st.cached, "db"):
                    st.cached("prog", [2, 1e-3, 200, "full", 0.5, None], st.prog)
                v = st.cached.db.get(key)
                return v["tmax"] if isinstance(v, dict) else v

            def e(v, ref):
                """!
                @brief Percent error string.
                @param v Value or None.
                @param ref Reference.
                @return str.
                """
                return "-" if v is None else f"{100 * (v / ref - 1):+.2f}"
            fv = {(c, n): g("prog", [L, tm, h, variant, c, n]) for c, n in ((0.5, None), (0.5, 8), (0.25, None), (0.25, 8), (0.125, 8))}
            fd = {(c, n): g("fdm", [L, tm, h, variant, c, n]) for c, n in ((0.5, None), (0.25, None), (0.25, 8))}
            rf = {dx: g("ref", [L, tm, h, variant, dx, 8]) for dx in (0.25e-3, 0.125e-3)}
            row = {"board": f"{variant} {L}L {total} mm", "h": h, "fem": vals, "p": r["p"], "ext_point": ext, "gci": r["gci"], "zcorr": zc_h, "ext_cell": ext_cell,
                   "ref": {str(k): v for k, v in rf.items()}, "fvm": {f"{c}/{n}": v for (c, n), v in fv.items()}, "fdm": {f"{c}/{n}": v for (c, n), v in fd.items()}}
            rows.append(row)
            print(f"| {row['board']} | {h} | {' / '.join(f'{v:.3f}' for v in vals)} | {r['p']:.2f} | {ext:.3f} ({100 * r['gci']:.2f} %) | {zc_h:+.3f} | "
                  f"{ext_cell['cell025']:.3f} / {ext_cell['cell05']:.3f} / {ext_cell['cell0125']:.3f} | {e(rf[0.25e-3], ext_cell['cell025'])} | {e(rf[0.125e-3], ext_cell['cell0125'])} | "
                  f"{e(fv[(0.5, None)], ext_cell['cell05'])} / {e(fv[(0.5, 8)], ext_cell['cell05'])} | {e(fv[(0.25, None)], ext_cell['cell025'])} / {e(fv[(0.25, 8)], ext_cell['cell025'])} | "
                  f"{e(fv[(0.125, 8)], ext_cell['cell0125'])} | {e(fd[(0.5, None)], ext_cell['cell05'])} | {e(fd[(0.25, None)], ext_cell['cell025'])} / {e(fd[(0.25, 8)], ext_cell['cell025'])} |")
    json.dump(rows, open(os.path.join(OUT, "thin_report.json"), "w"), indent=1)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "report"
    if what == "fem":
        fem(load(FEM_CACHE))
    elif what == "prog":
        prog()
    else:
        report()
