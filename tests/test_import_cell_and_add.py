#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_import_cell_and_add.py
@brief Typing a new cell size for an imported board raises nothing, and Add with the files of another board takes no part of it.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from tests.test_reimport_different_board import other_board
from tests.test_reimport_matrix import app, base  # noqa: F401  (fixtures)
from tests.test_import_apply_flow import board_dir, win, _drive  # noqa: F401  (fixtures)


def test_typing_a_cell_on_an_imported_board_raises_nothing(win, board_dir, monkeypatch, qtbot):
    """!
    @brief Import a board, then set several cell sizes in the Simulation settings box.
    @param win Main window fixture.
    @param board_dir Synthetic set.
    @param monkeypatch pytest fixture.
    @param qtbot pytest-qt fixture.
    """
    _drive(monkeypatch, board_dir, powers={"U1": 3.0})
    win.a_import.trigger()
    panel = win.solver_panel
    for k in ("fdm", "solid3d", "lumped", "analytic"):
        panel.cb[k].setChecked(True)
    for v in (0.5, 0.2, 3.0, 0.1, 20.0, 1.0, 0.37):
        panel.cell.setValue(v)
        qtbot.wait(20)
    # A new board size typed in the Board settings box (the imported masks keep their extent)
    bp = win.board_panel
    for w in (0.05, 0.03, 0.04):
        bp.width.setValue(w * 1000)
        qtbot.wait(20)
    assert panel.cells_label.text()
    assert not bp.width.isEnabled() and not bp.height.isEnabled()


def test_add_with_the_files_of_another_board_puts_none_of_its_parts_in_the_record(app, base, tmp_path):
    """!
    @brief Add files with the files of ANOTHER board: the record keeps its own parts and takes no file or part of the other board.
    @param app Driver of the real window (fixture of test_reimport_matrix).
    @param base Synthetic set of the first import.
    @param tmp_path Temporary folder.
    """
    app.run(base, "replace", powers={"U1": 3.0})
    rec0 = app.doc.project.imports[0]
    before = sorted((p.designator, repr(p.from_file)) for p in rec0.parts)
    files0 = sorted((f.name, f.sha256) for f in rec0.files)
    app.run(other_board(base, tmp_path), "add")
    assert not app.dialogs[-1].radios["add"].isEnabled()
    rec = app.doc.project.imports[0]
    assert sorted((p.designator, repr(p.from_file)) for p in rec.parts) == before
    assert sorted((f.name, f.sha256) for f in rec.files) == files0
