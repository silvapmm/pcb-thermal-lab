# Changelog

All notable changes are recorded here. The project follows [Semantic Versioning](https://semver.org/):
MAJOR for incompatible changes, MINOR for new features, PATCH for fixes. Releases are tagged `vMAJOR.MINOR.PATCH` on `main`.

## [Unreleased]

### Changed
- **Sink is now called Heatsink** everywhere (class, `add_heatsink`, `Problem.heatsinks`, JSON key `heatsinks`, application labels, documentation). Project files saved with the key `sinks` and the old editor files still open.

### Added
- **Metal block**: a Heatsink with a thickness (material, interface resistance, extra coefficient for fins) is a heat spreader in the FVM and FDM with lateral conduction, mass and a contact only over the copper it overlaps; block results (table, temperature view, report), checks, `example block`; validated against a 3D solid within 1.8 %.

Next: the Component element (Package 2R, heat sink, passive areas) in its own version, then Gerber import and a variable stack-up (see `docs/roadmap.md`).

## [2.3.0] - 2026-10-16

The finite-difference model in time.

### Added
- The **FDM now also does the time-dependent work**: power-step animation (Animation tab, `transient --model fdm`, GIF export), step responses and the power-profile time simulation, with the same theta-method as the FVM on the grid points (the hottest point follows the FVM within 0.7 °C on the example; the profile peak is 3 % lower at 2 mm, where the 6 mm heater is three cells wide). With only the FDM selected it also makes the average-or-resolve decision.
- `transient --model fvm|fdm|analytic`.

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
- The 3D finite-element check now models vias (copper rods) and sinks; `examples/validation_study.py [--fem]` prints the tables of the new `docs/validation.md`.
- Documentation reduced to three documents: `docs/models.md`, `docs/validation.md`, `docs/roadmap.md`.
- **Calibration of the convection**: `calibrate_convection` / `pcbthermal calibrate board.json --measured 85 [--heater U1]` fits the convection multiplier to one measured steady temperature.
- `examples/fem3d_validation.py`: independent 3D finite-element check (scikit-fem, offline) of the three models; results in `docs/validation.md`.
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
