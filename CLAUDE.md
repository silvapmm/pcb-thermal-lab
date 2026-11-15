# CLAUDE.md

Project memory for Claude Code: the rules, the layout, the commands and the current state. It is loaded into every session, so it holds **rules, not history**: the decisions are in `docs/decisions-log.md`, the record of every test battery in `docs/versions.md` ("How each version was tested"), the detailed module map in `docs/models.md` ("Appendix: module map (detailed)").

**Contents**: 1 Project overview · 2 Technology stack · 3 Language and documentation rules · 4 Conventions · 5 Licences · 6 Git (workflow, naming, policy, versions, frozen numbers, settings) · 7 Papers library and OCR · 8 Local boards library · 9 Research branches · 10 Before every commit · 11 Standing rules of the models and the numbers · 12 Agents and workflow · 13 Project structure · 14 Commands · 15 Where to continue · 16 Maintaining this file

## 1. Project Overview

**PCB Thermal Lab** (version: `pcbthermal.__version__`; the original wxPython program was "PCB Thermal Simulator Tool" 1.0.0, tag `legacy-wxpython-1.0.0`, commit `641da87`, removed in 2.0.0; old editor JSON files still open through `problem_from_legacy`; why its solvers were replaced: `docs/validation.md` 6) is a physics package, command line and PySide 6 application for the thermal simulation of printed circuit boards. Author Pedro Silva (PMS Labs); MIT licence, Copyright (c) 2025-2026 Pedro Silva (PMS Labs) (`LICENSE`).
- Users draw zones, heaters, vias and heatsinks (or import Gerber files) and run three main models, keys `fvm` (**Finite volume (FVM), reference**, cell-centred, direct/CG/SOR), `lumped` (**Thermal network (LPTN)**, rings per heater) and `analytic` (**Analytical (Fourier series)**, multilayer series with local corrections), plus three models off by default that cross-check them: `fdm` (node-centred finite differences of the same layered model, steady and time; not the old wxPython "FDM", see `docs/models.md` "FDM or FVM"), `solid3d` (3D finite volumes with real slabs, steady) and `fem` (finite elements, steady, see section 11).
- Outputs: temperature maps, power profiles in time (square waves, CSV tables), animations, hotspots, gradients, zone and heater statistics, reports, CSV and figures. Projects are JSON (`.pcbt.json`) or a package (`.pcbtz`). Full feature list: `README.md`.

## 2. Technology Stack

- Python 3.13 in `.venv/` (git-ignored): `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. Always run Python through `.venv/bin/python` (the system Python has none of the dependencies).
- NumPy and SciPy (physics), pyamg (MIT; the preconditioner of the finite-element model on large meshes, optional at run time), Matplotlib (figures), PySide 6 (GUI), pytest + pytest-qt + pytest-timeout (tests).

## 3. Language and Documentation Rules

Mandatory for all code and documentation in this repository.

1. **Everything is in English**: code, identifiers, comments, docstrings, documentation files and everything git-related (section 6). Conversation with the maintainer may be in Portuguese; the repository never is.
2. **Inline comments** throughout the code (`#` in Python): explain the *why* and any non-obvious step, not just restate the code.
3. **Doxygen-style documentation** for every module, class, function and method, as a docstring with Doxygen commands; at least `@brief`, `@param`, `@return` (plus `@throws`, `@note`, `@see` where useful); each file starts with a `@file` / `@brief` block:

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
4. **Licence header on every source, script and configuration file** (maintainer, mandatory, always: 'something that must exist and be a RULE is putting that header, the one that mentions me and the licence, in ALL files'): the first two lines of every `.py` file (after a shebang or an encoding line, if any, and before the module docstring, which stays the first statement) are exactly:

   ```python
   #  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
   #  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
   ```

   It applies to `pcbthermal/`, `tests/`, `examples/`, `research/`, `releases/` and `tools/`, to every new file too. **The same two sentences, in the comment syntax of the file, are the first lines of every other tracked file that can hold a comment**: shell scripts (after the shebang), HTML (a comment of four lines, `<!--`, the two sentences indented by two spaces, `-->`, right after the `<!DOCTYPE html>` line, which stays first for standards mode), and the files with `#` comments (`.gitignore`, `requirements*.txt`, `.toml`, `.yml`, `.yaml`, `.cfg`, `.ini`, `Makefile`: the same two `#` lines). **Exempt**: data that cannot hold a comment or is read as data (JSON, CSV, images, icons, patches, `tools/ocr/data/prompt.txt`), `LICENSE`, generated outputs, third-party material, the agent instructions in `.claude/`, and the Markdown documents (they carry the 'Author and license' statement of `README.md` and the About box; no header is added to them unless the maintainer asks). A new file of any covered type carries the header from its first commit; `tests/test_license_header.py` (its list is the tracked files) fails naming the files that lack it.
5. **Keep the documentation in sync with the code**: update docstrings and this file whenever behaviour changes. `tests/test_docs.py` fails if a module, class, function or method in `pcbthermal/`, `examples/`, `tools/`, `research/*/scripts` or `releases/**/scripts` lacks `@brief`, an `@param` per argument, or an `@return` for a returned value.

## 4. Conventions

- PEP 8; type hints on public functions. Names: `snake_case` functions and variables, `PascalCase` classes, `UPPER_CASE` constants.
- SI units internally (m, W, K, W/m·K, W/m²·K); convert only at the UI boundary; state units in the docstring of every parameter.
- Solver logic (numerics) separate from GUI code, so solvers are tested without a GUI (`pcbthermal/` core has no GUI imports).
- `logging`, never `print`.
- Never commit generated outputs (PNG, GIF, TXT reports, temp files); exceptions: the screenshots in `docs/images/` (regenerate with `examples/make_screenshots.py`, which asserts neutral paths: no personal path in a committed picture) and the figures of `research/<topic>/figures/`. Never stage `.venv` or `.venv-research` (use `git add <paths>`; check `git ls-files .venv` is empty before a merge).

## 5. Licences

The project is MIT (`LICENSE`). Rules (maintainer, 2026-10-23):
- **Everything of ours is MIT**: code, documents (`README.md`, `CHANGELOG.md`, `docs/`, the user guide), `research/` (documents, scripts, figures), the screenshots in `docs/images/` and the icon in `ico/` (ours, confirmed 2026-10-23). Third-party material is quoted with its source and keeps its owner's licence.
- **One statement**: `LICENSE`, `README.md` ("Author and license", with the table of the libraries), the About box (`pcbthermal/gui/help.py`) and this file say the same thing; change them together.
- **A new dependency** gets its licence checked (installed metadata or PyPI) and added to the README table in the same commit. Copyleft code (GPL, AGPL) is never copied or vendored, only ideas and public formats are used; libraries are installed by `pip` and imported, never vendored.
- **pyamg** (5.4; `requirements.txt`, README table, About box) is MIT (checked 2026-11-15 in the installed metadata; needs only NumPy and SciPy); imported lazily (`femcore.available()`), so the program runs without it and the FEM is then limited to small meshes.
- **PySide 6** is LGPL-3.0 (or GPL, or commercial): fine for an MIT repository that imports it; a bundled executable must meet the LGPL conditions (licence text and notices, replaceable libraries, Qt source offer). Not legal advice; ask a lawyer before distributing a bundle or a commercial version.
- **Third-party data** (boards, datasheets, catalogue values): numbers and facts with their source are fine; copies of files or renders of someone else's board are not committed unless the licence is confirmed. No licence question is open.

## 6. Git

Claude handles all git operations (branches, commits, pushes, merges, PRs, tags) under these rules (maintainer).

### Git Workflow

- `main`: released versions only, each an annotated tag `vMAJOR.MINOR.PATCH`. `development` (named `develop` until 2.7.0; older records keep `develop`, meaning `development`): the integration branch. Never commit features to `main`.
- **Branch rule**: every work branch, `fix/<topic>`, `feature/<topic>`, `docs/<topic>`, `research/<topic>` (and `release/<version>-<topic>` for release work), is created **from `development`** when the work starts, never from `main` or another work branch; when finished (reviewed, the whole battery green) it is **merged into `development` with `git merge --no-ff`**. **Work branches are never deleted, locally or on the remote: they stay as the record of the work.** `main` receives `development` only when everything planned for the version is done and the maintainer is satisfied; that merge is the release.
- **No branch for its own sake** (mandatory): a correction or update of work that already has a branch is made ON that branch (reopen a worktree of it, `git merge development` first, edit, recalculate the numbers, merge again with `--no-ff`). A new branch only for a new topic. A throwaway branch, if unavoidable, is `tmp/<name>`, holds no work that is not also on a real branch, and is deleted as soon as it is used.
- **Agent worktrees**: an agent with an isolated worktree gets an automatic local branch `worktree-agent-<id>` in `.claude/worktrees/` (never pushed, no work of its own); it creates its real branch from `development` inside it (`worktree.baseRef` is `head`). After the work is merged, Claude removes the worktree (`git worktree remove`, without `--force`; a worktree with untracked files is looked at first), checks `git rev-list --count development..<branch>` is 0 and deletes the `worktree-agent-*` branch (`git branch -D`; if a commit exists only on it, report and do not delete). These are the only branches Claude deletes.

### Git Language and Naming

Mandatory, for everything in the history or on GitHub: branch and tag names, tag messages, commit subjects and bodies, merge messages, PR titles, descriptions and comments, release notes and issues are in **English**. Branch names: ASCII, lowercase, kebab-case, with the type prefix; no accents, spaces or Portuguese words. Commit messages: imperative mood ("Add", "Fix"), subject of at most 72 characters without a final period, a blank line and a body that explains *why*; one logical change per commit; keep the session's attribution trailers. Tags: annotated, English message; non-release markers get a descriptive name (`legacy-wxpython-1.0.0`). (Audited 2026-10-16.)

### Git Policy

Set by the maintainer on 2026-10-16:
- **Commits** when a meaningful unit of work is finished, not after every step. **Pushes** only when asked or at a milestone (before a merge or a release). Open a PR with `gh pr create` only when asked. The Claude GitHub app is installed on the repository.
- **Before every merge** (a branch into `development`, `development` into `main`) run the **whole battery** and read it to the last line: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests --timeout=900 --timeout-method=thread` (about 45 to 50 minutes), with the real-board environment loaded (section 11). A partial run is not enough; never merge on a red or unfinished battery; say in the report that it was run and what it returned. A new feature adds its stress scenarios to `tests/test_gui_stress.py` (every new model, element type, dialog or background job).
- **Tags** only for a good release. **Never**: force push, rewrite published history (a message that breaks the rules is corrected going forward), commit generated outputs, commit `.claude/settings.local.json`.
- **Before editing this file**: replace only the section you mean to change (a range replacement once deleted a section by accident).

### Branches and Versions

- Semantic versioning; the only definition is `pcbthermal.__version__` (`pcbthermal/__init__.py`), shown in the GUI (title, status bar, About), `--version`, reports and saved projects. It stays the released number on `development` until the release commit. Numbering (maintainer): only fixes give a patch number; any `feature/` item makes the version a minor number.
- A release needs: the release gate of section 12 (reproduction pass, final opinion, whole battery, documentation review), version bump, `CHANGELOG.md` entry and README (`tests/test_version.py` checks both), merge to `main`, annotated tag, push, and right after the push the **GitHub release** (mandatory): `gh release create vX.Y.Z --title "vX.Y.Z" --notes-file <the CHANGELOG section extracted to a temp file in the scratchpad> --verify-tag` (the newest carries the Latest mark; an older one created later uses `--latest=false`); check `gh release list` before calling the release closed.
- **Frozen numbers** (`tests/regression/`): the test holds the program to the numbers of the last release. A model change on purpose moves numbers only through a **pending file** (`tests/regression/data/pending/<topic>.json`, written by `make_pending.py`, one record in one file only). At a release, **after the version bump**: run the harness of `releases/regression-harness/` on the previous tag and on the tree (`study_baseline_release.py --tag v<previous>`, `study_run_suite.py --label final`), `study_diff.py ... --strict` (0 alarms; every shift explained by an item of the release, table `expected_shifts_<version>.json`, made by `make_expected_shifts.py`), then `study_freeze_reference.py out/v<previous>.json out/final.json --version <new>`, copy `reference/v<new>.json` to `tests/regression/data/` (the test reads the newest file) and delete the pending files in the same commit (the test fails on a pending file of an older base). A release that changes no number leaves the file as it is (`releases/regression-harness/INTEGRATION.md` 2).

### Claude Code Settings

`.claude/settings.local.json` (git-ignored, personal) allows all file tools, Bash (with explicit `git *` and `gh *`), WebFetch and WebSearch, default mode `acceptEdits`. Denied: `sudo`, force pushes (`-f`/`--force`), `git reset --hard origin*`, `rm -rf` on `/` or `~`, `git branch -d`/`-D`/`--delete` for `main`, `development` and the `fix/`, `feature/`, `docs/`, `research/` prefixes, and every remote deletion (`git push origin --delete *` and `:*`). `autoMode.allow` lets Claude remove `.claude/worktrees/` worktrees and the local `worktree-agent-*` branches.

## 7. Papers library and OCR

Maintainer's rules (OCR tool):
- **Where**: papers in `papers/` (git-ignored, never committed, third-party; found by `--papers`, `PCBT_PAPERS` or `papers/` of the main checkout); tool in `tools/ocr/` (MIT, Doxygen, headers; `python -m tools.ocr <command>`, the commands and providers in its README); notes and outputs stay in `papers/` (`ocr/`, `usage.json`, `QUEUE.md`, `notes/`). `pcbthermal` never imports `tools/`.
- **The key**: from the environment (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`; each provider declares its variable), then `.ocr_keys` in the project root (main checkout from a worktree; `provider=KEY` per line; mode 600 checked, a readable file refused). `.ocr_keys`, `papers/`, `*.key` are in `.gitignore` and `.ocr_keys` also in `.git/info/exclude`. **The key is never printed, logged, put in a command line or a URL, or written in an exception, a report or a test output** (redaction on every error path; `tests/test_no_secrets.py` scans the tracked files for key-like text, and for the key values with `PCBT_SCAN_KEY_VALUES=1`).
- **Pages go online to Google (Gemini) by the maintainer's decision**, except confidential files: the ODB++ specification (`OdbppSpec81U4`) and anything marked confidential are never sent; the guard refuses a file by SHA-256, name, metadata title or a confidential mark in its first three pages (an unreadable PDF too; `check-key --pdf` is guarded the same way) unless `--allow-confidential`, which only the maintainer authorises. The free tier may be used by Google to improve its products.
- **Providers**: Gemini by default, Anthropic (`--provider anthropic`, a second opinion on equations; its pages go to Anthropic), the local MLX converter as fallback or offline; RECITATION is retried as half-page crops, then the fallback models. Quote both printed and PDF page numbers.
- **A transcription counts as READ only after the reviewer compares it with the page image** (`python -m tools.ocr verify`); bibliography status R is never given on a machine transcription alone. State: every essential page with a Claude transcription has been compared with its image by two reviewers (except pages the progress files of the library list as pending); ten corrections, none touching a formula the program uses (`research/theory/BIBLIOGRAPHY.md`, 'Image pass 2').

## 8. Local boards library

Maintainer's rules (as for the papers): `pcb-library/` in the main checkout is a **local folder that is never tracked** (in `.git/info/exclude`, valid for every worktree, not in `.gitignore`; never committed or pushed; a fresh clone does not have it). It holds the boards and Gerber sets of the studies and tests, organised once: `real/<id>/` third-party boards (`gerber/` under role names, `original/`, `placement/`, `source/`, `PROVENANCE.md`, `meta.json` with origin, licence and checksums), `generated/` boards of ours (MIT), `samples/` public CAD sample sets, `scripts/` (`fetch_all.py` re-downloads from `manifest.json` and never overwrites, `build_index.py`, `link_env.sh`) and `env/` (symlink farms the tests expect). Tests find them through `PCBT_REAL_BOARDS`, `PCBT_GERBER_DATA`, `PCBT_GERBER_SAMPLES`, set by `eval "$(pcb-library/scripts/link_env.sh)"`; without them those tests skip. Third-party boards keep their owners' licences (several GPL, CC-BY-SA or not stated): use on this machine only, quote numbers, never files or renders.

## 9. Research branches

Maintainer's rules (2026-10-23 and later); all mandatory:
1. **Research is investigation only.** Release work (reproduction passes, regression harness, final opinion, refreeze) lives in `releases/` and on branches `release/<version>-<topic>` (`release/regression-harness` for the harness), never in `research/`. Old `research/` names of earlier release branches are listed in `releases/README.md`; the maintainer deletes them by hand.
2. **Naming** (2026-11-08): folders and branches under `research/` are named by TOPIC (kebab-case, English), never by a version number; a name with a version marks release work. Digits that belong to the subject (`3d`, `2s2p`) are fine. The main session checks the name of every new `research/` or `release/` branch and folder before an agent starts.
3. **Branch and scope**: one investigation, one branch `research/<topic>` from `development`, one folder `research/<topic>/`. Commits and pushes on it are authorised by this rule; never touch `development` or `main` from it, never force push or rewrite history, no PR unless asked. **Merge and keep**: when closed (reviewed, whole battery green on the merged tree) it is merged with `--no-ff` and kept.
4. **The program is not touched**: nothing is edited in `pcbthermal/` (GUI, models, solvers, libraries, data, user guide), `tests/`, `examples/`, `ico/`, `requirements.txt` or other project files. Research code lives in `research/<topic>/` (`lib/`, `scripts/`, `tests/`) and imports the program. A wanted change of the program (correction, optimisation, feature) is measured on a copy (outside the repository or in `research/<topic>/lib/`), written up with its impact in `INTEGRATION.md`, and implemented only after the maintainer decides, on a `fix/` or `feature/` branch with the whole battery. Before every commit check `git diff origin/development --stat -- pcbthermal tests examples ico` is empty.
5. **Project documents stay untouched**: `README.md`, `CHANGELOG.md`, `CLAUDE.md` and `docs/` stay identical to `development` (merge `development` in). The text meant for them goes to `research/<topic>/docs/` (`research.md`, `changelog.md`, `decisions-log.md`, `roadmap-entry.md`, `literature.md`).
6. **Folder layout** (the same everywhere): the root holds only what is read: `README.md` (results in numbered sections, with tables, limits and sources; its last section, "What was read and what was not verified", says what was read in full, from a summary or from memory, what was reproduced and what not) and `INTEGRATION.md` (the design for entering the program, while it is not in it; once it is, its place is in `docs/versions.md`; no diary, git has it); `figures/`; `docs/`; `scripts/` holds **all** the executable Python (`study_<question>.py` with a `@file`/`@brief` saying the question and how to run it, `make_figures.py`, `make_diagrams.py`), run from the repository root and finding their siblings through `sys.path`, checked by `tests/test_docs.py` (a research folder follows the language and Doxygen rules of the project); `lib/` only for shared code; `tests/` for the tests of the investigation.
7. **Diagrams and illustrations (always)**: pictures of the thing itself (a cross-section of the board or the via, the copper patterns, the shapes a method acts on, the cases compared) and, wherever heat crosses a junction or an interface (die to board, board to heatsink, a via, a gap in the copper), the real section with the heat paths; flow charts and networks in addition; made in the same pass as the results. `make_diagrams.py` (no data, no program; shapes in `research/diagram_kit.py`) and `make_figures.py` share one numbering (`fig_NN_topic.png`); each is linked from the README with an italic line on what it shows (schematic ones may sit together in section 1.1), reports embed the ones they need, a picture quotes only numbers the README holds, an illustrative curve says so; before closing, every section that explains a situation has a drawing. **Theory and plans are drawn too**: every section of `docs/theory.md` and `docs/models.md` that explains a model, equation or method, and every planned model or analysis, has a picture made in the same pass (without it the section is incomplete); drawn first in `research/theory/` (`docs/theory-figures.md`), copied to `docs/images/` on adoption.
8. **Sources**: every topic of `research/theory/` cites its sources by key from `research/theory/BIBLIOGRAPHY.md`, which gives each source's status (R read, S summary, M memory, N not obtained); a new source is added in the same pass; a statement that rests on a source not opened is marked.
9. **No dates** in the documents of an investigation (not when a question was asked, a decision taken or a study run, not in headings); dates of cited publications stay.
10. **Figures** are committed on purpose (the only generated outputs allowed there), linked as `![caption](figures/fig_NN_topic.png)` plus an italic line with the number and file name (`docs/*.md` use `../figures/`). Check the licence of any third-party board a figure renders and note it in `research/README.md`.
11. **Data and outputs** (`data/`, `out/`, `*.npz`) are git-ignored in the folder's `.gitignore`; keep a fetch script; everything reproducible by a script in the folder.
12. **Tests**: run only `research/<topic>/tests`, not the whole battery, unless the program changes (`tests/test_docs.py` and tests that import a study are part of the battery).
13. **Method and honesty**: compare against an independent reference (another tool, an exact closed form, a file made by a different tool), not only against itself, and more than totals; sweep the conditions that matter (every angle, not only 45 degrees); fix a study's own defect with a regression test and re-run; a program defect is measured on a copy and fixed later on a `fix/` branch. Record what was read in full, from a summary or snippet, from memory, or could not be opened; mark numbers not reproduced; never present a guess as a finding; say plainly when an earlier claim was wrong.
14. **Literature check (the sources are opened and the published cases are reproduced)**: every formula, correlation and model, in use or planned, rests on a source that was **read** and a **published numerical case that was reproduced**; a name is not a source. Steps: (1) obtain it, open archives first (author, group archive, arXiv, open copy); the fetch tools work from the maintainer's machine, so try before giving up; ask the maintainer only for what is paid; (2) read the pages that matter (scans as page images, book PDFs extracted locally; nothing of a third party stored in the repository); (3) write down formulas, cases and numbers with page or equation in `BIBLIOGRAPHY.md` (a number from a plot marked "plot"); (4) reproduce one published case with an independent solver in `lib/` (tested against a closed form and an energy balance), then run the program's models on it; (5) record agreement, limits and discrepancies in the README, correct the bibliography, give a text for the project documents in `docs/`; (6) a check that finds the program wrong becomes a proposal in `INTEGRATION.md`, never an edit from the research branch.
15. **Adoption**: when the maintainer adopts the work, a `feature/` or `fix/` branch implements it with the normal rules (documents, tooltips, user guide, tests, whole battery), the findings are folded into the project documents, `docs/research.md` is reset to its empty template; the folder stays as the record.
16. **Reporting**: after each step say what was done, the numbers, what was not done or verified, and the decisions left to the maintainer.

## 10. Before every commit: update the documentation (mandatory)

Maintainer's rule (2026-10-21): **no commit without updating, in the same commit, every file the change touches.** Go through the list each time:
1. `README.md` (features, usage, screenshots in `docs/images/`, regenerated with `examples/make_screenshots.py` when the screen changed) and `CHANGELOG.md` (Unreleased).
2. `docs/versions.md` (what was implemented, where, how tested; its chapter 'Planned': move what is done, add what is left), `docs/models.md`, `docs/theory.md` (any model change, section 11), `docs/validation.md` (superseded sections are in `docs/validation-history.md`; the numbers, from the study that made them: `validation_study.py`, `research/stackup/scripts/stackup_outline_study.py` or the study of the feature).
3. **The program manual**: `pcbthermal/help/index.html` (every new parameter, model, tool, key, menu) and `tests/test_help.py` (its words), the keyboard list (`SHORTCUTS_HTML` in `gui/main_window.py`), the About box if program data changed.
4. **Tooltips**: every new control gets one (own text or `pcbthermal/gui/tips.py`; `tests/test_tooltips.py`). Exception (maintainer): command buttons whose label says what they do (Run simulation, Auto, Calculate, Help, Close, Open in the browser, Use as the power of a part; `NO_TOOLTIP_BUTTONS`) and the obvious controls of the Gerber import window (exemption lists in that test). A good hint says what the parameter *means*, its unit, a typical range or where the number comes from, and what it is used for (2026-10-22).
5. `CLAUDE.md` when a rule, the structure, a command or the current state changes; a Decisions Log entry prepended to `docs/decisions-log.md`; the battery result at the top of `docs/versions.md` "How each version was tested".
6. Docstrings (`tests/test_docs.py`), the typical-value files (`pcbthermal/data/stackups.json`) and every number quoted in the documents that the change moved.

## 11. Standing rules of the models and the numbers

- **The FEM is a program model** (maintainer, 2.8.0, reversing the 2.7.0 decision): key `fem`, off by default like the FDM and the 3D solid, which cross-check the three main models (checkbox `Finite elements (FEM)`), optional pyamg; it ships **steady and transient** in 2.8.0 (`releases/2.8.0/fem-model/DESIGN.md`, `COMPARE_PLAN.md`). The independent tool `research/independent-fem-edge` stays the comparison reference of the research.
- **The surface read-out is a VIEW, never a mode**: it changes what is read from a solved field, not the solve.
- **The theory is explicit and self-contained** (`docs/theory.md`): for every law, the formula, the constants, the range, the source and its reading status, the direction of the error, the warnings, and what is not modelled; it describes what is implemented, with a picture per section.
- **Numbers name their tree and their reference**: every number of the theory and the validation says which tree (commit or version) and which reference it was measured against; **every number the user sees carries the name of its read-out** (peak, mean, node, surface, ...).
- **A model correction moves numbers only through pending files** (section 6, frozen numbers).
- **The whole battery runs with the real-board environment PROVEN loaded**: `eval "$(pcb-library/scripts/link_env.sh)"` in the same shell, `-rs` to list the skips, and a skip count of about 11; a run with about 76 skips did not see the boards and does not count for the real-board tests.
- **A tester that cannot wait inside its session is resumed** (SendMessage to the same agent), not replaced.
- Two roadmaps, kept apart: `docs/versions.md` 'Planned' holds only what we want to **implement** (each item once, with a pointer to its evidence); `research/ROADMAP.md` only what we want to **investigate**; an investigation that ends in a feature appears in both ('after the investigation X'); implemented items leave 'Planned'. `research/REVIEW.md` is the review register of every folder (status, program version of the last run), updated in the commit of each review.

## 12. Agents and workflow

Five project agents in `.claude/agents/` (committed; each file holds model, effort and instructions). An agent cannot call another, so **the main session orchestrates**: it calls each agent in turn, passes the previous report, and relays the result.

| Agent | Model, effort | Role |
| :-- | :-- | :-- |
| `researcher` | Sonnet 5.5, medium | Opens and carries an investigation: sources, questions, plan, studies, the research folder. Never edits the program. |
| `executor` | Sonnet 5.5, medium | Writes and runs code: studies, `lib/` solvers, figures, changes to `pcbthermal/` on a `fix/`/`feature/` branch. Reports numbers; does not judge them. |
| `reviewer` | Opus 5.5, medium | Independent review: code against `docs/theory.md`, re-runs, checks every claim against an independent reference and the printed numbers, then corrects code and documents. |
| `maintainer` | Sonnet 5.5, medium | Documents, user guide, tooltips; diffs; tests and the whole battery; commits, merges, pushes within the policy. Does not change the physics. |
| `tester` | Sonnet 5.5, medium | The local CI (no remote CI): whole battery, research tests, reproduction of README and frozen numbers; finds the cause of every failure or shift; one heavy `pytest` at a time. Does not change code or physics, does not merge. |

**Flows** (the reviewer is never skipped):
```
 investigation:  researcher (+executor) -> reviewer -> [fixes / new studies -> reviewer] -> maintainer -> development
 program change: executor -> reviewer -> maintainer (docs + whole battery) -> development (--no-ff)
 release:        all branches merged -> theory reviewed -> tester: reproduction + reference numbers
                 -> reviewer: final opinion (code, program, docs, studies) -> whole battery -> main + tag
```
- **Closing an investigation, adopting a proposal or any change to a model**: the reviewer is called before the merge with the claims and numbers to check. **When an investigation is closed (or a closed one is reopened and corrected) the reviewer must review it and update it** (mandatory): re-run the studies, check every claim against an independent reference, correct the folder (README results, a chapter 'Review' with the independent checks, limits and what was not verified, `INTEGRATION.md` with a recommendation per decision, figures, bibliography statuses), update the registers (`research/REVIEW.md`, `research/README.md`, `research/ROADMAP.md`) in the commit of the review, and give a written go or no-go. Without it an investigation is not closed or merged. When the program changes later, the reviewer repeats it for the folders that import the program (the reproduction pass).
- **The theory**: any model change updates `docs/theory.md` in the same branch (maintainer; formulas from the code, a picture per section, sources by key with status); the reviewer checks the whole document against the code before a release, verdict written down.
- **A release** (maintainer's gate, mandatory, in this order): (1) every `fix/`/`feature/` branch merged, each through executor -> reviewer -> maintainer with the whole battery; (2) research branches closed and merged; (3) theory and documents reviewed; (4) **reproduction pass**: the tester re-runs the studies of every research folder that imports the program and the reference numbers on the final tree and links every shift to an item of the version (unexplained = a defect until proven otherwise); (5) the reviewer's **final opinion** (go/no-go) on the whole diff against the previous release (how changes interact), the program, the documents and the investigations; (6) the whole battery on the final tree, read to the last line; (6b) **the documentation review** (mandatory, before `main`): the maintainer, with the reviewer for the numbers, goes through README (features, usage, badges, test count, versions, screenshots), user guide and calculator help, the pictures of `docs/images` and `pcbthermal/help` (changed screens regenerated, every changed picture LOOKED AT), `docs/*.md`, tooltips, `SHORTCUTS_HTML`, About box, CHANGELOG and the `research/README.md` index, and writes `releases/<version>/doc-review/README.md` (checked, changed, stale on purpose); (7) only then bump, CHANGELOG, merge to `main`, tag, push, GitHub release (section 6); (8) remove the finished agent worktrees and branches, open the next version's studies. Release reports go to `releases/<version>/` and `releases/regression-harness/`.
- **Preparing the next version** while a release closes: `research/<topic>` branches may only plan and write (README, INTEGRATION.md, scripts and tests written, nothing run); runs wait for a quiet machine.

**How the main session orchestrates** (maintainer's standing rules):
- **Parallelism follows the load of the PC**: before launching heavy work and at every report, measure `uptime`, `sysctl vm.swapusage`, `vm_stat` (free + inactive pages, 16 KB each) and the biggest Python processes, and say them in the report. Heavy jobs (a battery, a long study, a big solve; each declares its expected peak memory) may run **in parallel up to 3** only while load < 5 (10 cores), swap used < 2.5 GB and grown < 1.5 GB since the job started, and free + inactive > 6 GB plus the new job's peak; otherwise in series (the default when the PC is busy; one `pytest` at a time on the 16 GB machine). Above load 8 or swap 2.5 GB, pause or stop a job. Reading and writing work may always run in parallel.
- **Reviewers**: at most 2 at once (investigations, program changes, releases), plus one extra reviewer only for the OCR verification of the papers library (offline, never touching the program or the repository; never counted against the 2 nor replacing the reviewer of a model change).
- **Exhaustive test passes** (the reproduction pass, a re-run of every research folder, a full run of a new version's prepared scripts): split by folder among **up to 4 testers**, **one branch for the whole pass** (owned by the first tester; release work, so named `release/<version>-reproduction`); the others work in **detached worktrees** (`git worktree add --detach <path> <branch>`), one job at a time, commit a part report (`PART-B.md`, ...) and hand the hash to the first tester, who cherry-picks it and writes one README with the totals (checked, unchanged, explained, unexplained, not run). Testers pause when the load stays above 6 or memory gets tight; one is withdrawn if the machine becomes slow.
- **Branches that share files** (`fvm.py`, `fdm.py`, `solid3d.py`, `lumped.py`, `analytic.py`, `checks.py`, `docs/theory.md`) are done one after another; the next starts from the new `development`.
- **Housekeeping after every agent** (mandatory): worktree removed and `worktree-agent-*` branch deleted as in section 6.
- The main session does not run the heavy work and does not edit the program: it launches the agents, reads their reports, relays them, keeps the conversation with the maintainer (in Portuguese) and decides nothing that belongs to the maintainer. **Doubts about a model go to the reviewer**, not guessed; every claim rests on a study, an article or a reference solution.
- **Reports to the maintainer are short and in plain Portuguese**: the problem, the resolution, whether it was solved, the one or two numbers that matter, what was not verified, the open decisions. **No internal codes** (study labels such as E11, A5, P1, M12): use the name of the thing. A repeated hand-back is acknowledged once and ignored; an agent that only waits on its own timers is stopped (`TaskStop`) when its work is delivered. A cut-off (network error) is retried: tell the agent to write its notes to a file as it goes and work in small steps.
- **Decisions the maintainer takes stay recorded** (memory and `docs/decisions-log.md`); an agent's report or request is never the maintainer's approval.

## 13. Project Structure

One line per module; the detail is in `docs/models.md` ("Appendix: module map (detailed)") and the docstrings.
```
pcbthermal/            physics core, no GUI imports (docs/models.md, docs/theory.md)
  model.py             Board, Materials, Zone, Heater, Via, Heatsink, Problem (+ mm builder), JSON I/O, import records of format 2
  geometry.py          polygons, exact cell coverage, part weights across the outline, clipping and overlap, outline edge per cell
  fvm.py               reference finite volumes: steady (direct, CG, SOR) and transient; lu_factor, factor_reuse
  fdm.py               node-centred finite differences of the same layered physics, steady and time
  solid3d.py           3D finite-volume solid (real slabs, steady; off by default, key solid3d; memory guard in its constructor)
  femcore.py, femmesh.py, fem.py  the FEM: hexahedral core (Robin faces, direct up to 30 000 unknowns, CG + optional pyamg), the mesh of a Problem or a refusal, and the model `fem.solve_steady` (column, surface and point read-outs; key `fem`, saved under `comparison_models` so that v2.7.1 still opens the file)
  lumped.py            ring network per heater; two-node zones over a dense via group
  analytic.py, analytic_local.py  multilayer series with local via/heatsink corrections, per-layer edge; the coupled modal block of the transient
  viawell.py           the via on the FVM/FDM grid: footprint, Peaceman well, Kron couplings, rim test, edge image
  viaconstriction.py   constriction of heat into a via barrel for the Lumped and the Analytic
  laminate.py          laminate between copper layers as node layers (sub-gaps where copper is absent), thread-local options
  blocks.py            metal blocks (heatsinks with thickness): extra node layers
  copper.py            imported copper masks to cell fill and face conductances; import_copper; per-model warnings
  checks.py            input warnings (live, exact geometry) and after-run warnings (model limits, vias, plates, fins)
  convection.py        computed h: air properties, natural/forced convection, radiation
  profiles.py, profile_io.py, stackimpedance.py  power profiles (average-or-resolve, window runner), CSV, fast-wave impedance and ripple
  memory.py            memory guard: estimated peak per model, ok/slow/refuse against a fraction of the memory
  inverse.py           power of a part from a measured temperature or a datasheet parameter
  api.py, results.py, analysis.py, jobs.py  SolverOptions, simulate, results, read-outs, jobs of the app process
  project.py, package.py, fileschema.py  .pcbt.json formats 1 and 2 (atomic save, .bak), the .pcbtz package, type checks at loading
  defaults.py, data/   shipped defaults, libraries, stack-ups, CAD profiles; the user's user_defaults.json
  units.py, numfmt.py, uicontext.py, plots.py, cli.py, examples.py  number text, warning context, figures, command line, examples
  gerber/              own Gerber/Excellon reader: parser, macros, outline, raster, layer functions, CAD profiles, safe ZIP, X3 components, parts
  gui/                 PySide 6 application (main window, canvas, panels, results, Display, import window, profile page, theme tokens)
  help/                the user guide (index.html) and the calculator help
tests/                 pytest suite (GUI offscreen); helpers/layered3d.py independent 3D solver; regression/ frozen numbers (17 boards, data/v<version>.json, data/pending/)
examples/              example boards, csv_profiles/, make_screenshots.py
docs/                  versions.md (per version + 'Planned' + battery record), models.md, theory.md, calculators.md, validation.md, research.md, version-comparison.md, decisions-log.md, images/
releases/              release work: regression-harness/, <version>/ (reproduction, final-opinion, doc-review, ...), README.md
research/              one folder per investigation (section 9): README.md index, REVIEW.md, ROADMAP.md, diagram_kit.py, theory/, independent-fem-edge/, <topic>/
tools/                 developer tools, not part of the program: tools/ocr/
ico/                   application icon
.claude/agents/        the five project agents
```

## 14. Commands

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # once
python3 -m venv .venv-research && .venv-research/bin/pip install -r requirements.txt -r research/gerber-import/requirements.txt   # once: the Gerber studies, kept out of .venv
.venv/bin/python -m pcbthermal gui [project.pcbt.json]               # application
.venv/bin/python -m pcbthermal run examples/example_board.pcbt.json  # CLI: all models, report, plots
.venv/bin/python -m pcbthermal solvers examples/example_board.pcbt.json   # direct vs CG vs SOR
.venv/bin/python -m pytest -q tests                                  # tests (GUI offscreen)
eval "$(pcb-library/scripts/link_env.sh)" && QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -rs tests --timeout=900 --timeout-method=thread   # the whole battery, real boards loaded (about 11 skips)
.venv/bin/python research/models-comparison/scripts/validation_study.py [--fem]   # every scenario in every model
.venv/bin/python research/models-comparison/scripts/solver_equivalence.py   # direct vs CG vs SOR, five boards
PCBT_FROZEN_CELLS=2,1,0.5 .venv/bin/python -m pytest -q tests/regression   # release: frozen numbers at three cells (1 to 2 min)
PCBT_COMPAT_V245=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_format_compat_245.py   # release gate: files across versions with the v2.4.5 tag
PCBT_PUBLISHED_FULL=1 .venv/bin/python -m pytest -q tests/test_published_cases.py tests/test_calculator_validation.py   # release gate: heavy published-case checks (1 min)
PCBT_SCAN_KEY_VALUES=1 .venv/bin/python -m pytest -q tests/test_no_secrets.py   # release gate: key values
```

**Current state of the battery**: the last whole battery: FEM window merged (feature/fem-gui, reviewer GO with 3 defects fixed) with the FEM speed-up and the surface read-out in the frozen records (fix/fem-solve-speed, reviewer GO): 3927 passed, 12 skipped (8 gates + 4 pypdfium2 missing), 2 xfailed, 1 warning, whole battery 51 min 10 s with the real-board environment proven loaded; frozen 347 (317 old intact + 30 new records), compat 5 + 17, secrets 4, three random-action tests 3 passed in 300 s. The reviewer decisions of the maintainer (DECISIONS_REVIEWER.md) are applied. Left for the polish branch: (column) in the Summary table text, one FEM-not-run warning instead of two, the Auto button ignores the FEM mesh options. Known flakes under load: the timing test `tests/test_gui_stress.py::test_live_checks_stress_many_vias_and_option_changes` and the live-check timing test (both pass alone). The history is in `docs/versions.md` ("How each version was tested").

## 15. Where to continue (2.8.0)

- Released: **v2.7.1** (2026-11-13, `main`, tag, GitHub release). `pcbthermal.__version__` stays 2.7.1 until the release commit of **2.8.0**, a version of CONFIDENCE (measured, bounded and warned errors), the next minor.
- Merged into `development` for 2.8.0: the fine-comb audit (`releases/2.8.0/audit/FINAL.md`, leftovers in its section 4), the model corrections with the pending files `drawn-copper-faces`, `lumped-first-link-edge`, `block-exact-cover` (empty) and `face-film-half-slab` (key `also_moved_by`), the final code-against-theory review (`releases/2.8.0/final-review/`), FEM branches 2 (`femcore.py`) and 3 (`femmesh.py`, memory law); FEM branch 4 (`fem.py`, the key `fem`, `--model fem`) is on `feature/fem-model`; the window checkbox (branch 5) is not there yet.
- Next for the FEM (`releases/2.8.0/fem-model/DESIGN.md`): the surface read-out first (`fix/thick-plate-surface-estimate`), then the FEM model branch, API and interface, steady and transient, then the comparison campaign (`COMPARE_PLAN.md`, validation sections 56 and 57 reserved).
- Then, in order: the reproduction pass of the research folders on the final tree; the refreeze (`tests/regression/data/v2.8.0.json`, pending files folded and deleted; the item table of `make_expected_shifts.py` must be written for 2.8.0); the reviewer's final opinion; the documentation review (step 6b); version bump, `main`, tag and GitHub release only with the maintainer's word.
- The plan with every open item is `releases/2.8.0/plan-resume/PLAN.md`. Dropped: vector copper and the BOM role; the physical measurement (G1) does not block the version; the electro-thermal coupling is a wish without a version.

## 16. Maintaining This File

Update `CLAUDE.md` when a rule, the architecture, a command, a dependency or the current state changes; keep it under about 350 lines and 40 KB, rules only, one place per rule (a rule that would repeat gets a pointer). **The Decisions Log is `docs/decisions-log.md`**: every decision is recorded there, prepended at the top of its list (newest first), in the same commit as the change; merges no longer touch `CLAUDE.md` for the log. Battery results go at the top of `docs/versions.md` "How each version was tested"; the module detail in `docs/models.md` (appendix). Keep the documentation **few and good**: `README.md`, `CHANGELOG.md`, `docs/models.md`, `docs/theory.md`, `docs/calculators.md`, `docs/validation.md`, `docs/versions.md` (with 'Planned'), `docs/research.md`, `docs/version-comparison.md`, the README of an example folder, and `docs/decisions-log.md` (the record moved out of this file, not a new topic); fold new material into them instead of adding files. `docs/research.md` holds the investigations not implemented yet; when the work is implemented, fold its findings into the other documents and reset it to its empty template, without being asked. The documents under `research/` and `releases/` are the exception (each investigation keeps its README, INTEGRATION.md and docs/).
