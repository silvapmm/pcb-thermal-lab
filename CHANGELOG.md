# Changelog

All notable changes are recorded here. The project follows [Semantic Versioning](https://semver.org/):
MAJOR for incompatible changes, MINOR for new features, PATCH for fixes. Releases are tagged `vMAJOR.MINOR.PATCH` on `main`.

## [Unreleased]

### Added
- **Power profiles**: a heater can have a square wave (period or frequency with unit, duty, power while on and off; the average is derived) instead of a constant power.
  Every heater is either replaced by its average power or simulated in time, decided per heater from the oscillation in °C (default 1 °C) with a shared error budget;
  heaters in both regimes run together. Works in all three models (FVM, Lumped, Analytic modal), start from the steady state of the average power or from a typed
  temperature, run until the cycle repeats / for N cycles / for a fixed time, step cap 200,000. Results: temperature versus time, peak, minimum, oscillation,
  steady bounds with the average and the peak power, peak-temperature map and the last window as frames. Steady models can use the average (default) or peak power.
- GUI: "Power profile" tab (editor, decisions, settings) and "Power profile" results tab; CLI: `run --duration/--cycles/--time-s/--initial-c/--threshold-c/--steady-power`,
  `example --which profile`; `profile_<model>.csv/png` and `peak_map_<model>.png` outputs.
- Model labels in the GUI: "Finite volume (FVM), reference", "Thermal network (LPTN)", "Analytical (Fourier series)"; temperature differences shown in °C (thermal resistance stays in K/W, the same number as °C/W).

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
