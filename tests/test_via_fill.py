"""!
@file test_via_fill.py
@brief What fills a via barrel (open, epoxy resin, conductive paste, electroplated copper): the equivalent area, the models, the file and the form.
"""

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.model import VIA_FILLS, Via, problem_from_dict, problem_to_dict

K_CU, PLATING = 385.0, 25e-6


def test_equivalent_area_of_every_fill():
    r, r_in = 0.15e-3, 0.125e-3
    ring, core = math.pi * (r * r - r_in * r_in), math.pi * r_in * r_in
    assert Via(0, 0, 0.3e-3).thermal_area(PLATING, K_CU) == pytest.approx(ring)                              # Open barrel
    assert Via(0, 0, 0.3e-3, False, "", 0.3).thermal_area(PLATING, K_CU) == pytest.approx(ring + 0.3 / K_CU * core)
    assert Via(0, 0, 0.3e-3, False, "", 8.0).thermal_area(PLATING, K_CU) == pytest.approx(ring + 8.0 / K_CU * core)
    assert Via(0, 0, 0.3e-3, True).thermal_area(PLATING, K_CU) == pytest.approx(math.pi * r * r)             # The legacy copper flag: the whole disc
    assert Via(0, 0, 0.3e-3, False, "", 385.0).thermal_area(PLATING, K_CU) == pytest.approx(math.pi * r * r)  # The library's Copper fill (385 W/mK): the same disc
    # Resin is within 0.2 % of the open barrel, the paste about 5 % above it, the copper 3.3 times
    ring_ratio = [Via(0, 0, 0.3e-3, False, "", k).thermal_area(PLATING, K_CU) / ring for _, k, _ in VIA_FILLS]
    assert ring_ratio[1] < 1.002 and 1.03 < ring_ratio[2] < 1.07 and 3.2 < ring_ratio[3] < 3.4


def test_the_models_order_the_fills_and_agree_on_the_resin():
    temps = {}
    for label, k, _ in VIA_FILLS:
        p = example_board()
        for v in p.vias:
            v.filled, v.fill_k = False, k
        temps[label] = {m: simulate(p, SolverOptions(models=(m,), cell_mm=1.0)).results[m].t_max for m in ("fvm", "fdm", "solid3d", "lumped", "analytic")}
    open_, resin, paste, copper = (temps[x[0]] for x in VIA_FILLS)
    for m in open_:
        assert abs(resin[m] - open_[m]) < 0.05                                       # An epoxy plug is no heat path
        assert open_[m] >= paste[m] > copper[m]                                      # Paste a little, copper a lot
    assert open_["fvm"] - copper["fvm"] > 2.0                                        # A copper fill cools the example board by several kelvin


def test_file_round_trip_and_validation():
    p = Problem.new(50, 40, 2).add_zone(1, rect=(0, 0, 50, 40)).add_heater(1, 1.0, rect=(20, 15, 30, 25))
    p.add_via(25, 20, 0.3, fill_k=0.3, fill="Epoxy resin").add_via(26, 20, 0.3, filled=True).add_via(27, 20, 0.3)
    q = problem_from_dict(problem_to_dict(p))
    assert [(v.filled, v.fill_k, v.fill) for v in q.vias] == [(False, 0.3, "Epoxy resin"), (True, 0.0, ""), (False, 0.0, "")]
    assert "fill_k_w_per_mk" not in problem_to_dict(p)["vias"][2]                    # An open via writes nothing new (old files unchanged)
    old = problem_to_dict(p)
    for v in old["vias"]:
        v.pop("fill_k_w_per_mk", None)
    assert all(v.fill_k == 0.0 for v in problem_from_dict(old).vias)


def test_fill_combo_and_typical_value_in_the_inspector(qtbot, tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QLabel
    from pcbthermal.gui.document import Document
    from pcbthermal.gui.main_window import MainWindow
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.show()
    win._load_problem(example_board(), "vias")

    def form():
        win.canvas.set_selection([("via", 0)])
        win._on_canvas_selection([("via", 0)])
        f = win.inspector.form_host
        combo = next(c for c in f.findChildren(QComboBox) if c.itemText(0) == "Open")
        spin = next(s for s in f.findChildren(QAbstractSpinBox) if s.toolTip().startswith("Conductivity of the fill"))
        texts = [l.text() for l in f.findChildren(QLabel) if l.text().startswith("Typical") or l.text() == "Custom value."]
        return combo, spin, texts

    combo, spin, texts = form()
    assert [combo.itemText(i) for i in range(combo.count())] == [x[0] for x in VIA_FILLS] == ["Open", "Epoxy resin", "Conductive paste", "Copper"]   # Names only
    assert texts and texts[0].startswith("Typical: 0 W/mK")
    combo.setCurrentIndex(1)                                                       # Choosing a name puts its typical value in the via ...
    v = win.doc.problem.vias[0]
    assert v.fill == "Epoxy resin" and v.fill_k == 0.3 and not v.filled
    combo, spin, texts = form()
    assert combo.currentText() == "Epoxy resin" and spin.value() == 0.3 and texts[0].startswith("Typical: 0.3 W/mK")
    spin.setValue(1.2)                                                             # ... and the value can be changed for this via
    assert win.doc.problem.vias[0].fill_k == 1.2 and win.doc.problem.vias[0].fill == "Epoxy resin"
    combo, spin, texts = form()
    combo.setCurrentIndex(3)
    assert win.doc.problem.vias[0].fill_k == 385.0 and win.doc.problem.vias[0].fill == "Copper"
