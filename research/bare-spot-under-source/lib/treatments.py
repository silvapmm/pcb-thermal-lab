#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file treatments.py
@brief The treatments of a bare spot measured on a copy of the layered FVM: more laminate nodes in the gaps next to the bare cells, or a thinner lateral path in them.
@details A treatment is a dict: {"kind": "none"} the program; {"kind": "nodes", "n": n, "margin": m} each gap that borders a layer with a cell of fill below 1 is cut into n equal
         sub-gaps in the flagged cells (the cells with some laminate showing in either layer of the gap, plus a margin of cells, default ceil(d / cell) + 1 so that the refined zone
         reaches a gap thickness beyond the bare cells and the extra nodes are not walled in); {"kind": "vert"} no new node, the vertical path across a layer without copper gets the laminate of half the layer thickness on each side of the node; any "nodes" treatment may carry "vert": true
         for the same correction; {"kind": "skin", "alpha": a} no new node, the copper nodes of a flagged cell keep only
         a * d of laminate in their lateral conduction instead of d / 2 (an empirical cut, to see what a free correction could do). `run` returns the peak rise of the top layer, the
         number of unknowns that a local implementation needs (extra nodes only in the flagged cells) and the number of flagged cells.
"""

import math

import numpy as np

import layered as LY


def flags_for(net, gaps, margin_cells=None):
    """!
    @brief Flagged cells of every gap: some laminate showing in the layer above or below, plus a margin.
    @param net A fvm.Network (arrays only).
    @param gaps Thickness of every gap in m.
    @param margin_cells Margin in cells (None: ceil(d / cell) + 1 for each gap).
    @return List of boolean arrays (ny, nx), one per gap.
    """
    out = []
    for g, d in enumerate(gaps):
        m = margin_cells if margin_cells is not None else int(math.ceil(d / net.dx)) + 1
        base = np.minimum(net.fill[g], net.fill[g + 1])
        out.append(LY.flag_bare(base, 1.0, m))
    return out


def run(problem, net, treatment, gaps, kz, kxy):
    """!
    @brief Peak rise of the top layer under one treatment.
    @param problem The Problem (unused except for symmetry).
    @param net fvm.Network built with assemble=False.
    @param treatment Dict as in the module description.
    @param gaps Gap thicknesses in m.
    @param kz Through conductivity of the gaps in W/mK.
    @param kxy In-plane conductivity of the gaps in W/mK.
    @return dict with peak (K), unknowns (local implementation), flagged (cells per gap), nodes.
    """
    L, N = net.nl, net.nx * net.ny
    kind = treatment["kind"]
    tcu = [float(x) for x in problem.board.copper_thickness] if treatment.get("vert") or kind == "vert" else None
    if kind == "none":
        r = LY.solve(net, gaps, kz, kxy, [None] * (L - 1), [None] * (L - 1))
        return {"peak": r["peak"], "unknowns": L * N, "flagged": [0] * (L - 1)}
    if kind == "vert":
        # Only the vertical path across the copper-free part of a layer is corrected: no new unknown
        r = LY.solve(net, gaps, kz, kxy, [None] * (L - 1), [None] * (L - 1), tcu=tcu)
        return {"peak": r["peak"], "unknowns": L * N, "flagged": [0] * (L - 1)}
    fl = flags_for(net, gaps, treatment.get("margin"))
    if kind == "nodes":
        n = treatment["n"]
        # A gap with no flagged cell keeps its single link: the board is then the program's own, to the last bit
        parts = [np.full(n, d / n) if f.any() else None for d, f in zip(gaps, fl)]
        r = LY.solve(net, gaps, kz, kxy, parts, fl, tcu=tcu)
        extra = sum((n - 1) * int(f.sum()) for f in fl)
        return {"peak": r["peak"], "unknowns": L * N + extra, "flagged": [int(f.sum()) for f in fl]}
    if kind == "skin":
        a = treatment["alpha"]
        flb = [LY.flag_bare(np.minimum(net.fill[g], net.fill[g + 1]), 1.0, 0) for g in range(L - 1)]
        r = LY.solve(net, gaps, kz, kxy, [None] * (L - 1), flb, skin=[a * d for d in gaps])
        return {"peak": r["peak"], "unknowns": L * N, "flagged": [int(f.sum()) for f in flb]}
    raise ValueError(kind)
