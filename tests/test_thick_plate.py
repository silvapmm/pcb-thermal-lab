#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_thick_plate.py
@brief The thick-plate warning: q'' t / (2 k) above 5 % of the rise of a heater (a bound on how much hotter the surface under a source can be than the through-thickness mean of the layered models).
@details The flux is the heat of the part over its footprint for its copper layer and the flux that enters a metal block in the solved result for a block;
         the bound is checked against the real effect of the block's thickness in the 3D solid, which cuts a block into slabs.
"""

import copy

import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.checks import THICK_PLATE_LIMIT, thick_plate_bound
from pcbthermal.examples import example_block_board, example_board


def thick(sim):
    """!
    @brief The thick-plate warnings of a simulation.
    @param sim Simulation.
    @return List of strings.
    """
    return [w for w in sim.warnings if "thick and poorly conducting" in w]


def block_board(side_mm, power, thickness_mm, k, same_face):
    """!
    @brief A 60 x 60 mm two-layer board, a square part at the centre of the top and a 30 mm metal block under a 30 mm copper pad.
    @param side_mm Side of the part in mm.
    @param power Power of the part in W.
    @param thickness_mm Block thickness in mm.
    @param k Block conductivity in W/mK.
    @param same_face True for the block on the top face (the part's own face), False for the bottom face (fed through the board).
    @return Problem.
    """
    p = Problem.new(60, 60, 2).add_zone(1, rect=(0, 0, 60, 60)).add_zone(2, rect=(15, 15, 45, 45))
    p.add_heater(1, power, rect=(30 - side_mm / 2, 30 - side_mm / 2, 30 + side_mm / 2, 30 + side_mm / 2), name="U1")
    p.add_heatsink(1 if same_face else 2, 0.0, rect=(15, 15, 45, 45), thickness_mm=thickness_mm, k=k, contact_r=1e-4, name="B")
    return p


def bound_in(warning):
    """!
    @brief The bound in kelvin quoted by a thick-plate warning.
    @param warning Warning text.
    @return float K.
    """
    return float(warning.split("up to ")[1].split(" K")[0])


def gradient_effect_3d(problem, cell_mm=2.0):
    """!
    @brief What the thickness of the block really does to the hottest point of the part, measured in the 3D solid (which cuts a block into slabs of 1 mm).
    @details (3D solid - FVM) for the block, minus the same for a block of the same size with a conductivity of 1e5 W/mK (no gradient through it): the rest
             of the difference between the two models (spreading in the laminate under a small part) cancels.
    @param problem Problem with one metal block.
    @param cell_mm Cell size in mm.
    @return float K.
    """
    def gap(p):
        sim = simulate(p, SolverOptions(models=("fvm", "solid3d"), cell_mm=cell_mm))
        return sim.results["solid3d"].t_max - sim.results["fvm"].t_max
    stiff = copy.deepcopy(problem)
    stiff.heatsinks[0].k = 1e5
    return gap(problem) - gap(stiff)


def test_the_bound_is_q_t_over_2k_and_degenerate_inputs_give_zero():
    # 5 W over 10 x 10 mm = 50 kW/m2; 10 mm of k 10: 50e3 * 0.01 / 20 = 25 K
    assert thick_plate_bound(5.0, 1e-4, 10e-3, 10.0) == pytest.approx(25.0)
    assert thick_plate_bound(5.0, 0.0, 10e-3, 10.0) == 0.0 and thick_plate_bound(5.0, 1e-4, 0.0, 10.0) == 0.0 and thick_plate_bound(5.0, 1e-4, 1e-3, 0.0) == 0.0
    assert THICK_PLATE_LIMIT == 0.05


@pytest.mark.parametrize("side, power, t, k, same", [(10, 5.0, 6.0, 10.0, True), (3, 2.0, 3.0, 50.0, True), (10, 5.0, 10.0, 2.0, False)])
def test_a_thick_poorly_conducting_block_fires_with_a_bound_above_the_3d_effect(side, power, t, k, same):
    # Measured on 2 mm cells: bound 10.9, 2.2 and 14.7 K against a real effect of 4.85, 0.90 and 1.67 K in the 3D solid (1 mm cells: 11.2, 3.1, 15.0 against 5.00, 1.04, 1.64)
    p = block_board(side, power, t, k, same)
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    w = thick(sim)
    assert len(w) == 1 and "U1" in w[0] and "B is thick" in w[0] and "not added to the results" in w[0] and "footprint" not in w[0]
    effect = gradient_effect_3d(p)
    # A bound above the effect. Since fix/face-film-half-slab the layered block has half the block in its contact link and in its exposed film, so it carries part of the
    # thickness: the remainder (3D solid minus FVM, block against a stiff block) was +4.81 / +0.90 / +1.76 K and is -2.54 / -0.46 / -0.41 K (the 1D half block over-resists a
    # source that spreads inside the block: the FVM is now on the hot side by that much, and the magnitude is smaller in every case)
    assert effect < bound_in(w[0])
    # The temperatures are those of the model: the warning does not change them
    assert sim.reference.t_max == simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0)).reference.t_max


def test_a_small_part_over_a_steel_block_under_the_board_does_not_fire():
    # The flux of the footprint (2 W over 3 x 3 mm) would give 6.7 K, 9.5 % of the rise; the heat that really enters the block has crossed the board and its copper
    # and gives 0.18 K, and the 3D solid sees no effect of the block's thickness at all (0.00 K): the check uses the flux into the block of the solved model
    p = block_board(3, 2.0, 3.0, 50.0, False)
    for model in ("fvm", "fdm"):
        assert thick(simulate(p, SolverOptions(models=(model,), cell_mm=2.0))) == [], model
    assert abs(gradient_effect_3d(p)) < 0.05


@pytest.mark.parametrize("model", ["lumped", "analytic"])
@pytest.mark.parametrize("case", [(3, 2.0, 3.0, 50.0, False), (10, 5.0, 10.0, 2.0, False), (10, 5.0, 6.0, 10.0, True)])
def test_lumped_and_analytic_use_an_auxiliary_fvm_flux_and_agree_with_the_fvm(model, case):
    # These models do not give the flux into the block: a quiet auxiliary FVM run does, so the warning is the one of the FVM run (the same
    # decision and the same bound), not the footprint flux (which would fire on the 3 x 3 mm part over steel under the board)
    p = block_board(*case)
    ref = thick(simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0)))
    w = thick(simulate(p, SolverOptions(models=(model,), cell_mm=2.0)))
    assert len(w) == len(ref) and all("heat flux of the footprint" not in x for x in w)
    if ref:
        assert bound_in(w[0]) == pytest.approx(bound_in(ref[0]), rel=0.15)           # Same flux; the rise of the heater differs a little between models


def test_the_footprint_flux_remains_the_stated_fallback_of_the_check():
    # Called without a result that carries the flux (the auxiliary run is not possible), the check uses the footprint flux and says so
    from pcbthermal.checks import check_thick_plates
    p = block_board(3, 2.0, 3.0, 50.0, False)
    sim = simulate(p, SolverOptions(models=("analytic",), cell_mm=2.0))
    w = check_thick_plates(p, sim.heater_rows(), None)
    assert len(w) == 1 and "heat flux of the footprint" in w[0] and bound_in(w[0]) == pytest.approx(6.7, abs=0.05)


def test_a_conductive_or_thin_block_does_not_fire():
    for side, t, k, same in ((10, 10.0, 204.0, True), (10, 3.0, 50.0, False), (10, 1.0, 10.0, False), (3, 3.0, 204.0, False)):
        sim = simulate(block_board(side, 5.0 if side == 10 else 2.0, t, k, same), SolverOptions(models=("fvm",), cell_mm=2.0))
        assert thick(sim) == [], (side, t, k, same)


def test_one_layer_board_block_temperatures_are_the_block_layer():
    # On a one-layer board the laminate nodes sit between the board layer and the block layer: arrays["block_T"] must be the block, not a laminate node
    p = Problem.new(60, 60, 1).add_full_copper()
    p.add_heater(1, 2.0, rect=(27, 27, 33, 33))
    p.add_heatsink(1, 0.0, rect=(15, 15, 45, 45), thickness_mm=3.0, k=204.0, contact_r=1e-4)
    for model in ("fvm", "fdm"):
        r = simulate(p, SolverOptions(models=(model,), cell_mm=2.0)).results[model]
        assert r.arrays["block_T"].shape[0] == r.arrays["block_cov"].shape[0] == r.arrays["block_flux"].shape[0] == 1, model
        assert r.arrays["block_T"][0].max() == pytest.approx(r.extras["block_top_max"]), model
        # The flux into the block adds up to the heat into the block
        area = r.dx * r.dy if r.grid == "cells" else None
        if area:
            assert (r.arrays["block_flux"][0] * r.arrays["block_cov"][0] * area).sum() == pytest.approx(r.extras["block_top_w_to_block"], rel=1e-9)


def test_a_thick_poorly_conducting_copper_layer_fires():
    # A "copper" layer of 10 mm and k 5 W/mK typed by the user (the program has no such layer of its own)
    p = Problem.new(100, 80, 2).add_zone(1, rect=(0, 0, 100, 80)).add_zone(2, rect=(0, 0, 100, 80))
    p.board.copper_thickness = [10e-3, 35e-6]
    p.board.thickness = 30e-3
    p.board.materials.k_copper = 5.0
    p.add_heater(1, 5.0, rect=(45, 35, 55, 45), name="U1")
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    assert len(thick(sim)) == 1 and "the copper of layer 1" in thick(sim)[0]


def test_the_standard_examples_never_fire():
    for which in ("example", "block"):
        p = example_board() if which == "example" else example_block_board()
        sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
        assert thick(sim) == [], which


def test_the_metal_block_cases_of_the_program_never_fire_and_stay_far_below_the_limit():
    # The 74 cases of research/block-and-fins (block and pad sizes, thickness, metal, interface swept), here a coarse sample of the same 100 x 80 mm board:
    # with the flux that enters the block the criterion is 0.07 % at the median and 0.34 % at the maximum over all 74 (measured, FVM and FDM, 1 and 2 mm cells;
    # 0.50 % and 1.78 % with the footprint flux), 5 % is the limit; the sample adds 6 mm of steel, which is not among the 74 (0.62 %, measured)
    cases = [(t, k, rc) for t in (1.0, 3.0, 6.0) for k in (50.0, 204.0, 386.0) for rc in (1e-4, 1e-3)]
    worst = 0.0
    for t, k, rc in cases:
        p = Problem.new(100, 80, 2).add_zone(1, rect=(0, 0, 100, 80)).add_zone(2, rect=(30, 20, 70, 60))
        p.add_heater(1, 5.0, rect=(45, 35, 55, 45))
        p.add_heatsink(2, 0.0, rect=(30, 20, 70, 60), thickness_mm=t, k=k, contact_r=rc)
        sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
        assert thick(sim) == [], (t, k, rc)
        res = sim.reference
        q = float(res.arrays["block_flux"][0][res.arrays["block_cov"][0] > 0].max())
        worst = max(worst, thick_plate_bound(q, 1.0, t * 1e-3, k) / (sim.heater_rows()[0]["t_max"] - p.board.ambient))
    assert 0.0 < worst < 0.01


def plate(t_mm, k, power, side_mm=10.0, h=400.0, w_mm=50.0):
    """!
    @brief A one-layer plate (the copper layer is the whole plate), adiabatic top and sides, bottom coefficient h, one square source at the centre.
    @param t_mm Plate thickness in mm.
    @param k Plate conductivity in W/mK.
    @param power Power of the source in W.
    @param side_mm Side of the source in mm.
    @param h Bottom coefficient in W/m2K.
    @param w_mm Side of the plate in mm.
    @return Problem.
    """
    from pcbthermal.model import Materials
    p = Problem.new(w_mm, w_mm, layers=1, thickness_mm=1.0001 * t_mm, copper_um=t_mm * 1e3, ambient=25.0, h_top=1e-6, h_bottom=h, h_side=None, materials=Materials(k_copper=k))
    p.add_full_copper(layers=None)
    c = w_mm / 2
    p.add_heater(1, power, rect=(c - side_mm / 2, c - side_mm / 2, c + side_mm / 2, c + side_mm / 2), name="S")
    return p


def test_the_bound_adds_the_film_term_and_a_column_reaches_q_t_over_k():
    # A column fed over its whole top and leaving through the film: q'' t / (2 k) + q'' t / (2 k) = q'' t / k (case 2 plate, 70 W over 50 x 50 mm: 1.87 K, 3D measured 1.77 K)
    q = 70.0 / 0.05 ** 2
    assert thick_plate_bound(70.0, 0.05 ** 2, 10e-3, 150.0, film_flux=q) == pytest.approx(q * 10e-3 / 150.0)
    assert thick_plate_bound(70.0, 0.05 ** 2, 10e-3, 150.0, film_flux=q) == pytest.approx(2 * thick_plate_bound(70.0, 0.05 ** 2, 10e-3, 150.0))


def test_the_case_2_plate_fires_for_the_three_larger_sources_and_has_no_film_clause():
    # Muzychka, Culham and Yovanovich (2003) case 2: the layered models read 2.0 to 4.6 K below the surface since the film passes the half plate (they read 2.9 to 5.5 K
    # before: 0.84 K of it the film, the rest through the thickness); the bound is the through-thickness term alone, so the source of 10 W (3.3 K, 4.7 % of its rise) stays silent
    from pcbthermal.model import Materials
    p = Problem.new(50, 50, layers=1, thickness_mm=10.001, copper_um=10000.0, ambient=25.0, h_top=1e-6, h_bottom=400.0, h_side=None, materials=Materials(k_copper=150.0))
    p.add_full_copper(layers=None)
    for i, (c, pw) in enumerate(zip([(12.5, 12.5), (37.5, 12.5), (12.5, 37.5), (37.5, 37.5)], [10.0, 25.0, 20.0, 15.0])):
        p.add_heater(1, pw, rect=(c[0] - 5, c[1] - 5, c[0] + 5, c[1] + 5), name=f"S{i + 1}")
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0))
    w = thick(sim)
    assert len(w) == 3 and all("from the face film" not in x and "through the thickness" in x for x in w)
    gaps = [4.59, 3.72, 2.87]                             # K, printed centroid minus the FVM of the three warned sources (S2, S3, S4; 2.01 K for the silent S1)
    for x, g in zip(w, gaps):
        assert bound_in(x) >= g


def test_a_thin_copper_board_does_not_fire_and_a_stiff_plate_has_no_film_term():
    assert thick(simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=2.0))) == []
    # 35 um of copper, and a plate of k 385 and 1 mm: the through-thickness bound stays under the limit
    p = plate(1.0, 385.0, 20.0)
    assert thick(simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))) == []


@pytest.mark.parametrize("t_mm, k, power", [(5.0, 50.0, 20.0), (10.0, 150.0, 40.0), (20.0, 385.0, 60.0)])
def test_the_number_in_the_text_is_the_closed_form(t_mm, k, power):
    # The bound quoted equals 0.5 q'' t / k with q'' = P / A of the footprint (the ambient film passes the half plate in the model since fix/face-film-half-slab)
    p = plate(t_mm, k, power)
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    rise = sim.heater_rows()[0]["t_max"] - p.board.ambient
    q = power / 1e-4
    expected = 0.5 * q * t_mm * 1e-3 / k
    w = thick(sim)
    if expected > THICK_PLATE_LIMIT * rise:
        assert len(w) == 1 and bound_in(w[0]) == pytest.approx(expected, abs=0.051)
        assert "from the face film" not in w[0]
    else:
        assert w == []


@pytest.mark.parametrize("side, power, measured", [(20.0, 50.0, 17.9), (40.0, 100.0, 14.9)])
def test_two_thick_plates_quote_the_face_towards_the_laminate(side, power, measured):
    # Review of the bound: two 3 mm plates of k 20 joined by 0.05 mm of k 3, a 20 x 20 mm source of 50 W on top, h 400 below. The heat leaves the copper of the
    # part through its face towards the laminate, and the vertical links of the layered models start at the node, so the half plate on that side is missing as
    # well, and the second plate (one node too) loses its whole drop. An independent 3D solver (tests/helpers/layered3d.py, 4 sub-slabs per layer, 0.5 mm cells)
    # reads the surface 17.9 K (20 mm source, 50 W) and 14.9 K (40 mm, 100 W) above the FVM; the first version of this bound quoted 9.4 and 4.7 K (through the
    # thickness only) and called it a bound, and the 40 mm source did not warn at all
    from pcbthermal.model import Materials
    m = Materials(k_copper=20.0, k_fr4_through=3.0, k_fr4_inplane=3.0)
    p = Problem.new(50, 50, layers=2, thickness_mm=6.05, copper_um=3000.0, ambient=25.0, h_top=1e-6, h_bottom=400.0, h_side=None, materials=m)
    p.add_full_copper(layers=None)
    p.add_heater(1, power, rect=(25 - side / 2, 25 - side / 2, 25 + side / 2, 25 + side / 2), name="S")
    w = thick(simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)))
    assert len(w) == 1 and "where the heat leaves the copper" in w[0] and "across the other copper layers" in w[0]
    assert bound_in(w[0]) >= measured


def test_computed_coefficients_leave_no_film_term_in_the_bound():
    # A 10 mm plate of k 20 with computed coefficients (natural convection and radiation, about 10 W/m2K a face): the film passes the half plate inside the model (with the
    # coefficients of the solve), so the bound is the through-thickness term alone
    p = plate(10.0, 20.0, 5.0)
    p.board.h_mode = "computed"
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    ex = sim.reference.extras
    rise = sim.heater_rows()[0]["t_max"] - p.board.ambient
    q = 5.0 / 1e-4
    assert ex["h_top"] + ex["h_bottom"] > 0 and rise > 0
    w = thick(sim)
    assert len(w) == 1 and "from the face film" not in w[0]
    assert bound_in(w[0]) == pytest.approx(0.5 * q * 10e-3 / 20.0, abs=0.051)


def test_the_short_title_of_the_warning_says_what_it_is():
    # The closed row of the warning box shows the first clause: it must carry 'thick and poorly conducting', not stop at the parenthesis of the dimensions
    from pcbthermal.checks import warning_title
    w = thick(simulate(plate(10.0, 20.0, 5.0), SolverOptions(models=("fvm",), cell_mm=2.0)))
    assert len(w) == 1 and "thick and poorly conducting" in warning_title(w[0])
