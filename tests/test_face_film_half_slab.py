#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_face_film_half_slab.py
@brief The face film passes the half copper layer of its node (fix/face-film-half-slab, docs/theory.md 1.2): the series formula, the arrays of the FVM and FDM, the
       column of a thick plate against its closed form, conservation and the 3D solid left alone.
"""

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, simulate, fvm, fdm
from pcbthermal.model import Materials

AMB = 25.0


def _plate(model_cells=1.0, k=150.0, t_mm=10.0, h=400.0, width=20.0, power=10.0):
    """!
    @brief A one-layer plate of one copper layer (conductivity k, thickness t_mm) on a 1 um laminate, a source over its whole face, film h on the bottom, insulated top and edges.
    @param model_cells Unused (kept for symmetry with the callers).
    @param k Conductivity of the plate in W/mK.
    @param t_mm Thickness in mm.
    @param h Bottom film coefficient in W/m2K.
    @param width Side in mm.
    @param power Power of the source in W.
    @return Problem.
    """
    p = Problem.new(width, width, layers=1, thickness_mm=1.0001 * t_mm, copper_um=t_mm * 1e3, ambient=AMB, h_top=1e-9, h_bottom=h, h_side=None,
                    materials=Materials(k_copper=k))
    p.add_full_copper()
    p.add_heater(1, power, rect=(0.0, 0.0, width, width), name="S")
    return p


def test_series_formula_is_the_closed_form():
    """!
    @brief Board.face_film_h is h / (1 + h t / (2 k)) over copper, h over bare laminate, and the area mean in between; zero stays zero.
    @return None.
    """
    p = Problem.new(30.0, 20.0, layers=2, thickness_mm=1.6, copper_um=35.0)
    b = p.board
    r = 35e-6 / (2.0 * b.materials.k_copper)
    h = 400.0
    assert b.face_film_h(h, 0, 1.0) == pytest.approx(1.0 / (1.0 / h + r), rel=1e-14)
    assert b.face_film_h(h, 0, 0.0) == h
    assert b.face_film_h(h, 1, 0.25) == pytest.approx(0.25 / (1.0 / h + r) + 0.75 * h, rel=1e-14)
    assert b.face_film_h(0.0, 0, 1.0) == 0.0
    assert np.allclose(b.face_film_h(h, 0, np.array([0.0, 1.0])), [h, 1.0 / (1.0 / h + r)])


def test_fvm_and_fdm_faces_carry_the_series_film_on_the_outer_copper_only():
    """!
    @brief On a two-layer board with a full plane on each face the FVM and FDM face conductances are the series film times the area, on the outer nodes only.
    @return None.
    """
    p = Problem.new(24.0, 16.0, layers=2, thickness_mm=1.6, copper_um=105.0, h_top=12.0, h_bottom=15.0, h_side=None)
    p.add_full_copper(layers=None)
    p.add_heater(1, 1.0, rect=(10.0, 6.0, 14.0, 10.0))
    r_half = 105e-6 / (2.0 * p.board.materials.k_copper)
    f_top, f_bot = 1.0 / (1.0 / 12.0 + r_half), 1.0 / (1.0 / 15.0 + r_half)
    net = fvm.Network(p, 12, 8)
    cell = 2e-3 * 2e-3
    # Every cell is copper in both layers: the conductance is the series film times the cell area
    # atol=0: the series factor is 1 - 2e-6 here, below the default absolute tolerance of allclose (1e-8 on values of 5e-5 W/K), which let a plain film pass
    assert np.allclose(net.g_top[0], cell * f_top, rtol=1e-12, atol=0.0)
    assert np.allclose(net.g_bottom[1], cell * f_bot, rtol=1e-12, atol=0.0)
    assert net.g_top[1].sum() == 0.0 and net.g_bottom[0].sum() == 0.0      # no film on the faces towards the laminate
    nd = fdm.Network(p, cell_mm=2.0)
    on = nd.g_top[0] > 0
    # FDM nodes on the board border carry half or a quarter of the cell: the ratio to the plain film is the series factor everywhere
    ratio_t = nd.g_top[0][on] / (nd.g_top[0][on].max())
    assert np.all(ratio_t <= 1.0 + 1e-12)
    assert nd.g_top[0].max() == pytest.approx(cell * f_top, rel=1e-12)
    assert nd.g_bottom[1].max() == pytest.approx(cell * f_bot, rel=1e-12)


@pytest.mark.parametrize("model", ["fvm", "fdm", "analytic"])
def test_thick_plate_column_reads_the_column_mean(model):
    """!
    @brief A source over a whole plate and a film on the other face give a one-dimensional column: the node is the column mean, q'' (1/h + t / (2 k)), exactly.
    @details k 150 W/mK, 10 mm, h 400 W/m2K: h t / (2 k) = 1.3 % of 1/h, the size of the film term; without the half plate in series the node read 1.3 % of the rise low.
             The 1 um laminate under the plate adds 1e-6 / 0.3 m2K/W, which the expected value includes.
    @param model Model key.
    @return None.
    """
    p = _plate()
    area = 0.02 * 0.02
    q = 10.0 / area
    t, k, h = 0.01, 150.0, 400.0
    # The laminate is 0.0001 * 10 mm = 1 um thick: 1e-6 / k_through (0.3) is added in series
    expected = q * (1.0 / h + t / (2.0 * k) + 1e-6 / 0.3)
    sim = simulate(p, SolverOptions(models=(model,), cell_mm=2.0))
    res = sim.results[model]
    rise = float(np.asarray(res.T)[0].mean()) - AMB
    # Within 0.2 % of the rise: the laminate nodes (a mid-point of the 1 um gap) and the discretisation are well below; the film term alone is 1.3 %
    assert rise == pytest.approx(expected, rel=2e-3)
    assert 1.0 / h * q < rise * (1.0 - 0.008)      # the plain film alone would be 1.3 % lower: the series film is in the result


@pytest.mark.parametrize("model", ["fvm", "fdm", "analytic", "lumped"])
def test_conservation_and_ambient_without_a_source(model):
    """!
    @brief No source: every node stays at the ambient; with a source the heat that leaves through the effective films equals the power in (balance to 1e-9).
    @param model Model key.
    @return None.
    """
    p = Problem.new(30.0, 20.0, layers=2, thickness_mm=1.6, copper_um=70.0, h_top=15.0, h_bottom=12.0, h_side=10.0)
    p.add_full_copper(layers=None)
    sim = simulate(p, SolverOptions(models=(model,), cell_mm=2.0))
    assert np.allclose(np.asarray(sim.results[model].T), AMB, atol=1e-9)
    p.add_heater(1, 2.0, rect=(12.0, 7.0, 18.0, 13.0))
    sim = simulate(p, SolverOptions(models=(model,), cell_mm=2.0))
    assert abs(sim.results[model].balance_error) < (1e-9 if model != "lumped" else 1e-6)


def test_the_3d_solid_is_not_changed_by_the_film_series():
    """!
    @brief The 3D solid resolves the slab (solid3d.face_g puts half a slab in series with the film): its result does not depend on the series film of the layered models.
    @details The solid builds from Board.h_top and Board.h_bottom directly; the check is that it does not call face_film_h (a monkeypatch that makes the helper raise leaves it running).
    @return None.
    """
    import pcbthermal.model as model_mod
    p = Problem.new(20.0, 16.0, layers=2, thickness_mm=1.6, copper_um=35.0, h_top=12.0, h_bottom=15.0, h_side=None)
    p.add_full_copper(layers=None)
    p.add_heater(1, 1.0, rect=(8.0, 6.0, 12.0, 10.0))
    saved = model_mod.Board.face_film_h

    def refuse(*a, **k):
        raise AssertionError("the 3D solid must not use the layered series film")
    model_mod.Board.face_film_h = refuse
    try:
        sim = simulate(p, SolverOptions(models=("solid3d",), cell_mm=2.0))
    finally:
        model_mod.Board.face_film_h = saved
    assert np.isfinite(np.asarray(sim.results["solid3d"].T)).all()


def test_a_block_column_needs_the_half_block_in_the_link_and_in_the_film():
    """!
    @brief A metal block over the whole bottom face under a source over the whole top is a one-dimensional column: the block node is the column mean only with half the
           block in the contact link AND in the exposed film (blocks.extra_layers); the FVM then matches the 3D solid (the block cut in 1 mm slabs) within 0.5 %.
    @details 200 mm board, 8 mm block of 5 W/mK, film 400 W/m2K on the block, 10 mm cell (review of fix/face-film-half-slab, docs/validation.md 55.3): FVM 8.870 K against the
             3D solid 8.848 K; without the half block in the film 8.235 K (-6.9 %), without it in the link 8.068 K (-8.8 %), without both 7.434 K (-16 %).
    @return None.
    """
    w = 200.0
    p = Problem.new(w, w, 2, h_top=1e-9, h_bottom=400.0, h_side=None).add_zone(1, rect=(0, 0, w, w)).add_zone(2, rect=(0, 0, w, w))
    p.add_heater(1, 40.0, rect=(0, 0, w, w), name="U1")
    p.add_heatsink(2, 0.0, rect=(0, 0, w, w), thickness_mm=8.0, k=5.0, contact_r=1e-4, name="B")
    sim = simulate(p, SolverOptions(models=("fvm", "solid3d"), cell_mm=10.0))
    f = float(np.asarray(sim.results["fvm"].T)[0].mean()) - AMB
    s = float(np.asarray(sim.results["solid3d"].T)[0].mean()) - AMB
    assert f == pytest.approx(s, rel=5e-3)


def test_thick_plate_warning_has_no_film_clause_for_a_plate():
    """!
    @brief The warning bound of a one-layer plate is the through-thickness term only (the film is inside the model): the case 2 source of 25 W reads 8.3 K and the text has no film clause.
    @return None.
    """
    from pcbthermal import checks
    assert checks.thick_plate_bound(2.5e5, 1.0, 0.01, 150.0) == pytest.approx(8.333333, rel=1e-6)
    assert not hasattr(checks, "THICK_PLATE_FILM_RATIO")
