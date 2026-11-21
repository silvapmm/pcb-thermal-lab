#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_campaign_warnings.py
@brief The three warnings that the closing review of the FEM comparison campaign asked for (texts only): the LPTN on a part over a copper window, the FEM on a profile stretch
       shorter than its gap mesh follows, and the bare corner of a footprint (FVM, FDM, 3D solid, FEM). They fire on the boards of the campaign, stay silent where the campaign
       measured no problem, and move no temperature of any model (the checks are switched off and every field is compared bit for bit).
"""
import ast
import copy
import re
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "regression"))
import regress_boards as B                                                  # noqa: E402
from pcbthermal import Problem, SolverOptions, SquareWave, TableProfile, checks, simulate   # noqa: E402

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
    assert "11.4 and 6.7 %" in ws[0] and "below on all of them" in ws[0]              # the direction and the measured sizes (validation 56.1)
    assert "within about 2 %" in ws[0]                                                # the criterion is broad, and the text says so
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


def pulse_plate(stretch, layers=2):
    """!
    @brief The plate of study_fem_profile_limit.py: a one-shot pulse (0 W, 10 W, 0 W, each for the stretch) on a 10 mm part over full copper.
    @param stretch Length of each stretch in s.
    @param layers Copper layers.
    @return Problem.
    """
    p = Problem.new(60.0, 40.0, layers=layers)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(25.0, 15.0, 35.0, 25.0), name="U")
    p.heaters[0].set_profile(TableProfile(times=[0.0, stretch, 2 * stretch, 3 * stretch], powers=[0.0, 10.0, 0.0], repeat=False))
    return p


def test_fem_profile_note_on_a_one_shot_pulse_the_fem_steps():
    p = pulse_plate(0.05)
    limit, first = checks.fem_profile_limit(p)
    assert 0.3 < limit < 0.4 and 170e-6 < first < 180e-6                              # 2 (175 um)^2 / alpha, docs/theory.md 4b
    ws = texts(p, ("fem",), key="power profile has a stretch")
    assert len(ws) == 1 and "one-shot" in ws[0] and "6 elements across a gap" in ws[0] and "lower estimate" in ws[0]
    assert "0.6 and 1.0 %" in ws[0] and "2.6 to 5.5 %" in ws[0] and "22 %" in ws[0]   # study_fem_profile_limit.py and validation 57.2
    assert texts(p, ("fvm", "fdm", "lumped", "analytic", "solid3d"), key="power profile has a stretch") == []   # the other models have their own fast-wave warnings
    assert texts(pulse_plate(0.5), ("fem",), key="power profile has a stretch") == []                          # above the limit


def test_fem_profile_note_is_silent_on_a_fast_wave_over_copper_which_gets_the_closed_form():
    # review: the 20 Hz wave of validation 57.2 is given the closed-form ripple by profiles.decide in a normal run (REGIME_RIPPLE), never stepped by the FEM,
    # so a note that its FEM swing reads low would be false; the same for the 100 Hz part of the profile example
    assert texts(plate_wave(20.0), ("fem",), key="power profile has a stretch") == []
    assert texts(board("profile_board"), ("fem",), key="power profile has a stretch") == []


def test_fem_profile_note_on_a_wave_over_bare_laminate_which_has_no_closed_form():
    p = Problem.new(60.0, 40.0, layers=2)
    p.add_zone(2, rect=(0.0, 0.0, 60.0, 40.0))                                      # copper only on the bottom: the part sits on bare laminate
    p.add_heater(1, 1.0, rect=(25.0, 15.0, 35.0, 25.0), name="U")
    p.heaters[0].set_profile(SquareWave(p_on=10.0, period=0.5, duty=0.3))
    ws = texts(p, ("fem",), key="power profile has a stretch")
    assert len(ws) == 1 and "over the oscillation threshold" in ws[0]


def test_fem_profile_note_reads_the_chosen_gap_elements():
    p = pulse_plate(0.15)                                                           # 0.44 times the limit of 6 elements, about 6 times that of 12 (0.024 s)
    assert len(texts(p, ("fem",), key="power profile has a stretch")) == 1
    assert checks.check_input(p, ("fem",), 1.0, fem_gap_elements=12) == [w for w in checks.check_input(p, ("fem",), 1.0, fem_gap_elements=12)
                                                                          if "power profile has a stretch" not in w]
    ws = [w for w in checks.check_input(pulse_plate(0.01), ("fem",), 1.0, fem_gap_elements=12) if "power profile has a stretch" in w]
    assert len(ws) == 1 and "12 elements across a gap" in ws[0]


def test_fem_profile_note_is_silent_for_a_slow_wave_and_for_no_swing():
    assert texts(plate_wave(0.1, 0.5), ("fem",), key="power profile has a stretch") == []   # 5 s stretches, far above 0.34 s
    p = pulse_plate(0.05)
    p.heaters[0].set_profile(TableProfile(times=[0.0, 0.05, 0.1], powers=[5.0, 5.0], repeat=False))
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
    assert "9 % of the footprint" in w and "FVM, FDM, 3D solid, FEM (measured on one board)" in w
    assert "105.2 K" in w and "-39 / -20 / -9 %" in w and "-41 / +8 / -4 %" in w          # the FEM and the 3D solid rows of validation 56.1.2
    # only the models that run are named
    only = texts(board("drawn_ell"), ("fvm", "fem"), key="of the footprint is on bare laminate")
    assert "with the cell in FVM, FEM (measured" in only[0]
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


# ---------------------------------------------------------------- one source for the trust numbers

def _summary_rows():
    """!
    @brief The rows 'without the drawn and the pad boards' (peak) of the summary table of docs/validation.md 56.1, the printed output of study_compare_c1.py.
    @return Dict (cell mm as text, model) -> (mean, largest) in %.
    """
    text = (HERE.parent / "docs" / "validation.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| without the drawn and the pad boards \| (1|0\.5) \| (FVM|FDM|3D solid) \| peak \| \d+ \| ([\d.]+) \| ([\d.]+) \(", text, re.M)
    return {(c, m): (float(a), float(b)) for c, m, a, b in rows}


def _model_tooltips():
    """!
    @brief The tooltip texts of the Models box, read from the source of gui/panels.py (the string constants of the dict 'tips'), without a window.
    @return Dict model key -> text.
    """
    tree = ast.parse((HERE.parent / "pcbthermal" / "gui" / "panels.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "tips" for t in node.targets) and isinstance(node.value, ast.Dict):
            keys = [k.value for k in node.value.keys]
            if "fvm" in keys and "solid3d" in keys:
                return {k: "".join(c.value for c in ast.walk(v) if isinstance(c, ast.Constant) and isinstance(c.value, str)) for k, v in zip(keys, node.value.values)}
    raise AssertionError("the tooltips of the Models box were not found")


def test_the_trust_numbers_of_the_tooltips_guide_and_manual_are_those_of_validation_56_1():
    rows = _summary_rows()
    assert len(rows) == 6
    tips = _model_tooltips()
    guide = (HERE.parent / "pcbthermal" / "help" / "index.html").read_text(encoding="utf-8")
    manual = (HERE.parent / "docs" / "USER_MANUAL.md").read_text(encoding="utf-8")
    for key, model in (("fvm", "FVM"), ("fdm", "FDM"), ("solid3d", "3D solid")):
        m1, l1 = rows[("1", model)]
        m5, l5 = rows[("0.5", model)]
        assert f"{m1:.2f} % mean, {l1:.1f} % largest" in tips[key], model
        assert f"{m5:.2f} and {l5:.2f} % at 0.5 mm" in tips[key], model
        assert f"| {model} | {m1:.2f}, {l1:.1f} % " in manual and f"| {m5:.2f}, {l5:.2f} % |" in manual, model
    order = ("FVM", "FDM", "3D solid")
    assert ("within " + ", ".join(f"{rows[('1', m)][1]:.1f}" for m in order[:2]) + f" and {rows[('1', order[2])][1]:.1f} % at a 1 mm cell") in guide
    assert ("(means of the magnitudes " + ", ".join(f"{rows[('1', m)][0]:.2f}" for m in order[:2]) + f" and {rows[('1', order[2])][0]:.2f} %)") in guide
    assert ("within " + ", ".join(f"{rows[('0.5', m)][1]:.2f}" for m in order[:2]) + f" and {rows[('0.5', order[2])][1]:.2f} % at 0.5 mm") in guide
