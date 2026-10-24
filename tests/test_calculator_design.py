"""!
@file test_calculator_design.py
@brief The design-uncertainty terms of the power calculator band: zero term identical to the old band, root-sum-square combination, levels in the defaults, Preferences round trip.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from pcbthermal import Problem, SolverOptions, defaults, simulate
from pcbthermal.inverse import DESIGN_LEVELS, design_amounts, power_band


def board4(power=2.0):
    """!
    @brief A four-layer board with a part, copper on the top, one inner plane (layer 2) and the bottom, vias under the part.
    @param power Power of the part in W.
    @return Problem.
    """
    p = Problem.new(60, 60, 4)
    p.add_zone(1, rect=(5, 5, 55, 55))
    p.add_zone(2, rect=(5, 5, 55, 55))
    p.add_zone(4, rect=(5, 5, 55, 55))
    p.add_heater(1, power, rect=(27, 27, 33, 33), name="Q1", theta=4.0)
    for x in (28.0, 30.0, 32.0):
        p.add_via(x, 30.0, 0.3)
    return p


def reading(problem):
    """!
    @brief The board-ring temperature the model gives for the part.
    @param problem Problem.
    @return Temperature in degC.
    """
    return simulate(problem, SolverOptions(models=("fvm",), cell_mm=1.5)).heater_rows()[0]["t_ring"]


def test_levels_and_amplitudes_come_from_the_defaults():
    d = defaults.load()["calculator"]
    assert d["design_level"] in DESIGN_LEVELS
    assert design_amounts({**d, "design_level": "none"}) == {"coverage": 0.0, "weight": 0.0, "planes": 0.0, "vias": 0.0}
    hand, cad, est = (design_amounts({**d, "design_level": k}) for k in ("hand", "cad", "estimated"))
    # The levels are ordered, and "estimated" is the amplitude of the defaults itself
    assert all(cad[k] < hand[k] < est[k] for k in est)
    assert est["coverage"] == pytest.approx(d["design_coverage_pct"] / 100.0 * d["design_scale_estimated"])
    with pytest.raises(ValueError, match="design level"):
        design_amounts({**d, "design_level": "guess"})


def test_zero_design_term_is_the_old_band_bit_for_bit_and_the_terms_add_in_quadrature():
    prob = board4()
    t = reading(prob)
    none = power_band(prob, 0, t, point="ring", cell_mm=1.5, uncertainty={"design_level": "none"})
    zero = power_band(prob, 0, t, point="ring", cell_mm=1.5, uncertainty={"design_level": "hand", "design_scale_hand": 0.0})
    assert [c["factor"] for c in none["contributions"]] == ["copper", "heat transfer", "reading"]
    assert (zero["best_w"], zero["worst_w"]) == (none["best_w"], none["worst_w"])           # Exactly equal, not approximately
    hand = power_band(prob, 0, t, point="ring", cell_mm=1.5, uncertainty={"design_level": "hand"})
    names = [c["factor"] for c in hand["contributions"] if c["design"]]
    assert names == ["design: copper coverage", "design: copper weight", "design: inner planes", "design: vias"]
    assert [c["factor"] for c in hand["contributions"] if not c["design"]] == ["copper", "heat transfer", "reading"]
    down = sum((hand["power_w"] - c["low_w"]) ** 2 for c in hand["contributions"]) ** 0.5
    up = sum((c["high_w"] - hand["power_w"]) ** 2 for c in hand["contributions"]) ** 0.5
    assert hand["best_w"] == pytest.approx(hand["power_w"] - down) and hand["worst_w"] == pytest.approx(hand["power_w"] + up)
    assert hand["best_w"] < none["best_w"] and hand["worst_w"] > none["worst_w"]                 # The extra terms only widen the band
    for c in hand["contributions"]:
        assert c["low_w"] <= hand["power_w"] + 1e-9 <= c["high_w"] + 2e-9
    # A wider level gives a wider band
    est = power_band(prob, 0, t, point="ring", cell_mm=1.5, uncertainty={"design_level": "estimated"})
    assert est["worst_w"] - est["best_w"] > hand["worst_w"] - hand["best_w"]


def test_coverage_moves_only_the_outer_layers_and_planes_only_the_inner_ones():
    import copy
    from pcbthermal.inverse import _design_coverage, _design_planes
    p = board4()
    p.zones[0].fill = 0.5
    down, up = copy.deepcopy(p), copy.deepcopy(p)
    _design_coverage(down, 0.8)
    _design_coverage(up, 1.2)
    # Outer layers move (and a solid pour cannot be more than solid); the inner plane belongs to the planes term, so the same doubt is not counted twice
    assert [z.fill for z in down.zones] == pytest.approx([0.4, 1.0, 0.8])
    assert [z.fill for z in up.zones] == pytest.approx([0.6, 1.0, 1.0])
    _design_planes(down, 0.25, -1.0)
    assert [z.fill for z in down.zones] == pytest.approx([0.4, 0.75, 0.8])
    # An inner layer without a zone gets a board-sized plane at the fill of the amplitude on the "up" side only
    _design_planes(up, 0.25, 1.0)
    added = [z for z in up.zones if z.name == "undrawn plane"]
    assert [(z.layer, z.fill) for z in added] == [(2, 0.25)]


def test_terms_without_anything_to_change_are_left_out():
    p = Problem.new(60, 60, 2)
    p.add_zone(1, rect=(5, 5, 55, 55))
    p.add_zone(2, rect=(5, 5, 55, 55))
    p.add_heater(1, 2.0, rect=(27, 27, 33, 33), name="Q1")
    out = power_band(p, 0, reading(p), point="ring", cell_mm=1.5, uncertainty={"design_level": "estimated"})
    names = [c["factor"] for c in out["contributions"]]
    assert "design: vias" not in names and "design: inner planes" not in names           # No vias, no inner layers
    assert "design: copper coverage" in names and "design: copper weight" in names


def test_a_plane_that_was_not_drawn_raises_the_worst_case():
    p = board4()
    p.zones = [z for z in p.zones if z.layer != 1]                              # Drawn without the inner plane
    out = power_band(p, 0, reading(p), point="ring", cell_mm=1.5, uncertainty={"design_level": "estimated"})
    planes = next(c for c in out["contributions"] if c["factor"] == "design: inner planes")
    assert planes["high_w"] > out["power_w"]                                           # A plane may exist although it is not drawn: more copper, more watts


def test_the_design_level_survives_the_user_file():
    full = defaults.load()
    full["calculator"]["design_level"] = "estimated"
    full["calculator"]["design_planes_pct"] = 70.0
    defaults.save_user(full)
    assert defaults.value("calculator", "design_level") == "estimated" and defaults.value("calculator", "design_planes_pct") == 70.0
    assert defaults.diff(full)["calculator"] == {"design_level": "estimated", "design_planes_pct": 70.0}       # Only the differences go to the user file
    out = power_band(board4(), 0, 60.0, point="ring", cell_mm=1.5)
    assert out["uncertainty"]["design_level"] == "estimated" and out["uncertainty"]["design_planes_pct"] == 70.0
