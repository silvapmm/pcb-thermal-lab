#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_simple_stackup_review.py
@brief Review of fix/simple-stackup-physical-layers: the layered models with the old (T / L) and the new (physical) node slabs of the simple stack-up against an independent 3D solver with a cooled side wall.
@details The reference is the solver of tests/helpers/layered3d.py (copied, imports nothing of the program) extended with a film on the four side walls of every cell, copper and FR-4
         sub-slabs alike; isotropic FR-4 (0.3 W/mK in both directions, set the same in the program), h 10 W/m2K on both faces, 20 x 20 mm board 1.6 mm thick, 6 mm source of 1 W at the
         centre, mean rise of the top-copper cells under the source. The program's 'old' slabs are obtained by replacing Board.slab_thicknesses with thickness / layers for the simple
         stack-up (the code of develop before the branch). Usage from the repository root:

             .venv/bin/python releases/2.7.0/final-opinion/scripts/study_simple_stackup_review.py table 4      # 4-layer boards, cell 0.5 mm (about 3 min)
             .venv/bin/python releases/2.7.0/final-opinion/scripts/study_simple_stackup_review.py table 6      # 6-layer boards (about 5 min)
             .venv/bin/python releases/2.7.0/final-opinion/scripts/study_simple_stackup_review.py subgaps      # sub-gap sweep at 1000 W/m2K
             .venv/bin/python releases/2.7.0/final-opinion/scripts/study_simple_stackup_review.py fine         # 0.25 mm cell at 1000 W/m2K (under 2 GB)
"""

import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from pcbthermal import Problem, SolverOptions, simulate        # noqa: E402
from pcbthermal.model import Board, Materials                  # noqa: E402

K_CU, K_FR4, W_MM, H_FACE = 385.0, 0.3, 20.0, 10.0


def reference(dx, n, slabs, src, power, h_side):
    """!
    @brief Independent 3D steady rise of a laminated square board with a film on both faces and on the side walls.
    @param dx Plan cell in m.
    @param n Cells per side.
    @param slabs List of (thickness in m, conductivity number or (n, n) array in W/mK, sub-slabs) from the top down.
    @param src Source rectangle (x0, y0, x1, y1) in m on cell edges.
    @param power Power in W.
    @param h_side Side film coefficient in W/m2K (0: insulated).
    @return float Mean rise of the top cells under the source in K.
    """
    dz, kz = [], []
    for t, k, m in slabs:
        dz += [t / m] * m
        kz += [np.broadcast_to(np.asarray(k, float), (n, n))] * m
    dz, kz = np.array(dz), np.array(kz)
    nz = len(dz)
    N = nz * n * n
    idx = np.arange(N).reshape(nz, n, n)
    xs = (np.arange(n) + 0.5) * dx
    mask = (xs[None] > src[0]) & (xs[None] < src[2]) & (xs[:, None] > src[1]) & (xs[:, None] < src[3])
    R, C, V = [], [], []
    diag = np.zeros(N)
    A = dx * dx

    def link(a, b, g):
        """!
        @brief Add a symmetric conductance between two node arrays.
        @param a Node indices.
        @param b Node indices.
        @param g Conductance in W/K.
        @return None.
        """
        g = np.broadcast_to(g, a.shape)
        R.extend([a.ravel(), b.ravel()]); C.extend([b.ravel(), a.ravel()]); V.extend([-g.ravel(), -g.ravel()])
        np.add.at(diag, a.ravel(), g.ravel()); np.add.at(diag, b.ravel(), g.ravel())

    for k in range(nz):                                         # in-plane: harmonic mean of two half cells
        a, b = kz[k][:, :-1], kz[k][:, 1:]
        link(idx[k, :, :-1], idx[k, :, 1:], dz[k] * 2 * a * b / (a + b))
        a, b = kz[k][:-1], kz[k][1:]
        link(idx[k, :-1], idx[k, 1:], dz[k] * 2 * a * b / (a + b))
    for k in range(nz - 1):                                     # vertical: two half cells in series
        link(idx[k], idx[k + 1], 1 / (dz[k] / (2 * kz[k] * A) + dz[k + 1] / (2 * kz[k + 1] * A)))
    if h_side:
        for k in range(nz):                                     # side film behind half a cell of the slab's own conductivity
            for sl in [(slice(None), 0), (slice(None), -1), (0, slice(None)), (-1, slice(None))]:
                g = 1 / (1 / (2 * kz[k][sl] * dz[k]) + 1 / (h_side * dz[k] * dx))
                np.add.at(diag, idx[k][sl].ravel(), np.broadcast_to(g, idx[k][sl].shape).ravel())
    rt, rb = dz[0] / (2 * kz[0] * A), dz[-1] / (2 * kz[-1] * A)
    np.add.at(diag, idx[0].ravel(), (1 / (rt + 1 / (H_FACE * A))).ravel())
    np.add.at(diag, idx[-1].ravel(), (1 / (rb + 1 / (H_FACE * A))).ravel())
    q = np.zeros(N)
    qc = np.where(mask, power / mask.sum(), 0.0)
    q[idx[0].ravel()] = (qc / (1 + H_FACE * A * rt)).ravel()   # the film acts under the source too, as in the program
    K = sp.coo_matrix((np.concatenate(V), (np.concatenate(R), np.concatenate(C))), shape=(N, N)).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), q).reshape(nz, n, n)
    return float(T[0][mask].mean())


def build(cu, pattern, h_side):
    """!
    @brief The program's board: simple stack-up, 1.6 mm, copper per layer and pattern per layer.
    @param cu Copper thickness per layer in um.
    @param pattern Per layer 'full', 'pad' (8 mm square at the centre) or 'none'.
    @param h_side Edge coefficient in W/m2K or None.
    @return Problem.
    """
    mat = Materials(k_copper=K_CU, k_fr4_through=K_FR4, k_fr4_inplane=K_FR4)
    p = Problem.new(W_MM, W_MM, layers=len(cu), thickness_mm=1.6, copper_um=35, ambient=0.0, h_top=H_FACE, h_bottom=H_FACE, h_side=h_side, materials=mat)
    p.board.copper_thickness = [c * 1e-6 for c in cu]
    c = W_MM / 2
    for layer, pat in enumerate(pattern, start=1):
        if pat == "full":
            p.add_zone(layer, rect=(0, 0, W_MM, W_MM))
        elif pat == "pad":
            p.add_zone(layer, rect=(c - 4, c - 4, c + 4, c + 4))
    p.add_heater(1, 1.0, rect=(c - 3, c - 3, c + 3, c + 3), name="U")
    return p


def program(p, cell, model, old, n_max=None):
    """!
    @brief Mean rise under the source in one model, with the old or the new node slabs.
    @param p Problem.
    @param cell Cell in mm.
    @param model Model key.
    @param old True: the simple stack-up gives every node thickness / layers (the code before the branch).
    @param n_max Sub-gaps (with s_max 0.05 mm), or None for the defaults.
    @return float Rise in K.
    """
    new = Board.slab_thicknesses

    def legacy(self):
        """!
        @brief The old slab rule.
        @return Array of slabs in m.
        """
        return np.full(self.layers, self.thickness / self.layers) if self.dielectrics is None else new(self)
    if old:
        Board.slab_thicknesses = legacy
    try:
        kw = {} if n_max is None else {"laminate_n_max": n_max, "laminate_s_max_mm": 0.05}
        T = np.asarray(simulate(p, SolverOptions(models=(model,), cell_mm=cell, **kw)).results[model].T)[0]
    finally:
        Board.slab_thicknesses = new
    ny, nx = T.shape
    xs = (np.arange(nx) + 0.5) * W_MM / nx
    m = (np.abs(xs[None] - W_MM / 2) < 3) & (np.abs(xs[:, None] - W_MM / 2) < 3)
    return float(T[m].mean())


def case(cu, pattern, h_side, cell=0.5, models=("fvm",), n_max=None):
    """!
    @brief One board: the reference and the error of every model, old and new slabs.
    @param cu Copper per layer in um.
    @param pattern Copper pattern per layer.
    @param h_side Edge coefficient in W/m2K or None.
    @param cell Cell in mm (the reference uses the same plan cell).
    @param models Model keys.
    @param n_max Sub-gaps of the program, or None.
    @return dict with the reference rise and (old %, new %) per model.
    """
    p = build(cu, pattern, h_side)
    gaps = p.board.gap_thicknesses()
    dx, n, c = cell * 1e-3, int(round(W_MM / cell)), W_MM / 2 * 1e-3
    xs = (np.arange(n) + 0.5) * dx
    pad = (np.abs(xs[None] - c) < 4e-3) & (np.abs(xs[:, None] - c) < 4e-3)
    slabs = []
    for layer, pat in enumerate(pattern):
        k = K_CU if pat == "full" else (np.where(pad, K_CU, K_FR4) if pat == "pad" else K_FR4)
        slabs.append((cu[layer] * 1e-6, k, 1))
        if layer < len(cu) - 1:
            slabs.append((float(gaps[layer]), K_FR4, 8))
    r = reference(dx, n, slabs, (c - 3e-3, c - 3e-3, c + 3e-3, c + 3e-3), 1.0, h_side or 0.0)
    out = {"cu": cu, "pattern": pattern, "h_side": h_side, "cell": cell, "n_max": n_max, "ref": round(r, 4)}
    for m in models:
        out[m] = tuple(round(100 * (program(p, cell, m, old, n_max) / r - 1), 2) for old in (True, False))
    return out


def main(argv):
    """!
    @brief Run one part of the review and print one JSON line per board.
    @param argv Arguments: 'table 4', 'table 6', 'subgaps' or 'fine'.
    @return int exit code.
    """
    if argv[0] == "table":
        sets = {"4": [[35] * 4, [35, 17.5, 17.5, 35], [35, 70, 70, 35]], "6": [[35] * 6, [35, 17.5, 17.5, 17.5, 17.5, 35]]}[argv[1]]
        for cu in sets:
            L = len(cu)
            pats = [["pad"] + ["full"] * (L - 2) + ["none"], ["full"] * L] + ([["pad", "none", "none", "pad"]] if L == 4 else [])
            for pat in pats:
                for hs in (None, 50.0, 1000.0):
                    print(json.dumps(case(cu, pat, hs, models=("fvm", "fdm", "lumped", "analytic"))), flush=True)
    elif argv[0] == "subgaps":
        for pat in (["pad", "full", "full", "none"], ["full"] * 4):
            for nm in (4, 8, 16):
                print(json.dumps(case([35] * 4, pat, 1000.0, n_max=nm)), flush=True)
    elif argv[0] == "fine":
        for cu, pat in (([35] * 4, ["full"] * 4), ([35] * 4, ["pad", "full", "full", "none"]), ([35] * 6, ["full"] * 6)):
            print(json.dumps(case(cu, pat, 1000.0, cell=0.25, models=("fvm", "fdm"))), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
