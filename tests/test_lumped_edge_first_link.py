#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_lumped_edge_first_link.py
@brief The first footprint-to-ring link of the thermal network sees the mirror images of the board sides (fix/lumped-edge-first-link, research/lumped-edge-link INTEGRATION.md 2 and 3).

@details Held here: the logarithmic potential of the footprint with its images against a brute-force sum and a closed form (one source and its images), the mirror symmetry of the
         board, a 6 mm part touching a side and in a corner of a 40 x 40 mm board against the independent 3D layered solver (before the images -9.9 % and -15.9 % of the rise, now about
         -3 %), the centred part moving only a few points hot, a footprint above IMAGE_MAX_CELLS keeping the plain link, and the cost of a 30 mm part.
"""

import os
import sys
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
import layered3d as L3                                         # noqa: E402

from pcbthermal import Problem, SolverOptions, lumped, simulate   # noqa: E402
from pcbthermal.model import Materials                         # noqa: E402

DX = 0.5e-3
CU_T, GAP, K_CU, K_FR4, H = 35e-6, 1.5e-3, 400.0, 0.3, 10.0


def board(w_mm, h_mm, side_mm, centre, h_side=None):
    """!
    @brief A uniform two-layer board with isotropic FR-4 and one square 1 W source on layer 1.
    @param w_mm Board width in mm.
    @param h_mm Board height in mm.
    @param side_mm Side of the source in mm.
    @param centre (x, y) centre of the source in mm.
    @param h_side Edge coefficient in W/m2K (None: insulated).
    @return Problem.
    """
    mat = Materials(k_copper=K_CU, k_fr4_through=K_FR4, k_fr4_inplane=K_FR4)
    p = Problem.new(w_mm, h_mm, layers=2, thickness_mm=(2 * CU_T + GAP) * 1e3, copper_um=CU_T * 1e6, ambient=0.0, h_top=H, h_bottom=H, h_side=h_side, materials=mat)
    p.add_full_copper()
    s = side_mm / 2
    p.add_heater(1, 1.0, rect=(centre[0] - s, centre[1] - s, centre[0] + s, centre[1] + s), name="U")
    return p


def lumped_rise(p, cell_mm=0.5):
    """!
    @brief Hottest rise of the LPTN model.
    @param p Problem.
    @param cell_mm Cell in mm.
    @return float Rise in K.
    """
    return simulate(p, SolverOptions(models=("lumped",), cell_mm=cell_mm)).results["lumped"].t_max


def ref3d(w_mm, h_mm, side_mm, centre):
    """!
    @brief Peak temperature of the source in the independent 3D layered solver (insulated sides, film under the source).
    @param w_mm Board width in mm.
    @param h_mm Board height in mm.
    @param side_mm Side of the source in mm.
    @param centre (x, y) centre of the source in mm.
    @return float Peak rise in K.
    """
    s = side_mm / 2
    c = (centre[0] * 1e-3, centre[1] * 1e-3)
    return L3.solve(DX, int(round(w_mm * 1e-3 / DX)), int(round(h_mm * 1e-3 / DX)), [(CU_T, K_CU, 1), (GAP, K_FR4, 2), (CU_T, K_CU, 1)],
                    (c[0] - s * 1e-3, c[1] - s * 1e-3, c[0] + s * 1e-3, c[1] + s * 1e-3), 1.0, H, H, film_under_source=True)["max_source"]


def test_footprint_potential_with_images_is_the_brute_force_sum():
    """!
    @brief For one cell of a 40 x 40 grid the potential at the centre of another cell is the log distance to the cell itself plus to its eight images (floor 0.447 cell on the diagonal), and
           `_ring1_potential` of a one-cell footprint equals the mean of that over the cells of the ring.
    @return None.
    """
    ny = nx = 40
    dx = dy = 0.5e-3
    cov = np.zeros((ny, nx))
    cov[3, 5] = 1.0
    sx, sy = 5.5 * dx, 3.5 * dy
    mask = np.zeros((ny, nx), dtype=bool)
    mask[3:6, 6:9] = True
    cy, cx = np.nonzero(mask)
    gx, gy = (cx + 0.5) * dx, (cy + 0.5) * dy
    expected = np.zeros(len(gx))
    for mx in (-1, 0, 1):
        for my in (-1, 0, 1):
            xi = sx if mx == 0 else (-sx if mx < 0 else 2 * nx * dx - sx)
            yi = sy if my == 0 else (-sy if my < 0 else 2 * ny * dy - sy)
            expected += np.log(np.maximum(np.hypot(gx - xi, gy - yi), 0.447 * dx))
    assert lumped._ring1_potential(cov, dx, dy, ny, nx, mask) == pytest.approx(expected.mean(), rel=1e-12)


def test_images_raise_the_potential_next_to_a_side_and_vanish_with_distance():
    """!
    @brief The potential is the mean of ln(distance): the images of a footprint at a side are close, so they lower it (a hotter source) by more than the far images of a centred footprint do.
    @return None.
    """
    ny = nx = 100
    near, far = np.zeros((ny, nx)), np.zeros((ny, nx))
    near[48:52, 0:4] = 1.0
    far[48:52, 48:52] = 1.0
    d_near = lumped._footprint_potentials_images(near, 1e-3, 1e-3)[0] - lumped._footprint_potentials(near, 1e-3, 1e-3)[0]
    d_far = lumped._footprint_potentials_images(far, 1e-3, 1e-3)[0] - lumped._footprint_potentials(far, 1e-3, 1e-3)[0]
    assert d_near < d_far - 1.0, (d_near, d_far)
    # Above IMAGE_MAX_CELLS the cell-resolved potentials are not built and the plain link is kept
    big = np.ones((ny, nx))
    assert lumped._footprint_potentials_images(big, 1e-3, 1e-3) is None


def test_mirror_symmetry_of_the_board():
    """!
    @brief A part at the left side and its mirror image at the right side read the same (the images are symmetric), to 1e-6 K.
    @return None.
    """
    left = lumped_rise(board(40, 40, 6, (3.0, 20.0)))
    right = lumped_rise(board(40, 40, 6, (37.0, 20.0)))
    assert left == pytest.approx(right, abs=1e-6)


@pytest.mark.parametrize("centre,floor", [((3.0, 20.0), -5.0), ((3.0, 3.0), -6.0)])
def test_part_touching_a_side_or_a_corner_against_the_independent_3d_solver(centre, floor):
    """!
    @brief A 6 mm part touching a side (gap 0) and in a corner of a 40 x 40 mm board, insulated sides, against the independent 3D layered solver. The research folder measured it against a
           converged 3D at -9.9 % (side) and -15.9 % (corner) before the images and -3.1 % and -3.3 % with them; here the 3D solver is the cell-0.5 mm one of the test helper, so the bounds
           are wider than the research's (the part must read at most 5 % (side) and 6 % (corner) too cool, and not hot by more than 3 %).
    @param centre (x, y) centre of the source in mm.
    @param floor Lowest error allowed in percent of the 3D rise.
    @return None.
    """
    lum = lumped_rise(board(40, 40, 6, centre))
    ref = ref3d(40, 40, 6, centre)
    e = 100.0 * (lum / ref - 1.0)
    assert floor < e < 3.0, (lum, ref, e)


def test_centred_part_moves_a_few_points_hot_only():
    """!
    @brief A 6 mm part at the centre of a 100 x 80 mm sheet reads at most 3 points more than with the plain link (the interior factor and the first-ring cap were fitted with the old link),
           and still within 4 % of the 3D solver.
    @return None.
    """
    p = board(100, 80, 6, (50.0, 40.0))
    new = lumped_rise(p)
    old_fn = lumped._footprint_potentials_images
    lumped._footprint_potentials_images = lambda cov, dx, dy: None          # the plain link
    try:
        old = lumped_rise(p)
    finally:
        lumped._footprint_potentials_images = old_fn
    assert 0.0 < 100 * (new / old - 1.0) < 3.0, (new, old)
    assert abs(100 * (new / ref3d(100, 80, 6, (50.0, 40.0)) - 1.0)) < 4.0


def test_a_30_mm_part_stays_fast():
    """!
    @brief The cell-resolved potentials of a 30 mm part (3600 cells at 0.5 mm, the limit) cost under 2 s of the whole LPTN run.
    @return None.
    """
    p = board(100, 80, 30, (50.0, 40.0), h_side=10.0)
    t0 = time.perf_counter()
    lumped_rise(p)
    assert time.perf_counter() - t0 < 2.0


def test_the_footprint_limit_is_a_jump_for_a_part_at_a_side(monkeypatch):
    """!
    @brief The stated limit of docs/validation.md 53.4: a part above IMAGE_MAX_CELLS (a 30.1 mm square at 0.5 mm) keeps the plain link bit for bit, while 30.0 mm takes the images,
           so a part touching a side jumps back to the old deficit (13.36 against 12.18 K; the FVM reads 14.31 and 14.26 K).
    @param monkeypatch pytest fixture.
    @return None.
    """
    def run(side):
        p = Problem.new(100, 80, layers=2, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=15.0, h_side=10.0)
        p.add_full_copper(fill=1.0)
        p.add_heater(1, 1.0, rect=(0.0, 40.0 - side / 2, side, 40.0 + side / 2), name="U")
        return simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"].t_max - p.board.ambient
    below, above = run(30.0), run(30.1)
    assert below == pytest.approx(13.358, abs=0.01) and above == pytest.approx(12.176, abs=0.01)
    monkeypatch.setattr(lumped, "IMAGE_MAX_CELLS", -1)            # the image path switched off everywhere: the plain link of the merge base
    assert run(30.1) == above
    assert run(30.0) < below - 1.0
