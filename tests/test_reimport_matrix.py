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
        self.plan = {"source": None, "mode": "replace", "powers": {}, "choice": {}, "cancel": None, "untick": [], "roles": {}}
        self.dialogs = []
        plan, app = self.plan, self

        def fake_exec(window):
            window.confirm = lambda *a: True
            window.notify = lambda title, text: pytest.fail(f"{title}: {text}")
            window.open_path(str(plan["source"]))
            names = [f.name for f in window.session.files]
            for n in plan["untick"]:
                window.session.set_use(names.index(n), False)
            for n, role in plan["roles"].items():
                window.session.set_role(names.index(n), role)
            if plan["untick"] or plan["roles"]:
                window.reload()
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

    def run(self, source, mode="replace", powers=None, choice=None, cancel=None, untick=(), roles=None):
        """!
        @brief Run File - Import Gerber board once.
        @param source Folder or ZIP the window reads.
        @param mode Command of the re-import dialog.
        @param powers dict designator -> W set in step 2.
        @param choice dict function -> "stored" or "new" for the Add conflicts.
        @param cancel None, "window" (the import window is closed) or "dialog" (the re-import dialog is cancelled).
        @param untick File names the user unticks in step 1.
        @param roles dict file name -> function the user chooses in step 1.
        @return str The status bar message afterwards.
        """
        self.plan.update(source=source, mode=mode, powers=powers or {}, choice=choice or {}, cancel=cancel, untick=list(untick), roles=dict(roles or {}))
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


def edit_copper(src, rev, box):
    """!
    @brief Copy a fabrication set and change its top copper: a 5 mm clear hole at the centre of the board with a 2 mm dot in it (a change whether or not there was copper).
    @param src Folder of the set.
    @param rev Folder of the copy (created).
    @param box Board box (x0, y0, x1, y1) in mm in the Gerber frame.
    @return pathlib.Path of the copy.
    """
    shutil.copytree(src, rev)
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    f = rev / "F.gbr"
    text = f.read_text()
    assert "M02*" in text
    extra = (f"%ADD97C,5.000000*%\n%ADD98C,2.000000*%\n%LPC*%\nD97*\nX{int(cx * 1e6)}Y{int(cy * 1e6)}D03*\n%LPD*%\nD98*\nX{int(cx * 1e6)}Y{int(cy * 1e6)}D03*\nM02*")
    f.write_text(text.replace("M02*", extra, 1))
    return rev


def copper_item_hash(app):
    """!
    @brief Hash of the pixmap the canvas draws for the imported copper of the active layer (None when none is drawn).
    @param app The App.
    @return str or None
    """
    app.win.canvas.rebuild() if hasattr(app.win.canvas, "rebuild") else None
    item = app.win.canvas._copper_item
    if item is None:
        return None
    img = item.pixmap().toImage()
    return hashlib.md5(bytes(img.constBits())).hexdigest()


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
    assert "Every file is the same as the stored one" in dlg.intro.text()            # the same folder chosen again: the dialog says nothing will change
    dlg.radios["add"].setChecked(True)
    assert not dlg.go.isEnabled() and "nothing" in dlg.note.text().lower()
    dlg.radios["update"].setChecked(True)
    assert dlg.go.isEnabled()
    assert isinstance(dlg, ReimportDialog)


def library(key):
    """!
    @brief Folder of a library board, or skip the test.
    @param key Board key (rp2040, co60, oswlight).
    @return str
    """
    path = os.path.join(REAL, key) if REAL else ""
    if not os.path.isdir(path):
        pytest.skip("the library boards are not linked (PCBT_REAL_BOARDS)")
    return path


@pytest.mark.parametrize("key, power", [("rp2040", {"C1": 0.5}), ("co60", {}), ("oswlight", {})])
@pytest.mark.parametrize("mode", ["replace", "update"])
def test_library_boards_take_changed_copper_and_the_same_files_again(app, tmp_path, key, power, mode):
    src = library(key)
    app.run(src, "replace", powers=power)
    before = snapshot(app.doc)
    app.run(src, mode)                                                                 # the very same files
    assert snapshot(app.doc) == before
    rev = edit_copper(src, tmp_path / "rev", app.doc.project.imports[0].box_mm)
    msg = app.run(rev, mode)
    after = snapshot(app.doc)
    assert after["masks"] != before["masks"] and after["files"] != before["files"]
    for d, w in power.items():
        assert [h for h in after["heaters"] if h[0] == d][0][1] == w
    assert "copper layer(s) replaced" in msg and not msg.startswith("Gerber board re-imported (" + mode + "): 0 of"), msg
    app.doc.stack.undo()
    assert snapshot(app.doc)["masks"] == before["masks"]


def test_rp2040_add_new_paste_and_placement_files_to_a_project_imported_without_them(app, tmp_path):
    src = library("rp2040")
    bare = tmp_path / "bare"
    shutil.copytree(src, bare)
    for n in ("pasteF.gbr", "pasteB.gbr", "pos.csv"):
        (bare / n).unlink()
    app.run(bare, "replace")
    before = snapshot(app.doc)
    assert before["parts"] == [] and before["heaters"] == []
    msg = app.run(src, "add", powers={"C1": 0.5})
    rec = app.doc.project.imports[0]
    assert len(rec.parts) == 30 and [h.name for h in app.doc.problem.heaters] == ["C1"]
    assert app.doc.problem.heaters[0].power == 0.5
    assert mask_hash(app.doc) == before["masks"] and sorted(v for v in snapshot(app.doc)["vias"]) == before["vias"]
    assert "30 part(s) added" in msg and "untouched" in msg, msg


def test_the_canvas_draws_the_new_copper_after_a_reimport_and_the_old_after_undo(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    h0 = copper_item_hash(app)
    assert h0 is not None
    app.run(variant(base, tmp_path, "rev", F_gbr=COPPER_EDIT), "replace")
    h1 = copper_item_hash(app)
    assert h1 is not None and h1 != h0
    app.doc.stack.undo()
    assert copper_item_hash(app) == h0
    app.doc.stack.redo()
    assert copper_item_hash(app) == h1


def test_a_moved_part_says_moved_and_the_status_gives_the_numbers(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    new = variant(base, tmp_path, "rev", pasteF_gbr=("X12000000Y15000000D03", "X16000000Y15000000D03"),
                  pos_csv=('"U1","reg","SOT-223",12.0,15.0', '"U1","reg","SOT-223",16.0,15.0'), F_gbr=COPPER_EDIT)
    msg = app.run(new, "update")
    assert "1 of 2 copper layer(s) replaced" in msg and "1 moved" in msg and "0 orphaned" in msg, msg


def test_merge_parts_reports_the_move_and_the_position_match():
    from pcbthermal.gerber.parts import merge_parts
    from pcbthermal.model import ImportPart
    sq = lambda x, y: [[x, y], [x + 2, y], [x + 2, y + 2], [x, y + 2]]
    old = [ImportPart("U1", polygon_mm=sq(0, 0), power=2.0, edits={}), ImportPart("U2", polygon_mm=sq(10, 0)), ImportPart("H1", polygon_mm=sq(20, 0), from_file={"grouping": "hand"})]
    new = [ImportPart("U1", polygon_mm=sq(3, 0)), ImportPart("U2", polygon_mm=sq(10, 0)), ImportPart("H1", polygon_mm=sq(20.2, 0), from_file={"grouping": "hand"})]
    lines = merge_parts(old, new).changes
    assert "U1: moved by 3.00 mm, kept power 2 W" in lines and "U2: matched" in lines
    assert "H1: matched by position" in lines, lines                                    # 0.10 mm is within the one threshold (parts.MOVED_MM, 0.3 mm) of the table and the status


def _second_drill(folder):
    """!
    @brief Add a second plated drill file to a synthetic set.
    @param folder Folder of the set.
    @return None
    """
    (folder / "drill2.drl").write_text((folder / "drill.drl").read_text().replace("X20.0Y10.0", "X5.0Y25.0").replace("X22.0Y10.0", "X6.0Y25.0").replace("X30.0Y25.0", "X7.0Y25.0"))


def test_two_files_of_one_function_are_paired_and_kept(app, base, tmp_path):
    """!
    @brief A function that may hold several files (two plated drill files) was collapsed to one by the file comparison and by Add files.
    """
    first = tmp_path / "two_drills"
    shutil.copytree(base, first)
    _second_drill(first)
    app.run(first, "replace", powers={"U1": 3.0})
    rec = app.doc.project.imports[0]
    plated = sorted(f.name for f in rec.files if f.function == "Plated drill")
    assert plated == ["drill.drl", "drill2.drl"]
    before = snapshot(app.doc)
    app.run(first, "add")
    assert sorted(f.name for f in app.doc.project.imports[0].files if f.function == "Plated drill") == plated
    assert snapshot(app.doc) == before
    # one of them changes: it is paired with its own stored file, the other stays identical
    rev = tmp_path / "rev"
    shutil.copytree(first, rev)
    (rev / "drill2.drl").write_text((rev / "drill2.drl").read_text().replace("X5.0Y25.0", "X5.5Y25.0"))
    app.run(rev, "replace", powers={"U1": 3.0})
    status = {(i["old"] or i["new"]).name: i["status"] for i in app.dialogs[-1].sources if i["function"] == "Plated drill"}
    assert status == {"drill.drl": "identical", "drill2.drl": "changed"}, status
    assert snapshot(app.doc)["vias"] != before["vias"]


def test_the_choices_about_the_files_survive_a_reimport(app, base, tmp_path):
    """!
    @brief A second placement table stops the import until the user unticks it; the user's decision about the files (a function chosen, a file left out) must not come back.
    """
    two = tmp_path / "two_pos"
    shutil.copytree(base, two)
    shutil.copy(two / "pos.csv", two / "cpl2.csv")
    app.run(two, "replace", powers={"U1": 3.0}, untick=["cpl2.csv"])
    before = snapshot(app.doc)
    assert "cpl2.csv" in app.doc.project.imports[0].settings["not_used"]
    app.run(two, "update")                                                              # no untick this time: the stored choice is applied by the window
    assert snapshot(app.doc) == before
    # a function chosen by hand: a placement table given another function is kept so
    third = tmp_path / "third"
    shutil.copytree(base, third)
    shutil.copy(third / "pos.csv", third / "cpl3.csv")
    app.run(third, "update", roles={"cpl3.csv": "Ignore"})
    assert app.doc.project.imports[0].settings["user_roles"]["cpl3.csv"] == "Ignore"
    app.run(third, "update")
    assert snapshot(app.doc)["parts"] == before["parts"] and app.doc.project.imports[0].settings["user_roles"]["cpl3.csv"] == "Ignore"


@pytest.mark.parametrize("mode", ["replace", "update"])
def test_values_typed_in_step2_of_a_reimport_win(app, base, mode):
    """!
    @brief Review: step 2 of a re-import started at zero powers and the merge kept the stored ones, so a power typed or a part ticked there was dropped: the re-import "changed nothing".
    """
    app.run(base, "replace", powers={"U1": 3.0})
    seen = {}
    real = iw.ImportBoardWindow.open_path

    def spy(window, source):
        real(window, source)
        seen.update({p.designator: (p.power, bool(p.edits.get("use"))) for p in window.session.parts()})
    iw.ImportBoardWindow.open_path = spy
    try:
        msg = app.run(base, mode, powers={"U1": 5.0, "Q1": 1.0})
    finally:
        iw.ImportBoardWindow.open_path = real
    assert seen["U1"] == (3.0, True) and seen["Q1"] == (0.0, False)                    # the table shows what the project has
    assert {h.name: h.power for h in app.doc.problem.heaters} == {"U1": 5.0, "Q1": 1.0}
    assert {p.designator: p.power for p in app.doc.project.imports[0].parts}["U1"] == 5.0
    assert "took the values of step 2" in msg and "kept power 3 W" not in msg, msg
    app.doc.stack.undo()
    assert {h.name: h.power for h in app.doc.problem.heaters} == {"U1": 3.0}


def test_a_part_unticked_in_step2_stops_heating_and_the_editor_power_is_shown(app, base):
    app.run(base, "replace", powers={"U1": 3.0})
    app.doc.edit("user", lambda project: setattr(project.problem.heaters[0], "power", 7.0))
    seen = {}
    real = iw.ImportBoardWindow.open_path

    def spy(window, source):
        real(window, source)
        seen["U1"] = window.session.part("U1").power
        window.session.set_part("U1", use=False)
    iw.ImportBoardWindow.open_path = spy
    try:
        app.run(base, "update")
    finally:
        iw.ImportBoardWindow.open_path = real
    assert seen["U1"] == 7.0                                                           # the editor's power, not the record's 3 W
    assert app.doc.problem.heaters == []


def test_a_renamed_heater_and_a_deleted_heater_survive_the_prefilled_table(app, base):
    app.run(base, "replace", powers={"U1": 3.0, "Q1": 1.0})

    def edit(project):
        hs = {h.name: h for h in project.problem.heaters}
        hs["U1"].name, hs["U1"].power = "Regulator", 4.0
        project.problem.heaters = [h for h in project.problem.heaters if h is not hs["Q1"]]
    app.doc.edit("user", edit)
    for mode in ("replace", "update"):
        app.run(base, mode)
        assert {h.name: h.power for h in app.doc.problem.heaters} == {"Regulator": 4.0}, mode


def test_add_with_a_moved_part_moves_its_heater(app, base, tmp_path):
    """!
    @brief Review: Add files with a new placement and paste file moved the part in the record but left its heater at the old place (the status said "moved by 4.00 mm").
    """
    app.run(base, "replace", powers={"U1": 3.0})
    before = {h.name: h.polygon.copy() for h in app.doc.problem.heaters}
    new = variant(base, tmp_path, "rev", pasteF_gbr=("X12000000Y15000000D03", "X16000000Y15000000D03"),
                  pos_csv=('"U1","reg","SOT-223",12.0,15.0', '"U1","reg","SOT-223",16.0,15.0'))
    msg = app.run(new, "add")
    (h,) = app.doc.problem.heaters
    assert h.power == 3.0 and abs((h.polygon - before["U1"])[:, 0].mean() - 0.004) < 1e-9 and abs((h.polygon - before["U1"])[:, 1]).max() < 1e-9
    rec = {p.designator: p for p in app.doc.project.imports[0].parts}["U1"]
    box = app.doc.project.imports[0].box_mm
    assert abs(h.polygon[0][0] * 1e3 + box[0] - rec.polygon_mm[0][0]) < 1e-6           # the heater sits on the part of the record
    assert "moved the heater" in msg, msg


def test_a_typed_pixel_is_kept_by_a_reimport(app, base):
    real = iw.ImportBoardWindow.open_path

    def typed(window, source):
        real(window, source)
        window.session.pixel_mm = 0.04
    iw.ImportBoardWindow.open_path = typed
    try:
        app.run(base, "replace", powers={"U1": 3.0})
    finally:
        iw.ImportBoardWindow.open_path = real
    first = dict(app.doc.project.imports[0].settings)
    assert first["pixel_mm"] == 0.04 and first.get("pixel_user") is True
    masks = mask_hash(app.doc)
    app.run(base, "replace")
    assert app.doc.project.imports[0].settings["pixel_mm"] == 0.04 and mask_hash(app.doc) == masks


def test_add_files_takes_the_power_typed_for_a_stored_part(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    new = variant(base, tmp_path, "rev", pos_csv=('"U1","reg","SOT-223",12.0,15.0', '"U1","reg","SOT-223",12.0,15.0\n"U9","x","SOT-23",5.0,5.0'))
    app.run(new, "add", powers={"U1": 6.0, "Q1": 0.5})
    assert {h.name: h.power for h in app.doc.problem.heaters} == {"U1": 6.0, "Q1": 0.5}
    assert {p.designator: p.power for p in app.doc.project.imports[0].parts}["U1"] == 6.0


def test_a_different_board_makes_cancel_the_default_button(app, base, tmp_path):
    app.run(base, "replace", powers={"U1": 3.0})
    other = make_board(tmp_path / "other", inner=0)
    (other / "edge.gbr").write_text((other / "edge.gbr").read_text().replace("X40000000", "X80000000"))
    app.run(other, "replace", cancel="dialog")
    dlg = app.dialogs[-1]
    assert dlg.different and "this looks like a different board" in dlg.warn.text().lower()
    assert dlg.go.isEnabled() and not dlg.go.isDefault()
    cancel = [b for b in dlg.findChildren(type(dlg.go)) if b.text().replace("&", "") == "Cancel"][0]
    assert cancel.isDefault()
    app.run(base, "replace", cancel="dialog")
    assert not app.dialogs[-1].different
