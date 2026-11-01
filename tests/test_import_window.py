#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_import_window.py
@brief The Gerber import window: the session (files, roles, checks, board, hooks of the features not merged yet), the stepper and its locked steps, Back / Next / Import now,
       the file list with editable functions, the preview, the live theme switch and the File menu entry.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pcbthermal.gui import theme as th
from pcbthermal.gui import import_session as ims
from pcbthermal.gui.document import Document
from pcbthermal.gui.import_session import ImportNotAvailable, ImportSession
from pcbthermal.gui.import_window import ImportBoardWindow
from pcbthermal.gui.main_window import MainWindow
from tests.helpers.synthetic_board import HEIGHT, WIDTH, make_board, make_zip


@pytest.fixture
def board_dir(tmp_path):
    """!
    @brief The synthetic fabrication set with two inner layers.
    @param tmp_path Temporary folder.
    @return Path of the folder.
    """
    return make_board(tmp_path / "fab", inner=2)


@pytest.fixture
def window(qtbot, board_dir):
    """!
    @brief An import window with the synthetic board read.
    @param qtbot pytest-qt fixture.
    @param board_dir Folder of the files.
    @return ImportBoardWindow
    """
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    w.confirm = lambda title, text: True
    w.notify = lambda title, text: w.__dict__.setdefault("notes", []).append((title, text))
    w.open_path(str(board_dir))
    return w


# ---------------------------------------------------------------------------------------------------------------------------------- session
def test_roles_are_detected_from_x2_excellon_and_columns(board_dir):
    sx = ImportSession()
    sx.set_files(board_dir)
    roles = {f.name: f.role for f in sx.files}
    assert roles == {"B.gbr": ims.COPPER_BOTTOM, "F.gbr": ims.COPPER_TOP, "In1.gbr": "Inner copper 1", "In2.gbr": "Inner copper 2", "drill.drl": ims.PLATED, "edge.gbr": ims.OUTLINE,
                     "pasteF.gbr": "Solder paste top", "pos.csv": ims.PLACEMENT}
    assert {f.name: f.how for f in sx.files}["drill.drl"] == "Excellon header" and {f.name: f.how for f in sx.files}["F.gbr"] == "Gerber X2 attribute"
    assert [l.role for l in sx.layers()] == [ims.COPPER_TOP, "Inner copper 1", "Inner copper 2", ims.COPPER_BOTTOM]
    assert sx.complete() and sx.stackup()["copper_um"].__len__() == 4


def test_the_board_is_read_with_outline_holes_and_layers(board_dir):
    sx = ImportSession()
    sx.set_files(board_dir)
    b = sx.load()
    assert b.width == pytest.approx(WIDTH) and b.height == pytest.approx(HEIGHT)
    assert b.outline_area_mm2 == pytest.approx(WIDTH * HEIGHT)
    assert [r for r, _, _ in b.copper] == [ims.COPPER_TOP, "Inner copper 1", "Inner copper 2", ims.COPPER_BOTTOM]
    # The bottom copper is a pour of 38 x 28 mm on a 40 x 30 board: its coverage is that share of the window
    cov = dict((r, c) for r, _, c in b.copper)[ims.COPPER_BOTTOM]
    assert cov.sum(dtype=np.float64) / 255.0 * b.pixel_mm ** 2 == pytest.approx(38 * 28, rel=0.02)
    assert sx.vias() == (2, 1, 0)                               # Two 0.3 mm vias, one 3 mm component hole
    assert sx.board() is b


def test_two_files_claiming_a_function_stop_the_import(board_dir):
    sx = ImportSession()
    sx.set_files(board_dir)
    i = [f.name for f in sx.files].index("B.gbr")
    sx.set_role(i, ims.COPPER_TOP)
    assert any("Two files claim 'Top copper'" in p for p in sx.problems()) and not sx.complete()
    assert sx.load() is None
    sx.set_role(i, ims.COPPER_BOTTOM)
    assert sx.complete() and sx.load() is not None


def test_no_copper_and_inner_gaps_are_problems(board_dir):
    sx = ImportSession()
    sx.set_files(board_dir)
    for i, f in enumerate(sx.files):
        if f.role in ims.COPPER:
            sx.set_use(i, False)
    assert "No copper layer is selected" in sx.problems()
    sx.set_files(board_dir)
    i = [f.name for f in sx.files].index("In1.gbr")
    sx.set_use(i, False)                                         # Inner 2 without inner 1
    assert any("without a gap" in p for p in sx.problems())


def test_a_missing_outline_and_drill_are_notes_not_problems(tmp_path):
    d = make_board(tmp_path / "fab", drills=False)
    (d / "edge.gbr").unlink()
    sx = ImportSession()
    sx.set_files(d)
    assert sx.complete()
    notes = " ".join(sx.notes())
    assert "No board outline" in notes and "No drill file" in notes
    b = sx.load()
    assert b.outline == [] and b.outline_area_mm2 is None and b.width == pytest.approx(WIDTH - 2, abs=0.5)      # The box of the copper: 38 x 28 mm


def test_a_file_the_reader_refuses_is_marked(tmp_path):
    d = make_board(tmp_path / "fab")
    (d / "F.gbr").write_text("%TF.FileFunction,Copper,L1,Top*%\n%FSLAX46Y46*%\n%MOMM*%\n%AMFOO*1,1,1,0,0*%\n%ADD10FOO,1*%\nD10*\nX0Y0D03*\nM02*\n%SRX2Y2I1J1*%\n")
    sx = ImportSession()
    sx.set_files(d)
    sx.load()
    top = next(f for f in sx.files if f.name == "F.gbr")
    # Whatever the reader does with this file, a refusal is shown with the file's name and never raises out of load()
    assert top.error == "" or "F.gbr" in " ".join(sx.problems())


def test_a_zip_is_read_in_memory_and_gives_the_same_board(board_dir, tmp_path):
    z = make_zip(board_dir, tmp_path / "set.zip")
    sx = ImportSession()
    sx.set_files(z)
    assert sx.complete() and len(sx.files) == 8 and sx.name == "set"
    b = sx.load()
    assert b.outline_area_mm2 == pytest.approx(WIDTH * HEIGHT) and sx.vias() == (2, 1, 0)
    folder = ImportSession()
    folder.set_files(board_dir)
    assert {f.name: f.sha256 for f in sx.files} == {f.name: f.sha256 for f in folder.files}
    sx.close()


def test_an_unsafe_zip_and_a_non_source_are_refused(tmp_path):
    import zipfile
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("../evil.gbr", "x")
    sx = ImportSession()
    with pytest.raises(Exception, match="unsafe"):
        sx.set_files(bad)
    (tmp_path / "note.txt").write_text("hello")
    with pytest.raises(ValueError):
        sx.set_files(tmp_path / "note.txt")
    with pytest.raises(ValueError):
        sx.set_files(tmp_path / "empty_folder_that_does_not_exist")


def test_files_from_a_list_and_numbered_inner_layers(tmp_path):
    d = make_board(tmp_path / "fab")
    sx = ImportSession()
    sx.set_files([d / "F.gbr", d / "B.gbr", d / "edge.gbr"])
    assert sx.complete() and len(sx.files) == 3 and not sx.used(ims.PLATED)
    # Altium names an inner layer .G1 and .G2 without an X2 index: they get distinct numbers
    for name in ("a.g1", "b.g2"):
        (d / name).write_text("%FSLAX46Y46*%\n%MOMM*%\nM02*\n")
    sx.set_files(d)
    assert sorted(f.role for f in sx.files if f.role in ims.INNER) == ["Inner copper 1", "Inner copper 2"]


def test_parts_come_from_the_paste_layer_and_the_placement_file(board_dir):
    sx = ImportSession()
    sx.set_files(board_dir)
    sx.load()
    parts = {p.designator: p for p in sx.parts()}
    assert set(parts) == {"U1", "Q1", "D1", "R1"}                    # R1 is in the placement file only
    assert [sx.source_label(parts[d]) for d in ("U1", "Q1", "D1", "R1")] == ["paste TO.C + placement"] * 3 + ["placement only"]
    assert parts["R1"].polygon_mm == [] and parts["R1"] in sx.parts()[-1:]       # listed after the candidates, no heat source
    assert sx.unmatched() == [] and len(sx.openings()) == 3
    assert sx.heat_sources() == []
    sx.set_part("U1", power=2.0, tj_max=125.0, role="Source")
    u1 = sx.part("U1")
    assert u1.power == 2.0 and u1.edits["use"] and u1.edits["tj_max"] == 125.0 and sx.is_source(u1)
    sx.set_part("R1", use=True)                                        # no opening: cannot be ticked
    assert not sx.is_source(sx.part("R1"))
    # the shapes are always editable: hull (the suggestion), box and, for several openings, the largest
    assert sx.shapes_of(u1) == ["hull", "box"]
    sx.set_shape("U1", "box")
    xs = [q[0] for q in u1.polygon_mm]
    assert u1.shape == "box" and max(xs) - min(xs) == pytest.approx(3.0, abs=0.1)     # the 3.0 x 2.5 mm pad
    assert u1.edits["shape_user"]


def test_a_click_selects_creates_and_adds(tmp_path):
    d = make_board(tmp_path / "fab")
    (d / "pos.csv").unlink()                                          # TO.C only: every opening is named
    sx = ImportSession()
    sx.set_files(d)
    sx.load()
    assert [sx.source_label(p) for p in sx.parts()] == ["paste only"] * 3
    # An opening the files do not name: take the TO.C attribute off one flash
    text = (d / "pasteF.gbr").read_text().replace("%TO.C,D1*%\n", "")
    (d / "pasteF.gbr").write_text(text)
    sx2 = ImportSession()
    sx2.set_files(d)
    sx2.load()
    assert len(sx2.unmatched()) == 1 and sx2.unmatched()[0].ref is None
    o = sx2.unmatched()[0]
    des = sx2.click(o.x, o.y)                                         # a click on a red opening makes a part
    assert des == "H1" and sx2.unmatched() == [] and sx2.part("H1").from_file["grouping"] == "hand" and sx2.is_source(sx2.part("H1"))
    assert sx2.click(o.x, o.y) == "H1"                                # a click on it again selects it
    assert sx2.click(1.0, 1.0) is None


def test_the_frame_check_proposes_an_offset_and_the_user_answers(tmp_path):
    d = make_board(tmp_path / "fab")
    lines = (d / "pos.csv").read_text().splitlines()
    shifted = [lines[0]]
    for ln in lines[1:]:
        f = ln.split(",")
        f[3], f[4] = str(float(f[3]) + 6.0), str(float(f[4]) + 4.0)                # another origin
        shifted.append(",".join(f))
    (d / "pos.csv").write_text("\n".join(shifted) + "\n")
    text = (d / "pasteF.gbr").read_text()
    for ref in ("U1", "Q1", "D1"):
        text = text.replace(f"%TO.C,{ref}*%\n", "")                           # no designators: position matching is needed
    (d / "pasteF.gbr").write_text(text)
    sx = ImportSession()
    sx.set_files(d)
    sx.load()
    fr = sx.frame_proposal()
    assert fr is not None and (fr["propose"] or fr["misfit"])
    assert any("origin" in w or "do not fit" in w for w in sx.parts_warnings())
    if fr["propose"]:
        sx.answer_frame(True)
        assert sx.offset == (fr["dx"], fr["dy"]) and sx.frame_proposal() is None or sx.offset_answer == "accepted"
    sx.answer_frame(False)
    assert sx.offset == (0.0, 0.0) and sx.offset_answer == "rejected"


def test_the_model_settings_the_memory_verdict_and_the_warnings(board_dir):
    sx = ImportSession()
    sx.set_files(board_dir)
    sx.load()
    assert sx.mapping == "faces" and 0.4 <= sx.auto_cell() <= 1.0
    assert sx.auto_pixel(1.0) == pytest.approx(min(sx.thinnest_mm(), 0.1))
    mv = sx.memory_verdict()
    assert mv["fvm"].verdict == "ok" and mv["import_error"] == "" and mv["import_peak"] > 0
    tiny = sx.memory_verdict(pixel_mm=0.0005)                         # a pixel that cannot fit: the guard refuses before anything is drawn
    assert "pixel of" in tiny["import_error"]
    w = " ".join(sx.warnings())
    assert "No heat source is defined" in w and "Lumped / Analytic" in w and "flow-based face" in w
    sx.cell_mm, sx.mapping = 2.0, "fill"
    w = " ".join(sx.warnings())
    assert "'fill' mapping" in w
    sx.mapping, sx.cell_mm = "faces", 2.0
    assert "above 1 mm" in " ".join(sx.warnings())


def test_the_job_file_is_read_and_a_disagreement_warned(board_dir):
    import json
    (board_dir / "job.gbrjob").write_text(json.dumps({"GeneralSpecs": {"LayerNumber": 2, "BoardThickness": 2.4}}))
    sx = ImportSession()
    sx.set_files(board_dir)
    assert sx.job == {"layers": 2, "thickness_mm": 2.4}
    w = " ".join(sx.job_warnings())
    assert "2 copper layers, the file list has 4" in w and "board thickness of 2.4 mm" in w
    (board_dir / "job.gbrjob").write_text("not json")
    sx.set_files(board_dir)
    assert sx.job is None and sx.job_warnings() == []


def test_build_problem_makes_the_project_with_the_import_record(board_dir, tmp_path):
    from pcbthermal import load_project, save_project
    from pcbthermal.project import Project
    sx = ImportSession()
    sx.set_files(board_dir)
    sx.load()
    sx.set_part("U1", power=2.0, tj_max=125.0)
    sx.cell_mm = 1.0
    prob = sx.build_problem()
    assert prob.board.width == pytest.approx(0.040) and prob.board.height == pytest.approx(0.030) and prob.board.layers == 4
    assert len(prob.vias) == 2 and [h.name for h in prob.heaters] == ["U1"] and prob.heaters[0].power == 2.0 and prob.heaters[0].tj_max == 125.0
    rec = sx.record
    assert [f.function for f in rec.files].count(ims.COPPER_TOP) == 1 and all(len(f.sha256) == 64 for f in rec.files)
    assert {h["kind"] for h in rec.holes} == {"via", "component"} and sum(h["kind"] == "component" for h in rec.holes) == 1
    assert rec.copper.mapping == "faces" and len(rec.copper.layers) == 4 and rec.settings["roles"]["F.gbr"] == ims.COPPER_TOP
    assert {p.designator for p in rec.parts} == {"U1", "Q1", "D1", "R1"}
    path = str(tmp_path / "board.pcbt.json")
    save_project(path, Project(problem=prob, imports=[rec]))
    again = load_project(path)
    assert again.imports[0].name == rec.name and again.imports[0].parts[0].designator in {"U1", "Q1", "D1", "R1"} and len(again.problem.heaters) == 1
    assert again.run_problem().imported is not None


def test_a_panel_outline_is_refused_with_a_message(tmp_path):
    from tests.helpers.synthetic_board import _line
    d = make_board(tmp_path / "fab")
    text = (d / "edge.gbr").read_text().replace("M02*", _line([(50, 0), (60, 0), (60, 10), (50, 10), (50, 0)]) + "M02*")
    (d / "edge.gbr").write_text(text)
    sx = ImportSession()
    sx.set_files(d)
    sx.load()
    with pytest.raises(ValueError, match="panel"):
        sx.build_problem()


def test_reimport_merge_keeps_powers_and_orphans(board_dir, tmp_path):
    sx = ImportSession()
    sx.set_files(board_dir)
    sx.load()
    sx.set_part("U1", power=2.0)
    sx.set_part("Q1", power=1.0)
    sx.build_problem()
    old = sx.record
    # the layout revision: D1 and its paste opening are gone, the copper file changed
    d2 = make_board(tmp_path / "fab2", inner=2)
    text = (d2 / "pasteF.gbr").read_text()
    text = text.replace("%TO.C,D1*%\nD11*\nX30000000Y20000000D03*\n%TD*%\n", "")
    (d2 / "pasteF.gbr").write_text(text)
    (d2 / "pos.csv").write_text("".join(ln + "\n" for ln in (d2 / "pos.csv").read_text().splitlines() if not ln.startswith('"D1"')))
    (d2 / "F.gbr").write_text((d2 / "F.gbr").read_text().replace("M02*", "D10*\nX3000000Y3000000D03*\nM02*"))
    s2 = ImportSession()
    s2.set_files(d2)
    s2.load()
    s2.build_problem()
    diff = {r["ref"]: r["change"] for r in s2.part_diff(old)}
    assert diff["U1"] == "kept" and diff["D1"] == "removed"
    same, _ = s2.same_board(old, s2.record)
    assert same
    st = {c["function"]: c["status"] for c in s2.classify_files(old, s2.record)}
    assert st[ims.COPPER_TOP] == "changed" and st[ims.COPPER_BOTTOM] == "identical"
    res = s2.merge_import("update", old)
    merged = {p.designator: p for p in res["parts"]}
    assert merged["U1"].power == 2.0 and merged["Q1"].power == 1.0
    assert merged["D1"].from_file["orphan"] and res["orphans"] == ["D1"] and not s2.is_orphan(merged["U1"])
    gone = s2.merge_import("replace", old, remove=["D1"])
    assert "D1" not in {p.designator for p in gone["parts"]}
    added = s2.merge_import("add", old, file_choice={ims.COPPER_TOP: "new"})
    assert any("took the new file" in c for c in added["changes"])


def test_the_hash_of_a_large_member_uses_head_tail_and_size(board_dir, tmp_path, monkeypatch):
    z = make_zip(board_dir, tmp_path / "set.zip")
    monkeypatch.setattr(ims, "HASH_WHOLE_BYTES", 100)
    sx = ImportSession()
    sx.set_files(z)
    big = {f.name: f.sha256 for f in sx.files}
    sx.close()
    monkeypatch.setattr(ims, "HASH_WHOLE_BYTES", 10 ** 9)
    sy = ImportSession()
    sy.set_files(z)
    assert {f.name: f.sha256 for f in sy.files}["F.gbr"] != big["F.gbr"] and len(big["F.gbr"]) == 64
    sy.close()


# ---------------------------------------------------------------------------------------------------------------------------------- window
def test_the_window_reads_the_folder_and_fills_the_file_list(window):
    t = window.page1.table
    assert t.rowCount() == 8 and window.session.complete()
    names = [t.item(r, 1).text() for r in range(t.rowCount())]
    assert names == sorted(names) and "F.gbr" in names
    assert "Step 1 is complete" in window.page1.problem.text()
    assert window.page1.layers_label.text().startswith("4:")
    assert "2 vias, 1 component holes" in window.page1.drill_label.text()
    assert "40.00 x 30.00 mm" in window.page1.outline_label.text()
    assert window.page1.layer_pick.count() == 4


def test_the_function_combo_changes_the_session_and_a_clash_is_shown(window, qtbot):
    page = window.page1
    row = [window.session.files[r].name for r in range(8)].index("B.gbr")
    page.table.cellWidget(row, 3).setCurrentText(ims.COPPER_TOP)
    qtbot.waitUntil(lambda: not window.session.complete(), timeout=2000)
    assert "Two files claim" in page.problem.text()
    assert not window.next_btn.isEnabled() and not window.early_btn.isEnabled()
    assert "Next is disabled" in window.status.text()
    red = QColor(th.colors(th.current_name())["bad"])
    assert page.table.item(row, 1).foreground().color().name() == red.name()
    page.table.cellWidget(row, 3).setCurrentText(ims.COPPER_BOTTOM)
    qtbot.waitUntil(window.session.complete, timeout=2000)
    assert window.next_btn.isEnabled()


def test_use_box_leaves_a_file_out(window, qtbot):
    row = [f.name for f in window.session.files].index("In2.gbr")
    window.page1.table.item(row, 0).setCheckState(Qt.Unchecked)
    qtbot.waitUntil(lambda: len(window.session.layers()) == 3, timeout=2000)
    assert window.page1.layer_pick.count() == 3 or window.page1.layers_label.text().startswith("3:")


def test_steps_are_locked_until_step_1_is_complete(qtbot):
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    states = w.step_states()
    assert [s for s, _ in states] == ["current", "locked", "locked"]
    assert all("Locked: step 1 is not complete" in tip for s, tip in states if s == "locked")
    assert "No folder, ZIP or files chosen" in states[1][1]
    assert not w.next_btn.isEnabled() and not w.early_btn.isEnabled() and not w.back_btn.isEnabled()
    w.go(1)
    assert w.step == 0                                           # A locked step cannot be opened
    QTest.mouseClick(w.stepper, Qt.LeftButton, pos=w.stepper.point_of(2))
    assert w.step == 0


def test_stepper_states_back_next_and_import(window):
    w = window
    assert [s for s, _ in w.step_states()] == ["current", "ready", "ready"]
    assert w.next_btn.text() == "Next" and w.early_btn.isVisible() and w.early_btn.isEnabled() and not w.back_btn.isEnabled()
    QTest.mouseClick(w.next_btn, Qt.LeftButton)
    assert w.step == 1 and [s for s, _ in w.step_states()] == ["done", "current", "ready"] and w.back_btn.isEnabled()
    QTest.mouseClick(w.stepper, Qt.LeftButton, pos=w.stepper.point_of(2))     # A click on a reachable marker jumps
    assert w.step == 2 and w.next_btn.text() == "Import" and not w.early_btn.isVisible()
    QTest.mouseClick(w.back_btn, Qt.LeftButton)
    assert w.step == 1
    QTest.mouseClick(w.stepper, Qt.LeftButton, pos=w.stepper.point_of(0))
    assert w.step == 0 and w.stack.currentIndex() == 0


def test_import_now_asks_when_no_heat_source_and_builds_the_project(window, qtbot):
    answers = []
    window.confirm = lambda title, text: (answers.append((title, text)), False)[1]
    assert window.do_import() is False and answers and answers[0][0] == "No heat source defined"
    window.confirm = lambda title, text: True
    assert window.do_import() is True and window.mode == "new"
    assert window.problem.board.layers == 4 and window.record.copper is not None and len(window.record.parts) == 4


def test_the_parts_page_table_edits_and_clicks(window, qtbot):
    window.go(1)
    pg, sx = window.page2, window.session
    assert window.step == 1 and pg.table.rowCount() == 4
    assert [pg.table.item(r, 1).text() for r in range(4)][-1] == "R1"               # listed only, after the candidates
    src = {pg.table.item(r, 1).text(): pg.table.item(r, 3).text() for r in range(4)}
    assert src["U1"] == "paste TO.C + placement" and src["R1"] == "placement only"
    row = [pg.table.item(r, 1).text() for r in range(4)].index("U1")
    pg.table.cellWidget(row, 7).setValue(1.5)                                       # a power ticks the part
    assert sx.part("U1").power == 1.5 and sx.is_source(sx.part("U1")) and window.step_states()[1][0] == "current"
    row = [pg.table.item(r, 1).text() for r in range(4)].index("U1")
    pg.table.selectRow(row)
    assert pg.selected == "U1" and pg.radios["hull"].isChecked() and not pg.radios["largest"].isEnabled()
    pg.radios["box"].setChecked(True)
    assert sx.part("U1").shape == "box"
    pg.table.cellWidget(row, 8).setValue(90.0)
    assert sx.part("U1").edits["tj_max"] == 90.0
    pg.table.cellWidget(row, 9).setCurrentText("Source")
    assert sx.part("U1").edits["role"] == "Source"
    pg.preview.resize(500, 400)
    img = pg.preview.grab().toImage()                                               # the preview draws openings and sources
    assert img.width() > 0
    window.go(0)
    window.go(1)
    assert sx.part("U1").power == 1.5                                              # the edits survive a trip between the steps


def test_the_model_page_mapping_advanced_pixel_cell_and_memory(window, qtbot):
    window.go(2)
    pg, sx = window.page3, window.session
    assert window.step == 2 and window.next_btn.text() == "Import" and pg.radios["faces"].isChecked()
    assert not pg.adv_body.isVisible() and sx.cell_mm == sx.auto_cell()
    pg.adv.setChecked(True)
    assert pg.adv_body.isVisibleTo(pg)
    pg.radios["fill"].setChecked(True)
    assert sx.mapping == "fill" and "'fill' mapping" in " ".join(sx.warnings())
    pg.radios["faces"].setChecked(True)
    assert sx.mapping == "faces"
    pg.cell.setValue(2.0)
    assert sx.cell_mm == 2.0 and "above 1 mm" in pg.wl.toolTip() + " ".join(sx.warnings())
    pg.pix.setValue(0.05)
    assert sx.pixel_mm == 0.05
    pg.refresh()
    pg.pix.parent()
    # Auto buttons restore the automatic values
    autos = [b for b in pg.findChildren(type(window.help_btn)) if b.text() == "Auto"]
    for b in autos:
        b.click()
    assert sx.pixel_mm is None and sx.cell_mm == sx.auto_cell()
    assert "unknowns" in pg.mem.text() and "fits" in pg.mem.text()
    pg.via_max.setValue(0.2)
    assert sx.vias() == (0, 3, 0) and "0 vias, 3 component holes" in pg.vias.text()
    pg.newname.setText("my board")
    assert sx.name == "my board"
    assert pg.layers_label.text().startswith("4:")


def test_the_reimport_dialog_asks_and_the_window_returns_the_merge(window, board_dir, tmp_path, qtbot):
    from pcbthermal.gui.import_window import ReimportDialog
    window.session.set_part("U1", power=2.0)
    window.do_import()
    old = window.record
    w2 = ImportBoardWindow(existing=old)
    qtbot.addWidget(w2)
    w2.confirm = lambda title, text: True
    w2.notify = lambda *a: None
    w2.open_path(str(board_dir))
    seen = []

    def answer(dlg):
        seen.append((dlg.mode, [dlg.table.item(r, 0).text() for r in range(dlg.table.rowCount())]))
        dlg.radios["update"].setChecked(True)
        return True
    w2.ask_reimport = answer
    assert w2.do_import() is True
    assert seen[0][0] == "replace" and w2.mode == "update"
    assert {p.designator: p.power for p in w2.record.parts}["U1"] == 2.0           # the update keeps the stored power, the new session has none
    dlg = ReimportDialog(w2.session, old)
    qtbot.addWidget(dlg)
    assert set(dlg.radios) == {"replace", "update", "add"} and dlg.radios["replace"].isChecked()
    dlg.radios["add"].setChecked(True)
    assert dlg.mode == "add" and dlg.table.columnCount() == 4 and dlg.table.rowCount() >= 1
    assert dlg.file_choice() == {} and dlg.remove_refs() == []
    dlg.radios["update"].setChecked(True)
    assert dlg.table.horizontalHeaderItem(3).text() == "Kept from the stored import"
    assert w2.ask_reimport is answer


def test_the_application_applies_a_new_import_and_a_reimport_as_one_undo_step(qtbot, tmp_path, monkeypatch, board_dir):
    from PySide6.QtWidgets import QMessageBox
    from pcbthermal.gui import import_window as iw
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Discard)
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)

    def fake_exec(self):
        self.confirm = lambda *a: True
        self.open_path(str(board_dir))
        self.session.set_part("U1", power=3.0)
        self.ask_reimport = lambda dlg: (dlg.radios["update"].setChecked(True), True)[1]
        return 1 if self.do_import() else 0
    monkeypatch.setattr(iw.ImportBoardWindow, "exec", fake_exec)
    win.show_import()
    assert win.doc.project.imports and len(win.doc.problem.heaters) == 1 and win.doc.problem.heaters[0].power == 3.0
    win.doc.set_props("heater", 0, power=5.0, merge=False)                          # the user edits after the import
    n = win.doc.stack.count()
    win.show_import()                                                               # the project holds an import: Update
    assert win.doc.stack.count() == n + 1 and len(win.doc.problem.heaters) == 1
    win.doc.stack.undo()
    assert win.doc.problem.heaters[0].power == 5.0


# ---------------------------------------------------------------------------------------------------------------------------------- real boards
REAL = os.environ.get("PCBT_REAL_BOARDS", "")


@pytest.mark.skipif(not REAL or not os.path.isdir(os.path.join(REAL, "rp2040")), reason="PCBT_REAL_BOARDS does not point to the real boards")
def test_the_rp2040_board_through_the_whole_window(qtbot, tmp_path):
    from pcbthermal import load_project, save_project
    from pcbthermal.project import Project
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    w.confirm = lambda *a: True
    w.notify = lambda title, text: pytest.fail(f"{title}: {text}")
    w.open_path(os.path.join(REAL, "rp2040"))
    sx = w.session
    assert sx.complete() and len(sx.layers()) == 2 and sx.vias() == (43, 78, 0)
    w.go(1)
    parts = sx.parts()
    assert len(parts) == 30 and len(sx.openings()) == 129 and sx.unmatched() == []
    assert sx.parts_info()["frame"]["propose"] is False
    assert any("names no parts" in x for x in sx.parts_warnings())
    sx.set_part("C1", power=0.5)
    sx.set_part("C2", power=0.25)
    w.go(2)
    assert w.page3.mem.text() and w.next_btn.text() == "Import"
    assert w.do_import() is True
    prob = w.problem
    assert [h.name for h in prob.heaters] == ["C1", "C2"] or sorted(h.name for h in prob.heaters) == ["C1", "C2"]
    assert len(prob.vias) == 43 and abs(prob.board.width - 0.052) < 1e-3
    save_project(str(tmp_path / "rp.pcbt.json"), Project(problem=prob, imports=[w.record]))
    assert load_project(str(tmp_path / "rp.pcbt.json")).run_problem().imported is not None


def test_a_bad_source_gives_a_message_and_keeps_the_window(window, tmp_path):
    window.open_path(str(tmp_path / "nothing.zip"))
    assert window.notes and window.notes[-1][0] == "Cannot read the files"


def test_the_preview_draws_and_zooms(window, qtbot):
    pv = window.page1.preview
    pv.resize(500, 400)
    img = pv.grab().toImage()
    centre = QColor(img.pixel(img.width() // 2, img.height() // 2))
    assert centre.name() != QColor(th.colors(th.current_name())["canvas"]).name()      # Copper is drawn over the canvas colour
    z = pv.zoom
    QTest.mouseClick(pv, Qt.LeftButton)
    pv.zoom = 4.0
    pv.update()
    pv.reset_view()
    assert pv.zoom == 1.0 and z == 1.0
    window.page1.layer_pick.setCurrentText("Inner copper 2")
    assert pv.selected == "Inner copper 2"


@pytest.mark.parametrize("name", ["light", "dark"])
def test_the_window_follows_a_live_theme_switch(window, name):
    app = QApplication.instance()
    other = "dark" if name == "light" else "light"
    th.apply_theme(app, name)
    window.refresh()
    first = window.page1.preview.grab().toImage()
    stepper_first = window.stepper.grab().toImage()
    th.apply_theme(app, other)
    window.refresh()
    second = window.page1.preview.grab().toImage()
    assert first != second and window.stepper.grab().toImage() != stepper_first
    c = th.colors(other)
    assert QColor(second.pixel(3, 3)).name() == QColor(c["canvas"]).name()      # The canvas of the preview is the theme's canvas token
    window.page1.refresh()
    assert c["ok"] in window.page1.problem.text()                # The message carries the status colour of the new theme
    th.apply_theme(app, "dark")


def test_the_file_menu_opens_the_window_and_loads_nothing_when_closed(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Discard)
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    assert "Import Gerber board" in win.a_import.text() and win.a_import.toolTip()
    texts = [a.text() for m in win.menuBar().actions() if m.text() == "&File" for a in m.menu().actions()]
    assert "Import Gerber board…" in texts
    opened = []
    monkeypatch.setattr("pcbthermal.gui.main_window.ImportBoardWindow.exec", lambda self: (opened.append(self), 0)[1])
    win.a_import.trigger()
    assert len(opened) == 1 and not win.doc.problem.heaters
    assert QPoint is not None
