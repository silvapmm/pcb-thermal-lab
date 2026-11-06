#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_reimport_matrix.py
@brief The re-import of a Gerber board through the application (File - Import Gerber board on a project that already holds an import): every command (Replace, Update, Add files)
       against every kind of change in the files, with the editor's work, a saved and reopened project, undo and redo, Cancel, and the message the user reads.
@details The earlier tests drove the session, the window or the merge on their own; the maintainer found that a re-import "changed nothing", so these tests drive the MainWindow slot
         that applies the result, with the window answering the dialog like a user. What is compared is the document: the packed copper masks, the stored files and their hashes,
         the parts and the heaters. Fast cases use the synthetic board; one case runs the RP2040 files of the library when they are present.
"""

import hashlib
import os
import shutil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from pcbthermal.gui import import_window as iw
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from tests.helpers.synthetic_board import make_board, make_zip

REAL = os.environ.get("PCBT_REAL_BOARDS", "")


def mask_hash(doc):
    """!
    @brief Hash of the packed copper masks of the open problem.
    @param doc The Document.
    @return str (empty without imported copper).
    """
    imp = doc.problem.imported
    if imp is None:
        return ""
    return hashlib.md5("".join(str(e.get("mask", {}).get("data")) for e in imp.layers).encode()).hexdigest()


def snapshot(doc):
    """!
    @brief What a re-import may change in the document.
    @param doc The Document.
    @return dict of comparable values.
    """
    rec = doc.project.imports[0] if doc.project.imports else None
    pr = doc.problem
    return {"masks": mask_hash(doc),
            "files": [(f.function, f.name, f.sha256) for f in rec.files] if rec else None,
            "parts": sorted((p.designator, round(p.power, 6), bool(p.from_file.get("orphan"))) for p in rec.parts) if rec else None,
            "heaters": sorted((h.name, float(h.power), tuple(round(float(v), 9) for v in h.polygon.ravel())) for h in pr.heaters),
            "vias": sorted((round(v.x, 9), round(v.y, 9)) for v in pr.vias),
            "box": list(rec.box_mm) if rec else None}


class App:
    """!
    @brief A main window whose File - Import Gerber board is answered like a user: the folder to read, the powers to set and the command to choose.
    """

    def __init__(self, qtbot, tmp_path, monkeypatch):
        """!
        @param qtbot pytest-qt fixture.
        @param tmp_path Temporary folder.
        @param monkeypatch pytest fixture.
        """
        monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Discard)
        self.win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
        qtbot.addWidget(self.win)
        self.plan = {"source": None, "mode": "replace", "powers": {}, "choice": {}, "cancel": None}
        self.dialogs = []
        plan, app = self.plan, self

        def fake_exec(window):
            window.confirm = lambda *a: True
            window.notify = lambda title, text: pytest.fail(f"{title}: {text}")
            window.open_path(str(plan["source"]))
            for d, w in plan["powers"].items():
                window.session.set_part(d, power=w)
            if getattr(app, "plan_cell", None):
                window.session.cell_mm, window._cell_set = app.plan_cell, True      # the user typed a cell in step 3

            def answer(dlg):
                app.dialogs.append(dlg)
                if plan["cancel"] == "dialog":
                    return False
                dlg.radios[plan["mode"]].setChecked(True)
                for fn, cb in dlg.combos.items():
                    if fn in plan["choice"]:
                        cb.setCurrentIndex(1 if plan["choice"][fn] == "new" else 0)
                return True
            window.ask_reimport = answer
            if plan["cancel"] == "window":
                return 0
            return 1 if window.do_import() else 0
        monkeypatch.setattr(iw.ImportBoardWindow, "exec", fake_exec)

    @property
    def doc(self):
        """!
        @brief The document of the window.
        @return Document
        """
        return self.win.doc

    def run(self, source, mode="replace", powers=None, choice=None, cancel=None):
        """!
        @brief Run File - Import Gerber board once.
        @param source Folder or ZIP the window reads.
        @param mode Command of the re-import dialog.
        @param powers dict designator -> W set in step 2.
        @param choice dict function -> "stored" or "new" for the Add conflicts.
        @param cancel None, "window" (the import window is closed) or "dialog" (the re-import dialog is cancelled).
        @return str The status bar message afterwards.
        """
        self.plan.update(source=source, mode=mode, powers=powers or {}, choice=choice or {}, cancel=cancel)
        self.win.statusBar().showMessage("")
        self.win.show_import()
        return self.win.statusBar().currentMessage()


@pytest.fixture
def app(qtbot, tmp_path, monkeypatch):
    """!
    @brief The application driver.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    @return App
    """
    return App(qtbot, tmp_path, monkeypatch)


@pytest.fixture
def base(tmp_path):
    """!
    @brief The synthetic fabrication set of the first import.
    @param tmp_path Temporary folder.
    @return pathlib.Path
    """
    return make_board(tmp_path / "base", inner=0)


def variant(base, tmp_path, name, **edits):
    """!
    @brief A copy of the fabrication set with some files edited or removed.
    @param base Folder of the original set.
    @param tmp_path Temporary folder.
    @param name Folder name of the copy.
    @param edits file name -> (old text, new text), or None to remove the file.
    @return pathlib.Path
    """
    d = tmp_path / name
    shutil.copytree(base, d)
    for fname, change in edits.items():
        fname = fname.replace("_", ".")
        if change is None:
            (d / fname).unlink()
        else:
            text = (d / fname).read_text()
            assert change[0] in text, (fname, change[0])
            (d / fname).write_text(text.replace(*change))
    return d


# The clear window of the top copper gets a corner pulled out: the copper really changes (a pad flashed on the pour would not)
COPPER_EDIT = ("X10000000Y20000000D01*\nX8000000Y20000000D01", "X10000000Y20000000D01*\nX12000000Y22000000D01*\nX8000000Y20000000D01")


@pytest.mark.parametrize("mode", ["replace", "update", "add"])
def test_the_same_files_again_change_nothing_and_say_so(app, base, mode):
    app.run(base, "replace", powers={"U1": 3.0})
    before = snapshot(app.doc)
    n = app.doc.stack.index()
    msg = app.run(base, mode)
    assert snapshot(app.doc) == before
    assert app.doc.stack.index() <= n + 1                                            # at most one undo step, even when nothing moved
    assert msg.startswith("Gerber board re-imported"), msg
    if mode == "add":
        assert "nothing" in msg.lower(), msg                                         # an empty message looked like a failure


@pytest.mark.parametrize("mode", ["replace", "update"])
def test_changed_copper_is_taken_by_replace_and_update_and_undone_in_one_step(app, base, tmp_path, mode):
    app.run(base, "replace", powers={"U1": 3.0})
    before = snapshot(app.doc)
    new = variant(base, tmp_path, "rev", F_gbr=COPPER_EDIT)
    n = app.doc.stack.index()
    app.run(new, mode)
    after = snapshot(app.doc)
    assert app.doc.stack.index() == n + 1
    assert after["masks"] != before["masks"] and after["files"] != before["files"]
    assert dict(after, masks=0, files=0) == dict(before, masks=0, files=0)         # the powers, parts and heaters stay
    app.doc.stack.undo()
    assert snapshot(app.doc) == before
    app.doc.stack.redo()
    assert snapshot(app.doc) == after


def test_add_never_takes_copper_and_the_message_says_which_file_was_left(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    before = snapshot(app.doc)
    msg = app.run(variant(base, tmp_path, "rev", F_gbr=COPPER_EDIT), "add")
    assert snapshot(app.doc) == before
    assert "F.gbr" in msg and "Replace or Update" in msg, msg


@pytest.mark.parametrize("mode", ["replace", "update"])
def test_a_moved_part_and_a_moved_hole_follow_the_files(app, base, tmp_path, mode):
    app.run(base, "replace", powers={"U1": 3.0})
    before = snapshot(app.doc)
    new = variant(base, tmp_path, "rev", pasteF_gbr=("X12000000Y15000000D03", "X16000000Y15000000D03"),
                  pos_csv=('"U1","reg","SOT-223",12.0,15.0', '"U1","reg","SOT-223",16.0,15.0'), drill_drl=("X20.0Y10.0", "X18.0Y12.0"))
    app.run(new, mode)
    after = snapshot(app.doc)
    assert after["vias"] != before["vias"]
    (u1_before,) = [h for h in before["heaters"] if h[0] == "U1"]
    (u1_after,) = [h for h in after["heaters"] if h[0] == "U1"]
    assert u1_after[1] == 3.0 and u1_after[2] != u1_before[2]                         # same power, new place


def test_add_with_a_changed_placement_file_uses_the_new_file_by_default(app, base, tmp_path):
    """!
    @brief Adding files that claim a function the import already has used to keep the stored file unless the user found the combo: the command did nothing.
    """
    app.run(base, "replace", powers={"U1": 3.0})
    new = variant(base, tmp_path, "rev", pos_csv=('"U1","reg","SOT-223",12.0,15.0', '"U1","reg","SOT-223",12.0,15.0\n"U9","x","SOT-23",5.0,5.0'))
    app.run(new, "add")
    assert app.dialogs[-1].file_choice().get("Placement (pick and place)") == "new"
    assert "U9" in {p.designator for p in app.doc.project.imports[0].parts}


def test_add_takes_the_parts_files_a_copper_only_import_lacked(app, base, tmp_path):
    bare = variant(base, tmp_path, "bare", pasteF_gbr=None, pos_csv=None)
    app.run(bare, "replace")
    assert app.doc.project.imports[0].parts == [] and app.doc.problem.heaters == []
    app.run(base, "add", powers={"U1": 2.0})
    rec = app.doc.project.imports[0]
    assert {p.designator for p in rec.parts} == {"U1", "Q1", "D1", "R1"}
    assert any(f.name == "pos.csv" for f in rec.files) and any(f.name == "pasteF.gbr" for f in rec.files)
    assert mask_hash(app.doc)                                                          # the copper is still there


@pytest.mark.parametrize("mode", ["replace", "update"])
def test_files_that_left_the_folder_leave_orphans_and_the_message_says_so(app, base, tmp_path, mode):
    app.run(base, "replace", powers={"U1": 3.0})
    msg = app.run(variant(base, tmp_path, "gone", pasteF_gbr=None, pos_csv=None), mode)
    rec = app.doc.project.imports[0]
    assert {p.designator: p.power for p in rec.parts}["U1"] == 3.0 and all(p.from_file.get("orphan") for p in rec.parts)
    assert [h.name for h in app.doc.problem.heaters] == []
    assert "orphan" in msg.lower() or "removed" in msg.lower(), msg


def test_a_zip_gives_the_same_result_as_the_folder(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    before = snapshot(app.doc)
    app.run(make_zip(base, tmp_path / "set.zip"), "replace")
    assert snapshot(app.doc) == before


def test_the_choices_of_the_first_import_are_kept_by_a_reimport(app, base):
    """!
    @brief A re-import started from the automatic cell and the default mapping: the cell, the pixel of the masks and the via limit of the stored import were silently replaced.
    """
    app.plan_cell = 0.8
    app.run(base, "replace", powers={"U1": 3.0})
    first = dict(app.doc.project.imports[0].settings)
    assert first["cell_mm"] == 0.8
    app.plan_cell = None
    app.run(base, "replace")
    again = app.doc.project.imports[0].settings
    for k in ("mapping", "cell_mm", "pixel_mm", "via_max_mm"):
        assert again[k] == first[k], k


def test_a_saved_and_reopened_project_takes_a_reimport(app, base, tmp_path, qtbot, monkeypatch):
    app.run(base, "replace", powers={"U1": 3.0})
    path = str(tmp_path / "p.pcbt.json")
    app.doc.save(path)
    second = App(qtbot, tmp_path / "other", monkeypatch) if (tmp_path / "other").mkdir() is None else None
    second.win.open_file(path)
    before = snapshot(second.doc)
    assert before["masks"] == snapshot(app.doc)["masks"]
    second.run(variant(base, tmp_path, "rev", F_gbr=COPPER_EDIT), "update")
    assert snapshot(second.doc)["masks"] != before["masks"]


def test_the_work_done_in_the_editor_survives_every_command(app, base):
    import numpy as np
    from pcbthermal.model import Heater, Zone
    app.run(base, "replace", powers={"U1": 3.0})
    sq = np.array([[0.002, 0.002], [0.004, 0.002], [0.004, 0.004], [0.002, 0.004]])

    def draw(project):
        pr = project.problem
        pr.heaters[0].power = 7.0
        pr.heaters.append(Heater(0, sq.copy(), 1.0, name="Mine"))
        pr.zones.append(Zone(1, sq.copy() * 2, 1.0, name="Pour"))
        pr.add_via(15.0, 15.0, diameter=0.3)
    app.doc.edit("user", draw)
    before = dict(snapshot(app.doc), parts=0)
    for mode in ("replace", "update", "add"):
        app.run(base, mode)
        assert dict(snapshot(app.doc), parts=0) == before, mode
        assert len(app.doc.problem.zones) == 1
        assert {p.designator: p.power for p in app.doc.project.imports[0].parts}["U1"] == 7.0       # the record agrees with the editor


@pytest.mark.parametrize("cancel", ["window", "dialog"])
def test_cancel_at_either_step_changes_nothing(app, base, tmp_path, cancel):
    app.run(base, "replace", powers={"U1": 3.0})
    before = snapshot(app.doc)
    n = app.doc.stack.index()
    app.run(variant(base, tmp_path, "rev", F_gbr=COPPER_EDIT), "replace", cancel=cancel)
    assert snapshot(app.doc) == before and app.doc.stack.index() == n


def test_two_reimports_in_a_row_and_back_again(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    first = snapshot(app.doc)
    rev = variant(base, tmp_path, "rev", F_gbr=COPPER_EDIT)
    app.run(rev, "update")
    second = snapshot(app.doc)
    app.run(rev, "replace")
    assert snapshot(app.doc) == second
    app.run(base, "update")
    assert snapshot(app.doc) == first


def test_the_dialog_does_not_offer_a_continue_that_does_nothing(app, base, qtbot):
    from pcbthermal.gui.import_window import ReimportDialog
    app.run(base, "replace", powers={"U1": 3.0})
    app.run(base, "replace")
    dlg = app.dialogs[-1]
    qtbot.addWidget(dlg)
    dlg.radios["add"].setChecked(True)
    assert not dlg.go.isEnabled() and "nothing" in dlg.note.text().lower()
    dlg.radios["update"].setChecked(True)
    assert dlg.go.isEnabled()
    assert isinstance(dlg, ReimportDialog)


@pytest.mark.skipif(not REAL or not os.path.isdir(os.path.join(REAL, "rp2040")), reason="the library boards are not linked (PCBT_REAL_BOARDS)")
@pytest.mark.parametrize("mode", ["replace", "update"])
def test_the_rp2040_takes_a_changed_copper_file(app, tmp_path, mode):
    src = os.path.join(REAL, "rp2040")
    app.run(src, "replace", powers={"C1": 0.5})
    before = snapshot(app.doc)
    rev = tmp_path / "rp2"
    shutil.copytree(src, rev)
    text = (rev / "F.gbr").read_text()
    assert "M02*" in text
    (rev / "F.gbr").write_text(text.replace("M02*", "%ADD99R,6.000000X6.000000*%\n%LPC*%\nD99*\nX100000000Y-95000000D03*\n%LPD*%\nM02*", 1))
    app.run(rev, mode)
    after = snapshot(app.doc)
    assert after["masks"] != before["masks"] and after["files"] != before["files"]
    assert [h for h in after["heaters"] if h[0] == "C1"][0][1] == 0.5
    app.doc.stack.undo()
    assert snapshot(app.doc)["masks"] == before["masks"]
