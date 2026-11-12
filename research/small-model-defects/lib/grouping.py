#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file grouping.py
@brief Candidate rules for the grouping of vias in the Lumped model, applied to a copy of the program in memory (the program is not edited).
@details The program joins two vias when their distance is at most twice the LARGER of their nearest-neighbour distances (viaconstriction.via_groups). A via far
         from everything has a large nearest-neighbour distance, so its ball (2 d_nn) reaches the cluster and it is joined to it. The variants here change the rule:
         "min"   joins two vias when the distance is at most twice the SMALLER of the two distances (both balls must reach each other);
         "min_inf" the same, and the nearest-neighbour distance of a via that stays alone is set to infinity (as for a board with one via, the documented
                 convention of viaconstriction.nearest_neighbour), so that a lone via is the same whatever the other vias are.
         Use: with grouping.using("min_inf"): ... run the Lumped model ...
"""

import contextlib
import math

import numpy as np

from pcbthermal import viaconstriction as vc

_ORIG_INIT = vc.ViaSet.__init__


def groups_min(points, d_nn):
    """!
    @brief Single linkage with the smaller nearest-neighbour distance: i and j are joined when dist <= 2 min(d_i, d_j).
    @param points Array (n, 2) of positions in m.
    @param d_nn Nearest-neighbour distance of every via in m.
    @return numpy.ndarray (n,) of integer group labels.
    """
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    n = len(points)
    if n < 2:
        return np.zeros(n, dtype=int)
    tree = cKDTree(points)
    rows, cols = [], []
    for i, nbrs in enumerate(tree.query_ball_point(points, 2.0 * d_nn * (1.0 + 1e-12))):
        for j in nbrs:
            # Both balls must reach the other via: the ball of i is the query, the ball of j is checked here
            if j != i and math.dist(points[i], points[j]) <= 2.0 * d_nn[j] * (1.0 + 1e-12):
                rows.append(i)
                cols.append(j)
    if not rows:
        return np.arange(n)
    return connected_components(coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)), directed=False)[1]


def _patched_init(variant):
    """!
    @brief Build a ViaSet.__init__ that applies a grouping variant after the original one.
    @param variant "min" or "min_inf".
    @return function(self, problem).
    """
    def init(self, problem):
        """!
        @brief ViaSet.__init__ with the candidate grouping.
        @param self ViaSet.
        @param problem Problem.
        @return None.
        """
        _ORIG_INIT(self, problem)
        pts = np.column_stack([self.x, self.y])
        self.group = groups_min(pts, self.d_nn)
        if variant == "min_inf":
            size = np.bincount(self.group)[self.group]
            self.d_nn = np.where(size == 1, np.inf, self.d_nn)
    return init


@contextlib.contextmanager
def using(variant):
    """!
    @brief Apply a grouping variant for the duration of a with block ("program" leaves the program as it is).
    @param variant "program", "min" or "min_inf".
    @return context manager.
    """
    if variant == "program":
        yield
        return
    vc.ViaSet.__init__ = _patched_init(variant)
    try:
        yield
    finally:
        vc.ViaSet.__init__ = _ORIG_INIT
