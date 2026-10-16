# CLAUDE.md

Project memory for Claude Code. Keep this file up to date as the project evolves:
record decisions, architecture, commands, and conventions here.

## Project Overview

**PCB Thermal Lab** (see `pcbthermal.__version__`; the original wxPython program was "PCB Thermal Simulator Tool" 1.0.0) is a
physics package, command line and PySide 6 application for simulating the thermal behavior of printed circuit boards (PCBs).

- Author: Pedro Silva (PMS Labs)
- License: (C) 2025 Pedro Silva. All rights reserved (see `LICENSE`).
- Users draw PCB elements (zones, heaters, vias, sinks), configure parameters,
  and run three models (keys `fvm`, `lumped`, `analytic`):
  - **Finite volume (FVM), reference**: cell-centred finite volumes on a sparse matrix (direct, CG or SOR solver), any geometry.
  - **Thermal network (LPTN)**: lumped-parameter thermal resistance network per heater (rings by distance from the footprint).
  - **Analytical (Fourier series)**: multilayer cosine series with local corrections for vias and sinks.
  - Naming: **FDM** (finite *difference*, node-centred, SOR) is the name of the *legacy* solver only; it was replaced by the FVM
    (see `docs/model_guide.md`, "FDM or FVM").
- Outputs: temperature maps, power profiles in time (square waves and CSV tables), animations, hotspots, gradients, zone and heater
  statistics, reports, CSV and figures. Projects are plain JSON (`.pcbt.json`).

See `README.md` for the full feature list.

## Technology Stack

- Python 3.13 in a virtual environment (`.venv/`, git-ignored): `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- NumPy and SciPy (physics), Matplotlib (figures), PySide 6 (GUI), pytest + pytest-qt + pytest-timeout (tests)
- Always run Python through `.venv/bin/python`; the system Python has none of the dependencies.

## Language and Documentation Rules

These rules are mandatory for all code and documentation in this repository.

1. **Everything is in English**: code, identifiers, comments, docstrings,
   documentation files, and everything git-related (branch names, tag names,
   commit messages, PR titles and descriptions; see "Git Language and Naming").
   (Conversation with the maintainer may be in Portuguese; the repository never is.)
2. **Inline comments** must be present throughout the code, using `#` in Python.
   Explain the *why* and any non-obvious step, not just restate the code.
3. **Doxygen-style documentation** is required for every module, class, function,
   and method. In Python, write it as a docstring using Doxygen commands:

   ```python
   def solve_fdm(grid, power_map, tolerance=1e-6, max_iter=5000, omega=1.8):
       """!
       @brief Solve the steady-state temperature field with the FDM/SOR method.

       @param grid       Solver grid description (cell size, layer count).
       @param power_map  2D array of heat sources in W per cell.
       @param tolerance  Convergence threshold on the max temperature change in K.
       @param max_iter   Maximum number of SOR iterations.
       @param omega      SOR relaxation factor (1 < omega < 2).

       @return numpy.ndarray Temperature field in degrees Celsius.
       @throws ValueError If the grid and power map shapes do not match.
       """
       # Validate inputs before starting the iteration
       ...
   ```

   Use at least `@brief`, `@param`, and `@return` (plus `@throws`, `@note`,
   `@see` where useful). Start each file with a `@file` / `@brief` header block.
4. Keep the documentation in sync with the code: update docstrings and this file
   whenever behavior changes. `tests/test_docs.py` fails if a module, class, function or method in
   `pcbthermal/` or `examples/` lacks `@brief`, an `@param` per argument, or an `@return` for a returned value.

## Conventions

- Style: follow PEP 8; use type hints on public functions.
- Names: `snake_case` for functions and variables, `PascalCase` for classes,
  `UPPER_CASE` for constants.
- Units: use SI units internally (m, W, K, W/m·K, W/m²·K). Convert only at the
  UI boundary, and state units in the docstring of every parameter.
- Keep solver logic (numerics) separate from GUI code so solvers can be tested
  without wxPython.
- Use the `logging` module instead of `print`.
- Never commit generated outputs (PNG, GIF, TXT reports, temp files).

## Git Workflow

- Default branch: `main`; active branch: `develop`. Do not commit features directly
  to `main`; use a branch and open a PR with `gh pr create`.
- All git text is in English (details below).
- The Claude GitHub app is installed on the repository (`/install-github-app`).

### Git Language and Naming

Mandatory, and applies to everything that ends up in the repository history or on GitHub:

- **Language**: branch names, tag names and tag messages, commit subjects and bodies, merge commit
  messages, PR titles, PR descriptions and comments, release notes and issue text are all in **English**.
  Talking to the maintainer in Portuguese does not change this.
- **Branch names**: ASCII, lowercase, kebab-case, with a type prefix: `feature/<topic>`, `fix/<topic>`,
  `docs/<topic>`, for example `feature/component-models`. No accents, spaces or Portuguese words.
  Long-lived branches are only `main` and `develop`.
- **Commit messages**: imperative mood ("Add", "Fix", "Remove"), a subject of at most 72 characters
  without a final period, then a blank line and a body that explains *why* when it is not obvious.
  One logical change per commit. Keep the attribution trailers required by the session.
- **Tags**: annotated, `vMAJOR.MINOR.PATCH` (see "Branches and Versions"), with an English message;
  non-release markers use a descriptive English name, for example `legacy-wxpython-1.0.0`.
- **Published history is never rewritten** (no force push). A message that breaks these rules is
  corrected going forward, not by rewriting history.
- Audited on 2026-10-16: all existing branches, tags, commits and the open PR already follow these rules.

## Project Structure

```
pcbthermal/            Physics core (no GUI imports) - see docs/physics_core.md
  model.py             Board, Materials, Zone, Heater, Via, Sink, Problem (+ mm builder API), JSON I/O
  geometry.py          polygon area/centroid/point-in-polygon, cell coverage fractions
  fvm.py               reference finite-volume model: steady (direct, CG, SOR) and transient
  lumped.py            ring network per heater, superposed
  analytic.py          multilayer cosine series + local via/sink corrections
  checks.py            input validity warnings (heater outside the board, no copper, copper edge across a heater, ...)
  convection.py        computed h: air properties, natural/forced convection, radiation, board_h (Picard loop is in api.py)
  profile_io.py        power profiles as CSV files (read/write)
  profiles.py          power profiles (square wave): decision average-or-resolve, window runner shared by the three models
  results.py, analysis.py, api.py (SolverOptions, simulate, suggest_cell_mm), project.py (.pcbt.json), examples.py
  plots.py             draw_* functions (any Figure) and file wrappers; no pyplot
  cli.py               python -m pcbthermal {run,solvers,transient,convergence,convert,gui,example}
  gui/                 PySide 6 app: document (undo), canvas (editor), panels, results_view, main_window, theme
tests/                 pytest suite (128 tests; GUI tests run offscreen; test_docs.py enforces Doxygen docs on every function)
examples/              example boards (.pcbt.json), accuracy_study.py, stress_study.py, solver_equivalence.py
docs/                  README.md (index), physics_core.md (current), new_approach.md, findings.md (all discoveries), candidate_methods.md (literature), thermal_models.md + legacy_vs_new.md (history of the old solvers)
ico/                   application icon
```

The original wxPython program (`core/`, `ui/`, `main.py`, `config.py`) was removed in release 2.0.0;
it can be inspected in git history (for example commit `641da87`). Old editor JSON files still open (`problem_from_legacy`).

## Algorithm Review (2026-10-16, of the removed legacy solvers)

This section records why the legacy solvers were replaced; all items below are fixed in `pcbthermal` (see `docs/physics_core.md`).

Full detail, formulas and experiment tables: `docs/thermal_models.md`. Keep that file in sync with any solver change.

Code review plus numerical experiments (100x100 mm, 2 layers, 5 W, 20x20 mm heater,
h_top=10, h_bottom=15 W/m2K). Reference: a direct sparse solve of the same FDM system.
Priorities for the next work, most severe first.

1. FDM `converged` can be false-positive. The stop test is the max change per sweep
   (`tol=0.01`), not the residual. With weak convection (h=2) it reported converged
   after dissipating only 15% of the input power; Tmax was 39.4 vs 46.5 degC (7 K error).
   With defaults (omega 1.5) the error was 2.7 K. Fix: stop on residual or on
   power balance, or replace SOR by `scipy.sparse.linalg` (the matrix is symmetric
   positive definite; a direct or CG solve is exact and fast).
2. FDM heater power is not conserved. Power is `W/mm2 * dx*dy` per node inside the
   polygon, so the inserted power depends on the grid (1.4 W instead of 5 W at dx=10;
   0 W if no node falls inside). Fix: distribute exactly the requested power over the
   covered nodes (area-weighted).
3. `fdm_solver.py` does not import without Numba: `float64[:,:,:]` annotations are
   evaluated at definition time -> `NameError`. The "pure Python fallback" is broken.
4. Analytic conduction term is dimensionally wrong: `L/(k*A*t)` (should use the
   cross-section `t*width`). Result: 1002 degC in Basic mode and 24466 degC in
   Advanced mode for the reference case (FDM: ~92 degC). Advanced mode also uses
   the heater footprint as the convective area, which is physically wrong.
5. Lumped network is not a valid series/parallel network: `R_total = (Rcu+Rfr4+Rconv)/(1+n_vias)`,
   `R_th_via` is computed but unused, copper resistance uses the board thickness, only one
   FR4 layer is used for N layers, and `T_max` can be below `T_top`. Advanced mode gives 1342 degC.
6. FDM mesh: boundary nodes use a full `dx*dy` cell (should be half), FR4 has no lateral
   conduction (nodes outside a Zone are isolated; with no Zone at all Tmax = 548 degC),
   sinks on inner layers are ignored, vias are solid copper (ignore plating thickness
   `DEFAULT_VIA_PLATING_THICKNESS`), `_process_elements` loops are pure Python.
7. The "time evolution" GIF shows SOR iterations, not physical time. A real transient
   needs heat capacity (rho*cp) and time stepping (implicit Euler / Crank-Nicolson).
8. The solvers `print()` to the console and mix numerics with wx dialogs.

Suggested direction: (a) keep FDM as the reference solver but fix 1-3 and 6; (b) rewrite
Lumped as a real RC/resistor network; (c) replace Analytic by sheet-spreading
resistance (Lee et al.) plus convection; (d) add regression tests that compare the
solvers on one benchmark board and check energy balance (out/in ~ 1).

## Commands

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # once
.venv/bin/python -m pcbthermal gui [project.pcbt.json]               # application
.venv/bin/python -m pcbthermal run examples/example_board.pcbt.json  # CLI: all models, report, plots
.venv/bin/python -m pcbthermal solvers examples/example_board.pcbt.json   # direct vs CG vs SOR
.venv/bin/python -m pytest -q tests                                  # tests (GUI offscreen)
.venv/bin/python examples/accuracy_study.py                          # Lumped/Analytic accuracy table
.venv/bin/python examples/stress_study.py                            # stress cases
.venv/bin/python examples/solver_equivalence.py                      # direct vs CG vs SOR on five boards
```

## Branches and Versions

- `main`: released versions only, each tagged `vMAJOR.MINOR.PATCH` (annotated tag). Current release: **v2.1.0** (2026-10-16).
- `develop`: integration branch for the next version; feature work branches off it (`feature/<topic>`) and merges back when it is solid.
- Tag `legacy-wxpython-1.0.0` marks the original wxPython program (version 1.0.0), kept for reference.
- Version policy: semantic versioning. The only definition of the version is `pcbthermal/__version__` (`pcbthermal/__init__.py`); it is shown in the GUI
  (title bar, status bar, About), in `--version`, in reports and in saved projects. A release needs: version bump, `CHANGELOG.md` entry
  (`tests/test_version.py` checks it and the README), README update, tests green, merge to `main`, annotated tag, push.

## Git Policy

Claude handles all git operations in this repository: branches, commits, pushes,
merges, PRs, and tags. The maintainer set these rules (2026-10-16):

- **Commits**: commit when a meaningful unit of work is finished (a feature, a fix, a batch of
  documentation), not after every small step; the maintainer leaves the call to Claude.
  Work on a feature branch; commits can be reverted locally.
- **Pushes**: do not push after every commit. Push only when asked, or at a
  milestone (before a merge or a release).
- **Merges**: merge into `main` only when `develop` holds a solid, working
  development (the app runs, tests pass and the change is complete). Not for every commit.
- **Tags**: create a tag only for a good release (see "Branches and Versions"). Never tag routine work.
- **Never**: force push, rewrite published history, or commit generated outputs.
- **Before editing this file**: replace only the section you mean to change. A range replacement
  once deleted this section by accident (restored on 2026-10-16).

## Maintaining This File

Update `CLAUDE.md` whenever something important happens: architecture or
structure changes, new commands, new dependencies, workflow or convention
changes, and notable decisions. Add an entry to the Decisions Log in the same
change. Do this without being asked.

## Claude Code Settings

`.claude/settings.local.json` (gitignored, personal) gives Claude broad access in
this repository: all file tools, Bash (including explicit `git *` and `gh *` rules), WebFetch
and WebSearch are allowed, with `acceptEdits` as the default mode. Denied: `sudo`,
force pushes (`-f` / `--force`), `git reset --hard origin*`, and `rm -rf` on `/` or `~`.

## Decisions Log

Record important decisions here, newest first, with date and reason.

- 2026-10-16: Independent 3D FEM check (`examples/fem3d_validation.py`, scikit-fem not in requirements): FVM within 0.4 to 2.4 % of the 3D rise, Lumped 2 to 7 %, Analytic 0.2 % on uniform copper and up to 24 % with a 20 mm pad; explains why FVM and Analytic agree on uniform boards (same layered model). Convection calibration helper (`calibrate_convection`, CLI `calibrate`).
- 2026-10-16: Added power tables and CSV (`TableProfile`, `profile_io.py`, GUI import/export buttons, `run --profile`, `examples/csv_profiles/`); the decision uses the periodised step response for any periodic table, one-shot tables are always resolved from the steady state of their first power; analytic transient now has one modal system per heater with the via (or sink) conductance scaled to the local steady response (single global scale tried and rejected: it cooled the distant heater by 18 %); animation of the power step also for the Analytical model. Version bump to be decided at the release.
- 2026-10-16: Released **2.1.0** (power profiles + computed heat transfer coefficients), merged `feature/more-models` into `develop` and `main`, tag `v2.1.0`. Next: Component element (Package, heat sink), then Gerber import and variable stack-up.
- 2026-10-16: Implemented computed heat transfer coefficients (`convection.py`, `Board.h_mode/emissivity_top/emissivity_bottom/air_speed/orientation/h_calibration`, Picard loop outside the models in `api._solve_computed_h`): one `h` per face from the mean face temperature, radiation always included (emissivity per face, default 0.9), global convection multiplier, edge `h` stays typed, time simulation and animation fixed at the steady-state coefficients. Measured effect on the example: a constant `h` overestimates the rise by 10 % at 22 W and underestimates it at low power (`roadmap.md` section 2).
- 2026-10-16: Roadmap extended: heat sink on a component (θCS + θSA in K/W, θSA scaled with ΔT from a reference rise, optional sink capacity C_hs from the first version), Gerber import of the copper per layer (section 7, `gerbonara` as candidate, fill fraction per cell), and variable stack-up (section 8: per-gap dielectric thickness and material, layer nodes of copper plus half the adjacent dielectrics, backward compatible when gaps are equal). All future work, nothing implemented.
- 2026-10-16: Researched the Package (JEDEC 2R) basis and recorded it in `docs/package_models.md` (sources read: NISTIR 7648, TI SPRA953B, Renesas white paper, Semiconductor Digest, Siemens). Rules taken from it: the user enters θJB and θJC,top as resistances, never ψ; ψJT and ψJB are reported as consistency checks; θJB is spread over the footprint with area weights; the Package is quasi-static until a Foster chain exists; the share of power into the board is checked against 75 to 95 %. Unverified figures (2 to 20 % error of 2R) are not used. Implementation order: computed `h` first, then the Component element.
- 2026-10-16: Future Component element agreed: one element with a type (Source = today's heater, Package 2R, passive areas such as cooled area, contact, material patch); its power and profile drive `T_j`, top cooling uses the computed `h` (Picard iteration), the profile decision measures the oscillation at `T_j`. Thermal resistance is displayed in K/W (same number as °C/W). Multigrid and the 3D FEM validation script are kept in `docs/roadmap.md` as optional future work; computed `h` and the Component element follow after the current models are polished. See `docs/roadmap.md` sections 2 to 5.
- 2026-10-16: Implemented power profiles on `feature/more-models` (square wave only; `profiles.py`; all three models; GUI "Power profile" tab; CLI options). Decision average-vs-resolve per heater from the oscillation in °C (default 1 °C, shared error budget, smallest first), mixed regimes in one run; start = steady state of the average power or a typed °C; duration until the cycle repeats / N cycles / fixed time; 200,000 step cap. Analytic transient smears vias and sinks (warned). GUI labels descriptive ("Finite volume (FVM), reference", "Thermal network (LPTN)", "Analytical (Fourier series)"), keys unchanged; units °C and °C/W. Results tab index is now 2 (Board, Power profile, Results).

- 2026-10-15: Created CLAUDE.md. Decided that all code, comments, and docs are
  in English, with `#` inline comments and Doxygen-style docstrings.
- 2026-10-16: Working branch is `develop` (it holds the application code). Added
  `.claude/settings.local.json` with broad permissions, `.gitignore`, and documented
  the real project structure and run command.
- 2026-10-16: Git policy defined: merge to `main` only for solid developments, tag only for good releases. Git rules made explicit in the local settings.
- 2026-10-16: Full algorithm review done; findings recorded in "Algorithm Review". No solver code changed yet.
- 2026-10-16: Added `docs/thermal_models.md` documenting the three models (formulas as implemented), validation experiments, review findings and references.
- 2026-10-16: Started the rebuild (branch `feature/physics-core`, merged into `main` as 2.0.0): new GUI-independent package `pcbthermal` (FVM reference, ring-network lumped, modal analytic, CLI, plots, 30 tests). Cell-centred finite volumes chosen over node-centred FD (exact power and area conservation, no half-cell borders); sparse direct/CG solver instead of SOR; FR-4 anisotropic (0.3 through, 0.9 in-plane); hollow via barrels; analytic uses the exact multilayer fin series instead of Lee spreading formulas (their coefficients could not be sourced). See `docs/physics_core.md`. The legacy `core/` and `ui/` are untouched; the planned UI is PySide 6 on top of `pcbthermal`.
- 2026-10-16: Lumped rewritten as per-heater ring networks aggregated from the real geometry (24 % -> 1 % error on the example); Analytic got copper weighting, Green-function corrections for vias and sinks and validity warnings (47 % -> 9 %). New public API: `SolverOptions`, `simulate`, `Problem` builder (mm, 1-based layers), `Project` files. SOR kept as an optional FVM solver (vectorised red-black) to compare with the direct sparse solve: same answer with a residual criterion, wrong answer with the original step criterion.
- 2026-10-16: Legacy wxPython code removed. PySide 6 GUI built on `pcbthermal` (editor canvas, panels, results tabs, themes, undo/redo). Transients exist in the CLI (`--gif`) but are out of the GUI scope for now, at the user's request. Virtual environment `.venv/` created and ignored by git.
- 2026-10-16: SOR and the sparse direct solver give the same temperatures (≤1e-8 K on five boards) when SOR stops on the residual; the direct solver is the default (3 to 30 times faster). Real-time animation added to the GUI (Animation tab) and CLI (`transient --gif`), validated against an exact exponential (Euler first order, Crank-Nicolson second order). Docs added: `new_approach.md`, `candidate_methods.md`. The `example_board` vias use 3.5 mm pitch (same positions as the legacy comparison).
- 2026-10-16: Models tuned after an audit (see `docs/findings.md`): Lumped uses offset-contour rings from the real footprint with exact disc interior relations and a Bessel vertical-loss correction (example board +24 % -> -2 %); Analytic weights copper per layer with the layer's own fin length (+47 % -> -2 %). Added `checks.py` (input validity warnings, shown live in the GUI), `suggest_cell_mm` (Auto cell size), a documentation test gate, and the findings/index docs. Corrected an earlier wrong claim that vias made the FVM mesh-dependent by 1 % (it was a different via layout).
- 2026-10-16: Released **2.0.0** (first release of the rebuilt program; the old wxPython program was 1.0.0, so a major bump avoids a clash). Added `docs/model_guide.md` (which model to use), `CHANGELOG.md`, README with screenshots (`examples/make_screenshots.py`), version shown in the GUI, `--version`, version recorded in reports and projects.
- 2026-10-16: Git language rule made explicit: branch names, tags, commit messages and PR text are in English, with naming conventions (`feature/<topic>` kebab-case, imperative commit subjects of at most 72 characters). History audited, nothing needed to change.
