#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file summarise.py
@brief Tables of out/remeasure.json: mean and worst error of the part read-out of every variant by group of cases.
@details Error = Lumped / FVM - 1 in % of the rise, on the hottest point of the part (peak with peak) and on the footprint mean (mean with mean). Groups: all cases, place and gap,
         edge film, part size, board, layers. Run from the repository root: .venv/bin/python research/lumped-edge-link/scripts/summarise.py [file.json]
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / "out"


def table(rows, variants, keyfn, title, which=1):
    """!
    @brief Print a table: for every group the number of cases, and per variant mean [worst cool, worst hot] of the error.
    @param rows List of case dicts.
    @param variants Variant names.
    @param keyfn Function case -> group key.
    @param title Heading text.
    @param which 0 for the footprint mean, 1 for the hottest point.
    @return None.
    """
    groups = defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)
    print(f"\n{title} ({'peak' if which else 'mean'}), mean [min, max] %")
    print("%-22s %4s " % ("group", "n") + " ".join("%-24s" % v for v in variants))
    for k in sorted(groups):
        g = groups[k]
        cells = []
        for v in variants:
            e = np.array([r[v][which] for r in g])
            cells.append("%+6.1f [%+6.1f,%+6.1f]" % (e.mean(), e.min(), e.max()))
        print("%-22s %4d " % (str(k), len(g)) + " ".join("%-24s" % c for c in cells))


def main():
    """!
    @brief Print the tables.
    @return None.
    """
    rows = json.loads((OUT / (sys.argv[1] if len(sys.argv) > 1 else "remeasure.json")).read_text())
    variants = [v for v in ("program", "expo_peak", "img", "pot", "pot_first", "pot_rings", "delta", "pot:0.8", "pot_first:0.8", "first", "first:zone") if v in rows[0]]
    for which in (1, 0):
        table(rows, variants, lambda r: "all", "all cases", which)
        table(rows, variants, lambda r: (r["place"], r["d"]), "place and gap", which)
        table(rows, variants, lambda r: r["h_side"], "edge film", which)
        table(rows, variants, lambda r: r["side"], "part side mm", which)
        table(rows, variants, lambda r: (r["W"], r["layers"]), "board width and layers", which)
        far = [r for r in rows if r["d"] >= 25 or (r["place"] == "edge" and r["d"] >= 10 and r["W"] >= 100)]
        table(far, variants, lambda r: "far (gap >= 10 on 100 mm, 25)", "far from every side", which)


if __name__ == "__main__":
    main()
