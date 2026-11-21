#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_memory_prototype.py
@brief Measurement of the review of DESIGN.md (section 4): peak memory, time and CG iterations of a PROTOTYPE FEM step response against the steady FEM, on one mesh.
@details Not the program's transient (it does not exist yet) and not the law of the branch: a prototype built from the program's own pieces (`femmesh.build`, `Model.assemble`, the
         solver settings of `Model.solve`) plus a consistent mass assembled after `A` (one more element loop, a uniform rho c of 1.7e6 J/m3K: the value does not change the memory),
         then eleven step sizes of four Crank-Nicolson steps each (0.06 s doubling to 128 s, about the grid of DESIGN.md 3), one factor or one pyamg hierarchy alive, the old one freed
         before the next, warm-started CG at the steady tolerance 1e-10. One case per fresh process (the peak `ru_maxrss` minus the resident size after the imports, as
         `releases/2.8.0/fem-model/scripts/measure_fem_law.py`). Heavy for a review script: the direct case holds about 2.1 GB and the CG case runs about 3 minutes on the example board
         at 2 mm (67 229 unknowns); run one at a time on a quiet machine. Usage, from the repository root:
         `.venv/bin/python releases/2.9.0/fem-transient/scripts/check_memory_prototype.py {steady|transient} {cg|direct} [cell_mm]`.
"""
import os
import resource
import sys
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..")
sys.path.insert(0, ROOT)
from pcbthermal import femcore, femmesh, memory, project      # noqa: E402

STEPS = (0.06, 0.24, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0)    # step sizes of the stages (s)
PER_STAGE = 4


def peak_bytes():
    """!
    @brief Peak resident size of this process.
    @return int Bytes.
    """
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)


def mass(model, used, n):
    """!
    @brief Consistent mass on the used nodes, assembled after A by one more element loop (2 x 2 x 2 Gauss rule, chunks of 20 000 elements, as the stiffness).
    @param model femcore.Model.
    @param used Boolean (N,) of the used nodes from `Model.assemble`.
    @param n Number of used nodes.
    @return scipy.sparse.csc_matrix (n, n) in J/K.
    """
    remap = np.cumsum(used) - 1
    rho_c = np.full(model.elems.shape[0], 1.7e6)
    rows, cols, vals = [], [], []
    g = femcore.G1
    for s in range(0, model.elems.shape[0], 20000):
        el = model.elems[s:s + 20000]
        X = model.nodes[el]
        me = np.zeros((el.shape[0], 8, 8))
        for gx in (-g, g):
            for gy in (-g, g):
                for gz in (-g, g):
                    nn, dn = femcore.shape(gx, gy, gz)
                    det = np.abs(np.linalg.det(np.einsum("eai,aj->eij", X, dn)))
                    me += (rho_c[s:s + 20000] * det)[:, None, None] * np.outer(nn, nn)[None]
        rows.append(remap[np.repeat(el, 8, axis=1)].ravel())
        cols.append(remap[np.tile(el, (1, 8))].ravel())
        vals.append(me.ravel())
    return sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()


def transient(model, solver):
    """!
    @brief The prototype step response: eleven stages of four Crank-Nicolson steps, one factor or hierarchy alive.
    @param model femcore.Model.
    @param solver 'direct' or 'cg'.
    @return tuple (unknowns, list of CG iterations per step, empty for the direct path).
    """
    a = model.assemble()
    A, rhs, used = a["A"], a["rhs"], a["used"]
    del a
    n = rhs.size
    M = mass(model, used, n)
    T, its = np.zeros(n), []
    for dt in STEPS:
        B = (M / dt + 0.5 * A).tocsc()
        lu = ml = P = None
        if solver == "direct":
            lu = spla.splu(B, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0, options=dict(SymmetricMode=True))
        else:
            ml = femcore._import_pyamg().smoothed_aggregation_solver(B.tocsr(), symmetry="symmetric", strength=("symmetric", {"theta": 0.0}), max_coarse=200)
            P = ml.aspreconditioner(cycle="V")
        for _ in range(PER_STAGE):
            b = M @ T / dt - 0.5 * (A @ T) + rhs
            if lu is not None:
                T = lu.solve(b)
            else:
                count = [0]
                T, _ = spla.cg(B, b, x0=T, rtol=1e-10, maxiter=5000, M=P, callback=lambda x: count.__setitem__(0, count[0] + 1))
                its.append(count[0])
        del lu, ml, P, B                                              # the old factor or hierarchy is freed before the next is built
    return n, its


def main():
    """!
    @brief Run one case and print the unknowns, the growth of the peak resident size, the bytes per unknown, the seconds and the CG iterations.
    @return None.
    """
    mode, solver = sys.argv[1], sys.argv[2]
    cell = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    p = project.load_project(os.path.join(ROOT, "examples", "example_board.pcbt.json"))
    p = getattr(p, "problem", p)
    start = memory.resident_bytes()
    mesh = femmesh.build(p, cell)
    t0 = time.time()
    if mode == "steady":
        n, its = mesh.model.solve(force=solver)["n"], []
    else:
        n, its = transient(mesh.model, solver)
    grown = peak_bytes() - start
    print(f"{mode} {solver} cell {cell} mm: unknowns {n}, peak growth {grown / 1e6:.1f} MB, {grown / n:.0f} B per unknown, {time.time() - t0:.1f} s"
          + (f", CG iterations per step {its}" if its else ""))


if __name__ == "__main__":
    main()
