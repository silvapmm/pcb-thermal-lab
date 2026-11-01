#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_target_radius.py
@brief Is the target radius r_t = 0.78 r_v of the recommended via treatment general? An axisymmetric 3D solve of the unit cell of a via lattice against the layered model.
@details Question (review of the folder): the radius that the mean-potential treatment reproduces, `r_t = e^(-1/4) r_v`, was derived from the uniform sink density of the
         fine-grid reference (`lib/sheets2d.py`, which spreads the barrel over its disc) and checked against one 3D solver on a four-layer 1.6 mm board. Does it hold on
         other stack-ups, drill diameters, pitches and fills, and with the plane drilled through as on a real board?
         Method (written for the review, independent of `lib/` and of the program: numpy and scipy only):
         * the unit cell of a square via lattice of pitch p is replaced by the circle of the same area (radius p / sqrt(pi), insulated rim; the same approximation is made
           on both sides, so it cancels in the comparison);
         * **3D**: axisymmetric finite volumes in (r, z), the copper planes (35 um) and the dielectric gaps as slabs, the barrel drawn at its size (plating 25 um, core of air
           or copper), FR-4 0.3 W/mK through and 0.3 or 0.9 W/mK in the plane, the plane either whole across the bore (as `layered3d.py` and the program's 3D solid draw
           it) or drilled (the core material inside the plating in the plane slabs too, as on a real board; the source is then put on the copper only);
         * **layered model**: one node per plane and radial cell (sheet conductance k_cu t_cu plus the in-plane FR-4 of half the adjacent gaps, vertical k_z / d per area,
           the film on the bottom), the via as one barrel node per plane on an equipotential circle of radius r_t, the barrel conductance k_cu A / d per gap with A the
           program's thermal area (ring, plus the core for a copper fill);
         * via effect E = T_max(no via) - T_max(via) of the top copper; the radius r_t* for which the layered E equals the 3D E is found by root finding.
         Output: one row per case with E (3D), the error of the layered E with r_t = 0.78 r_v and r_t = r_v (percent of E), r_t* / r_v and the energy balance of the 3D solve.
         Run from the repository root: `.venv/bin/python research/point-via-convergence/scripts/study_target_radius.py [--k-inplane 0.9] [--conv]` (about 10 s).
"""

import argparse
import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.optimize import brentq

K_CU = 385.0                                       # copper conductivity, W/mK (the program's value)
T_CU = 35e-6                                       # copper plane thickness, m
PLATING = 25e-6                                    # barrel plating, m
K_AIR = 0.026                                      # air in an open bore, W/mK

# Gap thicknesses (m) of the stack-ups: equal gaps of a 1.6 mm board with 2, 4 and 6 planes, the JLCPCB-like 4-layer build (thin prepreg, thick core), a 0.8 mm 2-layer
STACKS = {
    "2L 1.6 mm": [1.6e-3 - 2 * T_CU],
    "4L 1.6 mm": [(1.6e-3 - 4 * T_CU) / 3] * 3,
    "6L 1.6 mm": [(1.6e-3 - 6 * T_CU) / 5] * 5,
    "4L 0.21/1.07/0.21": [0.2104e-3, 1.065e-3, 0.2104e-3],
    "2L 0.8 mm": [0.8e-3 - 2 * T_CU],
}


def radial_faces(r_cell, r_via, fine=2.5e-6, n_far=80):
    """!
    @brief Radial cell faces: uniform and fine up to just beyond the via, geometric to the rim; the faces of the plating are exact.
    @param r_cell Rim radius in m.
    @param r_via Drill radius in m.
    @param fine Cell size near the via in m.
    @param n_far Number of geometric faces beyond.
    @return numpy.ndarray of increasing face radii starting at 0.
    """
    lim = r_via + 60e-6
    pts = [0.0] + list(np.arange(fine, lim, fine)) + list(np.geomspace(lim, r_cell, n_far)) + [r_via - PLATING, r_via]
    f = np.unique(np.round(np.array(pts), 12))
    return f[(f >= 0) & (f <= r_cell)]


def _laplacian(n, links, diag_extra):
    """!
    @brief Assemble a symmetric conductance matrix from links.
    @param n Number of unknowns.
    @param links List of (a, b, g) arrays (node indices and conductances in W/K).
    @param diag_extra Array (n,) added to the diagonal (conductances to the ambient).
    @return scipy.sparse.csc_matrix.
    """
    rows, cols, vals = [], [], []
    diag = np.array(diag_extra, dtype=float)
    for a, b, g in links:
        a, b = np.atleast_1d(a).ravel(), np.atleast_1d(b).ravel()
        g = np.broadcast_to(g, a.shape).ravel()
        rows += [a, b]
        cols += [b, a]
        vals += [-g, -g]
        np.add.at(diag, a, g)
        np.add.at(diag, b, g)
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() + sp.diags(diag)
    return K.tocsc()


def solve_3d(r_cell, r_via, gaps, k_fill, k_z, k_r, h_bottom, q, drilled, via=True, n_cu=3, n_gap=24, fine=2.5e-6):
    """!
    @brief Axisymmetric 3D steady state of the circular unit cell; maximum rise of the top copper and the energy balance.
    @param r_cell Rim radius in m.
    @param r_via Drill radius in m.
    @param gaps Gap thicknesses in m.
    @param k_fill Core conductivity in W/mK (0 = air).
    @param k_z Through conductivity of the dielectric in W/mK.
    @param k_r In-plane conductivity of the dielectric in W/mK.
    @param h_bottom Bottom film in W/m2K (the top is adiabatic, as in the unit cell of the study).
    @param q Source on the top in W/m2.
    @param drilled True: the plane slabs are drilled (core material inside the plating).
    @param via False: no via at all (the reference board).
    @param n_cu Slabs per copper plane.
    @param n_gap Slabs per gap.
    @param fine Radial cell near the via in m.
    @return tuple (maximum rise of the top copper in K, relative energy balance error).
    """
    L = len(gaps) + 1
    rf = radial_faces(r_cell, r_via, fine)
    nr = len(rf) - 1
    rc = 0.5 * (rf[:-1] + rf[1:])
    r_in = r_via - PLATING
    slabs = []
    for layer in range(L):
        slabs += [(T_CU / n_cu, "cu")] * n_cu
        if layer < L - 1:
            slabs += [(gaps[layer] / n_gap, "gap")] * n_gap
    nz = len(slabs)
    kr, kz = np.zeros((nz, nr)), np.zeros((nz, nr))
    k_core = k_fill if k_fill > 0 else K_AIR
    for iz, (_, kind) in enumerate(slabs):
        if kind == "cu":
            kr[iz] = kz[iz] = K_CU
            if via and drilled:
                kr[iz, rc < r_in] = kz[iz, rc < r_in] = k_core
        else:
            kr[iz], kz[iz] = k_r, k_z
            if via:
                kr[iz, rc < r_in] = kz[iz, rc < r_in] = k_core
                ring = (rc >= r_in) & (rc < r_via)
                kr[iz, ring] = kz[iz, ring] = K_CU
    dz = np.array([s[0] for s in slabs])
    idx = np.arange(nz * nr).reshape(nz, nr)
    links = []
    for iz in range(nz):
        # Radial conductance between cell centres through the shared face: two half-cells of a cylindrical shell in series
        res = (np.log(rf[1:-1] / rc[:-1]) / (2 * math.pi * kr[iz, :-1] * dz[iz]) + np.log(rc[1:] / rf[1:-1]) / (2 * math.pi * kr[iz, 1:] * dz[iz]))
        links.append((idx[iz, :-1], idx[iz, 1:], 1.0 / res))
    area = math.pi * (rf[1:] ** 2 - rf[:-1] ** 2)
    for iz in range(nz - 1):
        links.append((idx[iz], idx[iz + 1], 1.0 / (dz[iz] / 2 / (kz[iz] * area) + dz[iz + 1] / 2 / (kz[iz + 1] * area))))
    g_bottom = 1.0 / (1.0 / (h_bottom * area) + dz[-1] / 2 / (kz[-1] * area))
    diag = np.zeros(nz * nr)
    diag[idx[-1]] += g_bottom
    K = _laplacian(nz * nr, links, diag)
    copper = kz[0] >= K_CU                                   # the source sits on the copper of the top plane (all of it unless drilled)
    Q = np.zeros(nz * nr)
    Q[idx[0]] = q * np.where(copper, area, 0.0) * (math.pi * r_cell ** 2 / area[copper].sum())
    T = spla.spsolve(K, Q).reshape(nz, nr)
    balance = (g_bottom * T[-1]).sum() / Q.sum() - 1.0
    return float(T[0][copper].max()), float(balance)


def solve_layered(r_cell, r_t, gaps, g_barrel, k_z, k_r, h_bottom, q, via=True, nr=400):
    """!
    @brief Layered model of the circular unit cell with the via as an equipotential circle of radius r_t in every plane; maximum rise of the top plane.
    @param r_cell Rim radius in m.
    @param r_t Radius of the circle through which every plane reaches its barrel node, in m.
    @param gaps Gap thicknesses in m.
    @param g_barrel Barrel conductance of every gap in W/K.
    @param k_z Through conductivity of the dielectric in W/mK.
    @param k_r In-plane conductivity of the dielectric in W/mK.
    @param h_bottom Bottom film in W/m2K.
    @param q Source on the top in W/m2.
    @param via False: no via.
    @param nr Radial cells (geometric, exact logarithmic conductances).
    @return float Maximum rise in K.
    """
    L = len(gaps) + 1
    S = np.array([K_CU * T_CU + k_r * ((gaps[l - 1] / 2 if l > 0 else 0.0) + (gaps[l] / 2 if l < L - 1 else 0.0)) for l in range(L)])
    gk = np.array([k_z / d for d in gaps])
    rf = np.geomspace(r_t if via else 1e-9, r_cell, nr + 1)
    rc = np.sqrt(rf[:-1] * rf[1:])
    area = math.pi * (rf[1:] ** 2 - rf[:-1] ** 2)
    n = L * nr + (L if via else 0)
    idx = np.arange(L * nr).reshape(L, nr)
    links = [(idx[l, :-1], idx[l, 1:], 2 * math.pi * S[l] / np.log(rc[1:] / rc[:-1])) for l in range(L)]
    links += [(idx[k], idx[k + 1], gk[k] * area) for k in range(L - 1)]
    Q = np.zeros(n)
    Q[idx[0]] = q * area
    diag = np.zeros(n)
    diag[idx[-1]] += h_bottom * area
    if via:
        b = L * nr + np.arange(L)
        links += [(b[l], idx[l, 0], 2 * math.pi * S[l] / math.log(rc[0] / r_t)) for l in range(L)]
        a0 = math.pi * r_t * r_t                             # the disc inside the circle: its source, dielectric and film go to the barrel nodes
        links += [(b[k], b[k + 1], g_barrel[k] + gk[k] * a0) for k in range(L - 1)]
        Q[b[0]] = q * a0
        diag[b[-1]] += h_bottom * a0
    T = spla.spsolve(_laplacian(n, links, diag), Q)
    return float(T[idx[0]].max())


def case(pitch, dia, gaps, k_fill, drilled, k_z=0.3, k_r=0.3, h_bottom=200.0, fine=2.5e-6, n_gap=24):
    """!
    @brief One case: 3D via effect, errors of the layered model at r_t = 0.78 r_v and r_v, and the matching radius.
    @param pitch Pitch of the lattice in m.
    @param dia Drill diameter in m.
    @param gaps Gap thicknesses in m.
    @param k_fill Core conductivity in W/mK (0 = open).
    @param drilled True: planes drilled through.
    @param k_z Through conductivity of the dielectric in W/mK.
    @param k_r In-plane conductivity of the dielectric in W/mK.
    @param h_bottom Bottom film in W/m2K.
    @param fine Radial cell near the via in m.
    @param n_gap Slabs per gap.
    @return dict with E3 (K), err78 and err100 (percent of E3), r_star (r_t* / r_v, nan if outside 0.05 to 5) and balance.
    """
    r_cell, r_via, q = pitch / math.sqrt(math.pi), dia / 2, 1.0 / (pitch * pitch)
    t0, b0 = solve_3d(r_cell, r_via, gaps, k_fill, k_z, k_r, h_bottom, q, drilled, via=False, n_gap=n_gap, fine=fine)
    t1, b1 = solve_3d(r_cell, r_via, gaps, k_fill, k_z, k_r, h_bottom, q, drilled, via=True, n_gap=n_gap, fine=fine)
    e3 = t0 - t1
    r_in = r_via - PLATING
    a_th = math.pi * (r_via ** 2 - r_in ** 2) + (min(k_fill / K_CU, 1.0) * math.pi * r_in ** 2 if k_fill > 0 else 0.0)   # the program's thermal area
    g_barrel = [K_CU * a_th / d for d in gaps]
    s0 = solve_layered(r_cell, r_via, gaps, g_barrel, k_z, k_r, h_bottom, q, via=False)

    def e_layered(r_t):
        """!
        @brief Via effect of the layered model.
        @param r_t Radius of the equipotential circle in m.
        @return float E in K.
        """
        return s0 - solve_layered(r_cell, r_t, gaps, g_barrel, k_z, k_r, h_bottom, q)

    try:
        r_star = brentq(lambda x: e_layered(x * r_via) - e3, 0.05, 5.0, xtol=1e-4)
    except ValueError:
        r_star = float("nan")
    return {"E3": e3, "err78": (e_layered(math.exp(-0.25) * r_via) / e3 - 1) * 100, "err100": (e_layered(r_via) / e3 - 1) * 100, "r_star": r_star,
            "balance": max(abs(b0), abs(b1))}


def main():
    """!
    @brief Run the sweep (or the grid convergence of one case) and print the table.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--k-inplane", type=float, default=0.3, help="in-plane conductivity of the dielectric (W/mK)")
    ap.add_argument("--conv", action="store_true", help="grid convergence of the 4-layer, 4 mm, 0.3 mm open case")
    args = ap.parse_args()
    if args.conv:
        for fine, n_gap in ((5e-6, 12), (2.5e-6, 24), (1.25e-6, 48)):
            r = case(4e-3, 0.3e-3, STACKS["4L 1.6 mm"], 0.0, False, fine=fine, n_gap=n_gap)
            print(f"radial cell {fine * 1e6:.2f} um, {n_gap} slabs per gap: E3 {r['E3']:.4f} K, err 0.78 {r['err78']:+.3f} %, err 1.0 {r['err100']:+.3f} %, "
                  f"r*/r_v {r['r_star']:.4f}")
        return
    print(f"FR-4 in-plane {args.k_inplane} W/mK; E3 per W of the cell; errors in percent of E3")
    print("| stack-up | pitch mm | drill mm | fill | plane | E3 (K/W) | err at 0.78 r_v | err at r_v | r_t* / r_v | balance |")
    print("| :-- | --: | --: | :-- | :-- | --: | --: | --: | --: | --: |")
    for name, gaps in STACKS.items():
        for pitch in (2e-3, 4e-3):
            for dia in (0.2e-3, 0.3e-3, 0.6e-3, 1.0e-3):
                for k_fill in (0.0, 385.0):
                    for drilled in ((False, True) if k_fill == 0 else (False,)):       # a copper core drilled through is the same copper
                        r = case(pitch, dia, gaps, k_fill, drilled, k_r=args.k_inplane)
                        print(f"| {name} | {pitch * 1e3:.0f} | {dia * 1e3:.1f} | {'copper' if k_fill else 'open'} | {'drilled' if drilled else 'whole'} | "
                              f"{r['E3']:.2f} | {r['err78']:+.2f} | {r['err100']:+.2f} | {r['r_star']:.2f} | {r['balance']:.0e} |", flush=True)


if __name__ == "__main__":
    main()
