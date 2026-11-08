#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file summarize_barrel.py
@brief Subsets of the barrel-length sweep and the best extra length a for each (reads out/barrel.json).
@details The error of R is close to linear in a (checked: the five rules lie on a line within 0.3 points), so the best a of a subset is found on a fine grid by linear
         interpolation of the five computed rules. Subsets: all, copper 35 um and above, the same with air, copper 18 um, and "multilayer" (4 and 6 layers, copper 35 um and above).
         Run from the repository root after study_barrel_length.py: `.venv/bin/python research/via-contact-geometry/scripts/summarize_barrel.py`.
"""

import json
import sys

import _bootstrap
import numpy as np

RULES = np.array([0.0, 0.25, 0.5, 0.75, 1.0])


def err_at(row, model, a):
    """!
    @brief Error of a row at an arbitrary a by linear interpolation of the computed rules.
    @param row One record of barrel.json.
    @param model "fvm" or "fdm".
    @param a Extra length in units of t_cu.
    @return float per cent.
    """
    return float(np.interp(a, RULES, [row["err"][f"{model}|{r}"] for r in RULES]))


def main():
    """!
    @brief Print the table.
    @return None.
    """
    rows = json.load(open(_bootstrap.OUT / "barrel.json"))["rows"]
    subsets = {
        "all": lambda r: True,
        "copper >= 35 um": lambda r: r["t_cu"] >= 35e-6 - 1e-12,
        "copper >= 35 um, air": lambda r: r["t_cu"] >= 35e-6 - 1e-12 and r["fill"] == "air",
        "copper 18 um": lambda r: r["t_cu"] < 20e-6,
        "4 and 6 layers, copper >= 35 um": lambda r: r["layers"] >= 4 and r["t_cu"] >= 35e-6 - 1e-12,
        "2 layers, copper >= 35 um": lambda r: r["layers"] == 2 and r["t_cu"] >= 35e-6 - 1e-12,
    }
    grid = np.linspace(0, 1, 101)
    for model in ("fvm", "fdm"):
        print(f"== {model}: n, error (mean / min / max, per cent) at a = 0 and 0.5, best a (minimum of the mean |error|) and the mean |error| there")
        for name, f in subsets.items():
            sub = [r for r in rows if f(r)]
            e0 = np.array([err_at(r, model, 0.0) for r in sub])
            e5 = np.array([err_at(r, model, 0.5) for r in sub])
            mae = [np.mean([abs(err_at(r, model, a)) for r in sub]) for a in grid]
            ab = grid[int(np.argmin(mae))]
            print(f"{name:34s} n {len(sub):3d} | a=0 {e0.mean():+6.1f} {e0.min():+6.1f} {e0.max():+6.1f} | a=.5 {e5.mean():+6.1f} {e5.min():+6.1f} {e5.max():+6.1f} | best a {ab:4.2f} (mean|e| {min(mae):4.2f}; a=0: {np.mean(np.abs(e0)):4.2f}; a=.5: {np.mean(np.abs(e5)):4.2f})")
    lin = max(abs(r["err"]["fvm|0.5"] - 0.5 * (r["err"]["fvm|0.0"] + r["err"]["fvm|1.0"])) for r in rows)
    print(f"linearity: largest departure of the a = 0.5 error from the mean of the a = 0 and a = 1 errors: {lin:.2f} points")


if __name__ == "__main__":
    sys.exit(main())
