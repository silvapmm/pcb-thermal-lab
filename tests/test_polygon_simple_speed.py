#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_polygon_simple_speed.py
@brief The fast `geometry.polygon_is_simple` agrees with the all-pairs test and is fast on big outlines.
"""
import time

import numpy as np

from pcbthermal.geometry import polygon_is_simple


def _reference_is_simple(poly):
    """!
    @brief The original O(n^2) all-pairs test, kept as the reference.
    @param poly Array-like (n, 2) of vertices.
    @return bool.
    """
    p = np.asarray(poly, dtype=float)
    n = len(p)

    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

    for i in range(n):
        a, b = p[i], p[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or (i + 1) % n == j:
                continue
            c, d = p[j], p[(j + 1) % n]
            if ccw(a, b, c) * ccw(a, b, d) < 0 and ccw(c, d, a) * ccw(c, d, b) < 0:
                return False
    return True


def test_equivalent_to_all_pairs_on_random_polygons():
    """!
    @brief 2000 random polygons (grid-snapped to force touching, collinear and duplicate points) agree with the reference.
    @return None.
    """
    rng = np.random.default_rng(12345)
    n_true = 0
    for k in range(2000):
        n = int(rng.integers(3, 201)) if k % 4 == 0 else int(rng.integers(3, 20))
        grid = int(rng.choice([2, 3, 5, 10, 1000]))
        mode = k % 3
        if mode == 0:
            pts = rng.integers(0, grid + 1, size=(n, 2)).astype(float)
        elif mode == 1:
            # A star-shaped (usually simple) polygon, snapped to the grid
            ang = np.sort(rng.uniform(0, 2 * np.pi, n))
            r = rng.uniform(0.5, 1.0, n)
            pts = np.round(np.c_[r * np.cos(ang), r * np.sin(ang)] * grid) / grid
        else:
            pts = rng.uniform(0, 1, size=(n, 2))
            if rng.random() < 0.5 and n > 3:
                pts[rng.integers(0, n)] = pts[rng.integers(0, n)]   # A duplicated point
        ref = _reference_is_simple(pts)
        n_true += ref
        assert polygon_is_simple(pts) == ref, (k, pts.tolist())
    assert 200 < n_true < 1800                                    # Both outcomes are well represented


def test_non_finite_and_small():
    """!
    @brief Triangles are simple, NaN edges never cross, like the reference.
    @return None.
    """
    assert polygon_is_simple([[0, 0], [1, 0], [0, 1]])
    pts = [[0, 0], [2, 2], [2, 0], [0, 2], [float("nan"), 1]]
    assert polygon_is_simple(pts) == _reference_is_simple(pts)


def test_big_outlines_are_fast():
    """!
    @brief 20 000-point round and noisy simple outlines, and a crossing one, take under a second each.
    @return None.
    """
    n = 20000
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    circle = np.c_[40 * np.cos(t), 40 * np.sin(t)]
    rng = np.random.default_rng(1)
    rad = 1 + 0.002 * rng.uniform(-1, 1, n)                      # Radial noise only: stays star-shaped, so simple
    noisy = np.c_[40 * rad * np.cos(t), 30 * rad * np.sin(t)]
    bad = circle.copy()
    bad[[5000, 5001]] = bad[[15000, 15001]]                      # Two edges swapped across the board cross
    for poly, expect in ((circle, True), (noisy, True), (bad, False)):
        t0 = time.perf_counter()
        assert polygon_is_simple(poly) is expect
        assert time.perf_counter() - t0 < 1.0


def _reference_self_intersects(poly):
    """!
    @brief The original row-vectorised O(n^2) `polygon_self_intersects`, kept as the reference.
    @param poly Array-like (n, 2) of vertices.
    @return bool.
    """
    p = np.asarray(poly, dtype=float)
    n = len(p)
    if n < 4:
        return False
    a, b = p, np.roll(p, -1, axis=0)
    for i in range(n - 2):
        j = np.arange(i + 2, n if i > 0 else n - 1)
        if len(j) == 0:
            continue
        d1 = (b[i, 0] - a[i, 0]) * (a[j, 1] - a[i, 1]) - (b[i, 1] - a[i, 1]) * (a[j, 0] - a[i, 0])
        d2 = (b[i, 0] - a[i, 0]) * (b[j, 1] - a[i, 1]) - (b[i, 1] - a[i, 1]) * (b[j, 0] - a[i, 0])
        d3 = (b[j, 0] - a[j, 0]) * (a[i, 1] - a[j, 1]) - (b[j, 1] - a[j, 1]) * (a[i, 0] - a[j, 0])
        d4 = (b[j, 0] - a[j, 0]) * (b[i, 1] - a[j, 1]) - (b[j, 1] - a[j, 1]) * (b[i, 0] - a[j, 0])
        if np.any((d1 * d2 < 0) & (d3 * d4 < 0)):
            return True
    return False


def test_self_intersects_matches_its_old_form():
    """!
    @brief `polygon_self_intersects` (now the negation of the fast test) agrees with its old code on 1500 random polygons.
    @return None.
    """
    from pcbthermal.geometry import polygon_self_intersects
    rng = np.random.default_rng(777)
    for k in range(1500):
        n = int(rng.integers(3, 60))
        if k % 2:
            pts = rng.integers(0, int(rng.choice([3, 6, 20])) + 1, size=(n, 2)).astype(float)
        else:
            pts = rng.uniform(0, 1, size=(n, 2))
        assert polygon_self_intersects(pts) == _reference_self_intersects(pts), k


def _exact_is_simple(poly):
    """!
    @brief All-pairs crossing test in exact rational arithmetic (`fractions.Fraction` of the float coordinates).
    @param poly Array-like (n, 2) of finite vertices.
    @return bool.
    """
    from fractions import Fraction
    q = [(Fraction(float(x)), Fraction(float(y))) for x, y in poly]
    n = len(q)

    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue                                          # The closing edge is adjacent to the first
            a, b, c, d = q[i], q[(i + 1) % n], q[j], q[(j + 1) % n]
            if ccw(a, b, c) * ccw(a, b, d) < 0 and ccw(c, d, a) * ccw(c, d, b) < 0:
                return False
    return True


def test_matches_exact_arithmetic_on_small_integer_polygons():
    """!
    @brief On small integer coordinates (touching vertices, T-junctions, collinear overlaps, repeated points), scaled by powers of two, the answer is the exact one.
    @return None.
    """
    rng = np.random.default_rng(4242)
    for k in range(1500):
        n = int(rng.integers(3, 14))
        g = int(rng.choice([1, 2, 3, 5]))
        pts = rng.integers(-g, g + 1, size=(n, 2)).astype(float)
        if k % 3 == 0 and n >= 5:
            a, b = pts[0], pts[1]
            pts[3] = (a + b) / 2                                  # A vertex on the interior of another edge (exact in binary)
        scale = float(rng.choice([1.0, 2.0 ** -20, 2.0 ** 20]))
        # Powers of two keep every difference and product exact (tiny, huge, and huge with small features)
        for p in (pts, pts * scale, pts * 2.0 ** -10 + 2.0 ** 20):
            assert polygon_is_simple(p) == _exact_is_simple(p), (k, p.tolist())


def test_no_spurious_crossing_of_collinear_edges_apart():
    """!
    @brief A triangle whose long side holds nearly collinear points is simple; the old all-pairs loop said it crossed itself.
    @note The rounded orientation products of collinear edges change sign at random; the old loop compared the first and
          the third edge of the side (far apart along it) and found a "crossing". The box test never compares them.
    @return None.
    """
    from pcbthermal.geometry import polygon_self_intersects
    tri = [[0.1580864194840257, 0.47425925845207695], [0.5430920201342117, 1.6292760604026346],
           [0.5619097232232606, 1.6857291696697816], [0.8719644465264909, 2.6158933395794737], [0.5, -5.0]]
    assert _exact_is_simple(tri)
    assert not _reference_is_simple(tri)                          # The defect of the old code, kept as the record
    assert polygon_is_simple(tri) and not polygon_self_intersects(tri)


def test_crossings_on_box_edges_and_near_parallel():
    """!
    @brief A crossing at the end of a box (axis-aligned plus sign) and long nearly parallel edges that cross are found.
    @return None.
    """
    assert not polygon_is_simple([[0, 0], [2, 0], [1, -1], [1, 1]])            # Horizontal against vertical edge
    assert not polygon_is_simple([[0, 0], [1e6, 1.0], [1e6, 0.0], [0, 1.0]])   # Two edges of slope 1e-6 crossing at the middle
    assert polygon_is_simple([[0, 0], [1e6, 0.0], [1e6, 1.0], [0, 1.0]])       # The same four points in order
