# Changelog

All notable changes are recorded here. The project follows [Semantic Versioning](https://semver.org/):
MAJOR for incompatible changes, MINOR for new features, PATCH for fixes. Releases are tagged `vMAJOR.MINOR.PATCH` on `main`.

## [Unreleased]

### Fixed
- **Interface leftovers**: the Simulation footer no longer takes a low window (the warning list is limited to a quarter of the dock and the settings keep a strip of 120 px); the count of unknowns is not cut to one line; a decimal comma pasted from the right-click menu of a number field is read as a point; a click on a warning after an edit and before the check is ignored instead of selecting another element.

## [2.4.3] - 2026-10-29

### Fixed
- **3D solid keeps the copper of a via larger than its cell**: the copper of a via whose area exceeds a cell is spread over the cells of its disc instead of being clipped to the one that holds its centre (a 0.5 mm copper fill kept 32 % at 0.25 mm cells); smaller vias do not change.
- **Zones that meet inside a cell** keep the copper of both: the zones of a layer are combined by the union of their points (`geometry.zone_fill`) and not by the larger of their shares of a cell, which lost the copper of the other zone (5 to 15 % too cool on real copper, 0.6 to 0.7 K in the test case). The example boards do not change. The input check also warns of a zone whose outline crosses itself.
- **Input check for a heat source that carries component fields**: a source (role `source`) with `theta`, `theta_jc_top`, `theta_sa`, `interface`, `contact_area` or a top sheet set, from a file or the API, is warned that they are ignored; `tj_max`, `psi_jb` and `power_tc` keep working on a source (new tests).
- **Interface cleanups**: the model comparison plot writes the names of the models (`Lumped (LPTN)`) and not the keys; a log axis of more than six decades gets a tick every three decades (the step of the engineering notation) so that its labels no longer crowd; the inner tab bar of the Results keeps whole names and scrolls; Preferences open 980 x 600 so that the Defaults page has no horizontal bar; the vertical ruler leaves out a label that would reach the corner where `mm` is written.
- **Unknowns shown next to the cell size** are the ones the models have: `fvm.unknowns` and `fdm.unknowns` count the laminate nodes of a one-layer board and the layers of the metal blocks, as the models build them (the panel showed 2400 for 9600 on a one-layer 60 x 40 mm board with a block at 1 mm); the FDM count is shown when the FDM is selected.
- **Via diameter is the drill**: the field, its tooltip, the docstrings, the user guide and `docs/models.md` say *Drill diameter* (the plating is inside it, finished hole = drill minus twice the plating), which is what the model has always used; before they called it the finished hole, and a user who typed the hole of a fabricator drawing got 18 % less copper than the board has. No number changes.
- **Top path only on a component**: a heat source (role `source`) that carries `theta` and `theta_sa` from a file or the API ignores them; before, the report showed a top resistance with no heat through it, and with an interface under the source a hidden top path cooled the part by 39 K in the test case.
- **Metal block beyond the board outline** is cut at the outline in the FVM, FDM and 3D solid; before, it drained into the cells off the board and the part read about 38 K too cold (FVM 66.8 against 104.7 degC on the test board) without any warning. The input check now measures the block against the outline.

### Changed
- **Licence header**: every Python file starts with the copyright and MIT notice of Pedro Silva (PMS Labs); `tests/test_license_header.py` checks it for new files.

## [2.4.2] - 2026-10-29

### Added
- **Power Calculator, design uncertainty**: a *Board description* list (none, CAD, hand, estimated) adds copper coverage, copper weight, inner planes and vias to the best / nominal / worst band (default *hand*: the example of `docs/calculators.md` 1.1b goes from 1.62-2.31 to 1.56-2.34 W; *none* reproduces the old band).
- **Thick-plate warning** when `q'' t / (2 k)` of a copper layer or a metal block under a heater exceeds 5 % of its rise (a bound, never added to the result).
- **Natural convection form** of a vertical board, `general` (default, bit-identical) or laminar (Churchill and Chu), with a range warning (`Board.natural_form`, Environment panel, CLI `--natural-form`).
- **Inner copper 0.5 oz (default) or 1 oz** for the typical stack-ups, all dielectrics kept; 6.9 to 7.5 K cooler on the example with inner planes (`docs/validation.md` 14.1).
- **Independent 3D solver in the tests** (`tests/helpers/layered3d.py`, `tests/test_layered_vs_3d.py`).

### Fixed
- **Interface**: numbers with the decimal point and engineering notation outside 0.01 to 10000 whatever the system language (a comma typed in a field is read as the point); docks of a usable width with the Run button always in sight; a list of all input warnings that selects the element; keyboard focus kept after an edit; readable Preferences; low-contrast notes; two grid icons told apart; no tooltip on command buttons; models table without a scroll bar; texts for a first-time user; the name Power Calculator.
- **One-layer boards**: two laminate nodes in FVM, FDM and Lumped and a series film in the Analytic; the 3D solid keeps the laminate (a 20 mm pad read 120 degC against about 74 degC); mean error against the 3D solid 3.8 to 1.0 % on nine boards.
- **Boards with an outline**: the cells off the board no longer count as a path to the air (a round board had a time constant of 0.02 s instead of about 107 s); the whole edge is counted (a 60 mm T lost 70 of 240 mm; a disc 2 to 6 %).
- **Side walls of a finned block** no longer carry the fin ratio: the rise of a finned block was 5.5 to 6.4 % too low.
- **Top path on small pads**: the split is a root, not a fixed-point loop that stopped 17 to 58 K cold with a false runaway warning (MOSFET: 33.2 instead of 90.9 degC).
- **A 3D-solid run that never ended**: the 3D solid is limited to 250 000 unknowns, checked before building, with the cell that fits; a cancel kills a process that survives SIGTERM.
- **Lumped**: rings narrower than a cell are merged, so the result no longer grows with the ring count.
- **Smaller**: the Analytic heat balance with a metal block closes (was 9 % off); the block map on a one-layer board; a power loop that does not settle warns; the stack-up templates note and validation section 14 (6 and 8-layer rows had no bottom copper).

### Documentation
- Times and memory of the solves replaced by the measured table (example board at the 250 000 limit: 15 s and 3.5 GB; layered FVM about 3 GB per million unknowns); stale branch pointers removed; corrections from the reviews of the research folders in `docs/validation.md`, `theory.md`, `models.md`, `calculators.md` and `research.md`.
- Screenshots regenerated (three new: power calculator, 1 oz stack-up, vertical natural convection).
- `docs/versions.md` shortened to one entry per version; the program roadmap is now its chapter "Planned" (`docs/roadmap.md` removed); the dates of our own work removed from the technical documents.

### Changed
- Licences: everything of ours is MIT; the README lists the licence of every dependency and what the LGPL of Qt means for a bundled executable.
- **Investigations in `research/`**: the studies of `examples/` moved to one folder per investigation (README with numbered results, `figures/`, `INTEGRATION.md`, `scripts/`); the index is `research/README.md`. Reproducing the block study corrected its case count to 74.
- Plate check of the metal block: +0.6 %, -0.8 % and -4.6 % from Seri Lee's article (centre, edge, corner), not +4.5 %.

## [2.4.1] - 2026-10-22

### Changed
- Licensing: the MIT License is now stated consistently in `LICENSE`, the README, the About box and `CLAUDE.md` (they previously said "All rights reserved"). Added a note that the results are a design aid, not validated against a physical board.

## [2.4.0] - 2026-10-22

### Added
- **Advanced stack-up** in all five models: copper thickness per layer and thickness, conductivities, density and specific heat per dielectric gap (presets for FR-4, high-Tg, polyimide, PTFE-ceramic, metal-core, alumina, AlN); the simple stack-up is unchanged. New **Stack-up tab** between Board and Power profile with the cross-section drawn in µm and mm (true or readable proportions), the total thickness, a click on a layer for its data, and the layer table. Validated against the exact series circuit (1e-6 K). `docs/models.md` section 8, `docs/validation.md` section 12.
- **Board outline polygon** (any shape: presets, vertex table, outline tool `O`) in the FVM, FDM and 3D solid; the lumped and analytic models run on the rectangle of the same area (box and positions scaled by sqrt(area ratio)), with a warning in the Results summary; against the FVM on the real shape they are 0.2 to 3 % off for parts away from the edge (bounding box: 6 to 10 % cool), more near the edge (`docs/validation.md` section 13). Blank cells in the plots, edge loss along the outline, parts off the board still deliver their power. `docs/models.md` section 9.
- **Top path of a part** (heatsink on the package): `theta_jc_top`, `interface`, `theta_sa`; within 0.4 to 0.8 K of a junction-node prototype (`research/component-heatsink/scripts/top_path_study.py`).
- **Power Calculator** (Simulation menu): the power of a part from a measured temperature, by the board model (`pcbthermal.inverse`) or from a datasheet ψ/θ parameter.
- **Calculations in a separate process** (`pcbthermal/jobs.py`, `gui/compute.py`): a Cancel button and `Ctrl+.`, a window that never freezes, and a process that stops when the program closes or dies.
- **Help menu**: an HTML user guide (`pcbthermal/help/index.html`, `F1`, in the program or in the browser) and an About box with version, author and project link.
- **A tooltip on every control** (`gui/tips.py`, checked by `tests/test_tooltips.py`), rulers and a scale bar on the board, position and size fields for the selected shape, tab shortcuts `Ctrl+1` to `Ctrl+4`.
- **Right-click menu on the board**: add a vertex on the nearest edge of a shape (then drag it), delete a vertex, duplicate, delete; on an empty spot add a heater, zone, heatsink or via there. The geometry is in `geometry.insert_vertex`.
- **Properties panel in titled boxes** (Part, Junction, Package top, Interface, Heatsink on the package, Copper, Position and size, ...). A heatsink is *Manual input* (typed as **h** or as **θSA**, with the equivalent of the other shown) or *Metal block* (boxes Metal block, Interface, Fins, Extra cooling). New interface preset **Direct contact** (no material, R = 0).
- **Simple stack-up and Materials moved to the Stack-up tab** (right of the cross-section; in the advanced mode the rows that only belong to the simple one are hidden); the Board panel keeps size, outline and environment.
- **Typical stack-ups checked against fabricators' tables** (JLCPCB, PCBWay; Eurocircuits and Sierra catalogue limits): the maximum temperature moves by under 0.5 % between them (`research/stackup/scripts/stackup_vendor_check.py`, `docs/validation.md` section 14).
- `docs/versions.md` (chapter 'Planned') is now two lists (what has been implemented, what we want to implement); the Component evidence moved to `docs/research.md` with its bibliography; the fabricator sources are in `docs/validation.md` section 10.
- **Metal block in the Lumped and Analytic models** (steady state): one more layer of the ring network, and a graph of tiles condensed into the Green-function correction; 2.0 % and 1.1 % off the FVM on average, 4.8 % and 4.3 % at most in 74 cases (the equivalent coefficient was 15 to 31 % off); no time simulation for them with a block. **Fields that do not apply are greyed**: the top path of a part without θ and θSA, the solver settings of a model that is not selected.
- **Verification**: the fins against a 2D solution of one fin (24 cases within 0.08 %, `research/block-and-fins/scripts/fin_validation.py`), the 3D solid against Yovanovich's spreading resistance table (0.7 to 0.8 %) and a grid-convergence study (GCI 1.14 %, `research/solid3d-verification/scripts/solid3d_verification.py`); `docs/validation.md` sections 15 and 16.
- **Fix**: dragging a vertex handle no longer drags the whole selected polygon along (Qt moves every selected movable item with the dragged one); only the vertex follows the mouse. Switching a heatsink to a metal block no longer carries its manual `h` into the block's extra cooling (it starts at 0).
- **Fix**: the side panels (Board, Simulation, Properties) are in scroll areas, so a field below the visible part (for example *Position and size* of a zone in a short window) can always be reached; the Properties dock gets a bit more height by default.
- **Via fill**: a via barrel can be open, filled with epoxy resin (the usual fabricator "filled via", +0.1 %), conductive paste (+5 %) or electroplated copper (×3.3, −3.9 K on the example board); the old checkbox "Filled with copper" became the *Fill* list (old files read as before). **Power from the top of the package** in the power calculator (θ and ψJT); `docs/validation.md` sections 18 and 19 (the copper dominates the result: 11 to 45 % error for a wrong board).
- **Preferences** (menu Edit, `Ctrl+,`): the material libraries (via fills, metals, interface materials, dielectrics, package families) and the defaults of a new board, of new elements, of the materials and of the solver live in `pcbthermal/data/defaults.json`; a user file in the configuration folder (`user_defaults.json`, only the differences) overrides them, is edited in the new window, can be exported, imported and reset, and the status bar, a start-up message and the About box say when it is in use. The via *Fill* list shows names only, with the typical conductivity in an editable field below.
- **Power Calculator** reworked: simpler name, the parameters (θ junction-pad, ψJT) inside the window, hints on every field and on every option of *Measured at*, a result with the temperatures at the power found and the board resistance, validated against two datasheet boards (`docs/calculators.md`, `research/power-calculator/scripts/calculator_validation.py`). **The program starts with an empty board**; the example is in File - Open example. Preferences: one tab with four boxes for the defaults of new projects.
- **Power Calculator**: two tabs for the two independent routes, a window that keeps its size (unused parameters are greyed), a **Help** button with a formatted explanation, and an **uncertainty band** (best case / nominal / worst case from the copper ±25 %, heat transfer ±30 %, θ ±20 %, ψJT ±30 % and the reading ±1 K, editable in Preferences) with a selector for the power written into the part.
- **Heater Type**: *Heat source* (power and the interface under it) or *Component* (junction, package, top path); the package family list fills the typical θ junction-pad, θJC(top) and Tj max from a library in Preferences (new columns); old files infer the type.
- **Heatsink on the package**: two lists, the typical heatsink and its air flow (catalogue θSA with source and conditions, a library in Preferences, only the flows the catalogue gives) fill θSA, which stays editable; the boxes of the top path (package top, interface) appear as soon as θSA is above zero and are not shown without a heatsink; the family and heatsink notes are one short line with the source in the tooltip; the family note for a custom part reads "Custom: no typical values applied".
- `docs/versions.md`: what was implemented in every version, where and how it is tested. `research/stackup/scripts/stackup_outline_study.py`.

- **Typical stack-ups by layer count** in an editable JSON file (`pcbthermal/data/stackups.json`), loaded when the number of layers changes and by *Load typical stack-up* on the Stack-up tab; `docs/models.md` section 12 lists them and what is inside the dielectric.
- Interface material presets (paste, gap pads) for the heatsink on a package; θSA from the datasheet for the Heatsink element; rounded-corner preset, Subdivide button and `geometry.rounded_rectangle`; `docs/models.md` sections 13 and 14.

- **Cooling model of the Heatsink**: *Coefficient* (extra h or θSA) or *Metal block, computed* from its thickness, metal, interface and **fins** (height, thickness, pitch: area gain with fin efficiency; warning when the fins are too close in still air). Contact area of a part's interface (lid or exposed top), body helper for θJC(top), several sheets in one dielectric gap (`combine_sheets`). `docs/models.md` sections 15 to 18.

- The interface between a heatsink and the board or the package is **one dielectric sheet with its own material and thickness** (preset, thickness, conductivity, resulting K·cm²/W), for the metal block and for the heatsink on a part.

### Changed
- Changing the number of layers loads the typical stack-up of the new count (a 4-layer board is now 1.586 mm).
- Tool keys are now `S Z H C V O` (Select, Zone, Heater, Heatsink/Cooling, Via, board Outline); `V` is the via tool.
- The Environment panel hides the typed `h top` and `h bottom` in computed mode (they were only a starting guess), and every field shows its unit.
- The edge loss of the FVM and FDM no longer adds the board edge conductance to the layers of metal blocks (it was counted twice).

### Fixed
- Dragging a via (or any element) no longer moves it by its own coordinates off the board; elements and selections cannot leave the board when dragged, nudged or moved.
- Leaving the application no longer leaves a calculation running.

### Added (earlier in this cycle)
- **Parts**: a heater can be a part with a junction-to-pad resistance `theta` (worst case: all the power enters the board; the old `theta_jb` key still opens), a maximum junction temperature (margin, **power limit** and warning), `psi_jb` (second estimate from the board temperature in the ring around the package) and a **power temperature coefficient** (power solved together with the board, thermal runaway detected). Typical θ by package family, hints and a datasheet guide in the application; the Components tab shows the junction, margin and power limit. `docs/models.md` section 6, `docs/validation.md` section 9, `research/component-heatsink/scripts/component_study.py`, `tests/test_component.py`.
- **Top path of a part** (heatsink on the package): `theta_jc_top`, `interface` (K·cm²/W over the footprint) and `theta_sa` (K/W) make the part a junction node joined to the board by θ and to the ambient through the top; the board receives only the power the top does not take (fixed-point loop around any model, together with the power coefficient). The report and the Components table give the top-path power and its share; steady-state models only. Within 0.4 to 0.8 K of the junction-node prototype on four chips; `research/component-heatsink/scripts/top_path_study.py`, `docs/models.md` section 6, `docs/validation.md` section 9.
- `docs/research.md` for investigations before implementation.

### Added
- Metals (aluminium, copper, brass, carbon steel, stainless 304) and interface presets (good paste, default paste, gap pads) for the Heatsink block in the application; default block conductivity 204 W/mK (was 205); `research/component-heatsink/scripts/heatsink_study.py` and the typical values in `docs/versions.md` (chapter 'Planned') 1.9c.

Next: the Component element (Package 2R, heat sink, passive areas) in its own version, then Gerber import and a variable stack-up (see `docs/versions.md` (chapter 'Planned')).

## [2.3.0] - 2026-10-16

The finite-difference model in time, metal blocks, the Heatsink rename and a 3D solid model.

### Added
- The **FDM now also does the time-dependent work**: power-step animation (Animation tab, `transient --model fdm`, GIF export), step responses and the power-profile time simulation, with the same theta-method as the FVM on the grid points (the hottest point follows the FVM within 0.7 °C on the example; the profile peak is 3 % lower at 2 mm, where the 6 mm heater is three cells wide). With only the FDM selected it also makes the average-or-resolve decision.
- `transient --model fvm|fdm|analytic`.
- **3D solid model** (`solid3d.py`, key `solid3d`, "3D solid (finite volumes), comparison" in the application, `--model solid3d|compare`): the board as a real 3D solid on the plan grid with real slabs (every copper layer, four per dielectric gap, metal blocks as pad and metal slabs, vias with their real copper area); steady state, SciPy only; the number of 3D unknowns is shown and a too large model is skipped with a warning. Within 0.2 % of an independent finite-element solid on three boards and 1.6 % on a 20 mm pad; within 0.3 % of the FVM on ordinary scenarios. Validation tables of `docs/validation.md` now include it.
- `research/component-heatsink/scripts/component_study.py`: what a Component parametrisation adds on five real parts (one resistance to the pad adds 2 to 28 % of the rise, a top path matters only with a heatsink); results and the proposed minimal Component in `docs/versions.md` (chapter 'Planned') 1.9b.
- `research/solid3d-verification/scripts/copper_dissipation.py` and `tests/test_copper.py`: the outer copper dissipates and spreads heat by itself and a heatsink works through the copper under it (FVM within 2.5 % of a 3D solid for pads of 20 mm and more).
- **Metal block**: a Heatsink with a thickness (material, interface resistance, extra coefficient for fins) is a heat spreader in the FVM and FDM with lateral conduction, mass and a contact only over the copper it overlaps; block results (table, temperature view, report), checks, `example block`; validated against a 3D solid within 1.8 %.

### Changed
- **Sink is now called Heatsink** everywhere (class, `add_heatsink`, `Problem.heatsinks`, JSON key `heatsinks`, application labels, documentation). Project files saved with the key `sinks` and the old editor files still open.

## [2.2.0] - 2026-10-16

Power tables and CSV, a finite-difference model, validation against a 3D solid and a cleaner documentation.

### Fixed
- A result that arrives after the design was edited during the run is marked outdated (it was shown as current).
- The application aborted when a simulation started while an animation or an analysis was still computing (the sparse direct solver of SciPy is not safe in two threads); background calculations now wait for each other.
- Node fields (FDM) in the plots, hotspot list, heater statistics and the board overlay.

### Added
- **Power tables and CSV files**: a heater can follow any piecewise-constant power over time (`TableProfile`), repeating or run once (a start-up or mission profile with the last power held), read from and written to CSV files (`time_s,power_w`, comment lines, optional units, errors with the line number).
  GUI: "Table (CSV file)" profile with **Import CSV…** and **Export CSV…** buttons (a square wave is exported as a table); CLI: `run --profile HEATER=file.csv`; project files store tables.
  The average-or-resolve decision works for any periodic table (periodised step response), one-shot tables are always resolved, and several repeating profiles are simulated over the least common multiple of their periods.
- **Analytic transient with vias and sinks**: one modal system per heater with the smeared via (or sink) conductance scaled so that its steady response equals the locally corrected steady model; the example's temperature curve now follows the FVM within 2.5 °C
  (10 °C before) and the profile peak within 0.5 %. Animation of the power step also for the Analytical model (selector in the Animation tab).
- **Finite-difference model** (`pcbthermal/fdm.py`, checkbox "Finite difference (FDM), comparison" in the application, `--model fdm` or `--model compare`, `models=("fdm",)`): node-centred FDM of the same layered physics, steady state only; area sampling of the copper and of the heater footprint by default (classic point sampling optional).
- **About 40 % faster direct solves** (symmetric sparse ordering) in the FVM, the FDM and the time simulations.
- The 3D finite-element check now models vias (copper rods) and sinks; `research/models-comparison/scripts/validation_study.py [--fem]` prints the tables of the new `docs/validation.md`.
- Documentation reduced to three documents: `docs/models.md`, `docs/validation.md`, `docs/versions.md` (chapter 'Planned').
- **Calibration of the convection**: `calibrate_convection` / `pcbthermal calibrate board.json --measured 85 [--heater U1]` fits the convection multiplier to one measured steady temperature.
- `research/solid3d-verification/scripts/fem3d_validation.py`: independent 3D finite-element check (scikit-fem, offline) of the three models; results in `docs/validation.md`.
- `examples/csv_profiles/`: documented example board with three profile CSV files, scripts and a README.

## [2.1.0] - 2026-10-16

Power profiles and computed heat transfer coefficients.

### Added
- **Power profiles**: a heater can have a square wave (period or frequency with unit, duty, power while on and off; the average is derived) instead of a constant power.
  Every heater is either replaced by its average power or simulated in time, decided per heater from the oscillation in °C (default 1 °C) with a shared error budget;
  heaters in both regimes run together. Works in all three models (FVM, Lumped, Analytic modal), start from the steady state of the average power or from a typed
  temperature, run until the cycle repeats / for N cycles / for a fixed time, step cap 200,000. Results: temperature versus time, peak, minimum, oscillation,
  steady bounds with the average and the peak power, peak-temperature map and the last window as frames. Steady models can use the average (default) or peak power.
- GUI: "Power profile" tab (editor, decisions, settings) and "Power profile" results tab; CLI: `run --duration/--cycles/--time-s/--initial-c/--threshold-c/--steady-power`,
  `example --which profile`; `profile_<model>.csv/png` and `peak_map_<model>.png` outputs.
- Model labels in the GUI: "Finite volume (FVM), reference", "Thermal network (LPTN)", "Analytical (Fourier series)"; temperature differences shown in °C (thermal resistance stays in K/W, the same number as °C/W).

- **Computed heat transfer coefficients** (`Board.h_mode = "computed"`): natural and forced convection plus radiation per face from the mean face temperature, orientation, emissivities, air speed and a global calibration multiplier of the convection, solved by iteration (3 to 4 solves) in all three models. GUI: Environment panel; CLI: `run --computed-h --air-speed --orientation --emissivity --h-multiplier`.
- Profile plot: a fast wave is drawn as a band, the hottest-point line is no longer hidden.

### Notes
- The analytic transient uses vias and sinks smeared over the board (a warning quantifies the difference); use the FVM near them.

## [2.0.0] - 2026-10-16

First release of the rebuilt program. The original wxPython application (1.0.0) was replaced by a physics package and a new GUI.

### Added
- `pcbthermal` physics package without GUI dependencies, with a public API (`SolverOptions`, `simulate`, `Problem` builder in mm, project files `.pcbt.json`).
- Three models on one problem description: **FVM** (cell-centred finite volumes, sparse matrices, reference), **Lumped** (offset-contour thermal networks, one per heater)
  and **Analytic** (multilayer cosine series with local via and sink corrections). Guide: `docs/model_guide.md`.
- Exact energy balance in every result, input validity checks (`check_problem`) and model warnings, automatic cell size.
- SOR as an optional FVM solver (vectorised red-black) to compare with the sparse direct solver (default); both give the same temperatures.
- Transient response (implicit Euler, Crank-Nicolson) with real-time animation: GUI Animation tab and `transient --gif`.
- Component junction temperature (`theta_jb`), hotspot list, gradient maps, profiles, zone and heater statistics.
- PySide 6 application: board editor (rectangles, polygons, vias, sinks), undo/redo, inspector, background image, dark and light themes, background simulation,
  results tabs, temperature overlay on the board, export of reports, CSV and figures. The version is shown in the title bar, status bar and About box.
- Command line: `run`, `solvers`, `transient`, `convergence`, `convert`, `gui`, `example`, `--version`.
- 94 tests, including a documentation gate that requires Doxygen-style documentation on every function.
- Documentation: `docs/` (model guide, physics, old-versus-new comparison, findings log, candidate methods from the literature).

### Changed
- FR-4 is anisotropic (0.3 W/mK through the thickness, 0.9 W/mK in the plane); vias are hollow barrels with plating thickness; heater power is injected exactly on any grid.
- Projects use millimetres and 1-based layers; legacy editor JSON files still open.
- Dependencies are installed in a virtual environment (`.venv/`, see `requirements.txt`).

### Removed
- The wxPython editor, the old solvers (`core/`, `ui/`, `main.py`, `config.py`) and the iterations GIF (it animated solver iterations, not time). They remain in the git history.

### Fixed (relative to 1.0.0)
- FDM false convergence (step-size stop rule) and grid-dependent heater power (8.17 W injected for 5.50 W requested on the default grid).
- Dimensionally wrong Analytic formula and an inconsistent Lumped network (errors of several hundred to tens of thousands of degrees).
- FDM import failure without Numba.
Details and evidence: `docs/findings.md`.

## [1.0.0] - 2025

Original wxPython program (PCB Thermal Simulator Tool): Analytic, Lumped and FDM (SOR) solvers with an interactive editor. Kept in git history (tag `legacy-wxpython-1.0.0`).
