#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file femcore.py
@brief Core of the finite-element comparison model: a conforming isoparametric trilinear (Q1) hexahedral solver for steady orthotropic conduction with Robin
       (film) faces, plus helpers for structured meshes (node lines, per-element conductivity, source cells, via rods). Imports nothing of the other pcbthermal modules.
@details Port of the independent finite-element tool of `research/independent-fem-edge/lib/fem.py` (same element, same quadrature, same boundary terms, same
         symmetric direct solve). The temperature is a continuous trilinear field on the nodes of a hexahedral mesh (any mapped brick). Every element has its own
         diagonal conductivity tensor (kx, ky, kz) in the global axes; the weak form is integrated with 2 x 2 x 2 Gauss points; a Robin face `-k dT/dn = h (T - T_amb)`
         is the natural boundary integral `h N_i N_j` (2 x 2 Gauss on the bilinear face), so the film term is inherent (no half-cell film in series); a prescribed
         flux is a face load; a heat source is a volumetric load per element. The matrix is symmetric positive definite and is solved by SuperLU in symmetric mode, or,
         above `FEM_DIRECT_MAX` unknowns, by conjugate gradients with a pyamg preconditioner. **pyamg is optional**: it is imported only when needed
         (`available()` says whether it is importable; without it a mesh above the direct limit raises `FemUnavailable`). Not selectable in the program yet; there is
         no mesh builder from a Problem here (see `docs/theory.md` 4a). SI units throughout: m, W, K, W/mK, W/m2K. Local node order of an element: the four nodes of
         its bottom quad counter-clockwise in the plan, then the same four at the top; the local coordinates (xi, eta, zeta) in [-1, 1]^3 follow that order.
"""

import logging
import resource
import sys
from typing import Callable, Optional

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

log = logging.getLogger(__name__)

## Largest unknown count solved by the direct (SuperLU symmetric) factorisation; above it the CG + AMG path is used (needs pyamg).
FEM_DIRECT_MAX = 30000

# signs of the eight local nodes (counter-clockwise quad at zeta = -1, then at zeta = +1)
SX = np.array([-1.0, 1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0])
SY = np.array([-1.0, -1.0, 1.0, 1.0, -1.0, -1.0, 1.0, 1.0])
SZ = np.array([-1.0, -1.0, -1.0, -1.0, 1.0, 1.0, 1.0, 1.0])
G1 = 1.0 / np.sqrt(3.0)                                            # the two-point Gauss abscissa, weight 1

## Local node ids of the six faces of a brick, in cyclic order (so that the bilinear face shape functions apply).
FACE_LOCAL = {"bottom": (0, 1, 2, 3), "top": (4, 5, 6, 7), "ymin": (0, 1, 5, 4), "xmax": (1, 2, 6, 5), "ymax": (2, 3, 7, 6), "xmin": (3, 0, 4, 7)}


class FemUnavailable(RuntimeError):
    """!
    @brief Raised when a solve needs the optional package pyamg and it cannot be imported.
    """


class FemCancelled(RuntimeError):
    """!
    @brief Raised when the cancel callback of a solve returns True.
    """


def available() -> bool:
    """!
    @brief Tell whether the optional package pyamg (large-mesh preconditioner) can be imported.
    @return bool True when `import pyamg` works.
    """
    try:
        import pyamg  # noqa: F401  (only a presence test)
    except ImportError:
        return False
    return True


def _import_pyamg():
    """!
    @brief Import pyamg lazily, with a clear error.
    @return The pyamg module.
    @throws FemUnavailable If pyamg is not installed.
    """
    try:
        import pyamg
    except ImportError as exc:
        raise FemUnavailable("this mesh is above the direct-solve limit and needs the package pyamg (pip install pyamg)") from exc
    return pyamg


def shape(xi: float, eta: float, zeta: float):
    """!
    @brief Trilinear shape functions and their local gradients at one point.
    @param xi Local coordinate along the first quad edge, dimensionless in [-1, 1].
    @param eta Local coordinate along the second quad edge, dimensionless in [-1, 1].
    @param zeta Local coordinate through the element, dimensionless in [-1, 1].
    @return Tuple (N (8,), dN (8, 3)).
    """
    n = (1 + SX * xi) * (1 + SY * eta) * (1 + SZ * zeta) / 8.0
    dn = np.stack([SX * (1 + SY * eta) * (1 + SZ * zeta), SY * (1 + SX * xi) * (1 + SZ * zeta), SZ * (1 + SX * xi) * (1 + SY * eta)], axis=1) / 8.0
    return n, dn


def face_shape(xi: float, eta: float):
    """!
    @brief Bilinear shape functions of a quadrilateral face (nodes counter-clockwise) and their local gradients.
    @param xi First local coordinate, dimensionless in [-1, 1].
    @param eta Second local coordinate, dimensionless in [-1, 1].
    @return Tuple (N (4,), dN (4, 2)).
    """
    sx, sy = SX[:4], SY[:4]
    n = (1 + sx * xi) * (1 + sy * eta) / 4.0
    dn = np.stack([sx * (1 + sy * eta), sy * (1 + sx * xi)], axis=1) / 4.0
    return n, dn


class Model:
    """!
    @brief One steady conduction problem: nodes, hexahedra with their conductivities and sources, Robin and flux faces.
    """

    def __init__(self, nodes, elems):
        """!
        @brief Create the model from a mesh.
        @param nodes Node coordinates (N, 3) in m.
        @param elems Element connectivity (E, 8), local order as the file header says.
        @return None.
        """
        self.nodes = np.asarray(nodes, float)
        self.elems = np.asarray(elems, np.int64)
        E = self.elems.shape[0]
        self.k = np.ones((E, 3))                                   # (kx, ky, kz) of every element, W/mK
        self.q = np.zeros(E)                                       # volumetric source of every element, W/m3
        self.faces = []                                            # list of dicts: nodes (F, 4), h (F,), t_amb (F, 4), flux (F,)

    def add_faces(self, face_nodes, h=0.0, t_amb=0.0, flux=0.0):
        """!
        @brief Add boundary faces with a film and/or a prescribed flux.
        @param face_nodes Node ids (F, 4) of every face, in cyclic order (the area is taken positive).
        @param h Film coefficient in W/m2K, a number or an array (F,).
        @param t_amb Ambient temperature of the film in K (or degC: only differences matter), a number, an array (F,) or (F, 4) per face node.
        @param flux Prescribed heat flux INTO the body in W/m2, a number or an array (F,).
        @return None.
        """
        fn = np.asarray(face_nodes, np.int64).reshape(-1, 4)
        F = fn.shape[0]
        if F == 0:
            return
        ta = np.asarray(t_amb, float)
        ta = np.broadcast_to(ta[:, None] if ta.ndim == 1 else ta, (F, 4)).copy()
        self.faces.append({"nodes": fn, "h": np.broadcast_to(np.asarray(h, float), (F,)).copy(), "t_amb": ta,
                           "flux": np.broadcast_to(np.asarray(flux, float), (F,)).copy()})

    def element_volumes(self):
        """!
        @brief Volume of every element by the same quadrature as the stiffness.
        @return numpy.ndarray (E,) in m3.
        """
        X = self.nodes[self.elems]
        v = np.zeros(self.elems.shape[0])
        for gx in (-G1, G1):
            for gy in (-G1, G1):
                for gz in (-G1, G1):
                    _, dn = shape(gx, gy, gz)
                    J = np.einsum("eai,aj->eij", X, dn)
                    v += np.abs(np.linalg.det(J))
        return v

    def _assemble_elements(self, chunk=20000, cancel: Optional[Callable[[], bool]] = None):
        """!
        @brief Stiffness triplets and volumetric load of all elements, in chunks to bound the memory.
        @param chunk Elements per chunk.
        @param cancel Optional callable checked between chunks; True aborts with FemCancelled.
        @return Tuple (rows, cols, vals, rhs) with rhs the nodal load (N,) in W.
        """
        E = self.elems.shape[0]
        N = self.nodes.shape[0]
        rows, cols, vals = [], [], []
        rhs = np.zeros(N)
        gps = [(gx, gy, gz) for gx in (-G1, G1) for gy in (-G1, G1) for gz in (-G1, G1)]
        for a in range(0, E, chunk):
            if cancel is not None and cancel():
                raise FemCancelled("the finite-element assembly was cancelled")
            el = self.elems[a:a + chunk]
            X = self.nodes[el]                                     # (e, 8, 3)
            k = self.k[a:a + chunk]
            ke = np.zeros((el.shape[0], 8, 8))
            fe = np.zeros((el.shape[0], 8))
            for gx, gy, gz in gps:
                n, dn = shape(gx, gy, gz)
                J = np.einsum("eai,aj->eij", X, dn)                # dx_i / dxi_j
                det = np.abs(np.linalg.det(J))
                Jinv = np.linalg.inv(J)
                B = np.einsum("aj,eji->eai", dn, Jinv)             # grad N_a in physical coordinates, (e, 8, 3)
                # B diag(k) B^T times det (weight 1 at every Gauss point)
                ke += np.einsum("eai,ei,ebi->eab", B, k, B) * det[:, None, None]
                fe += (self.q[a:a + chunk] * det)[:, None] * n[None, :]
            rows.append(np.repeat(el, 8, axis=1).ravel())
            cols.append(np.tile(el, (1, 8)).ravel())
            vals.append(ke.ravel())
            np.add.at(rhs, el.ravel(), fe.ravel())
        return rows, cols, vals, rhs

    def _assemble_faces(self):
        """!
        @brief Robin matrix triplets and face loads (film ambient and prescribed flux).
        @return Tuple (rows, cols, vals, rhs, gam, q_amb) with gam the row sums of the Robin matrix (so that gam . T is the heat leaving through
                the films at T_amb = 0) and q_amb the integral of h T_amb over the faces.
        """
        N = self.nodes.shape[0]
        rows, cols, vals = [], [], []
        rhs = np.zeros(N)
        gam = np.zeros(N)
        q_amb = 0.0
        for f in self.faces:
            fn = f["nodes"]
            X = self.nodes[fn]                                     # (F, 4, 3)
            mf = np.zeros((fn.shape[0], 4, 4))
            lf = np.zeros((fn.shape[0], 4))
            for gx in (-G1, G1):
                for gy in (-G1, G1):
                    n, dn = face_shape(gx, gy)
                    t = np.einsum("fai,aj->fij", X, dn)            # two tangent vectors (F, 3, 2)
                    dA = np.linalg.norm(np.cross(t[:, :, 0], t[:, :, 1]), axis=1)
                    mf += (f["h"] * dA)[:, None, None] * np.outer(n, n)[None, :, :]
                    ta = f["t_amb"] @ n                            # ambient at the Gauss point (F,)
                    lf += ((f["flux"] + f["h"] * ta) * dA)[:, None] * n[None, :]
                    q_amb += float((f["h"] * ta * dA).sum())
            rows.append(np.repeat(fn, 4, axis=1).ravel())
            cols.append(np.tile(fn, (1, 4)).ravel())
            vals.append(mf.ravel())
            np.add.at(rhs, fn.ravel(), lf.ravel())
            np.add.at(gam, fn.ravel(), mf.sum(axis=2).ravel())
        return rows, cols, vals, rhs, gam, q_amb

    def assemble(self, cancel: Optional[Callable[[], bool]] = None):
        """!
        @brief Assemble the global matrix and load.
        @param cancel Optional cancel callable (see `_assemble_elements`).
        @return dict with A (csc, used nodes only), rhs, used (bool N), gam, q_gen (W generated by the volumetric sources), q_flux (W of the
                prescribed fluxes), q_amb (integral of h T_amb).
        """
        r1, c1, v1, rhs1 = self._assemble_elements(cancel=cancel)
        r2, c2, v2, rhs2, gam, q_amb = self._assemble_faces()
        N = self.nodes.shape[0]
        used = np.zeros(N, bool)
        used[self.elems.ravel()] = True
        remap = np.cumsum(used) - 1
        n = int(used.sum())
        r = np.concatenate(r1 + r2)
        c = np.concatenate(c1 + c2)
        v = np.concatenate(v1 + v2)
        A = sp.csr_matrix((v, (remap[r], remap[c])), shape=(n, n)).tocsc()
        del r, c, v, r1, c1, v1, r2, c2, v2
        q_gen = float((self.q * self.element_volumes()).sum())
        q_flux = 0.0
        for f in self.faces:
            X = self.nodes[f["nodes"]]
            for gx in (-G1, G1):
                for gy in (-G1, G1):
                    _, dn = face_shape(gx, gy)
                    t = np.einsum("fai,aj->fij", X, dn)
                    dA = np.linalg.norm(np.cross(t[:, :, 0], t[:, :, 1]), axis=1)
                    q_flux += float((f["flux"] * dA).sum())
        return {"A": A, "rhs": (rhs1 + rhs2)[used], "used": used, "gam": gam, "q_gen": q_gen, "q_flux": q_flux, "q_amb": q_amb}

    def solve(self, direct_max: int = FEM_DIRECT_MAX, tol: float = 1e-12, cancel: Optional[Callable[[], bool]] = None, force: Optional[str] = None):
        """!
        @brief Assemble and solve.
        @param direct_max Largest unknown count solved by SuperLU (its fill-in for the 27-point stencil is large); above it conjugate gradients with a
                          pyamg smoothed-aggregation preconditioner.
        @param tol Relative residual of the iterative solve (dimensionless).
        @param cancel Optional callable checked between assembly chunks; True raises FemCancelled.
        @param force None (by size), 'direct' or 'cg' (for tests and studies).
        @return dict with T (node field (N,) in the units of T_amb, NaN on unused nodes), n (unknowns), E (elements), balance (heat leaving through the films
                over the heat put in: an identity of a consistent assembly, so it checks the assembly and the solve), q_in, q_out in W, peak_gb (peak resident
                memory of the process so far in GB), solver ('direct' or 'cg'), residual (relative residual of the final solution).
        @throws FemUnavailable If the CG path is needed and pyamg is not installed.
        @throws RuntimeError If the conjugate gradients do not converge.
        """
        a = self.assemble(cancel=cancel)
        A, rhs, used = a["A"], a["rhs"], a["used"]
        n = rhs.size
        use_cg = (n > direct_max) if force is None else (force == "cg")
        if not use_cg:
            lu = spla.splu(A, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0, options=dict(SymmetricMode=True))
            t = lu.solve(rhs)
            del lu
            how = "direct"
        else:
            pyamg = _import_pyamg()                                # raises FemUnavailable before any heavy work
            ml = pyamg.smoothed_aggregation_solver(A.tocsr(), symmetry="symmetric", strength=("symmetric", {"theta": 0.0}), max_coarse=200)
            M = ml.aspreconditioner(cycle="V")
            t, info = spla.cg(A, rhs, rtol=tol, maxiter=5000, M=M)
            if info != 0:
                raise RuntimeError(f"conjugate gradients did not converge (info {info})")
            how = "cg"
        bnorm = float(np.linalg.norm(rhs))
        resid = float(np.linalg.norm(A @ t - rhs) / bnorm) if bnorm > 0 else 0.0
        if how == "cg" and resid > max(1e-8, 100 * tol):
            raise RuntimeError(f"the conjugate-gradient solution has a relative residual of {resid:.2e}")
        T = np.full(self.nodes.shape[0], np.nan)
        T[used] = t
        q_in = a["q_gen"] + a["q_flux"]
        q_out = float((a["gam"][used] * t).sum()) - a["q_amb"]
        # ru_maxrss is in bytes on macOS and in kB on Linux
        scale = 2 ** 30 if sys.platform == "darwin" else 2 ** 20
        log.debug("femcore solve: %d unknowns, %s, balance %.12f", n, how, q_out / q_in if q_in != 0 else float("nan"))
        return {"T": T, "n": n, "E": int(self.elems.shape[0]), "balance": q_out / q_in if q_in != 0 else float("nan"), "q_in": q_in, "q_out": q_out,
                "peak_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale, "solver": how, "residual": resid}

    def face_integral(self, T, face_nodes):
        """!
        @brief Integral of the nodal field over quadrilateral faces and their total area (exact for the bilinear field on a planar face).
        @param T Node field (N,).
        @param face_nodes Faces (F, 4).
        @return Tuple (integral, area) in (field unit x m2, m2).
        """
        fn = np.asarray(face_nodes, np.int64).reshape(-1, 4)
        X = self.nodes[fn]
        tot, area = 0.0, 0.0
        for gx in (-G1, G1):
            for gy in (-G1, G1):
                n, dn = face_shape(gx, gy)
                t = np.einsum("fai,aj->fij", X, dn)
                dA = np.linalg.norm(np.cross(t[:, :, 0], t[:, :, 1]), axis=1)
                tot += float(((T[fn] @ n) * dA).sum())
                area += float(dA.sum())
        return tot, area

    def volume_integral(self, T, elem_ids):
        """!
        @brief Integral of the nodal field over a set of elements and their total volume.
        @param T Node field (N,).
        @param elem_ids Element indices.
        @return Tuple (integral, volume) in (field unit x m3, m3).
        """
        el = self.elems[np.asarray(elem_ids, np.int64)]
        X = self.nodes[el]
        tot, vol = 0.0, 0.0
        for gx in (-G1, G1):
            for gy in (-G1, G1):
                for gz in (-G1, G1):
                    n, dn = shape(gx, gy, gz)
                    det = np.abs(np.linalg.det(np.einsum("eai,aj->eij", X, dn)))
                    tot += float(((T[el] @ n) * det).sum())
                    vol += float(det.sum())
        return tot, vol


def structured_mesh(xn, yn, zn):
    """!
    @brief Node and element arrays of a tensor-product hexahedral mesh from three node lines.
    @details Node id = i + (nx+1) (j + (ny+1) k); element id = i + nx (j + ny k), with i, j, k the cell indices along x, y, z.
    @param xn Increasing node coordinates along x in m (nx + 1 values).
    @param yn Increasing node coordinates along y in m (ny + 1 values).
    @param zn Increasing node coordinates along z in m (nz + 1 values).
    @return Tuple (nodes (N, 3) in m, elems (E, 8) in the local order of this module).
    @throws ValueError If a node line is not strictly increasing or has fewer than two values.
    """
    lines = [np.asarray(v, float) for v in (xn, yn, zn)]
    for v in lines:
        if v.ndim != 1 or v.size < 2 or np.any(np.diff(v) <= 0):
            raise ValueError("every node line must be strictly increasing with at least two values")
    xn, yn, zn = lines
    nx, ny, nz = xn.size - 1, yn.size - 1, zn.size - 1
    X, Y, Z = np.meshgrid(xn, yn, zn, indexing="ij")
    # meshgrid with 'ij' is (x, y, z); node id runs x fastest, so transpose to (z, y, x) and flatten
    nodes = np.stack([X.transpose(2, 1, 0).ravel(), Y.transpose(2, 1, 0).ravel(), Z.transpose(2, 1, 0).ravel()], axis=1)
    k, j, i = np.meshgrid(np.arange(nz), np.arange(ny), np.arange(nx), indexing="ij")
    i, j, k = i.ravel(), j.ravel(), k.ravel()

    def nid(a, b, c):
        """!
        @brief Node id of the lattice point (a, b, c).
        @param a Index along x.
        @param b Index along y.
        @param c Index along z.
        @return numpy.ndarray of node ids.
        """
        return a + (nx + 1) * (b + (ny + 1) * c)

    elems = np.stack([nid(i, j, k), nid(i + 1, j, k), nid(i + 1, j + 1, k), nid(i, j + 1, k),
                      nid(i, j, k + 1), nid(i + 1, j, k + 1), nid(i + 1, j + 1, k + 1), nid(i, j + 1, k + 1)], axis=1)
    return nodes, elems


def structured_face(elems, shape_cells, side, mask=None):
    """!
    @brief Face node ids on one outer side of a structured mesh.
    @param elems Element array of `structured_mesh`.
    @param shape_cells Tuple (nx, ny, nz) of cell counts.
    @param side One of 'bottom' (z min), 'top' (z max), 'xmin', 'xmax', 'ymin', 'ymax'.
    @param mask Optional boolean array over the cells of that side (shape (ny, nx) for top/bottom, (nz, nx) for ymin/ymax, (nz, ny) for xmin/xmax) selecting faces.
    @return tuple (face nodes (F, 4), element ids (F,) of the cells that own the faces).
    @throws ValueError If the side is unknown.
    """
    nx, ny, nz = shape_cells
    if side not in FACE_LOCAL:
        raise ValueError(f"unknown side {side!r}")
    ids = np.arange(nx * ny * nz).reshape(nz, ny, nx)
    sel = {"bottom": ids[0], "top": ids[-1], "ymin": ids[:, 0, :], "ymax": ids[:, -1, :], "xmin": ids[:, :, 0], "xmax": ids[:, :, -1]}[side]
    if mask is not None:
        m = np.asarray(mask, bool)
        if m.shape != sel.shape:
            raise ValueError(f"mask shape {m.shape} does not match the side {sel.shape}")
        sel = sel[m]
    else:
        sel = sel.ravel()
    return elems[sel][:, list(FACE_LOCAL[side])], sel


def rod_conductivity(k_background, k_rod: float, area_fraction):
    """!
    @brief Effective through-thickness conductivity of an element that holds a vertical rod (a via barrel) over part of its plan area (parallel mix).
    @param k_background Conductivity of the material around the rod in W/mK (number or array).
    @param k_rod Conductivity of the rod material in W/mK.
    @param area_fraction Share of the element plan area occupied by the rod, 0 to 1 (number or array).
    @return numpy.ndarray or float of the effective kz in W/mK.
    @throws ValueError If a fraction is outside [0, 1].
    """
    f = np.asarray(area_fraction, float)
    if np.any(f < 0) or np.any(f > 1):
        raise ValueError("the rod area fraction must be between 0 and 1")
    return (1.0 - f) * np.asarray(k_background, float) + f * k_rod


def structured_model(xn, yn, zn, k=None, q=None, films=None, t_amb=0.0):
    """!
    @brief Build a Model on a tensor-product mesh from node lines, per-element conductivities and sources, and films on the outer sides.
    @param xn Node coordinates along x in m.
    @param yn Node coordinates along y in m.
    @param zn Node coordinates along z in m.
    @param k Conductivity in W/mK: a number, an array (nz, ny, nx) for an isotropic cell, or (nz, ny, nx, 3) for (kx, ky, kz); None is 1.
    @param q Volumetric source in W/m3, array (nz, ny, nx) or a number (None is 0).
    @param films Dict side -> h (W/m2K number, or an array shaped as the side's cells; see `structured_face`); sides absent are insulated.
    @param t_amb Ambient temperature of every film (a number).
    @return Model ready to solve.
    """
    nodes, elems = structured_mesh(xn, yn, zn)
    cells = (len(xn) - 1, len(yn) - 1, len(zn) - 1)
    m = Model(nodes, elems)
    if k is not None:
        kk = np.asarray(k, float)
        if kk.ndim == 0:
            m.k[:] = kk
        elif kk.ndim == 3:
            m.k[:] = kk.reshape(-1, 1)
        else:
            m.k[:] = kk.reshape(-1, 3)
    if q is not None:
        m.q[:] = np.broadcast_to(np.asarray(q, float), (cells[2], cells[1], cells[0])).reshape(-1)
    for side, h in (films or {}).items():
        hh = np.asarray(h, float)
        fn, owner = structured_face(elems, cells, side)
        m.add_faces(fn, h=hh.reshape(-1) if hh.ndim else float(hh), t_amb=t_amb)
    return m
