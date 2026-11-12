#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file summarize_program.py
@brief Group the table of study_order_program.py by (layers, fill, h_side) and print the largest shifts of the rise and of the via effect.
@details Run: `.venv/bin/python research/via-well-sheet-order/scripts/summarize_program.py research/via-well-sheet-order/out/program_fvm.md`.
"""

import sys
from collections import defaultdict


def main():
    """!
    @brief Read the Markdown table of the first argument and print the maxima per group.
    @return None.
    """
    g = defaultdict(list)
    for line in open(sys.argv[1]):
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 13 or not c[1].isdigit():
            continue
        row = dict(model=c[0], layers=c[1], fill=c[2], h=c[3], via=c[4], d=c[5], cell=c[6], t0=float(c[7]), eb=float(c[8]), dt=float(c[10]), pr=float(c[11]), pe=float(c[12]))
        g[(row["layers"], row["fill"], row["h"])].append(row)
    print("| layers | fill | h_side | rows | max abs dT (K) | max abs dT % rise | max abs dT % E | worst case |")
    print("| --: | --: | --: | --: | --: | --: | --: | :-- |")
    for k, rows in sorted(g.items()):
        w = max(rows, key=lambda r: abs(r["dt"]))
        print(f"| {k[0]} | {k[1]} | {k[2]} | {len(rows)} | {abs(w['dt']):.4f} | {max(abs(r['pr']) for r in rows):.3f} | {max(abs(r['pe']) for r in rows):.2f} | {w['via']} d={w['d']} cell={w['cell']} (dT {w['dt']:+.4f}) |")


if __name__ == "__main__":
    main()
