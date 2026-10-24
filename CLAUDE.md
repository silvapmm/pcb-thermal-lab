# CLAUDE.md

Project memory for Claude Code. Keep this file up to date as the project evolves:
record decisions, architecture, commands, and conventions here.

## Project Overview

**PCB Thermal Lab** (see `pcbthermal.__version__`; the original wxPython program was "PCB Thermal Simulator Tool" 1.0.0) is a
physics package, command line and PySide 6 application for simulating the thermal behavior of printed circuit boards (PCBs).

- Author: Pedro Silva (PMS Labs)
- License: MIT, Copyright (c) 2025-2026 Pedro Silva (PMS Labs) (see `LICENSE`).
- Users draw PCB elements (zones, heaters, vias, heatsinks), configure parameters,
  and run three main models (keys `fvm`, `lumped`, `analytic`) plus two comparison models:
  - **Finite volume (FVM), reference**: cell-centred finite volumes on a sparse matrix (direct, CG or SOR solver), any geometry.
  - **Thermal network (LPTN)**: lumped-parameter thermal resistance network per heater (rings by distance from the footprint).
  - **Analytical (Fourier series)**: multilayer cosine series with local corrections for vias and heatsinks.
  - Comparison models (keys `fdm`, `solid3d`): **FDM** (node-centred finite differences of the same layered model, steady state and time) and the **3D solid** (3D finite volumes with real slabs, steady state only).
    The old wxPython solver was also called FDM; it was replaced (see `docs/models.md`, "FDM or FVM").
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
- Never commit generated outputs (PNG, GIF, TXT reports, temp files); the README screenshots in `docs/images/` are the exception (regenerate with `examples/make_screenshots.py`).

## Licences

The project is MIT (`LICENSE`). Rules (maintainer, 2026-10-23, after the incoherence between the documents was found):
- **Everything of ours is MIT**: code, documents (`README.md`, `CHANGELOG.md`, `docs/`, the user guide), the investigations in `research/` (documents, scripts, figures), the screenshots in `docs/images/` and the application icon in `ico/` (the icon is ours, confirmed by the maintainer on 2026-10-23). Third-party material is quoted with its source and keeps its owner's licence.
- **One statement**: `LICENSE`, `README.md` ("Author and license", with the table of the libraries), the About box (`pcbthermal/gui/help.py`) and this file say the same thing; change them together.
- **A new dependency** gets its licence checked (installed metadata or PyPI) and added to the README table in the same commit; copyleft code (GPL, AGPL) is never copied or vendored into the repository, only ideas and public formats are used (see `docs/roadmap.md`, section 6); libraries are installed by `pip` and imported, never vendored.
- **Qt for Python (PySide 6)** is LGPL-3.0 (or GPL, or commercial): fine for an MIT repository that only imports it; a bundled executable would have to meet the LGPL conditions (licence text and notices, replaceable libraries, Qt source offer). Not legal advice; ask a lawyer before distributing a bundle or a commercial version.
- **Third-party data** (boards, datasheets, catalogue values): numbers and facts with their source are fine; copies of files or renders of someone else's board are not committed unless the licence is confirmed (see "Research branches").
- **No open licence question** at the moment: the icon and the screenshots are ours.

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
  `docs/<topic>`, for example `feature/component-models`, and `research/<topic>` for studies that do not change the program, for example `research/gerbers`.
  No accents, spaces or Portuguese words.
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
  blocks.py            metal blocks (heatsinks with thickness): extra node layers for FVM/FDM
  model.py             Board, Materials, Zone, Heater, Via, Heatsink, Problem (+ mm builder API), JSON I/O
  geometry.py          polygon area/centroid/point-in-polygon, cell coverage fractions
  solid3d.py           3D finite-volume solid (real slabs per copper layer, gap and block; steady state; comparison model, key `solid3d`)
  fdm.py               node-centred finite-difference model of the same layered physics (steady state, power-step animation, step responses and power profiles, `--model fdm|compare`; reuses the FVM transient machinery)
  fvm.py               reference finite-volume model: steady (direct, CG, SOR) and transient
  laminate.py          the laminate of a one-layer board: node layers under the copper (FVM, FDM, Lumped) or a series film (Analytic)
  lumped.py            ring network per heater, superposed
  analytic.py          multilayer cosine series + local via/heatsink corrections
  checks.py            input validity warnings (heater outside the board, no copper, copper edge across a heater, ...)
  convection.py        computed h: air properties, natural/forced convection, radiation, board_h (Picard loop is in api.py)
  profile_io.py        power profiles as CSV files (read/write)
  defaults.py          defaults and libraries: shipped data/defaults.json + the user's user_defaults.json (only the differences, found at start-up); data/stackups.json for the stack-ups
  profiles.py          power profiles (square wave): decision average-or-resolve, window runner shared by the three models
  jobs.py              calculations run by the application in a separate process (no Qt): simulate, transient, analyze, inverse
  inverse.py           power of a part from a measured temperature (board model run backwards) and from a datasheet parameter
  help/index.html      the user guide (HTML, shown by Help - User guide and F1)
  results.py, analysis.py, api.py (SolverOptions, simulate, suggest_cell_mm), project.py (.pcbt.json), examples.py
  plots.py             draw_* functions (any Figure) and file wrappers; no pyplot
  cli.py               python -m pcbthermal {run,solvers,transient,convergence,convert,gui,example}
  gui/                 PySide 6 app: document (undo), canvas (editor, rulers), panels, stackup (cross-section tab), calculator, help (guide, About), tips (tooltips), compute (calculation process), results_view, main_window, theme
tests/                 pytest suite (about 390 tests; GUI tests run offscreen; test_docs.py enforces Doxygen docs on every function)
examples/              example boards (`.pcbt.json`), `csv_profiles/` (documented CSV power-profile example) and `make_screenshots.py`; the studies that used to live here are in `research/` (one folder per investigation, see `research/INDEX.md`)
docs/                  versions.md (what was implemented in every version), models.md (models, features, API), theory.md (every equation and approximation of every model; update it with any model change), calculators.md (the auxiliary calculators: formulas, validation, limits, sources), validation.md (every scenario in every model, 3D check, history), roadmap.md (what is implemented and what we want to implement), research.md (open investigations, empty when nothing is pending), images/
ico/                   application icon
research/              one folder per investigation (see "Research branches"); not part of the program
  INDEX.md             index of the investigations by area of the program (status and question of each)
  README.md            index of the investigations and the rules for figures
  <topic>/             everything about one investigation; the same layout in every folder:
    README.md, IMPLEMENTED.md or INTEGRATION.md, LOG.md   what is read (results in numbered sections, where it lives in the program or the design for it, what was read and how)
    figures/           fig_NN_topic.png, generated by scripts/make_figures.py and linked from the README files
    docs/              text to adopt later (only when the work is open)
    scripts/           ALL the executable Python: the studies (study_<question>.py; older ones keep their names) and make_figures.py
    lib/               only when the studies share reusable code (readers, solvers, prototypes)
    tests/             tests of the investigation (only when it has its own)
```

Example: `research/gerbers/` (kept by its own cloud session, which will arrange it in this layout) holds the independent reader `native_gerber.py`, `conduction.py` (mappings), `joule.py` (current and Joule heat of a net) as `lib/`; `study_*.py`, `make_synthetic.py`, `compare_readers.py` and `make_figures.py` as `scripts/`; `tests/`, `README.md` (results, numbered sections 4.x), `INTEGRATION.md` (how it would enter the program), `docs/` (`research.md` summary, `changelog.md`, `decisions-log.md`, `roadmap-entry.md`, `literature.md`) and `figures/` (`fig_NN_topic.png`). The studies that were in `examples/` live in the folders `component-heatsink`, `block-and-fins`, `solid3d-verification`, `outline`, `stackup`, `power-calculator`, `models-comparison` and `via-fill`.

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
.venv/bin/python research/models-comparison/scripts/validation_study.py [--fem]                # every scenario in every model (+ 3D solid)
.venv/bin/python research/models-comparison/scripts/solver_equivalence.py                      # direct vs CG vs SOR on five boards
```

## Branches and Versions

- `main`: released versions only, each tagged `vMAJOR.MINOR.PATCH` (annotated tag). Current release: **v2.4.1** (2026-10-22).
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
- **Before every merge** (feature branch into `develop`, `develop` into `main`) run the **whole test battery** and read its result: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests --timeout=900 --timeout-method=thread`
  (about 8 minutes: it includes the application stress tests, the documentation gate and the version checks). A partial run is not enough. If anything fails, fix it first; never merge on a red or unfinished battery, and say in the report that it was run and what it returned.
  A new feature adds its own stress scenarios to `tests/test_gui_stress.py` (every new model, element type, dialog or background job).
- **Tags**: create a tag only for a good release (see "Branches and Versions"). Never tag routine work.
- **Never**: force push, rewrite published history, or commit generated outputs.
- **Before editing this file**: replace only the section you mean to change. A range replacement
  once deleted this section by accident (restored on 2026-10-16).

## Research branches

Maintainer's rules (2026-10-23):

- **Branch and scope**: an investigation that does not change the program is done on its own branch `research/<topic>`, created from `develop`, and in its own folder `research/<topic>/`. Commits and pushes on a research branch are authorised by this rule; never touch `develop` or `main` from it, never force push or rewrite history, and do not open a PR unless asked.
- **Project documents stay untouched** on a research branch: `README.md`, `CHANGELOG.md`, `CLAUDE.md` and everything in `docs/` must stay identical to `develop` (merge `develop` into the branch to keep them so). New documents go only in `research/<topic>/`. The text that would go into the project documents when the work is adopted is kept in `research/<topic>/docs/` (`research.md` summary, `changelog.md`, `decisions-log.md`, `roadmap-entry.md`, and `literature.md` for the literature status).
- **Folder content and layout** (the same in every folder, so a reader always knows where to look): the root holds only what is read, `README.md` with the results in numbered sections (tables with the numbers, the limits of the study, the sources), `INTEGRATION.md` with the design for entering the program (what changes, what does not, risks) or, when the work is already in the program, `IMPLEMENTED.md` (where it lives and how it is tested), and `LOG.md` (dated entries: what was read in full, from a summary or from memory; what was reproduced and what not); `figures/`; `docs/` as above; `scripts/` holds **all** the executable Python, the studies (`study_<question>.py`, each with a `@file`/`@brief` header saying what question it answers and how to run it) and `make_figures.py`; `lib/` only when the studies share reusable code (readers, solvers, prototypes); `tests/` for the tests of the investigation. Scripts are run from the repository root (`.venv/bin/python research/<topic>/scripts/<script>.py`), find the repository root and their siblings through `sys.path`, and are checked by `tests/test_docs.py` (Doxygen rules) except the Gerber research. A research folder follows the language and Doxygen documentation rules of the project for its Python files.
- **Figures**: figures live in `research/<topic>/figures/`, named `fig_NN_topic.png` with NN in order of creation, generated by a script in the folder (`make_figures.py`), committed on purpose (the only generated outputs allowed in git there), and linked from the README files with a relative Markdown link, `![caption](figures/fig_NN_topic.png)`, followed by an italic line with the figure number and file name (`docs/*.md` use `../figures/`). Check the licence of any third-party board a figure renders and note it in `research/README.md`.
- **Data and outputs**: downloaded boards, caches and outputs go in `data/`, `out/` and `*.npz`, git-ignored in the folder's `.gitignore`, never committed; keep a fetch script instead and respect the licences of what is downloaded. Everything must be reproducible by running a script in the folder.
- **Tests**: run only the tests of the investigation (`research/<topic>/tests`), not the whole battery, unless the program changes (the documentation gate `tests/test_docs.py` and the tests that import a study from `research/<topic>/scripts` are part of the program's tests and run with the battery).
- **Method and honesty**: compare against an independent reference (another tool, an exact closed form, or a file of known answer made by a different tool), not only against itself; compare more than totals (positions, connectivity, behaviour at the limits); sweep the conditions that matter (for example every angle, not only 45 degrees); when a study finds a defect, fix it, add a regression test and re-run the earlier comparison. Record in the documents what was read in full, what only from a summary or a search snippet, what is from memory, and what could not be opened (for example hosts blocked by the environment's network policy); mark numbers that were not reproduced; never present a guess as a finding. Say plainly when an earlier claim was wrong (for example a drill comparison that matched only the counts).
- **Adoption**: when the maintainer decides to adopt the work, a `feature/<topic>` branch off `develop` implements it in `pcbthermal/` following the normal rules (documentation, tooltips, user guide, tests, the whole battery), the findings are folded into the project documents and `docs/research.md` is reset to its empty template; the `research/<topic>/` folder stays as the record.
- **Reporting**: after each step say briefly what was done, what the numbers are, what was not done or not verified, and which decisions are left to the maintainer.

## Before every commit: update the documentation (mandatory)

Maintainer's rule (2026-10-21): **no commit without updating, in the same commit, every file the change touches.** Go through this list each time and update what applies:

1. `README.md` (features, usage, screenshots in `docs/images/`: regenerate with `examples/make_screenshots.py` when the screen changed) and `CHANGELOG.md` (the Unreleased section).
2. `docs/versions.md` (what was implemented, where in the code, how it is tested), `docs/models.md` (physics and formulas), `docs/validation.md` (numbers and tables of the new behaviour: run `research/stackup/scripts/stackup_outline_study.py`, `validation_study.py` or the study of the feature), `docs/roadmap.md` (move what is done, add what is left).
3. **The program manual**: the HTML user guide `pcbthermal/help/index.html` (every new parameter, model, tool, key, menu) and `tests/test_help.py` (add the new words it must contain), the keyboard list in `gui/main_window.py` (`show_shortcuts`), the About box if the program data changed.
4. **Tooltips**: every new control gets a tooltip (own text or an entry in `pcbthermal/gui/tips.py`); `tests/test_tooltips.py` fails otherwise. A good hint says what the parameter *means*, its unit, a typical range or where the number comes from, and what it is used for (maintainer's rule, 2026-10-22).
5. `CLAUDE.md` itself: project structure, commands, test count, and a Decisions Log entry.
6. Docstrings (`tests/test_docs.py`), the typical-value files (`pcbthermal/data/stackups.json`) and any number quoted in the documents that the change moved.

Then run the tests (the whole battery before a merge or a push of a feature), commit and push.

## Maintaining This File

Update `CLAUDE.md` whenever something important happens: architecture or
structure changes, new commands, new dependencies, workflow or convention
changes, and notable decisions. Add an entry to the Decisions Log in the same
change. Keep the documentation **few and good**: `README.md`, `CHANGELOG.md`, `docs/models.md`, `docs/theory.md`, `docs/calculators.md`, `docs/validation.md`, `docs/roadmap.md`, `docs/research.md` and the README of an example folder; fold new material into them instead of adding files. `docs/research.md` holds the investigations that are not implemented yet (what was read, simulated and is still open): use it while discussing, and when the work is implemented fold its findings into the other documents and reset it to its empty template. Do this without being asked. The documents under `research/` are the exception to the "few and good documents" rule, because each investigation keeps its own README, INTEGRATION.md and docs/.

## Claude Code Settings

`.claude/settings.local.json` (gitignored, personal) gives Claude broad access in
this repository: all file tools, Bash (including explicit `git *` and `gh *` rules), WebFetch
and WebSearch are allowed, with `acceptEdits` as the default mode. Denied: `sudo`,
force pushes (`-f` / `--force`), `git reset --hard origin*`, and `rm -rf` on `/` or `~`.

## Decisions Log

Record important decisions here, newest first, with date and reason.

- 2026-10-24: **One-layer boards and the Lumped rings** (maintainer: close the fix branch, test with more complicated boards before and after): a one-layer board gets two laminate nodes under the copper in the FVM, FDM and Lumped (`laminate.py`; chosen from a sweep, 1 to 4 nodes: -4.1, -2.5, -1.8, -1.5 % on a bare pad) and a series film in the Analytic (laminate nodes made its bare-pad estimate worse); the Lumped merges rings narrower than a cell (`RING_MIN_WIDTH = 1`; the result no longer grows with the ring count). Nine boards against the 3D solid, run on the program before and after: mean error FVM 3.8 -> 1.0 %, FDM 5.3 -> 2.9 %, Lumped 6.9 -> 5.2 %, Analytic 5.5 -> 5.5 % (better with full copper, hotter on partial copper where its uniform sheet already overestimated); multilayer boards unchanged. Left: bare pads on one-layer boards in Lumped and Analytic, FDM pad-edge sampling (roadmap). Found on the way and fixed: the Analytic heat balance with a metal block counted the face hidden by the block (9 % off; reporting only, temperatures unchanged).

- 2026-10-24: **Model corrections after a review** (maintainer: "corrigir os nossos modelos é o mais importante"; branch `fix/model-corrections`): the pin of the cells off a board with an outline (1 W/K) is kept apart as `g_pin` and left out of the board time constant (`fvm.board_time_constant`: a round board read 0.02 s instead of 107 s, so the step responses of the power profiles stopped at 12 % of the steady resistance) and of the transient mean (`fvm.mean_weights`); the 3D solid builds the laminate of a one-layer board as four FR-4 slabs (it had only the copper: 120 °C against about 74 on a 20 mm pad; an independent 3D solver with patterned copper puts it within 0.2 % on that pad, it was 40 % high; full copper does not test it, the old model was within 0.2 % there too); a power loop that does not settle in 80 iterations warns. The Lumped's dependence on the ring count (no convergence with more rings) is recorded in the roadmap, not changed: the rings are tuned at 10 and a new construction is a project of its own. The plate check of the documents (+4.5 %) was a 24 mm source made by `round()`; corrected to +0.6 / −0.8 / −4.6 % with Seri Lee (1998) as the source.

- 2026-10-23: **Licences checked** (maintainer: "corrige a questão das licenças, há incoerência nos documentos"): the README now lists the licence of every dependency (read from the installed packages: NumPy BSD-3-Clause, SciPy BSD-3-Clause, Matplotlib PSF-based, PySide 6 LGPL-3.0 or GPL, pytest MIT) and the LGPL consequence for a bundled executable; gerbonara is Apache-2.0 and shapely BSD-3-Clause (PyPI); the roadmap no longer says gerbonara's licence is unchecked; a Licences section in this file holds the rules. The icon in `ico/` is ours; everything of ours (code, documents, research, images, icon) is MIT.
- 2026-10-23: **Research folder layout** (maintainer): in every folder the root holds only what is read (README, IMPLEMENTED or INTEGRATION, LOG), plus `figures/`, `docs/`, `tests/`; all executable Python goes in `scripts/` (studies `study_<question>.py`, `make_figures.py`) and shared code in `lib/` only when needed, because a root with scripts and documents mixed made it hard to see what to read and what to run. Applied to the eight folders moved from `examples/`; the Gerber research is arranged by its own session. `tests/test_docs.py` now also checks `research/<topic>/scripts`.
- 2026-10-23: **Existing investigations moved into `research/`** (maintainer): the studies of `examples/` went to `research/component-heatsink`, `block-and-fins`, `solid3d-verification`, `outline`, `stackup`, `power-calculator`, `models-comparison` and `via-fill` (done on `develop`; `research/gerbers` stays on its own branch), each with README (numbered results, figures), `IMPLEMENTED.md` or `INTEGRATION.md`, `LOG.md`; tests import the studies from the new folders; `research/INDEX.md` is the index (kept apart from `research/README.md`, which the Gerber branch keeps editing, to be merged later). Found while reproducing: the block study called flags that no longer exist and its case count was 74, not 62 (corrected everywhere). `research/gerbers/` is done in the cloud by the maintainer and was not touched (its figures 02 and 03 render boards of the gerbonara test set whose licence could not be confirmed: to be handled there). Studies are in a folder for their topic because they import each other (`component_study`); `docs/research.md` keeps the open notes and a copy is in `research/component-heatsink/NOTES.md`.
- 2026-10-23: **Research branches and folders** (maintainer): investigations live on `research/<topic>` branches and in `research/<topic>/` folders (code, studies, tests, README with numbered results, INTEGRATION.md, docs/, figures/); the project documents are not edited there; figures are named fig_NN_topic.png, committed and linked from the README files; downloaded data and outputs stay out of git. First case: `research/gerbers` (Gerber import, mapping of copper to the grid cells, independent reader, nets and Joule heat, comparison with gerbonara, pygerber and pcb-tools).
- 2026-10-22: **Released 2.4.1** (licensing only: the MIT text aligned in README, About box and CLAUDE.md after 2.4.0 had been tagged with the old text); `develop` merged into `main`, tag `v2.4.1`.
- 2026-10-22: License decision (maintainer): the project stays MIT. README, CLAUDE.md, the About box and the roadmap were aligned with `LICENSE` (they said "All rights reserved"). A paid or proprietary model is not decided; if it comes, versions up to v2.4.0 stay MIT (old releases cannot be revoked) and the change applies from a later version.
- 2026-10-22: Read FYPA (Tomachie fork), padne and altium_monkey for ideas (roadmap section 6, ideas 11 to 20): pass/fail checks with an exit code, result cache, regulator losses from efficiency, parameters in the CAD files with a sidecar, the electrical solution as heat source, probes, ParaView export, release automation, a visible disclaimer. All three are AGPL-3.0 and the project is MIT: ideas only, no code copied. WebFetch worked for github.com on this occasion (it failed for other hosts).
- 2026-10-21: The interface between a heatsink and the board or the package is **one dielectric sheet with its own material and thickness** (`pad_thickness`, `pad_k`; the resistance t/k replaces the typed value when both are set). Roadmap section 6 collects the ideas found in similar projects (KiCad thermal plug-ins, pcb-sim-toolkit, electro-thermal simulators, commercial tools): KiCad import, power list from a BOM, electro-thermal (Joule) coupling, thermal-via tools, sweeps, component library, reports.
- 2026-10-21: **Rule added: update the documentation, the user guide and the tooltips before every commit** (see the section above). Orientation reduced to horizontal (layer 1 = top faces up) or vertical, validated against the textbook correlations; the facing-down option and tilted boards were dropped for simplicity.
- 2026-10-21: **Advanced stack-up, board outline, calculation process, help** (maintainer's list of 18 items, branch `claude/eloquent-dijkstra-safezy`; `main` untouched by request). Stack-up: `Board.dielectrics` (None = simple) read through four helpers by every model; simple mode kept bit-compatible, advanced with equal gaps within 0.1 K; exact 1D series-circuit test. Outline: cell cover (`Board.cover`) in FVM/FDM/3D, cells off the board pinned to ambient, Lumped and Analytic left rectangle-only (skipped with a warning) because their geometry (rings, cosine series) is rectangular. Calculations moved from threads to one `spawn` process (cancel = terminate; a watchdog thread makes it exit when the parent dies; found because an orphan kept a pipe open and hung a shell). Power calculator: the board model run backwards (affine in the power with two runs) rather than a datasheet-only formula, because Tj = Tboard + psi P needs Tj. Help: one HTML file, shown in a QTextBrowser and openable in the browser. Tooltips: one table keyed by label (`gui/tips.py`) plus a test that scans the whole application. `docs/versions.md` added at the maintainer's request (one more document: it is the per-version detail the CHANGELOG does not give). Second and third batches the same day: typical stack-up templates in `pcbthermal/data/stackups.json` (loaded when the layer count changes, only the 4-layer entry is a published fabricator table; the others are constructed to add up), interface presets and contact area for a heatsink on a package (no drawing of the paste: resistance per area over a contact area), computed metal block with plate fins (efficiency tanh(mL)/(mL), no channel choking, a warning instead), `combine_sheets` for gaps of several sheets, orientation top-up/top-down/vertical (no tilt), curved boards as polygons (rounded preset, subdivide). Findings: dielectric conductivity and thickness move the temperature by about 1 %, copper weight by 5 %. WebFetch cannot reach most sites from the session; WebSearch snippets were the source. The remote branch `add-claude-github-actions-1792104903738` could not be deleted from the session (the git proxy cut the push): delete it in GitHub.

- 2026-10-21: **Top path of a part implemented** (heatsink on the package) on the session branch `claude/eloquent-dijkstra-safezy` (the maintainer asked not to touch `main`). Chosen as a fixed-point loop around any model instead of a junction unknown inside each matrix: `analysis.part_split` closes the series-parallel network (junction node joined to the board by θ and to the ambient by `R_top = θJC(top) + interface/A + θSA`), `api._solve_with_tc` gives the board `P − P_top` and shares the loop with the power coefficient, so FVM, FDM, Lumped, Analytic and the 3D solid all get it. Worst-case convention kept (hottest point under the footprint); 0.4 to 0.8 K above the uniform-conductance node prototype. Steady state only. Without `theta_sa` nothing changes. Still for later: heatsink scenarios, plate layer, interface with its own area, Foster chain (`docs/roadmap.md` 1.11).

- 2026-10-16: The FDM also does animation and power profiles: `fdm.Network` exposes the attributes of `fvm.Network` (K, C, Q, Qw_matrix, footprints on the nodes) so the generic `fvm.transient_from_network`, `step_responses_from_network` and the profile runner work on it; transient frames carry `grid="nodes"`. FDM within 0.7 °C of the FVM over the whole step response on the example. Released as **2.3.0**; the Component element gets its own version (2.4.0, branch `feature/component-model`) because it is long and heavy.
- 2026-10-16: Released **2.2.0** after a stress test of the application (`tests/test_gui_stress.py`: every example with every model, every results view, the profile page with every control and bad CSV files, odd boards, edits during a run, files and exports, random actions with several seeds). It found one real bug: a result arriving after an edit made during the run was shown as current; fixed (marked outdated). The stress test also aborted the whole process (SuperLU is not safe in two threads at once) when a simulation started while an animation was computing; all background calculations now take one lock (`gui/compute.py`) and wait for each other. A real file dialog opened by choosing "Table (CSV file)" blocks tests unless patched.
- 2026-10-16: Component decision (maintainer): **worst case first**. All the power reaches the board; no top path, no heat heatsink, no junction node in the next version. The Component stays a Source with an optional junction-to-pad resistance (renamed `θJB` field) and `T_j = T_max under the footprint + P·θ`; the junction node, heat heatsink and Foster chain stay in `docs/roadmap.md` as future work. Prototype (`research/component-heatsink/scripts/package_prototype.py`): the offset reproduces the TI CSD17308Q3 datasheet `RθJA` within 2 %, and a top path changes the result by a factor of two only with a heat heatsink. Planned first delivery listed at the top of roadmap section 1.
- 2026-10-16: Documentation cut to three documents (`docs/models.md`, `docs/validation.md`, `docs/roadmap.md`) plus README and CHANGELOG; eight older documents (model guide, physics core, new approach, findings, candidate methods, thermal models, legacy comparison, package models) were merged and removed (history is in git). `docs/validation.md` is the clean comparison of the same scenarios in every model, generated by `research/models-comparison/scripts/validation_study.py`. The FDM is now in the application (checkbox, steady state only); area sampling made it the default; the symmetric sparse ordering made every direct solve about 40 % faster. The 3D check now has vias (copper rods of the barrel's copper area) and heatsinks: example board 85.6 °C against FVM 85.9, FDM 85.2, Lumped 84.7, Analytic 84.7.
- 2026-10-16: Added `pcbthermal/fdm.py`, a correct node-centred FDM of the same model, as a comparison model (API `models=("fdm",)`, CLI `--model fdm|compare`, no GUI, no time simulation) and `examples/model_comparison.py`: FDM agrees with the FVM within ~1 % and jumps ±0.5 °C with the grid while the FVM converges monotonically; the old program's errors were modelling, not the discretisation.
- 2026-10-16: Explained in `docs/model_guide.md` why FVM and Analytic agree (same layered model; the Analytic is its exact solution on a uniform sheet; Lumped and Analytic were tuned against the FVM so the 3D FEM is the independent check) and listed the literature on FDM/FVM and PCB models; recorded that no model has been compared with a physical board measurement yet.
- 2026-10-16: Independent 3D FEM check (`research/solid3d-verification/scripts/fem3d_validation.py`, scikit-fem not in requirements): FVM within 0.4 to 2.4 % of the 3D rise, Lumped 2 to 7 %, Analytic 0.2 % on uniform copper and up to 24 % with a 20 mm pad; explains why FVM and Analytic agree on uniform boards (same layered model). Convection calibration helper (`calibrate_convection`, CLI `calibrate`).
- 2026-10-16: Added power tables and CSV (`TableProfile`, `profile_io.py`, GUI import/export buttons, `run --profile`, `examples/csv_profiles/`); the decision uses the periodised step response for any periodic table, one-shot tables are always resolved from the steady state of their first power; analytic transient now has one modal system per heater with the via (or heatsink) conductance scaled to the local steady response (single global scale tried and rejected: it cooled the distant heater by 18 %); animation of the power step also for the Analytical model. Version bump to be decided at the release.
- 2026-10-16: Released **2.1.0** (power profiles + computed heat transfer coefficients), merged `feature/more-models` into `develop` and `main`, tag `v2.1.0`. Next: Component element (Package, heat heatsink), then Gerber import and variable stack-up.
- 2026-10-16: Implemented computed heat transfer coefficients (`convection.py`, `Board.h_mode/emissivity_top/emissivity_bottom/air_speed/orientation/h_calibration`, Picard loop outside the models in `api._solve_computed_h`): one `h` per face from the mean face temperature, radiation always included (emissivity per face, default 0.9), global convection multiplier, edge `h` stays typed, time simulation and animation fixed at the steady-state coefficients. Measured effect on the example: a constant `h` overestimates the rise by 10 % at 22 W and underestimates it at low power (`roadmap.md` section 2).
- 2026-10-16: Roadmap extended: heat heatsink on a component (θCS + θSA in K/W, θSA scaled with ΔT from a reference rise, optional heatsink capacity C_hs from the first version), Gerber import of the copper per layer (section 7, `gerbonara` as candidate, fill fraction per cell), and variable stack-up (section 8: per-gap dielectric thickness and material, layer nodes of copper plus half the adjacent dielectrics, backward compatible when gaps are equal). All future work, nothing implemented.
- 2026-10-16: Researched the Package (JEDEC 2R) basis and recorded it in `docs/package_models.md` (sources read: NISTIR 7648, TI SPRA953B, Renesas white paper, Semiconductor Digest, Siemens). Rules taken from it: the user enters θJB and θJC,top as resistances, never ψ; ψJT and ψJB are reported as consistency checks; θJB is spread over the footprint with area weights; the Package is quasi-static until a Foster chain exists; the share of power into the board is checked against 75 to 95 %. Unverified figures (2 to 20 % error of 2R) are not used. Implementation order: computed `h` first, then the Component element.
- 2026-10-16: Future Component element agreed: one element with a type (Source = today's heater, Package 2R, passive areas such as cooled area, contact, material patch); its power and profile drive `T_j`, top cooling uses the computed `h` (Picard iteration), the profile decision measures the oscillation at `T_j`. Thermal resistance is displayed in K/W (same number as °C/W). Multigrid and the 3D FEM validation script are kept in `docs/roadmap.md` as optional future work; computed `h` and the Component element follow after the current models are polished. See `docs/roadmap.md` sections 2 to 5.
- 2026-10-22: **Released 2.4.0** (parts, advanced stack-up, outline, power calculator, preferences, typical heatsinks); `develop` merged into `main`, tag `v2.4.0`, the auxiliary feature branches deleted; work continues on `develop`.
- 2026-10-22: **Typical heatsinks** (maintainer): the boxes of the top path appear as soon as θSA > 0 (no orange message, no greyed boxes); `Heater.heatsink` names a typical heatsink and flow ("heatsink, flow") of the library `heatsinks` (11 catalogue entries with θSA, source and test conditions, editable in Preferences; flow factors, fan and geometry kept in the roadmap, `docs/research.md` R3) that fills θSA, or Custom/None; the family note for a custom part reads "Custom: no typical values applied".
- 2026-10-22: **Heater as a source or a component** (maintainer agreed option 1): `Heater.role` ("source"/"component"/"" inferred) with `base_interface`/`base_pad_*` (the interface under a pure source, K cm2/W over the footprint) and `junction_theta()`; the package family list fills θ, θJC(top) and Tj max from the library `package_theta` (editable in Preferences). GUI first; naming, box order and the report of a source still to tune (`docs/research.md`).
- 2026-10-22: **Power calculator: band, tabs, help** (maintainer): the two routes are independent tabs; a Help button shows `pcbthermal/help/calculator.html`; the window keeps its size (parameters not used by the point are greyed); `inverse.power_band` gives best / nominal / worst from the one-at-a-time effects of copper, heat transfer, theta, psi_JT and the reading combined by root-sum-square (defaults in the `calculator` section of defaults.json); the selector decides which power is written into the part. Two-point fit is a study only; the known-power reference is not implemented (applies only to parts with a controllable dissipation, and the copper error it fixes goes away with Gerber/KiCad import).
- 2026-10-22: **Power calculator reworked and documented in `docs/calculators.md`** (maintainer): the program starts with an empty board (the example is in File - Open example), the menu entry is "Power calculator…", the parameters (θ, ψJT) are fields of the calculator that appear when the chosen point needs them, every field has a hint, the result shows the temperatures at the power found and the board resistance, and the validation against datasheets is `research/power-calculator/scripts/calculator_validation.py` (CSD17308Q3 -1.7 %, JEDEC 2s2p exposed-pad QFN +3 %). Defaults for new projects are one tab of Preferences with four boxes.
- 2026-10-22: **Preferences and defaults in JSON** (maintainer): `pcbthermal/data/defaults.json` (libraries: via fills, metals, interfaces, dielectrics, package theta; sections new_board, new_elements, materials, solver) plus a user file `user_defaults.json` in the configuration folder (`PCBTHERMAL_CONFIG` or the per-user folder) holding only the differences (entries merge by name, `removed` hides names); read at start-up and cached by file time, so the program knows by itself when it exists: status bar label, start-up message and About box. `model.DIELECTRICS/VIA_FILLS/METALS/INTERFACES/PACKAGE_THETA` are lists refilled in place by `model.reload_libraries()`; `model.new_problem()` and `api.default_options()` apply the defaults; the physics core API (`Problem.new`) is unchanged. Tests use a private `PCBTHERMAL_CONFIG`. Via fill is chosen by name; its conductivity is an editable field (typical value from the library).
- 2026-10-22: **Via fill** (maintainer's question, fabricator pages read): a "filled" via is normally an epoxy resin plug that conducts like FR-4; `Via.fill_k` + `VIA_FILLS` give open / resin (0.3 W/mK) / conductive paste (8) / electroplated copper; only copper matters (3.3 times the barrel, -3.9 K on the example). **Power from the top of the package** added to `inverse.py` and the calculator (theta + psi_JT); the study shows the copper dominates the error (11 to 45 %), so the datasheet shortcut theta_JA - psi_JT is not offered.
- 2026-10-22: **Metal block in the Lumped and Analytic models, steady state** (maintainer asked to reactivate and find a way): after a first decision to leave them out (the equivalent coefficient was 10 to 31 % off), 74 test cases (`research/block-and-fins/scripts/block_equivalent_study.py`) showed that an equivalent coefficient with contact area and an annular fin is still 9 to 11 % off, while the block as one more layer of the ring network (Lumped, 2.0 % mean / 4.8 % max) and as a Schur complement on the tile graph of the Green-function correction (Analytic, 1.1 % / 4.3 %) work; no time simulation for them with a block. Other fields that do not apply are greyed or hidden (settings of unselected models, the top path without θ and θSA). Fins validated against a 2D fin (24 cases within 0.08 %); the 3D solid verified against Yovanovich's Table 3 (0.7 to 0.8 %) and a GCI study (1.14 %); the fin-array channel effect (Elenbaas, Bar-Cohen and Rohsenow) is not modelled and not validated against a datasheet.
- 2026-10-22: `docs/roadmap.md` restructured (maintainer): chapters "What has been implemented" and "What we want to implement" as bullet lists; the Component evidence and its references moved to `docs/research.md`; whenever something is implemented it moves to the first list in the same commit, and every source read goes into the bibliography of the document that uses it.
- 2026-10-22: GUI reorganisation (maintainer): the Properties panel groups fields in titled boxes; a heatsink is Manual input (h or θSA, one typed and the other shown) or Metal block (own boxes); Direct contact interface preset; the simple stack-up and Materials moved to the Stack-up tab; right-click menu on the board (vertex add/delete, add elements). Tests set a conftest autouse that answers the modal messages (a real dialog blocked the battery once).
- 2026-10-22: **Lumped and Analytic on a board with an outline** run on the rectangle of the same area (`Problem.equivalent_rectangle`, box and positions scaled by sqrt(area ratio), parts keep their size, field stretched back) instead of being skipped; the message is only the warning in the Results summary (a pre-run dialog was tried and removed at the maintainer's request: simpler). Chosen by test (`research/outline/scripts/outline_rectangle_study.py`, `docs/validation.md` 13): the bounding box is 6 to 10 % cool on a circle, a box enlarged outwards is worse (10 to 20 % cool), the same-area box is within 0.2 to 3 % away from the edge; near the edge or in a T arm it is 10 to 18 % cool (documented, warned). No time simulation for these two models on an outline. The About box no longer lists library versions.
- 2026-10-17: Added `docs/theory.md` (maintainer request): the complete mathematical and physical formulation of every model (layered idealisation, FVM, FDM, 3D solid, Lumped, Analytic, metal blocks, convection, parts, profiles), written from the code; `tests/test_docs.py` checks that it covers every model module. Rule: a change to a model or a formula updates `theory.md` in the same commit.
- 2026-10-17: **Parts implemented** (branch `feature/component-element`): `Heater.theta` (junction-to-pad, worst case; old key `theta_jb` still read), `tj_max` (margin, power limit, warning), `psi_jb` (ring estimate), `power_tc` (fixed-point loop around the solve in `api._solve_with_tc`, runaway detection), `model.PACKAGE_THETA` (typical θ by family), inspector hints, Components table columns. Decided with the maintainer: θ always worst case; no top heatsink on the IC for now (kept in `docs/research.md` and `docs/roadmap.md` 1.11); heatsink fixed `θsa` when it comes. `docs/research.md` pruned to what is still open.
- 2026-10-17: Added `docs/research.md` for investigations before they are implemented (Component: which θ, top heatsink and interface, heatsink larger than its contact, temperature-dependent power); the studies of roadmap 1.9b and 1.9c moved there.
- 2026-10-17: Heatsink presets: metals (Al, Cu, brass, carbon steel, stainless) and interface materials (grease, default paste 0.5 K cm2/W, gap pads) as `model.METALS` and `model.INTERFACES`; the study (`heatsink_study.py`, `docs/roadmap.md` 1.9c) showed that the interface matters on top of a small package and the metal hardly matters under the board; with only θJB or ψJB the ring-temperature estimate `Tj = T_ring + ψJB·P` is the least pessimistic.
- 2026-10-17: **Release 2.3.0 rewritten at the maintainer's explicit request** (the only exception to the no-rewrite rule): the metal block, the Heatsink rename, the 3D solid and the copper/component studies, all done on `feature/component-model`, were folded into 2.3.0; `main` was reset to before the first 2.3.0 merge, develop merged in, tag `v2.3.0` recreated and force-pushed. The Component element (previously planned as 2.4.0) continues on `feature/component-element` and will be the next version.
- 2026-10-17: **3D solid model** `solid3d.py` (own finite volumes on a structured 3D grid, SciPy only) chosen over adding scikit-fem as a dependency: assembly with NumPy slices, conservative, per-cell volume-averaged materials (the tiled-conductivity method), real barrel copper area for vias, exact power, same plan grid as the FVM; 0.1 to 10 s; steady state only (time simulation stays with the layered models); skipped with a warning above 2 million unknowns. scikit-fem stays as the offline cross-check of the 3D solid itself (FV and FEM bracket the same limit on small pads). Component study (`docs/roadmap.md` 1.9b): keep the Source with one junction-to-pad resistance, add a top path only as an optional heatsink block; no ψ, no mandatory 2R, no Foster chain for now.
- 2026-10-16: **Sink renamed Heatsink** (class, `add_heatsink`, `Problem.heatsinks`, JSON key `heatsinks`, GUI, docs); old files with `sinks` and the legacy editor type "Sink" still load. The copper that dissipates needs no element (confirmed against the 3D solid, `docs/validation.md` 3.1; Lumped/Analytic unreliable for a one-sided pad): outer-layer copper already radiates/convects through `h_top`/`h_bottom` and spreads through its sheet conductance (`docs/models.md` section 1).
- 2026-10-16: Metal block on `feature/component-model`: a Heatsink with `thickness>0` is a heat spreader (extra node layer in FVM/FDM, `blocks.py`), heat enters only where it overlaps copper (intersection of planes), laminate in series elsewhere; Lumped/Analytic use an equivalent coefficient and warn; validated within 1.8 % of the 3D solid (whose script had a singular-matrix bug, fixed). Component design still to be discussed with the maintainer.
- 2026-10-16: Implemented power profiles on `feature/more-models` (square wave only; `profiles.py`; all three models; GUI "Power profile" tab; CLI options). Decision average-vs-resolve per heater from the oscillation in °C (default 1 °C, shared error budget, smallest first), mixed regimes in one run; start = steady state of the average power or a typed °C; duration until the cycle repeats / N cycles / fixed time; 200,000 step cap. Analytic transient smears vias and heatsinks (warned). GUI labels descriptive ("Finite volume (FVM), reference", "Thermal network (LPTN)", "Analytical (Fourier series)"), keys unchanged; units °C and °C/W. Results tab index is now 2 (Board, Power profile, Results).

- 2026-10-15: Created CLAUDE.md. Decided that all code, comments, and docs are
  in English, with `#` inline comments and Doxygen-style docstrings.
- 2026-10-16: Working branch is `develop` (it holds the application code). Added
  `.claude/settings.local.json` with broad permissions, `.gitignore`, and documented
  the real project structure and run command.
- 2026-10-16: Git policy defined: merge to `main` only for solid developments, tag only for good releases. Git rules made explicit in the local settings.
- 2026-10-16: Full algorithm review done; findings recorded in "Algorithm Review". No solver code changed yet.
- 2026-10-16: Added `docs/thermal_models.md` documenting the three models (formulas as implemented), validation experiments, review findings and references.
- 2026-10-16: Started the rebuild (branch `feature/physics-core`, merged into `main` as 2.0.0): new GUI-independent package `pcbthermal` (FVM reference, ring-network lumped, modal analytic, CLI, plots, 30 tests). Cell-centred finite volumes chosen over node-centred FD (exact power and area conservation, no half-cell borders); sparse direct/CG solver instead of SOR; FR-4 anisotropic (0.3 through, 0.9 in-plane); hollow via barrels; analytic uses the exact multilayer fin series instead of Lee spreading formulas (their coefficients could not be sourced). See `docs/physics_core.md`. The legacy `core/` and `ui/` are untouched; the planned UI is PySide 6 on top of `pcbthermal`.
- 2026-10-16: Lumped rewritten as per-heater ring networks aggregated from the real geometry (24 % -> 1 % error on the example); Analytic got copper weighting, Green-function corrections for vias and heatsinks and validity warnings (47 % -> 9 %). New public API: `SolverOptions`, `simulate`, `Problem` builder (mm, 1-based layers), `Project` files. SOR kept as an optional FVM solver (vectorised red-black) to compare with the direct sparse solve: same answer with a residual criterion, wrong answer with the original step criterion.
- 2026-10-16: Legacy wxPython code removed. PySide 6 GUI built on `pcbthermal` (editor canvas, panels, results tabs, themes, undo/redo). Transients exist in the CLI (`--gif`) but are out of the GUI scope for now, at the user's request. Virtual environment `.venv/` created and ignored by git.
- 2026-10-16: SOR and the sparse direct solver give the same temperatures (≤1e-8 K on five boards) when SOR stops on the residual; the direct solver is the default (3 to 30 times faster). Real-time animation added to the GUI (Animation tab) and CLI (`transient --gif`), validated against an exact exponential (Euler first order, Crank-Nicolson second order). Docs added: `new_approach.md`, `candidate_methods.md`. The `example_board` vias use 3.5 mm pitch (same positions as the legacy comparison).
- 2026-10-16: Models tuned after an audit (see `docs/findings.md`): Lumped uses offset-contour rings from the real footprint with exact disc interior relations and a Bessel vertical-loss correction (example board +24 % -> -2 %); Analytic weights copper per layer with the layer's own fin length (+47 % -> -2 %). Added `checks.py` (input validity warnings, shown live in the GUI), `suggest_cell_mm` (Auto cell size), a documentation test gate, and the findings/index docs. Corrected an earlier wrong claim that vias made the FVM mesh-dependent by 1 % (it was a different via layout).
- 2026-10-16: Released **2.0.0** (first release of the rebuilt program; the old wxPython program was 1.0.0, so a major bump avoids a clash). Added `docs/model_guide.md` (which model to use), `CHANGELOG.md`, README with screenshots (`examples/make_screenshots.py`), version shown in the GUI, `--version`, version recorded in reports and projects.
- 2026-10-16: Git language rule made explicit: branch names, tags, commit messages and PR text are in English, with naming conventions (`feature/<topic>` kebab-case, imperative commit subjects of at most 72 characters). History audited, nothing needed to change.
