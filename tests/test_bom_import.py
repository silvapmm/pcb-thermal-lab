#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_bom_import.py
@brief The BOM in the Gerber import: the file role found by content (folder, ZIP, UTF-16, an Excel workbook that is not read), the BOM line of step 1, the guess and the not-fitted mark in
       step 2 (never applied silently, never touching a tick), the project written with and without a BOM, the re-import cases (same file, changed BOM, BOM removed, Add files, a user
       edit that wins) driven through the real MainWindow, and the package round trip with a BOM.
"""

import json
import os
import shutil
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from pcbthermal import package as pkg
from pcbthermal.gui import import_session as ims
from pcbthermal.gui.import_session import BOM, ImportSession
from pcbthermal.gui.import_window import ImportBoardWindow
from tests.helpers.synthetic_board import make_board, make_zip
from tests.test_reimport_matrix import App, snapshot  # noqa: F401  (the application driver)

# The parts of the synthetic board are U1, Q1, D1 and R1; the file name carries no "bom" on purpose (found by its columns)
TABLE = "Designator,Comment,Footprint,Quantity,DNP,LCSC Part #\nU1,reg,SOT-223,1,,C1\nQ1,fet,SOT-23,1,,C2\nD1,led,D_0603,1,DNP,C3\nR1,1k,R_0603,1,,C4\nTP9,TP,TestPoint,1,,\n"
TABLE_B = TABLE.replace("U1,reg,SOT-223", "U1,reg,Connector_PinHeader")                 # the footprint of U1 now says connector: another guess for U1


@pytest.fixture
def base(tmp_path):
    """!
    @brief The synthetic fabrication set with a BOM that has no "bom" in its name.
    @param tmp_path Temporary folder.
    @return pathlib.Path
    """
    d = make_board(tmp_path / "base", inner=0)
    (d / "assembly.csv").write_text(TABLE)
    return d


@pytest.fixture
def app(qtbot, tmp_path, monkeypatch):
    """!
    @brief The application driver of the re-import matrix.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    @return App
    """
    return App(qtbot, tmp_path, monkeypatch)


def roles_of(session):
    """!
    @brief The function of each file of a session.
    @param session ImportSession.
    @return dict name -> role.
    """
    return {f.name: f.role for f in session.files}


# ---------------------------------------------------------------------------------------------------------------------------------------- step 1
def test_the_bom_is_found_by_its_columns_in_a_folder_and_a_zip(tmp_path, base):
    for src in (base, make_zip(base, tmp_path / "set.zip")):
        s = ImportSession()
        s.set_files(src)
        r = roles_of(s)
        assert r["assembly.csv"] == BOM and r["pos.csv"] == ims.PLACEMENT
        assert next(f for f in s.files if f.name == "assembly.csv").how == "columns of a BOM table" and next(f for f in s.files if f.name == "assembly.csv").use
        assert s.complete()


def test_a_utf16_bom_is_found_and_read(tmp_path, base):
    (base / "assembly.csv").write_bytes(TABLE.encode("utf-16"))
    s = ImportSession()
    s.set_files(base)
    assert roles_of(s)["assembly.csv"] == BOM
    assert sorted(s.bom_set().rows) == ["D1", "Q1", "R1", "TP9", "U1"]


def test_an_excel_workbook_is_listed_as_a_bom_that_is_not_read(tmp_path, base):
    (base / "parts.xlsx").write_bytes(b"PK\x03\x04" + b"\x00" * 100)
    s = ImportSession()
    s.set_files(base)
    f = next(f for f in s.files if f.name == "parts.xlsx")
    assert f.role == BOM and "not read" in f.how and "save the table as CSV" in f.error
    assert any("parts.xlsx is not used" in n and "CSV" in n for n in s.notes())
    assert s.bom_set().rows.keys() >= {"U1"}                                  # the CSV next to it is still read
    assert s.complete()                                                      # the import is not blocked


def test_the_line_of_step_1_says_what_was_read_and_the_variant(base):
    s = ImportSession()
    s.set_files(base)
    text, check, tip = s.bom_line()
    assert "5 designators from 1 file(s)" in text and "1 marked not fitted" in text and "names no assembly variant" in text and not check and "never sets a power" in tip
    (base / "assembly.csv").write_text("Designator,Comment,Variant\nR1,1k,Lite\n")
    s.set_files(base)
    assert "assembly variant: Lite" in s.bom_line()[0]
    s.set_use([f.name for f in s.files].index("assembly.csv"), False)
    assert s.bom_line() == ("", False, "") and s.bom_set() is None


def test_a_file_that_is_a_placement_table_is_not_taken_for_a_bom(tmp_path):
    d = make_board(tmp_path / "plain")
    s = ImportSession()
    s.set_files(d)
    assert BOM not in roles_of(s).values() and s.bom_set() is None and s.bom_line()[0] == ""


def test_the_user_can_change_the_function_of_the_bom(base):
    s = ImportSession()
    s.set_files(base)
    i = [f.name for f in s.files].index("assembly.csv")
    s.set_role(i, ims.IGNORE)
    assert s.bom_set() is None
    s.set_role(i, BOM)
    assert s.bom_set() is not None


# ---------------------------------------------------------------------------------------------------------------------------------------- step 2
def test_the_parts_carry_the_guess_and_the_mark_and_nothing_else_changes(base):
    plain = ImportSession()
    shutil.copytree(base, base.parent / "nobom")
    (base.parent / "nobom" / "assembly.csv").unlink()
    plain.set_files(base.parent / "nobom")
    s = ImportSession()
    s.set_files(base)
    by = {p.designator: p for p in s.parts()}
    assert by["U1"].from_file["bom"] == {"role": "component", "dnp": False, "lcsc": "C1", "qty": "1"}
    assert by["R1"].from_file["bom"]["role"] == "source" and by["D1"].from_file["bom"]["dnp"] is True
    assert "TP9" not in by                                                    # a BOM-only designator makes no part
    assert s.bom_match()["bom_only"] == ["TP9"] and s.bom_match()["not_fitted"] == ["D1"] and s.bom_match()["not_in_bom"] == []
    assert [s.bom_proposal_text(by[d]) for d in ("U1", "R1", "D1")] == ["component", "source", "not fitted"]
    # Powers, ticks, positions and roles are exactly those of an import without the BOM: the guess is never applied on its own
    for p in plain.parts():
        q = by[p.designator]
        assert (p.power, p.edits, p.polygon_mm, p.shape) == (q.power, q.edits, q.polygon_mm, q.shape) and "bom" not in p.from_file
    assert all("role" not in p.edits and not p.edits.get("use") for p in s.parts())


def test_the_roles_are_applied_only_when_the_user_asks_and_a_chosen_role_stays(base):
    s = ImportSession()
    s.set_files(base)
    s.set_part("Q1", role="Source")                                            # the user chose it
    n = s.use_bom_roles()
    by = {p.designator: p for p in s.parts()}
    assert by["Q1"].edits["role"] == "Source" and by["U1"].edits["role"] == "Component" and by["R1"].edits["role"] == "Source" and n == 3
    assert not by["D1"].edits.get("use")                                       # not fitted, still unticked, and nothing unticked it


def test_a_part_not_in_the_bom_is_said_so(base):
    (base / "assembly.csv").write_text("Designator,Comment\nU1,reg\n")
    s = ImportSession()
    s.set_files(base)
    by = {p.designator: p for p in s.parts()}
    assert s.bom_proposal_text(by["Q1"]) == "not in BOM" and sorted(s.bom_match()["not_in_bom"]) == ["D1", "Q1", "R1"]


def test_the_step_2_table_shows_the_column_only_with_a_bom(qtbot, base, tmp_path):
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    w.confirm = lambda *a: True
    w.open_path(str(base))
    assert w.page1.bom_label.isVisible() is False or w.page1.bom_label.text().startswith("BOM: 5 designators")
    w.go(1)
    t = w.page2.table
    assert not t.isColumnHidden(w.page2.BOM_COL) and w.page2.bom_roles_btn.isVisible()
    texts = {t.item(r, 1).text(): t.item(r, w.page2.BOM_COL).text() for r in range(t.rowCount())}
    assert texts["U1"] == "component" and texts["D1"] == "not fitted"
    assert t.item(0, w.page2.BOM_COL).toolTip()
    assert "BOM: 4 of these parts are in it" in w.page2.info.text()
    w.page2.bom_roles_btn.click()
    assert w.session.part("U1").edits["role"] == "Component"
    # Without a BOM the window is the one it always was
    w2 = ImportBoardWindow()
    qtbot.addWidget(w2)
    w2.show()
    w2.confirm = lambda *a: True
    w2.open_path(str(make_board(tmp_path / "nb")))
    w2.go(1)
    assert w2.page2.table.isColumnHidden(w2.page2.BOM_COL) and not w2.page2.bom_roles_btn.isVisible() and not w2.page1.bom_label.isVisible()


# ---------------------------------------------------------------------------------------------------------------------------------------- the project
def test_a_project_without_a_bom_has_no_bom_key_and_with_one_round_trips(app, base, tmp_path):
    nobom = tmp_path / "nb"
    shutil.copytree(base, nobom)
    (nobom / "assembly.csv").unlink()
    app.run(nobom, powers={"U1": 2.0})
    text = json.dumps(app.doc.project.imports[0].to_dict(), sort_keys=True)
    assert "bom" not in text.lower() and "BOM (bill" not in text
    app.run(base, powers={"U1": 2.0})
    rec = app.doc.project.imports[0]
    assert any(f.function == BOM and f.name == "assembly.csv" for f in rec.files)
    by = {p.designator: p for p in rec.parts}
    assert by["U1"].from_file["bom"]["role"] == "component" and by["D1"].from_file["bom"]["dnp"] is True
    # Only the role, the mark and the part numbers are stored: never a price or a distributor
    assert set(by["U1"].from_file["bom"]) <= {"role", "dnp", "mpn", "lcsc", "qty"}
    again = type(rec).from_dict(json.loads(json.dumps(rec.to_dict())))
    assert {p.designator: p.from_file.get("bom") for p in again.parts} == {p.designator: p.from_file.get("bom") for p in rec.parts}


def test_the_package_stores_the_bom_by_its_role_and_gives_it_back(tmp_path, base):
    from pcbthermal.gui import package_actions as pa
    s = ImportSession()
    s.set_files(base)
    got = {n: k for n, _, k, _, _ in pa.session_files(s)[0]}
    assert got["assembly.csv"] == "bom" and got["pos.csv"] == "placement"
    s.set_role([f.name for f in s.files].index("assembly.csv"), ims.IGNORE)
    assert {n: k for n, _, k, _, _ in pa.session_files(s)[0]}["assembly.csv"] == "other"
    assert pkg.KINDS.count("bom") == 1


# ---------------------------------------------------------------------------------------------------------------------------------------- re-import
def bom_roles(app):
    """!
    @brief The BOM role of each part of the open project.
    @param app The App.
    @return dict designator -> role or None.
    """
    return {p.designator: (p.from_file.get("bom") or {}).get("role") for p in app.doc.project.imports[0].parts}


def test_the_same_bom_again_changes_nothing(app, base):
    app.run(base, powers={"U1": 3.0})
    before = snapshot(app.doc)
    msg = app.run(base, "replace", powers={"U1": 3.0})
    assert snapshot(app.doc) == before and "BOM role" not in msg


def test_a_changed_bom_updates_the_guess_and_the_user_role_wins(app, base, tmp_path):
    app.run(base, powers={"U1": 3.0})
    rev = tmp_path / "rev"
    shutil.copytree(base, rev)
    (rev / "assembly.csv").write_text(TABLE_B)
    msg = app.run(rev, "update", powers={"U1": 3.0})
    assert bom_roles(app)["U1"] == "unknown"                                   # prefix U says component, a connector footprint says none: a tie
    rec = app.doc.project.imports[0]
    assert next(p for p in rec.parts if p.designator == "U1").power == 3.0     # the power is the user's


def test_a_user_edit_of_the_role_survives_a_re_import_with_another_bom_role(app, base, tmp_path):
    app.run(base, powers={"U1": 3.0})
    rec = app.doc.project.imports[0]
    next(p for p in rec.parts if p.designator == "U1").edits["role"] = "Source"
    rev = tmp_path / "rev"
    shutil.copytree(base, rev)
    (rev / "assembly.csv").write_text(TABLE_B)
    app.run(rev, "update")
    u1 = next(p for p in app.doc.project.imports[0].parts if p.designator == "U1")
    assert u1.edits["role"] == "Source" and u1.from_file["bom"]["role"] == "unknown"


def test_a_bom_removed_in_the_new_files_drops_the_stored_bom_data(app, base, tmp_path):
    app.run(base, powers={"U1": 3.0})
    assert bom_roles(app)["U1"] == "component"
    rev = tmp_path / "rev"
    shutil.copytree(base, rev)
    (rev / "assembly.csv").unlink()
    app.run(rev, "replace", powers={"U1": 3.0})
    rec = app.doc.project.imports[0]
    assert all("bom" not in p.from_file for p in rec.parts) and not any(f.function == BOM for f in rec.files)
    assert next(p for p in rec.parts if p.designator == "U1").power == 3.0


def test_add_files_writes_the_new_bom_into_the_stored_parts_and_keeps_powers_and_edits(app, base, tmp_path):
    nobom = tmp_path / "nb"
    shutil.copytree(base, nobom)
    (nobom / "assembly.csv").unlink()
    app.run(nobom, powers={"U1": 3.0})
    rec = app.doc.project.imports[0]
    next(p for p in rec.parts if p.designator == "R1").edits["role"] = "Component"
    assert all("bom" not in p.from_file for p in rec.parts)
    before = snapshot(app.doc)
    app.run(base, "add")
    rec = app.doc.project.imports[0]
    by = {p.designator: p for p in rec.parts}
    assert by["U1"].from_file["bom"]["role"] == "component" and by["D1"].from_file["bom"]["dnp"] is True
    assert by["R1"].edits["role"] == "Component" and by["R1"].from_file["bom"]["role"] == "source"
    after = snapshot(app.doc)
    assert after["masks"] == before["masks"] and after["heaters"] == before["heaters"] and after["parts"] == before["parts"]
    assert any(f.function == BOM for f in rec.files)


def test_a_dnp_part_keeps_the_tick_the_user_gave_it(app, base):
    app.run(base, powers={"D1": 1.0})                                            # the user types a power on a part the BOM marks not fitted
    names = [h.name for h in app.doc.problem.heaters]
    assert names == ["D1"] and next(p for p in app.doc.project.imports[0].parts if p.designator == "D1").from_file["bom"]["dnp"] is True


def test_the_package_round_trip_with_a_bom(app, base, tmp_path):
    app.run(base, powers={"U1": 3.0})
    prj = app.doc.project
    pkg.attach_sources(prj, [("assembly.csv", (base / "assembly.csv").read_bytes(), "bom", BOM, "folder"), ("pos.csv", (base / "pos.csv").read_bytes(), "placement", ims.PLACEMENT, "folder")])
    out = tmp_path / "x.pcbtz"
    pkg.save_package(out, prj, include_sources=True)
    with zipfile.ZipFile(out) as z:
        manifest = json.loads(z.read("manifest.json"))
    assert '"bom"' in json.dumps(manifest)
    app.win.open_file(str(out))
    again = app.doc.project.imports[0]
    assert {p.designator: p.from_file.get("bom") for p in again.parts} == {p.designator: p.from_file.get("bom") for p in prj.imports[0].parts}
    assert any(f.function == BOM for f in again.files)
    import hashlib
    stored = {m.rsplit("/", 1)[-1]: b for m, b in app.doc.project.package.sources.items()}
    assert hashlib.sha256(stored["assembly.csv"]).hexdigest() == hashlib.sha256((base / "assembly.csv").read_bytes()).hexdigest()   # the BOM bytes, not a decoded text


def test_the_re_import_lines_name_the_parts_whose_bom_role_or_mark_changed():
    from pcbthermal.model import ImportPart
    old = [ImportPart(designator="U1", from_file={"bom": {"role": "component", "dnp": False}}), ImportPart(designator="D1", from_file={"bom": {"role": "component", "dnp": False}}),
           ImportPart(designator="R1")]
    new = [ImportPart(designator="U1", from_file={"bom": {"role": "none", "dnp": False}}), ImportPart(designator="D1", from_file={"bom": {"role": "component", "dnp": True}}),
           ImportPart(designator="R1", from_file={"bom": {"role": "source", "dnp": False}})]
    assert ImportSession.bom_changes(old, new) == ["U1: BOM role component -> none (your Role is kept)", "D1: BOM now says not fitted"]


# ---------------------------------------------------------------------------------------------------------------------------------------- review
def test_a_refused_bom_is_read_once_and_its_message_is_in_the_list_at_the_first_refresh(qtbot, base, monkeypatch):
    """!
    @brief Review: a BOM the reader refuses was read again at every call (once per row of step 2, in the GUI thread: 7 reads and 7 s for a refused table of 250 000 rows on four
           parts), and the step 1 list showed its message only from the second refresh while the BOM line already said "see the list".
    @param qtbot pytest-qt fixture.
    @param base Synthetic set with a BOM.
    @param monkeypatch pytest fixture.
    @return None
    """
    from pcbthermal.gerber import bom as bm
    (base / "assembly.csv").write_text("Designator,Comment,Footprint\nR1,1k," + "x" * 200000 + "\n")      # a cell beyond the csv field limit: refused
    calls = []
    real = bm.read_bom
    monkeypatch.setattr(bm, "read_bom", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    w.confirm = lambda *a: True
    w.notify = lambda *a: None
    w.open_path(str(base))
    row = [f.name for f in w.session.files].index("assembly.csv")
    assert "cannot be read" in w.page1.table.item(row, 4).text()
    assert w.page1.bom_label.text().startswith("BOM: no file could be read")
    w.page2.refresh()
    w.page2.refresh()
    w.session.bom_line()
    assert len(calls) == 1


def test_text_from_the_bom_in_the_tooltips_is_escaped(qtbot, base):
    """!
    @brief Review: the part numbers of the BOM (step 2 cells) and the file names in the warnings of the BOM line (step 1) went into tooltips unescaped, and Qt renders a tooltip
           that looks like markup as rich text (the Decisions Log: text from the files in the tooltips is escaped).
    @param qtbot pytest-qt fixture.
    @param base Synthetic set with a BOM.
    @return None
    """
    (base / "assembly.csv").write_text(TABLE.replace(",C1\n", ",<img src=x>\n") + "U1,dup,x,1,,\n")
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    w.confirm = lambda *a: True
    w.notify = lambda *a: None
    w.open_path(str(base))
    tip = w.page1.bom_label.toolTip()
    assert "<img" not in tip and "appear more than once" in tip
    w.page2.refresh()
    t = w.page2.table
    tips = [t.item(k, w.page2.BOM_COL).toolTip() for k in range(t.rowCount()) if t.item(k, w.page2.BOM_COL)]
    assert any("&lt;img src=x&gt;" in x for x in tips) and not any("<img" in x for x in tips)
