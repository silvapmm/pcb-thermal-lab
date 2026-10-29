#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_templates.py
@brief Typical stack-up templates (JSON), board orientation, rounded outlines, and the controls added with them.
"""

import json
import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.geometry import polygon_area, polygon_is_simple, rounded_rectangle
from pcbthermal.model import DIELECTRICS, STACKUP_FILE, load_stackup_templates, stackup_template


def test_template_file_is_consistent_and_every_layer_count_has_a_template():
    data = load_stackup_templates()
    assert data["notes"] and data["sources"] and data["templates"]
    names = {d[0] for d in DIELECTRICS}
    for key, t in data["templates"].items():
        n = int(key)
        assert len(t["copper_um"]) == n
        assert all(c > 0 for c in t["copper_um"]) and t["copper_um"][0] == t["copper_um"][-1] == 35      # Outer layers 1 oz finished
        for d in t["dielectrics"]:
            assert d["material"] in names and d["thickness_um"] > 0 and d["kind"] in ("core", "prepreg")
        total = t.get("total_thickness_um") or sum(t["copper_um"]) + sum(d["thickness_um"] for d in t["dielectrics"])
        assert 1500 <= total <= 2500                                    # A real board thickness
        if t["dielectrics"]:                                            # Symmetric build: the same stack from the top and from the bottom
            assert [d["thickness_um"] for d in t["dielectrics"]] == [d["thickness_um"] for d in reversed(t["dielectrics"])]
    for n in range(1, 13):
        t = stackup_template(n)
        assert len(t["copper_um"]) == n and (t["mode"] == "simple" or len(t["dielectrics"]) == n - 1) and 1500 <= t["total_thickness_um"] <= 2500


def test_apply_template_advanced_simple_and_a_user_file(tmp_path):
    p = Problem.new(50, 50, 4)
    b = p.board
    b.make_advanced()
    t = b.apply_template()
    assert b.is_advanced() and len(b.dielectrics) == 3 and "JLC" in t["name"]
    assert b.copper_thickness == pytest.approx([35e-6, 15.2e-6, 15.2e-6, 35e-6])
    assert b.dielectrics[1].thickness == pytest.approx(1065e-6) and b.total_thickness() == pytest.approx(1586.2e-6)
    p.validate()
    s = Problem.new(50, 50, 4).board
    s.apply_template()
    assert not s.is_advanced() and s.thickness == pytest.approx(1586.2e-6) and s.copper_thickness == [35e-6] * 4
    # The file is the place to change the defaults
    custom = json.load(open(STACKUP_FILE, encoding="utf-8"))
    custom["templates"]["4"]["dielectrics"][1]["thickness_um"] = 800
    f = tmp_path / "mine.json"
    f.write_text(json.dumps(custom))
    b.apply_template(str(f))
    assert b.dielectrics[1].thickness == pytest.approx(800e-6)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"templates": {"4": {"copper_um": [35, 35], "mode": "advanced", "dielectrics": []}}}))
    with pytest.raises(ValueError):
        load_stackup_templates(str(bad))


def test_every_template_runs_in_every_model():
    for n in (2, 6, 8):
        p = Problem.new(40, 30, n)
        p.board.h_mode, p.board.h_top, p.board.h_bottom = "manual", 12.0, 12.0
        for l in range(1, n + 1):
            p.add_zone(l, rect=(1, 1, 39, 29))
        p.add_heater(1, 2.0, rect=(18, 13, 22, 17))
        p.board.make_advanced()
        p.board.apply_template()
        sim = simulate(p, SolverOptions(models=("fvm", "fdm", "solid3d", "lumped", "analytic"), cell_mm=2.0))
        rise = {m: r.t_max - 25.0 for m, r in sim.results.items()}
        assert max(rise.values()) < 1.5 * rise["fvm"] and min(rise.values()) > 0.6 * rise["fvm"], (n, rise)


def test_rounded_rectangle_is_a_valid_polygon_and_the_curve_converges():
    pts = rounded_rectangle(60.0, 40.0, 8.0)
    assert polygon_is_simple(pts) and len(pts) == 36
    exact = 60 * 40 - (4 - math.pi) * 8.0 ** 2                          # The rectangle minus the four corner pieces
    assert polygon_area(pts) == pytest.approx(exact, rel=0.01)
    assert polygon_area(rounded_rectangle(60.0, 40.0, 8.0, 32)) == pytest.approx(exact, rel=1e-3)
    assert min(np.array(pts).min(axis=0)) >= -1e-9 and np.array(pts)[:, 0].max() <= 60 + 1e-9
    # A heater on a board with rounded corners: the temperature changes little with the number of edges of the arc
    rises = []
    for seg in (4, 8, 16):
        p = Problem.new(60, 40, 2)
        p.board.h_mode, p.board.h_top, p.board.h_bottom = "manual", 12.0, 12.0
        p.add_zone(1, rect=(1, 1, 59, 39)); p.add_zone(2, rect=(1, 1, 59, 39))
        p.add_heater(1, 2.0, rect=(2, 2, 8, 8))                         # Near a rounded corner
        p.set_outline(rounded_rectangle(60.0, 40.0, 12.0, seg))
        rises.append(simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).reference.t_max - 25.0)
    assert abs(rises[2] - rises[1]) < 0.01 * rises[1] and abs(rises[1] - rises[0]) < 0.03 * rises[0]


def test_gui_template_on_layer_change_interface_preset_heatsink_helper_and_subdivide(tmp_path, qtbot, monkeypatch):
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QMessageBox
    from pcbthermal.examples import example_board
    from pcbthermal.gui.document import Document
    from pcbthermal.gui.main_window import MainWindow
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Discard)
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.show()
    win._load_problem(example_board(), "t")
    page, bp = win.stackup_page, win.board_panel
    page.mode.setCurrentIndex(1)
    for n, total in ((6, 1600.0), (8, 1600.1), (10, 2000.0), (2, 1600.0)):
        bp.layers.setValue(n)
        b = win.doc.problem.board
        assert len(b.dielectrics) == n - 1 and b.total_thickness() * 1e6 == pytest.approx(total, abs=0.2)
        assert b.copper_thickness[0] == pytest.approx(35e-6) and (n == 2 or b.copper_thickness[1] == pytest.approx(15.2e-6))
    win.doc.problem.board.dielectrics[0].thickness = 5e-4                # Edit, then go back to the template with the button
    page.typical.click()
    assert win.doc.problem.board.dielectrics[0].thickness == pytest.approx(1530e-6)
    win.doc.stack.undo()
    assert win.doc.problem.board.dielectrics[0].thickness == pytest.approx(5e-4)
    # Orientation: only horizontal (layer 1 faces up) and vertical
    assert [bp.orientation.itemData(i) for i in range(bp.orientation.count())] == ["horizontal", "vertical"]
    bp.orientation.setCurrentIndex(1)
    assert win.doc.problem.board.orientation == "vertical"
    # Part: interface material preset fills the interface (the top-path boxes show once the part has a heatsink resistance)
    win.doc.set_props("heater", 0, theta=3.0, theta_sa=10.0)
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    form = win.inspector.form_host
    preset = next(c for c in form.findChildren(QComboBox) if c.itemText(0).startswith("Interface material"))
    preset.setCurrentIndex(preset.findText("Direct contact", Qt.MatchStartsWith))             # No material: zero resistance and no sheet
    h0 = win.doc.problem.heaters[0]
    assert h0.interface == 0.0 and h0.pad_thickness == 0.0 and h0.pad_k == 0.0
    form = win.inspector.form_host
    preset = next(c for c in form.findChildren(QComboBox) if c.itemText(0).startswith("Interface material"))
    preset.setCurrentIndex(4)
    assert win.doc.problem.heaters[0].interface == pytest.approx(1.667, abs=0.01)
    # Heatsink: theta_SA from the datasheet sets the extra h
    win.canvas.set_selection([("heatsink", 0)])
    win._on_canvas_selection([("heatsink", 0)])
    hs = win.doc.problem.heatsinks[0]
    area = polygon_area(hs.polygon)
    how = next(c for c in win.inspector.form_host.findChildren(QComboBox) if c.itemText(0).startswith("Heat transfer coefficient"))
    how.setCurrentIndex(1)                                                                     # Input as θSA instead of h: the form is rebuilt with the θSA field
    spin = next(s for s in win.inspector.form_host.findChildren(QAbstractSpinBox) if s.toolTip().startswith("Heatsink resistance to ambient"))
    spin.setValue(4.0)
    assert win.doc.problem.heatsinks[0].h_extra == pytest.approx(1.0 / (4.0 * area), rel=1e-3)
    win._on_canvas_selection([("heatsink", 0)])                                                # The heatsink is on a layer the canvas is not showing: select it again for the inspector
    how = next(c for c in win.inspector.form_host.findChildren(QComboBox) if c.itemText(0).startswith("Heat transfer coefficient"))
    how.setCurrentIndex(0)                                                                     # Back to h: it shows the same coefficient
    h_spin = next(s for s in win.inspector.form_host.findChildren(QAbstractSpinBox) if s.suffix().strip() == "W/m²K")
    assert h_spin.value() == pytest.approx(win.doc.problem.heatsinks[0].h_extra, rel=1e-2)
    # Outline: rounded preset and subdivide
    bp.preset.setCurrentIndex(bp.preset.findData("Rounded corners"))
    n0 = len(win.doc.problem.board.outline)
    assert n0 == 36
    bp.v_sub.click()
    assert len(win.doc.problem.board.outline) == 2 * n0
    win.doc.problem.validate()
