#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cell_major.py
@brief Cell-major ordering of the unknowns before the sparse direct solve, as a function applied to a network of the program (a copy of the solve, the program is not edited).
@details The program numbers the unknowns layer by layer (index = layer * ny * nx + cell). Putting the nodes of a cell next to each other (index = cell * layers + layer)
         before spsolve changes the tie-breaking of the minimum-degree ordering and was measured by the reviewer of fix/laminate-nodes to cut a 2-layer board at 0.25 mm
         from 21.4 s and 4.5 GB to 12.7 s and 3.0 GB. The answer is the same linear system, so it must agree with the program to the round-off of the solver (test: tests/test_cell_major.py).
"""

import numpy as np
import scipy.sparse.linalg as spla

from pcbthermal.fvm import ORDERING


def cell_major_order(nl, n_cells):
    """!
    @brief Old indices listed in the cell-major order.
    @param nl Node layers of the network.
    @param n_cells Cells of the plan (ny * nx).
    @return int array of nl * n_cells old indices; entry j is the layer-major index of the j-th unknown in the new numbering.
    """
    return np.arange(nl * n_cells).reshape(nl, n_cells).T.ravel()


def solve_cell_major(net):
    """!
    @brief Steady solve of a fvm.Network (or fdm.Network) with the unknowns renumbered cell-major, the dropped laminate nodes left out as in Network.solve_steady.
    @param net Assembled network (attributes K, Q, drop, nl, ny, nx).
    @return Tuple (theta, residual) as Network.solve_steady: rise of shape (nl, ny, nx) and the relative residual.
    """
    order = cell_major_order(net.nl, net.ny * net.nx)
    q = net.Q.ravel()
    drop = net.drop.ravel() if getattr(net, "drop", None) is not None else np.zeros(q.size, dtype=bool)
    keep = order[~drop[order]]                                  # Unknowns that are solved, in the new order
    Kc = net.K.tocsr()[keep][:, keep].tocsc()                   # Symmetric permutation P K P^T
    theta = np.zeros(q.size)
    theta[keep] = spla.spsolve(Kc, q[keep], permc_spec=ORDERING)
    res = np.linalg.norm(net.K @ theta - q) / max(np.linalg.norm(q), 1e-300)
    return theta.reshape(net.nl, net.ny, net.nx), float(res)
