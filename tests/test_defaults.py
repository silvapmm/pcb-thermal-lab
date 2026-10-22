"""!
@file test_defaults.py
@brief The defaults and libraries in JSON: the shipped file, the user file that overrides it, the diff that is saved, and what the program does with them.
"""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from pcbthermal import defaults, model
from pcbthermal.api import default_options
from pcbthermal.model import DIELECTRICS, INTERFACES, METALS, PACKAGE_THETA, VIA_FILLS, new_problem, via_fill_k


def user_path():
    return defaults.user_file()


def test_shipped_file_has_every_library_and_the_model_uses_it():
    d = defaults.shipped()
    assert set(d["libraries"]) == set(defaults.LIBRARIES)
    assert [e[0] for e in VIA_FILLS] == [e["name"] for e in d["libraries"]["via_fills"]] == ["Open", "Epoxy resin", "Conductive paste", "Copper"]
    assert METALS[0][0] == "Aluminium" and len(DIELECTRICS) == 7 and len(INTERFACES) == 5 and len(PACKAGE_THETA) == 8
    assert via_fill_k("Epoxy resin") == 0.3 and via_fill_k("nothing", 7.0) == 7.0
    assert not defaults.has_user_file() and defaults.diff_text() == ""


def test_defaults_of_a_new_board_and_options_are_the_old_ones_without_a_user_file():
    p = new_problem()
    b = p.board
    assert (b.width, b.height, b.layers, b.ambient, b.h_top, b.h_bottom, b.h_side) == (0.1, 0.08, 2, 25.0, 10.0, 15.0, 10.0)
    assert b.via_plating == pytest.approx(25e-6) and b.materials.k_copper == 385.0
    o = default_options()
    assert o.models == ("fvm", "lumped", "analytic") and o.cell_mm == 1.0 and o.hotspot_c == 100.0


def test_user_file_overrides_by_name_adds_removes_and_only_differences_are_saved():
    full = defaults.load()
    full["libraries"]["via_fills"][1]["k_w_per_mk"] = 0.5                                   # Change a shipped entry
    full["libraries"]["via_fills"].append({"name": "My paste", "k_w_per_mk": 12.0, "note": "from the supplier"})     # Add one
    full["libraries"]["metals"] = [m for m in full["libraries"]["metals"] if m["name"] != "Brass"]     # Hide one
    full["new_board"]["ambient_c"] = 40.0
    full["solver"]["models"] = ["fvm", "fdm"]
    written = defaults.save_user(full)
    assert set(written) == {"_comment", "libraries", "removed", "new_board", "solver"}
    assert [e["name"] for e in written["libraries"]["via_fills"]] == ["Epoxy resin", "My paste"]      # Only what differs
    assert written["removed"] == {"metals": ["Brass"]} and written["new_board"] == {"ambient_c": 40.0}
    assert defaults.has_user_file() and "3 in" not in defaults.diff_text() and "removed from metals" in defaults.diff_text()
    model.reload_libraries()
    assert via_fill_k("Epoxy resin") == 0.5 and via_fill_k("My paste") == 12.0
    assert "Brass" not in [m[0] for m in METALS] and len(METALS) == 4
    assert new_problem().board.ambient == 40.0
    assert default_options().models == ("fvm", "fdm")
    # Saving the shipped values again removes the file; so does reset
    defaults.save_user(defaults.shipped())
    assert not defaults.has_user_file()
    defaults.save_user(full)
    defaults.reset_user()
    model.reload_libraries()
    assert not defaults.has_user_file() and via_fill_k("Epoxy resin") == 0.3 and len(METALS) == 5


def test_a_broken_user_file_is_ignored_not_fatal():
    os.makedirs(defaults.user_dir(), exist_ok=True)
    with open(user_path(), "w") as fh:
        fh.write("{ not json")
    assert defaults.user_overrides() == {} and defaults.load()["new_board"]["ambient_c"] == 25.0
    with open(user_path(), "w") as fh:
        json.dump({"solver": {"models": ["nonsense"], "cell_mm": 999}}, fh)
    o = default_options()                                                                    # A bad value falls back to the built-in settings
    assert o.models == ("fvm", "lumped", "analytic") and o.cell_mm == 1.0


def test_new_elements_use_the_defaults(qtbot, tmp_path):
    from PySide6.QtCore import QSettings
    from pcbthermal.gui.document import Document
    full = defaults.load()
    full["new_elements"].update(heater_power_w=2.5, via_diameter_mm=0.4, via_fill="Epoxy resin", heatsink_h_extra=33.0, zone_fill=0.7)
    full["new_board"].update(width_mm=70.0, height_mm=50.0, layers=4)
    defaults.save_user(full)
    doc = Document()
    assert (doc.problem.board.width, doc.problem.board.height, doc.problem.board.layers) == (0.07, 0.05, 4)
    doc.add_shape("heater", 0, [[5, 5], [10, 5], [10, 10], [5, 10]])
    doc.add_shape("zone", 0, [[5, 5], [10, 5], [10, 10], [5, 10]])
    doc.add_shape("heatsink", 0, [[15, 5], [20, 5], [20, 10], [15, 10]])
    i = doc.add_via(30.0, 20.0)
    p = doc.problem
    assert p.heaters[0].power == 2.5 and p.zones[0].fill == 0.7 and p.heatsinks[0].h_extra == 33.0
    assert p.vias[i].diameter == pytest.approx(0.4e-3) and p.vias[i].fill == "Epoxy resin" and p.vias[i].fill_k == 0.3


def test_preferences_window_edits_saves_resets_and_the_status_bar_says_so(qtbot, tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QAbstractSpinBox, QMessageBox
    from pcbthermal.gui.document import Document
    from pcbthermal.gui.main_window import MainWindow
    from pcbthermal.gui.preferences import PreferencesDialog
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.show()
    assert win.defaults_label.text() == ""                                               # Shipped defaults: nothing to say
    d = PreferencesDialog(win)
    qtbot.addWidget(d)
    table, cols = d.tables["via_fills"]
    assert cols == ["name", "k_w_per_mk", "note"] and table.rowCount() == 4
    table.item(1, 1).setText("0.45")                                                     # Epoxy resin: 0.45 W/mK
    d._add_row("via_fills")
    assert table.rowCount() == 5 and len(d.data["libraries"]["via_fills"]) == 5
    d.widgets[("new_board", "ambient_c")].setValue(33.0)
    d.save()
    assert defaults.has_user_file() and via_fill_k("Epoxy resin") == 0.45 and defaults.value("new_board", "ambient_c") == 33.0
    assert "New entry" in [e[0] for e in VIA_FILLS]
    win._show_defaults_state()
    assert win.defaults_label.text() == "Custom defaults" and "via_fills" in win.defaults_label.toolTip()
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    d.reset()
    assert not defaults.has_user_file() and via_fill_k("Epoxy resin") == 0.3 and table.rowCount() == 4
    assert d.widgets[("new_board", "ambient_c")].value() == 25.0
    # Starting the program again with a user file in place says so
    full = defaults.load()
    full["new_board"]["ambient_c"] = 31.0
    defaults.save_user(full)
    win2 = MainWindow(Document(), QSettings(str(tmp_path / "t2.ini"), QSettings.IniFormat))
    qtbot.addWidget(win2)
    qtbot.waitUntil(lambda: "Custom defaults in use" in win2.statusBar().currentMessage(), timeout=2000)
    assert win2.defaults_label.text() == "Custom defaults"
    assert win2.doc.problem.board.ambient == 31.0
    from tests.test_tooltips import missing
    assert not missing(d, "preferences")                                                # Every control of the window explains itself
