"""!
@file test_geometry.py
@brief Unit tests of the polygon helpers.
"""

import numpy as np

from pcbthermal import geometry as g


def test_polygon_area_and_centroid():
    sq = [[0, 0], [2, 0], [2, 1], [0, 1]]
    assert abs(g.polygon_area(sq) - 2.0) < 1e-12
    assert np.allclose(g.polygon_centroid(sq), (1.0, 0.5))


def test_point_in_polygon_concave():
    # L-shaped polygon: the notch (1.5, 1.5) is outside, (0.5, 1.5) is inside
    poly = [[0, 0], [2, 0], [2, 1], [1, 1], [1, 2], [0, 2]]
    px = np.array([0.5, 1.5, 0.5, 2.5])
    py = np.array([0.5, 1.5, 1.5, 0.5])
    assert list(g.points_in_polygon(px, py, poly)) == [True, False, True, False]


def test_coverage_sums_to_polygon_area():
    # A polygon that does not line up with the grid: covered area must match the true area
    poly = np.array([[0.013, 0.021], [0.047, 0.019], [0.052, 0.061], [0.011, 0.058]])
    nx = ny = 25
    dx = dy = 0.1 / nx
    cov = g.coverage_fraction(poly, nx, ny, dx, dy, samples=8)
    assert abs(cov.sum() * dx * dy - g.polygon_area(poly)) / g.polygon_area(poly) < 0.01
    assert cov.min() >= 0.0 and cov.max() <= 1.0
