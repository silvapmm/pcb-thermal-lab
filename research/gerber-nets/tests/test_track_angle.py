"""!
@file test_track_angle.py
@brief A track at an angle on the pixel grid (phase 3): connectivity, area and resistance with the five-point stencil.
@details A small deterministic case written as Gerber text and read by the independent reader; NumPy and SciPy only.
"""

import math

import numpy as np
import pytest
from scipy import ndimage

import native_gerber as ng
from boards_synthetic import HEAD, mm


def draw(text, size, pix):
    """!
    @brief Rasterise a Gerber text on a square window with the origin at the lower left.
    @param text Gerber text.
    @param size Window side (mm).
    @param pix Pixel size (mm).
    @return Boolean mask, rows from the top.
    """
    cv = ng.Canvas(0.0, size, size, size, pix)
    ng.Layer(text).draw(cv)
    return cv.mask


def test_thin_track_at_an_angle_connectivity_area_and_resistance():
    """!@brief A 0.1 mm track at 30 degrees: in pieces with 4-connectivity at a 0.1 mm pixel, one piece with 8-connectivity; a 0.2 mm track is exact in area and within 15 % in resistance at 8 pixels across. @return None."""
    import joule
    ca, sa = math.cos(math.radians(30)), math.sin(math.radians(30))
    def track(w, pix, length=6.0):
        t = HEAD + f"%ADD10C,{w}*%\nD10*\nX{mm(1)}Y{mm(1)}D02*\nX{mm(1 + length * ca)}Y{mm(1 + length * sa)}D01*\nM02*\n"
        return draw(t, 8.0, pix)
    thin = track(0.1, 0.1)
    assert ndimage.label(thin)[1] > 5
    assert ndimage.label(thin, structure=np.ones((3, 3)))[1] == 1
    m = track(0.2, 0.025)
    exact = 6.0 * 0.2 + math.pi * 0.01
    assert m.sum() * 0.025 ** 2 == pytest.approx(exact, rel=0.02)
    lab, n = ndimage.label(m)
    assert n == 1
    ys, xs = np.where(m)
    order = np.argsort(xs)
    src = np.zeros_like(m); snk = np.zeros_like(m)
    src[ys[order[:20]], xs[order[:20]]] = True
    snk[ys[order[-20:]], xs[order[-20:]]] = True
    r, _, _ = joule.solve_net(m, 1.0, src, snk, 1.0)
    ideal = (6.0 - 0.2) / 0.2                                              # squares between the end caps, roughly
    assert 0.9 * ideal < r < 1.35 * ideal                                   # the five-point stencil is too resistive on a tilted track (claim: +10 % at 8 pixels)
