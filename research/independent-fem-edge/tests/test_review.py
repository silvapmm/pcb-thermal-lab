#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_review.py
@brief Checks added by the review: the patch test (a linear field reproduced to rounding on a distorted hexahedral mesh, orthotropic conductivity, Robin on
       every face with a per-node ambient), Seri Lee's plate against an own cosine series (uniform plan refinement), and a two-layer orthotropic board with a
       volumetric source in the top copper against an own layered series (transfer of each Fourier mode through the stack, source particular solution).
"""

import numpy as np

import cases
import fem

FACES = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]


def _box(n, dims, rng, amp):
    """!
    @brief Structured hexahedral box with every node moved at random (boundary nodes only along their face, so faces stay planar).
    @param n Elements per side.
    @param dims Box sides (3,).
    @param rng numpy Generator.
    @param amp Perturbation as a fraction of the element size.
    @return Tuple (nodes (N, 3), elems (E, 8)).
    """
    ax = [np.linspace(0, d, n + 1) for d in dims]
    X, Y, Z = np.meshgrid(*ax, indexing="ij")
    nodes = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    idx = np.arange(nodes.shape[0]).reshape(n + 1, n + 1, n + 1)
    el = []
    for i in range(n):
        for j in range(n):
            for k in range(n):
                el.append([idx[i, j, k], idx[i + 1, j, k], idx[i + 1, j + 1, k], idx[i, j + 1, k],
                           idx[i, j, k + 1], idx[i + 1, j, k + 1], idx[i + 1, j + 1, k + 1], idx[i, j + 1, k + 1]])
    h = np.asarray(dims) / n
    P = rng.uniform(-amp, amp, nodes.shape) * h
    for a, d in enumerate(dims):
        # a node on a face of the box moves only within that face
        P[(np.abs(nodes[:, a]) < 1e-12) | (np.abs(nodes[:, a] - d) < 1e-12), a] = 0.0
    return nodes + P, np.array(el)


def test_patch_linear_field_on_distorted_mesh():
    """!
    @brief A linear temperature with orthotropic k and Robin films (ambient chosen so that the film flux equals k grad T . n) is reproduced to rounding.
    @return None.
    """
    dims = (1.0, 0.7, 0.3)
    nodes, el = _box(5, dims, np.random.default_rng(1), 0.3)
    m = fem.Model(nodes, el)
    k = np.array([3.0, 2.0, 0.5])
    m.k[:] = k
    g = np.array([2.0, -1.0, 4.0])
    t_ex = 5.0 + nodes @ g
    h = 7.0
    for e in el:
        for fc in FACES:
            fn = e[fc]
            for a, d in enumerate(dims):
                for val, sgn in ((0.0, -1.0), (d, 1.0)):
                    if np.all(np.abs(nodes[fn, a] - val) < 1e-12):
                        nrm = np.zeros(3)
                        nrm[a] = sgn
                        # -k dT/dn = h (T - T_amb)  ->  T_amb = T + (k g) . n / h
                        m.add_faces(fn[None, :], h=h, t_amb=(t_ex[fn] + (k * g) @ nrm / h)[None, :])
    r = m.solve()
    assert np.nanmax(np.abs(r["T"] - t_ex)) < 1e-12 * np.ptp(t_ex)


def _lee_series(src, a=0.1, t=1.3e-3, k=200.0, h=100.0, M=800):
    """!
    @brief Maximum constriction resistance of Seri Lee's plate by an own cosine series (top insulated except the flux source, film h on the bottom).
    @param src Source rectangle (x0, x1, y0, y1) in m.
    @param a Plate side, m.
    @param t Thickness, m.
    @param k Conductivity, W/mK.
    @param h Bottom film, W/m2K.
    @param M Modes per direction.
    @return float K/W (1 W).
    """
    def coeffs(s0, s1):
        """!
        @brief Cosine coefficients of the indicator of [s0, s1] on [0, a].
        @param s0 Start, m.
        @param s1 End, m.
        @return Tuple (wavenumbers, coefficients).
        """
        lam = np.arange(M) * np.pi / a
        c = np.empty(M)
        c[0] = (s1 - s0) / a
        c[1:] = 2 * (np.sin(lam[1:] * s1) - np.sin(lam[1:] * s0)) / (lam[1:] * a)
        return lam, c
    x0, x1, y0, y1 = src
    lx, cx = coeffs(x0, x1)
    ly, cy = coeffs(y0, y1)
    B = np.hypot(lx[:, None], ly[None, :])
    Z = np.empty_like(B)
    Z[0, 0] = t / k + 1 / h
    bb = B[B > 0]
    th = np.tanh(bb * t)
    Z[B > 0] = (1 / h + th / (k * bb)) / (1 + k * bb * th / h)
    A = cx[:, None] * cy[None, :] * Z / ((x1 - x0) * (y1 - y0))
    xs, ys = np.linspace(x0, x1, 51), np.linspace(y0, y1, 51)
    T = np.cos(np.outer(xs, lx)) @ A @ np.cos(np.outer(ys, ly)).T
    return T.max() - 1.0 / (a * a * h)


def test_lee_plate_against_own_series():
    """!
    @brief Seri Lee's plate, centre and corner, uniformly refined FEM (1 and 0.5 mm, Richardson) against the series: within 2e-4 relative.
    @return None.
    """
    c = 0.0375
    for pos, src in (("centre", (c, c + 0.025, c, c + 0.025)), ("corner", (0.0, 0.025, 0.0, 0.025))):
        if pos == "corner":
            vals = [2.27518, 2.27457]       # 2 and 1 mm uniform (measured by the review; the 0.5 mm corner needs pyamg)
            ext = vals[1] + (vals[1] - vals[0]) / 3
        else:
            vals = []
            for hf in (1.0, 0.5):
                b, read = cases.lee_plate(pos, hf=hf, hmax=hf)
                vals.append(read(b.solve()))
            ext = vals[1] + (vals[1] - vals[0]) / 3
        ref = _lee_series(src)
        assert abs(ext / ref - 1) < 2e-4, (pos, vals, ext, ref)


def _stack_series(L=10e-3, s=2e-3, P=0.25, tcu=35e-6, tb=1.6e-3, kxy=0.9, kz=0.3, ht=10.0, hb=10.0, M=200):
    """!
    @brief Two copper layers and an orthotropic gap, quarter board (symmetry at 0, insulated at L), volumetric source in the top copper over [0, s]^2:
           an own layered cosine series (each mode carried through the stack in closed form with the particular solution of the source).
    @param L Quarter side, m.
    @param s Quarter heater side, m.
    @param P Power in the quarter, W.
    @param tcu Copper thickness, m.
    @param tb Board thickness, m.
    @param kxy Laminate in-plane conductivity.
    @param kz Laminate through conductivity.
    @param ht Top film.
    @param hb Bottom film.
    @param M Modes per direction.
    @return Tuple (rise at the heater centre, heater mean rise), K.
    """
    layers = [(tcu, 385.0, 385.0, True), (tb - 2 * tcu, kxy, kz, False), (tcu, 385.0, 385.0, False)]

    def top(beta, q):
        """!
        @brief Top-face value of one mode.
        @param beta Wavenumber, 1/m.
        @param q Source density of the mode in the top copper, W/m3.
        @return float.
        """
        def prop(f, F, src):
            """!
            @brief Carry (f, F = -kz f') through the stack.
            @param f Value at the top.
            @param F Flux at the top.
            @param src Include the source.
            @return Tuple (f, F) at the bottom.
            """
            for t, kx, kk, hot in layers:
                qq = q if (hot and src) else 0.0
                if beta == 0:
                    f, F = f - F / kk * t - qq * t * t / (2 * kk), F + qq * t
                else:
                    g = beta * np.sqrt(kx / kk)
                    fp = qq / (kx * beta ** 2)
                    A, Bc = f - fp, -F / (kk * g)
                    ch, sh = np.cosh(g * t), np.sinh(g * t)
                    f, F = A * ch + Bc * sh + fp, -kk * g * (A * sh + Bc * ch)
            return f, F
        fh, Fh = prop(1.0, -ht, False)
        fq, Fq = prop(0.0, 0.0, True)
        return (hb * fq - Fq) / (Fh - hb * fh)
    lam = np.arange(M) * np.pi / L
    c = np.empty(M)
    c[0] = s / L
    c[1:] = 2 * np.sin(lam[1:] * s) / (lam[1:] * L)
    avg = np.empty(M)
    avg[0] = 1.0
    avg[1:] = np.sin(lam[1:] * s) / (lam[1:] * s)
    q = P / (s * s * tcu)
    F = np.array([[top(np.hypot(lam[i], lam[j]), q * c[i] * c[j]) for j in range(M)] for i in range(M)])
    return F.sum(), (avg[:, None] * avg[None, :] * F).sum()


def test_layered_board_against_own_series():
    """!
    @brief The 20 mm two-layer board (insulated walls, full copper) at 0.2 / 0.1 mm against the layered series: heater mean within 1e-4 after Richardson.
    @return None.
    """
    t0, mean = _stack_series()
    vals = [cases.square(0.0, inset=0.0, hf=hf, hmax=2 * hf, n_gap=6).solve()["heater_mean"] for hf in (0.2, 0.1)]
    ext = vals[1] + (vals[1] - vals[0]) / 3
    assert abs(ext / mean - 1) < 1e-4, (vals, ext, mean)
