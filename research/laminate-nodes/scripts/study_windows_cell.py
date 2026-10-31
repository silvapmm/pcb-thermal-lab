#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_windows_cell.py
@brief Real Gerber windows against the cell size: is the shortfall of study_windows_real.py the copper finer than the cell?
@details Question answered: at the 0.8 mm cell the rule leaves -17 to -43 % on the seven real windows, while gerber-models R2 reported 1.9 and 5.3 % with eight nodes. Hypothesis: the
         scalar fill of a cell cannot hold copper tracks finer than the cell, and R2 used the pixel as the cell. The first window of each board is solved by the resolved reference at 0.2 mm
         (the copper pixel) and by the program, eight nodes everywhere and the rule at cells of 0.8, 0.4 and 0.2 mm. Output: out/windows_cell.json and a table.
         Run: .venv/bin/python research/laminate-nodes/scripts/study_windows_cell.py [--all]
"""

import _bootstrap  # noqa: F401  (import paths)

import sys

import boards as BD
import gapnet as GN
import report as RP
import rule as RU
import study_windows_real as W


def main():
    """!
    @brief Run the windows at three cell sizes.
    @return None.
    """
    p = W.problem()
    nb = BD.board_numbers(p)
    rules = {"program": RU.PRESETS["program"], "n=8 all": RU.Rule(n_fixed=8, mask="all", vert=False, face=-1.0), "rule": RU.Rule()}
    rows = []
    for name, m in W.load_windows("--all" in sys.argv):
        ref = W.reference(nb, name, m)
        row = {"window": name, "copper %": (".0f", 100 * m.mean()), "ref mean K": (".2f", ref["mean"])}
        for cell in (0.8, 0.4, 0.2):
            k = int(round(cell / W.PIX))
            n = m.shape[0] // k
            fill = m.reshape(n, k, n, k).mean(axis=(1, 3))[None]
            for rn, rl in rules.items():
                net = GN.build(p, cell, rl, fill=fill)
                th, _ = net.solve_steady()
                vals = GN.footprint_values(net, th, p, rl)[0]
                row[f"{rn} @{cell}"] = 100 * (vals[1].mean() / ref["mean"] - 1)
        rows.append(row)
        print(row, flush=True)
    RP.table(rows, list(rows[0]), title="Real windows: error of the mean heater rise against the 0.2 mm reference, by cell size (percent)")
    RP.save("windows_cell", rows)


if __name__ == "__main__":
    main()
