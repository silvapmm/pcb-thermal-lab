#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file transient.py
@brief Transient additions to the independent finite-element tool (`independent-fem-edge/lib/fem.py`, imported and not edited): the heat capacity, implicit
       time stepping (Crank-Nicolson with a Rannacher start after every change of power, implicit Euler as the check) and the periodic state of a square wave from the
       harmonic response in the frequency domain.
@details Semi-discrete system `M dT/dt + A T = p(t) f` with `A` the Galerkin stiffness plus the Robin face matrix and `f` the unit load of the sources of the model,
         both assembled by `fem.Model.assemble` (ambient 0 K: the field is a rise). `M` is the lumped mass `rho c int N_i dV` (row sums of the consistent mass, positive for
         Q1 bricks); the consistent mass is available for small meshes as a check. The theta step is `(M/dt + theta A) T1 = (M/dt - (1 - theta) A) T0 + (theta p1 + (1 - theta) p0) f`.
         Crank-Nicolson (theta 1/2) is not L-stable: the stiff modes of thin copper elements ring after a jump of the power, so after every jump two implicit-Euler steps of
         half the step open the stretch (Rannacher). Linear solves: SuperLU in symmetric mode up to 30 000 unknowns (the 2 GB budget of the shared machine), conjugate
         gradients with a smoothed-aggregation pyamg preconditioner above (pyamg only in the scratch environment of `independent-fem-edge`). SI units.
"""
import os
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "..", "independent-fem-edge", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import fem                                                              # noqa: E402

DIRECT_MAX = 30000


def lumped_mass(model, rho_c):
    """!
    @brief Lumped mass per node, `int rho c N_i dV` summed over the elements (the row sums of the consistent mass).
    @param model fem.Model.
    @param rho_c Volumetric heat capacity per element, J/m3K (E,).
    @return numpy.ndarray (N,) in J/K (zero on unused nodes).
    """
    N = model.nodes.shape[0]
    m = np.zeros(N)
    for a in range(0, model.elems.shape[0], 20000):
        el = model.elems[a:a + 20000]
        X = model.nodes[el]
        fe = np.zeros((el.shape[0], 8))
        for gx in (-fem.G1, fem.G1):
            for gy in (-fem.G1, fem.G1):
                for gz in (-fem.G1, fem.G1):
                    n, dn = fem.shape(gx, gy, gz)
                    det = np.abs(np.linalg.det(np.einsum("eai,aj->eij", X, dn)))
                    fe += (rho_c[a:a + 20000] * det)[:, None] * n[None, :]
        np.add.at(m, el.ravel(), fe.ravel())
    return m


def consistent_mass(model, rho_c):
    """!
    @brief Consistent mass matrix `rho c int N_i N_j dV` (small meshes: a check of the lumping).
    @param model fem.Model.
    @param rho_c Volumetric heat capacity per element, J/m3K (E,).
    @return scipy.sparse.csr_matrix (N, N).
    """
    N = model.nodes.shape[0]
    rows, cols, vals = [], [], []
    for a in range(0, model.elems.shape[0], 20000):
        el = model.elems[a:a + 20000]
        X = model.nodes[el]
        me = np.zeros((el.shape[0], 8, 8))
        for gx in (-fem.G1, fem.G1):
            for gy in (-fem.G1, fem.G1):
                for gz in (-fem.G1, fem.G1):
                    n, dn = fem.shape(gx, gy, gz)
                    det = np.abs(np.linalg.det(np.einsum("eai,aj->eij", X, dn)))
                    me += (rho_c[a:a + 20000] * det)[:, None, None] * np.outer(n, n)[None]
        rows.append(np.repeat(el, 8, axis=1).ravel())
        cols.append(np.tile(el, (1, 8)).ravel())
        vals.append(me.ravel())
    return sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N))


def face_weights(model, faces, n_nodes=None):
    """!
    @brief Weights `w` with `w @ T` = the mean of the nodal field over quadrilateral faces (area weighted).
    @param model fem.Model.
    @param faces Faces (F, 4) node ids.
    @param n_nodes Length of the result (default: all nodes of the model).
    @return numpy.ndarray (N,).
    """
    fn = np.asarray(faces, np.int64).reshape(-1, 4)
    N = model.nodes.shape[0] if n_nodes is None else n_nodes
    w = np.zeros(N)
    X = model.nodes[fn]
    area = 0.0
    for gx in (-fem.G1, fem.G1):
        for gy in (-fem.G1, fem.G1):
            n, dn = fem.face_shape(gx, gy)
            t = np.einsum("fai,aj->fij", X, dn)
            dA = np.linalg.norm(np.cross(t[:, :, 0], t[:, :, 1]), axis=1)
            np.add.at(w, fn.ravel(), (dA[:, None] * n[None, :]).ravel())
            area += dA.sum()
    return w / area


class Transient:
    """!
    @brief Capacity and time stepping on a `fem.Model`.
    """

    def __init__(self, model, rho_c, consistent=False):
        """!
        @brief Assemble the stiffness, the unit load and the mass.
        @param model fem.Model with its source and faces (ambient 0).
        @param rho_c Volumetric heat capacity per element, J/m3K.
        @param consistent True: the consistent mass instead of the lumped one (small meshes).
        @return None.
        """
        a = model.assemble()
        self.model, self.used = model, a["used"]
        self.A, self.f = a["A"], a["rhs"]
        self.gam = a["gam"][self.used]
        self.n = self.f.size
        if consistent:
            Mf = consistent_mass(model, np.asarray(rho_c, float)).tocsr()
            self.M = Mf[self.used][:, self.used].tocsc()
            self.m_lump = np.asarray(self.M.sum(axis=1)).ravel()
        else:
            self.m_lump = lumped_mass(model, np.asarray(rho_c, float))[self.used]
            self.M = sp.diags(self.m_lump).tocsc()
        self.q_in = a["q_gen"] + a["q_flux"]
        self._cache = {}
        self.how = "direct" if self.n <= DIRECT_MAX else "cg"

    def full(self, t):
        """!
        @brief Expand a reduced field to the nodes of the model (NaN on unused nodes).
        @param t Reduced field (n,).
        @return numpy.ndarray (N,).
        """
        T = np.full(self.model.nodes.shape[0], np.nan)
        T[self.used] = t
        return T

    def reduce_weights(self, w):
        """!
        @brief Restrict node weights to the used unknowns.
        @param w Weights (N,).
        @return numpy.ndarray (n,).
        """
        return np.asarray(w)[self.used]

    def steady(self, scale=1.0):
        """!
        @brief Steady state of the power `scale`.
        @param scale Power factor.
        @return numpy.ndarray (n,) rise.
        """
        return self._factor(0.0, 1.0)(scale * self.f)

    def _factor(self, dt, theta):
        """!
        @brief Solver of `(M/dt + theta A)` (cached for the last three step sizes; `dt = 0` is the steady matrix A).
        @param dt Step in s (0: steady).
        @param theta Implicitness.
        @return callable b -> x.
        """
        key = (round(dt, 15), theta)
        if key in self._cache:
            return self._cache[key]
        B = (self.A if dt == 0 else self.M / dt + theta * self.A).tocsc()
        if self.n <= DIRECT_MAX:
            lu = spla.splu(B, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0, options=dict(SymmetricMode=True))
            solve = lu.solve
        else:
            import pyamg
            ml = pyamg.smoothed_aggregation_solver(B.tocsr(), symmetry="symmetric", strength=("symmetric", {"theta": 0.0}), max_coarse=200)
            Mp = ml.aspreconditioner(cycle="V")

            def solve(b, B=B, Mp=Mp):
                """!
                @brief CG with the AMG preconditioner.
                @param b Right-hand side.
                @return numpy.ndarray.
                """
                x, info = spla.cg(B, b, rtol=1e-12, maxiter=2000, M=Mp)
                if info != 0:
                    raise RuntimeError(f"CG did not converge (info {info})")
                return x
        if len(self._cache) >= 3:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = solve
        return solve

    def step(self, T, dt, theta, p0, p1):
        """!
        @brief One theta step.
        @param T Field at the start (n,).
        @param dt Step in s.
        @param theta 1/2 (Crank-Nicolson) or 1 (implicit Euler).
        @param p0 Power factor at the start.
        @param p1 Power factor at the end.
        @return numpy.ndarray (n,).
        """
        rhs = self.M @ T / dt - (1.0 - theta) * (self.A @ T) + (theta * p1 + (1.0 - theta) * p0) * self.f
        return self._factor(dt, theta)(rhs)

    def march(self, T0, segments, power, readouts, rannacher=True, theta=0.5, record_every=1):
        """!
        @brief March through a list of segments, accumulating the energy.
        @param T0 Start field (n,) (the steady state of the mean power for a periodic wave).
        @param segments List of (t_start, t_end, n_steps): uniform steps inside a stretch of constant power.
        @param power Callable t -> power factor (piecewise constant; evaluated at the middle of every stretch).
        @param readouts Dict name -> vector w (n,): the series `w @ T` is returned.
        @param rannacher True: two implicit-Euler half steps open every stretch (also the first).
        @param theta Implicitness of the regular steps (1/2: Crank-Nicolson; 1: implicit Euler for the whole run).
        @param record_every Keep every n-th step.
        @return dict: t (times), series (name -> array), energy (input, stored, lost: J, over the whole march), T (end field).
        """
        t_list, out = [0.0], {k: [float(v @ T0)] for k, v in readouts.items()}
        T = T0.copy()
        e_in = e_lost = 0.0
        loss = lambda x: float(self.gam @ x)                             # noqa: E731  heat leaving through the films at ambient 0
        e0 = float(self.m_lump @ T0)
        t_now, k = segments[0][0], 0
        for (ta, tb, n) in segments:
            p = power(0.5 * (ta + tb))
            dt = (tb - ta) / n
            plan = []
            if rannacher and theta < 1.0:
                plan += [(0.5 * dt, 1.0)] * 2
                left = n * dt - dt
                if left > 1e-15:
                    plan += [(dt, theta)] * int(round(left / dt))
            else:
                plan += [(dt, theta)] * n
            for (h, th) in plan:
                Tn = self.step(T, h, th, p, p)
                e_in += p * self.q_in * h
                e_lost += h * ((th * loss(Tn)) + (1 - th) * loss(T))
                T = Tn
                t_now += h
                k += 1
                if k % record_every == 0:
                    t_list.append(t_now)
                    for kk, v in readouts.items():
                        out[kk].append(float(v @ T))
        return {"t": np.array(t_list), "series": {k: np.array(v) for k, v in out.items()}, "energy": (e_in, float(self.m_lump @ T) - e0, e_lost), "T": T}

    def step_response(self, readouts, t_end, dt0=1e-3, per_level=6, factor=2.0, theta=0.5):
        """!
        @brief Unit step of the power from rest: a step size that grows by `factor` every `per_level` steps (one factorisation per level).
        @param readouts Dict name -> weights (n,).
        @param t_end End time, s.
        @param dt0 First step, s.
        @param per_level Steps per level.
        @param factor Growth of the step between levels.
        @param theta 1/2 or 1.
        @return dict as `march` (the power is 1 from t = 0).
        """
        segs, t, dt = [], 0.0, dt0
        while t < t_end:
            segs.append((t, t + per_level * dt, per_level))
            t += per_level * dt
            dt *= factor
        T0 = np.zeros(self.n)
        t_list, out = [0.0], {k: [0.0] for k, v in readouts.items()}
        T = T0
        e_in = e_lost = 0.0
        tn = 0.0
        first = True
        for (ta, tb, n) in segs:
            h = (tb - ta) / n
            for i in range(n):
                th = theta
                hh = h
                if first and i < 2 and theta < 1.0:
                    th, hh = 1.0, 0.5 * h
                Tn = self.step(T, hh, th, 1.0, 1.0)
                e_in += self.q_in * hh
                e_lost += hh * (th * float(self.gam @ Tn) + (1 - th) * float(self.gam @ T))
                T = Tn
                tn += hh
                t_list.append(tn)
                for kk, v in readouts.items():
                    out[kk].append(float(v @ T))
            first = False
        return {"t": np.array(t_list), "series": {k: np.array(v) for k, v in out.items()}, "energy": (e_in, float(self.m_lump @ T), e_lost), "T": T}


def square_segments(period, duty, n_on, n_off, cycles):
    """!
    @brief Segments of a repeating square wave starting with the on stretch.
    @param period Period in s.
    @param duty On fraction.
    @param n_on Steps in the on stretch.
    @param n_off Steps in the off stretch.
    @param cycles Number of periods.
    @return list of (t_start, t_end, n_steps).
    """
    segs = []
    for c in range(cycles):
        t0 = c * period
        segs.append((t0, t0 + duty * period, n_on))
        segs.append((t0 + duty * period, t0 + period, n_off))
    return segs


def square_power(period, duty):
    """!
    @brief Power factor of a unit square wave (1 on, 0 off), as a function of time (evaluated at stretch middles).
    @param period Period in s.
    @param duty On fraction.
    @return callable.
    """
    return lambda t: 1.0 if (t % period) < duty * period else 0.0


def harmonic_response(tr, w, freqs):
    """!
    @brief Transfer function `H(f) = w @ (A + i 2 pi f M)^-1 f` of the unit load at the given frequencies (complex direct solves; small meshes only).
    @param tr Transient.
    @param w Readout weights (n,).
    @param freqs Frequencies in Hz.
    @return numpy.ndarray complex.
    """
    out = np.zeros(len(freqs), complex)
    for i, fr in enumerate(freqs):
        B = (tr.A + 1j * 2 * np.pi * fr * tr.M).tocsc()
        lu = spla.splu(B, permc_spec="MMD_AT_PLUS_A")
        out[i] = w @ lu.solve(tr.f.astype(complex))
        del lu
    return out


def periodic_wave(freqs, H, H0, period, duty, n_samples=16384):
    """!
    @brief Periodic steady state of a unit square wave from the transfer function at log-spaced frequencies (spline of log|H| and of the unwrapped phase in log f, the
           slope of the last two points above the last frequency), `T(t) = D H(0) + 2 Re sum_k c_k H(k f0) exp(i k w0 t)`, `c_k = (1 - exp(-i 2 pi k D)) / (i 2 pi k)`.
    @param freqs Frequencies of H in Hz (increasing, log-spaced).
    @param H Complex transfer function at `freqs`.
    @param H0 Steady transfer function (zero frequency), K/W.
    @param period Period in s.
    @param duty On fraction.
    @param n_samples Samples per period (harmonics up to n_samples / 2).
    @return Tuple (t (n,), T (n,)) over one period.
    """
    from scipy.interpolate import CubicSpline
    lf = np.log(freqs)
    amp = CubicSpline(lf, np.log(np.abs(H)))
    ph = CubicSpline(lf, np.unwrap(np.angle(H)))
    f0 = 1.0 / period
    k = np.arange(1, n_samples // 2)
    fk = k * f0
    lk = np.log(fk)
    a = np.where(lk <= lf[-1], amp(np.minimum(lk, lf[-1])), np.log(np.abs(H[-1])) + (np.log(np.abs(H[-1])) - np.log(np.abs(H[-2]))) / (lf[-1] - lf[-2]) * (lk - lf[-1]))
    p = np.where(lk <= lf[-1], ph(np.minimum(lk, lf[-1])), np.unwrap(np.angle(H))[-1] + (np.unwrap(np.angle(H))[-1] - np.unwrap(np.angle(H))[-2]) / (lf[-1] - lf[-2]) * (lk - lf[-1]))
    Hk = np.exp(a + 1j * p)
    ck = (1.0 - np.exp(-2j * np.pi * k * duty)) / (2j * np.pi * k)
    spec = np.zeros(n_samples, complex)
    spec[k] = ck * Hk
    t = np.arange(n_samples) * period / n_samples
    T = duty * H0 + 2.0 * np.real(np.fft.ifft(spec) * n_samples)
    return t, T
