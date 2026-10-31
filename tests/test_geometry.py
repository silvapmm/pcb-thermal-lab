#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
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


def test_coverage_of_a_large_polygon_samples_only_its_edge_cells_bit_for_bit():
    # Since the board cover is sampled 8 x 8, coverage_fraction samples the full lattice only in the cells an edge touches (the full lattice of
    # a 128-vertex outline on a million cells took 34 s and 2.6 GB); the result must be the full-lattice mean bit for bit, also for edges on
    # sample lines, clockwise polygons and polygons that leave the grid
    rng = np.random.default_rng(7)

    def full(poly, nx, ny, dx, dy, s):
        cov = np.zeros((ny, nx))
        got = g._sample_mask(poly, nx, ny, dx, dy, s)
        if got is not None:
            i0, i1, j0, j1, m = got
            cov[i0:i1, j0:j1] = m.mean(axis=(1, 3))
        return cov

    for trial in range(60):
        nx, ny = (int(v) for v in rng.integers(70, 140, 2))
        assert nx * ny > g._EDGE_ONLY_CELLS                 # large enough for the edge-cell path
        dx, dy = (float(v) for v in rng.uniform(0.3, 2.0, 2) * 1e-3)
        n = int(rng.integers(3, 60))
        c = np.array([nx * dx, ny * dy]) * rng.uniform(-0.2, 1.2, 2)
        r = rng.uniform(0.2, 1.0) * max(nx * dx, ny * dy) * rng.uniform(0.2, 1.0, n)
        a = np.sort(rng.uniform(0, 2 * np.pi, n))
        poly = np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)]
        if trial % 4 == 0:                             # a vertical edge on the sample lines of the 8 x 8 lattice
            k = int(rng.integers(1, 30))
            poly = np.array([[0, 0], [k * dx * 0.375 + dx, 0], [k * dx * 0.375 + dx, ny * dy * 0.5], [0, ny * dy * 0.5]])
        if trial % 4 == 1:
            poly = poly[::-1]
        for s in (2, 4, 8):
            assert np.array_equal(g.coverage_fraction(poly, nx, ny, dx, dy, s), full(poly, nx, ny, dx, dy, s))
    # A board outline of the size that made the full lattice slow: a 128-vertex disc on 300 x 300 cells
    t = np.linspace(0.0, 2.0 * np.pi, 129)[:-1]
    disc = np.c_[0.05 + 0.049 * np.cos(t), 0.05 + 0.049 * np.sin(t)]
    assert np.array_equal(g.coverage_fraction(disc, 300, 300, 1e-4 / 0.3, 1e-4 / 0.3, 8), full(disc, 300, 300, 1e-4 / 0.3, 1e-4 / 0.3, 8))
