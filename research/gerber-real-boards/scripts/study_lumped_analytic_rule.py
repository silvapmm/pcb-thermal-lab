#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_lumped_analytic_rule.py
@brief The Lumped and Analytic models on imported copper: when should the program warn and when refuse?
@details The two models assume a rectangle of uniform sheets with zones, vias and heatsinks; imported copper is a pattern. On the rectangle board of research/gerber-models (README 4.35, 4.37) they were 16 % (Lumped)
         and 26 % (Analytic) below the FVM. This study measures the same thing on real windows: the imported window is turned into the program's own zone description in the only way the two models can take it
         (one zone per cell with the coverage as fill, the path of `faces.solve_today`, which these models share), and the Lumped and Analytic steady solutions (pcbthermal.lumped.solve_steady, analytic.solve_steady)
         are compared with the face-conductance FVM (the best reference the program can run on this copper) and with the program's pixel run. The error is then set against the fine-copper indicators of
         `lib/fine_copper.py` (partial_share, thin_share), the copper fraction and the heater size, to find a rule of the form "refuse above X, warn between Y and X".
         Windows: 24 mm windows of every board (boardrun/onesheet.cut_windows), cell 1.0 mm, heater 6 mm, top layer, 1 W. Output: out/lumped_analytic_rule.json and the printed table.
         Success criterion (before the run): a rule on one indicator that separates the windows with error above 15 % from the rest with recall at least 0.9 for the warning and no refused window below 25 % error;
         if no indicator does, the rule is "always warn, never refuse" and the README says so. NOT verified: boards with an outline that is not a rectangle (the two models use the equivalent rectangle),
         parts with a top path, vias in large arrays; the models are run as the program runs them for zones, not on the face conductances.
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/study_lumped_analytic_rule.py [--quick]   (about 30 minutes)
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import copy
import json
import sys

import numpy as np

import boardrun
import faces as im
import fine_copper as fc
import native_gerber as ng
import onesheet
import rb_paths
import registry
from pcbthermal import analytic, lumped


def window_problem_with_zones(ib, problem, kind="coverage"):
    """!
    @brief The Problem with one zone per cell (fill = copper fraction), the description the Lumped and Analytic models can take.
    @param ib Imported board.
    @param problem Problem of the import (no zones).
    @param kind "coverage" or "binary" mask.
    @return pcbthermal.Problem (a copy).
    """
    import conduction as cd
    p = copy.deepcopy(problem)
    n = int(round(ib.cell / ib.pix))
    for l, ly in enumerate(ib.layers):
        f = cd.cell_blocks(ly[kind].astype(float)[::-1], n).mean(axis=(2, 3))
        for i in range(f.shape[0]):
            for j in range(f.shape[1]):
                if f[i, j] > 1e-6:
                    p.add_zone(l + 1, rect=(j * ib.cell, i * ib.cell, (j + 1) * ib.cell, (i + 1) * ib.cell), fill=float(f[i, j]))
    return p


def peak_on_top(res, centre, size, cell):
    """!
    @brief The mean rise of the heater block on the top layer of a program result.
    @param res pcbthermal SteadyResult of a steady solve (T in degC, shape (layers, ny, nx)).
    @param centre Heater centre (mm).
    @param size Heater side (mm).
    @param cell Cell (mm).
    @return float mean rise (K) over the block.
    """
    return boardrun.heater_stats(np.asarray(res.T) - res.ambient, cell, centre, size)[0]


def main(argv):
    """!
    @brief Run the windows, print the table, write the JSON.
    @param argv Command-line words: --quick.
    @return None.
    """
    quick = "--quick" in argv
    cell, size, heater = 1.0, 24.0, 6.0
    rows = []
    for key in registry.available():
        r = registry.roles(key)
        box0 = ng.layer_bbox(r["outline"]) if r["outline"] else ng.layer_bbox(r["copper"][0])
        for w in onesheet.cut_windows(r["copper"][0], box0, per_board=1 if quick else 4, pix=0.1, window=size, heater=heater, seed=5):
            box = (w["x_left"], w["y_bottom"], w["x_left"] + size, w["y_bottom"] + size)
            ib = boardrun.import_window(key, box, 0.1, cell)
            centre = (size / 2.0, size / 2.0)
            p = boardrun.make_problem(ib, centre, heater)
            sheets = im.layer_sheets(ib, p, "coverage")
            ref_faces = boardrun.heater_stats(im.solve_faces(ib, p, im.layer_faces(sheets, ib, p, "flow")), cell, centre, heater)[0]
            ref_fine = boardrun.heater_stats(im.solve_fine(ib, p, "coverage"), ib.pix, centre, heater)[0]
            pz = window_problem_with_zones(ib, p)
            rec = {"board": key, "x_left": w["x_left"], "y_bottom": w["y_bottom"], "copper_fraction": w["copper_fraction"], "heater_fraction": w["heater_fraction"],
                   "ref_faces_K": ref_faces, "ref_fine_K": ref_fine}
            rec.update({f"top_{k}": v for k, v in fc.indicators(ib.layers[0]["coverage"], ib.pix, cell).items()})
            for name, solver in (("lumped", lumped.solve_steady), ("analytic", analytic.solve_steady)):
                try:
                    res = solver(pz, cell_mm=cell)
                    t = peak_on_top(res, centre, heater, cell)
                    rec[name + "_K"] = float(t)
                    rec[name + "_vs_faces_percent"] = boardrun.percent(t, ref_faces)
                    rec[name + "_vs_fine_percent"] = boardrun.percent(t, ref_fine)
                except Exception as exc:                          # a model may refuse the problem: that is a result too
                    rec[name + "_error"] = str(exc)
            rows.append(rec)
            print(f"{key} ({w['x_left']}, {w['y_bottom']}): faces {ref_faces:.1f} K, fine {ref_fine:.1f} K; " + ", ".join(f"{n} {rec[n + '_vs_fine_percent']:+.1f} %" for n in ("lumped", "analytic") if n + "_vs_fine_percent" in rec), flush=True)
    # The rule: threshold on each indicator for each model
    summary = {}
    for model in ("lumped", "analytic"):
        have = [r for r in rows if model + "_vs_fine_percent" in r]
        if not have:
            continue
        err = np.abs([r[model + "_vs_fine_percent"] for r in have]) / 100.0
        for ind in ("top_partial_share", "top_thin_share", "copper_fraction", "heater_fraction"):
            x = np.array([r[ind] for r in have])
            summary[f"{model} warn at 15 %, indicator {ind}"] = fc.calibrate(x, err, err_limit=0.15, recall=0.9)
    for k, v in summary.items():
        print(f"{k}: threshold {v['threshold']:.3f}, recall {v['recall']:.2f}, false alarms {v['false_alarm']:.2f} (bad {v['n_bad']}, good {v['n_good']})")
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    with open(rb_paths.OUT / "lumped_analytic_rule.json", "w") as fh:
        json.dump({"rows": rows, "rule": summary}, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
