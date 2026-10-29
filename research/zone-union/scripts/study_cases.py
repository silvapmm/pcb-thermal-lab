"""!
@file study_cases.py
@brief Q3: the cases of zones that meet or overlap, in the five models under every rule, against the independent solver on the resolved copper.
@details Question answered: for each drawing in lib/cases.py, what is the peak rise of the heater under the old rule of `develop` (max_cell), the prototype (max_point) and the other rules,
         in FVM, FDM, Lumped, Analytic and the 3D solid, and how far is each from the independent 3D solver run on the resolved copper (the geometric union of the polygons, fine grid)?
         Modes (from the repository root):
           .venv/bin/python research/zone-union/scripts/study_cases.py develop      the program as it is (rule max_cell by construction), written to out/cases_develop.json
           .venv/bin/python research/zone-union/scripts/study_cases.py variant      the copy with every rule, written to out/cases_variant.json
           .venv/bin/python research/zone-union/scripts/study_cases.py reference    the independent solver at 0.25 mm (and 0.125 mm for the convergence), out/cases_reference.json
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
        for dx in (0.5, 0.25, 0.125):
            # The finest grid only for the cases whose seams are off the grid (the aligned ones do not change with it)
            if dx == 0.125 and ("meeting" not in name and "hole" not in name and "hatch" not in name):
                continue
            r = reference.reference_rise(p, resolved, dx)
            res[name][str(dx)] = {"max": float(r["max"]), "mean": float(r["mean"])}
            print(name, dx, res[name][str(dx)], flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cases_reference.json").write_text(json.dumps(res, indent=1))


def report():
    """!
    @brief Print the tables: for each cell size, the error (%) of every rule against the reference, per model, and the change against `one zone` for the cases that must equal it.
    @return None.
    """
    var = json.loads((OUT / "cases_variant.json").read_text())
    dev = json.loads((OUT / "cases_develop.json").read_text())
    ref = json.loads((OUT / "cases_reference.json").read_text())
    from zone_rules import RULES
    lines = []

    def out(s=""):
        """!
        @brief Print and keep a line.
        @param s Text.
        @return None.
        """
        print(s)
        lines.append(s)

    out("Check: the variant with rule max_cell against the unmodified program (peak rise, K; maximum difference over all cases, cells and models)")
    worst = {}
    for name in var:
        for cell in CELLS:
            for m in MODELS:
                a, b = var[name][str(cell)]["max_cell"][m], dev[name][str(cell)]["develop"][m]
                if isinstance(a, float) and isinstance(b, float):
                    worst[m] = max(worst.get(m, 0.0), abs(a - b))
    out("  " + "  ".join(f"{m} {worst.get(m, float('nan')):.4f}" for m in MODELS))
    for cell in CELLS:
        out(f"\n=== Cells of {cell} mm: peak rise (K) per rule and model; reference = independent solver on the resolved copper (0.125 mm where run, else 0.25 mm) ===")
        for name in var:
            r = ref.get(name)
            rv = None
            if r:
                rv = r.get("0.125", r.get("0.25"))["max"]
            out(f"\n{name}" + (f"   [reference {rv:.3f} K]" if rv is not None else "   [no resolved copper]"))
            out(f"{'rule':10s}" + "".join(f"{m:>10s}" for m in MODELS) + ("   error vs reference (%)" if rv is not None else ""))
            for rule in RULES:
                row = var[name][str(cell)][rule]
                s = f"{rule:10s}" + "".join(f"{row[m]:10.3f}" if isinstance(row[m], float) else f"{str(row[m]):>10s}" for m in MODELS)
                if rv is not None:
                    s += "   " + " ".join(f"{100 * (row[m] / rv - 1):+6.2f}" if isinstance(row[m], float) else "   -   " for m in MODELS)
                out(s)
    (OUT / "study_cases.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if mode == "develop":
        run_models(False)
    elif mode == "variant":
        run_models(True)
    elif mode == "reference":
        run_reference()
    else:
        sys.path.insert(0, str(variant.build()))
        report()
