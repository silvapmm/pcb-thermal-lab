#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file outline_prune.py
@brief Prototype: the board outline of a mechanical layer that also draws stubs, dimension marks or doubled lines.
@details The program's `outline_from_layer` chains the dark strokes and refuses a contour in which a joint does not connect
         exactly two segments.  Several tools draw more than the profile on the layer they send as outline (Altium's mechanical
         layer 1, EasyEDA's board-outline layer, Target 3001's outline, CAM350 re-exports).  This prototype, for the proposal of
         `INTEGRATION.md` 4, removes duplicated segments and then dangling segments (an end that touches nothing) until none is
         left, and chains what remains with the program's own `chain_segments`.  It reads the strokes with the program's parser
         and changes nothing in the program.
"""
import math
from collections import defaultdict
from typing import List, Tuple

import numpy as np

from pcbthermal.gerber import outline as O
from pcbthermal.gerber.errors import OutlineError


def strokes_of(layer) -> List[Tuple[float, float, float, float]]:
    """!
    @brief The dark strokes of a parsed layer as segments (x0, y0, x1, y1) in mm, zero-length ones dropped.
    @param layer  Parsed Layer.
    @return list Segments.
    """
    segs = []
    for kind, dark, a in layer.ops:
        if dark and kind == "stroke" and math.hypot(a[3] - a[1], a[4] - a[2]) > 1e-9:
            segs.append((a[1], a[2], a[3], a[4]))
    return segs


def prune(segs, tol_mm=0.01):
    """!
    @brief Remove duplicate and dangling segments.
    @param segs    Segments (x0, y0, x1, y1).
    @param tol_mm  Endpoints closer than this are the same node.
    @return tuple (kept segments, number of duplicates removed, number of dangling segments removed).
    """
    def key(x, y):
        return (round(x / tol_mm), round(y / tol_mm))

    seen, uniq, dup = set(), [], 0
    for s in segs:
        k = tuple(sorted((key(s[0], s[1]), key(s[2], s[3]))))
        if k in seen or k[0] == k[1]:
            dup += 1
            continue
        seen.add(k)
        uniq.append(s)
    dangling = 0
    while True:
        deg = defaultdict(int)
        for s in uniq:
            deg[key(s[0], s[1])] += 1
            deg[key(s[2], s[3])] += 1
        keep = [s for s in uniq if deg[key(s[0], s[1])] > 1 and deg[key(s[2], s[3])] > 1]
        if len(keep) == len(uniq):
            break
        dangling += len(uniq) - len(keep)
        uniq = keep
    return uniq, dup, dangling


def outline_pruned(layer, tol_mm=0.01):
    """!
    @brief Outline of a layer after pruning; raises the program's OutlineError when still not closed.
    @param layer   Parsed Layer.
    @param tol_mm  Join tolerance in mm.
    @return tuple (list of (n,2) arrays of the loops, duplicates removed, dangling removed).
    """
    segs, dup, dang = prune(strokes_of(layer), tol_mm)
    if not segs:
        raise OutlineError("nothing left after pruning")
    loops = O.chain_segments(np.array(segs, float), tol_mm, layer.name)
    return loops, dup, dang
