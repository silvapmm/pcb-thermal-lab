#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file strip.py
@brief The closed form of a heated copper strip on a bare laminate sheet (a one-dimensional fin with a step in the sheet conductance), the check of the independent 3D solver at a pad edge.

@details A strip |x| < a of sheet conductance S1 (W/K) heated uniformly with q (W/m2) sits in an infinite sheet of conductance S2; both lose heat to the ambient through the film h
         (W/m2K, the sum of the two faces, the through-thickness drop being negligible). The rise obeys S d2(theta)/dx2 - h theta = -q in the strip and S2 d2(theta)/dx2 = h theta outside:
         theta = q/h + C cosh(m1 x) for |x| < a and D exp(-m2 (|x| - a)) outside, with m = sqrt(h / S). Continuity of theta and of the flux S theta' at x = a gives
         C = -(q/h) / (cosh(m1 a) + (S1 m1 / (S2 m2)) sinh(m1 a)) and D = q/h + C cosh(m1 a)  (the fin equation of Carslaw and Jaeger, status M for the book; the algebra is checked in tests/test_strip.py).
"""

import numpy as np


def strip_profile(x, q, a, S1, S2, h):
    """!
    @brief Rise along the strip and outside it.
    @param x Positions in m (array or number).
    @param q Heat flux in the strip in W/m2.
    @param a Half width of the strip in m.
    @param S1 Sheet conductance of the strip in W/K.
    @param S2 Sheet conductance outside in W/K.
    @param h Film coefficient (both faces) in W/m2K.
    @return Array of rises in K.
    """
    x = np.abs(np.asarray(x, dtype=float))
    m1, m2 = np.sqrt(h / S1), np.sqrt(h / S2)
    c = -(q / h) / (np.cosh(m1 * a) + (S1 * m1 / (S2 * m2)) * np.sinh(m1 * a))
    d = q / h + c * np.cosh(m1 * a)
    return np.where(x < a, q / h + c * np.cosh(m1 * np.minimum(x, a)), d * np.exp(-m2 * np.maximum(x - a, 0.0)))


def strip_peak(q, a, S1, S2, h):
    """!
    @brief Rise at the centre of the strip.
    @param q Heat flux in the strip in W/m2.
    @param a Half width of the strip in m.
    @param S1 Sheet conductance of the strip in W/K.
    @param S2 Sheet conductance outside in W/K.
    @param h Film coefficient (both faces) in W/m2K.
    @return Rise over the ambient at x = 0 in K.
    """
    return float(strip_profile(0.0, q, a, S1, S2, h))
