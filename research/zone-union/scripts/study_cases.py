#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cases.py
@brief Q3: the cases of zones that meet or overlap, in the five models under every rule, against the independent solver on the resolved copper.
@details Question answered: for each drawing in lib/cases.py, what is the peak rise of the heater under the old rule of `develop` (max_cell), the prototype (max_point) and the other rules,
         in FVM, FDM, Lumped, Analytic and the 3D solid, and how far is each from the independent 3D solver run on the resolved copper (the geometric union of the polygons, fine grid)?
         Modes (from the repository root):
           .venv/bin/python research/zone-union/scripts/study_cases.py develop      the program as it is (rule max_cell by construction), written to out/cases_develop.json
           .venv/bin/python research/zone-union/scripts/study_cases.py variant      the copy with every rule, written to out/cases_variant.json
           .venv/bin/python research/zone-union/scripts/study_cases.py reference    the independent solver at 0.25 mm (and 0.125 mm for the convergence), out/cases_reference.json
           .venv/bin/python research/zone-union/scripts/study_cases.py hatch        the mean heater rise of the hatched cases, out/cases_hatch.json
           .venv/bin/python research/zone-union/scripts/study_cases.py report       the tables from the three files (printed and saved in out/study_cases.txt)
         Peak rise = hottest cell minus the ambient (K); the reference is the hottest heater cell. Laminate isotropic 0.3 W/mK (the reference solver is isotropic); the
         anisotropic default of the program is used in study_fix_impact_cases.py only to reproduce gerber-models 4.39.
"""

import _bootstrap  # noqa: F401  (import paths)

import json
import sys

import numpy as np

import variant
from paths import OUT

MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")
CELLS = (1.0, 0.5)


def peaks(problem, cell):
    """!
    @brief Peak rise of every model on a problem.
    @param problem Problem.
    @param cell Cell size (mm).
    @return dict model -> rise (K) or the error name.
    """
    from pcbthermal import SolverOptions, simulate
    out = {}
    for m in MODELS:
        try:
            out[m] = round(simulate(problem, SolverOptions(models=(m,), cell_mm=cell)).results[m].t_max - problem.board.ambient, 4)
        except Exception as e:                                           # reported, not hidden
            out[m] = type(e).__name__
    return out


def run_models(use_variant):
    """!
    @brief Run every case; with the variant, every rule.
    @param use_variant True for the copy with the rules, False for the program as it is.
    @return None (writes the JSON file).
    """
    variant.use(use_variant)
    import cases
    from zone_rules import RULES
    res = {}
    for name, case in cases.make_cases().items():
        p, _ = cases.build(case)
        res[name] = {}
        for cell in CELLS:
            if use_variant:
                res[name][str(cell)] = {}
                for rule in RULES:
                    variant.set_rule(rule)
                    res[name][str(cell)][rule] = peaks(p, cell)
            else:
                res[name][str(cell)] = {"develop": peaks(p, cell)}
        print("done", name, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("cases_variant.json" if use_variant else "cases_develop.json")).write_text(json.dumps(res, indent=1))


def heater_mean(result, problem):
    """!
    @brief Mean temperature rise over the cells of the top layer under the heater (cell centres inside its rectangle).
    @param result SteadyResult of a model.
    @param problem Problem with one rectangular heater.
    @return float Rise in K.
    """
    T = np.asarray(result.T)[0]
    ny, nx = T.shape
    xs = (np.arange(nx) + 0.5) * problem.board.width / nx
    ys = (np.arange(ny) + 0.5) * problem.board.height / ny
    x0, y0 = problem.heaters[0].polygon.min(axis=0)
    x1, y1 = problem.heaters[0].polygon.max(axis=0)
    m = (xs[None, :] > x0) & (xs[None, :] < x1) & (ys[:, None] > y0) & (ys[:, None] < y1)
    return float(T[m].mean() - problem.board.ambient)


def run_hatch():
    """!
    @brief The mean heater rise of the hatched cases in the FVM (1 mm cells) under every rule (the maximum over the heater cells depends on the stripe phase, the mean does not).
    @return None (writes out/cases_hatch.json).
    """
    variant.use(True)
    import cases
    from pcbthermal import SolverOptions, simulate
    from zone_rules import RULES
    res = {}
    for name, case in cases.make_cases().items():
        if not name.startswith("hatch"):
            continue
        p, _ = cases.build(case)
        res[name] = {}
        for rule in RULES:
            variant.set_rule(rule)
            res[name][rule] = heater_mean(simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"], p)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cases_hatch.json").write_text(json.dumps(res, indent=1))


def run_reference():
    """!
    @brief The independent solver on the resolved copper of every case that has it, at 0.25 mm and (a subset) 0.125 mm.
    @return None (writes out/cases_reference.json).
    """
    variant.use(False)
    import cases
    import reference
    res = {}
    for name, case in cases.make_cases().items():
        p, resolved = cases.build(case)
        if resolved is None:
            continue
        res[name] = {}
        for dx, nl in ((0.5, 8), (0.25, 8), (0.25, 2), (0.125, 2)):
            # The finest grid (fewer laminate slabs, to stay under 1 GB) only for the cases whose seams are off the grid
            if dx == 0.125 and ("meeting" not in name and "hole" not in name and "hatch" not in name):
                continue
            r = reference.reference_rise(p, resolved, dx, n_lam=nl)
            res[name][f"{dx}/{nl}"] = {"max": float(r["max"]), "mean": float(r["mean"])}
            print(name, dx, nl, res[name][f"{dx}/{nl}"], flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cases_reference.json").write_text(json.dumps(res, indent=1))


def run_converge(heavy=False):
    """!
    @brief Convergence of the independent solver on the cases whose reference was not converged (review): the stripes, the crossed stripes and the frame with an island,
           against the fine cell and the number of laminate slabs, and the estimate of the converged value when the two effects are taken as independent.
    @details Added by the review of the folder. The table of README 4.6 uses 0.125 mm with 2 laminate slabs; this mode measures how far that is from the converged value.
             The estimate is r(0.125, 4) * r(0.25, 16) / r(0.25, 4) (fine-cell effect at 4 slabs times slab effect at 0.25 mm). The runs at 16 slabs peak at about 4 GB of memory
             and are made only with `heavy`; without it the estimate uses the numbers of the heavy run written in HEAVY below (measured with this same code).
    @param heavy True to also run the 16-slab and 0.1 mm grids (about 4 GB, a few minutes).
    @return None (prints, writes out/cases_converge.json).
    """
    variant.use(False)
    import cases
    import reference
    # Measured by the review with heavy=True (mean rise over the part, K): (0.25 mm, 16 slabs) and the frame at 0.1 mm with 2 and 3 slabs
    HEAVY = {"hatch: one zone of vertical stripes (fill 0.5)": {"0.25/16": 266.344},
             "hatch: crossed hatched zones (vertical and horizontal stripes)": {"0.25/16": 158.391},
             "one zone": {"0.25/16": 141.022},
             "frame with a hole and an island 0.3 mm inside it": {"0.25/16": 141.817, "0.1/2": 206.972, "0.1/3": 202.242}}
    names = list(HEAVY)
    grids = [(0.25, 2), (0.25, 4), (0.25, 8), (0.125, 2), (0.125, 4)] + ([(0.25, 16), (0.1, 2), (0.1, 3)] if heavy else [])
    C = cases.make_cases()
    res = {}
    for name in names:
        p, resolved = cases.build(C[name])
        res[name] = dict(HEAVY[name]) if not heavy else {}
        for dx, nl in grids:
            if dx == 0.1 and "frame" not in name:
                continue
            res[name][f"{dx}/{nl}"] = float(reference.reference_rise(p, resolved, dx, n_lam=nl)["mean"])
        r = res[name]
        if "frame" not in name:                                          # the 0.25 mm grid does not see the gap of the frame: no estimate from it
            r["estimate"] = r["0.125/4"] * r["0.25/16"] / r["0.25/4"]
        print(f"{name:66s}" + "  ".join(f"{k}: {v:.2f}" for k, v in r.items()), flush=True)
    base = res["hatch: one zone of vertical stripes (fill 0.5)"]
    for name in ("one zone", "hatch: crossed hatched zones (vertical and horizontal stripes)"):
        r = res[name]
        print(f"change when the second hatched zone is added ({'shifted, solid' if name == 'one zone' else 'crossed'}): "
              f"at 0.125 mm / 2 slabs {100 * (r['0.125/2'] / base['0.125/2'] - 1):+.1f} %, estimate {100 * (r['estimate'] / base['estimate'] - 1):+.1f} %")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cases_converge.json").write_text(json.dumps(res, indent=1))


def report():
    """!
    @brief Print the tables (also saved in out/study_cases.txt): errors against the reference per rule, the other models, the fills that have no resolved copper, and the hatched cases.
    @return None.
    """
    var = json.loads((OUT / "cases_variant.json").read_text())
    dev = json.loads((OUT / "cases_develop.json").read_text())
    ref = json.loads((OUT / "cases_reference.json").read_text())
    lines = []

    def out(s=""):
        """!
        @brief Print and keep a line.
        @param s Text.
        @return None.
        """
        print(s)
        lines.append(s)

    def refval(name):
        """!
        @brief The reference of a case: the finest grid that was run.
        @param name Case name.
        @return float or None.
        """
        r = ref.get(name)
        return None if not r else r.get("0.125/2", r.get("0.25/8"))["max"]

    def old(name, cell, m):
        """!
        @brief Peak rise of the program as it is (develop).
        @param name Case name.
        @param cell Cell size (mm).
        @param m Model.
        @return float.
        """
        return dev[name][str(cell)]["develop"][m]

    out("Check: the variant with the old rule against the unmodified program (peak rise, K; largest difference over all cases and both cells)")
    worst = {m: max(abs(var[n][str(c)]["max_cell"][m] - old(n, c, m)) for n in var for c in CELLS) for m in MODELS}
    out("  " + "  ".join(f"{m} {worst[m]:.4f}" for m in MODELS) + "   (the FDM of develop takes the maximum of the zones after averaging each zone over the four cells around a node, the variant takes it on the cells and then averages: the old rule is taken from develop)")
    # Reference convergence
    out("\nReference convergence (one zone / hatch cases; peak rise of the independent solver, K, by fine cell and laminate slabs)")
    for name in ("one zone", "two zones meeting at x = 10.37 mm", "hatch: one zone of vertical stripes (fill 0.5)", "hatch: crossed hatched zones (vertical and horizontal stripes)"):
        out(f"  {name:70s}" + "  ".join(f"{k}: {v['max']:.3f}" for k, v in ref[name].items()))
    others = ("prob", "sum_clip", "priority", "additive")
    for cell in CELLS:
        out(f"\n=== Cells of {cell} mm. Cases with resolved copper: error of the peak rise against the independent solver (%), FVM ===")
        out(f"{'case':72s}{'ref K':>8s}{'old':>8s}{'proto':>8s}" + "".join(f"{r:>10s}" for r in others))
        for name in var:
            rv = refval(name)
            if rv is None:
                continue
            row = var[name][str(cell)]
            e = lambda t: f"{100 * (t / rv - 1):+8.2f}"
            out(f"{name:72s}{rv:8.2f}{e(old(name, cell, 'fvm'))}{e(row['max_point']['fvm'])}" + "".join(f"{e(row[r]['fvm']):>10s}" for r in others))
        out(f"\nCells of {cell} mm, the other models: error against the reference (%), old rule (develop) / prototype")
        out(f"{'case':72s}" + "".join(f"{m:>18s}" for m in MODELS[1:]))
        for name in var:
            rv = refval(name)
            if rv is None:
                continue
            row = var[name][str(cell)]
            out(f"{name:72s}" + "".join(f"{100 * (old(name, cell, m) / rv - 1):+8.2f} /{100 * (row['max_point'][m] / rv - 1):+7.2f}" for m in MODELS[1:]))
        out(f"\nCells of {cell} mm, densities (fill below 1: no resolved copper): peak rise (K), old rule (develop) then each rule in the variant, FVM / Lumped / Analytic / 3D solid")
        out(f"{'case':44s}{'old':>9s}" + "".join(f"{r:>10s}" for r in ("max_point",) + others))
        for name in var:
            if refval(name) is not None or name.startswith("hatch"):
                continue
            row = var[name][str(cell)]
            for m in ("fvm", "lumped", "analytic", "solid3d"):
                out(f"{(name if m == 'fvm' else '')[:44]:44s}{old(name, cell, m):9.2f}" + "".join(f"{row[r][m]:10.2f}" for r in ("max_point",) + others) + f"   {m}")
    # The hatched cases: the change that the second zone brings, on the mean over the heater (the maximum depends on the stripe phase)
    hat = json.loads((OUT / "cases_hatch.json").read_text())
    base = "hatch: one zone of vertical stripes (fill 0.5)"
    rmean = lambda n: ref[n]["0.125/2"]["mean"]
    out("\nHatched zones (stripes 0.5 mm wide, pitch 1 mm: fill 0.5; every case is drawn as the whole board with fill 0.5 twice, so the models cannot tell the cases apart).")
    out("Change (%) of the mean heater rise when the second hatched zone is added to the first one: the independent solver on the stripes (0.125 mm) against the FVM (1 mm cells) under each rule")
    out(f"{'case':72s}{'reference':>10s}" + "".join(f"{r:>10s}" for r in ("max_cell", "max_point") + others))
    for name in hat:
        if name == base or "over a solid" in name:
            continue
        out(f"{name:72s}{100 * (rmean(name) / rmean(base) - 1):+10.1f}" + "".join(f"{100 * (hat[name][r] / hat[base][r] - 1):+10.1f}" for r in ("max_cell", "max_point") + others))
    out(f"  (mean heater rise of the single hatched zone: reference {rmean(base):.1f} K, FVM {hat[base]['max_point']:.1f} K: the stripe pattern is not a scalar fill, gerber-models 4.11;")
    out("   the reference of the stripes moves by 4 % with the laminate slabs (n=8 against n=2 at 0.25 mm: 267.7 and 279.1 K), so its changes are good to a few percent)")
    (OUT / "study_cases.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if mode == "develop":
        run_models(False)
    elif mode == "variant":
        run_models(True)
    elif mode == "reference":
        run_reference()
    elif mode == "hatch":
        run_hatch()
    elif mode == "converge":
        run_converge(heavy="--heavy" in sys.argv)
    else:
        sys.path.insert(0, str(variant.build()))
        report()
