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
         (`available()` says whether it is importable; without it a mesh above the direct limit raises `FemUnavailable`). Selectable in the program since 2.8.0 (model `fem`, `fem.py`); there is
         no mesh builder from a Problem here (that is `femmesh.py`, see `docs/theory.md` 4a). SI units throughout: m, W, K, W/mK, W/m2K. Local node order of an element: the four nodes of
         its bottom quad counter-clockwise in the plan, then the same four at the top; the local coordinates (xi, eta, zeta) in [-1, 1]^3 follow that order.
"""

import logging
import sys
from typing import Callable, Optional

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

log = logging.getLogger(__name__)

## Largest unknown count solved by the direct (SuperLU symmetric) factorisation; above it the CG + AMG path is used (needs pyamg).
FEM_DIRECT_MAX = 30000

## Largest unknown count whose transient is stepped by a direct factorisation (one factor serves every step of a stage; the CG path costs about the steady iteration count at
## EVERY step, DESIGN.md 14.3). Shipped conservative, equal to the steady limit; the measurement that may raise it is `releases/2.9.0/fem-transient/scripts/measure_fem_transient_law.py`.
FEM_TRANSIENT_DIRECT_MAX = 30000

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


def _peak_gb() -> float:
    """!
    @brief Peak resident memory of this process so far, in GB (NaN where the module `resource` does not exist, as on Windows).
    @return float Gigabytes.
    """
    try:
        import resource                                            # Unix only: imported here so that the module loads on Windows too
    except ImportError:
        return float("nan")
    # ru_maxrss is in bytes on macOS and in kB on Linux
    scale = 2 ** 30 if sys.platform == "darwin" else 2 ** 20
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale


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


def jacobian(X, dn):
    """!
    @brief Jacobians dx_i/dxi_j of a batch of mapped bricks at one Gauss point (a batched matrix product, not an einsum).
    @param X Corner coordinates, array (e, 8, 3) in m.
    @param dn Local shape-function gradients at the point, array (8, 3), dimensionless.
    @return numpy.ndarray (e, 3, 3) in m.
    """
    return np.matmul(X.transpose(0, 2, 1), dn)


def det_inv3(J, need_inv: bool = True):
    """!
    @brief Determinant and inverse of a batch of 3 x 3 matrices by the closed-form cofactors (several times faster than the batched `numpy.linalg` calls on
           millions of tiny matrices, and equal to them to rounding).
    @param J Matrices, array (e, 3, 3).
    @param need_inv False skips the inverse (the volume and validation passes only need the determinant).
    @return Tuple (det (e,), inv (e, 3, 3) or None). A singular matrix gives a zero determinant and a non-finite inverse (no exception: `Model.validate` refuses such
            elements before any assembly).
    """
    a, b, c = J[:, 0, 0], J[:, 0, 1], J[:, 0, 2]
    d, e, f = J[:, 1, 0], J[:, 1, 1], J[:, 1, 2]
    g, h, i = J[:, 2, 0], J[:, 2, 1], J[:, 2, 2]
    c00, c01, c02 = e * i - f * h, f * g - d * i, d * h - e * g          # cofactors of the first row
    det = a * c00 + b * c01 + c * c02
    if not need_inv:
        return det, None
    inv = np.empty_like(J)
    with np.errstate(divide="ignore", invalid="ignore"):             # a singular element gives inf/nan here, never an exception
        r = 1.0 / det
        inv[:, 0, 0], inv[:, 0, 1], inv[:, 0, 2] = c00 * r, (c * h - b * i) * r, (b * f - c * e) * r
        inv[:, 1, 0], inv[:, 1, 1], inv[:, 1, 2] = c01 * r, (a * i - c * g) * r, (c * d - a * f) * r
        inv[:, 2, 0], inv[:, 2, 1], inv[:, 2, 2] = c02 * r, (b * g - a * h) * r, (a * e - b * d) * r
    return det, inv


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
        self.rho_c = np.zeros(E)                                   # volumetric heat capacity of every element, J/m3K (zero: no mass, only the transient reads it)
        self.faces = []                                            # list of dicts: nodes (F, 4), h (F,), t_amb (F, 4), flux (F,)

    def add_faces(self, face_nodes, h=0.0, t_amb=0.0, flux=0.0, label=""):
        """!
        @brief Add boundary faces with a film and/or a prescribed flux.
        @param face_nodes Node ids (F, 4) of every face, in cyclic order (the area is taken positive).
        @param h Film coefficient in W/m2K, a number or an array (F,).
        @param t_amb Ambient temperature of the film in K (or degC: only differences matter), a number, an array (F,) or (F, 4) per face node.
        @param flux Prescribed heat flux INTO the body in W/m2, a number or an array (F,).
        @param label Name of the group ("top", "bottom", "edge", "block", ...): only a tag for the read-outs that split the heat by path, never used by the solver.
        @return None.
        """
        fn = np.asarray(face_nodes, np.int64).reshape(-1, 4)
        F = fn.shape[0]
        if F == 0:
            return
        ta = np.asarray(t_amb, float)
        ta = np.broadcast_to(ta[:, None] if ta.ndim == 1 else ta, (F, 4)).copy()
        self.faces.append({"nodes": fn, "h": np.broadcast_to(np.asarray(h, float), (F,)).copy(), "t_amb": ta,
                           "flux": np.broadcast_to(np.asarray(flux, float), (F,)).copy(), "label": label})

    def validate(self):
        """!
        @brief Refuse inputs that would give a singular system or a silently wrong field (called by `assemble`).
        @details Checks: finite node coordinates; element and face node ids inside the node array; every conductivity finite and positive (a negative or
                 zero k made the factorisation fail or, worse, return a plausible field); every source, flux and ambient finite; every film coefficient
                 finite and not negative; every element with a non-degenerate mapping (|det J| at the eight Gauss points above 1e-12 of the cube of the
                 element's bounding-box diagonal); at least one film face with h > 0 (without one the problem has no reference temperature).
        @return None.
        @throws ValueError Naming the first problem found.
        """
        N = self.nodes.shape[0]
        if self.nodes.ndim != 2 or self.nodes.shape[1] != 3 or not np.isfinite(self.nodes).all():
            raise ValueError("the node coordinates must be an (N, 3) array of finite numbers")
        if self.elems.ndim != 2 or self.elems.shape[1] != 8 or self.elems.shape[0] == 0:
            raise ValueError("the elements must be a non-empty (E, 8) array of node ids")
        if self.elems.min() < 0 or self.elems.max() >= N:
            raise ValueError("an element refers to a node id outside the node array")
        E = self.elems.shape[0]
        if self.k.shape != (E, 3) or not np.isfinite(self.k).all() or (self.k <= 0).any():
            raise ValueError("every element conductivity (kx, ky, kz) must be finite and positive, in W/mK")
        if self.q.shape != (E,) or not np.isfinite(self.q).all():
            raise ValueError("every element source must be a finite number in W/m3")
        if self.rho_c.shape != (E,) or not np.isfinite(self.rho_c).all() or (self.rho_c < 0).any():
            raise ValueError("every element heat capacity must be a finite number not below zero, in J/m3K")
        any_film = False
        for f in self.faces:
            fn = f["nodes"]
            if fn.size and (fn.min() < 0 or fn.max() >= N):
                raise ValueError("a boundary face refers to a node id outside the node array")
            if not np.isfinite(f["h"]).all() or (f["h"] < 0).any():
                raise ValueError("every film coefficient must be finite and not negative, in W/m2K")
            if not np.isfinite(f["t_amb"]).all() or not np.isfinite(f["flux"]).all():
                raise ValueError("every ambient temperature and prescribed flux must be finite")
            any_film = any_film or bool((f["h"] > 0).any())
        if not any_film:
            raise ValueError("no face has a film (h > 0): the problem has no reference temperature")
        X = self.nodes[self.elems]
        diag = np.linalg.norm(X.max(axis=1) - X.min(axis=1), axis=1)
        dmin = np.full(E, np.inf)
        for gx in (-G1, G1):
            for gy in (-G1, G1):
                for gz in (-G1, G1):
                    _, dn = shape(gx, gy, gz)
                    dmin = np.minimum(dmin, np.abs(det_inv3(jacobian(X, dn), False)[0]))
        bad = np.flatnonzero(~(dmin > 1e-12 * diag ** 3))
        if bad.size:
            raise ValueError(f"{bad.size} element(s) have a degenerate (zero-volume) mapping, the first is element {int(bad[0])}")

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
                    v += np.abs(det_inv3(jacobian(X, dn), False)[0])
        return v

    def _assemble_elements(self, chunk=20000, cancel: Optional[Callable[[], bool]] = None, mass: bool = False):
        """!
        @brief Stiffness triplets and volumetric load of all elements, in chunks to bound the memory; optionally the consistent mass triplets in the SAME element loop.
        @details The mass uses the Jacobians the stiffness has just computed, so it adds only the outer product `N N^T` times `rho c det` per Gauss point (DESIGN.md 14.3).
        @param chunk Elements per chunk.
        @param cancel Optional callable checked between chunks; True aborts with FemCancelled.
        @param mass True: also return the values of the consistent mass matrix (the rows and columns are those of the stiffness).
        @return Tuple (rows, cols, vals, rhs) with rhs the nodal load (N,) in W; with `mass` a fifth item, the list of mass values per chunk (as `vals`), in J/K.
        """
        E = self.elems.shape[0]
        N = self.nodes.shape[0]
        rows, cols, vals, mvals = [], [], [], []
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
            me = np.zeros((el.shape[0], 8, 8)) if mass else None
            for gx, gy, gz in gps:
                n, dn = shape(gx, gy, gz)
                # closed-form 3 x 3 determinant and inverse and batched matrix products instead of per-call numpy.linalg and einsum (the same numbers to
                # rounding, a faster assembly: see docs/theory.md 4a)
                det, Jinv = det_inv3(jacobian(X, dn))              # J = dx_i / dxi_j
                det = np.abs(det)
                B = np.matmul(dn, Jinv)                            # grad N_a in physical coordinates, (e, 8, 3)
                # B diag(k) B^T times det (weight 1 at every Gauss point)
                ke += np.matmul(B * (k * det[:, None])[:, None, :], B.transpose(0, 2, 1))
                fe += (self.q[a:a + chunk] * det)[:, None] * n[None, :]
                if mass:
                    # consistent mass: rho c N N^T det (weight 1 at every Gauss point), the Jacobian determinant of the stiffness reused
                    me += (self.rho_c[a:a + chunk] * det)[:, None, None] * np.outer(n, n)[None, :, :]
            rows.append(np.repeat(el, 8, axis=1).ravel())
            cols.append(np.tile(el, (1, 8)).ravel())
            vals.append(ke.ravel())
            if mass:
                mvals.append(me.ravel())
            np.add.at(rhs, el.ravel(), fe.ravel())
        if mass:
            return rows, cols, vals, rhs, mvals
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

    def assemble(self, cancel: Optional[Callable[[], bool]] = None, capacity: bool = False):
        """!
        @brief Assemble the global matrix and load, and with `capacity` the heat capacity matrix in the same element loop.
        @param cancel Optional cancel callable (see `_assemble_elements`).
        @param capacity True: the result also holds M (the consistent mass, csc on the used nodes, J/K), m_lump (its row sums, (n,) in J/K) and capacity_total (the sum of
               all its entries, J/K, equal to the integral of rho c over the mesh).
        @return dict with A (csc, used nodes only), rhs, used (bool N), gam, q_gen (W generated by the volumetric sources), q_flux (W of the
                prescribed fluxes), q_amb (integral of h T_amb); with `capacity` also M, m_lump, capacity_total.
        @throws ValueError If `validate` refuses the inputs.
        """
        self.validate()
        if capacity:
            r1, c1, v1, rhs1, mv = self._assemble_elements(cancel=cancel, mass=True)
        else:
            r1, c1, v1, rhs1 = self._assemble_elements(cancel=cancel)
            mv = None
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
        extra = {}
        if capacity:
            # the mass has the element triplets only (a film face has no capacity); the same remap as A, so the two share their unknowns
            M = sp.csr_matrix((np.concatenate(mv), (remap[np.concatenate(r1)], remap[np.concatenate(c1)])), shape=(n, n)).tocsc()
            extra = {"M": M, "m_lump": np.asarray(M.sum(axis=1)).ravel(), "capacity_total": float(M.sum())}
            del mv
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
        return {"A": A, "rhs": (rhs1 + rhs2)[used], "used": used, "gam": gam, "q_gen": q_gen, "q_flux": q_flux, "q_amb": q_amb, **extra}

    def load_vector(self, elem_ids=None, q_unit=None, face_nodes=None, flux_unit=None):
        """!
        @brief Nodal load of a UNIT power spread over a group of elements (a volume source) and/or a group of faces (a prescribed flux), on the used unknowns.
        @details The same Gauss rules as the load of `assemble`, so that for the heaters of a mesh `sum_h p_h load_vector(h)` equals the steady `rhs` at the heater powers (the
                 load test). `q_unit` and `flux_unit` are densities per watt: W/m3 and W/m2 for a power of 1 W.
        @param elem_ids Element indices (n,) that carry the source (None: none).
        @param q_unit Source density of those elements for 1 W, W/m3 per W, array (n,) or a number.
        @param face_nodes Node ids (F, 4) of the faces that carry a prescribed flux (None: none).
        @param flux_unit Flux into the body over those faces for 1 W, W/m2 per W, array (F,) or a number.
        @return numpy.ndarray (n_used,) nodal load in W per W (K/W units cancel: the load of a unit power).
        """
        N = self.nodes.shape[0]
        rhs = np.zeros(N)
        if elem_ids is not None and len(elem_ids):
            ids = np.asarray(elem_ids, np.int64)
            qq = np.broadcast_to(np.asarray(q_unit, float), ids.shape)
            el = self.elems[ids]
            X = self.nodes[el]
            fe = np.zeros((el.shape[0], 8))
            for gx in (-G1, G1):
                for gy in (-G1, G1):
                    for gz in (-G1, G1):
                        n, dn = shape(gx, gy, gz)
                        det = np.abs(det_inv3(jacobian(X, dn), False)[0])
                        fe += (qq * det)[:, None] * n[None, :]
            np.add.at(rhs, el.ravel(), fe.ravel())
        if face_nodes is not None and len(face_nodes):
            fn = np.asarray(face_nodes, np.int64).reshape(-1, 4)
            fl = np.broadcast_to(np.asarray(flux_unit, float), (fn.shape[0],))
            X = self.nodes[fn]
            for gx in (-G1, G1):
                for gy in (-G1, G1):
                    n, dn = face_shape(gx, gy)
                    t = np.einsum("fai,aj->fij", X, dn)
                    dA = np.linalg.norm(np.cross(t[:, :, 0], t[:, :, 1]), axis=1)
                    np.add.at(rhs, fn.ravel(), ((fl * dA)[:, None] * n[None, :]).ravel())
        used = np.zeros(N, bool)
        used[self.elems.ravel()] = True
        return rhs[used]

    def solve(self, direct_max: int = FEM_DIRECT_MAX, tol: float = 1e-10, cancel: Optional[Callable[[], bool]] = None, force: Optional[str] = None):
        """!
        @brief Assemble and solve.
        @param direct_max Largest unknown count solved by SuperLU (its fill-in for the 27-point stencil is large); above it conjugate gradients with a
                          pyamg smoothed-aggregation preconditioner.
        @param tol Relative residual of the iterative solve (dimensionless). The default 1e-10 is what the recursive residual of CG can honestly deliver on these matrices: the true
                residual hardly moves when less is asked (example board at 1 mm: 2.2e-10 at 1e-12 and 2.3e-10 at 1e-10; the worst conditioned plate measured, 828 375 unknowns,
                needs the restart below at either tolerance), so 1e-12 only added iterations; the field changes by about 1e-10 K (docs/theory.md 4a).
        @param cancel Optional callable checked between assembly chunks; True raises FemCancelled.
        @param force None (by size), 'direct' or 'cg' (for tests and studies).
        @return dict with T (node field (N,) in the units of T_amb, NaN on unused nodes), n (unknowns), E (elements), balance (heat leaving through the films
                over the heat put in: an identity of a consistent assembly, so it checks the assembly and the solve), q_in, q_out in W, peak_gb (peak resident
                memory of the process so far in GB), solver ('direct' or 'cg'), residual (relative residual of the final solution).
        @throws FemUnavailable If the CG path is needed and pyamg is not installed.
        @throws RuntimeError If the conjugate gradients do not converge.
        @throws ValueError If the inputs are refused (`validate`), `force` is not None, 'direct' or 'cg', or the matrix is singular (a part of the mesh
                with no film).
        """
        if force not in (None, "direct", "cg"):
            raise ValueError(f"force must be None, 'direct' or 'cg', not {force!r}")
        a = self.assemble(cancel=cancel)
        A, rhs, used = a["A"], a["rhs"], a["used"]
        n = rhs.size
        use_cg = (n > direct_max) if force is None else (force == "cg")
        if not use_cg:
            try:
                lu = spla.splu(A, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0, options=dict(SymmetricMode=True))
            except RuntimeError as exc:
                # a block of elements joined to no film face (or to the rest only through a zero conductivity) has no reference temperature
                raise ValueError(f"the finite-element matrix is singular ({exc}): is every part of the mesh connected to a film face?") from exc
            t = lu.solve(rhs)
            del lu
            how = "direct"
        else:
            pyamg = _import_pyamg()                                # raises FemUnavailable before any heavy work
            ml = pyamg.smoothed_aggregation_solver(A.tocsr(), symmetry="symmetric", strength=("symmetric", {"theta": 0.0}), max_coarse=200)
            M = ml.aspreconditioner(cycle="V")
            t, info = spla.cg(A, rhs, rtol=tol, maxiter=5000, M=M)
            bnorm0 = float(np.linalg.norm(rhs))
            if info == 0 and bnorm0 > 0 and float(np.linalg.norm(A @ t - rhs)) / bnorm0 > max(1e-8, 100 * tol):
                # The recursive residual of CG drifts from the true one on a matrix with a strong conductivity contrast (review of branch 4: the case-2 plate with a
                # conductive film at 828 000 unknowns stopped at a true residual of 1.1e-8): one restart from the solution recomputes the true residual and reduces it
                t, info = spla.cg(A, rhs, x0=t, rtol=tol, maxiter=5000, M=M)
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
        log.debug("femcore solve: %d unknowns, %s, balance %.12f", n, how, q_out / q_in if q_in != 0 else float("nan"))
        return {"T": T, "n": n, "E": int(self.elems.shape[0]), "balance": q_out / q_in if q_in != 0 else float("nan"), "q_in": q_in, "q_out": q_out,
                "peak_gb": _peak_gb(), "solver": how, "residual": resid}

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
                    det = np.abs(det_inv3(jacobian(X, dn), False)[0])
                    tot += float(((T[el] @ n) * det).sum())
                    vol += float(det.sum())
        return tot, vol


class Stepper:
    """!
    @brief Linear solver of the theta step `(M/dt + theta A) T1 = M T0/dt - (1 - theta) A T0 + load`, with ONE factor or hierarchy alive at a time.
    @details The matrix depends on `dt` and `theta` only, never on the power: `prepare` builds it (freeing the previous factor FIRST, as `fvm.transient_from_network` does, so that
             the peak is one factor and not two) and factors it (SuperLU in symmetric mode up to `direct_max` unknowns) or builds the pyamg hierarchy for conjugate gradients above.
             With `M = None` the object is the steady solver (`prepare(0, 1)` is the matrix `A`), which is how several right-hand sides share one factor. The right-hand side is two
             matrix-vector products, no assembled `B_rhs`. An implicit-Euler half step has the matrix `2 (M/h + A/2)`: `euler_half_step` solves it with the Crank-Nicolson factor
             of the step `h`, so the Rannacher start costs no factorisation (DESIGN.md 14.1).
    """

    def __init__(self, A, M=None, direct_max: int = FEM_DIRECT_MAX, tol: float = 1e-10, cancel: Optional[Callable[[], bool]] = None, force: Optional[str] = None):
        """!
        @brief Hold the matrices; nothing is factored until `prepare`.
        @param A Stiffness plus film matrix (csc, n x n), W/K.
        @param M Consistent mass matrix (csc, n x n) in J/K, or None for the steady solver.
        @param direct_max Largest n solved by SuperLU; above it conjugate gradients with pyamg.
        @param tol Relative residual of the conjugate gradients (dimensionless).
        @param cancel Optional callable checked before every solve; True raises FemCancelled.
        @param force None (by size), 'direct' or 'cg' (tests and studies).
        @return None.
        @throws ValueError If `force` is not None, 'direct' or 'cg'.
        """
        if force not in (None, "direct", "cg"):
            raise ValueError(f"force must be None, 'direct' or 'cg', not {force!r}")
        self.A, self.M = A, M
        self.n = A.shape[0]
        self.tol, self.cancel = tol, cancel
        self.solver = ("cg" if force == "cg" else "direct") if force is not None else ("direct" if self.n <= direct_max else "cg")
        self.iterations = 0                                        # CG iterations of the last solve
        self.total_iterations = 0                                  # over every solve
        self.factorisations = 0                                    # factors or hierarchies built
        self.solves = 0
        self._key = None
        self._B = self._lu = self._prec = None

    def close(self):
        """!
        @brief Free the factor or hierarchy and the matrix of the current step size.
        @return None.
        """
        self._key = self._B = self._lu = self._prec = None

    def prepare(self, dt: float, theta: float):
        """!
        @brief Build the solver of `M/dt + theta A` (`dt = 0` or no mass: the steady matrix A), freeing the previous one first.
        @param dt Step in s (0 for the steady matrix).
        @param theta Implicitness, in (0, 1].
        @return None.
        @throws FemUnavailable If the CG path is needed and pyamg is not installed.
        @throws ValueError If the matrix is singular (a part of the mesh with no film).
        """
        steady = (self.M is None) or dt == 0
        key = ("steady",) if steady else (round(float(dt), 15), float(theta))
        if key == self._key:
            return
        self.close()                                               # the old factor is dead weight: free it before the new one is built
        B = (self.A if steady else (self.M / dt + theta * self.A)).tocsc()
        if self.solver == "direct":
            try:
                self._lu = spla.splu(B, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0, options=dict(SymmetricMode=True))
            except RuntimeError as exc:
                raise ValueError(f"the finite-element matrix is singular ({exc}): is every part of the mesh connected to a film face?") from exc
        else:
            pyamg = _import_pyamg()
            ml = pyamg.smoothed_aggregation_solver(B.tocsr(), symmetry="symmetric", strength=("symmetric", {"theta": 0.0}), max_coarse=200)
            self._prec = ml.aspreconditioner(cycle="V")
        self._B, self._key = B, key
        self.factorisations += 1

    def solve(self, b, x0=None):
        """!
        @brief Solve with the prepared matrix.
        @param b Right-hand side (n,).
        @param x0 Start of the conjugate gradients (the previous field: a warm start); ignored by the direct path.
        @return numpy.ndarray (n,) solution.
        @throws FemCancelled If the cancel callable returned True.
        @throws RuntimeError If `prepare` was not called or the conjugate gradients do not converge.
        """
        if self._key is None:
            raise RuntimeError("Stepper.solve before prepare")
        if self.cancel is not None and self.cancel():
            raise FemCancelled("the finite-element time stepping was cancelled")
        self.solves += 1
        if self.solver == "direct":
            return self._lu.solve(b)
        if b.ndim == 2:
            # several right-hand sides on the conjugate-gradient path: one solve per column, one hierarchy
            return np.column_stack([self.solve(b[:, j], None if x0 is None else x0[:, j]) for j in range(b.shape[1])])
        count = [0]

        def _tick(_xk):
            """!
            @brief Count one conjugate-gradient iteration.
            @param _xk Current iterate (unused).
            @return None.
            """
            count[0] += 1
        x, info = spla.cg(self._B, b, x0=x0, rtol=self.tol, maxiter=5000, M=self._prec, callback=_tick)
        bn = float(np.linalg.norm(b))
        if info == 0 and bn > 0 and float(np.linalg.norm(self._B @ x - b)) / bn > max(1e-8, 100 * self.tol):
            x, info = spla.cg(self._B, b, x0=x, rtol=self.tol, maxiter=5000, M=self._prec, callback=_tick)     # the restart of the steady solve: the recursive residual drifts
        if info != 0:
            raise RuntimeError(f"conjugate gradients did not converge (info {info})")
        self.iterations = count[0]
        self.total_iterations += count[0]
        return x

    def step(self, T0, dt: float, theta: float, load0, load1):
        """!
        @brief One theta step from `T0`.
        @param T0 Field at the start (n,) in K of rise.
        @param dt Step in s.
        @param theta 0.5 (Crank-Nicolson) or 1 (implicit Euler).
        @param load0 Load vector at the start of the step (n,) in W (the unit load times the power factor).
        @param load1 Load vector at the end of the step (n,) in W.
        @return numpy.ndarray (n,) field at the end of the step.
        """
        self.prepare(dt, theta)
        rhs = self.M @ T0 / dt + theta * load1 + (1.0 - theta) * load0
        if theta < 1.0:
            rhs -= (1.0 - theta) * (self.A @ T0)
        return self.solve(rhs, x0=T0)

    def euler_half_step(self, T0, h: float, load):
        """!
        @brief One implicit-Euler step of `h/2` (the Rannacher start), solved with the Crank-Nicolson factor of the step `h` when it is the prepared one.
        @details `M/(h/2) T1 + A T1 = M/(h/2) T0 + load` divided by two is `(M/h + A/2) T1 = M/h T0 + load/2`: the matrix of the Crank-Nicolson step of size h, so no new factor.
        @param T0 Field at the start (n,) in K of rise.
        @param h Full step in s (the half step is h/2).
        @param load Load vector (n,) in W (constant over the half step).
        @return numpy.ndarray (n,) field after the half step.
        """
        if self._key == (round(float(h), 15), 0.5):
            return self.solve(self.M @ T0 / h + 0.5 * load, x0=T0)
        return self.step(T0, 0.5 * h, 1.0, load, load)


def structured_mesh(xn, yn, zn):
    """!
    @brief Node and element arrays of a tensor-product hexahedral mesh from three node lines.
    @details Node id = i + (nx+1) (j + (ny+1) k); element id = i + nx (j + ny k), with i, j, k the cell indices along x, y, z.
    @param xn Increasing node coordinates along x in m (nx + 1 values).
    @param yn Increasing node coordinates along y in m (ny + 1 values).
    @param zn Increasing node coordinates along z in m (nz + 1 values).
    @return Tuple (nodes (N, 3) in m, elems (E, 8) in the local order of this module).
    @throws ValueError If a node line is not strictly increasing, holds a non-finite value or has fewer than two values.
    """
    lines = [np.asarray(v, float) for v in (xn, yn, zn)]
    for v in lines:
        if v.ndim != 1 or v.size < 2 or not np.isfinite(v).all() or np.any(np.diff(v) <= 0):
            raise ValueError("every node line must be strictly increasing finite values, at least two")
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
