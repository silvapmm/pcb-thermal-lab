#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_case2_gui.py
@brief Case 2 of Muzychka, Culham and Yovanovich (2003) through the real main window (offscreen): why the application shows other numbers than the study script.
@details Routes: A, the project of the study script opened in the window (as File - Open would) and run with the model of the window; B, what a user can TYPE in the Board dock (the
         copper thickness box stops at 210 um, the plate of the paper has 10 000 um, so the nearest typed board is a 0.21 mm copper layer in a 10 mm laminate), with the defaults of a new
         board (h_top 10, h_side 10) and with them set to the paper's values; C, the defaults of a new board (edges losing heat, h_top 10) applied to the script's plate to show the size of each
         default. For every route the heater rows of the Results table (peak and mean over the footprint, as the window shows them) and the layer-temperature centroid of the script are printed.
         Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python -u research/muzychka-case2-analytic/scripts/study_case2_gui.py
"""

import copy
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PCBTHERMAL_CONFIG", "/tmp/pcbthermal-case2-config")        # a private configuration: the user's preferences must not change the numbers

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import case2 as C  # noqa: E402


def fmt(v):
    """!
    @brief A list of numbers as text.
    @param v Iterable of floats.
    @return str.
    """
    return "[" + ", ".join(f"{x:7.2f}" for x in v) + "]"


def wait(win, app):
    """!
    @brief Process events until the background calculation of the window ends.
    @param win MainWindow.
    @param app QApplication.
    @return None.
    """
    from PySide6.QtCore import QThread
    while win.worker is not None and win.worker.isRunning():
        app.processEvents()
        QThread.msleep(20)
    for _ in range(20):
        app.processEvents()


def report(label, win, ref):
    """!
    @brief Print what the window shows for the finished run and the script's read-out.
    @param label Route name.
    @param win MainWindow with a result.
    @param ref Dict of the independent 3D references.
    @return None.
    """
    sim = win.sim
    rows = sim.heater_rows()
    res = sim.reference
    cen = C.readout(res)["cen"]
    print(f"\n{label}: model {res.model}, cell {win.doc.options.cell_mm} mm, h_top {win.doc.problem.board.h_top}, h_side {win.doc.problem.board.h_side}, "
          f"copper {win.doc.problem.board.copper_thickness[0] * 1e6:.0f} um, board thickness {win.doc.problem.board.thickness * 1e3:.2f} mm")
    print("  Results table, part rows: t_max", fmt([r["t_max"] for r in rows]), " t_mean", fmt([r["t_mean"] for r in rows]))
    print("  script read-out (layer temperature at the centroid):", fmt(cen), "  3D surface:", fmt(ref["surf_c"]), "  paper:", fmt(C.PAPER_CENTROID))
    print("  warnings:", len(sim.warnings), [w[:90] for w in sim.warnings][:4])


def main():
    """!
    @brief Build the routes in a real main window and run them.
    @return None.
    """
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication, QMessageBox
    from pcbthermal.gui.document import Document
    from pcbthermal.gui.main_window import MainWindow
    from pcbthermal.model import new_problem

    shown = []
    for kind in ("warning", "critical", "information"):
        setattr(QMessageBox, kind, staticmethod(lambda *a, _k=kind, **kw: shown.append((_k, a[1:3])) or None))
    QMessageBox.question = staticmethod(lambda *a, **kw: QMessageBox.Discard)          # "discard the changes?" when a new project replaces an edited one
    app = QApplication.instance() or QApplication([])
    win = MainWindow(Document(), QSettings("/tmp/pcbthermal-case2-settings.ini", QSettings.IniFormat))
    win.resize(1500, 900)
    win.show()
    ref = C.reference3d(0.5, 8)

    def run(models=("fvm",), cell=1.0):
        """!
        @brief Press Run with the given models and cell.
        @param models Model keys.
        @param cell Cell in mm.
        @return None.
        """
        win.doc.set_options(models=tuple(models), cell_mm=cell)
        win.board_panel.refresh()
        win.run_simulation()
        wait(win, app)

    print("route A: the project of the script, opened in the window")
    for m in ("fvm", "analytic"):
        win._load_problem(C.problem(), "case2")
        run((m,), 1.0)
        report(f"A ({m})", win, ref)

    print("\nroute B: the plate typed in the Board dock (what the controls allow)")
    p = new_problem(50.0, 50.0, layers=1)
    win._load_problem(p, "case2-typed")
    bp = win.board_panel
    print("  limits of the boxes: copper per layer", bp.copper.minimum(), "to", bp.copper.maximum(), "um; total thickness up to", bp.thickness.maximum(), "mm; h up to", bp.h_top.maximum(), "W/m2K")
    bp.thickness.setValue(10.0)
    bp.copper.setValue(10000.0)                                            # a user types the paper's 10 mm: the box clamps it
    print("  typed 10000 um, the box holds", bp.copper.value(), "um")
    bp.k_cu.setValue(150.0)

    def add_sources(win_):
        """!
        @brief Add the four sources of the paper to the document of the window.
        @param win_ MainWindow.
        @return None.
        """
        def mutate(project):
            for i, (c, pw) in enumerate(zip(C.CENTRES, C.POWERS)):
                project.problem.add_heater(1, pw, rect=C.rect(c), name=f"S{i}")
        win_.doc.edit("Add sources", mutate)

    win.doc.edit("Copper", lambda project: project.problem.add_full_copper(layers=None))     # the user draws a zone over the board
    add_sources(win)
    bp.h_bottom.setValue(400.0)
    run(("fvm",), 1.0)
    report("B1 (new-board defaults: h_top 10, h_side 10, copper 0.21 mm, laminate 0.3 W/mK)", win, ref)
    bp.h_top.setValue(0.0)
    bp.side_on.setChecked(False)
    run(("fvm",), 1.0)
    report("B2 (h_top 0, edges insulated, still copper 0.21 mm)", win, ref)

    print("\nroute A2: the same project, then ONE edit of any field of the Board dock (h_bottom 400 -> 401 -> 400): the dock writes its own copper box back")
    win._load_problem(C.problem(), "case2")
    print("  copper before the edit:", win.doc.problem.board.copper_thickness[0] * 1e6, "um")
    win.board_panel.h_bottom.setValue(401.0)
    win.board_panel.h_bottom.setValue(400.0)
    print("  copper after the edit: ", win.doc.problem.board.copper_thickness[0] * 1e6, "um, thickness", win.doc.problem.board.thickness * 1e3, "mm")
    run(("fvm",), 1.0)
    report("A2 (fvm)", win, ref)

    print("\nroute C: the plate of the script with the defaults of a new board, one default at a time (FVM 1 mm, API)")
    from pcbthermal import SolverOptions, simulate
    base = C.problem()
    for label, mut in (("script as is", lambda b: None), ("h_top 10", lambda b: setattr(b, "h_top", 10.0)), ("h_side 10", lambda b: setattr(b, "h_side", 10.0)),
                       ("both", lambda b: (setattr(b, "h_top", 10.0), setattr(b, "h_side", 10.0)))):
        q = copy.deepcopy(base)
        mut(q.board)
        s = simulate(q, SolverOptions(models=("fvm",), cell_mm=1.0))
        print(f"  {label:14s} centroids", fmt(C.readout(s.results['fvm'])['cen']), " peak rows", fmt([r['t_max'] for r in s.heater_rows()]))
    print("\nmessage boxes shown:", len(shown), shown[:3])


if __name__ == "__main__":
    main()
