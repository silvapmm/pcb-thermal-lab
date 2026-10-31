#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file matrix_stats.py
@brief Size and fill-in of the assembled FVM matrix with and without the mean-potential via couplings, memory estimates, the blocks of the block SOR and the data of the spy plots.
@details The numbers recorded are counts (unknowns, non-zeros of K, non-zeros of the sparse LU factors, via blocks, dense block entries) and byte estimates derived from them
         (12 bytes per stored non-zero: an 8-byte value and a 4-byte index; the memory of the factorisation is estimated from the factor non-zeros, not measured). Timings are not
         results of this module; `time_factor` exists for the scaling check on a quiet machine only. The factorisation uses the program's own ordering (`fvm.ORDERING`).
"""

import math
import os
import sys
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "point-via-convergence", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "sor-with-via-couplings", "lib"))

import edge_patch as ep                                                     # noqa: E402
import sorvia as sv                                                         # noqa: E402
from pcbthermal import fvm                                                  # noqa: E402

BYTES_PER_NNZ = 12


def build(problem, cell_mm, treatment, **options):
    """!
    @brief The assembled FVM network of a problem with a via treatment.
    @param problem A Problem.
    @param cell_mm Target cell in mm.
    @param treatment "program" (the point via of develop, no patch) or "mw" (the recommended treatment with the options of `edge_patch`).
    @param options Options of `edge_patch.patched_edge` (board_only, fold, image, s_mode).
    @return fvm.Network with K assembled.
    @throws ValueError If the treatment is unknown.
    """
    nx = max(int(round(problem.board.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(problem.board.height * 1000.0 / cell_mm)), 2)
    if treatment == "program":
        return fvm.Network(problem, nx, ny)
    if treatment == "mw":
        with ep.patched_edge(**options):
            return fvm.Network(problem, nx, ny)
    raise ValueError(treatment)


def matrix_counts(net):
    """!
    @brief Counts of the assembled matrix and of the via blocks.
    @param net An assembled fvm.Network.
    @return dict with unknowns, nnz_K, nnz_per_row, vias, block_cells (footprint cells summed over vias), dense_entries (sum over vias of (cells x layers)^2, the entries of the
            Kron-reduced couplings), largest_footprint (cells of the biggest footprint).
    """
    K = net.K.tocsr()
    blocks = getattr(net, "_via_blocks", [])
    dense = sum((len(c) * G.shape[0]) ** 2 for c, _, G in blocks)
    return {"unknowns": K.shape[0], "nnz_K": int(K.nnz), "nnz_per_row": float(K.nnz) / K.shape[0], "vias": len(blocks), "block_cells": sum(len(c) for c, _, _ in blocks),
            "dense_entries": int(dense), "largest_footprint": max((len(c) for c, _, _ in blocks), default=0)}


def lu_fill(net, limit_nnz=None):
    """!
    @brief Non-zeros of the sparse LU factors of K with the program's ordering, and the estimated memory.
    @param net An assembled fvm.Network.
    @param limit_nnz Skip the factorisation (return None) when the matrix has more non-zeros than this (a guard for the estimate runs).
    @return dict with nnz_LU, fill_ratio (nnz_LU / nnz_K), bytes_est (12 bytes per factor non-zero), or None when skipped.
    """
    K = net.K.tocsc()
    if limit_nnz is not None and K.nnz > limit_nnz:
        return None
    lu = spla.splu(K, permc_spec=fvm.ORDERING)
    nnz = int(lu.L.nnz + lu.U.nnz)
    return {"nnz_LU": nnz, "fill_ratio": nnz / K.nnz, "bytes_est": nnz * BYTES_PER_NNZ}


def time_factor(net):
    """!
    @brief Wall time of one factorisation and solve (to be quoted only as a scaling on a quiet machine, never as a result).
    @param net An assembled fvm.Network.
    @return float seconds.
    """
    t0 = time.perf_counter()
    spla.splu(net.K.tocsc(), permc_spec=fvm.ORDERING).solve(net.Q.ravel())
    return time.perf_counter() - t0


def block_structure(net):
    """!
    @brief The via blocks of the block SOR: how many, how large after merging overlapping footprints, how many colours, the memory of the dense inverses.
    @param net An assembled fvm.Network built with a mean-potential treatment.
    @return dict with blocks, largest_block (unknowns), mean_block, inverse_entries (sum of size^2), inverse_bytes (8 bytes each), colours (greedy colouring as in `sorvia.RB`).
    """
    blocks = sv.via_blocks(net)
    if not blocks:
        return {"blocks": 0, "largest_block": 0, "mean_block": 0.0, "inverse_entries": 0, "inverse_bytes": 0, "colours": 0}
    K = net.K.tocsr()
    n = K.shape[0]
    owner = np.full(n, -1)
    for k, b in enumerate(blocks):
        owner[b] = k
    colour = [0] * len(blocks)
    for k, b in enumerate(blocks):                                           # the greedy colouring of sorvia.RB
        nb = owner[K[b].indices]
        used = {colour[j] for j in set(nb.tolist()) if 0 <= j < k}
        colour[k] = min(c for c in range(len(blocks) + 1) if c not in used)
    sizes = np.array([len(b) for b in blocks])
    return {"blocks": len(blocks), "largest_block": int(sizes.max()), "mean_block": float(sizes.mean()), "inverse_entries": int((sizes ** 2).sum()),
            "inverse_bytes": int((sizes ** 2).sum() * 8), "colours": len(set(colour))}


def spy_pattern(K, max_dim=400):
    """!
    @brief A coarse picture of the sparsity pattern: the count of non-zeros in blocks of the matrix, for imshow (the exact pattern of a large matrix cannot be drawn).
    @param K Sparse matrix.
    @param max_dim Largest side of the picture in pixels.
    @return numpy.ndarray of non-zero counts per block (log-scaled by the caller).
    """
    K = K.tocoo()
    n = K.shape[0]
    f = max(int(math.ceil(n / max_dim)), 1)
    m = int(math.ceil(n / f))
    H = np.zeros((m, m))
    np.add.at(H, (K.row // f, K.col // f), 1.0)
    return H


def estimate_dense_entries(n_vias, drill_mm, cell_mm, layers):
    """!
    @brief Rough number of dense coupling entries the via blocks add to K, to refuse a build that would not fit in memory.
    @details A footprint covers about pi (1.3 r)^2 / cell^2 cells (the disc enlarged to the target radius) but at least one; every pair of layers couples all the footprint cells of
             both layers: (cells x layers)^2 entries per via. An estimate for a guard, not a count.
    @param n_vias Number of vias.
    @param drill_mm Drill diameter in mm.
    @param cell_mm Cell in mm.
    @param layers Copper layers.
    @return float estimated entries (triplets, counting both triangles).
    """
    r = drill_mm / 2.0
    cells = max(1.0, math.pi * (1.3 * r) ** 2 / cell_mm ** 2 + 3.0)
    return n_vias * (cells * layers) ** 2


def memory_estimate_gb(n_unknowns, nnz_lu_per_unknown):
    """!
    @brief Extrapolated memory of the LU factors from a measured factor non-zeros per unknown.
    @param n_unknowns Unknowns of the target board.
    @param nnz_lu_per_unknown Factor non-zeros per unknown measured on a smaller board with the same via density.
    @return float estimate in GB.
    """
    return n_unknowns * nnz_lu_per_unknown * BYTES_PER_NNZ / 1e9


__all__ = ["build", "matrix_counts", "lu_fill", "time_factor", "block_structure", "spy_pattern", "memory_estimate_gb", "sp"]
