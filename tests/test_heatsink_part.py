"""!
@file test_heatsink_part.py
@brief Finned metal blocks, the contact area of a part, gaps made of several sheets (prepreg and core), and the controls added with them.
"""

import json
import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.blocks import exposed_h, fin_ratio
from pcbthermal.checks import check_problem
from pcbthermal.model import Dielectric, combine_sheets, problem_from_dict, problem_to_dict, stackup_template


def board(fins=None, thickness=3.0, k=204.0):
    """!
    @brief A 60 x 40 mm two-layer board with a heater and a metal block on the bottom face.
    @param fins None or (height, thickness, pitch) in mm.
    @param thickness Block thickness in mm.
    @param k Block conductivity in W/mK.
    @return Problem.
    """
    p = Problem.new(60, 40, 2)
    p.board.h_mode, p.board.h_top, p.board.h_bottom = "manual", 10.0, 10.0
    p.add_zone(1, rect=(1, 1, 59, 39))
    p.add_zone(2, rect=(1, 1, 59, 39))
    p.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="U1")
    kw = {} if fins is None else dict(fin_height_mm=fins[0], fin_thickness_mm=fins[1], fin_pitch_mm=fins[2])
    p.add_heatsink(2, 0.0, rect=(10, 5, 50, 35), thickness_mm=thickness, k=k, contact_r=5e-5, **kw)
    return p


def test_fin_ratio_follows_the_textbook_formula():
    p = board((20.0, 1.5, 8.0))
    s = p.heatsinks[0]
    t, pitch, hc = 1.5e-3, 8e-3, 20e-3 + 0.75e-3
    for h in (5.0, 10.0, 50.0):
        m = math.sqrt(2 * h / (204.0 * t))
        eta = math.tanh(m * hc) / (m * hc)
        assert fin_ratio(h, s) == pytest.approx((1 - t / pitch) + 2 * hc * eta / pitch, rel=1e-12)
    assert exposed_h(s, 10.0) == pytest.approx(10.0 * fin_ratio(10.0, s))
    assert fin_ratio(10.0, board().heatsinks[0]) == 1.0                         # A plain plate
    # An ideal fin material has efficiency 1; a poor conductor wastes the tall fin
    assert fin_ratio(10.0, board((20.0, 1.5, 8.0), k=1e6).heatsinks[0]) == pytest.approx((1 - t / pitch) + 2 * hc / pitch, rel=1e-3)
    assert fin_ratio(10.0, board((20.0, 1.5, 8.0), k=1.0).heatsinks[0]) < 0.5 * fin_ratio(10.0, s)
    assert fin_ratio(10.0, s) > 1.0


@pytest.mark.parametrize("model", ["fvm", "fdm", "solid3d", "lumped", "analytic"])
def test_fins_cool_more_than_the_plain_plate_in_every_model(model):
    plain = simulate(board(), SolverOptions(models=(model,), cell_mm=1.0)).results[model].t_max
    finned = simulate(board((15.0, 1.5, 8.0)), SolverOptions(models=(model,), cell_mm=1.0)).results[model].t_max
    assert finned < plain - 1.0, (model, plain, finned)


def test_models_agree_on_a_finned_block_and_the_energy_balance_closes():
    rises = {}
    for m in ("fvm", "fdm", "solid3d"):
        r = simulate(board((15.0, 1.5, 8.0)), SolverOptions(models=(m,), cell_mm=1.0)).results[m]
        assert abs(r.balance_error) < 1e-9
        rises[m] = r.t_max - 25.0
    assert abs(rises["fdm"] - rises["fvm"]) < 0.05 * rises["fvm"] and abs(rises["solid3d"] - rises["fvm"]) < 0.05 * rises["fvm"], rises


def test_fins_json_validation_and_the_choke_warning():
    p = board((15.0, 1.5, 8.0))
    q = problem_from_dict(problem_to_dict(p))
    s = q.heatsinks[0]
    assert (s.fin_height, s.fin_thickness, s.fin_pitch) == pytest.approx((15e-3, 1.5e-3, 8e-3)) and s.has_fins()
    assert "fin_height_mm" not in problem_to_dict(board())["heatsinks"][0]
    with pytest.raises(ValueError):
        board((15.0, 1.5, 1.0)).validate()                                      # Pitch smaller than the fin thickness
    tight = board((15.0, 1.5, 4.0))
    assert any("fins" in w and "choke" in w for w in check_problem(tight))
    assert not any("choke" in w for w in check_problem(board((15.0, 1.5, 12.0))))
    tight.board.air_speed = 2.0                                                  # Forced air gets through narrow channels
    assert not any("choke" in w for w in check_problem(tight))


def test_contact_area_of_a_part_scales_the_interface_resistance():
    p = Problem.new(60, 40, 2)
    p.board.h_mode, p.board.h_top, p.board.h_bottom = "manual", 10.0, 10.0
    p.add_zone(1, rect=(1, 1, 59, 39))
    p.add_zone(2, rect=(1, 1, 59, 39))
    p.add_heater(1, 2.0, rect=(25, 15, 31, 21), theta=3.0, theta_jc_top=10.0, theta_sa=5.0, interface=1.0)
    h = p.heaters[0]
    area_cm2 = 0.36
    assert h.top_resistance() == pytest.approx(10.0 + 1.0 / area_cm2 + 5.0)
    h.contact_area = 4.0e-4                                                      # A 4 cm2 lid on a 0.36 cm2 footprint
    assert h.top_resistance() == pytest.approx(10.0 + 1.0 / 4.0 + 5.0)
    q = problem_from_dict(problem_to_dict(p))
    assert q.heaters[0].contact_area == pytest.approx(4.0e-4) and q.heaters[0].top_resistance() == pytest.approx(h.top_resistance())
    row = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).heater_rows()[0]
    assert row["r_top"] == pytest.approx(h.top_resistance()) and row["power_top_w"] > 0
    with pytest.raises(ValueError):
        p.heaters[0].contact_area = -1.0
        p.validate()


def test_gap_of_several_sheets_is_series_through_and_parallel_in_plane():
    sheets = [{"thickness_um": 100, "material": "FR-4 (standard)"}, {"thickness_um": 400, "material": "Metal-core dielectric (2 W/mK)"}]
    d = combine_sheets(sheets)
    assert d.thickness == pytest.approx(500e-6)
    assert d.k_through == pytest.approx(500e-6 / (100e-6 / 0.3 + 400e-6 / 2.0))   # Resistances add
    assert d.k_inplane == pytest.approx((100e-6 * 0.9 + 400e-6 * 2.0) / 500e-6)   # Conductances add
    assert d.rho == pytest.approx((100e-6 * 1850 + 400e-6 * 2300) / 500e-6)
    one = combine_sheets([{"thickness_um": 300, "material": "FR-4 (standard)"}])
    assert (one.k_through, one.k_inplane, one.rho, one.cp) == pytest.approx((0.3, 0.9, 1850.0, 900.0))
    with pytest.raises(ValueError):
        combine_sheets([])
    with pytest.raises(ValueError):
        combine_sheets([{"thickness_um": 0, "material": "FR-4 (standard)"}])


def test_template_with_sheets_loads_and_two_equal_plies_equal_one_sheet(tmp_path):
    data = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pcbthermal", "data", "stackups.json"), encoding="utf-8"))
    t2 = data["templates"]["2"]
    t2["dielectrics"] = [{"kind": "core", "sheets": [{"thickness_um": 765, "material": "FR-4 (standard)"}, {"thickness_um": 765, "material": "FR-4 (standard)"}]}]
    f = tmp_path / "sheets.json"
    f.write_text(json.dumps(data))
    p = Problem.new(40, 30, 2)
    p.board.make_advanced()
    p.board.apply_template(str(f))
    ref = Problem.new(40, 30, 2).board
    ref.make_advanced()
    ref.apply_template()
    assert p.board.dielectrics[0].thickness == pytest.approx(ref.dielectrics[0].thickness)
    assert p.board.dielectrics[0].k_through == pytest.approx(ref.dielectrics[0].k_through)
    assert stackup_template(2, str(f))["total_thickness_um"] == pytest.approx(1600.0)


def test_gui_cooling_model_fins_body_helper_and_contact_area(tmp_path, qtbot, monkeypatch):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QMessageBox
    from pcbthermal.examples import example_board
    from pcbthermal.gui.document import Document
    from pcbthermal.gui.main_window import MainWindow
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Discard)
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.show()
    win._load_problem(example_board(), "t")
    win.layer_combo.setCurrentIndex(3)                                                     # The heatsink is on the bottom layer
    win.canvas.set_selection([("heatsink", 0)])
    win._on_canvas_selection([("heatsink", 0)])

    def spins():
        return win.inspector.form_host.findChildren(QAbstractSpinBox)

    def mode_combo():
        return next(c for c in win.inspector.form_host.findChildren(QComboBox) if c.itemText(0).startswith("Coefficient"))

    assert not win.doc.problem.heatsinks[0].is_block()
    assert not any(s.toolTip().startswith("Height of the plate fins") for s in spins())      # Fins only exist in block mode
    mode_combo().setCurrentIndex(1)                                                        # Metal block: the program computes it
    assert win.doc.problem.heatsinks[0].thickness == pytest.approx(3e-3)
    qtbot.wait(50)                                                                         # The form is rebuilt with the block fields
    fin_h = next(s for s in spins() if s.toolTip().startswith("Height of the plate fins"))
    fin_t = next(s for s in spins() if s.toolTip().startswith("Thickness of one fin"))
    fin_p = next(s for s in spins() if s.toolTip().startswith("Distance between the axes"))
    fin_h.setValue(15.0)
    next(s for s in spins() if s.toolTip().startswith("Thickness of one fin")).setValue(1.5)
    next(s for s in spins() if s.toolTip().startswith("Distance between the axes")).setValue(9.0)
    hs = win.doc.problem.heatsinks[0]
    assert hs.has_fins() and hs.fin_height == pytest.approx(15e-3) and hs.fin_pitch == pytest.approx(9e-3)
    sim = simulate(win.doc.problem, SolverOptions(models=("fvm",), cell_mm=2.0))
    assert abs(sim.reference.balance_error) < 1e-9
    mode_combo().setCurrentIndex(0)                                                        # Back to a coefficient
    assert not win.doc.problem.heatsinks[0].is_block()
    qtbot.wait(50)
    # The part: contact area and the body helper
    win.layer_combo.setCurrentIndex(0)
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    ca = next(s for s in spins() if s.toolTip().startswith("Area of the package top"))
    ca.setValue(900.0)
    assert win.doc.problem.heaters[0].contact_area == pytest.approx(9e-4)
    body = next(s for s in spins() if s.toolTip().startswith("Estimate θJC(top)"))
    body.setValue(1.0)                                                                     # 1 mm of mould over a 9 cm2 contact
    assert win.doc.problem.heaters[0].theta_jc_top == pytest.approx(1e-3 / (0.9 * 9e-4), rel=1e-2)
