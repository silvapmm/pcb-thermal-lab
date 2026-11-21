#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_campaign_warnings.py
@brief The three warnings that the closing review of the FEM comparison campaign asked for (texts only): the LPTN on a part over a copper window, the FEM on a profile stretch
       shorter than its gap mesh follows, and the bare corner of a footprint (FVM, FDM, 3D solid, FEM). They fire on the boards of the campaign, stay silent where the campaign
       measured no problem, and move no temperature of any model (the checks are switched off and every field is compared bit for bit).
"""
import copy
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "regression"))
import regress_boards as B                                                  # noqa: E402
from pcbthermal import SolverOptions, SquareWave, checks, simulate         # noqa: E402

EXAMPLES = str(HERE.parent / "examples")
ALL = ("fvm", "fdm", "lumped", "analytic", "solid3d", "fem")


def board(name):
    """!
    @brief A board of the release harness.
    @param name Board name of regress_boards.
    @return Problem.
    """
    return B.build(name, EXAMPLES)


def texts(problem, models, cell_mm=1.0, key=""):
    """!
    @brief The live warnings of a problem that contain a phrase.
    @param problem A Problem.
    @param models Model keys.
    @param cell_mm Cell size in mm.
    @param key Phrase the text must contain.
    @return List of warnings.
    """
    return [w for w in checks.check_input(problem, models, cell_mm) if key in w]


# ---------------------------------------------------------------- the LPTN over a copper window

@pytest.mark.parametrize("name", ["plate_pad", "one_layer_pad"])
def test_lumped_warns_on_the_copper_window_boards_of_the_campaign(name):
    ws = texts(board(name), ("lumped",), key="copper coverage varies")
    assert len(ws) == 1 and "LPTN" in ws[0] and "Use the FVM" in ws[0]
    assert "11.4 and 6.7 %" in ws[0] and "never hotter" in ws[0]                      # the direction and the measured sizes (validation 56.1)
    assert "LPTN" in ws[0].short and "too cool" in ws[0].short


@pytest.mark.parametrize("name", ["plate_uniform", "one_layer_full", "reference_board", "example_board", "finned_block", "hatched_copper", "plate_vias"])
def test_lumped_copper_window_is_silent_where_the_copper_is_even(name):
    assert texts(board(name), ("lumped",), key="copper coverage varies") == []


def test_lumped_copper_window_only_when_the_lumped_runs_and_matches_the_analytic_criterion():
    p = board("plate_pad")
    assert texts(p, ("fvm", "fdm", "analytic"), key="copper coverage varies") == []   # the Analytic says it itself, after its run
    from pcbthermal import analytic
    spread = analytic._effective_sheet(p, 1.0)["copper_spread"]
    assert spread > analytic.COPPER_SPREAD_WARN                                      # the same number the Analytic compares with 0.25
    assert any("copper coverage varies" in w for w in analytic._effective_sheet(p, 1.0)["warnings"])


# ---------------------------------------------------------------- the FEM and a short stretch of a profile

def plate_wave(freq_hz, duty=0.3):
    """!
    @brief The 60 mm two-layer plate of the campaign with a square wave on its part.
    @param freq_hz Frequency in Hz.
    @param duty Duty cycle.
    @return Problem.
    """
    p = board("plate_uniform")
    p.heaters[0].set_profile(SquareWave(p_on=10.0, period=1.0 / freq_hz, duty=duty))
    return p


def test_fem_profile_note_on_the_20_hz_wave_of_the_campaign():
    p = plate_wave(20.0)
    limit, first = checks.fem_profile_limit(p)
    assert 0.3 < limit < 0.4 and 170e-6 < first < 180e-6                              # 2 (175 um)^2 / alpha, docs/theory.md 4b
    ws = texts(p, ("fem",), key="power profile has a stretch")
    assert len(ws) == 1 and "4.90 K" in ws[0] and "22 %" in ws[0] and "6.3 K" in ws[0] and "lower estimate" in ws[0]
    assert texts(p, ("fvm", "fdm", "lumped", "analytic", "solid3d"), key="power profile has a stretch") == []   # the other models have their own fast-wave warnings


def test_fem_profile_note_is_silent_for_a_slow_wave_and_for_no_swing():
    assert texts(plate_wave(0.1, 0.5), ("fem",), key="power profile has a stretch") == []   # 5 s stretches, far above 0.34 s
    p = board("plate_uniform")
    p.heaters[0].set_profile(SquareWave(p_on=5.0, p_off=5.0, period=0.05, duty=0.3))
    assert texts(p, ("fem",), key="power profile has a stretch") == []
    assert texts(board("plate_uniform"), ("fem",), key="power profile has a stretch") == []   # no profile


def test_fem_profile_limit_follows_the_gap_elements():
    p = board("plate_uniform")
    assert checks.fem_profile_limit(p, 12)[0] < checks.fem_profile_limit(p, 6)[0] / 2.0        # finer gap mesh, shorter stretch followed


# ---------------------------------------------------------------- the bare corner (the drawn L)

def test_bare_corner_warns_on_drawn_ell_naming_the_four_models_with_the_campaign_numbers():
    ws = texts(board("drawn_ell"), ALL, key="of the footprint is on bare laminate")
    assert len(ws) == 1
    w = ws[0]
    assert "9 % of the footprint" in w and "FVM, FDM, 3D solid, FEM" in w
    assert "105.2 K" in w and "-39 / -20 / -9 %" in w and "-41 / +8 / -4 %" in w          # the FEM and the 3D solid rows of validation 56.1.2
    # only the models that run are named
    only = texts(board("drawn_ell"), ("fvm", "fem"), key="of the footprint is on bare laminate")
    assert "converge in the cell in FVM, FEM." in only[0]
    assert texts(board("drawn_ell"), ("lumped", "analytic"), key="of the footprint is on bare laminate") == []


@pytest.mark.parametrize("name", ["plate_pad", "hatched_copper", "drawn_inset_square", "drawn_stripes_pad", "plate_uniform", "example_board", "two_layer_partial", "part_top_path"])
def test_bare_corner_is_silent_on_the_other_boards(name):
    assert texts(board(name), ALL, key="of the footprint is on bare laminate") == []


# ---------------------------------------------------------------- no number moves

@pytest.mark.parametrize("name,models", [("plate_pad", ("fvm", "fdm", "lumped", "analytic", "solid3d", "fem")), ("drawn_ell", ("fvm", "fdm", "lumped", "analytic", "solid3d", "fem")),
                                         ("one_layer_pad", ("fvm", "lumped", "analytic"))])
def test_no_temperature_moves_with_the_new_warnings_switched_off(monkeypatch, name, models):
    p = board(name)
    on = simulate(copy.deepcopy(p), SolverOptions(models=models, cell_mm=2.0))
    assert any("copper coverage varies" in w or "of the footprint is on bare laminate" in w for w in on.warnings)   # the warnings are there
    monkeypatch.setattr(checks, "check_lumped_copper_window", lambda *a, **k: [])
    monkeypatch.setattr(checks, "check_bare_corner", lambda *a, **k: [])
    monkeypatch.setattr(checks, "check_fem_profile", lambda *a, **k: [])
    off = simulate(copy.deepcopy(p), SolverOptions(models=models, cell_mm=2.0))
    assert len(off.warnings) < len(on.warnings)
    for m in models:
        assert on.results[m].t_max == off.results[m].t_max and np.array_equal(on.results[m].T, off.results[m].T), m
        assert on.results[m].power_out == off.results[m].power_out and on.power_used.get(m) == off.power_used.get(m)
