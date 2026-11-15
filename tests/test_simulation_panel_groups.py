#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_simulation_panel_groups.py
@brief The grouped Simulation settings: one label column and one field column in every group, a group greyed with its models, the memory lines, the model labels
       and the Auto button with the FEM mesh numbers.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import re

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QApplication

from pcbthermal import memory
from pcbthermal.api import suggest_cell_mm
from pcbthermal.examples import example_board
from pcbthermal.gui import theme as th
from pcbthermal.model import Problem
from tests.test_gui_stress import load, popups, win  # noqa: F401  (fixtures and helpers)

SETS = {"fvm_fem": ("fvm", "fem"), "lumped_analytic": ("lumped", "analytic")}


def _x(widget, panel):
    """!
    @brief The x of the left edge of a widget, in the coordinates of the panel.
    @param widget QWidget.
    @param panel The SolverPanel.
    @return int x in pixels.
    """
    return widget.mapTo(panel, widget.rect().topLeft()).x()


def _first_widget(item):
    """!
    @brief The widget of a grid field, or the first widget of a layout (the cell spin box of the Auto row).
    @param item QWidget or QLayout.
    @return QWidget.
    """
    return item if hasattr(item, "mapTo") else item.itemAt(0).widget()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("case", sorted(SETS))
def test_labels_and_fields_start_at_one_x_in_every_group(win, theme, case):
    """!
    @brief Every visible label at one x, every field of a row with a label at another, the titles at the label x; the panel is no wider than the dock.
    @param win Main window fixture.
    @param theme "light" or "dark".
    @param case Key of SETS.
    """
    if th.current_name() != theme:
        win.toggle_theme()
    load(win, example_board())
    win.doc.set_options(models=SETS[case], cell_mm=1.0)
    QApplication.processEvents()
    sp = win.solver_panel
    labels = {_x(lab, sp) for lab in sp._grid_labels if lab.isVisible()}
    fields = {_x(_first_widget(f), sp) for f, lab in zip(sp._grid_fields, sp._grid_labels) if lab.isVisible()}      # one field per label: the full-width rows are not in the list
    titles = {_x(h["title"], sp) for h in sp._heads}
    assert len(labels) == 1 and len(fields) == 1, (labels, fields)
    assert titles == labels
    assert min(fields) > max(labels)
    assert sp.minimumSizeHint().width() <= 340


def test_a_group_greys_with_its_models_and_says_so_in_words(win):
    """!
    @brief Each group follows its models: title in the muted tone, 'not ticked' in the tag, controls and labels disabled; it comes back when ticked.
    @param win Main window fixture.
    """
    load(win, example_board())
    sp = win.solver_panel
    heads = {h["title"].text(): h for h in sp._heads}
    muted = th.colors(th.current_name())["muted"]
    # (group title, model keys that serve it, controls)
    groups = (("Finite volume (FVM)", ("fvm",), (sp.solver,)), ("Thermal network (LPTN)", ("lumped",), (sp.rings,)), ("Analytical", ("analytic",), (sp.modes, sp.local)),
              ("Finite elements (FEM)", ("fem",), (sp.fem_gap, sp.fem_ref)))
    win.doc.set_options(models=("fdm",))
    QApplication.processEvents()
    for title, _models, controls in groups:
        assert "not ticked" in heads[title]["tag"].text() and muted in heads[title]["title"].styleSheet()
        assert not any(c.isEnabled() for c in controls)
    assert "not ticked" not in heads["Laminate (FVM, FDM)"]["tag"].text() and sp.lam_s.isEnabled() and sp.lam_n.isEnabled()   # the FDM serves the laminate group
    assert "not ticked" not in heads["All models"]["tag"].text()
    for title, models, controls in groups:
        win.doc.set_options(models=models)
        QApplication.processEvents()
        assert "not ticked" not in heads[title]["tag"].text() and all(c.isEnabled() for c in controls)
        assert muted not in heads[title]["title"].styleSheet()
        for other, _m, others in groups:
            if other != title:
                assert "not ticked" in heads[other]["tag"].text() and not any(c.isEnabled() for c in others)
        # the labels of the greyed rows are greyed with them
        assert sp._rows[sp.solver].isEnabled() == (models == ("fvm",))


def test_the_laminate_group_greys_on_a_board_with_a_metal_block_and_the_tooltip_reads_right(win):
    """!
    @brief A board with a metal block does not use the laminate rule: the group is greyed even with the FVM ticked, and the tooltip says it plainly.
    @param win Main window fixture.
    """
    p = example_board()
    p.add_heatsink(1, 50.0, rect=(5, 5, 20, 20), name="Block", thickness_mm=3.0)
    load(win, p)
    win.doc.set_options(models=("fvm",))
    QApplication.processEvents()
    sp = win.solver_panel
    head = next(h for h in sp._heads if h["title"].text().startswith("Laminate"))
    assert "not ticked" in head["tag"].text() and not sp.lam_s.isEnabled() and not sp.lam_n.isEnabled()
    tip = sp.lam_s.toolTip()
    assert "Greyed: not used on a board with a metal block" in tip and "used only by a board with a metal block" not in tip
    load(win, example_board())
    win.doc.set_options(models=("fvm",))
    QApplication.processEvents()
    assert sp.lam_s.isEnabled() and "not ticked" not in head["tag"].text()


def test_accent_text_reaches_4_5_to_1_on_the_dock_and_the_boxes_in_both_themes():
    """!
    @brief The title colour is text: 4.5:1 or more against the dock background and against the white of a box.
    """
    for name in ("light", "dark"):
        c = th.colors(name)
        for ground in ("window", "base"):
            ratio = th.contrast(th.qcolor(c["accent_text"]), th.qcolor(c[ground]))
            assert ratio >= 4.5, (name, ground, ratio)
    assert th.colors("light")["accent_text"] == th.colors("light")["accent_pressed"] and th.colors("dark")["accent_text"] == th.colors("dark")["accent"]


def test_the_memory_lines_are_compact_with_a_dot_and_no_thousands_separator(win):
    """!
    @brief 'FVM: 39052 unknowns · 0.3 of 10.3 GB' with a coloured dot; the label is hidden when no guarded model is ticked.
    @param win Main window fixture.
    """
    load(win, example_board())
    sp = win.solver_panel
    win.doc.set_options(models=("fvm", "fem"), cell_mm=1.0)
    QApplication.processEvents()
    text = re.sub(r"<[^>]+>", "", sp.cells_label.text()).replace("&nbsp;", " ")
    assert re.search(r"● FVM: \d+ unknowns · \d+\.\d of \d+\.\d GB", text), text
    assert "about" not in text and not re.search(r"\d,\d{3}", text)
    assert th.colors(th.current_name())["ok"] in sp.cells_label.text() and sp.cells_label.isVisible()
    win.doc.set_options(models=("lumped", "analytic"))
    QApplication.processEvents()
    assert not sp.cells_label.isVisible()


def test_the_model_labels_have_no_comparison_suffix_and_a_line_separates_the_main_three(win):
    """!
    @brief Labels, order and the separator of the Models box; the three lower tooltips open with the same sentence.
    @param win Main window fixture.
    """
    sp = win.solver_panel
    assert [c.text() for c in sp.cb.values()] == ["Finite volume (FVM), reference", "Thermal network (LPTN)", "Analytical (Fourier series)", "Finite difference (FDM)",
                                                  "3D solid (finite volumes)", "Finite elements (FEM)"]
    lay = sp.cb["fvm"].parentWidget().layout()
    order = [lay.itemAt(i).widget() for i in range(lay.count())]
    assert order.index(sp._separator) == order.index(sp.cb["analytic"]) + 1 and order.index(sp.cb["fdm"]) == order.index(sp._separator) + 1
    assert sp._separator.height() == 1
    for k in ("fdm", "solid3d", "fem"):
        assert sp.cb[k].toolTip().startswith("Off by default; a cross-check of the three models above.")
    assert "comparison" not in " ".join(c.text() + c.toolTip() for c in sp.cb.values()).lower()


def test_auto_counts_the_fem_mesh_numbers(win, monkeypatch):
    """!
    @brief With 24 gap elements and the FEM ticked, Auto proposes a cell whose FEM verdict is not 'refuse' (it used the default mesh numbers before).
    @param win Main window fixture.
    @param monkeypatch pytest fixture.
    """
    monkeypatch.setattr(memory, "ram_bytes", lambda: int(4e9))
    load(win, example_board())
    win.doc.options.memory_fraction = 0.5
    win.doc.set_options(models=("fem",), fem_gap_elements=24, cell_mm=1.0)
    sp = win.solver_panel
    default = suggest_cell_mm(win.doc.problem, models=("fem",), fraction=0.5)
    sp._auto_cell()
    assert sp.cell.value() > default + 0.3                                   # 24 gap elements need a coarser cell than the default mesh
    win.doc.set_options(cell_mm=sp.cell.value())
    assert [v.verdict for v in sp.verdicts()] != ["refuse"]


def test_the_local_corrections_tooltip_says_steady_only(win):
    """!
    @brief The option does not reach the time run, and the tooltip says it.
    @param win Main window fixture.
    """
    assert "Steady run only" in win.solver_panel.local.toolTip()
