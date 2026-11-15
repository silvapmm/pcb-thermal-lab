# Manual test of the 2.8.0 window (for the maintainer, after `feature/fem-gui` is merged)

Written before the merge, from the code of `tmp/merge-fem-surface` (nothing was run): where a menu or label name below is a guess it is marked (?). Tick the box when the result is what is written; if you see what the 'Bug if' line says, tell me what you did and what you saw (a screenshot helps). Background for each item: `releases/2.8.0/fem-model/SURFACE_DECISIONS.md` (the surface), `REVIEW_BRANCH4.md` (the FEM), `pcbthermal/help/index.html` (the guide, chapter 'Surface temperature and column mean' and the paragraph 'Finite elements (FEM), comparison').

Start from the main checkout on the merged `development`: `.venv/bin/python -m pcbthermal gui`. Do it with the machine quiet (the FEM items solve for seconds).

## A. Start-up

- [ ] The window opens, no error box, the title shows the version. Expected: the version of `pcbthermal.__version__`. Bug if: a traceback in the terminal.
- [ ] Simulation panel, box **Models**: six boxes, FVM ticked, **Finite elements (FEM), comparison** present and **not** ticked. Hover it: a tooltip with the numbers 0.4 to 0.9 % below the FVM and 'no surface of a block'. Bug if: ticked by default, no tooltip, or the tooltip says '0.2 %'.
- [ ] Open Preferences (Solver page): the list of default models has a FEM tick, off. Bug if: missing.
- [ ] Without pyamg this is expected to still work for a small board; with it missing, a big mesh says it needs pyamg (see F). (If `pyamg` is not installed in the venv, say so in the report.)

## B. Draw a simple board

- [ ] New project; set 60 x 40 mm, 4 layers; draw one heater (a part) of 1 W in the middle and one copper zone. Expected: the board, the heater and the zone show; the live warnings box is quiet or says something sensible. Bug if: a crash while drawing or dragging.
- [ ] Undo (Cmd/Ctrl+Z) and redo (Cmd/Ctrl+Shift+Z) the last three edits. Expected: each restores the board and does not change the cell size or the ticked models (those are not undoable, on purpose). Bug if: undo changes the models or the cell.
- [ ] Board panel editing: click the **Width** box, change only it, press Tab; then check in the saved file (or by reopening) that the other fields are unchanged. Expected: only the edited field is written. Bug if: another value moves (for example the copper thickness rounds).
- [ ] Copper thickness box: type **10000** (um, 10 mm) and press Tab; leave and come back. Expected: it still reads 10000, not clipped to a smaller number. Bug if: it shows 1000, 9999 or any other value.

## C. Run FVM, FDM, Lumped, Analytic

- [ ] Tick FVM, FDM, Lumped and Analytic; cell 1 mm; Run (F5). Expected: a progress message per model, then the Results. The Temperature tab has a model combo with the four names; the hottest points agree within a few percent (the Lumped and the Analytic less closely). Bug if: a model is missing from the combo, or the progress bar sticks.
- [ ] Results > Models tab: one row per model, no scroll bar for six rows. Bug if: rows cut or a scroll bar appears with fewer than seven rows.
- [ ] Animation and Power profile tabs: the FEM never appears in their model lists, the others work. Bug if: FEM listed there.

## D. The surface read-out (FVM, FDM)

- [ ] Components table: a column **Mean °C (column)**, **Max °C (column)** and one last column **Max °C (surface, estimate)**; the headers are not cut. Hover a surface cell: the tooltip gives the difference to the column in K and in % of the rise and the surface mean. On a 35 um board the difference is tiny (about +0.001 K), still written out. Bug if: two surface columns, a cut header, or a tooltip without K and %.
- [ ] Temperature tab > toolbar **Layer** box: the entries **Surface (top)** and **Surface (bottom)** are listed after the layers (always, also for thin copper); hover one: its tooltip says 'estimate'. Choose **Surface (top)**: the map title says surface, 'estimate', and gives on a second line the column maximum with the difference in K and %. Bug if: the entries are missing on a 35 um board, or the title does not say which read-out it is.
- [ ] Choose a normal layer: the map title and the colour bar say **column mean**. Bug if: a map without the read-out named.
- [ ] Surface (bottom) on a one-layer board is the face of the copper against the laminate (a few mK from the column), not tens of kelvin. Bug if: a surface far from the column on a thin one-layer board.
- [ ] Thin against thick copper: set the copper to 2000 um on the 4-layer board (heater 20 W): the difference of the part's surface to its column grows to tenths of a kelvin or percents of the rise; the thick-plate warning may appear (see I). Back at 35 um it shrinks to mK. Bug if: the difference does not move with the thickness.
- [ ] The trap on patterned thin copper: draw a copper zone with a hole (or a hatched pour) under a heater on 35 um copper, run FVM at 1 mm. Expected: the **Surface (top)** map minus the column maximum is about 1 K or more (the bare laminate under the source), while the part's row in the Components table shows about +0.000 K (its column already includes that term); the tooltip text says so (the surface 'includes the rise across the bare laminate under a source'). Bug if: the part row shows the 1 K, or the text is silent.
- [ ] Lumped, Analytic: the part's surface cell reads **n/a** with a tooltip saying why (no surface read-out). A part on an inner layer: **n/a** with 'an inner layer has no outer face'. Bug if: a number, or an empty cell.
- [ ] Junction temperature, margin, power limit and top path are on the column (their numbers do not change when you switch the Layer box to Surface). Bug if: any of these changes with the Layer box.

## E. The FEM and the thick plate (Muzychka, Culham and Yovanovich 2003, case 2)

Build: new project 50 x 50 mm, **1 layer**, copper **10000 um**, copper k **150 W/mK**, h top about 0 (the smallest the box takes), **h bottom 400**, edges insulated (edges do not lose heat), full copper on the layer; four square heaters of 10 x 10 mm centred at (12.5, 12.5), (37.5, 12.5), (12.5, 37.5), (37.5, 37.5) mm with 10, 25, 20 and 15 W; ambient 25 degC. (The test `tests/test_fem_model.py::test_case_2_of_muzychka_the_resolved_surface_meets_the_paper` builds the same board.)

- [ ] Tick **FVM and FEM** and the **FDM**; cell 1 mm; Run. Expected: the Models tab lists three models and the FEM runs in a few seconds. Bug if: the FEM says 'left out' on this small board.
- [ ] Temperature, model **FEM**, Layer **Surface (top)**: the hottest values near the centres read about **97.5, 103.9, 101.3 and 100.0 degC** (paper: 97.40, 103.82, 101.28, 99.94; the program adds about 0.09 K for the 1 um laminate film). Hover/read the cell at each centre or use the part rows. Bug if: they differ from the paper by more than 0.15 K, or the title says 'estimate' for the FEM (it should say **resolved**).
- [ ] Same model, a normal layer (column mean): about **95.4, 99.2, 97.6 and 97.1 degC** at the centres, i.e. 2 to 4.7 K below the surface. Bug if: the column equals the surface (the plate then has no thickness effect: the source was made volumetric by mistake).
- [ ] FVM and FDM, Surface (top): about 0.6 to 1.3 K above the paper (an estimate flagged 'upper side', t/a = 1); their column about equal to the FEM column within 0.1 to 0.2 K. Bug if: the FVM/FDM surface equals their column (no estimate drawn).
- [ ] Components table with the FEM selected: the surface column is filled, and the tooltip says the surface is resolved, with the difference to the column of 2 to 4.7 K. Bug if: n/a for the FEM on a part on layer 1.
- [ ] Run again with only **FEM** ticked. Expected: the Results open on the FEM; every tab works (Temperature, Gradients, Models, Components). Bug if: an empty Results or an error box.
- [ ] The **card** on the board shows the title **FEM** (not 'fem'), and its model menu (key M) lists the models that ran. Bug if: a lower-case `fem`.
- [ ] Metal block: add a metal block on the board and run the FEM: the block table shows the block mean; there is **no surface of the block** (it is the mean through the thickness). Bug if: a block surface appears.

## F. Memory verdicts and refusals

- [ ] Make the board 400 x 300 mm, 4 layers, cell 0.25 mm, tick the FEM. Expected: the line under the models says for the FEM: N unknowns, about x GB of y GB, and either 'slow' or 'above the memory limit, it will not run: use a cell of c mm or more'; the other models have their own lines. Bug if: no FEM line, or an exception text.
- [ ] With **FVM and FEM** both ticked and the FEM refused: Run stays enabled, the run answers with the FVM and says the FEM was not run (a warning in the Results). With the **FEM alone** refused: Run is blocked (or the run stops with the cell to use). Bug if: the FVM is lost because the FEM was refused.
- [ ] A board with a slanted or curved outline and the FEM ticked: a live warning says the FEM cannot be built for this board and will be left out; the other models run. Bug if: the Run button is blocked with FVM also ticked.
- [ ] If `pyamg` is missing: a big mesh (above 30 000 unknowns) says the FEM needs the package pyamg and will be left out; a small board still runs the FEM. Bug if: the FEM is greyed on a small board without pyamg (decision 1 of `BRANCH5_PLAN.md` says it should work) or no reason is given.
- [ ] **Cancel** a long FEM run (big board, cell small enough to take a minute): the job stops, the window is usable, the next run works. Bug if: the window hangs or a ghost job remains (Activity Monitor: a Python process using CPU after cancel).
- [ ] The FEM mesh options (the two boxes under Settings, 'elements across a gap' and 'refinement'): greyed with a tooltip when the FEM is unticked; ticked, changing them changes the unknown count in the verdict line. Bug if: not greyed, or no effect on the count.

## G. Project files

- [ ] Save the Muzychka project with the FEM ticked (File > Save as), close the window, reopen the file: the FEM is ticked again with the same options. Bug if: unticked or the cell/mesh options lost.
- [ ] Save with **FEM only** ticked and reopen: FEM only ticked. Bug if: FVM ticked instead.
- [ ] Open the same file in the older version (the v2.7.1 program: `git worktree add` of the tag, or a copy installed): it must open without a refusal, with the FVM (and the FDM if it was ticked) and no FEM. Bug if: 'project is not valid' or a refusal naming `solver`.
- [ ] Open an old file of 2.7.1 or earlier in 2.8.0: it opens as before, FEM unticked, and the Surface entries exist. Bug if: a refusal or a changed number in the report.
- [ ] Save a project, open it and save it again without touching anything: the second file is identical to the first except fields you changed. (Compare with `diff`.) Bug if: values drift (10000 um becomes something else, a rounded `cell_mm`).

## H. Export

- [ ] File > **Export results to a folder**: the folder holds the report, the summary, the CSV fields and the figures; the temperature maps carry 'column mean'. Bug if: files missing or the maps without the read-out named.
- [ ] The surface CSV and the surface pictures are **not** in that folder: in this window they come only from the command line, `python -m pcbthermal run <project> --surface-files` (decision 6 of `BRANCH5_PLAN.md`); check that this command writes `surface_<model>.csv` and `surface_<model>_top/bottom.png` for the FVM and for the FEM (`--model fem`). Bug if: the command fails or the file is empty. (If the maintainer decided the menu item, test it here instead.)
- [ ] The figure tool bar of a Surface map saves the displayed picture. Bug if: it saves the column map.
- [ ] The report (TXT, JSON): has the surface lines with the difference in K and %, 'resolved' for the FEM, 'estimate' for the FVM/FDM, and for the FEM the hottest-node line. Bug if: 'estimate' on a FEM line or a missing difference.

## I. The thick-plate warning

- [ ] On the Muzychka board, run the FVM: after the run a warning (Results, Warnings box) says the surface under the part can be hotter than the layer mean by a bound in K and % (the 10 W source, 3.3 K, 4.7 % of its rise, is below the 5 % limit and stays silent; the other three warn). Read it: it should name the part, the bound `q'' t/(2k)`, and say the models give the layer mean. Bug if: no warning on the plate, a warning on the 35 um board, or a text that does not say what to do (use the FEM or the surface read-out).
- [ ] Switch the board to 35 um copper: the warning is gone. Bug if: still there.

## J. Preferences and help

- [ ] Preferences > Solver: the default-models list has FEM; tick it, Apply, make a **New** project: the FEM is ticked there; untick and restore. The memory limit is a machine preference (not saved in project files). Bug if: the FEM tick is saved inside project files as the default.
- [ ] Help (F1 or the Help menu): the guide opens; the paragraph **Finite elements (FEM), comparison** is there and names the checkbox as written in the window; the chapter 'Surface temperature and column mean' and its worked example (Muzychka) show the numbers of E. Bug if: the guide still says the FEM 'will' do something.
- [ ] Hover every new control (the FEM box, the two mesh boxes, the Surface entries, the Components table headers): each has a tooltip that says what it means, its unit and a typical value. Bug if: a control without a tooltip.
- [ ] Keyboard list (Help > Keyboard shortcuts (?)): unchanged from 2.7.1. Bug if: a shortcut listed that does nothing.
- [ ] About box: lists pyamg among the libraries (MIT) and the models. Bug if: missing.
- [ ] Light and dark theme: the verdict lines (ok / slow / refuse colours) and the Surface map titles are readable in both.

## K. Random use (10 minutes)

- [ ] Tick and untick models quickly, change the cell, undo and redo, run, cancel, switch tabs during a run, open and close projects. Bug if: any traceback in the terminal, a frozen window, or numbers that change when you run twice with the same inputs.

Report: the item letter and number, what you did, what you saw, and the terminal text if any.
