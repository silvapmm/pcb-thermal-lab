#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file hexfem.py
@brief Conforming trilinear (Q1) hexahedral finite-element solver for steady conduction with Robin walls on a graded tensor grid (imports nothing of pcbthermal).
@details A different METHOD from the cell-centred finite volumes of `solid3d.py`, `layered3d.py`, `ref3d.py` and `truth3d.py`: the temperature is a continuous trilinear field on
         the nodes, the stiffness is the exact Galerkin integral of every brick with piecewise-constant conductivity (kx = ky in the plane, kz through the thickness), the film
         `h T` on a wall is integrated with the consistent face mass matrix (no half-cell conduction in series, no harmonic mean), and the heat source is an exact brick load.
         Elements may be switched off (an outline of any axis-aligned shape: the wall is every face between an active and an inactive brick); the sides of the box are insulated
         symmetry planes unless a film is set. Everything is in SI units. Index order of every array: (z, y, x), z = 0 the top face.
"""

import resource

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def grid1d(length, breaks, zones, h_fine, growth=1.25, h_max=0.5, start=0.0):
    """!
    @brief Graded 1D node list that contains every break point.
    @param length End coordinate.
    @param breaks Coordinates that must be nodes (the ends are added).
    @param zones List of (a, b) intervals where the size is `h_fine`.
    @param h_fine Fine element size.
    @param growth Size growth per unit distance from a zone (size = h_fine + (growth - 1) d).
    @param h_max Largest element size.
    @param start First coordinate.
    @return numpy.ndarray of increasing node coordinates.
    """
    pts = sorted(set([float(start), float(length)] + [float(b) for b in breaks if start < b < length]))
    zs = np.asarray(zones, float).reshape(-1, 2)

    def size(x):
        """!
        @brief Target element size at x.
        @param x Coordinate.
        @return float size.
        """
        if zs.size == 0:
            return h_max
        d = np.maximum(np.maximum(zs[:, 0] - x, x - zs[:, 1]), 0.0).min()
        return min(h_max, h_fine + (growth - 1.0) * d)

    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        steps, x = [], a
        while x < b - 1e-12:
            s = size(x)
            steps.append(s)
            x += s
        # the march may overshoot b: drop the last step when it overshoots by more than half of it, then rescale to land on b
        if len(steps) > 1 and (x - b) > 0.5 * steps[-1]:
            steps.pop()
        steps = np.asarray(steps) * (b - a) / sum(steps)
        out.extend((a + np.cumsum(steps)).tolist())
        out[-1] = b
    return np.asarray(out)


def graded_gap(thickness, n, ratio=1.4):
    """!
    @brief Brick thicknesses of a gap split in n bricks, finest next to both faces (the copper), growing towards the middle.
    @param thickness Gap thickness.
    @param n Number of bricks.
    @param ratio Size ratio between neighbouring bricks (1: uniform).
    @return numpy.ndarray of n thicknesses summing to `thickness`.
    """
    if n == 1:
        return np.array([float(thickness)])
    i = np.arange(n)
    w = ratio ** np.minimum(i, n - 1 - i)
    return thickness * w / w.sum()


def _mass(h):
    """!
    @brief 1D consistent mass matrices of elements.
    @param h Element sizes.
    @return (E, 2, 2) array.
    """
    m = np.empty((h.size, 2, 2))
    m[:, 0, 0] = m[:, 1, 1] = h / 3.0
    m[:, 0, 1] = m[:, 1, 0] = h / 6.0
    return m


def _stiff(h):
    """!
    @brief 1D stiffness matrices of elements.
    @param h Element sizes.
    @return (E, 2, 2) array.
    """
    s = np.empty((h.size, 2, 2))
    s[:, 0, 0] = s[:, 1, 1] = 1.0 / h
    s[:, 0, 1] = s[:, 1, 0] = -1.0 / h
    return s


class Model:
    """!
    @brief One steady conduction problem on a graded hexahedral grid.
    @details Create with the node coordinate vectors, set `kxy`, `kz` (brick conductivities), `active`, the films and the source `q`, then `solve`.
    """

    def __init__(self, xn, yn, zn):
        """!
        @brief Create the grid.
        @param xn Node coordinates in x (m), increasing.
        @param yn Node coordinates in y (m), increasing.
        @param zn Node coordinates in z (m), increasing from the top face (z = 0).
        @return None.
        """
        self.xn, self.yn, self.zn = (np.asarray(a, float) for a in (xn, yn, zn))
        self.nx, self.ny, self.nz = self.xn.size - 1, self.yn.size - 1, self.zn.size - 1
        shape = (self.nz, self.ny, self.nx)
        self.kxy = np.ones(shape)
        self.kz = np.ones(shape)
        self.active = np.ones(shape, bool)
        self.h_top = 0.0
        self.h_bottom = 0.0
        self.h_wall = (0.0, 0.0, 0.0, 0.0)            # films on the box sides x-low, x-high, y-low, y-high (0: insulated, a symmetry plane)
        self.h_cut = 0.0                              # film on every face between an active and an inactive brick inside the box (an outline)
        self.q = np.zeros(shape)                      # volumetric source W/m3 per brick

    def solve(self, want_balance=True):
        """!
        @brief Assemble and solve.
        @param want_balance Also return the heat leaving through every film divided by the heat generated.
        @return dict with `T` (node field (nz+1, ny+1, nx+1), K, NaN on unused nodes), `balance`, `n` (unknowns), `E` (bricks), `peak_gb` (peak resident memory of the process, GB).
        """
        nx, ny, nz = self.nx, self.ny, self.nz
        hx, hy, hz = (np.diff(a) for a in (self.xn, self.yn, self.zn))
        nid = np.arange((nz + 1) * (ny + 1) * (nx + 1)).reshape(nz + 1, ny + 1, nx + 1)
        ez, ey, ex = np.nonzero(self.active)
        E = ez.size
        # corner nodes of every brick in the local order (iz, iy, ix)
        corners = np.stack([nid[ez + dz, ey + dy, ex + dx] for dz in (0, 1) for dy in (0, 1) for dx in (0, 1)], axis=1)
        Mx, My, Mz = _mass(hx[ex]), _mass(hy[ey]), _mass(hz[ez])
        Sx, Sy, Sz = _stiff(hx[ex]), _stiff(hy[ey]), _stiff(hz[ez])
        kxy, kz = self.kxy[ez, ey, ex], self.kz[ez, ey, ex]
        # exact Galerkin brick matrix: k_x (S_x M_y M_z) + k_y (M_x S_y M_z) + k_z (M_x M_y S_z), local index (iz, iy, ix)
        ke = (kxy[:, None, None] * (np.einsum("eij,ekl,emn->eikmjln", Mz, My, Sx, optimize=True).reshape(E, 8, 8) +
                                    np.einsum("eij,ekl,emn->eikmjln", Mz, Sy, Mx, optimize=True).reshape(E, 8, 8)) +
              kz[:, None, None] * np.einsum("eij,ekl,emn->eikmjln", Sz, My, Mx, optimize=True).reshape(E, 8, 8))
        rows = [np.repeat(corners, 8, axis=1).ravel()]
        cols = [np.tile(corners, (1, 8)).ravel()]
        vals = [ke.ravel()]
        del ke
        gam = np.zeros(nid.size)                      # film conductance of every node: h A / 4 per face node (row sums of the face mass)

        def add_face(nodes, ha, hb, hfilm):
            """!
            @brief Add the film `h T` of quadrilateral faces: h times the consistent face mass.
            @param nodes (F, 4) face nodes in the order (a0b0, a0b1, a1b0, a1b1).
            @param ha Face size along the first direction.
            @param hb Face size along the second direction.
            @param hfilm Film coefficient W/m2K.
            @return None.
            """
            if nodes.shape[0] == 0 or hfilm <= 0:
                return
            fm = hfilm * np.einsum("eij,ekl->eikjl", _mass(ha), _mass(hb)).reshape(-1, 4, 4)
            rows.append(np.repeat(nodes, 4, axis=1).ravel())
            cols.append(np.tile(nodes, (1, 4)).ravel())
            vals.append(fm.ravel())
            np.add.at(gam, nodes.ravel(), np.repeat(hfilm * ha * hb / 4.0, 4))

        act = self.active
        for kz_idx, node_k, hf in ((0, 0, self.h_top), (nz - 1, nz, self.h_bottom)):
            ey0, ex0 = np.nonzero(act[kz_idx])
            n4 = np.stack([nid[node_k, ey0 + dy, ex0 + dx] for dy in (0, 1) for dx in (0, 1)], axis=1)
            add_face(n4, hy[ey0], hx[ex0], hf)
        pad = np.pad(act, ((0, 0), (1, 1), (1, 1)), constant_values=False)
        # a face of an active brick with an inactive neighbour inside the box is a cut wall; with the box edge it is a box side
        inside_x_lo = np.zeros_like(act)
        inside_x_lo[:, :, 1:] = True
        inside_x_hi = np.zeros_like(act)
        inside_x_hi[:, :, :-1] = True
        inside_y_lo = np.zeros_like(act)
        inside_y_lo[:, 1:, :] = True
        inside_y_hi = np.zeros_like(act)
        inside_y_hi[:, :-1, :] = True
        hxl, hxh, hyl, hyh = self.h_wall
        for neigh_empty, inside, h_box, axis, is_hi in ((~pad[:, 1:-1, :-2], inside_x_lo, hxl, "x", False), (~pad[:, 1:-1, 2:], inside_x_hi, hxh, "x", True),
                                                        (~pad[:, :-2, 1:-1], inside_y_lo, hyl, "y", False), (~pad[:, 2:, 1:-1], inside_y_hi, hyh, "y", True)):
            for sel, hf in ((act & neigh_empty & inside, self.h_cut), (act & neigh_empty & ~inside, h_box)):
                zz, yy, xx = np.nonzero(sel)
                if zz.size == 0:
                    continue
                if axis == "x":
                    i = xx + (1 if is_hi else 0)
                    n4 = np.stack([nid[zz + dz, yy + dy, i] for dz in (0, 1) for dy in (0, 1)], axis=1)
                    add_face(n4, hz[zz], hy[yy], hf)
                else:
                    j = yy + (1 if is_hi else 0)
                    n4 = np.stack([nid[zz + dz, j, xx + dx] for dz in (0, 1) for dx in (0, 1)], axis=1)
                    add_face(n4, hz[zz], hx[xx], hf)
        r, c, v = np.concatenate(rows), np.concatenate(cols), np.concatenate(vals)
        # load: the heat of a brick split equally on its 8 nodes
        qe = self.q[ez, ey, ex] * hx[ex] * hy[ey] * hz[ez]
        rhs = np.zeros(nid.size)
        np.add.at(rhs, corners.ravel(), np.repeat(qe / 8.0, 8))
        used = np.zeros(nid.size, bool)
        used[corners.ravel()] = True
        n = int(used.sum())
        remap = np.cumsum(used) - 1
        A = sp.csr_matrix((v, (remap[r], remap[c])), shape=(n, n))
        del r, c, v, rows, cols, vals
        lu = spla.splu(A.tocsc(), permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0, options=dict(SymmetricMode=True))
        t = lu.solve(rhs[used])
        T = np.full(nid.size, np.nan)
        T[used] = t
        out = {"T": T.reshape(nid.shape), "n": n, "E": int(E), "peak_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30}
        if want_balance:
            gen = float(qe.sum())
            out["balance"] = float((gam[used] * t).sum() / gen) if gen > 0 else float("nan")
        return out

    def brick_mean(self, T, mask):
        """!
        @brief Volume mean of the temperature field over the bricks of a mask (exact for the trilinear field: the mean of the 8 corner values of each brick).
        @param T Node field from `solve`.
        @param mask Boolean (nz, ny, nx).
        @return float mean value.
        """
        hx, hy, hz = (np.diff(a) for a in (self.xn, self.yn, self.zn))
        ez, ey, ex = np.nonzero(mask & self.active)
        v = hx[ex] * hy[ey] * hz[ez]
        s = sum(T[ez + dz, ey + dy, ex + dx] for dz in (0, 1) for dy in (0, 1) for dx in (0, 1)) / 8.0
        return float((s * v).sum() / v.sum())
