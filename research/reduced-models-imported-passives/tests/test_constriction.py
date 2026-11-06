#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_constriction.py
@brief Checks of lib/constriction.py against closed forms: a strip (R = L/W) and a disc pad in a disc window (R = ln(b/a)/(2 pi)).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import constriction as C  # noqa: E402


def test_strip():
    """!
    @brief A strip W pixels wide and L long with the pad on the left column and the sink on the right: R = L / W squares.
    @return None.
    """
    W, L = 10, 40
    cov = np.ones((W, L))
    pad = np.zeros((W, L), bool); pad[:, 0] = True
    fixed = np.zeros((W, L), bool); fixed[:, -1] = True
    assert abs(C.resistance(cov, pad, fixed) - (L - 1) / W) < 1e-9


def test_disc():
    """!
    @brief Disc pad of radius a at the centre of a disc window of radius b: R = ln(b/a) / (2 pi) within 3 %.
    @return None.
    """
    n = 401
    y, x = np.mgrid[:n, :n] - n // 2
    r = np.hypot(x, y)
    a, b = 10.0, 190.0
    R = C.resistance(np.ones((n, n)), r <= a, r >= b)
    assert abs(R / (np.log(b / a) / (2 * np.pi)) - 1) < 0.03


def test_cut_off_pad_and_slot():
    """!
    @brief A pad enclosed by bare laminate is cut off (inf), and a slot in the strip raises R above the open strip.
    @return None.
    """
    n = 41
    cov = np.ones((n, n)); cov[10:31, 10:31] = 0.0; cov[18:23, 18:23] = 1.0
    pad = np.zeros((n, n), bool); pad[19:22, 19:22] = True
    fixed = np.zeros((n, n), bool); fixed[0, :] = fixed[-1, :] = fixed[:, 0] = fixed[:, -1] = True
    assert C.resistance(cov, pad, fixed) == float("inf")
    W, L = 10, 40
    c1 = np.ones((W, L)); c2 = c1.copy(); c2[:7, 20] = 0.0
    pad = np.zeros((W, L), bool); pad[:, 0] = True
    fixed = np.zeros((W, L), bool); fixed[:, -1] = True
    assert C.resistance(c2, pad, fixed) > C.resistance(c1, pad, fixed) + 0.1


def test_kappa_full_copper_is_one():
    """!
    @brief Full copper gives kappa = 1.
    @return None.
    """
    cov = np.ones((60, 60)); pad = np.zeros((60, 60), bool); pad[28:32, 28:32] = True
    assert abs(C.kappa(cov, pad, 30)[0] - 1.0) < 1e-12


def test_fin_disc_closed_form():
    """!
    @brief A disc pad on a uniform sheet that leaks to the ambient: the mean pad temperature for 1 unit of current is K0(x)/(x K1(x)) / (2 pi) with x = a / lambda (Carslaw and Jaeger, from memory), within 4 %.
    @return None.
    """
    from scipy.special import k0, k1
    n = 501
    y, x = np.mgrid[:n, :n] - n // 2
    r = np.hypot(x, y)
    a, lam = 8.0, 40.0
    fixed = np.zeros((n, n), bool); fixed[0, :] = fixed[-1, :] = fixed[:, 0] = fixed[:, -1] = True    # Far frame: 6 lambda away
    R = C.resistance(np.ones((n, n)), r <= a, fixed, leak=1.0 / lam ** 2)
    xx = a / lam
    assert abs(R / (k0(xx) / (xx * k1(xx)) / (2 * np.pi)) - 1) < 0.04
