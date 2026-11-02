#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_live_check_speed.py
@brief The live input check stays fast with hundreds of parts: the pairwise overlap test uses a bounding-box sweep, and the warnings are identical
       to those of the test of every pair (kept here as the slow reference).
"""

import time

import numpy as np
import pytest

from pcbthermal import Problem, checks
from pcbthermal.geometry import bbox_overlap_pairs


def _all_pairs(polys):
    """!
    @brief Reference of bbox_overlap_pairs: every pair of the polygons that are not None, as the double loop of the older check did.
    @param polys Sequence of polygons or None.
    @return List of (i, j), i < j, in loop order.
    """
    n = len(polys)
    return [(i, j) for i in range(n) for j in range(i + 1, n) if polys[i] is not None and polys[j] is not None]


def _random_board(n, seed, size=(60.0, 50.0), big=6.0):
    """!
    @brief A two-layer board with n random parts (rectangles and triangles, on both layers, many overlapping or touching), a few zones, blocks and vias.
    @param n Number of parts.
    @param seed Random seed.
    @param size Board width and height in mm.
    @param big Largest part side in mm.
    @return Problem.
    """
    rng = np.random.default_rng(seed)
    p = Problem.new(size[0], size[1], 2)
    for k in range(n):
        x, y = rng.uniform(1, size[0] - big - 1), rng.uniform(1, size[1] - big - 1)
        w, h = rng.uniform(0.5, big), rng.uniform(0.5, big)
        layer = 1 + int(rng.integers(0, 2))
        if k % 5 == 4:
            p.add_heater(layer, 0.1, polygon=[(x, y), (x + w, y), (x + w / 2, y + h)])       # a triangle (convex, not a box)
        elif k % 7 == 6:
            p.add_heater(layer, 0.1, rect=(x, y, x + 0.0, y + h))                           # zero area: skipped by the pair test
        else:
            p.add_heater(layer, 0.1, rect=(x, y, x + w, y + h))
    for k in range(4):
        x, y = rng.uniform(1, 40), rng.uniform(1, 30)
        p.add_zone(1 + k % 2, rect=(x, y, x + 15, y + 12))
    for k in range(5):
        x, y = rng.uniform(1, 40), rng.uniform(1, 30)
        p.add_heatsink(1, 0.0, rect=(x, y, x + 8, y + 8), thickness_mm=2.0)
    p.add_heatsink(1, 0.0, rect=(10, 10, 18, 18), thickness_mm=2.0)                         # touching and overlapping blocks
    p.add_heatsink(1, 0.0, rect=(18, 10, 26, 18), thickness_mm=2.0)
    for x, y in rng.uniform(1, 49, (60, 2)):
        p.add_via(float(x), float(y), 0.3)
    return p


def _texts(problem, models=("fvm", "lumped", "analytic")):
    """!
    @brief The live warning list as (text, short, kind, index) tuples.
    @param problem A Problem.
    @param models Model keys.
    @return list of tuples.
    """
    return [(str(w), w.short, w.kind, w.index) for w in checks.check_input(problem, models, 1.0)]


def test_sweep_pairs_equal_the_pairs_that_can_overlap():
    """!
    @brief The sweep returns exactly the pairs whose boxes overlap with a positive area, in loop order, including touching boxes (not a pair).
    @return None.
    """
    rng = np.random.default_rng(5)
    polys = []
    for k in range(120):
        x, y = rng.integers(0, 20, 2) * 1e-3                      # Integer millimetres: many boxes touch exactly
        w, h = rng.integers(1, 5, 2) * 1e-3
        polys.append(None if k % 11 == 0 else np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]))
    got = bbox_overlap_pairs(polys)
    want = []
    for i, j in _all_pairs(polys):
        a, b = polys[i], polys[j]
        if min(a[:, 0].max(), b[:, 0].max()) > max(a[:, 0].min(), b[:, 0].min()) and min(a[:, 1].max(), b[:, 1].max()) > max(a[:, 1].min(), b[:, 1].min()):
            want.append((i, j))
    assert got == want and len(want) > 20
    assert bbox_overlap_pairs([]) == [] and bbox_overlap_pairs([None, polys[1]]) == []


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_warnings_equal_the_test_of_every_pair(seed, monkeypatch):
    """!
    @brief The live warning list (texts, short forms, tags, order) is the same with the sweep and with the test of every pair.
    @param seed Random seed of the board.
    @param monkeypatch pytest fixture.
    @return None.
    """
    p = _random_board(60, seed)
    fast = _texts(p)
    monkeypatch.setattr(checks, "bbox_overlap_pairs", _all_pairs)
    slow = _texts(p)
    assert fast == slow
    assert any("overlap" in t[0] for t in fast)                   # The comparison is not empty


def _timed(problem):
    """!
    @brief Best of three times of the live check.
    @param problem A Problem.
    @return float seconds.
    """
    best = 1e9
    for _ in range(3):
        t0 = time.perf_counter()
        checks.check_input(problem, ("fvm", "lumped", "analytic"), 1.0)
        best = min(best, time.perf_counter() - t0)
    return best


@pytest.mark.parametrize("n, limit", [(300, 0.8), (1000, 2.5)])
def test_live_check_is_fast_with_many_parts(n, limit):
    """!
    @brief 300 small parts check in under 0.8 s and 1000 in under 2.5 s (about 0.05 s and 0.3 s on a quiet machine; 1.9 s and 9.6 s with every pair).
    @param n Number of parts.
    @param limit Time limit in seconds (generous, for a loaded battery).
    @return None.
    """
    rng = np.random.default_rng(0)
    p = Problem.new(100, 80, 2)
    for _ in range(n):
        x, y = rng.uniform(2, 95), rng.uniform(2, 75)
        p.add_heater(1, 0.1, rect=(x, y, x + rng.uniform(1, 4), y + rng.uniform(1, 4)))
    assert _timed(p) < limit


def test_live_check_is_fast_with_many_parts_and_vias():
    """!
    @brief 500 parts with 8000 vias around them (the zone-model test of each part used to scan every via): under 2 s (about 0.75 s quiet; 2.4 s before).
    @return None.
    """
    rng = np.random.default_rng(3)
    p = Problem.new(100, 80, 2)
    for _ in range(500):
        x, y = rng.uniform(2, 95), rng.uniform(2, 75)
        p.add_heater(1, 0.1, rect=(x, y, x + rng.uniform(1, 4), y + rng.uniform(1, 4)))
    for x, y in rng.uniform(1, [99, 79], (8000, 2)):
        p.add_via(float(x), float(y), 0.3)
    assert _timed(p) < 2.0
