#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_blocks.py
@brief Metal blocks (heatsinks with a thickness): the extra layer of the FVM and FDM networks, the contact over the copper overlap, results.
"""

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, analysis, blocks, check_problem, fdm, fvm, simulate
from pcbthermal.model import problem_from_dict, problem_to_dict


def board(block=True, pad=(35, 25, 65, 55), rect=(20, 10, 80, 70), h_extra=0.0, thickness=3.0, **kw):
    """!
    @brief 100 x 80 mm, 2 layers, 5 W on the top, a copper pad on the bottom and optionally a metal block larger than the pad under it.
    @param block True to add the block.
    @param pad Bottom copper rectangle in mm.
    @param rect Block rectangle in mm.
    @param h_extra Extra coefficient of the block in W/m2K.
    @param thickness Block thickness in mm.
    @param kw Further arguments of Problem.add_heatsink.
    @return Problem.
    """
    p = Problem.new(100, 80, 2).add_zone(1, rect=(0, 0, 100, 80))
    if pad:
        p.add_zone(2, rect=pad)
    p.add_heater(1, 5.0, rect=(45, 35, 55, 45))
    if block:
        p.add_heatsink(2, h_extra, rect=rect, thickness_mm=thickness, **kw)
    return p


def test_json_roundtrip_and_old_heatsinks_unchanged():
    p = board(name="Al", contact_r=1e-3, k=385.0)
    q = problem_from_dict(problem_to_dict(p))
    s = q.heatsinks[0]
    assert s.is_block() and s.thickness == pytest.approx(0.003) and s.k == 385.0 and s.contact_r == pytest.approx(1e-3)
    plain = Problem.new(50, 40, 2).add_heatsink(1, 10.0, rect=(5, 5, 15, 15))
    d = problem_to_dict(plain)["heatsinks"][0]
    assert "thickness_mm" not in d and not problem_from_dict(problem_to_dict(plain)).heatsinks[0].is_block()
    with pytest.raises(ValueError):
        board(thickness=-1.0).validate()


def test_energy_balance_closes_with_the_block_and_the_models_agree():
    p = board()
    r, d = fvm.solve_steady(p, 1.0), fdm.solve_steady(p, 1.0)
    for res in (r, d):
        assert abs(res.balance_error) < 1e-9 and "blocks" in res.power_out
        assert res.extras["block_bottom_w_to_block"] == pytest.approx(res.power_out["blocks"], rel=1e-6)   # What enters leaves
    assert d.t_max == pytest.approx(r.t_max, abs=1.0)
    rows = analysis.block_stats(r, p)
    assert len(rows) == 1 and rows[0]["face"] == "bottom" and rows[0]["t_max"] < r.t_max


def test_a_block_cools_and_a_better_contact_cools_more():
    bare = fvm.solve_steady(board(False), 1.0).t_max
    pad_5 = fvm.solve_steady(board(contact_r=5e-4), 1.0).t_max
    pad_20 = fvm.solve_steady(board(contact_r=2e-3), 1.0).t_max
    good = fvm.solve_steady(board(contact_r=5e-5), 1.0).t_max
    assert bare > pad_20 > pad_5 > good                       # More contact conductance, cooler board
    finned = fvm.solve_steady(board(h_extra=60.0), 1.0).t_max
    assert finned < pad_5                                      # A finned block (extra h) cools more


def test_the_contact_is_the_intersection_of_block_and_copper():
    # Same block, copper pad of half the size: the heat entering the block through the copper falls
    small = fvm.solve_steady(board(pad=(40, 30, 60, 50)), 1.0)
    large = fvm.solve_steady(board(pad=(25, 15, 75, 65)), 1.0)
    assert large.extras["block_bottom_w_to_block"] > small.extras["block_bottom_w_to_block"] > 0
    # No copper under the block: only the bare laminate conducts (through half a layer of FR-4 in series with the pad): over a larger area
    # this is of the same order as a small copper pad, and well below a large one
    none = fvm.solve_steady(board(pad=None), 1.0)
    assert none.extras["block_bottom_w_to_block"] < large.extras["block_bottom_w_to_block"]
    assert none.extras["block_bottom_w_to_block"] < 1.1 * small.extras["block_bottom_w_to_block"]
    net = fvm.Network(board(), 100, 80)
    link = net.extra_links[0][2]
    area_cell = net.dx * net.dy
    # Over the 30 x 30 mm pad the link is A / R'' (copper), outside it much smaller (laminate in series)
    assert link[40, 50] == pytest.approx(area_cell / 5e-4, rel=1e-6)
    assert 0 < link[10, 25] < 0.3 * link[40, 50]
    assert link[2, 2] == 0.0                                  # Outside the block: no link


def test_a_thick_conductive_block_is_isothermal_and_a_thin_one_is_not():
    thick = fvm.solve_steady(board(thickness=10.0, k=385.0), 1.0)
    spread = thick.extras["block_bottom_max"] - thick.extras["block_bottom_mean"]
    thin = fvm.solve_steady(board(thickness=0.3, k=50.0), 1.0)
    spread_thin = thin.extras["block_bottom_max"] - thin.extras["block_bottom_mean"]
    assert spread < 1.0 and spread_thin > spread


def test_transient_includes_the_mass_of_the_block():
    p = board(thickness=10.0, k=205.0)
    with_block = fvm.solve_transient(p, 600.0, n_out=20, cell_mm=4.0)
    without = fvm.solve_transient(board(False), 600.0, n_out=20, cell_mm=4.0)
    assert with_block.frames.shape[1] == 2                      # The block layer is not in the frames
    assert with_block.t_max[-1] < without.t_max[-1]            # More mass and more cooling: cooler at the same time
    assert with_block.t_mean[-1] == pytest.approx(float(with_block.frames[-1].mean()), rel=1e-9)
    assert with_block.steady_t_max < without.steady_t_max      # The steady state is cooler too (the 63 % time is of a lower rise)
    d = fdm.solve_transient(p, 120.0, n_out=10, cell_mm=4.0)
    assert d.frames.shape[1] == 2 and d.t_max[-1] > 25.0


def test_lumped_and_analytic_run_with_a_block_in_steady_state():
    p = board()
    sim = simulate(p, SolverOptions(models=("fvm", "fdm", "lumped", "analytic"), cell_mm=2.0))
    assert list(sim.results) == ["fvm", "fdm", "lumped", "analytic"]
    assert "Metal block" in sim.report()
    rise = sim.results["fvm"].t_max - 25.0
    for m in ("lumped", "analytic"):                                            # Block layer in the ring network / tile graph: within 6 % of the FVM
        assert abs(sim.results[m].t_max - sim.results["fvm"].t_max) < 0.06 * rise, m
    from pcbthermal import analytic, lumped
    for module in (lumped,):                                                    # Their transients still refuse a block
        with pytest.raises(ValueError, match="metal block"):
            module.step_responses(p, cell_mm=2.0)
    assert blocks.require_no_blocks(board(False)).heatsinks == board(False).heatsinks
    with pytest.raises(ValueError, match="metal block"):
        blocks.require_no_blocks(p)


def test_checks_warn_about_a_block_without_copper_and_sor_refuses():
    assert any("does not overlap any copper" in w for w in check_problem(board(pad=None), 1.0))
    assert any("perfect contact" in w for w in check_problem(board(contact_r=1e-6), 1.0))
    assert not any("block" in w for w in check_problem(board(), 1.0))
    with pytest.raises(ValueError, match="SOR"):
        fvm.solve_steady(board(), 2.0, method="sor")
    assert fvm.solve_steady(board(), 2.0, method="cg").t_max == pytest.approx(fvm.solve_steady(board(), 2.0).t_max, abs=1e-6)


def test_profile_time_simulation_with_a_block():
    from pcbthermal import SquareWave
    p = board()
    p.heaters[0].set_profile(SquareWave(10.0, 20.0, 0.5))
    sim = simulate(p, SolverOptions(models=("fvm", "fdm"), cell_mm=4.0))
    f = sim.profile_results["fvm"]
    assert f.resolved and f.frames.shape[1] == 2 and f.peak_map.shape[0] == 2
    assert f.peak > f.minimum and f.steady_peak_max > f.steady_average_max


def test_presets_of_metals_and_interfaces():
    from pcbthermal.model import INTERFACES, METALS, Heatsink
    names = [m[0] for m in METALS]
    assert names[:2] == ["Aluminium", "Copper"] and all(k > 0 and c > 1e6 for _, k, c in METALS)
    assert (METALS[0][1], METALS[0][2]) == (Heatsink.__dataclass_fields__["k"].default, Heatsink.__dataclass_fields__["rho_cp"].default)
    r = [t * 1e-3 / k * 1e4 for _, k, t in INTERFACES]                  # K cm2/W
    assert r == sorted(r) and 0.3 < r[0] < 0.4 and 5.0 < r[-1] < 15.0   # From grease to a hard gap pad
    # A worse interface heats the board more, a better metal cools it a little more
    base = fvm.solve_steady(board(contact_r=INTERFACES[0][2] * 1e-3 / INTERFACES[0][1]), 2.0).t_max
    worst = fvm.solve_steady(board(contact_r=INTERFACES[-1][2] * 1e-3 / INTERFACES[-1][1]), 2.0).t_max
    assert worst > base
    steel = fvm.solve_steady(board(k=METALS[3][1], rho_cp=METALS[3][2]), 2.0).t_max
    copper = fvm.solve_steady(board(k=METALS[1][1], rho_cp=METALS[1][2]), 2.0).t_max
    assert steel > copper
