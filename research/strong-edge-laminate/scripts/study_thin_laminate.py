#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_thin_laminate.py
@brief How cool does the layered FVM read a 10 x 10 mm board with a strongly cooled edge when the laminate gaps are thin (below the 0.4 mm of the sub-gap rule, so none is cut)?
@details Question: the edge-laminate warning is silent when no gap is cut (6 layers in 1.6 mm); what is the error there, against the finest program value and against an independent
         3D finite-volume reference written in this file (physical slabs, edge film on every slab wall, imports nothing of pcbthermal)? Boards: 2, 4, 6 and 8 copper layers of 35 um,
         total 1.0 to 2.4 mm, full copper or a pad on the outer layers (inner layers full), a 0.5 W 3 x 2 mm part on the top layer, h_top 10, h_bottom 200 W/m2K, h_side 200 to 2000.
         The program is run with an advanced stack-up (physical slabs) and `n` laminate sub-gaps per gap (n = None is the shipped rule, one node where the gap is under 0.4 mm).
         Run from the repository root: `.venv/bin/python research/strong-edge-laminate/scripts/study_thin_laminate.py [quick]`; results are cached in the file given by the
         environment variable THIN_OUT (default out/thin_cache.jsonl of this folder, git-ignored).
"""

import json
import logging
import os
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(ROOT))
sys.path.append(REPO)

from pcbthermal import Problem, SolverOptions, simulate          # noqa: E402
from pcbthermal import model as pmodel                           # noqa: E402
from pcbthermal.model import Materials                           # noqa: E402

logging.disable(logging.WARNING)
W = 10e-3                                         # board side in m
KCU, KFR, TCU = 385.0, 0.3, 35e-6                 # conductivities in W/mK, copper thickness in m
HTOP, HBOT, POWER = 10.0, 200.0, 0.5              # face coefficients in W/m2K, source in W
SRC = (1e-3, 4e-3, 4e-3, 6e-3)                    # source x0 y0 x1 y1 in m
PAD = (0.5e-3, 3e-3, 5.5e-3, 7e-3)                # outer-layer copper pad in the 'pad' variant, m
CACHE = os.environ.get("THIN_OUT", os.path.join(ROOT, "out", "thin_cache.jsonl"))


def ref(L, total, h_side, variant, dx, n_sub):
    """!
    @brief Independent 3D reference rise of the board (half domain, plane y = W/2 symmetric).
    @param L Copper layers.
    @param total Board thickness in m.
    @param h_side Edge film coefficient in W/m2K (acts on the walls x = 0, x = W and y = 0 of every slab).
    @param variant 'full' (copper everywhere) or 'pad' (outer layers only inside PAD, inner full).
    @param dx Plan cell in m (divides W/2).
    @param n_sub Sub-slabs per gap.
    @return dict tmax (K, hottest top-layer cell centre), balance (loss over power), n (unknowns).
    """
    gap = (total - L * TCU) / (L - 1)
    nx, ny = int(round(W / dx)), int(round(W / dx / 2))
    dz, kind = [], []
    for l in range(L):
        dz.append(TCU)
        kind.append(l)
        if l < L - 1:
            dz += [gap / n_sub] * n_sub
            kind += [-1] * n_sub
    nz = len(dz)
    xs, ys = (np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx
    pad = (xs[None, :] > PAD[0]) & (xs[None, :] < PAD[2]) & (ys[:, None] > PAD[1])
    k3 = np.empty((nz, ny, nx))
    for z, kd in enumerate(kind):
        if kd < 0:
            k3[z] = KFR
        elif variant == "pad" and kd in (0, L - 1):
            k3[z] = np.where(pad, KCU, KFR)
        else:
            k3[z] = KCU
    idx = np.arange(nz * ny * nx).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag, gamb, rhs = np.zeros(idx.size), np.zeros(idx.size), np.zeros(idx.size)

    def link(a, b, g):
        g = np.broadcast_to(g, a.shape)
        rows.extend([a.ravel(), b.ravel()])
        cols.extend([b.ravel(), a.ravel()])
        vals.extend([-g.ravel(), -g.ravel()])
        diag[a.ravel()] += g.ravel()
        diag[b.ravel()] += g.ravel()

    def harm(a, b):
        return 2 * a * b / (a + b)

    for z in range(nz):
        kz = k3[z]
        link(idx[z, :, :-1], idx[z, :, 1:], harm(kz[:, :-1], kz[:, 1:]) * dz[z])
        link(idx[z, :-1, :], idx[z, 1:, :], harm(kz[:-1, :], kz[1:, :]) * dz[z])
        gf = h_side * dz[z] * dx
        for sel, kk in ((idx[z, :, 0], kz[:, 0]), (idx[z, :, -1], kz[:, -1]), (idx[z, 0, :], kz[0, :])):
            g = 1.0 / (1.0 / (kk * dz[z] * 2.0) + 1.0 / gf)    # half-cell conduction in series with the film
            diag[sel] += g
            gamb[sel] += g
    a = dx * dx
    for z in range(nz - 1):
        link(idx[z], idx[z + 1], 1.0 / (dz[z] / (2 * k3[z] * a) + dz[z + 1] / (2 * k3[z + 1] * a)))
    for z, h in ((0, HTOP), (nz - 1, HBOT)):
        g = 1.0 / (1.0 / (h * a) + dz[z] / (2 * k3[z] * a))
        diag[idx[z].ravel()] += g.ravel()
        gamb[idx[z].ravel()] += g.ravel()
    m = (xs[None, :] > SRC[0]) & (xs[None, :] < SRC[2]) & (ys[:, None] > SRC[1]) & (ys[:, None] < SRC[3])
    rhs[idx[0][m]] += 0.5 * POWER / m.sum()
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(idx.size,) * 2) + sp.diags(diag)
    T = spla.splu(A.tocsc(), permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0, options=dict(SymmetricMode=True)).solve(rhs)
    return {"tmax": float(T[idx[0].ravel()].max()), "balance": float((gamb * T).sum() / (0.5 * POWER)), "n": int(idx.size)}


def prog(L, total, h_side, variant, cell_mm, n_sub):
    """!
    @brief Hottest rise of the program's FVM on the same board with an advanced stack-up (physical slabs).
    @param L Copper layers.
    @param total Board thickness in m.
    @param h_side Edge coefficient in W/m2K.
    @param variant 'full' or 'pad'.
    @param cell_mm Cell in mm.
    @param n_sub Sub-gaps per gap (None: the shipped rule).
    @return float rise in K.
    """
    pmodel.reload_libraries()
    w = W * 1e3
    p = Problem.new(w, w, L, total * 1e3, 35.0, h_top=HTOP, h_bottom=HBOT, h_side=h_side, materials=Materials(k_fr4_inplane=KFR))
    p.board.make_advanced()
    for layer in range(1, L + 1):
        if variant == "pad" and layer in (1, L):
            p.add_zone(layer, rect=(PAD[0] * 1e3, PAD[1] * 1e3, PAD[2] * 1e3, PAD[3] * 1e3))
        else:
            p.add_zone(layer, rect=(0, 0, w, w))
    p.add_heater(1, POWER, rect=(1, 4, 4, 6))
    opts = SolverOptions(models=("fvm",), cell_mm=cell_mm)
    if n_sub is not None:
        s = (total * 1e3 - L * 0.035) / (L - 1) / n_sub * 1.001 * 1e-3    # ceil(d / s) = n_sub
        opts.laminate_params = lambda: (s, int(n_sub))
    return float(simulate(p, opts).results["fvm"].t_max - p.board.ambient)


def cached(kind, args, fn):
    """!
    @brief One result from the JSON-lines cache or computed.
    @param kind 'ref' or 'prog'.
    @param args List of the arguments (JSON-able).
    @param fn Function called with *args.
    @return The value.
    """
    key = kind + json.dumps(args)
    if not hasattr(cached, "db"):
        cached.db = {}
        if os.path.exists(CACHE):
            for line in open(CACHE):
                r = json.loads(line)
                cached.db[r["key"]] = r["val"]
    if key not in cached.db:
        val = fn(*args)
        cached.db[key] = val
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "a") as f:
            f.write(json.dumps({"key": key, "val": val}) + "\n")
    return cached.db[key]


def main():
    """!
    @brief Run the cases and print one line per board and edge coefficient: the 3D reference at its refinements, the program's finest value and the shipped rule against it.
    @return None.
    """
    cases = [("full", 2, 1.0e-3, (200, 500, 1000, 2000)), ("full", 4, 1.0e-3, (200, 500, 1000, 2000)), ("full", 4, 1.6e-3, (200, 500, 1000, 2000)),
             ("full", 6, 1.6e-3, (200, 500, 1000, 2000)), ("full", 6, 1.0e-3, (200, 1000, 2000)), ("full", 6, 2.4e-3, (200, 1000, 2000)),
             ("full", 8, 1.0e-3, (200, 1000, 2000)), ("full", 8, 1.6e-3, (200, 1000, 2000)),
             ("pad", 4, 1.6e-3, (200, 1000, 2000)), ("pad", 6, 1.6e-3, (200, 1000, 2000)), ("pad", 8, 1.0e-3, (200, 1000, 2000))]
    for variant, L, total, hs in cases:
        gap = (total - L * TCU) / (L - 1) * 1e3
        for h in hs:
            R = {}
            for dx, ns in ((0.25e-3, 8), (0.25e-3, 16), (0.125e-3, 8)):
                if ns == 16 and h != 1000:
                    continue                # the sub-slab convergence is shown at one edge coefficient only (cost)
                if dx < 0.2e-3 and L >= 8 and h != 1000:
                    continue                # the finest reference of the 8-layer boards at one edge coefficient only (cost)
                R[(dx, ns)] = cached("ref", [L, total, h, variant, dx, ns], ref)["tmax"]
            fine = cached("prog", [L, total, h, variant, 0.125, 8], prog)
            row = {(c, n): cached("prog", [L, total, h, variant, c, n], prog) for c in (0.5, 0.25) for n in (None, 2, 8)}
            r_best = R[(0.125e-3, 8)] if (0.125e-3, 8) in R else R[(0.25e-3, 8)]
            print(f"{variant} L={L} T={total * 1e3:.1f} gap={gap:.3f} h={h}: ref " + " ".join(f"{k[0] * 1e3:g}/{k[1]}:{v:.3f}" for k, v in R.items())
                  + f" | prog0.125/8 {fine:.3f} ({(fine / r_best - 1) * 100:+.1f}% of ref) | "
                  + " ".join(f"c{c:g}n{n}:{v:.3f}({(v / fine - 1) * 100:+.1f})" for (c, n), v in row.items()), flush=True)


if __name__ == "__main__":
    main()
