#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review.py
@brief Question of the review: does the memory law of the class table hold outside the measured thickness t, do the real entry points (api.simulate, the transient, the computed h)
       take the memory the ladder measured, what does the SOR block cost in the program's build and in a dense one, and which law replaces the bins?
@details Run from the repository root, one part at a time, on a quiet machine (each point checks the swap first and refuses to start above --max-swap-gb):

             .venv/bin/python research/memory-guard/scripts/study_review.py --points       # 8 single points (8 and 12 layers FVM, 8 and 12 layers 3D solid), at most 3 GB each
             .venv/bin/python research/memory-guard/scripts/study_review.py --paths        # api.simulate, computed h, fvm.solve_transient and the one-factor copy, 4-layer board at 0.5 mm
             .venv/bin/python research/memory-guard/scripts/study_review.py --sor          # SOR block build: program path against a dense inverse (synthetic block, n = 2450)
             .venv/bin/python research/memory-guard/scripts/study_review.py --fit          # continuous law in t_eff, checks, ceilings (reads out/ladder.jsonl and out/review_*.jsonl)

         Results go to out/review_points.jsonl, out/review_paths.jsonl, out/review_sor.jsonl and out/review_fit.json. The continuous law is
         peak = base + k1 * t_eff^a * N * (N / 500 000)^(p - 1), with t_eff = min(t, cells / t): t = N / cells is the nodes per plan cell, and cells / t replaces it when the
         graph is thicker than it is wide (a 3D solid of 56 slabs on 33 x 33 cells), where the smallest separator of the graph is a horizontal plane and not a vertical one.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "lib"))
import cases                                               # noqa: E402
import measure                                             # noqa: E402
import memory_model as mm                                  # noqa: E402

OUT = HERE.parent / "out"
BASE = 0.08e9                                              # Baseline child, measured by the ladder
NREF = 5.0e5

# The review points: thicknesses the ladder did not reach (8 and 12 copper layers), small enough to stay under 3 GB
POINTS = (
    dict(family="plain", layers=12, size_mm=100, cell_mm=1.0, model="fvm"),
    dict(family="plain", layers=8, size_mm=100, cell_mm=0.7, model="fvm"),
    dict(family="plain", layers=12, size_mm=100, cell_mm=0.7, model="fvm"),
    dict(family="plain", layers=12, size_mm=100, cell_mm=3.0, model="solid3d"),
    dict(family="plain", layers=8, size_mm=100, cell_mm=2.0, model="solid3d"),
    dict(family="plain", layers=12, size_mm=100, cell_mm=2.5, model="solid3d"),
)

# Measurements of other folders on a quiet machine (README 2), used as out-of-sample checks of the laws: (model, unknowns, cells, peak bytes, what)
QUOTED = (
    ("solid3d", 158_000, 158_000 / 6, 0.75e9, "3D plain 2 layers (6 slabs), documents"),
    ("solid3d", 248_000, 248_000 / 6, 1.2e9, "3D plain 2 layers (6 slabs), documents"),
    ("solid3d", 393_000, 393_000 / 6, 2.65e9, "3D plain 2 layers (6 slabs), documents"),
    ("solid3d", 500_000, 500_000 / 6, 3.3e9, "3D plain 2 layers (6 slabs), documents"),
    ("fvm", 992_000, 992_000 / 2, 2.7e9, "FVM plain board (t = 2), documents"),
    ("fvm", 1_975_000, 1_975_000 / 2, 5.5e9, "FVM plain board (t = 2), documents"),
)


def swap_used_gb():
    """!
    @brief Swap in use now (macOS `sysctl vm.swapusage`; 0 elsewhere).
    @return float GB.
    """
    try:
        txt = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True, timeout=5).stdout
        used = txt.split("used = ")[1].split()[0]
        return float(used.rstrip("M").replace(",", ".")) / 1024.0
    except (OSError, IndexError, ValueError, subprocess.SubprocessError):
        return 0.0


def t_eff(n, cells):
    """!
    @brief Effective thickness of the graph: the nodes per plan cell, or cells / t when the graph is thicker than it is wide.
    @param n Unknowns.
    @param cells Plan cells.
    @return float.
    """
    t = np.asarray(n, float) / np.asarray(cells, float)
    return np.minimum(t, np.asarray(cells, float) / t)


def fit_continuous(n, cells, peak):
    """!
    @brief Least squares of log((peak - base) / N) = log k1 + (p - 1) log(N / NREF) + a log t_eff.
    @param n Unknowns (array).
    @param cells Plan cells (array).
    @param peak Peak bytes (array).
    @return Tuple (k1, p, a).
    """
    n, cells, y = np.asarray(n, float), np.asarray(cells, float), np.asarray(peak, float) - BASE
    A = np.column_stack([np.ones_like(n), np.log(n / NREF), np.log(t_eff(n, cells))])
    c, *_ = np.linalg.lstsq(A, np.log(y / n), rcond=None)
    return float(np.exp(c[0])), float(1.0 + c[1]), float(c[2])


def law(n, cells, k1, p, a):
    """!
    @brief The continuous law (bytes, base included).
    @param n Unknowns.
    @param cells Plan cells.
    @param k1 Bytes per unknown at N = NREF and t_eff = 1.
    @param p Exponent in N.
    @param a Exponent in t_eff.
    @return Bytes.
    """
    n = np.asarray(n, float)
    return BASE + k1 * t_eff(n, cells) ** a * n * (n / NREF) ** (p - 1.0)


def binned(model, n, cells):
    """!
    @brief The estimate of the proposed class table (memory_model.MEASURED), without and with its safety factor.
    @param model "fvm", "fdm" or "solid3d".
    @param n Unknowns.
    @param cells Plan cells.
    @return Tuple (law bytes, law x safety bytes).
    """
    with_safety = mm.estimate_measured(model, n, cells)
    return with_safety / mm.MEASURED[mm.classify_by_t(model, n, cells)][1], with_safety


def run_points(max_swap_gb, cutoff_gb):
    """!
    @brief Measure the review points one at a time with the ladder's wrapper (lib/measure.py).
    @param max_swap_gb Do not start a point when the swap in use is above this.
    @param cutoff_gb Watchdog cutoff of a point.
    @return None (appends to out/review_points.jsonl).
    """
    OUT.mkdir(exist_ok=True)
    for spec in POINTS:
        spec = dict(spec, order="layer", series="review")
        s0 = swap_used_gb()
        if s0 > max_swap_gb:
            print(f"swap {s0:.2f} GB above {max_swap_gb} GB: stop")
            return
        n, _ = cases.count(spec)
        nx = int(round(spec["size_mm"] / spec["cell_mm"]))
        r = measure.run_case(spec, cutoff_gb * 1e9)
        s1 = swap_used_gb()
        rec = dict(spec=spec, unknowns=n, cells=nx * nx, status=r["status"], peak_bytes=r["peak_bytes"], t_solve=r.get("t_solve"),
                   swap_before_gb=s0, swap_after_gb=s1, disturbed=bool(s1 > s0 + 0.2))
        with open(OUT / "review_points.jsonl", "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"{spec['model']:8s} {spec['layers']:2d}L {spec['cell_mm']:4.1f} mm N={n:>8d} t={n / nx / nx:5.1f} peak {r['peak_bytes'] / 1e9:5.2f} GB "
              f"{r['status']} swap {s0:.2f}->{s1:.2f} GB")


def _child_paths(mode, spec):
    """!
    @brief Child process of --paths: run one entry point and print its peak and the hottest temperature of the transient.
    @param mode "network", "simulate", "computed_h", "transient" or "transient_copy".
    @param spec Case spec.
    @return None.
    """
    import resource
    from pcbthermal import api, fvm
    import review_copies

    unit = 1 if sys.platform == "darwin" else 1024
    p = cases.build(spec)
    t0 = time.perf_counter()
    extra = {}
    if mode == "network":
        nx = int(round(spec["size_mm"] / spec["cell_mm"]))
        fvm.Network(p, nx, nx).solve_steady()
    elif mode in ("simulate", "computed_h"):
        if mode == "computed_h":
            p.board.h_mode = "computed"
        api.simulate(p, api.SolverOptions(models=("fvm",), cell_mm=spec["cell_mm"]))
    elif mode in ("transient", "transient_copy"):
        if mode == "transient_copy":
            fvm.transient_from_network = review_copies.transient_from_network_one_factor
        r = fvm.solve_transient(p, t_end=200.0, n_out=10, cell_mm=spec["cell_mm"])
        extra["t_max"] = [float(v) for v in r.t_max]
    print(json.dumps(dict(mode=mode, peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit, t_s=time.perf_counter() - t0, **extra)))


def run_paths(max_swap_gb):
    """!
    @brief Peak of the program's entry points on the 4-layer plain board at 0.5 mm (160 000 unknowns), each in its own process.
    @param max_swap_gb Do not start a run when the swap in use is above this.
    @return None (appends to out/review_paths.jsonl).
    """
    OUT.mkdir(exist_ok=True)
    spec = dict(family="plain", layers=4, size_mm=100, cell_mm=0.5, model="fvm")
    for mode in ("network", "simulate", "computed_h", "transient", "transient_copy"):
        s0 = swap_used_gb()
        if s0 > max_swap_gb:
            print(f"swap {s0:.2f} GB above {max_swap_gb} GB: stop")
            return
        out = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--child-paths", mode, json.dumps(spec)], capture_output=True, text=True, cwd=str(ROOT))
        rec = json.loads(out.stdout.strip().splitlines()[-1])
        s1 = swap_used_gb()
        rec.update(swap_before_gb=s0, swap_after_gb=s1, disturbed=bool(s1 > s0 + 0.2))
        with open(OUT / "review_paths.jsonl", "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"{mode:15s} peak {rec['peak_bytes'] / 1e9:5.2f} GB  {rec['t_s']:5.1f} s  swap {s0:.2f}->{s1:.2f} GB")


def _child_sor(n, mode):
    """!
    @brief Child process of --sor: build the inverse of a synthetic SPD block of n unknowns and print the growth of the peak.
    @param n Block size.
    @param mode "program" or "dense".
    @return None.
    """
    import resource
    import scipy.sparse as sp
    import review_copies

    unit = 1 if sys.platform == "darwin" else 1024
    A = sp.random(n, n, density=6.0 / n, format="csr", random_state=1)
    A = (A + A.T + sp.identity(n) * 20.0).tocsr()                   # Diagonally dominant, so invertible
    r0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit
    keep = review_copies.sor_inverse_program(A) if mode == "program" else review_copies.sor_inverse_dense(A)
    r1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit
    print(json.dumps(dict(n=n, mode=mode, growth_bytes=r1 - r0, per_n2=(r1 - r0) / n / n, kept=type(keep).__name__)))


def run_sor():
    """!
    @brief The block inverse of n = 2450 built as the program does and kept dense.
    @return None (appends to out/review_sor.jsonl).
    """
    OUT.mkdir(exist_ok=True)
    for mode in ("program", "dense"):
        out = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--child-sor", "2450", mode], capture_output=True, text=True, cwd=str(ROOT))
        rec = json.loads(out.stdout.strip().splitlines()[-1])
        with open(OUT / "review_sor.jsonl", "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"n = {rec['n']}  {mode:8s} growth {rec['growth_bytes'] / 1e9:5.3f} GB = {rec['per_n2']:5.1f} n^2 bytes")


def fit():
    """!
    @brief Fit the continuous law per model on the ladder, test it and the class table on the review points and on the quoted measurements, and give the ceilings.
    @return None (writes out/review_fit.json).
    """
    rows = [json.loads(line) for line in (OUT / "ladder.jsonl").read_text().splitlines() if line.strip()]
    ok = [r for r in rows if r["status"] == "ok" and r["spec"].get("mode", "solve") == "solve" and r["spec"]["series"] != "baseline"
          and r["spec"].get("order", "layer") == "layer" and r["unknowns"] >= 50000]
    rev = []
    if (OUT / "review_points.jsonl").exists():
        rev = [json.loads(line) for line in (OUT / "review_points.jsonl").read_text().splitlines() if line.strip()]
        rev = [r for r in rev if r["status"] == "ok" and not r["disturbed"]]
    res = {}
    print("== Continuous law peak = base + k1 t_eff^a N (N/500 000)^(p-1), fitted on the ladder (layer-major, N >= 50 000) ==")
    for model in ("fvm", "fdm", "solid3d"):
        pts = [r for r in ok if r["spec"]["model"] == model]
        n = np.array([r["unknowns"] for r in pts], float)
        c = np.array([r["cells"] for r in pts], float)
        y = np.array([r["peak_bytes"] for r in pts], float)
        k1, p, a = fit_continuous(n, c, y)
        rat = y / law(n, c, k1, p, a)
        bl = np.array([y[i] / binned(model, n[i], c[i])[0] for i in range(len(n))])
        safety = float(rat.max()) * 1.1
        res[model] = dict(k1=k1, p=p, a=a, ratio_min=float(rat.min()), ratio_max=float(rat.max()), safety=safety, points=len(pts),
                          binned_ratio_min=float(bl.min()), binned_ratio_max=float(bl.max()))
        print(f"{model:8s} pts {len(pts):3d}  k1 {k1:6.0f} B  p {p:4.2f}  a {a:4.2f}   ladder measured/law {rat.min():4.2f} - {rat.max():4.2f} (safety {safety:4.2f})"
              f"   class table measured/law {bl.min():4.2f} - {bl.max():4.2f}")
    print("\n== Review points (not in either fit): measured against the class table with its safety, and against the continuous law ==")
    for r in rev:
        m, n, c, y = r["spec"]["model"], r["unknowns"], r["cells"], r["peak_bytes"]
        b0, b1 = binned(m, n, c)
        cl = float(law(n, c, res[m]["k1"], res[m]["p"], res[m]["a"]))
        print(f"{m:8s} {r['spec']['layers']:2d}L {r['spec']['cell_mm']:4.1f} mm N={n:>7d} t={n / c:5.1f} t_eff={float(t_eff(n, c)):5.1f}  measured {y / 1e9:5.2f} GB"
              f"  class table {b0 / 1e9:5.2f} (x safety {b1 / 1e9:5.2f}) measured/estimate {y / b1:4.2f}   continuous {cl / 1e9:5.2f} measured/law {y / cl:4.2f}")
    print("\n== Quoted measurements of other folders (README 2), out of sample ==")
    for m, n, c, y, what in QUOTED:
        b0, b1 = binned(m, n, c)
        cl = float(law(n, c, res[m]["k1"], res[m]["p"], res[m]["a"]))
        print(f"{what:42s} N={n:>8d} measured {y / 1e9:5.2f} GB  class law {b0 / 1e9:5.2f} measured/law {y / b0:4.2f} (safety of the class "
              f"{mm.MEASURED[mm.classify_by_t(m, n, c)][1]:4.2f})   continuous {cl / 1e9:5.2f} measured/law {y / cl:4.2f}")
    print("\n== Largest N inside the limit, with the safety factor: the study's 0.7 x 16e9 and the program's 0.7 x ram_bytes() ==")
    ram = 17_179_869_184
    for model, t, label in (("solid3d", 6, "3D 6 slabs"), ("solid3d", 10, "3D 10 slabs"), ("solid3d", 16, "3D 16 slabs"), ("solid3d", 26, "3D 26 slabs"),
                            ("fvm", 2, "FVM t = 2"), ("fvm", 4, "FVM t = 4"), ("fvm", 6, "FVM t = 6"), ("fvm", 12, "FVM t = 12")):
        out = []
        for limit in (0.7 * 16e9, 0.7 * ram):
            lo, hi = 1e4, 1e8
            for _ in range(80):
                mid = (lo * hi) ** 0.5
                ok_ = law(mid, mid / t, res[model]["k1"], res[model]["p"], res[model]["a"]) * res[model]["safety"] <= limit
                lo, hi = (mid, hi) if ok_ else (lo, mid)
            lo2, hi2 = 1e4, 1e8
            for _ in range(80):
                mid = (lo2 * hi2) ** 0.5
                lo2, hi2 = (mid, hi2) if binned(model, mid, mid / t)[1] <= limit else (lo2, mid)
            out.append((int(lo), int(lo2)))
        res.setdefault("ceilings", {})[label] = out
        print(f"{label:12s} continuous: {out[0][0]:>9d} at 11.2 GB, {out[1][0]:>9d} at 12.0 GB    class table: {out[0][1]:>9d} at 11.2 GB, {out[1][1]:>9d} at 12.0 GB")
    (OUT / "review_fit.json").write_text(json.dumps(res, indent=1))


def main():
    """!
    @brief Entry: one part per call (see the file header).
    @return None.
    """
    a = sys.argv[1:]
    if a and a[0] == "--child-paths":
        _child_paths(a[1], json.loads(a[2]))
    elif a and a[0] == "--child-sor":
        _child_sor(int(a[1]), a[2])
    elif "--points" in a:
        run_points(max_swap_gb=1.5, cutoff_gb=3.2)
    elif "--paths" in a:
        run_paths(max_swap_gb=1.5)
    elif "--sor" in a:
        run_sor()
    elif "--fit" in a:
        fit()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
