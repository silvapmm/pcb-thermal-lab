#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_zone_union_research.py
@brief Tests of the zone-union investigation: the independent solver against a closed form and an energy balance, and the invariants that every sensible rule must satisfy.
@details Run: .venv/bin/python -m pytest -q research/zone-union/tests (from the repository root). The invariants: abutting zones give the copper of one zone (point rules), equal-fill
         overlapping zones give one zone (max_point, priority), the prototype equals the old rule on disjoint cell-aligned zones, rules agree on solid zones, layers are independent.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1]
for extra in (HERE / "lib", HERE.parents[1] / "tests" / "helpers", HERE.parents[1]):
    sys.path.insert(0, str(extra))

import layered3d as L3                                   # noqa: E402
import zone_rules as zr                                  # noqa: E402
import reference                                         # noqa: E402


def Z(x0, y0, x1, y1, fill=1.0, layer=0):
    """!
    @brief A zone-like object in metres.
    @param x0 Left (m).
    @param y0 Bottom (m).
    @param x1 Right (m).
    @param y1 Top (m).
    @param fill Fill.
    @param layer 0-based layer.
    @return SimpleNamespace with polygon, fill, layer.
    """
    return SimpleNamespace(polygon=np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]), fill=fill, layer=layer)


def test_independent_solver_matches_the_one_dimensional_closed_form_and_the_energy_balance():
    # Uniform flux on the whole top face: the rise is q'' / (h_top + 1 / (R + 1 / h_bottom)), R = sum t / k
    n, dx = 6, 1e-3
    slabs = [(35e-6, 385.0, 1), (1.565e-3, 0.3, 4)]
    P, ht, hb = 0.9, 10.0, 15.0
    area = (n * dx) ** 2
    R = sum(t / k for t, k, _ in slabs)
    expect = (P / area) / (ht + 1.0 / (R + 1.0 / hb))
    r = L3.solve(dx, n, n, slabs, (0.0, 0.0, n * dx, n * dx), P, ht, hb, film_under_source=True)
    assert r["mean_source"] == pytest.approx(expect, rel=1e-9)
    assert r["heat_out"] == pytest.approx(P, rel=1e-9)


def test_reference_raster_area_fractions():
    # A rectangle of 2.5 x 1.5 cells on a 1 mm grid: the area fraction is exact for edges on the sample lattice
    f = reference.raster([np.array([[0, 0], [2.5e-3, 0], [2.5e-3, 1.5e-3], [0, 1.5e-3]])], 4, 3, 1e-3, samples=4)
    assert f[0, 0] == pytest.approx(1.0) and f[0, 2] == pytest.approx(0.5) and f[1, 0] == pytest.approx(0.5) and f[1, 2] == pytest.approx(0.25) and f[2, 0] == 0.0


def grid(nx=20, ny=20, size=20e-3):
    """!
    @brief Grid description for the rules.
    @param nx Cells along x.
    @param ny Cells along y.
    @param size Board side (m).
    @return tuple (nx, ny, dx, dy).
    """
    return nx, ny, size / nx, size / ny


def test_abutting_zones_equal_one_zone_under_the_point_rules():
    nx, ny, dx, dy = grid()
    strips = [Z(0.0005 * j, 0, 0.0005 * (j + 1), 0.02) for j in range(40)]
    one = [Z(0, 0, 0.02, 0.02)]
    for rule in ("max_point", "prob", "sum_clip", "priority"):
        assert np.allclose(zr.combine(strips, 1, nx, ny, dx, dy, 4, rule), zr.combine(one, 1, nx, ny, dx, dy, 4, rule)), rule
    # The old rule loses half of every cell (two strips per cell, each half of it)
    assert zr.combine(strips, 1, nx, ny, dx, dy, 4, "max_cell").max() == pytest.approx(0.5)


def test_equal_fill_overlap_equals_one_zone_for_max_and_priority_only():
    nx, ny, dx, dy = grid()
    two = [Z(0, 0, 0.02, 0.02, 0.5), Z(0, 0, 0.02, 0.02, 0.5)]
    one = [Z(0, 0, 0.02, 0.02, 0.5)]
    ref = zr.combine(one, 1, nx, ny, dx, dy, 4, "max_point")
    for rule in ("max_cell", "max_point", "priority"):
        assert np.allclose(zr.combine(two, 1, nx, ny, dx, dy, 4, rule), ref), rule
    assert np.allclose(zr.combine(two, 1, nx, ny, dx, dy, 4, "additive"), 1.0)           # double counted
    assert np.allclose(zr.combine(two, 1, nx, ny, dx, dy, 4, "prob"), 0.75)
    assert np.allclose(zr.combine(two, 1, nx, ny, dx, dy, 4, "sum_clip"), 1.0)


def test_prototype_equals_the_old_rule_on_disjoint_cell_aligned_zones():
    nx, ny, dx, dy = grid()
    zs = [Z(0, 0, 0.007, 0.02, 0.6), Z(0.010, 0.004, 0.019, 0.012, 1.0), Z(0.010, 0.014, 0.018, 0.019, 0.3)]
    old = zr.combine(zs, 1, nx, ny, dx, dy, 4, "max_cell")
    for rule in ("max_point", "priority", "prob", "sum_clip", "additive"):
        assert np.allclose(zr.combine(zs, 1, nx, ny, dx, dy, 4, rule), old), rule


def test_solid_zones_overlapping_give_the_union_under_every_rule_but_additive_free_rules():
    nx, ny, dx, dy = grid()
    zs = [Z(0, 0, 0.0122, 0.02), Z(0.0078, 0, 0.02, 0.02)]
    for rule in ("max_point", "prob", "sum_clip", "priority"):
        assert np.allclose(zr.combine(zs, 1, nx, ny, dx, dy, 4, rule), 1.0), rule


def test_layers_are_combined_independently_and_no_copper_is_created_or_lost():
    nx, ny, dx, dy = grid()
    zs = [Z(0, 0, 0.0105, 0.02, layer=0), Z(0.0105, 0, 0.02, 0.02, layer=0), Z(0, 0, 0.02, 0.0105, layer=1)]
    f = zr.combine(zs, 2, nx, ny, dx, dy, 4, "max_point")
    assert f[0].mean() == pytest.approx(1.0) and f[1].mean() == pytest.approx(0.525, abs=0.01)


def test_unknown_rule_is_refused():
    with pytest.raises(ValueError):
        zr.combine([], 1, 2, 2, 1.0, 1.0, 4, "nonsense")


def test_variant_of_the_program_applies_the_prototype_and_gives_the_one_zone_value():
    # A separate process: the variant is a copy of the package, which must not be mixed with the program that pytest imports
    import subprocess
    code = (
        "import sys\n"
        f"sys.path[:0] = [{str(HERE / 'lib')!r}]\n"
        "import variant\n"
        "variant.use()\n"
        "from pcbthermal import Problem, SolverOptions, simulate\n"
        "def board(pieces):\n"
        "    p = Problem.new(20, 20, 1, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=None)\n"
        "    p.add_heater(1, 1.0, rect=(8, 8, 12, 12))\n"
        "    for j in range(40 if pieces else 1):\n"
        "        p.add_zone(1, rect=(0.5 * j, 0, 0.5 * (j + 1), 20) if pieces else (0, 0, 20, 20))\n"
        "    return p\n"
        "def rise(p, rule):\n"
        "    variant.set_rule(rule)\n"
        "    return simulate(p, SolverOptions(models=('fvm',), cell_mm=1.0)).results['fvm'].t_max\n"
        "one, strips = board(False), board(True)\n"
        "print(rise(one, 'max_point'), rise(strips, 'max_point'), rise(strips, 'max_cell'))\n"
    )
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd=str(HERE.parents[1]), timeout=170)
    assert out.returncode == 0, out.stderr
    one, union, old = (float(v) for v in out.stdout.split())
    assert union == pytest.approx(one, abs=1e-9)                    # abutting strips equal one zone under the per-point union
    assert old > one + 5.0                                          # the old rule loses the copper: about 14 K hotter on this board
