#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_program.py
@brief Q3 and Q7: the cases of gerber-models 4.39 on the program's default materials, and the three example boards of the repository, under the old rule and the per-point union, in the five models.
@details Question answered: (1) does this folder reproduce the numbers of gerber-models 4.39 (one zone, 40 abutting strips, two overlapping zones of fill 0.5, fills 0.8 and 0.4 overlapping partly) for the old rule, the additive rule and the per-point union?
         (2) do the example boards (`examples/*.pcbt.json`) give the same numbers under both rules (the proposal must not move them)? The examples are run with the cell of the project (the default of `simulate`), and every model.
         Modes (from the repository root): develop (the program as it is), variant (every rule on the copy), report (tables, out/study_program.txt), fdm-additive (review: the -2.3 % of 4.39).
         Run: .venv/bin/python research/zone-union/scripts/study_program.py develop | variant | report
"""

import _bootstrap  # noqa: F401  (import paths)

import json
import sys

import variant
from paths import OUT, REPO

MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")
CASES_439 = ("one zone", "40 abutting strips of 0.5 mm", "two overlapping zones of fill 0.5", "one zone of fill 0.5", "fills 0.8 and 0.4 overlapping partly")
EXAMPLES = ("example_board", "profile_board", "reference_board")


def peaks(p, cell):
    """!
    @brief Peak rise of every model.
    @param p Problem.
    @param cell Cell (mm).
    @return dict.
    """
    from pcbthermal import SolverOptions, simulate
    out = {}
    for m in MODELS:
        try:
            out[m] = round(simulate(p, SolverOptions(models=(m,), cell_mm=cell)).results[m].t_max - p.board.ambient, 4)
        except Exception as e:                               # reported, not hidden
            out[m] = type(e).__name__
    return out


def run(mode):
    """!
    @brief Run the cases and the examples.
    @param mode develop or variant.
    @return None (writes out/program_<mode>.json).
    """
    variant.use(mode == "variant")
    import cases
    from pcbthermal.project import load_project
    from zone_rules import RULES
    res = {"439": {}, "examples": {}}
    C = cases.make_cases()
    for name in CASES_439:
        p, _ = cases.build(C[name], isotropic=False)           # the 4.39 board: default anisotropic laminate, 1 mm cells
        if mode == "variant":
            res["439"][name] = {}
            for r in RULES:
                variant.set_rule(r)
                res["439"][name][r] = peaks(p, 1.0)
        else:
            res["439"][name] = {"develop": peaks(p, 1.0)}
    for ex in EXAMPLES:
        pr = load_project(REPO / "examples" / f"{ex}.pcbt.json")
        pr = getattr(pr, "problem", pr)
        for cell in (1.0, 0.5):
            key = f"{ex} ({pr.board.layers} layers, {len(pr.zones)} zones) cell {cell}"
            if mode == "variant":
                res["examples"][key] = {}
                for r in ("max_cell", "max_point"):
                    variant.set_rule(r)
                    res["examples"][key][r] = peaks(pr, cell)
            else:
                res["examples"][key] = {"develop": peaks(pr, cell)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"program_{mode}.json").write_text(json.dumps(res, indent=1))


def report():
    """!
    @brief Print the tables.
    @return None.
    """
    dev = json.loads((OUT / "program_develop.json").read_text())
    var = json.loads((OUT / "program_variant.json").read_text())
    lines = []

    def out(s=""):
        """!
        @brief Print and keep a line.
        @param s Text.
        @return None.
        """
        print(s)
        lines.append(s)

    out("gerber-models 4.39 on the default materials, 1 mm cells (20 x 20 mm, one layer, 4 x 4 mm heater of 1 W): peak rise (K) of the program as it is, then the change (%) under each rule")
    out(f"{'case':44s}{'rule':>11s}" + "".join(f"{m:>10s}" for m in MODELS))
    for name in CASES_439:
        d = dev["439"][name]["develop"]
        out(f"{name:44s}{'old (K)':>11s}" + "".join(f"{d[m]:10.2f}" for m in MODELS))
        for r in ("additive", "max_point", "prob", "sum_clip", "priority"):
            v = var["439"][name][r]
            out(f"{'':44s}{r:>11s}" + "".join(f"{100 * (v[m] / d[m] - 1):+9.1f}%" for m in MODELS))
    out("\nExample boards of the repository: peak rise (K) of the program as it is and the largest change under the per-point union (K)")
    out(f"{'board':64s}" + "".join(f"{m:>10s}" for m in MODELS))
    for key in dev["examples"]:
        d = dev["examples"][key]["develop"]
        v = var["examples"][key]["max_point"]
        num = lambda x: f"{x:10.3f}" if isinstance(x, float) else f"{str(x)[:9]:>10s}"
        out(f"{key:64s}" + "".join(num(d[m]) for m in MODELS))
        out(f"{'   change under max_point (K)':64s}" + "".join(f"{v[m] - d[m]:+10.4f}" if isinstance(v[m], float) and isinstance(d[m], float) else f"{'-':>10s}" for m in MODELS))
    (OUT / "study_program.txt").write_text("\n".join(lines))


def fdm_additive_at_nodes():
    """!
    @brief Review: trace the FDM difference on the partly overlapping pair (-2.0 % here, -2.3 % in gerber-models 4.39) by running the program's FDM with the additive rule written
           at the nodes, as gerber-models did (each zone's share averaged to the nodes, then min(1, fill + share)).
    @details The module text of the program's fdm.py is copied in memory, the one line of the zone loop is replaced, and the copy is executed as a separate module of the package;
             no file of the program is changed. Prints the peak rise of the program and of the copy and the change.
    @return float The change in percent.
    """
    import types
    variant.use(False)
    import cases
    import pcbthermal.fdm as fdm
    src = open(fdm.__file__).read()
    old = "fill[z.layer] = np.maximum(fill[z.layer], cover(z.polygon, 4) * z.fill)"
    if src.count(old) != 1:
        raise RuntimeError("the zone loop of fdm.py has changed")
    mod = types.ModuleType("pcbthermal.fdm_additive_at_nodes")
    mod.__package__ = "pcbthermal"
    exec(compile(src.replace(old, "fill[z.layer] = np.minimum(fill[z.layer] + cover(z.polygon, 4) * z.fill, 1.0)"), "fdm_additive_at_nodes", "exec"), mod.__dict__)
    p, _ = cases.build(cases.make_cases()["fills 0.8 and 0.4 overlapping partly"], isotropic=False)
    a = fdm.solve_steady(p, 1.0).t_max - p.board.ambient
    b = mod.solve_steady(p, 1.0).t_max - p.board.ambient
    change = 100 * (b / a - 1)
    print(f"FDM, fills 0.8 and 0.4 overlapping partly, 1 mm: program {a:.2f} K, additive at the nodes {b:.2f} K, change {change:+.2f} %")
    return change


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if mode in ("develop", "variant"):
        run(mode)
    elif mode == "fdm-additive":
        fdm_additive_at_nodes()
    else:
        sys.path.insert(0, str(variant.build()))
        report()
