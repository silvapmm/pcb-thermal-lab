#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_case2_review.py
@brief The independent checks of the review of this folder: (1) is the number of the thick-plate warning an upper bound, (2) which fields of the Board dock a single edit rewrites.
@details (1) The plate of case 2 (50 x 50 x 10 mm, k 150, h 400 on the bottom, adiabatic top and sides) heated by ONE source of 70 W over the whole top face (a one-dimensional
         column) and over a central 30 x 30 mm square: the independent 3D solver (tests/helpers/layered3d.py) against the FVM at the hottest point, and the 'up to' of
         checks.check_thick_plates, q'' t / (2 k), beside q'' t / k. (2) The real main window offscreen: a project whose board values lie outside the ranges of the Board dock
         or carry more decimals than its boxes, and a simple stack-up with unequal copper per layer, are loaded; one unrelated field (h_bottom, or the top emissivity) is edited;
         every board field is printed before and after. The program is not edited.
         Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python -u research/muzychka-case2-analytic/scripts/study_case2_review.py
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PCBTHERMAL_CONFIG", "/tmp/pcbthermal-case2-config")        # a private configuration: the user's preferences must not change the numbers

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import case2 as C  # noqa: E402


def bound_check():
    """!
    @brief Part 1: the 3D surface against the FVM node for a source over the whole face and over a 30 mm square, with the warning's bound.
    @return list of dicts (side, top_3d, fvm, gap, bound_half, bound_full, warned).
    """
    from pcbthermal import Problem, SolverOptions, simulate
    from pcbthermal.model import Materials
    out = []
    for side in (50.0, 30.0):
        rect = (25 - side / 2, 25 - side / 2, 25 + side / 2, 25 + side / 2)
        n, dx = 50, 1e-3
        res = C.L.solve(dx, n, n, [(C.T_MM * 1e-3, C.K_PLATE, 16)], [tuple(v * 1e-3 for v in rect)], [70.0], 0.0, C.H_PAPER)
        top = C.AMB + float(res["surface_top"][n // 2 - 1:n // 2 + 1, n // 2 - 1:n // 2 + 1].mean())     # the centre falls on a cell corner
        p = Problem.new(50, 50, layers=1, thickness_mm=1.0001 * C.T_MM, copper_um=C.T_MM * 1e3, ambient=C.AMB, h_top=1e-6, h_bottom=C.H_PAPER, h_side=None,
                        materials=Materials(k_copper=C.K_PLATE))
        p.add_full_copper(layers=None)
        p.add_heater(1, 70.0, rect=rect, name="U")
        sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0))
        fvm = sim.heater_rows()[0]["t_max"]
        q = 70.0 / (side * 1e-3) ** 2
        row = {"side": side, "top_3d": top, "fvm": fvm, "gap": top - fvm, "bound_half": q * C.T_MM * 1e-3 / (2 * C.K_PLATE), "bound_full": q * C.T_MM * 1e-3 / C.K_PLATE,
               "warned": any("thick and poorly" in w for w in sim.warnings)}
        out.append(row)
        print(f" source {side:.0f} x {side:.0f} mm: 3D surface {top:.2f} C, FVM peak {fvm:.2f} C, gap {row['gap']:.2f} K; warning bound q''t/2k {row['bound_half']:.2f} K, "
              f"q''t/k {row['bound_full']:.2f} K; warning shown: {row['warned']}")
    return out


def dock_check():
    """!
    @brief Part 2: one unrelated edit of the Board dock and every board field before and after it, in the real main window.
    @return list of (label, before dict, after dict).
    """
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication, QMessageBox
    from pcbthermal import Problem
    from pcbthermal.gui.document import Document
    from pcbthermal.gui.main_window import MainWindow
    for kind in ("warning", "critical", "information"):
        setattr(QMessageBox, kind, staticmethod(lambda *a, **kw: None))
    QMessageBox.question = staticmethod(lambda *a, **kw: QMessageBox.Discard)
    app = QApplication.instance() or QApplication([])
    win = MainWindow(Document(), QSettings("/tmp/pcbthermal-case2-review.ini", QSettings.IniFormat))
    win.show()

    def snap(b):
        """!
        @brief The board fields that the dock writes, in the units of the dock.
        @param b Board.
        @return dict.
        """
        m = b.materials
        return {"width mm": b.width * 1e3, "thickness mm": b.thickness * 1e3, "copper um": [round(c * 1e6, 3) for c in b.copper_thickness], "h_top": b.h_top,
                "h_bottom": b.h_bottom, "ambient": b.ambient, "k_copper": m.k_copper, "k_through": m.k_fr4_through, "plating um": round(b.via_plating * 1e6, 3)}

    out = []
    p = C.problem()
    b = p.board
    b.width, b.h_top, b.ambient, b.via_plating = 0.05004, 600.0, 25.37, 18.5e-6              # outside a range (h_top) or more decimals than the box (the others)
    b.materials.k_copper, b.materials.k_fr4_through = 150.4, 0.345
    win._load_problem(p, "plate")
    before = snap(win.doc.problem.board)
    win.board_panel.h_bottom.setValue(401.0)
    win.board_panel.h_bottom.setValue(400.0)
    app.processEvents()
    out.append(("plate, h_bottom 400 -> 401 -> 400", before, snap(win.doc.problem.board)))
    q = Problem.new(63.47, 41.23, layers=4, thickness_mm=1.6, copper_um=35)
    q.board.copper_thickness = [70e-6, 17.5e-6, 17.5e-6, 70e-6]                               # a simple stack-up (no dielectrics list) with unequal copper
    win._load_problem(q, "unequal")
    before = snap(win.doc.problem.board)
    win.board_panel.emis_top.setValue(0.8)
    app.processEvents()
    out.append(("4 layers 70/17.5/17.5/70 um, top emissivity 0.9 -> 0.8", before, snap(win.doc.problem.board)))
    for label, a, z in out:
        print(f" {label}")
        for key in a:
            mark = "  CHANGED" if a[key] != z[key] else ""
            print(f"   {key:13s} {str(a[key]):32s} -> {str(z[key]):32s}{mark}")
    return out


def main():
    """!
    @brief Run both parts.
    @return None.
    """
    print("1. is the 'up to' of the thick-plate warning a bound? (adiabatic top and sides, h 400 on the bottom, 70 W)")
    bound_check()
    print("\n2. one unrelated edit of the Board dock (real main window, offscreen)")
    dock_check()


if __name__ == "__main__":
    main()
