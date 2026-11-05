#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file robin_basis.py
@brief Orthogonal eigenfunctions of d2/dx2 on [0, L] with a convective (Robin) edge at both ends, the basis of the Analytic series with the edge cooled.

@details The Analytic model expands each layer in cos(m pi x / L), which has an insulated edge (d/dx = 0). A convective edge, S dtheta/dn = -h_e s theta, i.e.
         dtheta/dn + beta theta = 0 with beta = h_e s / S (1/m), has the eigenfunctions of the same Sturm-Liouville problem with that condition. On the centred
         coordinate u = x - L/2 (half length Lh = L/2) they split into even and odd functions:

             even   cos(lam u),  lam Lh tan(lam Lh) = beta Lh,           lam Lh in (k pi, k pi + pi/2)
             odd    sin(lam u),  lam Lh cot(lam Lh) = -beta Lh,          lam Lh in (k pi + pi/2, (k + 1) pi)

         ordered by lam (mode 0 even, 1 odd, 2 even, ...). beta = 0 gives lam = m pi / L, i.e. exactly the cosine basis of the program (the code returns the
         cosine itself in that case, so the program is reproduced to rounding). They are orthogonal for the weight 1, with the norms
         int cos^2 = Lh + sin(2 lam Lh) / (2 lam) and int sin^2 = Lh - sin(2 lam Lh) / (2 lam). The eigenvalue lam^2 replaces (m pi / L)^2 in the modal matrices
         of analytic.py; everything else (the L x L tridiagonal coupling of the layers) is unchanged because the basis is the same for every layer when beta is.
         Source: Muzychka, Culham and Yovanovich 2003 (AIAA 2003-4188) Part II eq. 12 to 21 (rectangular flux channel with edge cooling, source at the centroid,
         eigenvalue equation delta tan delta = Bi_e: R from the OCR text layer of p. 4, re-derived by the review) and the standard Sturm-Liouville theory [CarslawJaeger] (M); the general (off-centre)
         source needs the odd functions, which the paper's centred source does not.
"""

import numpy as np
from scipy.optimize import brentq


def _root(k, odd, bl):
    """!
    @brief The k-th root delta of the even (delta tan delta = bl) or odd (delta cot delta = -bl) eigen-equation, robust for any bl > 0.
    @details The equations are solved in the form without poles, even g(d) = d sin d - bl cos d on [k pi, k pi + pi/2] and odd g(d) = d cos d + bl sin d on
             [k pi + pi/2, (k + 1) pi], where g changes sign exactly once. When the root is closer to an end of its interval than rounding can resolve (a very small
             or a very large bl: the prototype's brentq on d tan d failed below bl of about 1e-9 times the highest root, i.e. h_side near 3e-7 W/m2K on a 60 x 40 mm,
             1.6 mm board, and above bl of about 1e12), the first-order asymptote is used instead: small bl, even d = sqrt(bl) (k = 0) or k pi + bl / (k pi), odd
             d = (k + 1/2) pi + bl / ((k + 1/2) pi); large bl, even d = (k + 1/2) pi (1 - 1/bl), odd d = (k + 1) pi (1 - 1/bl). (Reviewer's correction.)
    @param k Index of the interval (0, 1, ...).
    @param odd 0 for the even function, 1 for the odd function.
    @param bl Edge parameter times the half length, beta Lh (> 0).
    @return float The root delta = lam Lh.
    """
    if odd:
        lo, hi = k * np.pi + 0.5 * np.pi, (k + 1) * np.pi
        g = lambda d: d * np.cos(d) + bl * np.sin(d)          # noqa: E731
    else:
        lo, hi = k * np.pi, k * np.pi + 0.5 * np.pi
        g = lambda d: d * np.sin(d) - bl * np.cos(d)          # noqa: E731
    glo, ghi = g(lo), g(hi)
    if glo * ghi < 0.0:
        return brentq(g, lo, hi, xtol=1e-15, rtol=1e-15)
    # No sign change in floating point: the root sits at an end of the interval to rounding; use the asymptote of that end
    if bl < 1.0:
        if odd:
            return lo + bl / lo
        return np.sqrt(bl) if k == 0 else lo + bl / lo
    return hi * (1.0 - 1.0 / bl)


class Basis:
    """!
    @brief The first n eigenfunctions of one direction of the board.
    """

    def __init__(self, length, beta, n):
        """!
        @brief Build the basis.
        @param length Length L of the direction in metres.
        @param beta Edge parameter h_e s / S in 1/m (0: the insulated cosine basis of the program).
        @param n Number of modes.
        @return None.
        """
        self.L, self.beta, self.n = float(length), float(beta), int(n)
        Lh = 0.5 * self.L
        if self.beta <= 0.0:
            self.cosine = True
            self.lam = np.arange(n) * np.pi / self.L
            self.kind = None
            return
        self.cosine = False
        bl = self.beta * Lh
        lam = np.empty(n)
        kind = np.empty(n, dtype=int)                    # 0 even (cos in u), 1 odd (sin in u)
        for m in range(n):
            k = m // 2
            kind[m] = m % 2
            lam[m] = _root(k, m % 2, bl) / Lh
        self.lam, self.kind = lam, kind

    @property
    def eig2(self):
        """!
        @brief Eigenvalues lam^2 (1/m2) that replace (m pi / L)^2.
        @return Array (n,).
        """
        return self.lam ** 2

    @property
    def norm(self):
        """!
        @brief Squared norm int_0^L phi_m^2 dx of the (unnormalised) eigenfunctions.
        @return Array (n,).
        """
        Lh = 0.5 * self.L
        if self.cosine:
            return np.where(np.arange(self.n) == 0, self.L, 0.5 * self.L)
        lam = self.lam
        s = np.sin(2.0 * lam * Lh) / (2.0 * lam)
        return np.where(self.kind == 0, Lh + s, Lh - s)

    def evaluate(self, x):
        """!
        @brief The eigenfunctions at points x (metres from the lower edge).
        @param x Array (p,).
        @return Array (p, n).
        """
        x = np.asarray(x, dtype=float)
        if self.cosine:
            return np.cos(np.outer(x, self.lam))
        arg = np.outer(x - 0.5 * self.L, self.lam)
        return np.where(self.kind[None, :] == 0, np.cos(arg), np.sin(arg))

    def project(self, lo, hi):
        """!
        @brief Integral of every eigenfunction over [lo, hi].
        @param lo Lower bound in metres.
        @param hi Upper bound in metres.
        @return Array (n,).
        """
        if self.cosine:
            out = np.empty(self.n)
            out[0] = hi - lo
            k = self.lam[1:]
            out[1:] = (np.sin(k * hi) - np.sin(k * lo)) / k
            return out
        ul, uh = lo - 0.5 * self.L, hi - 0.5 * self.L
        lam = self.lam
        even = (np.sin(lam * uh) - np.sin(lam * ul)) / lam
        odd = -(np.cos(lam * uh) - np.cos(lam * ul)) / lam
        return np.where(self.kind == 0, even, odd)
