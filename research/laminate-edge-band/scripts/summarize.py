#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file summarize.py
@brief Largest absolute error of every rule over groups of the sweep (thickness, edge coefficient range, cell) from out/<name>.json, and the mean extra unknowns.
@details Run (repository root): .venv/bin/python research/laminate-edge-band/scripts/summarize.py sweep30b
"""

import json
import sys

import _bootband


def main(argv=None):
    """!
    @brief Print the summary tables.
    @param argv Command line: the name of the sweep file.
    @return None
    """
    argv = sys.argv[1:] if argv is None else argv
    d = json.loads((_bootband.OUT / f"{argv[0]}.json").read_text())
    rules = list(next(iter(d.values())))
    groups = {"h<=50": lambda h: h <= 50, "h=200": lambda h: h == 200, "h=500": lambda h: h == 500, "h=2000": lambda h: h == 2000}
    for cell in sorted({float(k.split("|")[-1]) for k in d}, reverse=True):
        for t in ("0.8", "1.6", "3.2"):
            print(f"cell {cell:g} mm, t {t} mm: max |error| % over both positions   (columns: " + " ".join(f"{r[:9]:>9s}" for r in rules) + ")")
            for g, f in groups.items():
                vals = {r: [] for r in rules}
                for k, v in d.items():
                    p = k.split("|")
                    if float(p[-1]) == cell and p[3] == t and f(float(p[4])):
                        for r in rules:
                            vals[r].append(abs(v[r][0]))
                print(f"   {g:7s} " + " ".join(f"{max(vals[r]):9.1f}" for r in rules))
            ratio = [v["b1+hc"][1] / v["default"][1] for k, v in d.items() if float(k.split("|")[-1]) == cell and k.split("|")[3] == t]
            r05 = [v["b0.5+hc"][1] / v["default"][1] for k, v in d.items() if float(k.split("|")[-1]) == cell and k.split("|")[3] == t]
            print(f"   unknowns x default: b1+hc {ratio[0]:.2f}, b0.5+hc {r05[0]:.2f}")


if __name__ == "__main__":
    main()
