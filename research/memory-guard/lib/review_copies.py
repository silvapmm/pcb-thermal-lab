#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file review_copies.py
@brief Copies of two program paths with a smaller memory footprint, measured by the review (README, chapter Review); the program is not edited.
@details (1) `transient_from_network_one_factor`: `fvm.transient_from_network` keeps the LU factor of every distinct time step in a dictionary (ten in the logarithmic
         mode of the animation), although the steps come stage after stage and an old factor is never used again; the copy keeps one. (2) `sor_inverse_program` and
         `sor_inverse_dense`: the block inverse of the block SOR as the program builds it (dense inverse turned into a CSR matrix and a block diagonal) and kept dense.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from pcbthermal.fvm import ORDERING, TransientResult, mean_weights


def transient_from_network_one_factor(net, ambient, t_end, n_out=40, substeps=4, theta_scheme=1.0, log_times=True, grid="cells"):
    """!
    @brief Copy of `fvm.transient_from_network` that keeps only the factor of the current time step (the steps of a stage are equal and the stages never come back).
    @param net The network (K, C, Q, nl, ny, nx, solve_steady()).
    @param ambient Ambient temperature in degC.
    @param t_end Final time in s.
    @param n_out Output frames (excluding t = 0).
    @param substeps Implicit steps between two frames (linear mode).
    @param theta_scheme 1.0 implicit Euler, 0.5 Crank-Nicolson.
    @param log_times True for the doubling time step.
    @param grid "cells" or "nodes".
    @return TransientResult, identical to the program's.
    """
    ny, nx = net.ny, net.nx
    nb = getattr(net, "n_board", net.nl)
    steady_theta, _ = net.solve_steady()
    weights = mean_weights(net)
    # Same time grid as the program
    if log_times:
        stages = 10
        per_stage = max(int(np.ceil(n_out / stages)), 1)
        dt0 = t_end / (per_stage * (2 ** stages - 1))
        dts = np.concatenate([np.full(per_stage, dt0 * 2.0 ** j) for j in range(stages)])
    else:
        dts = np.full(max(n_out, 1) * max(substeps, 1), t_end / (max(n_out, 1) * max(substeps, 1)))
    step_times = np.concatenate([[0.0], np.cumsum(dts)])
    step_times[-1] = t_end
    keep = np.arange(len(step_times)) if log_times else np.arange(0, len(step_times), max(substeps, 1))
    times = step_times[keep]
    N = net.nl * ny * nx
    Cd = net.C.ravel()
    q = net.Q.ravel()
    x = np.zeros(N)
    frames = {0: x.reshape(net.nl, ny, nx)[:nb] + ambient}
    current_key, lu, B = None, None, None
    kept = set(keep.tolist())
    for k, dt in enumerate(dts, start=1):
        key = round(float(dt), 12)
        if key != current_key:
            # The only change from the program: drop the old factor before making the new one (it is never used again)
            lu = B = None
            A = (sp.diags(Cd / dt) + theta_scheme * net.K).tocsc()
            B = (sp.diags(Cd / dt) - (1.0 - theta_scheme) * net.K).tocsr()
            lu, current_key = spla.splu(A, permc_spec=ORDERING), key
        x = lu.solve(B @ x + q)
        if k in kept:
            frames[k] = x.reshape(net.nl, ny, nx)[:nb] + ambient
    frames = np.asarray([frames[k] for k in keep])
    inside = weights > 0
    return TransientResult(
        times=times, t_max=frames[:, :, inside].reshape(len(times), -1).max(axis=1),
        t_mean=(frames * weights).sum(axis=(1, 2, 3)) / (nb * weights.sum()), frames=frames,
        steady_t_max=float(steady_theta[:nb].max() + ambient), ambient=ambient, grid=grid,
    )


def sor_inverse_program(block):
    """!
    @brief The block inverse as `fvm.Network._sor_block_groups` builds it: dense inverse, CSR of every entry, block diagonal.
    @param block Sparse SPD block (n x n).
    @return CSR matrix holding the n^2 entries of the inverse.
    """
    inv = [np.linalg.inv(block.toarray())]
    return sp.block_diag([sp.csr_matrix(m) for m in inv], format="csr")


def sor_inverse_dense(block):
    """!
    @brief The block inverse kept as a dense array (what a dense product in the SOR step would use).
    @param block Sparse SPD block (n x n).
    @return Dense n x n inverse.
    """
    return np.linalg.inv(block.toarray())
