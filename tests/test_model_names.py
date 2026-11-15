#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_model_names.py
@brief One name per model: every label of the window (Models box, Animation combo, cards, Temperature combo, Summary table, plot legends) comes from the two tables of results.py.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from pcbthermal import results
from pcbthermal.examples import example_board
from pcbthermal.gui import fieldscale
from tests.test_gui_stress import load, popups, run, win  # noqa: F401  (fixtures)

KEYS = ("fvm", "lumped", "analytic", "fdm", "solid3d", "fem")
BANNED = ("Lumped", "lumped")


def test_the_two_tables_cover_every_model_and_no_variant_survives():
    """!
    @brief Short and full names exist for every key; the cards use the short table; the short name is contained in the full name where it is a word of it.
    """
    assert set(results.MODEL_LABELS) == set(results.MODEL_FULL) == set(KEYS)
    assert fieldscale.MODEL_SHORT == results.MODEL_LABELS
    for k in KEYS:
        assert not any(b in results.MODEL_LABELS[k] + results.MODEL_FULL[k] for b in BANNED)
    assert results.MODEL_LABELS["lumped"] == "LPTN" and results.MODEL_FULL["lumped"] == "Thermal network (LPTN)"


def test_the_panel_the_animation_and_the_result_lists_use_the_tables(win, qtbot):
    """!
    @brief The Models box, the Animation combo and the Temperature combo carry the table names (the FVM adds ', reference' in the box).
    @param win Main window fixture.
    @param qtbot Fixture.
    """
    load(win, example_board())
    for k, box in win.solver_panel.cb.items():
        assert box.text() == results.MODEL_FULL[k] + (", reference" if k == "fvm" else "")
    anim = win.results.animation.model
    assert [anim.itemText(i) for i in range(anim.count())] == [results.MODEL_FULL[k] for k in ("fvm", "fdm", "analytic")]
    run(win, qtbot, ("fvm", "lumped", "analytic"), cell=2.0)
    combo = win.results.temp.model
    assert [combo.itemText(i) for i in range(combo.count())] == [results.MODEL_LABELS[combo.itemData(i)] for i in range(combo.count())]
    assert "LPTN" in [combo.itemText(i) for i in range(combo.count())]
