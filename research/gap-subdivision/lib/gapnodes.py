#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file gapnodes.py
@brief The layered model of the program with every dielectric gap cut into n laminate nodes through its thickness, on an in-memory copy: where, how (equal or graded) and with which correction.
@details Thin layer on top of research/bare-spot-under-source/lib/layered.py (which reproduces the program's FVM to round-off with one sub-gap and assembles the matrix again with
         sub-gaps; its tests check it against the program). Here the choices of this investigation are named:
         `where`: "all" (every cell of every gap gets the n nodes), "bare" (only the cells that show laminate in either layer of the gap, plus a margin of a gap thickness; the rest keep the
         single link, which is the program), "none" (no refinement: the program); `grading`: "equal" (n equal sub-gaps) or "graded" (the sub-gaps next to the copper are thin and grow
         by a ratio towards the middle of the gap); `half_layer`: the correction of the node of a layer that has no copper (laminate of half the layer thickness on each side of the node,
         no new unknown) with or without the new nodes. The number of unknowns of a local implementation (extra nodes only in the refined cells) is returned with the peak.
"""

import math

import numpy as np

import boards as B                                                           # noqa: F401  (puts the program and the bare-spot lib on sys.path)
import layered as LY                                                         # noqa: E402  (research/bare-spot-under-source/lib)


def parts_for(d, n, grading, ratio=2.0):
    """!
    @brief Sub-gap thicknesses of a gap of thickness d cut into n nodes' worth of sub-gaps.
    @param d Gap thickness in m.
    @param n Number of sub-gaps (n = 1 is the program's single link; n sub-gaps give n - 1 laminate nodes inside the gap).
    @param grading "equal" or "graded" (outer sub-gaps thin, growing by `ratio` towards the middle, mirrored so that both copper faces are resolved).
    @param ratio Growth ratio of a graded gap.
    @return numpy.ndarray of n thicknesses summing to d.
    """
    if n <= 1:
        return np.array([d])
    if grading == "equal":
        return np.full(n, d / n)
    # Symmetric geometric grading: weights r^min(i, n-1-i), normalised to d
    w = np.array([ratio ** min(i, n - 1 - i) for i in range(n)], dtype=float)
    return d * w / w.sum()


def run(problem, cell_mm, n, where="all", grading="equal", half_layer=False, margin=None, ratio=2.0):
    """!
    @brief Peak rise of the layered model with every gap cut into n sub-gaps.
    @param problem A Problem.
    @param cell_mm Cell size in mm.
    @param n Sub-gaps per gap (1 = the program).
    @param where "all", "bare", "under" (only the cells with copper in both layers of the gap: a probe) or "none" (see the module description).
    @param grading "equal" or "graded".
    @param half_layer True: add the half-layer laminate path to the vertical conductance and the face correction under the source (no new unknown).
    @param margin Margin of cells around the bare cells for where = "bare" (None: ceil(d / cell) + 1).
    @param ratio Growth ratio of a graded gap.
    @return dict with peak (K rise over the ambient of the top layer, mean of its hottest cell), unknowns (of a local implementation), nodes (per cell, dense), peak_all.
    """
    net = LY.network(problem, cell_mm)
    gaps, kz, kxy = LY.gap_data(problem)
    L, N = net.nl, net.nx * net.ny
    tcu = [float(x) for x in problem.board.copper_thickness] if half_layer else None
    if where == "none" or n <= 1:
        r = LY.solve(net, gaps, kz, kxy, [None] * (L - 1), [None] * (L - 1), tcu=tcu)
        return {"peak": r["peak"], "peak_all": r["peak_all"], "unknowns": L * N, "nodes": L}
    if where == "all":
        fl = [np.ones((net.ny, net.nx), dtype=bool) for _ in range(L - 1)]
    elif where == "under":
        # Single-effect probe: only the cells where both layers of the gap are copper (the gap under the pad), none of the bare laminate
        fl = [np.minimum(net.fill[g], net.fill[g + 1]) >= 1.0 - 1e-12 for g in range(L - 1)]
    else:
        fl = []
        for g, d in enumerate(gaps):
            m = margin if margin is not None else int(math.ceil(d / net.dx)) + 1
            fl.append(LY.flag_bare(np.minimum(net.fill[g], net.fill[g + 1]), 1.0, m))
    # A gap with no flagged cell keeps its single link (the program's own, bit for bit)
    parts = [parts_for(d, n, grading, ratio) if f.any() else None for d, f in zip(gaps, fl)]
    r = LY.solve(net, gaps, kz, kxy, parts, fl, tcu=tcu)
    extra = sum((n - 1) * int(f.sum()) for f in fl)
    return {"peak": r["peak"], "peak_all": r["peak_all"], "unknowns": L * N + extra, "nodes": r["nodes"], "peak_node": r["peak_node"]}
