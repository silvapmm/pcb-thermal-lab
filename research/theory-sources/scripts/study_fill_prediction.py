#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fill_prediction.py
@brief Can the fill of the program's sparse LU factor be predicted exactly before the numeric factorisation?

Question: the SuperLU guide (section 1.4.4) says that the nonzeros of L and U cannot be determined before the numeric
factorisation when the row and column permutations are not known.  The program factorises with the symmetric ordering
`fvm.ORDERING` ("MMD_AT_PLUS_A").  If no row pivot is taken, the pattern of L is that of the Cholesky factor of the
permuted matrix, which Gilbert, Ng and Peyton (1994) show is computable from the pattern alone.  This script checks, on
the FVM, FDM and 3D-solid matrices of the three example boards: (1) that `splu` takes no row pivot (perm_r == perm_c);
(2) that `lu.L.nnz` equals the symbolic Cholesky count in the elimination order of `perm_c`; (3) that `spilu` with an
infinite drop tolerance (memory of K only) returns the same `perm_c`, so the ordering is available before factorising.

Run (from the repository root, about 30 s):  .venv/bin/python research/theory-sources/scripts/study_fill_prediction.py
"""
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from pcbthermal import fdm, fvm, solid3d  # noqa: E402
from pcbthermal.model import load_problem  # noqa: E402


def cholesky_count(a, order) -> int:
    """!
    @brief Number of nonzeros (diagonal included) of the Cholesky factor of a symmetric pattern in a given elimination order.

    @param a     Square sparse matrix (its pattern is symmetrised).
    @param order Elimination order: order[k] is the original index of the k-th eliminated unknown.

    @return int nnz(L) of the lower factor.
    @note Elimination tree by Liu's algorithm with path compression, then the row subtrees (each row i marks the tree path from
          every j < i of its pattern up to i). Cost O(nnz(L)) in pure Python; the almost-linear column counts of Gilbert, Ng and
          Peyton would be the production method.
    """
    b = sp.csr_matrix(a)[order][:, order]
    b = (abs(b) + abs(b.T)).tocsr()  # symmetric pattern
    n = b.shape[0]
    parent = -np.ones(n, dtype=int)
    anc = -np.ones(n, dtype=int)
    for i in range(n):
        for j in b.indices[b.indptr[i]:b.indptr[i + 1]]:
            if j >= i:
                continue
            r = j
            # climb to the current root, compressing the path to i
            while anc[r] != -1 and anc[r] != i:
                t = anc[r]
                anc[r] = i
                r = t
            if anc[r] == -1:
                anc[r] = i
                parent[r] = i
    mark = -np.ones(n, dtype=int)
    count = n  # the diagonal
    for i in range(n):
        mark[i] = i
        for j in b.indices[b.indptr[i]:b.indptr[i + 1]]:
            # every node on the tree path from j to i is a nonzero of row i of L
            while j < i and mark[j] != i:
                mark[j] = i
                count += 1
                j = parent[j]
    return count


def check(name: str, k) -> bool:
    """!
    @brief Compare the fill of splu with the prediction (spilu ordering + symbolic count) for one matrix and print one line.

    @param name Label of the matrix.
    @param k    Sparse matrix of the network.

    @return bool True when the prediction equals lu.L.nnz and no row pivot was taken.
    """
    k = k.tocsc()
    t0 = time.time()
    ilu = spla.spilu(k, permc_spec=fvm.ORDERING, drop_tol=1e10, fill_factor=1)  # ordering only (memory of K)
    t_order = time.time() - t0
    predicted = cholesky_count(k, np.argsort(ilu.perm_c))
    t0 = time.time()
    lu = spla.splu(k, permc_spec=fvm.ORDERING)
    t_lu = time.time() - t0
    same_order = np.array_equal(ilu.perm_c, lu.perm_c)
    no_pivot = np.array_equal(lu.perm_r, lu.perm_c)
    ok = same_order and no_pivot and lu.L.nnz == predicted
    print("%-26s n=%7d  splu nnz(L)=%9d  predicted=%9d  same order=%s  no pivot=%s  t(order)=%.2f s  t(splu)=%.2f s"
          % (name, k.shape[0], lu.L.nnz, predicted, same_order, no_pivot, t_order, t_lu))
    return ok


def main() -> None:
    """!
    @brief Run the check on the FVM (0.5 mm), FDM (1 mm) and 3D solid (2 mm) of the three example boards.

    @return None
    """
    results = []
    for name in ("example_board", "reference_board", "profile_board"):
        prob = load_problem(ROOT / "examples" / ("%s.pcbt.json" % name))
        b = prob.board
        nx, ny = int(round(b.width * 1000.0 / 0.5)), int(round(b.height * 1000.0 / 0.5))
        results.append(check(name + " FVM 0.5 mm", fvm.Network(prob, nx, ny).K))
        results.append(check(name + " FDM 1 mm", fdm.Network(prob, 1.0).K))
        results.append(check(name + " 3D 2 mm", solid3d.Solid(prob, 2.0).K))
    print("all equal: %s (%d matrices)" % (all(results), len(results)))


if __name__ == "__main__":
    main()
