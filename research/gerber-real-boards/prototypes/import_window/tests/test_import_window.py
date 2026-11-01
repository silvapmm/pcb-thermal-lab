#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_import_window.py
@brief Tests of the import window prototype: the backend (detection, matching, diff, re-import merge) and the three layouts built offscreen, with a grab of every page in both themes.
@details Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/gerber-real-boards/tests` (the file is found through tests/conftest.py of the investigation; this folder is also collected directly).
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import backend as be  # noqa: E402


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    """!
    @brief The synthetic board folder.
    @param tmp_path_factory pytest factory.
    @return Path
    """
    return be.make_synthetic(tmp_path_factory.mktemp("synth") / "b")


def _record(folder):
    """!
    @brief Read a folder and build the record with a power on U1.
    @param folder Path.
    @return tuple (board, files, parts, record).
    """
    files = be.scan(folder)
    board = be.load_board(files)
    parts, un = be.match_parts(board)
    next(p for p in parts if p["ref"] == "U1").update(use=True, power=1.5, tj=125.0)
    return board, files, parts, be.build_record("t", board, files, parts)


def test_detection_and_match(synth):
    """!
    @brief Functions come from X2, designators from TO.C, the unmatched part has no opening.
    @param synth Fixture.
    @return None
    """
    files = {f["name"]: f for f in be.scan(synth)}
    assert files["F.gbr"]["func"] == "Top copper" and files["edge.gbr"]["func"] == "Board outline / profile" and files["pos.csv"]["func"].startswith("Placement")
    board, _, parts, _ = _record(synth)
    by = {p["ref"]: p for p in parts}
    assert by["U1"]["match"].startswith("matched by designator") and by["R1"]["groups"] == [] and abs(board["w"] - 40.25) < 0.05


def test_check_files_duplicate(synth):
    """!
    @brief Two files with the same function block step 1.
    @param synth Fixture.
    @return None
    """
    files = be.scan(synth)
    next(f for f in files if f["name"] == "B.gbr")["func"] = "Top copper"
    assert any("Two files claim" in p for p in be.check_files(files))


def test_diff_and_reimport(synth):
    """!
    @brief The diff between two imports of the same board where parts were moved, removed and resized is computed, and replace keeps the power of matched parts and orphans the removed ones.
    @param synth Fixture.
    @return None
    """
    _, _, _, rec = _record(synth)
    old = be.demo_previous(rec, seed_refs=["U1", "Q1", "D1"])
    old["parts"] = [dict(p) for p in rec["parts"]]
    old["parts"][0]["polygon"] = [(x + 1.0, y) for x, y in old["parts"][0]["polygon"]]
    old["parts"].append({"ref": "X9", "package": "x", "x": 1.0, "y": 1.0, "side": "top", "use": True, "power_w": 0.2, "tj_max_c": 0.0, "role": "Source", "shape": "box", "shape_user": False,
                         "polygon": [(0, 0), (1, 0), (1, 1), (0, 1)]})
    d = {x["ref"]: x["change"] for x in be.diff_parts(old["parts"], rec["parts"])}
    assert d["X9"] == "removed" and "moved" in d[old["parts"][0]["ref"]]
    res = be.apply_reimport("replace", old, rec)
    kept = {p["ref"]: p for p in res["record"]["parts"]}
    assert res["orphans"] == ["X9"] and kept["X9"]["orphan"] and kept["U1"]["power_w"] == old["parts"][[p["ref"] for p in old["parts"]].index("U1")]["power_w"]
    assert "X9" not in {p["ref"] for p in be.apply_reimport("update", old, rec, remove_refs=["X9"])["record"]["parts"]}


def test_add_files_conflict(synth):
    """!
    @brief Adding files takes only the missing functions and shows a conflict for a changed one.
    @param synth Fixture.
    @return None
    """
    _, _, _, rec = _record(synth)
    old = be.demo_previous(rec)
    kinds = {s["function"]: s["status"] for s in be.classify_sources(old, rec)}
    assert kinds["Placement (pick and place)"] == "added" and kinds["Top copper"] == "changed"
    res = be.apply_reimport("add", old, rec, file_choice={"Top copper": "new"})
    assert {s["function"] for s in res["record"]["sources"]} >= {"Placement (pick and place)"} and len(res["record"]["parts"]) >= len(old["parts"])
    assert any("took the new file" in c for c in res["changes"])


def test_different_board_warned(synth):
    """!
    @brief A record with another outline is reported as a different board.
    @param synth Fixture.
    @return None
    """
    _, _, _, rec = _record(synth)
    other = dict(rec, box=[0, 0, 80, 60])
    same, why = be.same_board(other, rec)
    assert not same and why


@pytest.mark.parametrize("layout", ["hybrid", "tabs", "wizard"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_windows_build_and_grab(synth, tmp_path, layout, theme):
    """!
    @brief Each layout builds offscreen with the synthetic board, shows its three pages, grabs them, selects a part by a click, and imports with the re-import dialog answered by the test.
    @param synth Fixture.
    @param tmp_path pytest folder.
    @param layout Layout key.
    @param theme Theme key.
    @return None
    """
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    import ui
    from pcbthermal.gui import theme as th
    th.fix_number_locale()
    th.apply_theme(app, theme)
    sx = ui.Session(str(tmp_path), tmp_path / "out", "demo")
    sx.open(synth, "synthetic")
    win = ui.create_window(layout, sx, theme, "synthetic")
    win.show()
    app.processEvents()
    win.confirm = lambda t, x: True
    win.notify = lambda t, x: None
    sizes = []
    for i in range(3):
        if layout == "tabs":
            win.tabs.setCurrentIndex(i)
        else:
            win.go(i)
        app.processEvents()
        img = win.grab()
        sizes.append(img.width() * img.height())
        assert img.width() > 500
    page2 = win.pages[1]
    g = sx.board["groups"]["top"][0]
    page2._clicked(g["x"], g["y"], False)
    assert sx.selected is not None
    sx.part(sx.selected)["power"] = 1.0
    sx.part(sx.selected)["use"] = True
    assert win.can_import() and sx.heat_sources()
    win.ask_reimport = lambda dlg: (setattr(dlg, "_seen", dlg.table.rowCount()), True)[1]
    out = win.do_import()
    assert out and out["mode"] in ("replace", "update") and (tmp_path / "out" / f"import_summary_{layout}.json").exists()
    if layout == "hybrid":
        assert win.stepper.states()[2][0] in ("ready", "current", "done")


def test_hybrid_locked_steps(synth, tmp_path):
    """!
    @brief In the hybrid layout, steps 2 and 3 are locked with an explanation while step 1 is incomplete, and Import now is disabled.
    @param synth Fixture.
    @param tmp_path pytest folder.
    @return None
    """
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    import ui
    sx = ui.Session(str(tmp_path), tmp_path / "out", "none")
    sx.open(synth, "synthetic")
    win = ui.create_window("hybrid", sx, "light", "")
    next(f for f in sx.files if f["name"] == "B.gbr")["func"] = "Top copper"
    sx.reload()
    app.processEvents()
    st = win.stepper.states()
    assert st[1][0] == "locked" and "Two files claim" in st[1][1] and not win.early_btn.isEnabled()
    win.go(1)
    assert win.step == 0


def test_side_of_paste_mask_and_silk_from_the_name(tmp_path):
    # Review: the first rule read any stem ending in "b" as the bottom side and missed "B_Paste" (KiCad names without X2) and the Protel extensions
    cases = {"board-B_Paste.gbr": "Solder paste bottom", "board-F_Paste.gbr": "Solder paste top", "board-B_Mask.gbr": "Solder mask bottom", "pasteB.gbr": "Solder paste bottom",
             "pasteF.gbr": "Solder paste top", "paste_bot.gbr": "Solder paste bottom", "top_paste_tab.gbr": "Solder paste top", "bottom-silk.gbr": "Legend (silkscreen) bottom",
             "board.gtp": "Solder paste top", "board.gbp": "Solder paste bottom", "board.gbs": "Solder mask bottom"}
    for name, want in cases.items():
        (tmp_path / name).write_text("%FSLAX46Y46*%\n%MOMM*%\nM02*\n")
        assert be.detect_function(tmp_path / name)[0] == want, name


def test_two_plated_drill_files_are_both_read(synth, tmp_path):
    # Review: the board kept one file per function, so a second plated drill file (vias apart from component holes) was dropped silently
    import shutil
    d = tmp_path / "b2"
    shutil.copytree(synth, d)
    (d / "drill_vias.drl").write_text("M48\n; #@! TF.FileFunction,Plated,1,2,PTH\nMETRIC,TZ\nT1C0.300\n%\nT1\nX30.0Y5.0\nM30\n")
    files = be.scan(d)
    assert sum(f["func"] == "Plated drill" for f in files) == 2 and not be.check_files(files)
    assert len(be.load_board(files)["holes"]) == 3


def test_reimport_applies_the_user_shape_to_the_new_openings(synth):
    # Review: a part whose shape the user chose kept its STORED polygon when the part moved (heat at the old place), and took the new
    # suggested polygon under the old shape name otherwise
    board, files, parts, rec = _record(synth)
    old = {k: v for k, v in rec.items()}
    old["parts"] = [dict(p) for p in rec["parts"]]
    u1 = next(p for p in old["parts"] if p["ref"] == "U1")
    u1.update(shape="hull", shape_user=True, polygon=[(x + 2.0, y) for x, y in u1["polygon"]])     # stored before a layout revision moved it by 2 mm
    merged = {p["ref"]: p for p in be.apply_reimport("update", old, rec)["record"]["parts"]}
    new_u1 = next(p for p in rec["parts"] if p["ref"] == "U1")
    assert merged["U1"]["shape"] == "hull" and merged["U1"]["polygon"] == new_u1["shapes"]["hull"]


def test_diff_compares_centres_in_one_frame():
    # Review: a part with openings in one import and none in the other was compared opening centre against placement origin
    a = {"ref": "U1", "x": 10.0, "y": 10.0, "polygon": [(11.0, 9.0), (14.0, 9.0), (14.0, 11.0), (11.0, 11.0)]}
    b = {"ref": "U1", "x": 10.0, "y": 10.0, "polygon": None}
    assert be.diff_parts([a], [b])[0]["change"] == "kept"


def test_archive_that_expands_too_much_is_refused(tmp_path, monkeypatch):
    # Review: the declared sizes of an archive are checked before anything is written
    import zipfile
    z = tmp_path / "big.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        f.writestr("F.gbr", "0" * 2_000_000)
    monkeypatch.setattr(be, "MAX_UNZIPPED", 1_000_000)
    with pytest.raises(ValueError, match="expands"):
        be.open_source(z, tmp_path / "w")
    with zipfile.ZipFile(tmp_path / "evil.zip", "w") as f:
        f.writestr("../evil.txt", "x")
    with pytest.raises(ValueError, match="unsafe"):
        be.open_source(tmp_path / "evil.zip", tmp_path / "w2")
