"""!
@file make_screenshots.py
@brief Renders the application off-screen and saves the screenshots used in the README and the docs.

Usage: python examples/make_screenshots.py [output_folder]   (default: docs/images)
"""

import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QSettings, Qt                                        # noqa: E402
from PySide6.QtWidgets import QApplication                                  # noqa: E402

from pcbthermal import SolverOptions, simulate                              # noqa: E402
from pcbthermal.examples import example_board, example_profile_board                               # noqa: E402
from pcbthermal.gui.calculator import PowerCalculator                      # noqa: E402
from pcbthermal.gui.main_window import TAB_PROFILE, TAB_RESULTS, TAB_STACKUP, MainWindow   # noqa: E402


def main(out_dir):
    """!
    @brief Produce the screenshots.
    @param out_dir Folder that receives the PNG files.
    @return List of written file paths.
    """
    os.makedirs(out_dir, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    settings = QSettings(os.path.join(tempfile.mkdtemp(), "shots.ini"), QSettings.IniFormat)
    settings.setValue("theme", "dark")
    win = MainWindow(settings=settings)
    win._load_problem(example_board(), "example-4layer")
    win.resize(2400, 1363)
    win.show()
    app.processEvents()                                                      # The window sizes its docks once it is shown; the wider docks below come after that
    # Wide docks so that no field of the panels is cut off (the default widths are narrow for the many controls)
    win.resizeDocks([win.dock_board, win.dock_sim], [420, 560], Qt.Horizontal)
    app.processEvents()
    written = []

    def shot(name):
        app.processEvents()
        path = os.path.join(out_dir, name)
        win.grab().save(path)
        written.append(path)

    win.canvas.fit()
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    shot("editor.png")

    sim = simulate(win.doc.problem, SolverOptions(cell_mm=1.0))
    win._on_done(sim)
    for tab, name in ((1, "results_temperature.png"), (0, "results_summary.png"), (4, "results_components.png")):
        win.results.tabs.setCurrentIndex(tab)
        shot(name)

    win.tabs.setCurrentIndex(TAB_RESULTS)
    win.results.tabs.setCurrentWidget(win.results.animation)
    anim = win.results.animation
    anim.t_end.setValue(120.0)
    anim.frames.setValue(40)
    anim.compute.click()
    while anim.tr is None:
        app.processEvents()
    anim.slider.setValue(int(anim.slider.maximum() * 0.55))
    shot("animation.png")

    # Advanced stack-up: the cross-section tab
    win._load_problem(example_board(), "example-4layer")
    b = win.doc.problem.board
    b.make_advanced()
    b.copper_thickness = [70e-6, 35e-6, 35e-6, 70e-6]
    b.dielectrics[0].thickness = 0.1e-3
    b.dielectrics[1].thickness, b.dielectrics[1].name = 1.0e-3, "Metal-core dielectric (2 W/mK)"
    b.dielectrics[1].k_through = b.dielectrics[1].k_inplane = 2.0
    b.thickness = b.total_thickness()
    win.doc.changed.emit()
    win.tabs.setCurrentIndex(TAB_STACKUP)
    shot("stackup.png")
    win.doc.stack.setClean()                                                 # Loading the next example must not ask about the edits above

    # A board with an outline: the L-shaped board and its temperature map
    win._load_problem(example_board(), "example-outline")
    win.doc.set_outline([[0, 0], [100, 0], [100, 30], [60, 30], [60, 80], [0, 80]])
    win.doc.set_props("heater", 1, power=0.0, merge=False)
    win.tabs.setCurrentIndex(0)
    win.canvas.fit()
    shot("outline.png")
    win._on_done(simulate(win.doc.problem, SolverOptions(models=("fvm",), cell_mm=1.0)))
    win.results.tabs.setCurrentIndex(1)
    shot("outline_temperature.png")
    win.doc.stack.setClean()

    # Power profiles: editor page and time simulation
    win._load_problem(example_profile_board(), "example-profile")
    win.show()
    win.tabs.setCurrentIndex(TAB_PROFILE)
    win.profile_page.table.selectRow(1)
    win.profile_page.run_analysis()
    while not win.profile_page.decisions:
        app.processEvents()
    shot("power_profile.png")
    win._on_done(simulate(win.doc.problem, SolverOptions(cell_mm=1.0)))
    win.results.tabs.setCurrentWidget(win.results.time_sim)
    shot("results_power_profile.png")
    # Computed heat transfer on a vertical board: the Board panel with the 'Vertical natural convection' control
    win._load_problem(example_board(), "example-vertical")
    bd = win.doc.problem.board
    bd.h_mode, bd.orientation, bd.natural_form = "computed", "vertical", "general"
    win.doc.changed.emit()
    win.tabs.setCurrentIndex(0)
    win.resizeDocks([win.dock_board], [600], Qt.Horizontal)                  # Wider only for this shot: the combo texts are long
    app.processEvents()
    path = os.path.join(out_dir, "environment_natural_form.png")
    win.dock_board.grab().save(path)                                         # Only the Board dock: the control is small on the full window
    written.append(path)
    win.resizeDocks([win.dock_board], [420], Qt.Horizontal)
    win.doc.stack.setClean()

    # Stack-up tab with the inner copper weight of the typical stack-up set to 1 oz
    win._load_problem(example_board(), "example-inner-copper")
    win.doc.problem.board.make_advanced()
    win.doc.set_inner_copper_oz(1.0)
    win.tabs.setCurrentIndex(TAB_STACKUP)
    shot("stackup_inner_copper.png")
    win.doc.stack.setClean()

    # Power calculator: board description list and the result terms (coarse cell: a quick case)
    win._load_problem(example_board(), "example-calculator")
    win.doc.set_options(cell_mm=2.0)
    win.tabs.setCurrentIndex(0)
    calc = PowerCalculator(win.doc, win)
    calc.design.setCurrentIndex(calc.design.findData("hand"))
    calc.show()
    calc.compute.click()
    t0 = time.time()
    while (calc.out is None or not calc.compute.isEnabled()) and time.time() - t0 < 300:
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()
    path = os.path.join(out_dir, "calculator_design.png")
    calc.grab().save(path)
    written.append(path)
    calc.close()
    win.doc.stack.setClean()
    return written


if __name__ == "__main__":
    for f in main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images")):
        print(f)
