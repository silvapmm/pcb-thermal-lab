#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_class_fit.py
@brief Question: which classes of board give a memory law peak = base + k N (N / 500 000)^(p - 1) that holds within a stated margin, how does the time grow, and what do the laws predict at the limit of a 16 GB machine?
@details Run from the repository root after study_memory_ladder.py --run:

             .venv/bin/python research/memory-guard/scripts/study_class_fit.py

         The first fit of study_memory_ladder.py --fit groups the points by layer count and by the laminate rule, and its ratios measured/fitted spread from 0.5 to 1.8: the
         peak depends on the nodes per column t = N / (plan cells) (a plain two-layer board has t = 2, a board with laminate nodes up to 6 or more), because the fill of the
         factor follows the thickness of the graph. This script groups the points of the layer-major order by model and by t, fits k and p of every class on the points
         with N >= 100 000 (50 000 for the models with few points), reports the ratio measured/fitted over ALL the points of the class with N >= 50 000, the prediction of the
         largest point from the others (leave-largest-out), the safety factor (largest ratio times 1.1) and the same table for the PROVISIONAL coefficients of memory_model.COEFFS,
         then the time law t_solve = a N^q, the largest N inside 70 % of 16 GB and the cell-major comparison by series. It writes out/class_fit.json.
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
import memory_model as mm                                  # noqa: E402

OUT = HERE.parent / "out"
BASE = 0.08e9              # Bytes of the baseline child (python + numpy + scipy), measured by the ladder
NREF = 5.0e5

# (class name, model, predicate on t) -- t is the nodes per column N / cells
CLASSES = (
    ("fvm_t_le_3.5", "fvm", lambda t: t <= 3.5),
    ("fvm_t_3.5_4.5", "fvm", lambda t: 3.5 < t <= 4.5),
    ("fvm_t_gt_4.5", "fvm", lambda t: t > 4.5),
    ("fdm_t_le_4.5", "fdm", lambda t: t <= 4.5),
    ("fdm_t_gt_4.5", "fdm", lambda t: t > 4.5),
    ("solid3d_t_le_6", "solid3d", lambda t: t <= 6.5),
    ("solid3d_t_6_12", "solid3d", lambda t: 6.5 < t <= 12),
    ("solid3d_t_gt_12", "solid3d", lambda t: t > 12),
)


def load():
    """!
    @brief Valid records of the ladder (status ok, solve mode, layer-major), the disturbed or killed points left out.
    @return List of dicts.
    """
    rows = [json.loads(line) for line in (OUT / "ladder.jsonl").read_text().splitlines() if line.strip()]
    return [r for r in rows if r.get("status") == "ok" and r["spec"].get("mode", "solve") == "solve" and r["spec"]["series"] != "baseline"]


def loglog(n, y):
    """!
    @brief Least-squares fit of log y = log k + p log(N / NREF) (so k is the bytes per unknown at NREF).
    @param n Unknowns.
    @param y Peak bytes minus the base.
    @return Tuple (k bytes per unknown at NREF, p).
    """
    a = np.column_stack([np.ones_like(n), np.log(n / NREF)])
    c, *_ = np.linalg.lstsq(a, np.log(y), rcond=None)
    return float(np.exp(c[0]) / NREF), float(c[1])


def law(n, k, p):
    """!
    @brief The memory law of one class (bytes, base included).
    @param n Unknowns.
    @param k Bytes per unknown at NREF.
    @param p Exponent.
    @return Bytes.
    """
    return BASE + k * n * (n / NREF) ** (p - 1.0)


def main():
    """!
    @brief Print the tables and write out/class_fit.json.
    @return None.
    """
    ok = load()
    res = {}
    print("== Memory laws by class (layer-major order; t = unknowns per plan cell) ==")
    print(f"{'class':18s} {'pts':>3s} {'p':>5s} {'k B/u@500k':>10s} {'ratio min-max (N>=50k)':>23s} {'largest from others':>20s} {'safety = max x 1.1':>19s} {'series'}")
    for name, model, pred in CLASSES:
        pts = [r for r in ok if r["spec"]["model"] == model and r["spec"]["order"] == "layer" and pred(r["unknowns"] / r["cells"])]
        big = [r for r in pts if r["unknowns"] >= (100000 if model == "fvm" else 50000)]
        if len(big) < 3:
            continue
        n = np.array([r["unknowns"] for r in big], float)
        y = np.array([r["peak_bytes"] for r in big], float) - BASE
        k, p = loglog(n, y)
        allp = [r for r in pts if r["unknowns"] >= 50000]
        ratios = np.array([r["peak_bytes"] / law(r["unknowns"], k, p) for r in allp])
        # Leave the largest point out and predict it
        order = np.argsort(n)
        k2, p2 = loglog(n[order][:-1], y[order][:-1]) if len(n) > 3 else (k, p)
        lo = big[int(order[-1])]
        loo = lo["peak_bytes"] / law(lo["unknowns"], k2, p2)
        safety = float(ratios.max()) * 1.1
        res[name] = dict(base=BASE, k=k, p=p, ratio_min=float(ratios.min()), ratio_max=float(ratios.max()), leave_largest_out=float(loo), safety=safety, points=len(allp),
                         nmax=int(max(r["unknowns"] for r in pts)), series=sorted({r["spec"]["series"] for r in pts}))
        print(f"{name:18s} {len(allp):3d} {p:5.2f} {k:10.0f} {ratios.min():10.2f} -{ratios.max():5.2f}           {loo:>10.2f}           {safety:>9.2f}      {','.join(res[name]['series'])}")

    print("\n== The same points against the PROVISIONAL coefficients of memory_model.COEFFS (measured / provisional) ==")
    prov = {}
    for r in ok:
        if r["spec"]["order"] != "layer" or r["unknowns"] < 50000 or r["spec"]["model"] not in ("fvm", "fdm", "solid3d"):
            continue
        m = r["spec"]["model"]
        if m == "solid3d":
            kl = mm.classify_solid3d(r["slabs"])
        else:
            kl = mm.classify_layered(r["spec"]["layers"], r["unknowns"] > r["spec"]["layers"] * r["cells"] * 1.02)
        prov.setdefault(kl, []).append(r["peak_bytes"] / mm.estimate_bytes(r["unknowns"], kl))
    for kl, v in sorted(prov.items()):
        print(f"{kl:24s} points {len(v):3d}  measured/provisional {min(v):.2f} - {max(v):.2f}  (>1 means the provisional estimate was BELOW the measurement)")
        res.setdefault("provisional_check", {})[kl] = dict(min=min(v), max=max(v), points=len(v))

    print("\n== Time of the solve (layer-major): t = a N^q over N >= 100 000 ==")
    for name, model, pred in CLASSES:
        pts = [r for r in ok if r["spec"]["model"] == model and r["spec"]["order"] == "layer" and pred(r["unknowns"] / r["cells"]) and r["unknowns"] >= 100000 and r.get("t_solve")]
        if len(pts) < 3:
            continue
        n = np.array([r["unknowns"] for r in pts], float)
        t = np.array([r["t_solve"] for r in pts], float)
        a = np.column_stack([np.ones_like(n), np.log(n / NREF)])
        c, *_ = np.linalg.lstsq(a, np.log(t), rcond=None)
        res[name]["t500k_s"], res[name]["q"] = float(np.exp(c[0])), float(c[1])
        k, p = res[name]["k"], res[name]["p"]
        limit = 0.7 * 16e9
        lo, hi = 1e4, 1e8
        for _ in range(80):
            mid = (lo * hi) ** 0.5
            lo, hi = (mid, hi) if law(mid, k, p) * res[name]["safety"] <= limit else (lo, mid)
        res[name]["n_at_70pct_16GB"] = int(lo)
        res[name]["t_at_that_n_s"] = float(np.exp(c[0]) * (lo / NREF) ** c[1])
        print(f"{name:18s} t(500k) = {np.exp(c[0]):6.1f} s  q = {c[1]:4.2f}   N at 70 % of 16 GB (with safety) = {int(lo):>9d}   predicted solve time there {res[name]['t_at_that_n_s']:6.0f} s")

    print("\n== Cell-major against layer-major, same board (peak GB / solve s) ==")
    by = {}
    for r in ok:
        by.setdefault((r["spec"]["family"], r["spec"]["layers"], r["spec"]["cell_mm"], r["spec"]["model"]), {})[r["spec"]["order"]] = r
    for key, d in sorted(by.items()):
        if "cell" in d and "layer" in d and key[3] == "fvm" and d["layer"]["unknowns"] >= 100000:
            a, b = d["layer"], d["cell"]
            print(f"{key[0]:8s} {key[1]}L cell {key[2]:4.2f} N={a['unknowns']:8d}  layer {a['peak_bytes'] / 1e9:5.2f} GB {a['t_solve']:6.1f} s   cell {b['peak_bytes'] / 1e9:5.2f} GB {b['t_solve']:6.1f} s")

    print("\n== Bytes per million unknowns at the finest points (the laminate rule at 0.25 mm) ==")
    for r in sorted(ok, key=lambda r: (r["spec"]["series"], r["unknowns"])):
        if r["spec"]["cell_mm"] == 0.25 and r["spec"]["model"] == "fvm" and r["spec"]["order"] == "layer":
            print(f"{r['spec']['series']:20s} N={r['unknowns']:8d} peak {r['peak_bytes'] / 1e9:5.2f} GB = {r['peak_bytes'] / r['unknowns'] * 1e6 / 1e9:4.1f} GB per million, solve {r['t_solve']:5.1f} s")
    print("\n== Unknown count: the program's count before the run against the count of the assembled network (zero tolerance) ==")
    sys.path.insert(0, str(HERE.parent / "lib"))
    import cases                                              # noqa: E402  (imports the program)
    bad, checked = [], 0
    for r in ok:
        if r["spec"]["model"] not in ("fvm", "fdm", "solid3d") or r["spec"].get("order") == "cell":
            continue
        n = cases.count(r["spec"])[0]
        checked += 1
        if n != r["unknowns"]:
            bad.append((r["spec"]["series"], r["spec"]["cell_mm"], n, r["unknowns"]))
    print(f"{checked} points checked, {len(bad)} differ" + "".join(f"\n  {b}" for b in bad[:10]))
    res["count_check"] = dict(checked=checked, differ=len(bad))
    (OUT / "class_fit.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
