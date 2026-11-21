#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_manual_callouts.py
@brief Renders the screenshots of the user manual that carry numbered red boxes (`docs/images/manual_<name>_callouts.png`) and writes the list that explains each box beside them (`<name>.md`).

@details Question it answers: which control is box N of a picture of the manual? Every box is the Qt geometry of the widget it numbers (`tools/manual/callouts.py`),
         and the list of the same call is what the manual prints under the picture, so the numbers of the picture and of the list cannot drift apart.
         The pictures are in the LIGHT theme and show the version in the status bar. The README and the in-app guide keep the plain screenshots of
         `examples/make_screenshots.py`; only the manual embeds the annotated ones.

         Usage: python examples/make_manual_callouts.py [--import <rp2040 folder of pcb-library>] [output_folder]
                (default folder: docs/images). The lists (`<name>.md`, pasted under the pictures in the manual) go to the folder named by the
                environment variable PCBT_CALLOUT_LISTS, default `output/callouts` of the repository (git-ignored).
         `--import` adds the three pictures of the import window (they need the Gerber folder of the RP2040 minimal design, BSD-3-Clause).
"""

import os
import shutil
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")
# Neutral configuration folder: Preferences shows the path of user_defaults.json, which must never be a personal path in a committed picture
NEUTRAL_CONFIG = "/tmp/pcbthermal-config"
os.makedirs(NEUTRAL_CONFIG, exist_ok=True)
os.environ["PCBTHERMAL_CONFIG"] = NEUTRAL_CONFIG
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QRect, QSettings, Qt                    # noqa: E402
from PySide6.QtWidgets import QApplication, QGroupBox, QWidget                         # noqa: E402

from pcbthermal import SolverOptions, simulate                              # noqa: E402
from pcbthermal.examples import example_board                              # noqa: E402
from pcbthermal.gui.main_window import TAB_RESULTS, TAB_STACKUP, MainWindow   # noqa: E402
from tools.manual.callouts import Callout, grow, render, union             # noqa: E402

WIDTH, HEIGHT = 2000, 1200            # The window of the pictures, in logical pixels
DOCKS = (420, 560)                    # Widths of the Board settings and Simulation settings docks


def _assert_neutral(path):
    """!
    @brief Refuse to save a picture while the configuration folder is not the neutral one.
    @param path Path of the picture about to be written (used in the message).
    @return None
    @throws RuntimeError If PCBTHERMAL_CONFIG is not the neutral folder.
    """
    if os.environ.get("PCBTHERMAL_CONFIG") != NEUTRAL_CONFIG:
        raise RuntimeError(f"PCBTHERMAL_CONFIG is not neutral; refusing to write {path}")


def find(root, cls_name, text):
    """!
    @brief The first visible descendant of a widget of the given class whose text starts with `text`.
    @param root Widget to search.
    @param cls_name Name of the Python class of the widget (for example "QCheckBox").
    @param text Beginning of its text().
    @return The widget.
    @throws LookupError If none is found (the picture would then mark nothing).
    """
    for w in root.findChildren(QWidget):
        if type(w).__name__ == cls_name and w.isVisibleTo(root.window()) and hasattr(w, "text") and w.text().startswith(text):
            return w
    raise LookupError(f"no {cls_name} with the text {text!r} under {root}")


def first(root, cls_name):
    """!
    @brief The first visible descendant of a widget whose Python class has the given name.
    @param root Widget to search.
    @param cls_name Name of the class (for example "QTableWidget").
    @return The widget.
    @throws LookupError If there is none.
    """
    for w in root.findChildren(QWidget):
        if type(w).__name__ == cls_name and w.isVisibleTo(root.window()):
            return w
    raise LookupError(f"no {cls_name} under {root}")


def tool_widget(win, *actions):
    """!
    @brief One target around the tool bar buttons of some actions.
    @param win The main window.
    @param actions The QActions of the tool bar.
    @return A target for `Callout`.
    """
    return union(*[win.toolbar.widgetForAction(a) for a in actions])


def make_saver(app, out_dir, lists_dir, written):
    """!
    @brief The function that renders one annotated picture and moves its list to the lists folder.
    @param app The QApplication (its events are processed before every grab).
    @param out_dir Folder of the PNG files.
    @param lists_dir Folder of the Markdown lists.
    @param written List that receives the path of every PNG written.
    @return A function `save(widget, name, callouts, **kw)`; `kw` goes to `render` (region, zoom).
    """
    def save(widget, name, callouts, **kw):
        app.processEvents()
        path = os.path.join(out_dir, f"manual_{name}_callouts.png")
        _assert_neutral(path)
        render(widget, callouts, path, **kw)
        shutil.move(os.path.splitext(path)[0] + ".md", os.path.join(lists_dir, f"{name}.md"))
        written.append(path)
    return save
    

def new_window(app, theme="light"):
    """!
    @brief The main window with the example board in the light theme, docks as in the other manual pictures.
    @param app The QApplication.
    @param theme Theme name of the settings.
    @return The shown MainWindow.
    """
    settings = QSettings(os.path.join(tempfile.mkdtemp(), "callouts.ini"), QSettings.IniFormat)
    settings.setValue("theme", theme)
    win = MainWindow(settings=settings)
    win._load_problem(example_board(), "example-4layer")
    win.resize(WIDTH, HEIGHT)
    win.show()
    app.processEvents()
    win.resizeDocks([win.dock_board, win.dock_sim], list(DOCKS), Qt.Horizontal)
    app.processEvents()
    win.canvas.fit()
    return win


def page_callouts(win, extra):
    """!
    @brief The callouts of the Summary page: the row of Results page tabs first (the other pages do not repeat it), then `extra`.
    @param win The main window.
    @param extra List of Callout objects of the page.
    @return List of Callout, the page tabs first.
    """
    tabs = Callout(win.results.tabs.tabBar(), "**Results pages.** Summary, Temperature, Gradients, Profiles, Components, Models, Animation and Power profile (chapter 5). The page shown here is Summary; the other pictures of this chapter show one page each.")
    return [tabs] + extra


def scenes_main(app, win, save):
    """!
    @brief The pictures of the main window: the numbered tour, the tool bar and the Simulation settings dock.
    @param app The QApplication.
    @param win The main window of `new_window`.
    @param save Function `save(widget, name, callouts, **kw)` of `make_saver`.
    @return None
    """
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])

    # 1. The tour of the window (chapter 3.1): the same nine areas and the same list as before, now boxes
    save(win, "window_tour", [
        Callout(win.menuBar(), "**Menu bar**: File, Edit, View, Simulation and Help (section 3.2). On macOS the menus are in the menu bar at the top of the screen."),
        Callout(win.toolbar, "**Tool bar**: the drawing tools, polygon mode, the Layer box, the Map and Display buttons, snap, fit, the grids and Run (section 3.3)."),
        Callout(win.dock_board, "**Board settings** dock: size, board outline and environment (section 3.4)."),
        Callout(win.dock_elements, "**Elements** dock: the list of every zone, heater, heatsink and via, with a filter field (section 3.5)."),
        Callout(win.tabs.tabBar(), "**Main tabs**: Board, Stack-up, Power profile and Results (section 3.6)."),
        Callout(win.canvas, "**The board** (Board tab): the drawing canvas with rulers along the top and left edges and a scale bar at the bottom left."),
        Callout(win.dock_sim, "**Simulation settings** dock: the Run button, the models to run, the settings and the live warnings (section 3.7)."),
        Callout(win.dock_inspector, "**Properties** dock: every field of the selected element (section 3.8)."),
        Callout(win.statusBar(), "**Status bar**: what the selected tool does, the state of a run, messages; the version at the right end.", badge_left=True),
    ])

    # 2. The tool bar, enlarged (chapter 3.3)
    tb = win.toolbar
    last = tb.widgetForAction(win.a_run)
    strip = QRect(0, 0, last.mapTo(tb, last.rect().topRight()).x() + 16, tb.height())      # the tool bar ends at Run; the rest of the width is empty
    save(tb, "toolbar", [
        Callout(tool_widget(win, *win.tool_actions.values()), "**Drawing tools**: Select (`S`), Copper zone (`Z`), Heater (`H`), Heatsink (`C`), Via (`V`) and Board outline (`O`)."),
        Callout(tool_widget(win, win.a_poly), "**Polygon mode** (`P`): draw polygons by clicking their corners instead of dragging rectangles."),
        Callout(win.layer_combo, "**Layer** box: the one layer choice of the program, for the drawing, the map on the board and every Results map."),
        Callout(tool_widget(win, win.a_overlay), "**Map** (`T`): the temperature map on the board, after a run."),
        Callout(win.display_button, "**Display** (`D`): how every map is drawn (underlay, opacity, view, contours, colour map; section 5.9)."),
        Callout(win.snap_combo, "**Snap**: the step that positions snap to."),
        Callout(tool_widget(win, win.a_fit), "**Fit board** (`Ctrl+0`): zoom to the whole board."),
        Callout(tool_widget(win, win.a_grid, win.a_sgrid), "**Grid** (`G`) and **Solver grid** (`Shift+G`): the drawing grid and the cells the solver will use."),
        Callout(tool_widget(win, win.a_run), "**Run** (`F5`): runs the selected models; while a calculation runs it reads Stop."),
    ], region=strip, zoom=1.6)


def scenes_results(app, win, save):
    """!
    @brief The Results pages with numbered boxes (chapter 5): Summary, Temperature, Difference, Profiles, Components, Models and Animation.
    @param app The QApplication.
    @param win The main window of `new_window`.
    @param save Function `save(widget, name, callouts, **kw)` of `make_saver`.
    @return None
    """
    res = win.results
    # The pictures of the Results pages keep the tool bar and the centre, and leave out the Simulation settings and Properties docks (their own pictures
    # show them): a narrower picture is scaled down less, so its boxes and badges are smaller against the controls
    full_save = save
    crop = QRect(0, 0, win.dock_sim.x(), win.height())

    def save(widget, name, callouts):
        full_save(widget, name, callouts, region=crop)

    win.doc.set_options(models=("fvm", "lumped", "analytic", "fdm", "solid3d", "fem"), cell_mm=1.0)
    six = ("fvm", "lumped", "analytic", "fdm", "solid3d", "fem")
    sim_all = simulate(win.doc.problem, SolverOptions(cell_mm=1.0, models=six))
    win._on_done(sim_all)
    win.tabs.setCurrentIndex(TAB_RESULTS)
    app.processEvents()

    # The Summary page (chapter 5.1)
    res.tabs.setCurrentIndex(0)
    save(win, "results_summary", page_callouts(win, [
        Callout(res.model_table, "**Table of the models**: one row per model that ran, with Tmax (column and surface), Tmean, ΔT, Rθ, the power, the energy balance, the error against the FVM and the time (the columns are listed above)."),
        Callout(find(res, "QPushButton", "Warnings"), "**Warnings (N)** box: the rows of the Simulation settings plus what only a run can know; click a row to read it (section 5.11)."),
        Callout(res.report, "**Text report** of the run: the reference model, the hotspots, the read-outs, the hottest surfaces, each heater, the parts by model and the zones."),
    ]))

    # The Temperature page (chapter 5.2)
    res.tabs.setCurrentWidget(res.temp)
    t = res.temp
    app.processEvents()
    save(win, "results_temperature", [
        Callout(win.layer_combo, "**Layer** (tool bar): the copper layer shown. Here it also offers All layers, All (2 × 2), Surface (top), Surface (bottom) and, when there is one, the Metal block."),
        Callout(win.display_button, "**Display** (tool bar): view (Current, Smooth, Terrain), underlay, contours and colour map of every map (section 5.9)."),
        Callout(union(find(t, "QLabel", "Model"), t.model), "**Model**: which model's map is drawn. The map on the board follows this choice."),
        Callout(union(t.diff_on, t.diff_ref), "**Difference to**: the map of the model minus a reference model, in K (section 5.12)."),
        Callout(t.hot, "**Hotspot contour**: draws the line of the Hotspot limit of the Simulation settings."),
        Callout(union(t.auto, t.vmin, t.vmax), "**Auto range** or your own colour limits."),
        Callout(t.toolbar, "**Plot tool bar**: home, back, forward, pan, zoom, subplots, customise and save the picture."),
        Callout(t.canvas, "**The map** with its colour bar. The hottest sample has a red ring, the coolest a blue ring; the title gives both values and the mean of the layer."),
    ])

    # The Difference view (chapter 5.12)
    t.model.setCurrentIndex(t.model.findData("lumped"))
    t.diff_on.setChecked(True)
    app.processEvents()
    save(win, "results_difference", [
        Callout(win.layer_combo, "**Layer**: decides what is compared. A copper layer compares the column mean of that layer in both models; Surface (top) or Surface (bottom) compares the surface read-out."),
        Callout(union(find(t, "QLabel", "Model"), t.model), "**Model**: the model to look at (here the LPTN)."),
        Callout(union(t.diff_on, t.diff_ref), "**Difference to** and its reference box (the FVM at the start). An item that cannot be used is greyed and its tooltip says why."),
        Callout(t.diff_note, "**Verdict line**: whether the difference of the hottest points is usual for this pair of models (judged at the 1 mm cell of the validation); in the warning colour when a choice cannot give a difference."),
        Callout(t.diff_export, "**Export statistics…**: writes the numbers of the view (largest and smallest difference with their positions, mean, RMS, the verdict) to a small CSV file."),
        Callout(t.canvas, "**The difference map**: model minus reference in K, white at zero, red where the model is hotter, blue where it is cooler; the red ring marks the largest difference and the blue ring the smallest."),
    ])
    t.diff_on.setChecked(False)
    t.model.setCurrentIndex(t.model.findData("fvm"))

    # The Profiles page (chapter 5.4)
    res.tabs.setCurrentWidget(res.profile)
    win.a_overlay.setChecked(True)
    app.processEvents()
    p = res.profile
    save(win, "results_profile", [
        Callout(p.axis, "**Along x** or **Along y**: the direction of the cut."),
        Callout(union(p.pos, p.pos_label), "**Cut** slider and the position of the cut (the row or column plotted)."),
        Callout(p.cut_overlay, "**Cut overlay**: a small picture of the board with the cut line, inset in the corner with the fewest curve points; it is part of the figure and of a saved PNG."),
        Callout(p.canvas, "**The curves**: the temperature along the cut for every model that ran, with the cut overlay (the cut line over the map of the reference model, since the Map button is on)."),
    ])
    win.a_overlay.setChecked(False)

    # The Components page (chapter 5.5)
    res.tabs.setCurrentIndex(4)
    app.processEvents()
    save(win, "results_components", [
        Callout(res.reference_line, "**Reference line**: names the model of every number of the page (the FVM when it ran, otherwise the first model that ran)."),
        Callout(res.heater_table, "**Heaters**: power, mean and maximum board temperature under the part (column), the junction temperature, the margin to Tj max, the power limit and the top-path power."),
        Callout(res.zone_table, "**Zones**: Mean, Max and Min of the column read-out of each zone."),
        Callout(res.hot_table, "**Hotspots**: Tmax (column) at the hot-spot point, its position and the area."),
        Callout(res.comp_canvas, "**Chart of the parts**: the mean and the maximum board temperature under each heater (column) and its junction temperature."),
    ])

    # The Models page (chapter 5.6)
    res.tabs.setCurrentWidget(res.compare)
    app.processEvents()
    c = res.compare
    save(win, "results_models", [
        Callout(union(c.title_max, c.table_max), "**Tmax** table: the hottest point under each part, °C (column); one row per part, one column per model that ran, the reference first and in bold."),
        Callout(union(c.title_mean, c.table_mean), "**Tmean** table: the mean under each part, °C (column)."),
        Callout(c.canvas, "**Bar chart of the whole board**: Tmax (column) and Tmean (all layers), one bar per model."),
    ])

    # The Animation page (chapter 5.7 and 4.11)
    res.tabs.setCurrentWidget(res.animation)
    a = res.animation
    a.t_end.setValue(120.0)
    a.frames.setValue(30)
    a.compute.click()
    while a.tr is None:
        app.processEvents()
    a.slider.setValue(int(a.slider.maximum() * 0.55))
    app.processEvents()
    save(win, "results_animation", [
        Callout(union(find(a, "QLabel", "Model"), a.model), "**Model** of the animation (FVM, FDM, Analytic and, while it is ticked, the FEM)."),
        Callout(union(find(a, "QLabel", "Duration"), a.t_end, a.frames), "**Duration** and the number of **Frames** (10 to 400)."),
        Callout(union(find(a, "QLabel", "Scheme"), a.scheme, a.spacing), "**Scheme** (Crank-Nicolson or Implicit Euler) and **Spacing** of the frames (logarithmic or linear time)."),
        Callout(a.compute, "**Compute**: solves the response of the board to the powers switched on at t = 0."),
        Callout(a.status, "**Status line**: what to do, the state of the computation and any warning of the time model."),
        Callout(union(a.play, a.slider), "**Play** and the time **slider**."),
        Callout(union(a.fps, a.export), "**Speed** of the playback and **Export GIF…**."),
        Callout(a.canvas, "**The frame** at the time of the slider, drawn with the Display choice; the title gives the time and the hottest value of the frame."),
    ])
    return None


def scene_settings(app, win, save):
    """!
    @brief The Simulation settings dock with numbered boxes (chapter 3.7), after a run so that the status line and the warnings are filled.
    @param app The QApplication.
    @param win The main window.
    @param save Function `save(widget, name, callouts, **kw)` of `make_saver`.
    @return None
    """
    win.tabs.setCurrentIndex(0)
    sp = win.solver_panel
    win.dock_inspector.hide()                                # the Simulation settings dock then has the whole height: every box of the picture is in view
    win.dock_sim.resize(win.dock_sim.width(), win.dock_sim.height())
    app.processEvents()
    save(win, "simulation_settings", [
        Callout(sp.run, "**Run simulation** (`F5`). It becomes **Stop** while any calculation runs."),
        Callout(sp.status, "**Status line**: the result of the last run (for example the hottest point and Rθ), or why a run was cancelled, failed or cannot start."),
        Callout(union(find(sp, "QCheckBox", "Finite volume"), find(sp, "QCheckBox", "Thermal network"), find(sp, "QCheckBox", "Analytical")), "**The three main models** (FVM, LPTN, Analytic), ticked by default."),
        Callout(union(find(sp, "QCheckBox", "Finite difference"), find(sp, "QCheckBox", "3D solid"), find(sp, "QCheckBox", "Finite elements")), "**The three cross-check models** (FDM, 3D solid, FEM), off by default (ticked here, for the pictures of the Results pages); a thin line separates them from the main ones."),
        Callout(union(sp.cell, sp.auto_cell), "**Cell size** and **Auto**: the solver cell in mm. Auto sets the cell from the heaters and enlarges it to the smallest one that the memory limit accepts for the models ticked (section 4.9)."),
        Callout(sp.hot, "**Hotspot limit**: the temperature above which an area is reported as a hotspot, in °C (100 °C unless you change it)."),
        Callout(find(win.dock_sim, "QPushButton", "Warnings"), "**Warnings (N)**: the live input warnings, one closed row each; click a row to read it (section 5.11)."),
    ], region=QRect(win.dock_sim.mapTo(win, win.dock_sim.rect().topLeft()), win.dock_sim.size()))


def scenes_stackup(app, win, save):
    """!
    @brief The Stack-up tab in the advanced mode with numbered boxes (chapter 4.7).
    @param app The QApplication.
    @param win The main window.
    @param save Function `save(widget, name, callouts, **kw)` of `make_saver`.
    @return None
    """
    win.doc.stack.setClean()
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
    app.processEvents()
    sp = win.stackup_page
    save(win, "stackup", [
        Callout(sp.mode, "**Stack-up** list: Simple (equal layers, one FR-4) or Advanced (each layer on its own)."),
        Callout(sp.typical, "**Load typical stack-up**: the typical build for the layer count."),
        Callout(sp.inner_oz, "**Inner copper of the typical stack-up**: 0.5 oz (the default) or 1 oz, for 3 or more layers."),
        Callout(union(sp.unit, sp.scale), "**Units** (µm, mm or both) and **Scale** (Readable, with thin layers enlarged, or True proportions)."),
        Callout(sp.view, "**Cross-section** of the board, drawn to the Scale chosen; click a layer to see its thickness, conductivities, density and specific heat in the line under it."),
        Callout(first(sp, "StackupEditor"), "**Layer table** (advanced stack-up): the thickness of each copper layer and of each dielectric gap, its material and its conductivities through and in the plane."),
        Callout(win.board_panel.materials_box, "**Materials**: the conductivity of copper and the via plating thickness."),
    ])


def scenes_import(app, board_dir, save):
    """!
    @brief The three steps of the Gerber import window with numbered boxes (chapter 9), on the RP2040 minimal design (BSD-3-Clause).
    @param app The QApplication.
    @param board_dir Folder with the Gerber files, the drill file and the placement file of the RP2040 minimal design.
    @param save Function `save(widget, name, callouts, **kw)` of `make_saver`.
    @return None
    """
    from pcbthermal.gui.import_window import ImportBoardWindow

    # A copy of the files under a neutral name, so that no path of this machine can appear in a picture
    work = os.path.join(tempfile.mkdtemp(), "rp2040")
    shutil.copytree(board_dir, work)
    settings = QSettings(os.path.join(tempfile.mkdtemp(), "callouts_import.ini"), QSettings.IniFormat)
    settings.setValue("theme", "light")
    win = MainWindow(settings=settings)
    win.resize(WIDTH, HEIGHT)
    win.show()
    app.processEvents()
    dlg = ImportBoardWindow(win)
    dlg.confirm = lambda *a: True
    dlg.notify = lambda *a: None
    dlg.resize(1280, 820)
    dlg.show()
    dlg.open_path(work)
    for _ in range(200):                                     # the files are read in the background: wait until the parts are known
        app.processEvents()
        if dlg.session.parts():
            break
        time.sleep(0.05)
    dlg.page1.source.setText("rp2040/gerber")                # Display only: the path of the copy is a temporary folder of this machine
    app.processEvents()
    p1 = dlg.page1
    boxes1 = p1.findChildren(QGroupBox)
    save(dlg, "import_step1", [
        Callout(dlg.stepper, "**Stepper**: the three steps, Files and layers, Parts and Model; click a step to go to it."),
        Callout(union(find(p1, "QLabel", "Folder, ZIP"), p1.source, find(p1, "QPushButton", "Folder"), find(p1, "QPushButton", "ZIP"), find(p1, "QPushButton", "Files")), "**Source**: a folder, a ZIP archive (read in memory, never extracted to disk) or files one by one; or type a path and press `Enter`."),
        Callout(p1.table, "**Files**: every file with the function detected from its X2 attributes, its Excellon header or its name; the function is a list you can change and the Use box leaves a file out."),
        Callout(union(p1.tool_label, p1.tool_pick), "**CAD tool** that wrote the files; it only gives better defaults for the file-name rules."),
        Callout(boxes1[1], "**Board** box: the copper layers and the typical stack-up for that count, the outline (size and area) and the drills."),
        Callout(union(p1.layer_pick, p1.preview), "**Preview** of the selected copper layer, the outline and the holes. The wheel zooms, a drag pans, a double click shows the whole board."),
        Callout(union(dlg.early_btn, dlg.back_btn, dlg.next_btn), "**Import now**, **Back** and **Next**: Import now imports with the defaults of the later steps."),
    ])

    # Step 2: the RP2040 chip (a QFN) selected, with a power so that it is a heat source and its pad outline is dashed
    des = next((p.designator for p in dlg.session.parts() if "QFN" in (p.footprint or "")), dlg.session.parts()[0].designator)
    dlg.session.set_part(des, power=1.5)
    dlg.go(1)
    p2 = dlg.page2
    p2.refresh()
    p2.selected = des
    for r in range(p2.table.rowCount()):
        if p2.table.item(r, 1) is not None and p2.table.item(r, 1).text() == des:
            p2.table.selectRow(r)
            p2.table.scrollToItem(p2.table.item(r, 1))
    app.processEvents()
    save(dlg, "import_step2", [
        Callout(p2.info, "**Count of parts** and how they were found (matched by position, paste only, placement only)."),
        Callout(p2.table, "**Parts table**: the Source column says how each part was found; tick **Heat source** and give a **Power** in W, a **Tj max** and a **Role**."),
        Callout(p2.findChildren(QGroupBox)[0], "**Shape** of the heat source of the selected part: the exposed pad or tab, the convex hull of the paste openings or the bounding box; the line under the choices says what was found for the part."),
        Callout(union(find(p2, "QPushButton", "Make selected"), find(p2, "QPushButton", "All parts with"), find(p2, "QPushButton", "All matched")), "**Make selected a heat source**, **All parts with a power** and **All matched parts**: tick the parts in one step."),
        Callout(union(p2.side, p2.preview), "**Preview** with the designators and the holes: white squares are matched paste openings, red ones match no part; the pad outline of the selected part is dashed."),
        Callout(p2.warn, "**Matching findings**: a placement file that does not fit, parts matched by position, differences between the X3 layer and the placement."),
    ])

    dlg.go(2)
    p3 = dlg.page3
    app.processEvents()
    boxes3 = p3.findChildren(QGroupBox)
    save(dlg, "import_step3", [
        Callout(boxes3[0], "**Copper mapping**: the flow-based faces (recommended); *Advanced* holds the older mappings, kept for comparison."),
        Callout(boxes3[1], "**Mask pixel** and **Cell size**, each with an **Auto** button (the pixel is the thinnest line of the files and at most a tenth of the cell)."),
        Callout(p3.mem, "**Memory verdict**: comes before anything is drawn."),
        Callout(boxes3[2], "**Board** of the new project: the copper layers, **Vias up to** (the largest plated hole that is a via) and the project name."),
        Callout(lambda root: _warnings_rect(root, p3), "**Warnings** (the import still runs): what the LPTN and Analytic do with imported copper, a coarse cell or pixel, and where a Gerber job file disagrees with the file list."),
        Callout(p3.preview, "**Preview** of the solver grid of the cell chosen on the left."),
    ])
    dlg.close()
    win.doc.stack.setClean()
    win.close()


def _warnings_rect(root, page):
    """!
    @brief Rectangle of the warnings list of step 3: from its title to the top of the preview.
    @param root The grabbed window.
    @param page The Step3Page.
    @return QRect in the logical pixels of `root`.
    """
    title = find(page, "QLabel", "<b>Warnings</b>")
    left = title.mapTo(root, title.rect().topLeft())
    top = page.preview.mapTo(root, page.preview.rect().topLeft())
    return QRect(left.x(), left.y(), title.width(), top.y() - left.y() - 4)


def main(out_dir, board_dir=None):
    """!
    @brief Produce every annotated picture of the user manual and the lists that go under them.
    @param out_dir Folder that receives the manual_*_callouts.png files.
    @param board_dir Folder of the RP2040 minimal design (BSD-3-Clause) for the import pictures, or None to skip them.
    @return List of written PNG paths.
    """
    _assert_neutral(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    lists_dir = os.environ.get("PCBT_CALLOUT_LISTS") or os.path.join(ROOT, "output", "callouts")
    os.makedirs(lists_dir, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    written = []
    save = make_saver(app, out_dir, lists_dir, written)
    win = new_window(app)
    scenes_main(app, win, save)
    scenes_results(app, win, save)
    scene_settings(app, win, save)
    scenes_stackup(app, win, save)
    win.doc.stack.setClean()
    win.close()
    if board_dir:
        scenes_import(app, board_dir, save)
    return written


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    board = None
    if "--import" in args:
        k = args.index("--import")
        board = args[k + 1]
        del args[k:k + 2]
    for f in main(args[0] if args else os.path.join(ROOT, "docs", "images"), board):
        print(f)
