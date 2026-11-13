#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file refine.py
@brief Mesh-refinement driver: observed order, Richardson extrapolation and the grid-convergence index (GCI) from three solutions on meshes refined by a constant ratio.
@details Roache's GCI with the safety factor 1.25 for three meshes: p = ln((f1 - f2) / (f2 - f3)) / ln r, f_ext = f3 + (f3 - f2) / (r^p - 1),
         GCI_fine = 1.25 |f3 - f2| / |f3| / (r^p - 1). When the sequence is not monotone the order is undefined and the finest value is returned
         with the last difference as its band (no extrapolation). Nothing here is specific to the solver.
"""

import numpy as np


def richardson(f, r=2.0, p_max=4.0):
    """!
    @brief Observed order, extrapolated value and GCI of a coarse-to-fine sequence of three values.
    @param f Values (f1 coarse, f2, f3 fine).
    @param r Refinement ratio between consecutive meshes.
    @param p_max Cap on the observed order used for the extrapolation (an order above the formal 2 is not trusted).
    @return dict: p (observed order, NaN if not monotone), ext (extrapolated value), gci (relative, fine mesh), monotone (bool), band (|f3 - f2| when not monotone).
    """
    f1, f2, f3 = (float(v) for v in f)
    d12, d23 = f1 - f2, f2 - f3
    if d12 * d23 <= 0 or d23 == 0:
        return {"p": float("nan"), "ext": f3, "gci": abs(d23) / abs(f3) if f3 else float("nan"), "monotone": False, "band": abs(d23)}
    p = np.log(abs(d12 / d23)) / np.log(r)
    pe = min(p, p_max)
    ext = f3 + (f3 - f2) / (r ** pe - 1.0)
    gci = 1.25 * abs(f3 - f2) / abs(f3) / (r ** pe - 1.0)
    return {"p": float(p), "ext": float(ext), "gci": float(gci), "monotone": True, "band": abs(ext - f3)}


def sequence(solve, hs, **kw):
    """!
    @brief Run a solver callable on a list of mesh sizes and collect the values.
    @param solve Callable(h, **kw) -> dict with the value under key 'value' (and anything else).
    @param hs Mesh sizes, coarse to fine.
    @param kw Passed through.
    @return List of result dicts, each with 'h' added.
    """
    out = []
    for h in hs:
        r = solve(h, **kw)
        r["h"] = h
        out.append(r)
    return out
