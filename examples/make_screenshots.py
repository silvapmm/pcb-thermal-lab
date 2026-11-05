#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_screenshots.py
@brief Renders the application off-screen and saves the screenshots used in the README and the docs.

Usage: python examples/make_screenshots.py [output_folder]   (default: docs/images)
       python examples/make_screenshots.py --import <rp2040 gerber folder> [output_folder]   (the import window, the imported board, Preferences, dark theme)
"""

import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QSettings, Qt                                        # noqa: E402
from PySide6.QtWidgets import QApplication, QScrollArea                                  # noqa: E402

from pcbthermal import SolverOptions, simulate                              # noqa: E402
from pcbthermal.examples import example_board, example_profile_board                               # noqa: E402
from pcbthermal.gui.calculator import PowerCalculator                      # noqa: E402
from pcbthermal.gui.main_window import TAB_PROFILE, TAB_RESULTS, TAB_STACKUP, MainWindow   # noqa: E402


def shrink(path, max_width=1400):
    """!
    @brief Make a screenshot light for the repository: at most `max_width` pixels wide and 256 colours with dithering (keeps the colour bars smooth).
    @param path PNG file, rewritten in place.
    @param max_width Largest width in pixels.
    @return None
    """
    from PIL import Image                                                    # Pillow comes with Matplotlib

    im = Image.open(path).convert("RGB")
    if im.width > max_width:
        im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
    im.quantize(256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG).save(path, optimize=True)


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
        shrink(path)
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
    shrink(path)
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
    shrink(path)
    written.append(path)
    calc.close()
    win.doc.stack.setClean()
    return written


def main_import(out_dir, board_dir):
    """!
    @brief Produce the screenshots of the Gerber import window, the editor with the imported copper, Preferences and the dark theme (one real board).
    @param out_dir Folder that receives the PNG files.
    @param board_dir Folder with the Gerber files of the RP2040 minimal design (BSD-3-Clause) and its placement file.
    @return List of written file paths.
    """
    import shutil

    from pcbthermal.gui.import_window import ImportBoardWindow, ReimportDialog
    from pcbthermal.gui.preferences import PreferencesDialog

    os.makedirs(out_dir, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    # A copy of the files under a neutral name, so that no path of this machine can appear in a picture
    work = os.path.join(tempfile.mkdtemp(), "rp2040")
    shutil.copytree(board_dir, work)
    written = []

    def save(widget, name):
        app.processEvents()
        path = os.path.join(out_dir, name)
        widget.grab().save(path)
        shrink(path)
        written.append(path)

    for theme_name, suffix in (("light", ""), ("dark", "_dark")):
        settings = QSettings(os.path.join(tempfile.mkdtemp(), "shots.ini"), QSettings.IniFormat)
        settings.setValue("theme", theme_name)
        win = MainWindow(settings=settings)
        win.resize(2000, 1200)
        win.show()
        app.processEvents()
        dlg = ImportBoardWindow(win)
        dlg.confirm = lambda *a: True
        dlg.notify = lambda *a: None
        dlg.resize(1280, 820)
        dlg.show()
        dlg.open_path(work)
        dlg.page1.source.setText("rp2040/gerber")                           # Display only: the path of the copy is a temporary folder of this machine
        app.processEvents()
        save(dlg, f"import_step1{suffix}.png")
        dlg.go(1)
        pg = dlg.page2
        # Select the RP2040 chip (a QFN with an exposed pad) so that its pad shape and the dashed outline show
        parts = dlg.session.parts()
        des = next((p.designator for p in parts if "QFN" in (p.footprint or "")), parts[0].designator)   # the RP2040 chip: a QFN with an exposed pad
        dlg.session.set_part(des, power=1.5)                                # a power ticks it as a heat source; the default shape of a part with an exposed pad is the pad
        pg.refresh()
        pg.selected = des
        for r in range(pg.table.rowCount()):
            if pg.table.item(r, 1) is not None and pg.table.item(r, 1).text() == des:
                pg.table.selectRow(r)
                pg.table.scrollToItem(pg.table.item(r, 1))
        app.processEvents()
        save(dlg, f"import_step2{suffix}.png")
        dlg.go(2)
        save(dlg, f"import_step3{suffix}.png")
        dlg.do_import()
        if not suffix:
            old = dlg.record
            # The stored import is the previous revision of the layout: one part is not in it yet (new in the files), one sits 0.8 mm from where the files now put it
            old.parts = [q for q in old.parts if q.designator != "C10"]
            for q in old.parts:
                if q.designator == "C1":
                    q.polygon_mm = [[x + 0.8, y] for x, y in q.polygon_mm]
                    q.from_file["position_mm"] = [q.from_file["position_mm"][0] + 0.8, q.from_file["position_mm"][1]] if q.from_file.get("position_mm") else None
            w2 = ImportBoardWindow(win, existing=old)
            w2.confirm = lambda *a: True
            w2.notify = lambda *a: None
            w2.open_path(work)
            w2.session.build_problem()                                       # the dialog compares the stored import with the one just built
            rd = ReimportDialog(w2.session, old, w2)
            rd.radios["update"].setChecked(True)                              # the table lists what the update does with every part
            rd.show()
            save(rd, "import_reimport.png")
            rd.close()
            w2.close()
        win.doc.open_import(dlg.problem, dlg.record)
        win._after_load()
        win.resizeDocks([win.dock_board, win.dock_sim], [420, 560], Qt.Horizontal)
        win.canvas.fit()
        app.processEvents()
        win.canvas.set_selection([("heater", 0)])
        win._on_canvas_selection([("heater", 0)])
        save(win, f"editor_imported{suffix}.png")
        # Live warnings under Run: a second source that is half off the board, drawn on the top layer
        win.doc.problem.add_heater(1, 0.5, rect=(46, 40, 58, 46), name="X1")
        win.doc.changed.emit()
        win.canvas.fit()
        t0 = time.time()
        while time.time() - t0 < 1.5:                                        # the live check runs a moment after an edit
            app.processEvents()
            time.sleep(0.05)
        save(win, f"editor_warnings{suffix}.png")
        # The run on the imported board: the summary with its notes, and the temperature map
        win.doc.problem.heaters = [h for h in win.doc.problem.heaters if h.name != "X1"]
        win.doc.changed.emit()
        win._on_done(simulate(win.doc.problem, SolverOptions(cell_mm=1.0)))
        win.results.tabs.setCurrentIndex(0)
        save(win, f"results_summary_imported{suffix}.png")
        win.results.tabs.setCurrentIndex(1)
        save(win, f"results_temperature_imported{suffix}.png")
        if not suffix:
            pref = PreferencesDialog(win)
            pref.resize(980, 700)
            pref.show()
            pref.sections.setCurrentRow(pref.section_titles().index("Defaults for new projects"))
            page = pref.pages.currentWidget()
            # The same page scrolled to its end: the Solver and Gerber import boxes (memory fraction, file-size limit)
            for sc in ([page] if isinstance(page, QScrollArea) else []) + page.findChildren(QScrollArea):
                sc.verticalScrollBar().setValue(sc.verticalScrollBar().maximum())
            save(pref, "preferences_solver_gerber.png")
            pref.close()
        dlg.close()
        win.doc.stack.setClean()
        win.close()
    return written


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--import":
        for f in main_import(sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images"), sys.argv[2]):
            print(f)
        sys.exit(0)
    for f in main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images")):
        print(f)
