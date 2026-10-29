#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_block_side_loss.py
@brief The side walls of a finned metal block lose heat with the plain coefficient: the fins stand on the exposed face, not on the sides.

@details Regression tests of the correction of 2026-10-25 (`blocks.extra_layers`, `solid3d.py`): the loss of a block node to the air is
         h_exp A c + h_wall t L_edge, with h_exp = h_face fin_ratio + h_extra and h_wall = h_face + h_extra.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, blocks, fvm, simulate, solid3d
from pcbthermal.geometry import coverage_fraction


def board(fins=None, h_extra=0.0):
    """!
    @brief The 60 x 40 mm two-layer board with a 3 W part and a 40 x 30 x 3 mm aluminium block on the bottom face.
    @param fins None or (height, thickness, pitch) in mm.
    @param h_extra Extra coefficient of the block in W/m2K.
    @return Problem.
    """
    p = Problem.new(60, 40, 2)
    p.board.h_mode, p.board.h_top, p.board.h_bottom = "manual", 10.0, 12.0
    p.add_zone(1, rect=(1, 1, 59, 39))
    p.add_zone(2, rect=(1, 1, 59, 39))
    p.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="U1")
    kw = {} if fins is None else dict(fin_height_mm=fins[0], fin_thickness_mm=fins[1], fin_pitch_mm=fins[2])
    p.add_heatsink(2, h_extra, rect=(10, 5, 50, 35), thickness_mm=3.0, k=204.0, contact_r=5e-5, **kw)
    return p


def layers_of(p, cell_mm=1.0):
    """!
    @brief Call blocks.extra_layers on a regular grid of the board.
    @param p A Problem.
    @param cell_mm Cell size in mm.
    @return Tuple (layers, cell area in m2, dx in m, number of cells).
    """
    nx, ny = int(round(p.board.width / (cell_mm * 1e-3))), int(round(p.board.height / (cell_mm * 1e-3)))
    dx, dy = p.board.width / nx, p.board.height / ny
    area = np.full((ny, nx), dx * dy)
    fill = np.ones((p.board.layers, ny, nx))
    cover = lambda poly, n: coverage_fraction(poly, nx, ny, dx, dy, samples=n)           # noqa: E731
    return blocks.extra_layers(p, cover, area, fill, dx, dy), dx * dy, dx, (nx, ny)


@pytest.mark.parametrize("h_extra", [0.0, 7.0])
def test_side_loss_uses_the_plain_coefficient(h_extra):
    p = board((15.0, 1.5, 8.0), h_extra)
    (ly,), a, dx, _ = layers_of(p)
    s = p.heatsinks[0]
    h_face = p.board.h_bottom
    assert blocks.fin_ratio(h_face, s) > 3.0                                    # The test only means something with real fins
    # Edge cells of a 40 x 30 mm rectangle on 1 mm cells (whole cells): one side length dx per exposed side
    g = ly["g_amb"]
    c = ly["cov"]
    face_part = (h_face * blocks.fin_ratio(h_face, s) + h_extra) * a * c
    side_part = g - face_part
    # Side walls: perimeter 140 mm x 3 mm thick, at h_face + h_extra
    assert side_part.sum() == pytest.approx((h_face + h_extra) * s.thickness * 0.140, rel=1e-3)          # The cover sampling moves the length by 0.02 %
    assert ly["h_wall"].max() == pytest.approx(h_face + h_extra)
    assert ly["h_total"].max() == pytest.approx(h_face * blocks.fin_ratio(h_face, s) + h_extra)
    # Interior cells (all four neighbours covered) carry no side loss
    assert np.allclose(side_part[19:21, 29:31], 0.0)


def test_plain_block_is_unchanged():
    p = board(None, 5.0)
    (ly,), a, dx, _ = layers_of(p)
    s = p.heatsinks[0]
    h = p.board.h_bottom + 5.0
    assert ly["h_wall"].max() == pytest.approx(ly["h_total"].max()) == pytest.approx(h)
    # The old formula h_tot (A c + t L_edge) is reproduced exactly when the fin ratio is 1
    assert ly["g_amb"].sum() == pytest.approx(h * (0.040 * 0.030 + s.thickness * 0.140), rel=1e-3)


def test_energy_balance_closes_and_finned_rise_follows_the_measured_change():
    # FVM rise of the 60 x 40 board of tests/test_heatsink_part.py (10 W/m2K on both faces), 1 mm cells
    expected = {(15.0, 1.5, 8.0): 65.008, (15.0, 1.5, 12.0): 69.969, (30.0, 1.5, 8.0): 56.553}      # After the correction
    before = {(15.0, 1.5, 8.0): 61.233, (15.0, 1.5, 12.0): 66.350, (30.0, 1.5, 8.0): 53.171}        # With the fin ratio on the sides
    for fins, rise in expected.items():
        p = board(fins)
        p.board.h_bottom = 10.0
        r = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
        assert abs(r.balance_error) < 1e-9
        assert r.t_max - 25.0 == pytest.approx(rise, abs=0.01), (fins, r.t_max)
        assert (r.t_max - 25.0) / before[fins] - 1.0 > 0.05                                # +5.5 to +6.4 % against the old code
    p = board(None)
    p.board.h_bottom = 10.0
    assert fvm.solve_steady(p, cell_mm=1.0).delta_t == pytest.approx(88.3307, abs=0.01)      # A plain plate does not move


@pytest.mark.parametrize("h_extra", [0.0, 7.0])
def test_solid3d_side_walls_use_the_plain_coefficient(h_extra):
    # The 3D solid has its own copy of the block boundary (solid3d.Solid): the side walls of every block slab must see h_face + h_extra,
    # the outer slab's face h_face * fin_ratio + h_extra in series with half a slab
    p = board((15.0, 1.5, 8.0), h_extra)
    p.board.h_bottom = 10.0
    net = solid3d.Solid(p, cell_mm=1.0)
    s = p.heatsinks[0]
    g = net.g["blocks"].reshape(net.ns, net.ny, net.nx)
    blk = [k for k, sl in enumerate(net.slabs) if sl["kind"] == "blk"]
    assert len(blk) == 3                                                       # 3 mm of block: three slabs, so the side area is split over them
    outer = blk[-1]                                                            # Bottom face: the last slab is the one that faces the air
    h_exp = 10.0 * blocks.fin_ratio(10.0, s) + h_extra
    face = (net.area_b / (1.0 / h_exp + net.slabs[outer]["dz"] / (2.0 * net.slabs[outer]["kz"])) * net.faces[1]["cov"]).sum()
    side = g[blk].sum() - face
    assert side == pytest.approx((10.0 + h_extra) * s.thickness * 0.140, rel=1e-9)          # Perimeter 140 mm on whole cells, no fin ratio
    assert side < 0.5 * h_exp * s.thickness * 0.140                                # The old code put h_exp on the sides (3 to 5 times more)


def test_solid3d_finned_rise_after_the_correction():
    # Rise of the hottest point of the 3D solid on the finned board of validation.md section 12 D (1 mm cells); 61.7 K before the correction
    p = board((15.0, 1.5, 8.0))
    p.board.h_bottom = 10.0
    r = solid3d.solve_steady(p, cell_mm=1.0)
    assert abs(r.balance_error) < 1e-9
    assert r.delta_t == pytest.approx(65.472, abs=0.01)
