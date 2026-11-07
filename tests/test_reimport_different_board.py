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

import os.path
import shutil
import zipfile

from tests.test_reimport_matrix import COPPER_EDIT, app, base, library, snapshot, swap_designators, variant  # noqa: F401  (fixtures)


def other_board(base, tmp_path):
    """!
    @brief A copy of the synthetic set that is ANOTHER board for the re-import: no file name and no content in common, an outline twice as wide, and the designators U1, Q1 and D1
           on each other's pads (the same names, other parts).
    @details Review: with the parts at the same place and only the names and contents changed, the files are a renamed re-export of the SAME board, and the rule now says so
             (see `test_a_renamed_reexport_with_the_parts_in_place_is_the_same_board`); the other board therefore has its parts elsewhere.
    @param base Folder of the original set.
    @param tmp_path Temporary folder.
    @return pathlib.Path
    """
    out = tmp_path / "other"
    out.mkdir()
    for f in base.iterdir():
        # A comment line changes the hash and a new name removes the shared name; the board is twice as wide
        text = f.read_text()
        if f.name == "edge.gbr":
            text = text.replace("X40000000", "X80000000")
        text = swap_designators(text)
        (out / ("x_" + f.name)).write_text(text.replace("M02*", "G04 other board*\nM02*") if f.suffix == ".gbr" else text + "\n")
    return out


def reexport(base, tmp_path, name="re", prefix=""):
    """!
    @brief A copy of the synthetic set as a CAD program writes it again: every file differs by a line (the date stamp of a real export), optionally under new names.
    @param base Folder of the original set.
    @param tmp_path Temporary folder.
    @param name Folder name of the copy.
    @param prefix Text put before every file name ("" keeps the names).
    @return pathlib.Path
    """
    out = tmp_path / name
    out.mkdir()
    for f in base.iterdir():
        text = f.read_text()
        (out / (prefix + f.name)).write_text(text.replace("M02*", "G04 #@! TF.CreationDate,2027-01-01T00:00:00*\nM02*") if f.suffix == ".gbr"
                                             else text.replace("\n", "\n; exported again\n", 1) if f.suffix == ".drl" else text + "\n")
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


# Review: the first rule called a board different when no file was byte-identical or no file name was shared. A CAD program stamps the date in every file it writes, so a
# re-export of the same board after a layout revision dropped every power; these tests hold the revision cases on the same-board side.

def test_a_reexport_with_every_file_changed_is_the_same_board_and_keeps_the_powers(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0, "Q1": 1.0})
    app.run(reexport(base, tmp_path), "update")
    dlg = app.dialogs[-1]
    assert not dlg.different and dlg.carry
    assert {h.name: h.power for h in app.doc.problem.heaters if h.power} == {"U1": 3.0, "Q1": 1.0}


def test_a_renamed_reexport_with_the_parts_in_place_is_the_same_board(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    app.run(reexport(base, tmp_path, prefix="revB-"), "update")                      # no name and no content in common: the parts at the same place decide
    assert not app.dialogs[-1].different
    assert [h.power for h in app.doc.problem.heaters if h.name == "U1"] == [3.0]


def test_renamed_identical_files_and_a_zip_with_a_folder_are_the_same_board(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    ren = tmp_path / "ren"
    ren.mkdir()
    for f in base.iterdir():
        shutil.copy(f, ren / ("board-" + f.name))                                    # new names, same bytes
    app.run(ren, "update")
    assert not app.dialogs[-1].different
    z = tmp_path / "fab.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for f in base.iterdir():
            zf.write(f, "gerbers/" + f.name)                                         # the names carry the folder of the archive
    app.run(z, "update")
    assert not app.dialogs[-1].different
    assert [h.power for h in app.doc.problem.heaters if h.name == "U1"] == [3.0]


def test_the_user_can_carry_the_parts_over_when_the_rule_says_another_board(app, base, tmp_path, monkeypatch):
    app.run(base, "replace", powers={"U1": 3.0, "Q1": 1.0})
    from pcbthermal.gui import import_window as iw
    real = iw.ReimportDialog._mode

    def tick(dlg, *a):
        """!
        @brief Tick the carry box once the dialog is built (the user insists that the files are a revision).
        @param dlg The dialog.
        @param a Signal arguments.
        @return None
        """
        if hasattr(dlg, "go") and dlg.different and not dlg.carry_box.isChecked():
            dlg.carry_box.setChecked(True)                                           # calls _mode again
            return None
        return real(dlg, *a)
    monkeypatch.setattr(iw.ReimportDialog, "_mode", tick)
    app.run(other_board(base, tmp_path), "update")
    dlg = app.dialogs[-1]
    assert dlg.different and dlg.carry and dlg.carry_box.isVisibleTo(dlg)
    assert {h.name: h.power for h in app.doc.problem.heaters if h.power} == {"U1": 3.0, "Q1": 1.0}


def test_the_descriptions_of_another_board_do_not_promise_to_keep_the_powers(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    app.run(other_board(base, tmp_path), "replace", cancel="dialog")
    dlg = app.dialogs[-1]
    assert "same designator keep" not in dlg.descs["replace"].text() and "no part of the stored import is carried over" in dlg.descs["replace"].text()
    assert not dlg.carry_box.isChecked() and not dlg.carry_box.isVisibleTo(dlg)    # hidden while the new project is chosen
    dlg.radios["replace"].setChecked(True)
    assert dlg.carry_box.isVisibleTo(dlg)


def test_library_rp2040_reexported_with_a_moved_part_keeps_the_powers(app, tmp_path):
    rp = library("rp2040")
    app.run(rp, "replace", powers={"U1": 1.0, "C1": 0.5})
    rev = tmp_path / "rev"
    shutil.copytree(rp, rev)
    for f in rev.iterdir():
        text = f.read_text(errors="replace")
        text = text.replace("CreationDate,2023", "CreationDate,2027")                # a new export
        if f.suffix == ".csv":
            text = text.replace('"C1","10u","C_0805_2012Metric",85.115000', '"C1","10u","C_0805_2012Metric",86.115000')
        f.write_text(text)
    assert not any((rev / n).read_bytes() == open(os.path.join(rp, n), "rb").read() for n in os.listdir(rp))
    app.run(rev, "update")
    assert not app.dialogs[-1].different
    assert {h.name: h.power for h in app.doc.problem.heaters if h.power} == {"U1": 1.0, "C1": 0.5}


def test_the_outline_rule_at_five_per_cent_and_a_grown_board_with_the_parts_in_place(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    for width, different in (("41960000", False), ("42040000", False)):              # 4.9 % and 5.1 % wider, the parts in place: the parts decide, a revision
        app.run(variant(base, tmp_path, "w" + width, edge_gbr=("X40000000", "X" + width)), "update")
        assert app.dialogs[-1].different is different
        assert [h.power for h in app.doc.problem.heaters if h.name == "U1"] == [3.0]


def test_the_outline_rule_alone_without_parts(app, base, tmp_path):
    # Without parts in both sets the outline box decides at 5 %
    bare = variant(base, tmp_path, "bare", pos_csv=None, pasteF_gbr=None)
    app.run(bare, "replace")
    for width, different in (("41960000", False), ("42040000", True)):
        app.run(variant(bare, tmp_path, "b" + width, edge_gbr=("X40000000", "X" + width)), "replace", cancel="dialog")
        assert app.dialogs[-1].different is different
