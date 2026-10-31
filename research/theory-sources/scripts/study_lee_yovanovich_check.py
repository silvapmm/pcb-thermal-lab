#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_lee_yovanovich_check.py
@brief F8: the two papers that were read only in part. Lee (Electronics Cooling, January 1998) equations 1 and 2 and its worked example; Yovanovich (J. Electronic Packaging 125, 2003, 169-177) Table 3, isoflux column.
@details Lee: the equation images of the article were opened (data-lazy-src files A3form1_2 and A3formula of the page): Rc = (sqrt(Ap) - sqrt(As)) / (k sqrt(pi Ap As)) * (lam k Ap R0 + tanh(lam t)) / (1 + lam k Ap R0 tanh(lam t)),
lam = pi^(3/2) / sqrt(Ap) + 1 / sqrt(As); worked example: k 200, plate 100 x 100 x 1.3 mm, source 25 x 25 mm, R0 1.0 K/W: lam 95.68 1/m, tanh(lam t) 0.124, lam k Ap R0 191.4, Rc = 0.0846 x 7.743 = 0.66 K/W.
Yovanovich: Table 3 (page 174, text layer) lists 4 a k Rs for the contact radius ratio e = 0 to 0.8 for the flux exponent m = 1/2, 0 and -1/2 (m = 0 is the isoflux source); the exact series
psi = 16 / (pi e) sum_n J1(delta_n e)^2 / (delta_n^3 J0(delta_n)^2) over the roots delta_n of J1 is evaluated here and compared with the m = 0 column.
Run from the repository root: .venv/bin/python research/theory-sources/scripts/study_lee_yovanovich_check.py
"""

import math

import numpy as np
from scipy.special import j0, j1, jn_zeros

TABLE3_M0 = {0.1: 0.9401, 0.2: 0.8009, 0.3: 0.6649, 0.4: 0.5337, 0.5: 0.4092, 0.6: 0.2936, 0.7: 0.1896, 0.8: 0.1008}


def lee_rc(k, ap, as_, t, r0):
    """!
    @brief Maximum spreading resistance of a centred source by equations 1 and 2 of Lee (1998).
    @param k Plate conductivity (W/mK).
    @param ap Plate area (m2).
    @param as_ Source area (m2).
    @param t Plate thickness (m).
    @param r0 Average resistance of the heat sink (K/W).
    @return Tuple (Rc in K/W, lambda in 1/m).
    """
    lam = math.pi ** 1.5 / math.sqrt(ap) + 1.0 / math.sqrt(as_)
    th = math.tanh(lam * t)
    x = lam * k * ap * r0
    rc = (math.sqrt(ap) - math.sqrt(as_)) / (k * math.sqrt(math.pi * ap * as_)) * (x + th) / (1.0 + x * th)
    return rc, lam


def yovanovich_psi_isoflux(e, n_terms=4000):
    """!
    @brief Dimensionless spreading resistance 4 a k Rs of an isoflux circular source on a semi-infinite-length flux tube of relative radius e = a / b (series over the roots of J1).
    @param e Contact radius ratio a / b.
    @param n_terms Number of roots.
    @return float psi.
    """
    d = jn_zeros(1, n_terms)
    return float(16.0 / (math.pi * e) * np.sum(j1(d * e) ** 2 / (d ** 3 * j0(d) ** 2)))


def main():
    """!
    @brief Print the Lee example and the Yovanovich comparison.
    @return None.
    """
    rc, lam = lee_rc(200.0, 0.01, 0.000625, 0.0013, 1.0)
    print("Lee 1998 example: lambda %.2f 1/m (article 95.68), Rc %.4f K/W (article 0.66 = 0.0846 x 7.743), total %.3f K/W (article 1.66)" % (lam, rc, 1.0 + rc))
    print("Yovanovich 2003 Table 3, isoflux column (m = 0): e | table | series | difference")
    for e, v in TABLE3_M0.items():
        s = yovanovich_psi_isoflux(e)
        print("  %.1f | %.4f | %.4f | %+.4f" % (e, v, s, s - v))


if __name__ == "__main__":
    main()
