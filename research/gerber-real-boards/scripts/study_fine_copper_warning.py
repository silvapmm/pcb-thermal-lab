#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fine_copper_warning.py
@brief The fine-copper warning: which indicator of "copper finer than the cell" predicts that the cell model of an import is off, and at what threshold should the program warn?
@details For windows cut from the top copper of every downloaded board (onesheet.cut_windows, 36 mm, 6 mm heater, pixel 0.05 mm) and cells of 0.5, 1.0 and 2.0 mm, the one-sheet physics of research/gerber-models
         gives the error of the cell model (fill fraction = what the program does, and the flow-based faces) against the five-point pixel reference. For every window and cell the indicators of `lib/fine_copper.py`
         are computed on the same coverage mask: partial_share (copper in cells that are neither empty nor full) and thin_share (copper narrower than the cell). `fine_copper.calibrate` then gives, for error limits
         of 5 and 10 %, the threshold at which at least 90 % of the bad cases are warned about and the share of good cases that are warned about too (false alarms). The indicator is also set against the heater block
         copper fraction (the simplest rival: warn when the heater block is partly covered) to see whether the new indicator earns its place.
         Output: out/fine_copper_warning.json and the printed table. Success criterion (before the run): one indicator with recall 0.9 and false alarms under 0.3 for the 10 % limit at all three cell sizes with ONE
         threshold (a threshold that moves with the cell is a function of the cell, and the warning must say so); otherwise the warning is graded by cell and the README gives the table.
         NOT verified: heaters other than 6 mm, copper thickness other than the program's default, the multilayer stack (this is the one-sheet error: a layer under another layer is less sensitive), tilted copper.
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/study_fine_copper_warning.py [--quick]   (about 1 hour; --quick: 2 windows per board, pixel 0.1 mm)
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import sys

import numpy as np

import fine_copper as fc
import native_gerber as ng
import onesheet
import rb_paths
import registry

CELLS = (0.5, 1.0, 2.0)


def collect(quick):
    """!
    @brief The cases: one per window and cell with the indicators and the errors.
    @param quick True for the reduced run.
    @return list of dicts.
    """
    pix = 0.1 if quick else 0.05
    cases = []
    for key in registry.available():
        r = registry.roles(key)
        box = ng.layer_bbox(r["outline"]) if r["outline"] else ng.layer_bbox(r["copper"][0])
        for w in onesheet.cut_windows(r["copper"][0], box, per_board=2 if quick else 6, pix=pix, seed=13):
            cov = w["coverage"]
            res = onesheet.run_window(cov, pix, CELLS, with_reference9=False)
            for c in CELLS:
                ind = fc.indicators(cov, pix, c)
                e = res["errors"][c]
                cases.append({"board": key, "x_left": w["x_left"], "y_bottom": w["y_bottom"], "cell": c, "heater_fraction": w["heater_fraction"], **ind,
                              "fill_error_percent": e["fill fraction (today)"]["5"], "flow_error_percent": e["flow-based faces"]["5"]})
            print(f"{key} ({w['x_left']}, {w['y_bottom']}) done", flush=True)
    return cases


def calibrations(cases):
    """!
    @brief The thresholds per indicator, cell, method and error limit.
    @param cases List returned by collect.
    @return dict key -> calibrate() result.
    """
    out = {}
    for c in [None] + list(CELLS):
        sel = [x for x in cases if c is None or x["cell"] == c]
        if not sel:
            continue
        for method in ("fill", "flow"):
            err = np.abs([x[f"{method}_error_percent"] for x in sel]) / 100.0
            for ind in ("partial_share", "thin_share", "heater_fraction"):
                x = np.array([s[ind] for s in sel])
                for lim in (0.05, 0.10):
                    out[f"cell {c if c else 'all'} | {method} model | {ind} | error above {int(lim * 100)} %"] = fc.calibrate(x, err, err_limit=lim, recall=0.9)
    return out


def main(argv):
    """!
    @brief Collect, calibrate, print and write the JSON.
    @param argv Command-line words: --quick.
    @return None.
    """
    if not registry.available():
        raise SystemExit("no board in data/: run scripts/fetch_boards.py first")
    cases = collect("--quick" in argv)
    cal = calibrations(cases)
    print("\nthreshold (recall 0.9), achieved recall, false alarms, cases above the limit / below")
    for k, v in cal.items():
        print(f"  {k:78s} {v['threshold']:7.3f} {v['recall']:5.2f} {v['false_alarm']:5.2f}   {v['n_bad']:3d} / {v['n_good']:3d}")
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    with open(rb_paths.OUT / "fine_copper_warning.json", "w") as fh:
        json.dump({"cases": cases, "calibration": cal}, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
