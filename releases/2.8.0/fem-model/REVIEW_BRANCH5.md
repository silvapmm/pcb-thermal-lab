# Review of FEM branch 5 (`feature/fem-gui`)

Reviewer's record of the window branch: the FEM checkbox, its memory and pyamg rows, the Run rule, the two mesh boxes, the Results views and read-outs, the guide, the tests and the screenshots (5 commits on `development` `eabe7a8f`; spec `BRANCH5_PLAN.md` as overridden by `DECISIONS_REVIEWER.md` A1 to A8; manual list `GUI_TEST_CHECKLIST.md`).

**Verdict: GO** for the merge into `development`, with the corrections of section 3 (committed with this file) and after the maintainer's whole battery. Two items of section 5 are left to the maintainer; the checks that need a person at a screen are listed in section 6.

**How it was checked**: the real `MainWindow` driven offscreen by scratch scripts (`QT_QPA_PLATFORM=offscreen`, light and dark theme), with the runs going through the real calculation process (`gui/compute.py`, spawned) as the user's runs do; one heavy Python at a time under a lock, every run below 2.5 GB. A run without pyamg was made in **both** processes (a package `pyamg` that raises `ImportError`, put first on `PYTHONPATH`, which the spawned job process inherits): `femcore.available()` was false in the window and in the job. Python 3.13, pyamg 5.4 installed otherwise, macOS arm64, 16 GB.

## 1. The checklist, item by item (offscreen)

| Item | Result | Evidence (printed) |
| :-- | :-- | :-- |
| A1 window opens, version | done | title 'untitled - PCB Thermal Lab 2.7.1' |
| A2 six boxes, FEM present, off, tooltip | done | `Finite elements (FEM), comparison`, unchecked, enabled; tooltip has '0.4 to 0.9 %', 'no surface' of a block, no '0.2 %' |
| A3 Preferences default models has FEM | done | `preferences.MODELS` ends with `fem`; the Solver page builds one box per entry (two columns) |
| A4 pyamg | done | installed; the no-pyamg runs are F4 |
| B1 to B4 drawing, undo, board fields | not testable offscreen as the user does it (mouse and typing); covered by the existing `test_gui.py` / stress tests, which pass |
| C1 four models, progress | done with FVM, FDM, FEM on the example board at 2 mm | progress texts 'Solving FVM', 'Solving FDM', 'Solving FEM (assembly and solve: a large board can take minutes)', 'Done: ...'; combos of Temperature, Gradients, Profiles, Models: `FVM, FDM, FEM` |
| C2 Models tab rows | done | three rows FVM 85.29 / FDM 84.62 / FEM 83.64 degC (column Tmax), FEM 'Error vs ref' -2.7 % (see 2.3) |
| C3 FEM never in Animation / Power profile lists | done | Animation combo FVM, FDM, Analytic; Power profile combo empty without a profile; the stress test with a profile asserts 'steady state only' for FEM alone |
| D surface read-out of FVM and FDM | done through the existing stress tests (`test_surface_*`, pass); the FVM title 'surface (top), estimate, upper side' on the plate |
| E1 Muzychka case 2, FVM + FDM + FEM at 1 mm | done | FEM 84 375 unknowns, 2.0 s, no 'left out' |
| E2 FEM Surface (top) at the centroids | done | **97.47, 103.85, 101.33, 99.99 degC** against the paper's 97.40, 103.82, 101.28, 99.94 (+0.03 to +0.07 K); title 'FEM - surface (top), resolved max 103.9 °C (column max 99.3 °C, +4.600 K, +6.20 % of the rise)', colour bar 'Surface temperature, resolved' |
| E3 FEM column at the centroids | done | **95.44, 99.23, 97.57, 97.10 degC**, 2.0 to 4.6 K below the surface |
| E4 FVM / FDM surface | done | FVM 97.97, 105.11, 102.34, 100.75 (+0.57 to +1.29 K over the paper); FDM 97.92, 105.11, 102.32, 100.72; their column equal to the FEM column within 0.05 K |
| E5 part table with the FEM | done | header 'Max °C (surface, resolved)', rows 97.5 / 103.9 / 101.3 / 100.0; tooltip 'Resolved by the finite elements (not an estimate) ... +4.600 K (+6.195 % of the rise) ... Hottest node under the part: 103.880 °C' |
| E6 FEM alone, every tab | done | reference `fem`, every tab rendered (screens looked at) |
| E7 card title | done | `_overlay_card['title'] == 'FEM'` (render looked at, dark theme) |
| E8 metal block with the FEM | done | block table FEM alone 'Block, bottom, 46.3, 46.4' (FVM 47.0, 47.1); no block surface entry; Layer box has 'Metal block (bottom)' and the two copper Surface entries only |
| F1 big board 400 x 300 mm, 4 layers, 0.25 mm | done | FVM row 'at least 7680000 unknowns, about 91.1 GB of 10.3 GB; above the memory limit ... 0.7 mm'; FEM row 'the FEM mesh would have about 47370823 unknowns, more than the 6000000 it accepts: use a coarser cell; it will be left out' (the mesh cap, not the memory law, so no cell is offered: see 5.3) |
| F2 FVM + FEM, FEM refused | done | at 1 mm: FVM green, FEM 'about 23.1 GB of 10.3 GB; above the memory limit, it will not run: use a cell of 1.7 mm or more', Run enabled; FEM alone: Run disabled with the reason in its tooltip; Lumped + FEM at 0.25 mm: Run enabled |
| F3 slanted outline | done | row 'FEM: the FEM needs a rectangular or axis-aligned outline ...; it will be left out', Run enabled; the run gives `['fvm']` and the warning; FEM alone: Run disabled with the reason |
| F4 without pyamg (both processes) | done, **defect found and corrected** (3.1) | small 2-layer board FEM alone: 6048 unknowns, runs in the job process by the direct solver (`cg` 0); example board FVM + FEM at 2 mm: row 'FEM: 67229 unknowns, more than the direct solver takes; it needs the package pyamg ... and will be left out', the run answers with the FVM; FEM alone: see 3.1 |
| F5 cancel a FEM run | done | example board at 1 mm (275 724 unknowns): Stop after 4 s, 'Cancelled.' in 0.50 s, the job process gone (child processes 2 before, 1 after: the resource tracker), the next FVM run works |
| F6 mesh boxes | done | greyed with 'Greyed: used only by the FEM ...' unless the FEM is ticked; unknowns 6048 / 8736 (gap 10) / 14 508 (refinement 3) on the small board; the row follows |
| G1, G2 save and reopen | done | FVM + FEM: file `"models": ["fvm"], "comparison_models": ["fem"]`, mesh numbers absent at their defaults, written after an edit (`fem_gap_elements` 10, `fem_refine` 3.0); reopened with the same models and values; FEM only reopens as FEM only |
| G3 open in v2.7.1 | done by the gate test | `PCBT_COMPAT_V271=1 tests/test_format_compat_271.py` passes (run in this review) |
| G5 save twice identical | done | byte-identical |
| H1 export to a folder | done | `report.txt`, `summary.json`, `field_fvm.csv`, `field_fem.csv`, `fields_*.png`, `profiles.png`, `comparison.png`; no surface files, as decided |
| H2 `--surface-files` with `--model fem` | done | `surface_fem.csv`, `surface_fem_top.png`, `surface_fem_bottom.png`; 'FEM surface (resolved): top 103.7 degC' at 2 mm |
| H3, H4 picture tool bar, report | H4 done (report has 'hottest node', 'resolved by the finite elements'); H3 not testable offscreen (a file dialog) |
| I1, I2 thick-plate warning | done, **defect found and corrected** (3.2) | S2, S3, S4 warn, S1 (10 W) silent; 35 um: no warning |
| J1 Preferences tick then New | partly: the list and `api.default_options()` accept `fem`; the dialog itself was not clicked |
| J2 guide | done (text read against the window; corrected in 3.3) | |
| J3 tooltips of the new controls | done | FEM box, both mesh boxes, Surface entries, Components headers; `test_tooltips.py` passes |
| J4 shortcuts, J5 About | done | `SHORTCUTS_HTML` unchanged; About names 'finite elements' and pyamg (MIT) |
| J6 light and dark | done | renders in both themes looked at (rows readable) |
| K random use | **not run** (the three random-action tests take about 7 minutes; skipped as instructed); their FEM pool was bounded in this review (3.5) |

## 2. Code against the decisions and the physics

1. **Run rule** (`panels.py` `_update_cells`): `v.model not in api.SKIPPABLE_MODELS or len(models) == 1`, the API's rule; a mesh refusal (0 unknowns) prints its own reason (A8). Holds; checked in F1 to F3.
2. **Memory row**: `verdicts()` and `_auto_cell` use `GUARDED_MODELS` with `fem`; `verdicts()` passes `fem_params`. `_auto_cell` does not (`api.suggest_cell_mm` has no `fem_params`): Auto ignores edited mesh numbers (5.3).
3. **The agreement quoted in the tooltip and the guide.** 'On plain boards 0.4 to 0.9 % below the FVM, mostly the finite volumes' own error' is the measurement of `REVIEW_BRANCH4.md` 3. On the example board (vias, a part 3 cells wide at 2 mm), which is the first board a user ticks the FEM on, it does not hold: measured here (API, column Tmax, this tree): FVM 60.293 / 60.465 / 60.412 K at 2 / 1 / 0.5 mm (moves 0.3 % then 0.1 %), FEM 58.638 / 59.686 K at 2 / 1 mm, **-2.7 % and -1.3 %**: there the FEM is the coarse one, converging from below. The tooltip says 'plain boards' and stays; the guide paragraph now gives the example-board numbers and says to halve the cell (3.3).
4. **Hottest node** (`analysis.point_max`): reads `arrays["T_point"]` of the part's outer face under the part's cell weights; `heater_rows` and `problem.heaters` are one-to-one, so `heaters[len(rows)]` is the right part. Values printed: 103.880 degC (S2) against the surface element mean 103.851 degC.
5. **Jobs and cancel**: the FEM runs in the spawned job process like every model; cancel stops the process (F5).
6. **Stress changes**: `ALL_MODELS` unchanged (A7); the profile loop gains `("fem",)` (only with pyamg) and `("fvm", "fem")`; the live-check loop gains `("fvm", "fem")`. The random actions could tick the FEM on any board below their 3e5-cell cap: a 400 x 300 mm 4-layer board at 2 mm is 120 000 cells there and 755 872 FEM unknowns, 'about 5.9 GB of 10.3 GB' green in the panel (F1): unbounded time and memory on the 16 GB machine. Corrected (3.5).
7. **`test_model_lists.py` exceptions in `checks.py`**: the small-part rule (`"layered"` / `"solid3d"`: the sub-layer of the layered models and the slabs of the solid; the FEM has its own 'part below two fine elements' warning in `check_fem`) and the two via-at-the-edge literals (a cut footprint on the cell grid). Justified; the reason text said the FEM meshes every barrel as a hollow tube, while 8 of the 9 vias of the example board are a rod (warning 'fem: 8 of 9 vias are a rod ...'): reworded.
8. **Label 'FEM gap elements'**: the tooltip says what it is (elements across every dielectric gap), the range and default (2 to 24, 6), the effect (0.1 mK between 6 and 12) and the cost; complete.
9. **Model lists**: `fieldscale.MODEL_SHORT`, `Preferences.MODELS`, the verdict names, `results_view` 'n/a' note (now `tips.model_label`) all name the FEM.

## 3. Defects found and corrected on the branch

1. **A FEM alone whose mesh needs pyamg failed the run** (program, medium). Without pyamg, FEM alone on the example board at 2 mm: the row said 'will be left out', Run stayed enabled, and the run ended in a 'Simulation failed' box. Now the row says 'will not run: install it or use a coarser cell' and Run is blocked with that reason, like a refusal; next to other models it is still 'left out' (`panels.py`). The box of a blocked run was titled 'Cannot run: not enough memory' also for a mesh or pyamg reason: now 'Cannot run' (`main_window.py`). Test `test_the_fem_alone_without_pyamg_on_a_large_mesh_blocks_run`.
2. **The thick-plate warning was wrong for a FEM reference** (program text, medium). With the FEM alone on the plate it said 'the models keep one temperature through the thickness' and 'The surface estimate of this model ...': false for the FEM, which resolves the plate. `checks.check_thick_plates(..., model=)` (called with `sim.reference.model`) now says 'hotter than its column mean (the headline read-out)', 'the column read-out is the mean through the thickness, which the finite elements resolve', 'The surface resolved by the finite elements under the part is 4.6 K above the column mean' and 'compare the resolved surface'. The bound and the firing rule are unchanged (S2, S3, S4 warn, S1 silent); the FVM wording is unchanged. Test `test_the_thick_plate_warning_of_a_fem_reference_says_resolved`.
3. **Guide** (document): the FEM paragraph gains the example-board numbers (2.3) and the pyamg rule when the FEM is alone; the Auto note says 'the 3D solid or the FEM' (a refused FEM also enlarges Auto's cell).
4. **Read-out names** (program text, low). The metal-block table showed 'Mean °C' / 'Max °C' without a read-out: now '(block)', with a tooltip (the mean through the block, no surface for any model; the FEM too). The temperature headers of the zone, hotspot and Summary tables get tooltips naming the column read-out (`tips.COLUMN_TABLE_TIP`, `BLOCK_TABLE_TIP`, `MODEL_TABLE_TIP`); the block table is 110 px high so its two rows still show under a two-line header. Test `test_the_tables_name_their_read_out`. `analysis.block_stats` docstring: FVM, FDM or FEM.
5. **Surface tooltips** (text, low): `SURFACE_ENTRY_TIP`, `SURFACE_MAX_TIP`, `COLUMN_HEADER_TIP` and the Temperature Layer-box tip opened with 'an estimate' for every model (the FEM sentence came after); reworded so the FVM/FDM estimate and the FEM resolved surface are said side by side. The Layer-box tip no longer says the Surface entries are for 'thick copper' only (they are always there).
6. **Random actions bounded** (test): the FEM is in the pool only on boards of at most `FEM_MONKEY_CELLS` = 20 000 cells (plan cells x layers at the run's cell): about 170 000 unknowns, 10 s, 1.5 GB at most (the example board at 1 mm: 32 000 cells, 275 724 unknowns, 15 s, 2 GB).
7. **Tests**: `test_the_main_window_progress_message_for_the_fem` checked only `MODEL_SHORT`: renamed `test_the_card_title_of_the_fem`.

CHANGELOG, `docs/versions.md`, `docs/models.md` and `docs/decisions-log.md` updated in the same commit. No number of any model moves (text, window and test changes only).

## 4. Runs of this review (all pass)

* `tests/test_fem_gui.py`, `test_model_lists.py`, `test_thick_plate.py`, `test_tooltips.py`, `test_help.py`, `test_docs.py`, `test_license_header.py`, `test_version.py`, `test_preferences_layout.py`, `test_results_views.py`: 922 passed before the corrections; after them, with `test_warning_severity.py`, `test_fem_model.py` and `PCBT_COMPAT_V271=1 test_format_compat_271.py`: 984 passed; `test_gui.py`, `test_preferences_layout.py`, `test_license_header.py`, `test_version.py`, `test_model_lists.py`: 39 passed.
* `tests/test_gui_stress.py -k "(fem or surface or profile or live) and not random"`: 9 passed (2 min 25 s; the profile loop with the FEM 105 s); after the block-table change `-k "not random and (block or component or surface or odd or fem)"` with `test_gui.py`: 47 passed.
* **Not run**: the three random-action tests (`test_random_user_actions`, about 7 minutes; skipped as instructed) and the whole battery (the maintainer's).

## 5. Open for the maintainer

1. **Summary table header text.** The Models table ('Tmax °C', 'Tmean °C', 'ΔT °C') now names its read-out in the header tooltips only. Adding '(column)' to the header text, as for the zone table, is consistent with the rule but changes the Summary pictures of the guide (regenerated at the documentation review). Recommendation: add it in 2.8.0 with the screenshot pass.
2. **Duplicate warnings and wording of a left-out comparison model** (`api.py`, branch 4, now visible in the window): a slanted outline or a missing pyamg gives two lines, the live check ('The finite-element model (FEM) cannot be built ... will be left out') and the guard ('the finite elements (FEM) was not run: ...', ungrammatical and lower case). Recommendation: keep one line (the guard's, capitalised, 'The finite-element model (FEM) was not run: ...') in a small `fix/` branch; several tests match the text 'was not run'.
3. **Auto with the FEM.** `_auto_cell` does not pass the mesh numbers (`suggest_cell_mm` has no `fem_params`), and a FEM refused for its mesh cap gives no 'use a cell of c mm' (F1). Both only matter for unusual mesh numbers or huge boards; recommendation: 2.9.0 with the memory law.

## 6. What a person must still look at (not testable offscreen)

Mouse drawing and typing in the board fields (B), the Preferences dialog clicked through to a New project (J1), the figure tool bar saving a Surface map (H3), real hover of the tooltips at the screen's size and font, the timing of Stop on a slow FEM in a visible window, and the 10 minutes of random use (K). The committed screenshots `simulation_fem.png` and `results_fem_surface.png` were looked at: right content, readable; the maps show the palette banding of the shrunk PNGs, as the other screenshots of the guide.
