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
    assert len(w) == 1 and "U1" in w[0] and "B (" in w[0] and "not added to the results" in w[0] and "footprint" not in w[0]
    effect = gradient_effect_3d(p)
    assert 0.0 < effect < bound_in(w[0])                                      # A bound, and an honest one: the 3D solid sees part of it
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
