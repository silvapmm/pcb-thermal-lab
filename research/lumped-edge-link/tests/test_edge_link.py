#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_edge_link.py
@brief Tests of the first-link prototype of research/lumped-edge-link on the frozen pre-fix copy: it is built, leaves the program untouched, is mirror symmetric, the ring-1 potential equals a brute-force field, and the prototype equals the adopted program to rounding.
@details Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/lumped-edge-link/tests
"""

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "lib"))
import boards as B  # noqa: E402
import variants as V  # noqa: E402


@pytest.fixture(autouse=True)
def restore_program():
    """!
    @brief Put the program's own Lumped module back after every test.
    @return Generator.
    """
    import pcbthermal.api as api
    import pcbthermal.lumped as orig
    yield
    api.lumped = orig


def _rise(p, v):
    """!
    @brief Part peak and mean of the Lumped with a variant installed.
    @param p Problem.
    @param v Variant name.
    @return (mean, peak) in K.
    """
    V.install(v)
    m, x, _ = B.part_read(p, "lumped", 0.5)
    return m, x


def test_shipped_module_is_untouched_by_the_variants():
    """!
    @brief Installing a variant never writes into pcbthermal.lumped (the prototypes are exec'd copies of the frozen pre-fix text).
    @return None.
    """
    import pcbthermal.lumped as orig
    p = B.board(60, 40, 6, (8, 20), h_side=10)
    before = B.part_read(p, "lumped", 0.5)
    _rise(p, "first:zone")
    assert V.load("first:zone") is not orig
    assert hasattr(orig, "_ring1_potential")               # the adopted fix lives in the program
    import pcbthermal.api as api
    api.lumped = orig
    assert B.part_read(p, "lumped", 0.5) == before


@pytest.mark.parametrize("pos,side,h_side", [((3, 40), 6, 10), ((50, 40), 6, 10), ((6, 6), 8, 50), ((8, 20), 6, 0)])
def test_adoption_prototype_equals_shipped_program(pos, side, h_side):
    """!
    @brief Adoption check: the prototype "first:zone" built on the frozen pre-fix copy and the Lumped module shipped in the tree agree to rounding (mean and peak of the part).
    @param pos Part centre in mm.
    @param side Part side in mm.
    @param h_side Edge coefficient in W/m2K.
    @return None.
    """
    p = B.board(100, 80, side, pos, h_side=h_side)
    ra, rb = _rise(p, "first:zone"), _rise(p, "shipped")
    assert ra[0] == pytest.approx(rb[0], rel=1e-9, abs=1e-9)
    assert ra[1] == pytest.approx(rb[1], rel=1e-9, abs=1e-9)


def test_every_variant_builds():
    """!
    @brief Every anchor of lib/variants.py exists in the frozen pre-fix text (a changed frozen copy fails here, not silently).
    @return None.
    """
    text = V.FROZEN.read_text()
    for name in ("expo", "expo_peak", "img", "pot", "pot_first", "pot_rings", "delta", "first", "first:zone"):
        compile(V.source(name, text), name, "exec")


@pytest.mark.parametrize("variant", ["first", "first:zone", "expo_peak"])
def test_mirror_symmetry(variant):
    """!
    @brief A part at the left side and its mirror image at the right side of the board read the same (to 1e-9 K).
    @param variant Variant name.
    @return None.
    """
    a = B.board(60, 40, 6, (8, 20), h_side=10)
    b = B.board(60, 40, 6, (52, 20), h_side=10)
    ra, rb = _rise(a, variant), _rise(b, variant)
    assert ra[1] == pytest.approx(rb[1], abs=1e-9)
    assert ra[0] == pytest.approx(rb[0], abs=1e-9)


def test_ring1_potential_equals_brute_force_field():
    """!
    @brief The ring-1 mean potential of the prototype equals the mean of the full-field potential over the ring-1 cells (the earlier study's `_total_potential`).
    @return None.
    """
    mod = V.load("pot")
    fast = V.load("first")
    ny, nx, dx = 40, 60, 5e-4
    cov = np.zeros((ny, nx))
    cov[15:21, 10:18] = 1.0
    mask = np.zeros((ny, nx), dtype=bool)
    mask[13:23, 8:20] = True
    mask &= cov == 0
    full = mod._total_potential(cov, dx, dx, ny, nx)
    assert fast._ring1_potential(cov, dx, dx, ny, nx, mask) == pytest.approx(float(full[mask].mean()), rel=1e-12)


def test_image_potential_of_one_point_is_the_analytic_one():
    """!
    @brief A single source cell and an insulated side: the potential of the module is -ln r - ln r_image (+ the terms of the other images), checked at one point for the side image alone.
    @return None.
    """
    mod = V.load("first")
    mod.RHO = 1.0
    ny, nx, dx = 20, 40, 1e-3
    cov = np.zeros((ny, nx))
    cov[10, 5] = 1.0
    mask = np.zeros((ny, nx), dtype=bool)
    mask[10, 12] = True
    got = mod._ring1_potential(cov, dx, dx, ny, nx, mask)
    sx, sy = 5.5e-3, 10.5e-3
    px, py = 12.5e-3, 10.5e-3
    expect = 0.0
    for mx in (-1, 0, 1):
        for my in (-1, 0, 1):
            xi = sx if mx == 0 else (-sx if mx < 0 else 2 * nx * dx - sx)
            yi = sy if my == 0 else (-sy if my < 0 else 2 * ny * dx - sy)
            expect += np.log(max(np.hypot(px - xi, py - yi), 0.447 * dx))
    assert got == pytest.approx(expect, rel=1e-12)


def test_far_part_is_barely_moved_and_edge_part_is_raised():
    """!
    @brief The first-link change raises a part at a side (gap 0, 6 mm, 100 x 80 mm) by more than 5 % and a part 25 mm from every side changes by less than 3 %.
    @return None.
    """
    near = B.board(100, 80, 6, (3, 40), h_side=10)
    far = B.board(100, 80, 6, (50, 40), h_side=10)
    n0, n1 = _rise(near, "program")[1], _rise(near, "first")[1]
    f0, f1 = _rise(far, "program")[1], _rise(far, "first")[1]
    assert n1 / n0 > 1.05
    assert abs(f1 / f0 - 1) < 0.03


def test_a_footprint_of_more_than_3600_cells_keeps_the_program_link():
    """!
    @brief A 40 mm part (6400 cells at 0.5 mm) is above the limit of the cell-resolved potentials: the correction is not applied and the numbers equal the program's.
    @return None.
    """
    p = B.board(100, 80, 40, (22, 40), h_side=10)
    assert _rise(p, "first") == _rise(p, "program")
