#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_skin.py
@brief Q2: why one node per layer is cool over a bare spot: the lateral-conduction experiment (how much laminate the bare node may keep in its lateral path) and the cell dependence of the program.
@details Question answered: is the error of the program over a bare window the vertical resistance (a missing path) or the lateral conduction (a node whose temperature is that of the hot surface
         but whose sideways conductance is that of half the gap)? Part (a): the FVM copy with no new node and the laminate that the copper nodes of a bare cell keep in their lateral conduction cut
         from d / 2 (the program) to alpha d, alpha from 0 to 0.5, on the 2-layer 1.6 mm and 0.8 mm boards and the 4-layer typical board, windows 2, 6 and 12 mm, cell 0.5 mm; the alpha that gives
         zero error is read for every case (not a proposal: an empirical cut that changes with the window). Part (b): the program's FVM peak of the 6 mm window board against the cell
         (2, 1, 0.5, 0.25 mm), to show that the error does not come from the discretisation of the window edge.
         Run from the repository root: .venv/bin/python research/bare-spot-under-source/scripts/study_skin.py; out/skin.json, out/skin.txt.
"""

import _bootstrap  # noqa: F401  (import paths)

import json

import numpy as np

import cases as C                                                           # noqa: E402
import layered as LY                                                        # noqa: E402
import sweep as SW                                                          # noqa: E402
from _bootstrap import OUT                                                  # noqa: E402

ALPHAS = (0.0, 0.025, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5)


def main():
    """!
    @brief Run parts (a) and (b).
    @return None.
    """
    rows, lines = [], []
    for stack in ("2L 1.6 mm", "2L 0.8 mm", "4L typical"):
        for w in (2, 6, 12):
            case = SW.make_case(stack, w)
            ref = SW.cached_reference(case)["max"]
            p = C.problem(case)
            net = LY.network(p, 0.5)
            gaps, kz, kxy = LY.gap_data(p)
            fl = [LY.flag_bare(np.minimum(net.fill[g], net.fill[g + 1]), 1.0, 0) for g in range(case.layers - 1)]
            errs = []
            for a in ALPHAS:
                v = LY.solve(net, gaps, kz, kxy, [None] * (case.layers - 1), fl, skin=[a * d for d in gaps])["peak"]
                errs.append(100.0 * (v / ref - 1.0))
            # alpha of zero error by linear interpolation of the sign change
            e = np.array(errs)
            a0 = None
            for i in range(len(e) - 1):
                if e[i] * e[i + 1] <= 0 < abs(e[i]) + abs(e[i + 1]):
                    a0 = ALPHAS[i] + (ALPHAS[i + 1] - ALPHAS[i]) * (e[i] / (e[i] - e[i + 1]))
                    break
            rows.append({"label": f"{stack}, window {w}", "alpha": list(ALPHAS), "err": errs, "alpha_zero": a0})
            lines.append(f"(a) {stack:<11} window {w:>2} mm  ref {ref:7.2f}  errors % at alpha {ALPHAS}: " + " ".join(f"{x:+6.1f}" for x in errs) + f"  | alpha of zero error: {a0}")
            print(lines[-1], flush=True)
    case = SW.make_case("2L 1.6 mm", 6)
    ref = SW.cached_reference(case)["max"]
    p = C.problem(case)
    cell_rows = []
    for cell in (2.0, 1.0, 0.5, 0.25):
        v = C.program_peak(case, "fvm", cell, p)
        cell_rows.append((cell, v, 100.0 * (v / ref - 1.0)))
        lines.append(f"(b) 2L 1.6 mm, window 6 mm: program FVM cell {cell} mm: peak {v:.2f} K, error {cell_rows[-1][2]:+.1f} % (reference {ref:.2f} K)")
        print(lines[-1], flush=True)
    json.dump(rows, open(OUT / "skin.json", "w"), indent=1)
    (OUT / "skin.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
