#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_warning_severity.py
@brief Every warning carries an explicit severity, "alert" or "note", set where it is created; the word list is only the fallback of plain strings.
@details The examples of the maintainer, the explicit field against the word list, the survival of the field through the process boundary (pickle) and a
         sweep over the example projects and the 17 boards of the frozen-number harness (input checks and the warnings of a coarse run).
"""

import pickle
import sys
from pathlib import Path

import pytest

from pcbthermal import Problem, SolverOptions, checks, simulate

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests" / "regression"))
import regress_boards as rb  # noqa: E402  (the harness boards, a path of this test folder)

ALL_MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")


def test_the_two_examples_of_the_maintainer():
    """!
    @brief 'the whole footprint is outside the board' is an alert; '9 vias under the footprint' (a note that quotes 'too hot') is a note.
    """
    p = Problem.new(20, 20, 2)
    p.add_heater(1, 1.0, rect=(30, 30, 34, 34), name="U1")
    out = [w for w in checks.check_input(p, ("fvm",), 1.0) if "outside the board" in w]
    assert out and all(checks.warning_severity(w) == "alert" for w in out)
    p = Problem.new(30, 30, 2)
    p.add_heater(1, 1.0, rect=(12, 12, 18, 18), name="U1")
    for x in (13.5, 15.0, 16.5):
        for y in (13.5, 15.0, 16.5):
            p.add_via(x, y)
    vias = [w for w in checks.check_input(p, ("lumped",), 1.0) if "9 vias under the footprint" in w]
    assert vias and all(w.severity == "note" and checks.warning_severity(w) == "note" for w in vias)


def test_an_explicit_severity_wins_over_the_words_and_plain_strings_fall_back():
    """!
    @brief The field decides; a string without one is classified by its words; an unknown severity is refused.
    """
    assert checks.warning_severity(checks.warn("the part is too hot and the model cannot run", "note")) == "note"
    assert checks.warning_severity(checks.warn("a quiet text", "alert")) == "alert"
    assert checks.warning_severity("it will not run") == "alert" and checks.warning_severity("just a remark") == "note"
    with pytest.raises(ValueError):
        checks.warn("x", "high")


def test_the_fallback_of_a_plain_model_string_follows_the_definition_of_an_alert():
    """!
    @brief The warnings of the models are plain strings: a measured error ('9 % too hot', 'the unsafe side') stays a note, a failure is an alert.
    @details Review: the first word list turned the Analytic copper-spread note and the imported-copper coarse-cell notes into alerts in the Results Summary.
    """
    from pcbthermal import copper
    note = ("copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of each layer into one uniform sheet and has no copper "
            "edge; on a part over a copper pad or a window it was measured between 76 % too cool and 9 % too hot against a resolved 3D solution")
    assert checks.warning_severity(note) == "note"
    assert checks.warning_severity(copper.COARSE_CELL_WARNING) == "note" and checks.warning_severity(copper.SCREENING_WARNING) == "note"
    for failure in ("SOR did not converge in 5000 sweeps (residual 1.00E-3)", "the 3D solid was not run: too large",
                    "the per-layer edge iteration of the Analytic model did not reach its tolerance in 30 products"):
        assert checks.warning_severity(failure) == "alert", failure


def test_the_severity_survives_the_process_boundary():
    """!
    @brief The calculation process sends results by pickle; the field must come back.
    """
    w = checks.warn("text", "alert", "heater", 2, "short")
    back = pickle.loads(pickle.dumps(w))
    assert str(back) == "text" and back.severity == "alert" and back.kind == "heater" and back.index == 2 and back.short == "short"


def test_the_profile_error_of_a_run_is_an_alert():
    """!
    @brief A time simulation that was not run is an alert in the Summary list.
    """
    p = Problem.new(30, 30, 2)
    p.add_heater(1, 1.0, rect=(12, 12, 18, 18), name="U1")
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    sim.profile_error = "bad table"
    got = [w for w in sim.warnings if "time simulation not run" in w]
    assert got and got[0].severity == "alert"


@pytest.mark.parametrize("name", rb.board_names())
def test_every_warning_of_the_examples_and_harness_boards_has_a_severity(name):
    """!
    @brief The input checks and the warnings of a coarse run of every example and harness board carry an explicit severity.
    @param name Board name of the harness.
    """
    p = rb.build(name, REPO / "examples")
    warnings = list(checks.check_input(p, ALL_MODELS, 1.0))
    sim = simulate(p, SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=2.0))
    warnings += sim.warnings
    for w in warnings:
        assert getattr(w, "severity", None) in (checks.ALERT, checks.NOTE), f"{name}: no explicit severity on: {str(w)[:90]}"
