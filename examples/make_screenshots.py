#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_screenshots.py
@brief Renders the application off-screen and saves the screenshots used in the README and the docs.

Usage: python examples/make_screenshots.py [output_folder]   (default: docs/images)
       python examples/make_screenshots.py --import <rp2040 gerber folder> [output_folder]   (the import window, the imported board, Preferences, dark theme)
       python examples/make_screenshots.py --surface [output_folder]   (the surface read-out of thick copper: the map of Surface (top) and the Components table)
       python examples/make_screenshots.py --views <rp2040 gerber folder> [output_folder]   (the 2.5.1 views: layer grid, Smooth, Terrain, copper underlay, temperature on the board, background image, re-import warning)
       python examples/make_screenshots.py --manual [output_folder]   (the manual_*.png pictures of the user manual: numbered window, start window, dialogs)
"""

import os
import sys
import tempfile
import time

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")
# Neutral configuration folder: Preferences shows the path of user_defaults.json, which must never be a personal path in a committed picture
NEUTRAL_CONFIG = "/tmp/pcbthermal-config"
os.makedirs(NEUTRAL_CONFIG, exist_ok=True)
os.environ["PCBTHERMAL_CONFIG"] = NEUTRAL_CONFIG
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QSettings, Qt                                        # noqa: E402
from PySide6.QtGui import QPainter, QPixmap                                  # noqa: E402
from PySide6.QtWidgets import QApplication                                  # noqa: E402

from pcbthermal import SolverOptions, simulate                              # noqa: E402
from pcbthermal.examples import example_board, example_profile_board                               # noqa: E402
from pcbthermal.gui.calculator import PowerCalculator                      # noqa: E402
from pcbthermal.gui.main_window import TAB_PROFILE, TAB_RESULTS, TAB_STACKUP, MainWindow   # noqa: E402


def _assert_neutral(path):
    """!
    @brief Refuse to save a picture while the configuration folder is not the neutral one.
    @param path Path of the picture about to be written (used in the message).
    @return None
    @throws RuntimeError If PCBTHERMAL_CONFIG is not the neutral folder.
    """
    if os.environ.get("PCBTHERMAL_CONFIG") != NEUTRAL_CONFIG:
        raise RuntimeError(f"PCBTHERMAL_CONFIG is not neutral; refusing to write {path}")


FULL_COLOUR = ("editor", "simulation_", "results_summary")      # File-name prefixes saved without the 256-colour quantisation (the verdict and warning dots must stay distinct)


def shrink(path, max_width=1400):
    """!
    @brief Make a screenshot light for the repository: at most `max_width` pixels wide and 256 colours with dithering (keeps the colour bars smooth), except the window pictures of FULL_COLOUR.
    @param path PNG file, rewritten in place.
    @param max_width Largest width in pixels.
    @return None
    """
    from PIL import Image                                                    # Pillow comes with Matplotlib

    _assert_neutral(path)

    im = Image.open(path).convert("RGB")
    if im.width > max_width:
        im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
    # The pictures of the windows (the Simulation panel with its red, amber and green dots) stay full colour: 256 colours merged the three dots into one tone
    if os.path.basename(path).startswith(FULL_COLOUR):
        im.save(path, optimize=True)
        return
    im.quantize(256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG).save(path, optimize=True)


def main(out_dir):
    """!
    @brief Produce the screenshots.
    @param out_dir Folder that receives the PNG files.
    @return List of written file paths.
    """
    _assert_neutral(out_dir)
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
    # The Models tab shows the six models side by side (the FEM and the 3D solid are off by default, so they are run for this picture only); the three-model run comes back after
    six = ("fvm", "lumped", "analytic", "fdm", "solid3d", "fem")
    sim_all = simulate(win.doc.problem, SolverOptions(cell_mm=1.0, models=six))
    # The Models box ticks the six models of the picture (so the panel and the tab agree), before the result is shown so that it is not marked outdated
    shown = [k for k, c in win.solver_panel.cb.items() if c.isChecked()]
    for k, c in win.solver_panel.cb.items():
        c.setChecked(k in six)
    win._on_done(sim_all)
    win.results.tabs.setCurrentWidget(win.results.compare)
    shot("results_models.png")
    for k, c in win.solver_panel.cb.items():
        c.setChecked(k in shown)
    win._on_done(sim)

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
    # U2 moves from the cut-away corner into the other arm of the L (x 75 to 81 mm, y 10 to 16 mm) so that it stands on the board; 0.5 W is a small real power
    win.doc.set_props("heater", 1, power=0.5, polygon=np.array([[0.075, 0.010], [0.081, 0.010], [0.081, 0.016], [0.075, 0.016]]), merge=False)
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

    _assert_neutral(out_dir)
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
            # A layout revision also changes files: the stored copy of the top paste layer is another version (other checksum), so the dialog says that some files differ
            for f in old.files:
                if "paste" in (f.function or "").lower():
                    f.sha256 = "0" * 64
                    break
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
        # Live warnings under Run: a second source fully on the board, over the copper pour left of the chip, close to the left side
        win.doc.problem.add_heater(1, 0.5, rect=(7, 27, 13, 31), name="X1")
        win.doc.changed.emit()
        win.canvas.fit()
        t0 = time.time()
        while time.time() - t0 < 1.5:                                        # the live check runs a moment after an edit
            app.processEvents()
            time.sleep(0.05)
        # The warnings are the 'Warnings (N)' box in the scrolled part of the Simulation dock: scroll it into view and open the first row
        acc = win.solver_panel.checks
        if acc.rows:
            acc.rows[0].set_open(True)
        from PySide6.QtWidgets import QScrollArea
        area = win.dock_sim.findChild(QScrollArea)
        if area is not None:
            area.ensureWidgetVisible(acc, 0, 20)
        win.resizeDocks([win.dock_sim, win.dock_inspector], [int(0.7 * win.height()), int(0.3 * win.height())], Qt.Vertical)
        app.processEvents()
        if area is not None:
            area.ensureWidgetVisible(acc, 0, 20)
        save(win, f"editor_warnings{suffix}.png")
        # The run on the imported board: the summary with its notes, and the temperature map
        win.doc.problem.heaters = [h for h in win.doc.problem.heaters if h.name != "X1"]
        # A junction limit of 100 degC on the chip: the run reads 108 degC, so the summary shows a genuine alert (a limit exceeded) beside the notes
        win.doc.problem.heaters[0].tj_max = 100.0
        win.doc.changed.emit()
        win._on_done(simulate(win.doc.problem, SolverOptions(cell_mm=1.0)))
        win.results.tabs.setCurrentIndex(0)
        save(win, f"results_summary_imported{suffix}.png")
        win.results.tabs.setCurrentIndex(1)
        save(win, f"results_temperature_imported{suffix}.png")
        if not suffix:
            pref = PreferencesDialog(win)
            pref.resize(980, 440)
            pref.show()
            # Solver and Gerber import are sections of their own: one picture with the two pages one above the other
            grabs = []
            for title in ("Solver", "Gerber import"):
                pref.sections.setCurrentRow(pref.section_titles().index(title))
                app.processEvents()
                grabs.append(pref.grab())
            sheet = QPixmap(grabs[0].width(), sum(g.height() for g in grabs))
            painter = QPainter(sheet)
            y = 0
            for g in grabs:
                painter.drawPixmap(0, y, g)
                y += g.height()
            painter.end()
            path = os.path.join(out_dir, "preferences_solver_gerber.png")
            sheet.save(path)
            shrink(path)
            written.append(path)
            pref.close()
        dlg.close()
        win.doc.stack.setClean()
        win.close()
    return written


def _sketch_picture(path, width_mm, height_mm):
    """!
    @brief Draw a neutral PCB-like sketch (green board, tracks, pads) as the background picture of a hand-drawn board.
    @param path PNG file to write.
    @param width_mm Board width in mm (sets the aspect ratio of the picture).
    @param height_mm Board height in mm.
    @return None
    """
    from PIL import Image, ImageDraw

    k = 10                                                                   # pixels per mm
    im = Image.new("RGB", (round(width_mm * k), round(height_mm * k)), (36, 92, 60))
    d = ImageDraw.Draw(im)
    track = (205, 170, 70)
    for i in range(1, 7):                                                    # a bus of parallel tracks with right-angle bends
        y = round(height_mm * k * i / 7)
        x1 = round(width_mm * k * (0.15 + 0.08 * i))
        d.line([(round(width_mm * k * 0.05), y), (x1, y), (x1, round(height_mm * k * 0.5)), (round(width_mm * k * 0.95), round(height_mm * k * 0.5))], fill=track, width=7)
    for i in range(10):                                                      # pads of a connector row
        x = round(width_mm * k * (0.1 + 0.08 * i))
        d.ellipse([x - 12, 18, x + 12, 42], fill=track)
        d.ellipse([x - 5, 25, x + 5, 35], fill=(20, 40, 30))
    d.rectangle([round(width_mm * k * 0.55), round(height_mm * k * 0.6), round(width_mm * k * 0.85), round(height_mm * k * 0.9)], outline=(235, 235, 235), width=4)
    im.save(path)


def main_views(out_dir, board_dir):
    """!
    @brief Produce the pictures of the 2.5.1 views: the Results maps with the layer grid, the Smooth and Terrain views and the copper underlay (light and dark), the Gradients tab,
           the Animation tab with its underlay, the temperature on the board, the Background image dialog with an image under a hand-drawn board and the re-import warning.
    @param out_dir Folder that receives the PNG files.
    @param board_dir Folder with the Gerber files of the RP2040 minimal design (BSD-3-Clause), used for the re-import warning.
    @return List of written file paths.
    """
    import copy
    import shutil

    from pcbthermal.gui.import_window import ImportBoardWindow, ReimportDialog
    from pcbthermal.gui.main_window import BackgroundDialog

    _assert_neutral(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    work = tempfile.mkdtemp()
    written = []

    def save(widget, name):
        app.processEvents()
        path = os.path.join(out_dir, name)
        widget.grab().save(path)
        shrink(path)
        written.append(path)

    def pick(combo, data):
        combo.setCurrentIndex(combo.findData(data))

    for theme_name, suffix in (("light", ""), ("dark", "_dark")):
        settings = QSettings(os.path.join(work, f"shots_{theme_name}.ini"), QSettings.IniFormat)
        settings.setValue("theme", theme_name)
        win = MainWindow(settings=settings)
        win._load_problem(example_board(), "example-4layer")
        win.resize(2000, 1200)
        win.show()
        app.processEvents()
        win.resizeDocks([win.dock_board, win.dock_sim], [420, 560], Qt.Horizontal)
        win.canvas.fit()
        win._on_done(simulate(win.doc.problem, SolverOptions(models=("fvm",), cell_mm=1.0)))
        win.tabs.setCurrentIndex(TAB_RESULTS)
        res = win.results
        # The Temperature tab: all four layers in a grid, smooth, with the copper under the map
        res.tabs.setCurrentWidget(res.temp)
        pick(win.layer_combo, -2)                           # The Layer box of the tool bar is the one layer choice (Temperature lists All (2 x 2))
        win.display.set_view("smooth")                      # One display choice for every map (the Display button of the tool bar)
        win.display.set_kind("copper")
        save(win, f"results_views{suffix}.png")
        if not suffix:
            # The Terrain view and the Gradients tab (the light theme is enough: the dark one only recolours them)
            pick(win.layer_combo, 0)
            win.display.set_view("terrain")
            win.display.set_contour("temperature", 5.0)
            save(win, "results_terrain.png")
            res.tabs.setCurrentWidget(res.grad)
            pick(win.layer_combo, 0)
            save(win, "results_gradient.png")
            # The Profiles tab: temperature along a cut with the cut overlay (the board picture over the curves) and the map on top
            res.tabs.setCurrentWidget(res.profile)
            pick(win.layer_combo, 0)
            win.display.set_view("current")
            win.display.set_kind("copper")
            win.a_overlay.setChecked(True)                  # The Map button: the temperature map of the reference model inside the cut picture
            save(win, "results_profile_cut.png")
            win.a_overlay.setChecked(False)
            win.display.reset()
        if suffix:
            win.doc.stack.setClean()
            win.close()
            continue
        # The Animation tab with the copper underlay and the Smooth view
        res.tabs.setCurrentWidget(res.animation)
        anim = res.animation
        anim.t_end.setValue(120.0)
        anim.frames.setValue(30)
        anim.compute.click()
        while anim.tr is None:
            app.processEvents()
        win.display.set_view("smooth")
        win.display.set_kind("copper")
        anim.slider.setValue(int(anim.slider.maximum() * 0.55))
        save(win, "animation_underlay.png")
        win.display.reset()                                  # The board picture shows the defaults (no underlay, Current), as before
        # The editor with the temperature on the board (colour bar in the strip beside the board)
        win.tabs.setCurrentIndex(0)
        win.canvas.fit()
        win.a_overlay.setChecked(True)
        win.canvas.fit()
        save(win, "editor_overlay.png")
        # The Display popover opened from the Board tab, drawn over the window (it is a separate window, so it is pasted in at its place) and cropped to the top;
        # the View shows Smooth, which works on the board (Terrain is the greyed entry)
        win.display.set_view("smooth")
        win.display.set_kind("copper")
        win._toggle_display_popover()
        app.processEvents()
        pm = win.grab()
        painter = QPainter(pm)
        painter.drawPixmap(win.mapFromGlobal(win.display_popover.pos()), win.display_popover.grab())
        painter.end()
        path = os.path.join(out_dir, "display_popover.png")
        pm.copy(0, 0, min(pm.width(), 1100), 360).save(path)
        shrink(path)
        written.append(path)
        win._toggle_display_popover()
        win.display.set_kind("none")
        win.a_overlay.setChecked(False)
        win.doc.stack.setClean()
        # A hand-drawn board with a picture under it: the dialog, then the editor
        win._load_problem(example_board(), "example-image")
        b = win.doc.problem.board
        w_mm, h_mm = b.width * 1000, b.height * 1000
        pic = os.path.join(work, "layout_sketch.png")
        _sketch_picture(pic, w_mm, h_mm)
        cfg = {"path": pic, "x_mm": 0.0, "y_mm": 0.0, "w_mm": w_mm, "h_mm": h_mm}
        dlg = BackgroundDialog(cfg, (w_mm, h_mm), win)
        dlg.show()
        save(dlg, "background_dialog.png")
        dlg.close()
        win.doc.project.view["background"] = cfg
        win.canvas.rebuild()
        win._sync_underlay()
        win.tabs.setCurrentIndex(0)
        win.canvas.fit()
        win.canvas.set_selection([])
        save(win, "editor_background.png")
        win.doc.stack.setClean()
        win.close()

    # The re-import dialog with the warning of a different board: the stored import is made to look like another board (a different outline and other files)
    copy_dir = os.path.join(work, "rp2040")
    shutil.copytree(board_dir, copy_dir)
    settings = QSettings(os.path.join(work, "shots_re.ini"), QSettings.IniFormat)
    settings.setValue("theme", "light")
    win = MainWindow(settings=settings)
    win.resize(1600, 1000)
    win.show()
    w1 = ImportBoardWindow(win)
    w1.confirm = lambda *a: True
    w1.notify = lambda *a: None
    w1.open_path(copy_dir)
    w1.session.build_problem()
    old = copy.deepcopy(w1.session.record)
    old.name = "OTHER-BOARD"
    old.box_mm = [0.0, 0.0, 2 * (old.box_mm[2] - old.box_mm[0]), 1.5 * (old.box_mm[3] - old.box_mm[1])]
    for i, f in enumerate(old.files):
        f.name, f.sha256 = f"other_{i}.gbr", f"{i:064x}"
    # The parts of another board sit elsewhere (the same parts at the same places make the files a revision of the same board)
    for p in old.parts:
        p.polygon_mm = [[x + 20.0, y + 15.0] for x, y in p.polygon_mm]
    w1.session.build_problem()
    rd = ReimportDialog(w1.session, old, w1)
    rd.resize(900, 700)
    rd.show()
    save(rd, "import_reimport_different.png")
    rd.close()
    w1.close()
    win.close()
    return written


def main_surface(out_dir):
    """!
    @brief Screenshot of the surface read-out: the 4-layer example board with 2 mm of outer copper, the Components table with its (column) columns and the one (surface) column and the Layer box.
    @param out_dir Folder that receives results_surface.png and results_surface_table.png (only these two pictures; the other screenshots are not remade).
    @return List of written file paths.
    """
    _assert_neutral(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    settings = QSettings(os.path.join(tempfile.mkdtemp(), "shots_surface.ini"), QSettings.IniFormat)
    settings.setValue("theme", "light")
    win = MainWindow(settings=settings)
    prob = example_board()
    prob.board.thickness = 6e-3
    prob.board.copper_thickness = [2e-3, 35e-6, 35e-6, 2e-3]               # Thick outer copper: the surface read-out exists and is worth showing
    prob.board.h_top, prob.board.h_bottom = 400.0, 400.0                     # A cooled plate: the surface differs from the layer mean by about 0.3 K, 2 % of the rise (shown on every board now, no threshold)
    for h in prob.heaters:
        if h.name == "U1":
            h.power = 20.0
    win._load_problem(prob, "example-thick-copper")
    win.resize(2000, 1200)
    win.show()
    app.processEvents()
    win.resizeDocks([win.dock_board, win.dock_sim], [420, 560], Qt.Horizontal)
    win.canvas.fit()
    win._on_done(simulate(win.doc.problem, SolverOptions(models=("fvm",), cell_mm=1.0)))
    win.tabs.setCurrentIndex(TAB_RESULTS)
    win.results.tabs.setCurrentWidget(win.results.temp)
    app.processEvents()
    from pcbthermal.gui import layerchoice
    win.layer_combo.setCurrentIndex(win.layer_combo.findData(layerchoice.SURFACE_BASE))      # Surface (top)
    app.processEvents()
    path = os.path.join(out_dir, "results_surface.png")
    win.grab().save(path)
    shrink(path)
    win.results.tabs.setCurrentWidget(win.results.tabs.widget(4))
    app.processEvents()
    path2 = os.path.join(out_dir, "results_surface_table.png")
    win.grab().save(path2)
    shrink(path2)
    win.doc.stack.setClean()
    win.close()
    return [path, path2]


def main_fem(out_dir):
    """!
    @brief Screenshots of the finite-element model in the window: the Simulation panel with the FEM ticked and its mesh boxes, and the Temperature tab of the thick plate of case 2 of Muzychka et al. on the FEM, Surface (top).
    @param out_dir Folder that receives simulation_fem.png and results_fem_surface.png (only these two pictures).
    @return List of written file paths.
    """
    from pcbthermal import api
    from pcbthermal.model import Materials, Problem
    _assert_neutral(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    settings = QSettings(os.path.join(tempfile.mkdtemp(), "shots_fem.ini"), QSettings.IniFormat)
    settings.setValue("theme", "light")
    win = MainWindow(settings=settings)
    prob = Problem.new(50, 50, layers=1, thickness_mm=10.001, copper_um=1e4, ambient=25.0, h_top=1e-6, h_bottom=400.0, h_side=None, materials=Materials(k_copper=150.0), name="plate-case-2")
    prob.add_full_copper()
    for i, (c, pw) in enumerate(zip([(12.5, 12.5), (37.5, 12.5), (12.5, 37.5), (37.5, 37.5)], [10.0, 25.0, 20.0, 15.0])):
        prob.add_heater(1, pw, rect=(c[0] - 5, c[1] - 5, c[0] + 5, c[1] + 5), name=f"S{i + 1}")
    win._load_problem(prob, "plate-case-2")
    win.resize(2000, 1200)
    win.show()
    app.processEvents()
    win.resizeDocks([win.dock_board, win.dock_sim], [420, 560], Qt.Horizontal)
    win.canvas.fit()
    win.doc.set_options(models=("fvm", "fem"), cell_mm=1.0)
    app.processEvents()
    path1 = os.path.join(out_dir, "simulation_fem.png")
    win.solver_panel.grab().save(path1)
    shrink(path1)
    win._on_done(api.simulate(win.doc.problem, win.doc.options))
    win.tabs.setCurrentIndex(TAB_RESULTS)
    win.results.tabs.setCurrentWidget(win.results.temp)
    win.results.temp.model.setCurrentIndex(win.results.temp.model.findData("fem"))
    from pcbthermal.gui import layerchoice
    win.layer_combo.setCurrentIndex(win.layer_combo.findData(layerchoice.SURFACE_BASE))
    app.processEvents()
    path2 = os.path.join(out_dir, "results_fem_surface.png")
    win.grab().save(path2)
    shrink(path2)
    win.doc.stack.setClean()
    win.close()
    return [path1, path2]


def _number_marks(pixmap, marks, radius=22):
    """!
    @brief Draw numbered round marks on a screenshot (the numbers of the legend that follows the figure in the user manual).
    @param pixmap QPixmap of the window, drawn on in place.
    @param marks List of (number, x, y) in pixels of the pixmap: the centre of each mark.
    @param radius Radius of a mark in pixels.
    @return None
    """
    from PySide6.QtGui import QColor, QFont, QPen

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(radius * 1.1))
    painter.setFont(font)
    for number, x, y in marks:
        # An amber disc with a dark ring reads on the dark and the light theme alike
        painter.setPen(QPen(QColor("#1f1f1e"), 3))
        painter.setBrush(QColor("#f2a900"))
        painter.drawEllipse(int(x - radius), int(y - radius), 2 * radius, 2 * radius)
        painter.setPen(QColor("#1f1f1e"))
        painter.drawText(int(x - radius), int(y - radius), 2 * radius, 2 * radius, Qt.AlignCenter, str(number))
    painter.end()


def main_manual(out_dir):
    """!
    @brief The screenshots that only the user manual (docs/USER_MANUAL.md) uses: the window with numbered areas, the empty start window, the New board dialog, the Properties of a heatsink and of a via, Preferences (first section) and the keyboard list.
    @param out_dir Folder that receives the manual_*.png pictures (the other screenshots are not remade).
    @return List of written file paths.
    """
    from pcbthermal.gui.main_window import NewBoardDialog
    from pcbthermal.gui.preferences import PreferencesDialog
    from pcbthermal.gui.shortcuts_dialog import ShortcutsDialog

    _assert_neutral(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    written = []

    def save_pixmap(pix, name):
        path = os.path.join(out_dir, name)
        pix.save(path)
        shrink(path)
        written.append(path)

    # 1. The empty window of a first start, light theme: the first-step hint on the board
    settings = QSettings(os.path.join(tempfile.mkdtemp(), "shots.ini"), QSettings.IniFormat)
    settings.setValue("theme", "light")
    win = MainWindow(settings=settings)
    win.resize(2400, 1363)
    win.show()
    app.processEvents()
    win.resizeDocks([win.dock_board, win.dock_sim], [420, 560], Qt.Horizontal)
    app.processEvents()
    win.canvas.fit()
    app.processEvents()
    save_pixmap(win.grab(), "manual_start.png")
    win.doc.stack.setClean()
    win.close()

    # 2. The example board in the dark theme with the areas of the window numbered (the legend is in the manual, chapter 3)
    settings = QSettings(os.path.join(tempfile.mkdtemp(), "shots.ini"), QSettings.IniFormat)
    settings.setValue("theme", "dark")
    win = MainWindow(settings=settings)
    win._load_problem(example_board(), "example-4layer")
    win.resize(2400, 1363)
    win.show()
    app.processEvents()
    win.resizeDocks([win.dock_board, win.dock_sim], [420, 560], Qt.Horizontal)
    app.processEvents()
    win.canvas.fit()
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    app.processEvents()
    pix = win.grab()

    def centre(widget, dx=0.5, dy=0.5):
        """Point of a widget in window pixels (dx, dy: fractions of its width and height)."""
        top_left = widget.mapTo(win, widget.rect().topLeft())
        return top_left.x() + widget.width() * dx, top_left.y() + widget.height() * dy

    ratio = pix.devicePixelRatio()
    marks = [(1, *centre(win.menuBar(), 0.11, 0.5)), (2, *centre(win.toolbar, 0.62, 0.5)),
             (3, *centre(win.dock_board, 0.85, 0.12)), (4, *centre(win.dock_elements, 0.85, 0.25)),
             (5, *centre(win.tabs, 0.33, 0.03)), (6, *centre(win.tabs, 0.5, 0.55)),
             (7, *centre(win.dock_sim, 0.85, 0.30)), (8, *centre(win.dock_inspector, 0.85, 0.20)),
             (9, *centre(win.statusBar(), 0.25, 0.5))]
    radius = 26
    # A mark keeps a margin from the edges of the window, so that the one of the menu bar and the one of the status bar are not cut
    marks = [(n, min(max(x, radius + 4), win.width() - radius - 4), min(max(y, radius + 4), win.height() - radius - 4)) for n, x, y in marks]
    _number_marks(pix, [(n, x * ratio, y * ratio) for n, x, y in marks], radius=int(radius * ratio))
    save_pixmap(pix, "manual_window_tour.png")

    # 3. The Properties dock of the heatsink and of a via of the example board
    for kind, name in (("heatsink", "manual_properties_heatsink.png"), ("via", "manual_properties_via.png")):
        win.canvas.set_selection([(kind, 0)])
        win._on_canvas_selection([(kind, 0)])
        app.processEvents()
        save_pixmap(win.dock_inspector.grab(), name)

    # 4. The New board dialog (shown, not executed: exec() would wait for a click)
    dlg = NewBoardDialog(win)
    dlg.show()
    app.processEvents()
    save_pixmap(dlg.grab(), "manual_new_board.png")
    dlg.close()

    # 5. Preferences on its first section (the libraries)
    pref = PreferencesDialog(win)
    pref.resize(980, 520)
    pref.show()
    pref.sections.setCurrentRow(0)
    app.processEvents()
    save_pixmap(pref.grab(), "manual_preferences.png")
    pref.close()

    # 6. The keyboard list (Help - Keyboard shortcuts)
    keys = ShortcutsDialog(win.SHORTCUTS_HTML, win.theme_name, win)
    keys.resize(1100, 700)
    keys.show()
    app.processEvents()
    save_pixmap(keys.grab(), "manual_shortcuts.png")
    keys.close()

    win.doc.stack.setClean()
    win.close()
    return written


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        for f in main_manual(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images")):
            print(f)
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--fem":
        for f in main_fem(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images")):
            print(f)
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--surface":
        for f in main_surface(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images")):
            print(f)
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "--import":
        for f in main_import(sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images"), sys.argv[2]):
            print(f)
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "--views":
        for f in main_views(sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images"), sys.argv[2]):
            print(f)
        sys.exit(0)
    for f in main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images")):
        print(f)
