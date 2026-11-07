#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_summary.py
@brief Summary of the imported-board runs: mean and range of the error of the Lumped (program and the two candidates) and of the Analytic, per board, on the uniform sheet and on the imported copper.
@details Reads out/imported_parts_<board>_<candidate>.json written by study_imported_parts.py. Error = model / FVM - 1 on the hottest node (per cent). Run from the repository root after the
         studies: .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_summary.py
"""

import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"


def load(board, slug):
    """!
    @brief Rows of one run.
    @param board Board folder name.
    @param slug File suffix (the candidate name with dashes).
    @return list of rows, empty when the run does not exist.
    """
    f = OUT / f"imported_parts_{board}_{slug}.json"
    return json.loads(f.read_text()) if f.exists() else []


def main():
    """!
    @brief Print the table.
    @return None.
    """
    print("| board | sheet | parts | Lumped, program: mean (range) | Lumped, first ring at most 1 a | Lumped, first ring 1.5 cells | Analytic |")
    print("| :-- | :-- | --: | :-- | :-- | :-- | :-- |")
    for board in ("rp2040", "oswlight", "co60"):
        cap, first = load(board, "cap-1-a"), load(board, "first-1.5-cells")
        for var in ("uniform", "imported"):
            rows = [r for r in cap if var in r]
            if not rows:
                continue
            frows = {r["part"]: r for r in first if var in r}

            def stat(key, src):
                """!
                @brief Mean and range of one series.
                @param key Key of the series.
                @param src Rows (dict part -> row) or list.
                @return str.
                """
                v = [100 * (r[var][key] / r[var]["fvm"] - 1) for r in src if var in r and key in r[var]]
                return f"{st.mean(v):+.1f} ({min(v):+.1f} to {max(v):+.1f})" if v else "not run"

            print(f"| {board} | {var} | {len(rows)} | {stat('program', rows)} | {stat('cap 1 a', rows)} | {stat('first 1.5 cells', [frows[r['part']] for r in rows if r['part'] in frows])} | {stat('analytic', rows)} |")


if __name__ == "__main__":
    sys.exit(main())
