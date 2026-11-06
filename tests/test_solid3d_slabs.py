#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_solid3d_slabs.py
@brief The 3D solid cuts each dielectric gap into slabs by its thickness (0.2 mm, 4 to 16) and adds the face term of a part over bare laminate:
       the rule, the counts, a closed-form column, the face term, convergence in the slabs, the energy balance and the unchanged old meaning of an integer.
"""

import numpy as np
import pytest

from pcbthermal import Problem, analysis, solid3d


def two_layer(copper_um=35.0, thickness_mm=1.6):
    """!
    @brief A small two-layer board with a 4 mm heater square at the centre.
    @param copper_um Copper thickness of every layer in micrometres.
    @param thickness_mm Board thickness in millimetres.
    @return Problem.
    """
    p = Problem.new(20.0, 20.0, layers=2, thickness_mm=thickness_mm, copper_um=copper_um)
    p.board.h_top = p.board.h_bottom = 1000.0
    p.board.h_side = None
    p.add_heater(1, 4.0, rect=(8, 8, 12, 12), name="U")
    return p


def test_slab_rule_by_thickness():
    """0.2 mm slabs, at least 4 and at most 16 per gap; exact multiples do not round up."""
    assert [solid3d.slab_rule(d * 1e-3) for d in (0.05, 0.2, 0.8, 0.81, 1.065, 1.53, 3.13, 5.0)] == [4, 4, 4, 5, 6, 8, 16, 16]


def test_shipped_templates_change_only_where_the_gap_is_thick():
    """The 2-layer board (1.53 mm) gets 8 slabs, the core of the 4-layer template 6, and 6 to 10 layers keep 4 everywhere."""
    p2 = Problem.new(20.0, 20.0, layers=2, thickness_mm=1.6, copper_um=35.0)
    assert solid3d.slabs_per_gap(p2) == [solid3d.slab_rule(float(p2.board.gap_thicknesses()[0]))] == [8]
    for layers, expect in ((4, [4, 6, 4]), (6, [4] * 5), (8, [4] * 7), (10, [4] * 9)):
        p = Problem.new(20.0, 20.0, layers=layers, thickness_mm=1.6, copper_um=35.0)
        p.board.dielectrics = []                                      # an advanced stack-up, filled by the template
        p.board.apply_template()
        assert solid3d.slabs_per_gap(p) == expect


def test_an_integer_keeps_the_old_uniform_meaning_and_a_list_is_per_gap():
    p = two_layer()
    assert solid3d.slabs_per_gap(p, 4) == [4]
    assert solid3d.unknowns(p, 1.0, 4)[1] == 6 and solid3d.unknowns(p, 1.0)[1] == 10 and solid3d.unknowns(p, 1.0, [5])[1] == 7
    with pytest.raises(ValueError):
        solid3d.slabs_per_gap(p, [4, 4])
    with pytest.raises(ValueError):
        solid3d.slabs_per_gap(p, 0)


def test_unknowns_counts_the_slabs_the_solid_builds_for_each_rule():
    for p in (two_layer(), two_layer(thickness_mm=3.2), Problem.new(30.0, 20.0, layers=1, thickness_mm=1.6, copper_um=35.0)):
        for nd in (None, 4, 8):
            n, ns, nx, ny = solid3d.unknowns(p, 2.0, nd)
            net = solid3d.Solid(p, 2.0, nd)
            assert (n, ns, nx, ny) == (net.n, net.ns, net.nx, net.ny)


def test_a_full_copper_column_matches_the_series_closed_form_for_any_slab_count():
    """Uniform heater over a full-copper board without side loss: a 1D problem, exact for any slabs (series of half slabs); the node of the top copper is P / (1/R_top + 1/R_bot)."""
    p = Problem.new(20.0, 20.0, layers=2, thickness_mm=1.6, copper_um=35.0).add_full_copper()
    b = p.board
    b.h_top = b.h_bottom = 500.0
    b.h_side = None
    p.add_heater(1, 3.0, rect=(0, 0, 20, 20), name="all")
    A = 0.02 * 0.02
    t = np.asarray(b.copper_thickness)
    d, kz = float(b.gap_thicknesses()[0]), float(b.gap_properties()[0][0])
    kc = b.materials.k_copper
    r_top = 1.0 / (b.h_top * A) + t[0] / 2.0 / (kc * A)
    r_bot = t[0] / 2.0 / (kc * A) + d / (kz * A) + t[1] / (kc * A) + 1.0 / (b.h_bottom * A)
    rise = 3.0 / (1.0 / r_top + 1.0 / r_bot)
    for nd in (None, 4, 12):
        res = solid3d.solve_steady(p, 2.0, nd)
        assert res.T[0].max() - b.ambient == pytest.approx(rise, rel=1e-9)
        assert "face_peak" not in res.arrays                         # full copper: no bare laminate under the part


def test_energy_balance_and_residual_with_the_rule():
    res = solid3d.solve_steady(two_layer(thickness_mm=3.2), 1.0)
    assert abs(res.balance_error) < 1e-9 and res.residual < 1e-9
    assert res.extras["slabs"] == 2 + 16


def test_face_term_of_a_part_over_bare_laminate():
    """The result carries q t_cu / (2 k_z A) in the cells under the part and the part statistics read it; the node field is unchanged."""
    p = two_layer()
    cell = 1.0
    res = solid3d.solve_steady(p, cell)
    b = p.board
    t_cu = float(np.asarray(b.copper_thickness)[0])
    kz = float(b.gap_properties()[0][0])
    per_cell = 4.0 / 16.0                                            # 16 cells of 1 mm under the 4 mm square
    expect = per_cell * t_cu / (2.0 * kz * (1e-3) ** 2)
    assert res.arrays["face_peak"][0].max() == pytest.approx(expect, rel=1e-9)
    assert res.arrays["face_mean"][0].max() == pytest.approx(expect, rel=1e-9)         # bare cells: the mean weights by the bare share (1)
    assert not res.arrays["face_peak"][1].any()                       # nothing on the bottom layer
    st = analysis.heater_stats(res, p)[0]
    assert st["t_max"] == pytest.approx(res.T[0][8:12, 8:12].max() + expect, rel=1e-12)


def test_face_term_agrees_with_the_layered_models_term():
    """Same function, same numbers: the layered FVM and the solid add the same face rise for the same source on the same raster."""
    from pcbthermal import fvm
    p = two_layer()
    f = fvm.solve_steady(p, 1.0)
    s = solid3d.solve_steady(p, 1.0)
    assert np.allclose(f.arrays["face_peak"], s.arrays["face_peak"], rtol=1e-12)


def test_no_face_term_on_a_board_with_a_metal_block():
    p = two_layer()
    p.add_heatsink(1, 0.0, rect=(2, 2, 18, 18), thickness_mm=2.0)
    assert "face_peak" not in solid3d.solve_steady(p, 2.0).arrays


def test_slabs_converge_from_above_and_the_rule_is_between_four_and_sixteen():
    """A 2 mm part on a 3.2 mm board: the mean temperature under it (face term included) falls with the slabs (the heat has more room to spread); the rule's 16 equal an explicit 16."""
    p = Problem.new(20.0, 20.0, layers=2, thickness_mm=3.2, copper_um=35.0)
    p.board.h_top = p.board.h_bottom = 1000.0
    p.board.h_side = None
    p.add_heater(1, 1.0, rect=(9, 9, 11, 11), name="U")
    mean = {}
    for n in (4, 8, 16, None):
        res = solid3d.solve_steady(p, 0.5, n)
        mean[n] = analysis.heater_stats(res, p)[0]["t_mean"]
    assert mean[4] > mean[8] > mean[16]
    assert mean[None] == pytest.approx(mean[16], rel=1e-12)
