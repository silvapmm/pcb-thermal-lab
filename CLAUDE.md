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
    (see `docs/models.md`, "FDM or FVM").
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
pcbthermal/            Physics core (no GUI imports) - see docs/models.md
  model.py             Board, Materials, Zone, Heater, Via, Sink, Problem (+ mm builder API), JSON I/O
  geometry.py          polygon area/centroid/point-in-polygon, cell coverage fractions
  fdm.py               node-centred finite-difference model of the same layered physics (steady state, power-step animation, step responses and power profiles, `--model fdm|compare`; reuses the FVM transient machinery)
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
tests/                 pytest suite (169 tests; GUI tests run offscreen; test_docs.py enforces Doxygen docs on every function)
examples/              example boards (.pcbt.json), csv_profiles/ (documented CSV power-profile example), validation_study.py (all models, every scenario; tables of docs/validation.md), accuracy_study.py and stress_study.py (the scenario lists), solver_equivalence.py, fem3d_validation.py (3D solid)
docs/                  models.md (models, formulas, profiles, convection, API), validation.md (every scenario in every model, 3D check, history), roadmap.md (planned work), images/
ico/                   application icon
```

The original wxPython program (`core/`, `ui/`, `main.py`, `config.py`) was removed in release 2.0.0;
it can be inspected in git history (for example commit `641da87`). Old editor JSON files still open (`problem_from_legacy`).

## Why the legacy solvers were replaced

The review of the removed wxPython program (false convergence of its SOR stopping rule, heater power depending on the grid, no lateral conduction in the FR-4, solid vias, dimensionally wrong analytic term, an invalid lumped
network, an iterations GIF instead of time) and the numbers before and after are in `docs/validation.md`, section 6; the code can be inspected at tag `legacy-wxpython-1.0.0` and commit `641da87`. All items are fixed in `pcbthermal`.

## Commands

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # once
.venv/bin/python -m pcbthermal gui [project.pcbt.json]               # application
.venv/bin/python -m pcbthermal run examples/example_board.pcbt.json  # CLI: all models, report, plots
.venv/bin/python -m pcbthermal solvers examples/example_board.pcbt.json   # direct vs CG vs SOR
.venv/bin/python -m pytest -q tests                                  # tests (GUI offscreen)
.venv/bin/python examples/validation_study.py [--fem]                # every scenario in every model (+ 3D solid)
.venv/bin/python examples/solver_equivalence.py                      # direct vs CG vs SOR on five boards
```

## Branches and Versions

- `main`: released versions only, each tagged `vMAJOR.MINOR.PATCH` (annotated tag). Current release: **v2.2.0** (2026-10-16).
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
change. Keep the documentation **few and good**: `README.md`, `CHANGELOG.md`, `docs/models.md`, `docs/validation.md`, `docs/roadmap.md` and the README of an example folder; fold new material into them instead of adding files. Do this without being asked.

## Claude Code Settings

`.claude/settings.local.json` (gitignored, personal) gives Claude broad access in
this repository: all file tools, Bash (including explicit `git *` and `gh *` rules), WebFetch
and WebSearch are allowed, with `acceptEdits` as the default mode. Denied: `sudo`,
force pushes (`-f` / `--force`), `git reset --hard origin*`, and `rm -rf` on `/` or `~`.

## Decisions Log

Record important decisions here, newest first, with date and reason.

- 2026-10-16: The FDM also does animation and power profiles: `fdm.Network` exposes the attributes of `fvm.Network` (K, C, Q, Qw_matrix, footprints on the nodes) so the generic `fvm.transient_from_network`, `step_responses_from_network` and the profile runner work on it; transient frames carry `grid="nodes"`. FDM within 0.7 °C of the FVM over the whole step response on the example. Version 2.3.0 planned.
- 2026-10-16: Released **2.2.0** after a stress test of the application (`tests/test_gui_stress.py`: every example with every model, every results view, the profile page with every control and bad CSV files, odd boards, edits during a run, files and exports, random actions with several seeds). It found one real bug: a result arriving after an edit made during the run was shown as current; fixed (marked outdated). The stress test also aborted the whole process (SuperLU is not safe in two threads at once) when a simulation started while an animation was computing; all background calculations now take one lock (`gui/compute.py`) and wait for each other. A real file dialog opened by choosing "Table (CSV file)" blocks tests unless patched.
- 2026-10-16: Documentation cut to three documents (`docs/models.md`, `docs/validation.md`, `docs/roadmap.md`) plus README and CHANGELOG; eight older documents (model guide, physics core, new approach, findings, candidate methods, thermal models, legacy comparison, package models) were merged and removed (history is in git). `docs/validation.md` is the clean comparison of the same scenarios in every model, generated by `examples/validation_study.py`. The FDM is now in the application (checkbox, steady state only); area sampling made it the default; the symmetric sparse ordering made every direct solve about 40 % faster. The 3D check now has vias (copper rods of the barrel's copper area) and sinks: example board 85.6 °C against FVM 85.9, FDM 85.2, Lumped 84.7, Analytic 84.7.
- 2026-10-16: Added `pcbthermal/fdm.py`, a correct node-centred FDM of the same model, as a comparison model (API `models=("fdm",)`, CLI `--model fdm|compare`, no GUI, no time simulation) and `examples/model_comparison.py`: FDM agrees with the FVM within ~1 % and jumps ±0.5 °C with the grid while the FVM converges monotonically; the old program's errors were modelling, not the discretisation.
- 2026-10-16: Explained in `docs/model_guide.md` why FVM and Analytic agree (same layered model; the Analytic is its exact solution on a uniform sheet; Lumped and Analytic were tuned against the FVM so the 3D FEM is the independent check) and listed the literature on FDM/FVM and PCB models; recorded that no model has been compared with a physical board measurement yet.
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
