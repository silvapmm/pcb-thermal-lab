#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_flux_tube_sources.py
@brief Equations 21 to 39 of Yovanovich, Culham and Teertstra (1998) evaluated against each other: the flux-tube series, its printed correlations, the Song and Lee closed form and the layer-on-half-space limits.
@details The paper (IEEE Trans. CPMT-A 21 (1), pages 168 to 176, pages 4 to 6 of the file read as images) prints the same quantity in four ways, which makes a self-consistency check that does not need
         a second solver: (a) the series of equation 22 (isoflux source on a flux tube, psi = 4 k a Rc) against the correlation of equation 24 (printed as accurate over 0 < eps < 0.9) and the
         limit eps -> 0 of 32 / (3 pi^2) = 1.08076; (b) the series of equation 21 (equivalent isothermal flux) against equation 23; (c) the Song and Lee closed form of equations 27 to 30 against the series
         of equation 22 with a large Biot number (the paper says within 10 %); (d) the thin-layer (equation 38) and thick-layer (equation 39) approximations of Dryden against the integral of equation 34.
         Run: .venv/bin/python research/theory-sources/scripts/study_flux_tube_sources.py (from the repository root; under a second).
"""

import numpy as np
from scipy.integrate import quad
from scipy.special import j0, j1, jn_zeros

ROOTS = jn_zeros(1, 4000)                                       # delta_n: positive roots of J1 (below equation 18)


def psi_isoflux_series(eps, tau=50.0, bi=np.inf):
    """!
    @brief Equation 22 with the film function of equations 15 to 17 (flux tube, uniform flux over the source).
    @param eps Relative source radius a / b.
    @param tau Relative thickness t / b of the tube.
    @param bi Biot number h b / k at the sink (inf = isothermal sink).
    @return float psi = 4 k a Rc.
    """
    d = ROOTS
    if np.isinf(bi):
        phi_n = np.tanh(d * tau)                                # equation 19
    else:
        phi_n = (d + bi * np.tanh(d * tau)) / (d * np.tanh(d * tau) + bi)   # equation 17 with kappa = 1 (B_n = 1)
    return 16.0 / (np.pi * eps) * np.sum(j1(d * eps) ** 2 / (d ** 3 * j0(d) ** 2) * phi_n)


def psi_isothermal_flux_series(eps, tau=50.0):
    """!
    @brief Equation 21 (equivalent isothermal flux, mu = -1/2).
    @param eps Relative source radius.
    @param tau Relative thickness.
    @return float psi.
    """
    d = ROOTS
    return 8.0 / (np.pi * eps) * np.sum(j1(d * eps) * np.sin(d * eps) / (d ** 3 * j0(d) ** 2) * np.tanh(d * tau))


def psi_24(e):
    """!
    @brief Equation 24, the printed correlation of the isoflux psi.
    @param e Relative source radius.
    @return float psi.
    """
    return 1.08076 - 1.41042 * e + 0.26604 * e ** 3 - 0.00016 * e ** 5 + 0.058266 * e ** 7


def psi_23(e):
    """!
    @brief Equation 23, the printed correlation of the equivalent-isothermal psi.
    @param e Relative source radius.
    @return float psi.
    """
    return 1.0 - 1.40978 * e + 0.34406 * e ** 3 + 0.04305 * e ** 5 + 0.02271 * e ** 7


def psi_song_lee(eps, tau, bi, kind="ave"):
    """!
    @brief Equations 27 to 30 of Song and Lee, psi = sqrt(pi) k a Rc.
    @param eps Relative source radius.
    @param tau Relative thickness.
    @param bi Biot number.
    @param kind "ave" (equation 27) or "max" (equation 28).
    @return float psi.
    """
    dc = np.pi + 1.0 / (np.sqrt(np.pi) * eps)                   # equation 30
    phic = (bi * np.tanh(dc * tau) + dc) / (bi + dc * np.tanh(dc * tau))   # equation 29
    return 0.5 * (1 - eps) ** 1.5 * phic if kind == "ave" else (1 - eps) * phic / np.sqrt(np.pi)


def rc_integral(k1, k2, a, t1):
    """!
    @brief Equation 34 (Dryden) for an isothermal-equivalent source on a layer on a half-space, by quadrature.
    @param k1 Layer conductivity in W/mK.
    @param k2 Substrate conductivity in W/mK.
    @param a Source radius in m.
    @param t1 Layer thickness in m.
    @return float Rc in K/W.
    """
    kk = (1 - k2 / k1) / (1 + k2 / k1)                          # equation 35
    f = lambda z: (1 + kk * np.exp(-2 * z * t1 / a)) / (1 - kk * np.exp(-2 * z * t1 / a)) * j1(z) * np.sin(z) / z ** 2
    # the integrand decays as exp(-z) only through the layer term; cut at a large z with the oscillatory tail
    val, _ = quad(f, 0, 400, limit=2000)
    return val / (np.pi * k1 * a)


def main():
    """!
    @brief Print the four comparisons.
    @return None.
    """
    print("(a) isoflux flux tube, psi = 4 k a Rc: series (eq. 22, tau = 50) against correlation (eq. 24); eps -> 0 limit 32/(3 pi^2) = %.5f" % (32 / (3 * np.pi ** 2)))
    for e in (0.01, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9):
        s, c = psi_isoflux_series(e), psi_24(e)
        print(f"   eps {e:4.2f}: series {s:.5f}  eq.24 {c:.5f}  difference {c - s:+.5f}")
    print("(b) m = -1/2 (equivalent isothermal flux): series (eq. 21) against Table 3 of Yovanovich (2003, page 174, read in the text layer): column m = -1/2 (Roess) and Negus-Yovanovich isothermal; eq. 23 is the correlation of the isothermal column")
    table3 = {0.1: (0.8592, 0.8594), 0.3: (0.5853, 0.5865), 0.5: (0.3342, 0.3396), 0.7: (0.1262, 0.1403), 0.8: (0.0483, 0.0672)}
    for e, (roess, ny) in table3.items():
        print(f"   eps {e:4.2f}: eq.21 series {psi_isothermal_flux_series(e):.5f} (Table 3 m=-1/2: {roess})  eq.23 {psi_23(e):.5f} (Table 3 N-Y isothermal: {ny})")
    print(f"   eps 0.90: eq.21 series {psi_isothermal_flux_series(0.9):.5f} (negative: the equivalent isothermal flux is stated valid only for eps < 0.6), eq.23 {psi_23(0.9):.5f}")
    print("(c) Song and Lee (eqs. 27 to 30), psi = sqrt(pi) k a Rc, against the isoflux series (psi_series * sqrt(pi) / 4 gives the same basis), Bi = 1e6 and tau = 50")
    for e in (0.1, 0.3, 0.5, 0.7):
        ref = psi_isoflux_series(e) * np.sqrt(np.pi) / 4.0
        # the series is for the area-mean of the source; the maximum (centroid) value is larger
        print(f"   eps {e:4.2f}: series (mean) {ref:.5f}  eq.27 {psi_song_lee(e, 50.0, 1e6, 'ave'):.5f} ({100 * (psi_song_lee(e, 50.0, 1e6, 'ave') / ref - 1):+.1f} %)  eq.28 (centroid) {psi_song_lee(e, 50.0, 1e6, 'max'):.5f}")
    print("(d) layer on a half-space, Rc in K/W: integral (eq. 34) against the thin-layer first-order term (eq. 38, printed for t/a <= 0.10), k1 = 400, a = 1 mm; the expansion parameter is (k1/k2)^2 t/a, not t/a")
    k1, a = 400.0, 1e-3
    for ratio in (1.2, 2.0, 10.0, 0.1):
        k2 = k1 / ratio
        for ta in (0.001, 0.05, 0.1):
            ex = rc_integral(k1, k2, a, ta * a)
            thin = 1 / (4 * k2 * a) + (1 / (np.pi * k1 * a)) * ta * (1 - (k1 / k2) ** 2)
            print(f"   k1/k2 {ratio:5.1f} t/a {ta:5.3f}: eq.34 {ex:.5f}  eq.38 {thin:.5f} ({100 * (thin / ex - 1):+.1f} %)")
    print("   thick layer (eq. 39, printed for t/a >= 2):")
    for ratio in (10.0, 100.0, 1000.0):
        k2 = k1 / ratio
        for ta in (2.0, 5.0):
            ex = rc_integral(k1, k2, a, ta * a)
            thick = 1 / (4 * k1 * a) - (1 / (2 * np.pi * k1 * a)) * (1 / ta) * np.log(2 / (1 + k1 / k2))
            print(f"   k1/k2 {ratio:6.1f} t/a {ta:4.1f}: eq.34 {ex:.5f}  eq.39 {thick:.5f} ({100 * (thick / ex - 1):+.1f} %)")


if __name__ == "__main__":
    main()
