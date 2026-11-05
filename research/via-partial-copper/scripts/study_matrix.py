#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_matrix.py
@brief Structure of the matrix K for every via treatment: symmetry, smallest eigenvalue (positive definiteness), positive off-diagonal entries, heat balance, minimum rise.
@details On the edge, track and antipad boards of lib/cases.py (FVM, FDM, cell 0.25 mm) and on the 30 x 30 mm board of tests/test_maximum_principle.py (FVM, 0.25 mm).
         For each treatment: max |K - K^T| relative to the largest entry, the smallest eigenvalue of K (shift-invert at zero, relative to the same matrix without vias), the number
         of positive off-diagonal entries, the largest of them over the diagonal of its row, whether the row sums are consistent with the energy balance (sum of K theta = sum Q) and the
         minimum of theta. An M-matrix (no positive off-diagonal entry, symmetric positive definite) has a nonnegative inverse: no temperature below the ambient and no interior
         minimum without a sink.
         Run from the repository root: `.venv/bin/python research/via-partial-copper/scripts/study_matrix.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np                                                            # noqa: E402
import scipy.sparse.linalg as spla                                            # noqa: E402

import cases                                                                  # noqa: E402
import viavariants as vv                                                      # noqa: E402
from test_maximum_principle import copper_edge_board                          # noqa: E402


def structure(problem, model, cell):
    """!
    @brief Numbers of the matrix of a problem.
    @param problem Problem.
    @param model "fvm" or "fdm".
    @param cell Cell in mm.
    @return dict.
    """
    net = cases.network(problem, model, cell)
    K = net.K.tocsr()
    keep = np.ones(K.shape[0], dtype=bool) if net.drop is None else ~net.drop.ravel()
    K = K[keep][:, keep]
    q = net.Q.ravel()[keep]
    asym = abs(K - K.T).max() / abs(K).max()
    lam = float(spla.eigsh(K.tocsc(), k=1, sigma=0.0, which="LM", return_eigenvectors=False)[0])
    coo = K.tocoo()
    off = coo.row != coo.col
    pos = off & (coo.data > 1e-12 * abs(K.diagonal()).max())
    rel = float((coo.data[pos] / K.diagonal()[coo.row[pos]]).max()) if pos.any() else 0.0
    theta = spla.spsolve(K.tocsc(), q)
    return dict(asym=float(asym), lam_min=lam, pos=int(pos.sum()), worst=rel, min_theta=float(theta.min()), max_theta=float(theta.max()))


def main():
    """!
    @brief Print the table.
    @return None.
    """
    boards = [("edge 10mm", cases.edge(), "fvm", 0.25), ("edge 10mm", cases.edge(), "fdm", 0.25), ("track 0.4", cases.track(), "fvm", 0.25),
              ("antipad 1.0", cases.antipad(), "fvm", 0.25), ("edge 30mm test", copper_edge_board(), "fvm", 0.25)]
    print(f"{'board':16s} {'model':5s} {'variant':8s} {'asym':>9s} {'lam_min':>11s} {'lam/lam0':>9s} {'pos':>5s} {'worst':>7s} {'min theta':>10s} {'max theta':>10s}")
    for name, p, model, cell in boards:
        q = type(p)(**{k: getattr(p, k) for k in ("board", "zones", "heaters", "heatsinks", "name")})
        q.vias = []
        lam0 = structure(q, model, cell)["lam_min"]
        for variant in ("current", "sheet", "plane", "star"):
            with vv.patched(variant):
                s = structure(p, model, cell)
            print(f"{name:16s} {model:5s} {variant:8s} {s['asym']:9.1e} {s['lam_min']:11.4e} {s['lam_min'] / lam0:9.4f} {s['pos']:5d} {s['worst']:7.3f} {s['min_theta']:10.3f} {s['max_theta']:10.3f}", flush=True)


if __name__ == "__main__":
    main()
