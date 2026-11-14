#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_via_checks.py
@brief The checks of the via chapter made by the audit of 2.8.0 (REVIEW_A3.md): the closed forms, the barrel and the target radius against resolved solves, the Shen case like for like,
       the mode cap of the Analytic tiles and the copper-fill gain of the example board.
@details Parts (run one or several):
         * `closed`: the lattice radius of a point sink (a direct solve of the five-point stencil, 601 x 601), the Krogh cell and the micro peak against a quadrature of the radial
           solution, the annulus link, the mean potential of a uniform disc (e^(-1/4)), the Kron reduction against a direct solve of the star network;
         * `barrel`: an axisymmetric finite-volume solve (nothing of the program) of a plated barrel that is the only path between two drilled copper planes (laminate
           conductivity 1e-9, Dirichlet rims at 3 mm), against the program's construction in its continuum form `2 ln(R/r_t)/(2 pi k t) + (d + 0.5 t)/(k A)`;
         * `target`: `research/point-via-convergence/scripts/study_target_radius.py` (the unit cells of a via lattice in axisymmetric 3D against the layered model) with the
           barrel over `d` (as written) and over `d + 0.5 t_cu` (the program since 2.6.0), summarised by plane kind (drilled cases only where the hole removes at most 4 % of the plane);
         * `shen`: the Shen 12 x 12 board of `research/lumped-zones-adoption` read like for like (the part mean against the unit-cell solver's top mean 1.4611 K/W);
         * `modes`: the via effect of the Analytic with the 64-mode cap of the tile Green function raised to 128 and 256 (a module-level `min` patched in memory);
         * `fillgain`: the copper-fill gain of the example board in the five models.
         Run from the repository root: `.venv/bin/python releases/2.8.0/audit/scripts/study_via_checks.py closed barrel target shen modes fillgain`
         (`fillgain` peaks at about 4 GB with the FVM at 0.25 mm; the others stay under 0.6 GB and take seconds to a minute).
"""

import builtins
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.integrate import quad

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))


def part_closed():
    """!
    @brief The closed forms of the via against independent computations.
    @return None (prints).
    """
    from pcbthermal import viaconstriction, viawell
    n = 601
    c = n // 2
    N = n * n
    idx = np.arange(N).reshape(n, n)
    rows, cols, vals = [], [], []
    for di, dj in ((0, 1), (1, 0)):
        a = idx[:n - di, :n - dj].ravel()
        b = idx[di:, dj:].ravel()
        rows += [a, b]
        cols += [b, a]
        vals += [-np.ones(a.size)] * 2
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), (N, N)).tocsr() + sp.diags(4.0 * np.ones(N))
    bnd = np.zeros((n, n), bool)
    bnd[0] = bnd[-1] = bnd[:, 0] = bnd[:, -1] = True
    inner = ~bnd.ravel()
    q = np.zeros(N)
    q[idx[c, c]] = 1.0
    T = np.zeros(N)
    T[inner] = spla.spsolve(K[inner][:, inner].tocsc(), q[inner])     # unit links, Dirichlet 0 on the square boundary
    T = T.reshape(n, n)
    for r in (10, 20, 40):
        d = T[c, c] - T[c, c + r]
        print(f"lattice: r = {r}: r_eq = {r * math.exp(-2 * math.pi * d):.5f} cells (program {viawell.POINT_SINK_RADIUS:.5f}, e^-pi/2 {math.exp(-math.pi / 2):.5f})")
    for xi in (1.5, 3.0, 10.0, 50.0, 200.0):
        R = xi
        temp = lambda r: 0.5 * (R * R * math.log(r) - (r * r - 1.0) / 2.0)       # S = 1, unit generation, sink radius 1, insulated rim
        mean = quad(lambda r: temp(r) * 2 * math.pi * r, 1.0, R, limit=200)[0] / (math.pi * (R * R - 1.0))
        P = math.pi * (R * R - 1.0)
        print(f"Krogh xi = {xi}: quadrature {mean / P:.12f}, program {viaconstriction.krogh(1.0, R, 1.0):.12f}; "
              f"rim - mean {(temp(R) - mean) / P:.12f}, program {viaconstriction.rim_minus_mean(1.0, R, 1.0):.12f}")
    for ri, ro in ((1.0, 2.0), (1.0, 5.0), (0.3, 3.0)):
        temp = lambda r: 0.5 * ((ro * ro - r * r) / 2.0 - ri * ri * math.log(ro / r))
        mean = quad(lambda r: temp(r) * 2 * math.pi * r, ri, ro)[0] / (math.pi * (ro * ro - ri * ri))
        print(f"annulus {ri} to {ro}: quadrature {mean / (math.pi * (ro * ro - ri * ri)):.12f}, program {viaconstriction.annulus_out_resistance(1.0, ri, ro):.12f}")
    mean = quad(lambda r: (-(r * r - 1.0) / 2.0) / (2 * math.pi) * 2 * r, 0.0, 1.0)[0]
    print(f"uniform disc: equivalent circle {math.exp(-2 * math.pi * mean):.12f} of the radius (program TARGET_RATIO {viawell.TARGET_RATIO:.12f})")
    rng = np.random.default_rng(1)
    for trial in range(3):
        L = 4
        gg = rng.uniform(0.01, 0.1, L - 1)
        gw = rng.uniform(0.5, 50.0, L)
        if trial == 2:
            gw[1] = 0.0
        G = viawell.kron_barrel(gg, gw)
        V = rng.normal(size=L)
        Y = np.zeros((2 * L, 2 * L))
        for a_, b_, g_ in [(l, L + l, gw[l]) for l in range(L)] + [(L + k, L + k + 1, gg[k]) for k in range(L - 1)]:
            Y[a_, a_] += g_
            Y[b_, b_] += g_
            Y[a_, b_] -= g_
            Y[b_, a_] -= g_
        Vb = np.linalg.solve(Y[L:, L:], -Y[L:, :L] @ V)
        direct = Y[:L, :L] @ V + Y[:L, L:] @ Vb
        kron = np.array([sum(G[l, m] * (V[l] - V[m]) for m in range(L)) for l in range(L)])
        print(f"Kron trial {trial}: max |direct - reduced| = {np.abs(direct - kron).max():.1e} W")


def _barrel_solve(rv, tp, t, d, R, f=1.0):
    """!
    @brief Axisymmetric finite volumes of a plated barrel joining two drilled copper planes, the laminate a near insulator; resistance between the two rims.
    @param rv Drill radius in m (the plating is inside it).
    @param tp Plating thickness in m.
    @param t Copper thickness in m.
    @param d Dielectric gap in m.
    @param R Rim radius in m (Dirichlet: top rim 1 K, bottom rim 0 K, on the copper).
    @param f Refinement factor (1 or 2).
    @return float Resistance in K/W.
    """
    k_cu, k_lam = 385.0, 1e-9

    def graded(x0, x1, h0, ratio):
        """!
        @brief Geometric faces from x0 to x1.
        @param x0 Start in m.
        @param x1 End in m.
        @param h0 First cell in m.
        @param ratio Growth ratio.
        @return numpy.ndarray of faces in m.
        """
        pts, h = [x0], h0
        while pts[-1] < x1 - 1e-15:
            pts.append(min(pts[-1] + h, x1))
            h *= ratio
        return np.array(pts)

    ri = rv - tp
    rf = np.unique(np.concatenate([np.linspace(0, ri, 4), np.linspace(ri, rv, int(10 * f) + 1), graded(rv, R, tp / (10 * f), 1.08 ** (1 / f))]))
    H = d + 2 * t
    zc = np.linspace(0, t, int(10 * f) + 1)
    zl = graded(t, t + d / 2, t / (10 * f), 1.08 ** (1 / f))
    zf = np.unique(np.concatenate([zc, zl, H - zl[::-1], H - zc[::-1]]))
    nr, nz = len(rf) - 1, len(zf) - 1
    rcen, zcen = 0.5 * (rf[1:] + rf[:-1]), 0.5 * (zf[1:] + zf[:-1])
    dz = np.diff(zf)
    Rg, Zg = np.meshgrid(rcen, zcen)
    k = np.full((nz, nr), k_lam)
    k[((Zg < t) | (Zg > H - t)) & (Rg > rv)] = k_cu                  # the planes, drilled, from the barrel wall outward
    k[(Rg > ri) & (Rg < rv)] = k_cu                                   # the plating over the whole height
    k[Rg < ri] = 1e-12                                                # the open hole
    idx = np.arange(nr * nz).reshape(nz, nr)
    I, J, V = [], [], []
    diag = np.zeros(nr * nz)
    for j in range(nr - 1):
        g = 2 * math.pi * rf[j + 1] * dz / ((rf[j + 1] - rcen[j]) / k[:, j] + (rcen[j + 1] - rf[j + 1]) / k[:, j + 1])
        I += [idx[:, j], idx[:, j + 1]]
        J += [idx[:, j + 1], idx[:, j]]
        V += [-g, -g]
        np.add.at(diag, idx[:, j], g)
        np.add.at(diag, idx[:, j + 1], g)
    area = math.pi * (rf[1:] ** 2 - rf[:-1] ** 2)
    for i in range(nz - 1):
        g = area / ((zf[i + 1] - zcen[i]) / k[i] + (zcen[i + 1] - zf[i + 1]) / k[i + 1])
        I += [idx[i], idx[i + 1]]
        J += [idx[i + 1], idx[i]]
        V += [-g, -g]
        np.add.at(diag, idx[i], g)
        np.add.at(diag, idx[i + 1], g)
    q = np.zeros(nr * nz)
    gR = 2 * math.pi * R * dz * k[:, -1] / (rf[-1] - rcen[-1])
    top, bot = np.nonzero(zcen > H - t)[0], np.nonzero(zcen < t)[0]
    for i in top:
        diag[idx[i, -1]] += gR[i]
        q[idx[i, -1]] += gR[i]
    for i in bot:
        diag[idx[i, -1]] += gR[i]
    A = sp.coo_matrix((np.concatenate(V), (np.concatenate(I), np.concatenate(J))), (nr * nz, nr * nz)).tocsr() + sp.diags(diag)
    T = spla.spsolve(A.tocsc(), q).reshape(nz, nr)
    return 1.0 / sum(gR[i] * (1.0 - T[i, -1]) for i in top)


def part_barrel():
    """!
    @brief The barrel as the only path between two planes: the resolved resistance against the program's continuum construction.
    @return None (prints).
    """
    print("drill mm | t um | d mm | resolved K/W (f 1 / f 2) | program form, error | best r_t/r_v at a = 0.5 | best a at r_t = 0.78 r_v")
    for D in (0.2, 0.3, 0.6):
        for t in (18e-6, 35e-6, 70e-6):
            for d in (0.1e-3, 0.4e-3, 1.5e-3):
                rv, tp, R = D / 2 * 1e-3, 25e-6, 3e-3
                r1, r2 = _barrel_solve(rv, tp, t, d, R, 1.0), _barrel_solve(rv, tp, t, d, R, 2.0)
                S, A = 385.0 * t, math.pi * (rv ** 2 - (rv - tp) ** 2)
                prog = 2 * math.log(R / (math.exp(-0.25) * rv)) / (2 * math.pi * S) + (d + 0.5 * t) / (385.0 * A)
                x = R / rv / math.exp((r2 - (d + 0.5 * t) / (385.0 * A)) * 2 * math.pi * S / 2)
                a = ((r2 - 2 * math.log(R / (math.exp(-0.25) * rv)) / (2 * math.pi * S)) * 385.0 * A - d) / t
                print(f"{D:.1f} | {t * 1e6:.0f} | {d * 1e3:.2f} | {r1:.3f} / {r2:.3f} | {prog:.3f}, {(prog / r2 - 1) * 100:+.2f} % | {x:.3f} | {a:+.2f}")


def _load_target():
    """!
    @brief Load the target-radius study of research/point-via-convergence as a module.
    @return module.
    """
    path = ROOT / "research/point-via-convergence/scripts/study_target_radius.py"
    spec = importlib.util.spec_from_file_location("study_target_radius", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def part_target():
    """!
    @brief The target radius e^(-1/4) r_v against the axisymmetric unit cells, with the barrel over d and over d + 0.5 t_cu.
    @return None (prints).
    """
    mod = _load_target()
    plain = mod.solve_layered
    for frac in (0.0, 0.5):

        def layered(r_cell, r_t, gaps, g_barrel, *args, _f=frac, **kw):
            """!
            @brief The study's layered model with the barrel length d + frac t_cu.
            @param r_cell Rim radius in m.
            @param r_t Equipotential radius in m.
            @param gaps Gap thicknesses in m.
            @param g_barrel Barrel conductances over d in W/K.
            @param args Other positional arguments of the study's function.
            @param _f Extra length in copper thicknesses.
            @param kw Keyword arguments of the study's function.
            @return float Maximum rise in K.
            """
            g = [gb * gap / (gap + _f * mod.T_CU) for gb, gap in zip(g_barrel, gaps)]
            return plain(r_cell, r_t, gaps, g, *args, **kw)

        mod.solve_layered = layered
        by = {}
        for name, gaps in mod.STACKS.items():
            for pitch in (2e-3, 4e-3):
                for dia in (0.2e-3, 0.3e-3, 0.6e-3, 1.0e-3):
                    for k_fill in (0.0, 385.0):
                        for drilled in ((False, True) if k_fill == 0 else (False,)):
                            if drilled and math.pi * (dia / 2) ** 2 / pitch ** 2 > 0.04:
                                continue                      # the hole removes more than 4 % of the plane (left out, as in the study's README)
                            r = mod.case(pitch, dia, gaps, k_fill, drilled)
                            key = "drilled" if drilled else "whole"
                            by.setdefault(key, []).append((r["err78"], r["r_star"]))
        for key, v in by.items():
            e = [x[0] for x in v]
            rs = [x[1] for x in v if x[1] == x[1]]
            print(f"barrel over d + {frac} t_cu, planes {key} ({len(v)} cases): error of E at 0.78 r_v {min(e):+.1f} to {max(e):+.1f} %, r_t*/r_v {min(rs):.2f} to {max(rs):.2f}")
    mod.solve_layered = plain


def part_shen():
    """!
    @brief The Shen 12 x 12 board, the program's part mean and hottest point against the unit-cell solver's top mean.
    @return None (prints).
    """
    sys.path.insert(0, str(ROOT / "research/lumped-zones-adoption/lib"))
    import shen_case as sc
    from pcbthermal import SolverOptions, simulate
    from pcbthermal.analysis import heater_stats
    ref = 1.4611                                                      # research/lumped-zones-adoption 9.3, the fine unit cell over 144 (mean of the top)
    p = sc.program_problem()
    for m, cell in (("fvm", 0.2), ("fvm", 0.1), ("fvm", 0.05), ("fdm", 0.1), ("solid3d", 0.1), ("lumped", 1.0), ("analytic", 1.0)):
        r = simulate(p, SolverOptions(models=(m,), cell_mm=cell)).results[m]
        tm = heater_stats(r, p)[0]["t_mean"] - p.board.ambient
        tx = r.t_max - p.board.ambient
        print(f"{m} {cell} mm: mean {tm:.4f} K/W ({(tm / ref - 1) * 100:+.1f} %), hottest {tx:.4f} K/W ({(tx / ref - 1) * 100:+.1f} %)")


def part_modes():
    """!
    @brief The Analytic via effect with the 64-mode cap of the tile Green function and with 128 and 256.
    @return None (prints).
    """
    from pcbthermal import SolverOptions, analytic, simulate
    from pcbthermal.examples import example_board
    from pcbthermal.model import Problem
    cap = [64]

    def capped(*a, **k):
        """!
        @brief builtins.min, except that min(x, 64) becomes min(x, cap).
        @param a Positional arguments of min.
        @param k Keyword arguments of min.
        @return The minimum.
        """
        if len(a) == 2 and a[1] == 64:
            return builtins.min(a[0], cap[0])
        return builtins.min(*a, **k)

    def board(w, h, n, pitch):
        """!
        @brief Four full planes, a 2 W 8 x 8 mm part over an n x n array of open 0.3 mm vias (or none).
        @param w Board width in mm.
        @param h Board height in mm.
        @param n Array side.
        @param pitch Pitch in mm.
        @return function(with_vias) -> Problem.
        """
        def make(v):
            """!
            @brief Build the board.
            @param v With the vias.
            @return Problem.
            """
            p = Problem.new(w, h, 4, 1.6, 35.0, h_top=10.0, h_bottom=10.0)
            for layer in (1, 2, 3, 4):
                p.add_zone(layer, rect=(0, 0, w, h))
            p.add_heater(1, 2.0, rect=(w / 2 - 4, h / 2 - 4, w / 2 + 4, h / 2 + 4), name="U")
            if v:
                for i in range(n):
                    for j in range(n):
                        p.add_via(w / 2 + (i - (n - 1) / 2) * pitch, h / 2 + (j - (n - 1) / 2) * pitch, 0.3)
            return p
        return make

    def fill(v):
        """!
        @brief The example board, open or copper-filled vias.
        @param v True: copper-filled.
        @return Problem.
        """
        p = example_board()
        if v:
            for via in p.vias:
                via.fill_k = 385.0
        return p

    cases = {"example board, copper-fill gain": lambda v: fill(not v), "60 x 40, 5 x 5 at 1 mm": board(60, 40, 5, 1.0),
             "200 x 150, 5 x 5 at 1 mm": board(200, 150, 5, 1.0), "200 x 150, 7 x 7 at 1 mm": board(200, 150, 7, 1.0)}
    analytic.min = capped
    try:
        for name, make in cases.items():
            row = []
            for c in (64, 128, 256):
                cap[0] = c
                t0 = simulate(make(False), SolverOptions(models=("analytic",), cell_mm=0.5)).results["analytic"].t_max
                t1 = simulate(make(True), SolverOptions(models=("analytic",), cell_mm=0.5)).results["analytic"].t_max
                row.append(f"{c}: {t0 - t1:.4f} K")
            print(f"{name}: " + ", ".join(row))
    finally:
        del analytic.min


def part_fillgain():
    """!
    @brief Copper-fill gain of the example board (validation 18.1).
    @return None (prints).
    """
    from pcbthermal import SolverOptions, simulate
    from pcbthermal.examples import example_board

    def tmax(m, c, filled):
        """!
        @brief Hottest temperature of the example board.
        @param m Model key.
        @param c Cell in mm.
        @param filled Copper-filled vias.
        @return float degC.
        """
        p = example_board()
        if filled:
            for v in p.vias:
                v.fill_k = 385.0
        return simulate(p, SolverOptions(models=(m,), cell_mm=c)).results[m].t_max

    for m, cells in (("fvm", (1.0, 0.8, 0.5, 0.25)), ("fdm", (1.0, 0.8, 0.5)), ("solid3d", (1.0, 0.8)), ("lumped", (1.0, 0.8, 0.5)), ("analytic", (1.0, 0.8, 0.5))):
        print(m, ", ".join(f"{c} mm: {tmax(m, c, True) - tmax(m, c, False):+.3f} K" for c in cells), flush=True)


PARTS = {"closed": part_closed, "barrel": part_barrel, "target": part_target, "shen": part_shen, "modes": part_modes, "fillgain": part_fillgain}


def main():
    """!
    @brief Run the parts named on the command line (all but fillgain by default).
    @return None.
    """
    names = sys.argv[1:] or ["closed", "barrel", "target", "shen", "modes"]
    for name in names:
        print(f"## {name}")
        PARTS[name]()


if __name__ == "__main__":
    main()
