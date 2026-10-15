# CLAUDE.md

Project memory for Claude Code. Keep this file up to date as the project evolves:
record decisions, architecture, commands, and conventions here.

## Project Overview

**PCB Thermal Simulator Tool** (v1.0.0) is a graphical application for simulating
the thermal behavior of printed circuit boards (PCBs).

- Author: Pedro Silva (PMS Labs)
- License: (C) 2025 Pedro Silva. All rights reserved (see `LICENSE`).
- Users draw PCB elements (zones, heaters, vias, sinks), configure parameters,
  and run simulations with three solvers:
  - **Analytic**: closed-form approximations for quick estimates.
  - **Lumped (LPTN)**: lumped-parameter thermal resistance network, multi-layer.
  - **FDM**: finite difference method using a SOR solver, multi-layer, with
    boundary conditions and convergence checks.
- Outputs: heatmaps, time-evolution GIFs, hotspot detection, gradients,
  zone charts, and PNG / TXT / GIF export. PCB configs are imported/exported as JSON.

See `README.md` for the full feature list.

## Technology Stack

- Python 3.8+
- wxPython (GUI)
- NumPy (numerical computation)
- Matplotlib (plots and heatmaps)
- Optional: Numba (FDM performance), SciPy (future extensions)

## Language and Documentation Rules

These rules are mandatory for all code and documentation in this repository.

1. **Everything is in English**: code, identifiers, comments, docstrings,
   commit messages, PR descriptions, and documentation files.
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
   whenever behavior changes.

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
- Commit messages and PR descriptions are in English.
- The Claude GitHub app is installed on the repository (`/install-github-app`).

## Project Structure

```
main.py                  Entry point: creates the wx.App and the PCBEditor frame.
config.py                Central constants: metadata, physical defaults, solver defaults, UI styles.
core/
  solver.py              ThermalSolver: validates json_config and dispatches to a solver.
  analytic_solver.py     AnalyticSolver + AnalyticResultsDialog.
  lumped_solver.py       LumpedSolver (LPTN) + LumpedResultsDialog.
  fdm_solver.py          FDMSolver (SOR, optional Numba kernel sor_update) + FDMResultsDialog.
ui/
  editor.py              PCBEditor (wx.Frame): canvas, drawing tools, parameter panels (~3000 lines).
ico/                     Application icons.
```

Data flow: the editor builds a `json_config` dict (`pcb_params`, `elements`,
`solver_mode`) -> `ThermalSolver.validate_config` -> the selected solver's static
`simulate` method -> a results dialog class chosen from `ThermalSolver._DIALOG_MAP`.

Known gaps (to improve): solver code and wx results dialogs live in the same
files, and there are no automated tests yet.

## Commands

```sh
pip install wxPython numpy matplotlib   # core dependencies
pip install numba scipy                 # optional (Numba speeds up FDM)
python3 main.py                         # run the application
```

Tests, linting, and formatting are not set up yet. Add the commands here once they exist.

## Branches

- `main`: stable, only has `README.md` and `LICENSE`.
- `develop`: active development branch with the working application. Work on
  `develop` (or feature branches created from it) and open PRs into `develop`.

## Maintaining This File

Update `CLAUDE.md` whenever something important happens: architecture or
structure changes, new commands, new dependencies, workflow or convention
changes, and notable decisions. Add an entry to the Decisions Log in the same
change. Do this without being asked.

## Claude Code Settings

`.claude/settings.local.json` (gitignored, personal) gives Claude broad access in
this repository: all file tools and Bash are allowed, with `acceptEdits` as the
default mode. A few commands stay denied: `sudo`, force pushes, and `rm -rf` on
`/` or `~`.

## Decisions Log

Record important decisions here, newest first, with date and reason.

- 2026-10-15: Created CLAUDE.md. Decided that all code, comments, and docs are
  in English, with `#` inline comments and Doxygen-style docstrings.
- 2026-10-16: Working branch is `develop` (it holds the application code). Added
  `.claude/settings.local.json` with broad permissions, `.gitignore`, and documented
  the real project structure and run command.
