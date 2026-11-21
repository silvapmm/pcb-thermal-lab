#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_steady_plates.py
@brief The surface read-out of the Lumped (upper bound and parabola), the Analytic (rule F) and the 3D solid (rule S, and the copper slabs) on eight plates, against the independent 3D solution and the finite-element surface.
@details Per plate (lib/plates.py: case 2's plate with one 25 W source, five thick plates, a two-layer board with 2 mm of top copper without and with a via) every model is run at the plan cell given
         (default 0.5 mm, where every source edge lies on a cell edge): the column read-out under the source (the part row: the hottest cell), the program's own surface of the FVM and the FEM, and the
         prototypes of lib/rules.py. Errors are against the independent surface (layered3d) in K and in percent of its rise above the ambient; the sign is + when the estimate is hot.
         The UPPER BOUND of the Lumped is its column peak plus q'' t / (2 k): it is hot-side when it is above the reference. Usage: .venv/bin/python research/surface-readout-models/scripts/study_steady_plates.py [cell_mm]
         (about 3 min, under 1.5 GB).
"""

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (ROOT, os.path.join(HERE, "..", "lib"), os.path.join(ROOT, "research", "through-thickness-readout", "lib")):
    if p not in sys.path:
        sys.path.insert(0, p)
import plates  # noqa: E402
import rules  # noqa: E402
import solid3d_sublayers  # noqa: E402
from pcbthermal import SolverOptions, analysis, simulate  # noqa: E402


def part_numbers(res, prob):
    """!
    @brief The column maximum and, when the result has one, the surface maximum under the part.
    @param res SteadyResult.
    @param prob Problem.
    @return tuple (column max degC, surface max degC or None).
    """
    row = analysis.heater_stats(res, prob)[0]
    s = analysis.surface_stats(res, prob.heaters[0].polygon, prob.heaters[0].layer, prob.board.outline)
    return row["t_max"], (s[0] if s else None)


def run_plate(spec, cell):
    """!
    @brief Every model on one plate.
    @param spec Entry of plates.PLATES.
    @param cell Plan cell in mm.
    @return dict of numbers (degC) keyed by what they are.
    """
    prob = plates.problem(spec)
    ref = plates.reference(spec)
    out = {"name": spec[0], "ref_surf": ref["surf"], "ref_col": ref["col"], "rise": ref["surf"] - plates.AMB}
    res = {}
    for m in ("fvm", "fem", "lumped", "analytic"):
        t0 = time.time()
        res[m] = simulate(prob, SolverOptions(models=(m,), cell_mm=cell)).results[m]
        out[f"time_{m}"] = time.time() - t0
        out[f"col_{m}"], s = part_numbers(res[m], prob)
        if s is not None:
            out[f"surf_{m}"] = s
    # Lumped and Analytic by rule F, the upper bound of the Lumped by the bound
    for m in ("lumped", "analytic"):
        f = rules.field_rule(prob, np.asarray(res[m].T), cell)
        mask = f["q_src"][0] > 0
        out[f"par_{m}"] = out[f"col_{m}"] + float(f["d_top"][mask].max())
        out[f"bound_{m}"] = out[f"col_{m}"] + float(f["bound_top"][mask].max())
        out[f"d_{m}"] = float(f["d_top"][mask].max())
    # the same rule on the FVM column: how much of the error is the rule and how much the column
    f = rules.field_rule(prob, np.asarray(res["fvm"].T), cell)
    out["par_fvm_field_rule"] = out["col_fvm"] + float(f["d_top"][f["q_src"][0] > 0].max())
    # 3D solid: the program (one slab) with rule S, and 4 and 8 copper slabs
    for n in (1, 4, 8):
        mod = solid3d_sublayers.load(n)
        t0 = time.time()
        net = mod.Solid(prob, cell)
        theta, _ = net.solve()
        r = rules.solid_rule(net, theta, n)
        out[f"time_solid{n}"] = time.time() - t0
        out[f"col_solid{n}"] = float(r["col"][r["mask"]].max())
        out[f"surf_solid{n}"] = float(r["top"][r["mask"]].max())
    return out


def line(o):
    """!
    @brief One printed line of errors against the independent surface.
    @param o Result dict of run_plate.
    @return str.
    """
    e = lambda key: o[key] - o["ref_surf"]  # noqa: E731
    return (f"{o['name'][:38]:38s} ref {o['ref_surf']:7.2f} (col {o['ref_col']:6.2f}, term {o['ref_surf'] - o['ref_col']:6.3f}) | FVM {e('surf_fvm'):+7.3f} FEM {e('surf_fem'):+7.3f} | "
            f"Lumped col {o['col_lumped'] - o['ref_col']:+6.3f} bound {e('bound_lumped'):+7.3f} par {e('par_lumped'):+7.3f} | Analytic col {o['col_analytic'] - o['ref_col']:+6.3f} F {e('par_analytic'):+7.3f} | "
            f"solid col {o['col_solid1'] - o['ref_col']:+6.3f} S1 {e('surf_solid1'):+7.3f} S4 {e('surf_solid4'):+7.3f} S8 {e('surf_solid8'):+7.3f}")


def summary(rows):
    """!
    @brief Aggregate numbers of a run: ranges of the errors per rule, in K and in units of the true term.
    @param rows List of run_plate results.
    """
    term = [r["ref_surf"] - r["ref_col"] for r in rows]
    print("\nSUMMARY over", len(rows), "plates (error = estimate - independent surface; term = independent surface - independent column)")
    for key, lab in (("surf_fvm", "FVM parabola"), ("surf_fem", "FEM computed"), ("par_lumped", "Lumped parabola"), ("bound_lumped", "Lumped upper bound"), ("par_analytic", "Analytic rule F"),
                     ("surf_solid1", "solid 1 slab rule S"), ("surf_solid4", "solid 4 slabs"), ("surf_solid8", "solid 8 slabs")):
        e = np.array([r[key] - r["ref_surf"] for r in rows])
        u = e / np.array(term)
        print(f"  {lab:22s} error {e.min():+7.3f} to {e.max():+7.3f} K; in units of the term {u.min():+6.2f} to {u.max():+6.2f}; hot on {int((e > 0).sum())} of {len(e)}")
    for key, lab in (("col_lumped", "Lumped column"), ("col_analytic", "Analytic column"), ("col_solid1", "solid column"), ("col_fvm", "FVM column"), ("col_fem", "FEM column")):
        e = np.array([r[key] - r["ref_col"] for r in rows])
        print(f"  {lab:22s} column error {e.min():+7.3f} to {e.max():+7.3f} K")
    b = np.array([r["bound_lumped"] - r["col_lumped"] for r in rows])
    print(f"  q'' t / 2k over the true term: {(b / np.array(term)).min():.2f} to {(b / np.array(term)).max():.2f}")


def main(cell=0.5):
    """!
    @brief Run every plate, print the table and write out/plates.json.
    @param cell Plan cell in mm.
    """
    rows = []
    print(f"cell {cell} mm; errors against the independent 3D surface under the source (K, + hot); 'term' = reference surface minus its column mean")
    for spec in plates.PLATES:
        o = run_plate(spec, cell)
        rows.append(o)
        print(line(o), flush=True)
    summary(rows)
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    with open(os.path.join(HERE, "..", "out", f"plates_{cell}.json"), "w") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "--summary":              # read the stored run of that cell, no solve
        with open(os.path.join(HERE, "..", "out", f"plates_{float(sys.argv[1])}.json")) as fh:
            summary(json.load(fh))
    else:
        main(float(sys.argv[1]) if len(sys.argv) > 1 else 0.5)
