#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review.py
@brief Review check, independent of the program and of `lib/`: does block SOR converge on boards beyond those of the study, and why (the energy argument)?
@details Own layered matrix (five-point and vertical stencil, ambient on the outer faces) with own mean-potential via couplings
         (area weights of a disc, a barrel chain between the layer means, `K_via = sum B^T G B`); nothing of `pcbthermal/`, `lib/` or `point-via-convergence/` is imported.
         Simple cases first, each isolating one effect:
         R1 one via on a uniform board (the cause: the program's rule converges to the matrix without the via off-diagonals);
         R2 a dense two-direction array of vias with footprints touching through the stencil (blocks updated at once: block Jacobi among blocks);
         R3 the same with three blocks that touch each other in a triangle (a block graph that is not two-colourable);
         R4 non-uniform sheet conductance (factor 1000 between cells);
         R5 an outline: cells off the board pinned to the ambient by 1 W/K, a footprint that reaches them;
         R6 a node-centred (FDM-like) matrix: half conductances and half areas on the border;
         For every case: the energy-argument quantity lambda_min(2 D_B - K_VV) (positive means the simultaneous block step cannot increase the energy error),
         the spectral radius of one sweep (dense) of the program's rule, of (c) (the study's block step: all blocks at once, not relaxed) and of (c')
         (blocks one after another, relaxed by the same omega), against the board without vias; then (c') iterated against the direct solver.
         Run from the repository root: `.venv/bin/python research/sor-with-via-couplings/scripts/study_review.py` (about two minutes).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K_CU = 385.0                                                                # copper conductivity (W/m K)


def disc_weights(xc, yc, r, dx, nx, ny, sub=8):
    """!
    @brief Area weights of a disc over the cells of a grid (sampled), normalised to one.
    @param xc Centre x in m.
    @param yc Centre y in m.
    @param r Radius in m.
    @param dx Cell size in m.
    @param nx Cells along x.
    @param ny Cells along y.
    @param sub Samples per cell side.
    @return dict {(i, j): w} with i the row (y) and j the column (x).
    """
    w = {}
    i0, i1 = max(int((yc - r) / dx) - 1, 0), min(int((yc + r) / dx) + 2, ny)
    j0, j1 = max(int((xc - r) / dx) - 1, 0), min(int((xc + r) / dx) + 2, nx)
    s = (np.arange(sub) + 0.5) / sub * dx
    for i in range(i0, i1):
        for j in range(j0, j1):
            X, Y = np.meshgrid(j * dx + s, i * dx + s)
            f = np.mean((X - xc) ** 2 + (Y - yc) ** 2 <= r * r)
            if f > 0:
                w[(i, j)] = f
    if not w:                                                               # a disc smaller than the samples: its cell
        w[(min(int(yc / dx), ny - 1), min(int(xc / dx), nx - 1))] = 1.0
    t = sum(w.values())
    return {k: v / t for k, v in w.items()}


def board(nx, ny, L=2, dx=0.5e-3, sheet=None, gap=0.5e-3, kz=0.3, h=10.0, vias=(), pinned=None, node_centred=False, g_pin=1.0):
    """!
    @brief Own layered conduction matrix with mean-potential via couplings.
    @param nx Cells along x.
    @param ny Cells along y.
    @param L Copper layers.
    @param dx Cell size in m.
    @param sheet Sheet conductance in W/K, scalar or array (L, ny, nx) (default 35 um of copper).
    @param gap Dielectric thickness between layers in m.
    @param kz Through-plane conductivity of the dielectric in W/m K.
    @param h Heat transfer coefficient of the two outer faces in W/m2 K.
    @param vias Sequence of (x, y, footprint radius, barrel conductance per gap in W/K), or of (weights dict {(i, j): w}, barrel conductance) for a footprint given cell by cell.
    @param pinned Boolean (ny, nx) of cells off the board (pinned to the ambient by g_pin), or None.
    @param node_centred True halves the border areas and the conductances along the border (an FDM-like node grid).
    @param g_pin Conductance of a pinned cell to the ambient in W/K.
    @return dict(K stencil-plus-via sparse, A stencil sparse, Kv via part sparse, blocks list of index arrays, n).
    """
    n = L * ny * nx
    idx = np.arange(n).reshape(L, ny, nx)
    S = np.full((L, ny, nx), K_CU * 35e-6) if sheet is None else np.broadcast_to(sheet, (L, ny, nx)).astype(float)
    area = np.full((ny, nx), dx * dx)
    if node_centred:                                                        # border nodes own half (corners a quarter) of a cell
        fy = np.ones(ny); fy[[0, -1]] = 0.5
        fx = np.ones(nx); fx[[0, -1]] = 0.5
        area = area * np.outer(fy, fx)
    rows, cols, vals = [], [], []

    def couple(a, b, g):
        # symmetric conductance g between unknowns a and b
        a, b, g = a.ravel(), b.ravel(), np.asarray(g).ravel()
        rows.extend([a, b, a, b]); cols.extend([a, b, b, a]); vals.extend([g, g, -g, -g])

    gx = 2 * S[:, :, :-1] * S[:, :, 1:] / (S[:, :, :-1] + S[:, :, 1:])
    gy = 2 * S[:, :-1, :] * S[:, 1:, :] / (S[:, :-1, :] + S[:, 1:, :])
    if node_centred:                                                        # a face along the border is half as wide
        gx = gx * np.where(np.isin(np.arange(ny), [0, ny - 1]), 0.5, 1.0)[None, :, None]
        gy = gy * np.where(np.isin(np.arange(nx), [0, nx - 1]), 0.5, 1.0)[None, None, :]
    couple(idx[:, :, :-1], idx[:, :, 1:], gx)
    couple(idx[:, :-1, :], idx[:, 1:, :], gy)
    for l in range(L - 1):
        couple(idx[l], idx[l + 1], kz * area / gap)
    d = np.zeros((L, ny, nx))
    d[0] += h * area
    d[-1] += h * area
    if pinned is not None:
        d[:, pinned] += g_pin
    rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(d.ravel())
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
    # Via part: barrel chain gv between the footprint means of consecutive layers, K_via = sum_l gv u_l u_l^T, u_l = e_l (x) w - e_l+1 (x) w
    vr, vc, vv, blocks = [], [], [], []
    for v in vias:
        if len(v) == 2:
            w, gv = {k: x / sum(v[0].values()) for k, x in v[0].items()}, v[1]
        else:
            w, gv = disc_weights(v[0], v[1], v[2], dx, nx, ny), v[3]
        cells = list(w)
        ci = np.array([c[0] for c in cells]); cj = np.array([c[1] for c in cells]); wv = np.array([w[c] for c in cells])
        for l in range(L - 1):
            u_idx = np.concatenate([idx[l, ci, cj], idx[l + 1, ci, cj]])
            u = np.concatenate([wv, -wv])
            vr.append(np.repeat(u_idx, len(u_idx))); vc.append(np.tile(u_idx, len(u_idx))); vv.append(gv * np.outer(u, u).ravel())
        blocks.append(set(idx[:, ci, cj].ravel().tolist()))
    if vias:
        Kv = sp.csr_matrix((np.concatenate(vv), (np.concatenate(vr), np.concatenate(vc))), shape=(n, n))
    else:
        Kv = sp.csr_matrix((n, n))
    merged = []
    for s in blocks:                                                        # vias that share a cell are one block (their couplings overlap)
        for m in [m for m in merged if m & s]:
            s |= m
            merged.remove(m)
        merged.append(s)
    return {"K": (A + Kv).tocsr(), "A": A, "Kv": Kv, "blocks": [np.array(sorted(s)) for s in merged], "n": n, "shape": (L, ny, nx)}


class Sweeps:
    """!
    @brief Own implementation of the sweeps compared (general sparse algebra, no stencil arrays).
    """

    def __init__(self, b, omega, mode, omega_b=1.0):
        """!
        @brief Prepare one kind of sweep.
        @param b Dict from `board`.
        @param omega Relaxation factor of the point (colour) updates.
        @param mode "program" (all cells in the two colours, the via off-diagonals dropped, the diagonal of K kept), "simultaneous" (colours without the via cells,
                    then every block at once), "sequential" (blocks one after another) or "novia" (the stencil alone, for the board without vias).
        @param omega_b Relaxation factor of the block step.
        """
        self.K, self.mode, self.omega, self.omega_b = b["K"], mode, omega, omega_b
        L, ny, nx = b["shape"]
        li, ii, jj = np.indices((L, ny, nx))
        red = ((li + ii + jj) % 2 == 0).ravel()
        if mode == "program":
            # what `fvm.Network.solve_sor` iterates: stencil off-diagonals and the diagonal of the assembled matrix
            self.M = (b["A"] - sp.diags(b["A"].diagonal()) + sp.diags(self.K.diagonal())).tocsr()
            blocks = []
        elif mode == "novia":
            self.M = self.K = b["A"]
            blocks = []
        else:
            self.M = self.K
            blocks = b["blocks"]
        via = np.zeros(b["n"], bool)
        for blk in blocks:
            via[blk] = True
        self.colours = [np.where(red & ~via)[0], np.where(~red & ~via)[0]]
        for c in self.colours:                                              # a colour must be a set of uncoupled unknowns for its simultaneous update to be Gauss-Seidel
            sub = self.M[c][:, c]
            assert abs(sub - sp.diags(sub.diagonal())).max() == 0.0 if sub.nnz else True
        self.dg = self.M.diagonal()
        self.blocks = blocks
        self.binv = [np.linalg.inv(self.K[blk][:, blk].toarray()) for blk in blocks]
        if blocks:
            self.ball = np.concatenate(blocks)
            self.Ball = sp.block_diag(self.binv, format="csr")

    def sweep(self, x, q):
        """!
        @brief One sweep (works on a vector or on a matrix of column vectors).
        @param x Iterate, (n,) or (n, k).
        @param q Right-hand side of the same shape.
        @return The new iterate.
        """
        x = x.copy()
        for c in self.colours:
            r = q[c] - self.M[c] @ x
            x[c] += self.omega * (r.T / self.dg[c]).T
        if self.blocks and self.mode == "simultaneous":
            r = q[self.ball] - self.K[self.ball] @ x
            x[self.ball] += self.omega_b * (self.Ball @ r)
        elif self.blocks:
            for blk, bi in zip(self.blocks, self.binv):
                x[blk] += self.omega_b * (bi @ (q[blk] - self.K[blk] @ x))
        return x

    def radius(self):
        """!
        @brief Spectral radius of one sweep (dense; the sweep applied to the identity with a zero right-hand side).
        @return float.
        """
        n = self.K.shape[0]
        T = self.sweep(np.eye(n), np.zeros((n, n)))
        return float(np.abs(np.linalg.eigvals(T)).max())

    def solve(self, q, tol=1e-9, max_iter=60000):
        """!
        @brief Iterate to a relative residual of the TRUE matrix below tol.
        @param q Right-hand side (n,).
        @param tol Tolerance.
        @param max_iter Sweep limit.
        @return Tuple (x, sweeps or None when not converged).
        """
        x = np.zeros_like(q)
        qn = np.linalg.norm(q)
        for it in range(1, max_iter + 1):
            x = self.sweep(x, q)
            if it % 10 == 0:
                res = np.linalg.norm(self.K @ x - q) / qn
                if not np.isfinite(res) or res > 1e6:
                    return x, None
                if res < tol:
                    return x, it
        return x, None


def energy_margin(b):
    """!
    @brief lambda_min(2 D_B - K_VV) / lambda_max(D_B): the simultaneous block step (block Jacobi among the via blocks) does not increase the energy error when it is >= 0.
    @param b Dict from `board`.
    @return float (inf when there are no blocks).
    """
    if not b["blocks"]:
        return np.inf
    allb = np.concatenate(b["blocks"])
    KVV = b["K"][allb][:, allb].toarray()
    DB = np.zeros_like(KVV)
    o = 0
    for blk in b["blocks"]:
        k = len(blk)
        DB[o:o + k, o:o + k] = KVV[o:o + k, o:o + k]
        o += k
    return float(np.linalg.eigvalsh(2 * DB - KVV).min() / np.linalg.eigvalsh(DB).max())


def rhs_centre(b, frac=0.25):
    """!
    @brief A 1 W source spread over the central cells of the top layer.
    @param b Dict from `board`.
    @param frac Side of the source as a fraction of the board side.
    @return numpy array (n,).
    """
    L, ny, nx = b["shape"]
    q = np.zeros((L, ny, nx))
    a, c = int(ny * (0.5 - frac / 2)), int(nx * (0.5 - frac / 2))
    q[0, a:max(a + 1, int(ny * (0.5 + frac / 2))), c:max(c + 1, int(nx * (0.5 + frac / 2)))] = 1.0
    return (q / q.sum()).ravel()


def cases():
    """!
    @brief The boards of the review (simple first), each isolating one effect.
    @return list of (name, effect, kwargs of `board`, dense) with dense True when the spectral radius is computed.
    """
    dx = 0.5e-3
    g_fill = K_CU * np.pi * (0.15e-3) ** 2 / 0.5e-3                         # 0.3 mm copper-filled barrel over a 0.5 mm gap (W/K)
    out = []
    out.append(("R1 one via", "the cause, a single footprint", dict(nx=12, ny=12, L=2, vias=[(3.0e-3, 3.0e-3, 0.6e-3, g_fill)]), True))
    # touching footprints: radius 0.5 mm at a 1 mm pitch on 0.5 mm cells (each footprint 2 x 2 cells, neighbours share a cell side, not a cell)
    arr = [(1.0e-3 * (i + 1.0), 1.0e-3 * (j + 1.0), 0.5e-3, 10 * g_fill) for i in range(5) for j in range(5)]
    out.append(("R2 5 x 5 array, touching", "blocks adjacent in x and y, updated at once", dict(nx=12, ny=12, L=2, vias=arr), True))
    out.append(("R2b same, 4 layers", "the dense couplings across non-adjacent planes", dict(nx=12, ny=12, L=4, vias=arr), True))
    # footprints given cell by cell: A = {(2,2), (2,3)}, B = {(3,2)}, C = {(3,3)}; A-B, A-C and B-C are stencil neighbours (a triangle of blocks)
    tri = [({(2, 2): 1.0, (2, 3): 1.0}, 10 * g_fill), ({(3, 2): 1.0}, 10 * g_fill), ({(3, 3): 1.0}, 10 * g_fill)]
    out.append(("R3 three blocks in a triangle", "a block graph that is not two-colourable", dict(nx=8, ny=8, L=2, vias=tri), True))
    rng = np.random.default_rng(1)
    S = K_CU * 35e-6 * 10 ** rng.uniform(-3, 0, (2, 12, 12))
    out.append(("R4 random sheet 1e-3..1", "non-uniform conductivity", dict(nx=12, ny=12, L=2, sheet=S, vias=arr), True))
    pin = np.zeros((12, 12), bool)
    pin[:, :3] = True
    pin[:4, :] = True
    out.append(("R5 outline, pinned cells", "cells off the board at 1 W/K, footprints reach them", dict(nx=12, ny=12, L=2, vias=arr, pinned=pin), True))
    out.append(("R6 node-centred", "an FDM-like border", dict(nx=12, ny=12, L=2, vias=arr, node_centred=True), True))
    return out


def per_decade(rho):
    """!
    @brief Sweeps needed to reduce the error tenfold, ln 10 / -ln rho.
    @param rho Spectral radius of one sweep.
    @return float (inf when rho >= 1).
    """
    return np.log(10.0) / -np.log(rho) if rho < 1.0 else np.inf


def main():
    """!
    @brief Print the review tables.
    @return None.
    """
    print("A. Sweeps per decade of error (ln 10 / -ln rho, dense spectral radius); energy margin = lambda_min(2 D_B - K_VV) / lambda_max(D_B)")
    print("| case | effect | N | blocks | via cells | energy margin | omega | no-via board | program's rule | (c) simultaneous, omega_b 1 | (c') sequential, omega_b = omega |")
    print("| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    for name, effect, kw, dense in cases():
        b = board(**kw)
        em = energy_margin(b)
        nvc = sum(len(x) for x in b["blocks"])
        for om in (1.0, 1.5, 1.9, 1.97):
            rn = Sweeps(b, om, "novia").radius()
            rp = Sweeps(b, om, "program").radius()
            rs = Sweeps(b, om, "simultaneous").radius()
            rq = Sweeps(b, om, "sequential", omega_b=om).radius()
            print(f"| {name} | {effect} | {b['n']} | {len(b['blocks'])} | {nvc} | {em:.4f} | {om} | {per_decade(rn):.0f} | {per_decade(rp):.0f} (to the wrong matrix) | "
                  f"{per_decade(rs):.0f} | {per_decade(rq):.0f} |", flush=True)
    print()
    print("B. Relaxation of the block step, R2b (4 layers, touching footprints), colours at omega 1.5: spectral radius")
    b = board(**cases()[2][2])
    print("| omega_b | blocks at once (block Jacobi among blocks) | blocks one after another |")
    print("| --: | --: | --: |")
    for ob in (0.5, 1.0, 1.5, 1.9):
        print(f"| {ob} | {Sweeps(b, 1.5, 'simultaneous', omega_b=ob).radius():.5f} | {Sweeps(b, 1.5, 'sequential', omega_b=ob).radius():.5f} |", flush=True)
    print()
    print("C. Iterated to a residual of 1e-9 at omega 1.9, 1 W source: (c') against the direct solver, and where the program's rule ends")
    print("| case | sweeps (c') | max |(c') - direct| (K) | program's rule after 60000 sweeps: max |x - direct| (K) | its limit: max |solve(K_drop) - direct| (K) |")
    print("| :-- | --: | --: | --: | --: |")
    for name, effect, kw, dense in cases():
        b = board(**kw)
        q = rhs_centre(b)
        xd = spla.spsolve(b["K"].tocsc(), q)
        sw = Sweeps(b, 1.9, "program")
        xdrop = spla.spsolve(sw.M.tocsc(), q)
        xs, ns = Sweeps(b, 1.9, "sequential", omega_b=1.9).solve(q)
        xp, _ = sw.solve(q, max_iter=60000)
        print(f"| {name} | {ns} | {np.abs(xs - xd).max():.1e} | {np.abs(xp - xd).max():.2f} | {np.abs(xdrop - xd).max():.2f} |", flush=True)


if __name__ == "__main__":
    main()
