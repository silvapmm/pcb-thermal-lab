#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fem.py
@brief Conforming isoparametric trilinear (Q1) hexahedral finite-element solver for steady orthotropic conduction with Robin faces (imports nothing of pcbthermal).
@details The temperature is a continuous trilinear field on the nodes of an unstructured hexahedral mesh (any mapped brick: graded tensor grids,
         O-grid patches around a cylinder, a disc, a rotated board). Every element has its own diagonal conductivity tensor in the global axes
         (kx, ky, kz; copper isotropic, laminate orthotropic). The weak form is integrated with 2 x 2 x 2 Gauss points (exact for an affine brick with
         constant conductivity); a Robin face `-k dT/dn = h (T - T_amb)` is the natural boundary integral `h N_i N_j` (consistent face mass, 2 x 2
         Gauss on the bilinear face), with `T_amb` constant or given per face node; a prescribed flux is a face load; a heat source is a volumetric
         load per element (its heat split by the exact brick integral of the shape functions, which for a brick is one eighth per node).
         Nothing of the cell-centred finite-volume family (half-cell film, harmonic mean, cell cover) is used: this is the structurally different
         method the comparison asks for. The linear system is symmetric positive definite and is solved by SuperLU in symmetric mode (or, above a
         size the caller sets, by conjugate gradients with a pyamg preconditioner when pyamg is importable). SI units throughout: m, W, K, W/mK,
         W/m2K. Local node order of an element: the four nodes of its bottom quad counter-clockwise (in the plan) then the same four at the top;
         the local coordinates (xi, eta, zeta) in [-1, 1]^3 follow that order.
"""

import resource

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

# signs of the eight local nodes (counter-clockwise quad at zeta = -1, then at zeta = +1)
SX = np.array([-1.0, 1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0])
SY = np.array([-1.0, -1.0, 1.0, 1.0, -1.0, -1.0, 1.0, 1.0])
SZ = np.array([-1.0, -1.0, -1.0, -1.0, 1.0, 1.0, 1.0, 1.0])
G1 = 1.0 / np.sqrt(3.0)                                            # the two-point Gauss abscissa, weight 1


def shape(xi, eta, zeta):
    """!
    @brief Trilinear shape functions and their local gradients at one point.
    @param xi Local coordinate along the first quad edge.
    @param eta Local coordinate along the second quad edge.
    @param zeta Local coordinate through the element.
    @return Tuple (N (8,), dN (8, 3)).
    """
    n = (1 + SX * xi) * (1 + SY * eta) * (1 + SZ * zeta) / 8.0
    dn = np.stack([SX * (1 + SY * eta) * (1 + SZ * zeta), SY * (1 + SX * xi) * (1 + SZ * zeta), SZ * (1 + SX * xi) * (1 + SY * eta)], axis=1) / 8.0
    return n, dn


def face_shape(xi, eta):
    """!
    @brief Bilinear shape functions of a quadrilateral face (nodes counter-clockwise) and their local gradients.
    @param xi First local coordinate.
    @param eta Second local coordinate.
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
        @param face_nodes Node ids (F, 4) of every face, counter-clockwise seen from outside or inside (the area is taken positive).
        @param h Film coefficient W/m2K, a number or an array (F,).
        @param t_amb Ambient temperature of the film, a number, an array (F,) or (F, 4) per face node, K.
        @param flux Prescribed heat flux INTO the body, W/m2, a number or an array (F,).
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
        @return numpy.ndarray (E,).
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

    def _assemble_elements(self, chunk=20000):
        """!
        @brief Stiffness triplets and volumetric load of all elements, in chunks to bound the memory.
        @param chunk Elements per chunk.
        @return Tuple (rows, cols, vals, rhs) with rhs the nodal load (N,).
        """
        E = self.elems.shape[0]
        N = self.nodes.shape[0]
        rows, cols, vals = [], [], []
        rhs = np.zeros(N)
        gps = [(gx, gy, gz) for gx in (-G1, G1) for gy in (-G1, G1) for gz in (-G1, G1)]
        for a in range(0, E, chunk):
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

    def assemble(self):
        """!
        @brief Assemble the global matrix and load.
        @return dict with A (csc, used nodes only), rhs, used (bool N), gam, q_gen (W generated by the volumetric sources), q_flux (W of the
                prescribed fluxes), q_amb (integral of h T_amb).
        """
        r1, c1, v1, rhs1 = self._assemble_elements()
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

    def solve(self, direct_max=60000, tol=1e-12):
        """!
        @brief Assemble and solve.
        @param direct_max Largest unknown count solved by SuperLU (its fill-in for the 27-point stencil reached 5.2 GB at 138 000 unknowns); above it conjugate
                          gradients with a pyamg smoothed-aggregation preconditioner (pyamg must be importable: the scratch venv), which needs a few hundred MB.
        @param tol Relative residual of the iterative solve.
        @return dict with T (node field (N,), NaN on unused nodes), n (unknowns), E (elements), balance (heat leaving through the films over the
                heat put in: identically 1 for a direct solve of a consistent assembly, so it checks the assembly and the solve), q_in, q_out,
                peak_gb (peak resident memory of the process so far), solver ('direct' or 'cg').
        """
        a = self.assemble()
        A, rhs, used = a["A"], a["rhs"], a["used"]
        n = rhs.size
        if n <= direct_max:
            lu = spla.splu(A, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0, options=dict(SymmetricMode=True))
            t = lu.solve(rhs)
            del lu
            how = "direct"
        else:
            import pyamg                                           # optional, only for the largest meshes
            ml = pyamg.smoothed_aggregation_solver(A.tocsr(), symmetry="symmetric", strength=("symmetric", {"theta": 0.0}), max_coarse=200)
            M = ml.aspreconditioner(cycle="V")
            t, info = spla.cg(A, rhs, rtol=tol, maxiter=5000, M=M)             # 46 000 unknowns of the strong-edge board: 135 iterations, 6e-12 K from the direct solve
            if info != 0:
                raise RuntimeError(f"conjugate gradients did not converge (info {info})")
            how = "cg"
        T = np.full(self.nodes.shape[0], np.nan)
        T[used] = t
        q_in = a["q_gen"] + a["q_flux"]
        q_out = float((a["gam"][used] * t).sum()) - a["q_amb"]
        return {"T": T, "n": n, "E": int(self.elems.shape[0]), "balance": q_out / q_in if q_in != 0 else float("nan"), "q_in": q_in, "q_out": q_out,
                "peak_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30, "solver": how}

    def face_integral(self, T, face_nodes):
        """!
        @brief Integral of the nodal field over quadrilateral faces and their total area (exact for the bilinear field on a planar face).
        @param T Node field (N,).
        @param face_nodes Faces (F, 4).
        @return Tuple (integral, area).
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
        @return Tuple (integral, volume).
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
