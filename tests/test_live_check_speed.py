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
    @brief 500 parts with 8000 vias around them (the zone-model test of each part used to scan every via): under 2 s (about 0.45 s; 2.4 s before).
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


def _box_pairs(polys):
    """!
    @brief Reference of the sweep: the pairs that pass the bounding-box test of polygon_overlap_area (min of the right edges above the max of the left
           edges, and the same in y), every pair tested; a polygon with a NaN coordinate is left out (its exact overlap is NaN and never warns).
    @param polys Sequence of polygons or None.
    @return List of (i, j), i < j, in loop order.
    """
    out = []
    for i, j in _all_pairs(polys):
        a, b = np.asarray(polys[i], float), np.asarray(polys[j], float)
        if np.isnan(a).any() or np.isnan(b).any():
            continue
        if min(a[:, 0].max(), b[:, 0].max()) > max(a[:, 0].min(), b[:, 0].min()) and min(a[:, 1].max(), b[:, 1].max()) > max(a[:, 1].min(), b[:, 1].min()):
            out.append((i, j))
    return out


def test_sweep_leaves_out_boxes_without_area_and_with_nan():
    """!
    @brief Review: a box with no width or no height inside another box (a point, a segment along an axis) passed the sweep, which tests only the edges of
           the partner, although its overlap is 0 by the box test; also infinite and NaN coordinates, duplicates and single points, on 2000 random sets.
    @return None.
    """
    rng = np.random.default_rng(11)
    point_in_box = [np.array([[0.0, 0.0], [3.0, 0.0], [3.0, 3.0], [0.0, 3.0]]), np.array([[1.0, 1.0]] * 4), np.array([[1.0, 0.5], [1.0, 2.5]])]
    assert bbox_overlap_pairs(point_in_box) == []
    for _ in range(2000):
        polys = []
        for _ in range(int(rng.integers(0, 30))):
            r = rng.random()
            if r < 0.08:
                polys.append(None)
                continue
            if polys and r < 0.2 and polys[-1] is not None:
                polys.append(np.array(polys[-1]))                                  # duplicate
                continue
            x, y = rng.integers(0, 8, 2).astype(float)
            w, h = rng.integers(0, 4, 2).astype(float)                             # zero widths and heights included, integer edges touch exactly
            q = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]])
            if rng.random() < 0.05:
                q[int(rng.integers(0, 4)), int(rng.integers(0, 2))] = rng.choice([np.nan, np.inf, -np.inf])
            if rng.random() < 0.05:
                q = q[:1]
            polys.append(q)
        assert bbox_overlap_pairs(polys) == _box_pairs(polys)


def test_column_of_parts_is_fast_and_equal():
    """!
    @brief The worst case of a sweep on x: 1000 parts in one column, every box overlapping every other in x (about 0.25 s quiet); the warnings are those of
           the test of every pair.
    @return None.
    """
    p = Problem.new(20, 905, 2)
    for k in range(1000):
        p.add_heater(1, 0.1, rect=(5, 0.5 + k * 0.85, 9, 0.5 + k * 0.85 + 0.9))
    assert _timed(p) < 2.5
    polys = [np.asarray(h.polygon) for h in p.heaters]
    assert bbox_overlap_pairs(polys) == _box_pairs(polys)


def _heater_distance_reference(problem, vs):
    """!
    @brief The distance of every via to the nearest footprint as written before the review (every footprint against every via), the reference of the pruned one.
    @param problem Problem.
    @param vs viaconstriction.ViaSet.
    @return numpy.ndarray (n,) in m.
    """
    from pcbthermal.geometry import points_in_polygon
    out = np.full(len(vs), np.inf)
    for h in problem.heaters:
        poly = np.asarray(h.polygon, dtype=float)
        inside = points_in_polygon(vs.x, vs.y, poly)
        out[inside] = 0.0
        a, e = poly, np.roll(poly, -1, axis=0) - poly
        len2 = np.maximum((e ** 2).sum(axis=1), 1e-300)
        i = np.flatnonzero(~inside)
        px, py = vs.x[i][:, None], vs.y[i][:, None]
        t = np.clip(((px - a[:, 0]) * e[:, 0] + (py - a[:, 1]) * e[:, 1]) / len2, 0.0, 1.0)
        out[i] = np.minimum(out[i], np.hypot(px - (a[:, 0] + t * e[:, 0]), py - (a[:, 1] + t * e[:, 1])).min(axis=1))
    return out


@pytest.mark.parametrize("seed", range(6))
def test_heater_distance_pruned_is_bit_identical(seed):
    """!
    @brief Review: the distance of the vias to the footprints skips the vias that a footprint's bounding box cannot bring closer; the distances are
           bit-identical to the test of every footprint (rotated, concave and identical parts, vias on edges and corners of the footprints).
    @param seed Random seed.
    @return None.
    """
    from pcbthermal import viaconstriction
    p = _random_board(80, seed)
    rng = np.random.default_rng(100 + seed)
    for k in range(20):
        cx, cy, r, a = rng.uniform(5, 55), rng.uniform(5, 45), rng.uniform(0.5, 4), rng.uniform(0, np.pi)
        pts = [(cx + r * np.cos(a + t), cy + r * np.sin(a + t)) for t in np.linspace(0, 2 * np.pi, 7)[:-1]]
        p.add_heater(1, 0.1, polygon=pts if k % 3 else pts[::2] + [(cx, cy)])
    for h in p.heaters[:30]:
        for x, y in np.asarray(h.polygon)[:2] * 1000:
            p.add_via(float(x), float(y), 0.3)                                    # on a corner and on an edge of a footprint
    vs = viaconstriction.ViaSet(p)
    assert np.array_equal(viaconstriction.heater_distance(p, vs), _heater_distance_reference(p, vs))


def test_prepared_zone_decision_equals_the_unprepared_one_on_an_outline():
    """!
    @brief will_be_zoned(prepared=True) on the board that check_model_limits prepares (equivalent rectangle, vias with no board under them dropped) gives the
           decision of the plain call for every part, on boards with an outline and vias off the board, with zoned and unzoned parts.
    @return None.
    """
    from pcbthermal import lumped, viaconstriction
    n_zoned = 0
    for seed in range(4):
        p = Problem.new(50, 40, 2)
        p.board.outline = np.array([(0, 0), (50, 0), (50, 20), (25, 20), (25, 40), (0, 40)], float) / 1000.0
        rng = np.random.default_rng(seed)
        for k in range(12):
            x, y = rng.uniform(1, 40), rng.uniform(1, 30)
            p.add_heater(1, 0.5, rect=(x, y, x + 4, y + 4))
            p.add_via_array((x + 0.5, y + 0.5, x + 3.5, y + 3.5), 2 + k % 3, 2 + k % 3, 0.3)
        for x, y in rng.uniform(26, 49, (30, 2)):
            p.add_via(float(x), float(y), 0.3)                                    # many in the cut-out corner: no board under them
        kept = p.equivalent_rectangle()[0].drop_off_board_vias()
        vs = viaconstriction.ViaSet(kept)
        for k, h in enumerate(p.heaters):
            plain = lumped.will_be_zoned(p, h)
            assert lumped.will_be_zoned(kept, kept.heaters[k], vias=vs, prepared=True) == plain
            n_zoned += plain
    assert 0 < n_zoned < 48
