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
