#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_reimport_different_board.py
@brief The re-import of a Gerber set that is ANOTHER board than the stored import, through the real MainWindow: the dialog offers and preselects a new project, no part is carried over
       by designator (no orphans, no removal list), hand-drawn elements stay, Continue is not the primary button, and the same-board cases are unchanged.
@details Uses the driver and the fixtures of `test_reimport_matrix.py`. The synthetic "other board" has the same designators as the first one (U1, Q1, D1) but no file name and no
         file content in common, which is what `ImportSession.same_board` calls a different board; the library case replaces the RP2040 by the oswlight board.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from tests.test_reimport_matrix import COPPER_EDIT, app, base, library, snapshot, variant  # noqa: F401  (fixtures)


def other_board(base, tmp_path):
    """!
    @brief A copy of the synthetic set that looks like ANOTHER board to the re-import (no file name and no content in common) but has the same designators.
    @param base Folder of the original set.
    @param tmp_path Temporary folder.
    @return pathlib.Path
    """
    out = tmp_path / "other"
    out.mkdir()
    for f in base.iterdir():
        # A comment line changes the hash and a new name removes the shared name; the geometry and the designators stay
        text = f.read_text()
        (out / ("x_" + f.name)).write_text(text.replace("M02*", "G04 other board*\nM02*") if f.suffix == ".gbr" else text + "\n")
    return out


def test_a_different_board_preselects_the_new_project_and_cancel_protects_the_work(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    before = snapshot(app.doc)
    app.run(other_board(base, tmp_path), "replace", cancel="dialog")
    dlg = app.dialogs[-1]
    assert dlg.different and dlg.radios["new"].isChecked() and dlg.mode == "new"      # (a) the fourth choice, preselected
    assert dlg.radios["new"].text() == "New project from these files"
    assert not dlg.go.isDefault() and dlg.go.objectName() != "primary"                # (d) Cancel is the default, Continue is not the primary action
    assert snapshot(app.doc) == before


def test_a_different_board_carries_no_part_and_has_no_removal_list(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0, "Q1": 1.0})
    app.run(other_board(base, tmp_path), "replace")                                   # the user does not choose the new project
    dlg = app.dialogs[-1]
    assert dlg.different
    for mode in ("replace", "update"):
        dlg.radios[mode].setChecked(True)
        assert dlg.table.isHidden() and dlg.checks == {}                              # (c) no empty box, (b) no removal list
    rec = app.doc.project.imports[0]
    assert not any(p.from_file.get("orphan") for p in rec.parts)                      # no orphans
    assert not any(p.power for p in rec.parts) and not [h for h in app.doc.problem.heaters if h.power]   # (b) U1 3 W of the other board did not land on U1 here
    app.doc.stack.undo()                                                              # one undo step restores the first import
    assert sorted((p.designator, p.power) for p in app.doc.project.imports[0].parts if p.power) == [("Q1", 1.0), ("U1", 3.0)]


def test_a_different_board_keeps_hand_drawn_heaters_and_drops_the_imported_ones(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    app.doc.problem.add_heater(0, 0.5, rect=(0.005, 0.005, 0.002, 0.002), name="hand")
    app.run(other_board(base, tmp_path), "replace")
    assert [h.name for h in app.doc.problem.heaters if h.power] == ["hand"]


def test_a_different_board_as_a_new_project_follows_the_new_board(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    app.run(other_board(base, tmp_path), "new")
    rec = app.doc.project.imports[0]
    assert not any(p.power for p in rec.parts) and app.doc.problem.name == rec.name   # nothing carried, the name is the new board's


def test_the_same_board_dialog_is_unchanged(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    app.run(variant(base, tmp_path, "rev", F_gbr=COPPER_EDIT), "replace")
    dlg = app.dialogs[-1]
    assert not dlg.different and dlg.mode != "new" and dlg.go.objectName() == "primary"
    assert not any(p.from_file.get("orphan") for p in app.doc.project.imports[0].parts)
    assert [h.power for h in app.doc.problem.heaters if h.name == "U1"] == [3.0]       # the stored power is carried as before


def test_the_replace_table_of_the_same_board_without_changes_is_hidden(app, base):
    app.run(base, "replace", powers={"U1": 3.0})
    app.run(base, "replace")
    assert app.dialogs[-1].table.isHidden()


def test_library_rp2040_replaced_by_oswlight_through_the_window(app):
    rp, osw = library("rp2040"), library("oswlight")
    app.run(rp, "replace", powers={"U1": 1.0, "C1": 0.5})
    app.run(osw, "replace", cancel="dialog")
    dlg = app.dialogs[-1]
    assert dlg.different and dlg.mode == "new"
    app.run(osw, "replace")
    rec = app.doc.project.imports[0]
    assert not any(p.from_file.get("orphan") for p in rec.parts) and not any(p.power for p in rec.parts)
