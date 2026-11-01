#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file rule.py
@brief The one rule of the laminate nodes, as data: how many nodes in a gap, how the gap is cut, which cells get them (the mask and its margin), and the options that the study sweeps.
@details The program has four unreconciled treatments of the laminate between copper layers (gap-subdivision, bare-spot-under-source, gerber-models R2 and `laminate.py`, README 1.2).
         All four are cases of one construction: a **gap** (the laminate between two copper nodes; for a one-layer board the laminate between the copper node and the bottom face) is
         cut into n sub-gaps s_1 ... s_n, a node sits at every boundary between sub-gaps, and the nodes exist only in the **flagged cells** (copper partly absent next to the gap, plus a
         margin); in every other cell the gap is one link. This module holds the parameters of that construction (`Rule`), the choice of n from the gap thickness (`n_for_gap`), the cut
         (`sub_gaps`), the mask (`flag_cells`) and the count of unknowns (`unknowns`). It uses NumPy and SciPy only and knows nothing of the program, so that the same rule drives the
         FVM, the FDM and the reference-side checks.
         The four old treatments are `Rule` presets in `PRESETS` (used by study_s0_four_treatments.py).
"""

import math
from dataclasses import dataclass, replace

import numpy as np
from scipy import ndimage


@dataclass(frozen=True)
class Rule:
    """!
    @brief Parameters of the construction. All lengths in m.
    @details n of a gap = min(n_max, max(n_min, ceil(d / s_max))) unless `n_fixed` is set (a sweep). The sub-gaps of a gap are symmetric about its middle with the ratio `ratio`
             between a sub-gap and the one nearer to the copper face (1: equal; 2: the middle ones are twice as thick as the ones at the faces).
    """
    s_max: float = 0.4e-3          # largest sub-gap: n = ceil(d / s_max), so 0.4 mm -> 1, 0.8 -> 2, 1.6 -> 4 (the cuts of bare-spot-under-source P2 are close to this)
    n_min: int = 1
    n_max: int = 4
    n_fixed: int = 0               # >0: this n for every gap (sweeps); 0: the law above
    ratio: float = 1.0             # grading of the sub-gaps (see above)
    threshold: float = 1.0         # a cell is bare when the copper fill of either layer next to the gap is below this
    mask: str = "bare"             # "bare": cells with fill below the threshold; "edge": cells next to a change of the fill; "all": every cell
    margin: str = "gap"            # cells of margin around the bare cells: "gap" = ceil(d / dx) + 1; "2gap" = 2 ceil(d / dx) + 1; "none"; or a number of cells as text ("3")
    shape: str = "disc"            # shape of the margin: "disc" (Euclidean distance), "diamond" (4-neighbour dilation, the copy of bare-spot-under-source), "square"
    vert: bool = True              # vertical correction: d + (1 - f_a) t_a / 2 + (1 - f_b) t_b / 2 in the link of a cell
    face: float = 1.0              # exponent p of the face term Q (1 - f)^p t / (2 k_z A) in the reported peak, for cells with f < 1 (0: the full term on every such cell; negative: off)
    one_layer: bool = True         # the laminate under the copper of a one-layer board follows the same rule (False: laminate.py as it is)
    via_mode: str = "series"       # "series": the barrel is part of every sub-link of a refined cell; "parallel": the barrel joins the two copper nodes (the copy of the old studies)
    budget: float = 0.0            # >0: largest ratio of unknowns to the program's; n is lowered until the ratio fits (cost cap for boards that are bare everywhere)
    rebuild_slabs: bool = False    # simple stack-up with 3 or more layers: give every node t_cu + d/2 + d/2 of laminate before refining (README 4.9)
    name: str = "rule"


# The four treatments of the program as presets of the same parameters (README 1.2)
PRESETS = {
    "program": Rule(n_fixed=1, vert=False, face=-1.0, one_layer=False, name="program (n = 1; one-layer: laminate.py, 2 nodes)"),
    "gap-subdivision": Rule(n_fixed=4, ratio=2.0, mask="bare", margin="gap", shape="diamond", vert=False, face=-1.0, one_layer=False, name="gap-subdivision (n = 4 graded, bare + margin)"),
    "bare-spot": Rule(s_max=0.4e-3, n_max=4, mask="bare", margin="gap", shape="diamond", vert=True, face=1.0, one_layer=False, via_mode="parallel", name="bare-spot (n by cuts, vertical, face)"),
    "one-layer-2": Rule(n_fixed=2, mask="all", vert=False, face=-1.0, one_layer=True, name="laminate.py (2 nodes everywhere on a one-layer board)"),
}


def n_for_gap(rule, d):
    """!
    @brief Number of sub-gaps of a gap of thickness d.
    @param rule A Rule.
    @param d Gap thickness in m.
    @return int >= 1.
    """
    if rule.n_fixed > 0:
        return int(rule.n_fixed)
    return int(min(rule.n_max, max(rule.n_min, math.ceil(d / rule.s_max - 1e-9))))


def sub_gaps(d, n, ratio=1.0):
    """!
    @brief Thicknesses of the n sub-gaps of a gap, symmetric about the middle, thinner towards the copper faces by the factor `ratio`.
    @param d Gap thickness in m.
    @param n Number of sub-gaps.
    @param ratio Growth ratio from a face towards the middle (1: equal).
    @return numpy.ndarray of n thicknesses summing to d.
    """
    if n <= 1:
        return np.array([d])
    w = np.array([ratio ** min(i, n - 1 - i) for i in range(n)], dtype=float)
    return d * w / w.sum()


def margin_cells(rule, d, dx):
    """!
    @brief Margin around the bare cells, in cells.
    @param rule A Rule.
    @param d Gap thickness in m.
    @param dx Cell size in m.
    @return int >= 0.
    """
    if rule.margin == "none":
        return 0
    if rule.margin == "gap":
        return int(math.ceil(d / dx - 1e-9)) + 1
    if rule.margin == "2gap":
        return 2 * int(math.ceil(d / dx - 1e-9)) + 1
    return int(rule.margin)


def dilate(mask, m, shape="disc"):
    """!
    @brief Grow a boolean mask by m cells.
    @param mask Boolean array (ny, nx).
    @param m Cells (0: unchanged).
    @param shape "disc" (distance to the mask at most m), "diamond" (m times a 4-neighbour dilation) or "square" (Chebyshev distance).
    @return Boolean array.
    """
    if m <= 0 or not mask.any():
        return mask.copy()
    if shape == "disc":
        return ndimage.distance_transform_edt(~mask) <= m + 1e-9
    if shape == "diamond":
        return ndimage.binary_dilation(mask, structure=ndimage.generate_binary_structure(2, 1), iterations=m)
    if shape == "square":
        return ndimage.binary_dilation(mask, structure=np.ones((3, 3), dtype=bool), iterations=m)
    raise ValueError(shape)


def flag_cells(rule, fill_a, fill_b, d, dx, active=None):
    """!
    @brief The cells of a gap that get the nodes.
    @param rule A Rule.
    @param fill_a Copper fill (ny, nx) of the layer above the gap.
    @param fill_b Copper fill of the layer below, or None for the laminate of a one-layer board (the far side is the bottom face, which has no copper to count).
    @param d Gap thickness in m.
    @param dx Cell size in m.
    @param active Optional boolean (ny, nx) of the cells on the board; cells off the board are never flagged.
    @return Boolean array (ny, nx).
    """
    f = fill_a if fill_b is None else np.minimum(fill_a, fill_b)
    if rule.mask == "all":
        m = np.ones(f.shape, dtype=bool)
    elif rule.mask == "bare":
        m = f < rule.threshold - 1e-12
    elif rule.mask == "edge":
        # A cell next to a change of the fill of either layer (the copper edge itself): the laminate under a uniform sheet is a plain vertical resistance
        m = np.zeros(f.shape, dtype=bool)
        for g in ([fill_a] if fill_b is None else [fill_a, fill_b]):
            lo = ndimage.minimum_filter(g, size=3, mode="nearest")
            hi = ndimage.maximum_filter(g, size=3, mode="nearest")
            m |= (hi - lo) > 1e-9
        m |= f < rule.threshold - 1e-12 if rule.threshold < 1.0 else np.zeros(f.shape, dtype=bool)
    else:
        raise ValueError(rule.mask)
    m = dilate(m, margin_cells(rule, d, dx), rule.shape)
    if active is not None:
        m &= active
    return m


def unknowns(layers, cells, flagged, ns, one_layer=False):
    """!
    @brief Unknowns of the network: the program's, and those of the construction in its two forms.
    @param layers Copper layers of the board.
    @param cells Cells of the grid (nx * ny).
    @param flagged List with the number of flagged cells of every gap.
    @param ns List with n of every gap (same length).
    @param one_layer True for a one-layer board (its single gap ends at the bottom node, which every cell has).
    @return dict with program (the program's count: layers * cells; a one-layer board has the 2 laminate nodes of laminate.py, so 3 * cells), ragged (extra nodes only in the flagged
            cells), dense (extra node layers over every cell, passive cells pinned), ratio_ragged and ratio_dense against the program's count.
    """
    prog = layers * cells + (2 * cells if one_layer else 0)
    base = layers * cells + (cells if one_layer else 0)                    # the copper nodes (+ the bottom node of a one-layer board)
    ragged = base + sum((n - 1) * f for n, f in zip(ns, flagged))
    dense = base + sum((n - 1) * cells for n, f in zip(ns, flagged) if f > 0)
    return {"program": prog, "ragged": ragged, "dense": dense, "ratio_ragged": ragged / prog, "ratio_dense": dense / prog}


def with_(rule, **kw):
    """!
    @brief A copy of a rule with some fields changed.
    @param rule A Rule.
    @param kw Fields to change.
    @return Rule.
    """
    return replace(rule, **kw)
