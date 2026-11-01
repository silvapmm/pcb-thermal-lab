#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_margin.py
@brief Q4: how wide must the refined zone around the bare cells be, and does grading the sub-gaps help?
@details Question answered: the extra laminate nodes of a bare cell need lateral partners in the cells around it, otherwise they are walled in at the edge of the refined zone. On the
         2-layer 1.6 mm board with a 6 mm window under the 6 mm part, cell 0.5 mm: the FVM peak (K and error against the reference) for n = 2, 4, 8 equal sub-gaps with a margin of 0, 1, 2, 4, 8
         cells and for the whole board refined; then n = 2, 3, 4, 6 with equal sub-gaps and with geometric grading (first sub-gap 0.1, 0.25 and 0.5 of a cell) at the margin the study proposes.
         No vertical correction here (to isolate the effect). Run from the repository root: .venv/bin/python research/bare-spot-under-source/scripts/study_margin.py; out/margin.txt.
"""

import _bootstrap  # noqa: F401  (import paths)

import numpy as np
from scipy.optimize import brentq

import cases as C                                                           # noqa: E402
import layered as LY                                                        # noqa: E402
import sweep as SW                                                          # noqa: E402
import treatments as TR                                                     # noqa: E402
from _bootstrap import OUT                                                  # noqa: E402


def geometric(d, n, first):
    """!
    @brief Sub-gap thicknesses growing by a constant ratio from `first` so that they sum to d (equal split if `first` is too large).
    @param d Gap thickness in m.
    @param n Number of sub-gaps.
    @param first Thickness of the first one in m.
    @return numpy.ndarray.
    """
    if first * n >= d:
        return np.full(n, d / n)
    r = brentq(lambda q: first * (q ** n - 1) / (q - 1) - d, 1.0000001, 50.0)
    return first * r ** np.arange(n)


def main():
    """!
    @brief Run the margin and grading tables.
    @return None.
    """
    lines = []
    case = SW.make_case("2L 1.6 mm", 6)
    ref = SW.cached_reference(case)["max"]
    p = C.problem(case)
    net = LY.network(p, 0.5)
    gaps, kz, kxy = LY.gap_data(p)
    one = [np.minimum(net.fill[0], net.fill[1])]
    lines.append(f"2L 1.6 mm, 6 mm window, cell 0.5 mm, reference {ref:.2f} K, program {LY.solve(net, gaps, kz, kxy, [None], [None])['peak']:.2f} K")
    for n in (2, 4, 8):
        row = []
        for mg in (0, 1, 2, 4, 8, "all"):
            fl = np.ones_like(net.fill[0], bool) if mg == "all" else LY.flag_bare(one[0], 1.0, mg)
            v = LY.solve(net, gaps, kz, kxy, [np.full(n, gaps[0] / n)], [fl])["peak"]
            row.append(f"margin {mg}: {v:.1f} K ({100 * (v / ref - 1):+.1f} %)")
        lines.append(f"n = {n}: " + "; ".join(row))
    mg = int(np.ceil(gaps[0] / net.dx)) + 1
    fl = [LY.flag_bare(one[0], 1.0, mg)]
    lines.append(f"grading at the proposed margin ({mg} cells): error % for n = 2, 3, 4, 6")
    for label, first in (("equal", None), ("first 0.1 cell", 0.1), ("first 0.25 cell", 0.25), ("first 0.5 cell", 0.5)):
        row = []
        for n in (2, 3, 4, 6):
            s = np.full(n, gaps[0] / n) if first is None else geometric(gaps[0], n, first * net.dx)
            row.append(100 * (LY.solve(net, gaps, kz, kxy, [s], fl)["peak"] / ref - 1))
        lines.append(f"  {label:<16}" + " ".join(f"{x:+6.1f}" for x in row))
    print("\n".join(lines))
    (OUT / "margin.txt").write_text("\n".join(lines))
    _ = TR


if __name__ == "__main__":
    main()
