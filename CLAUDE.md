# CLAUDE.md

Project memory for Claude Code: the rules, the layout, the commands and the current state. Loaded into every session: **rules, not history**: the decisions are in `docs/decisions-log.md`, the batteries in `docs/versions.md` ("How each version was tested"), the detailed module map in `docs/models.md` ("Appendix: module map (detailed)"); "appendix A<n>" below is 'Appendix: passages moved out of CLAUDE.md' of `docs/versions.md`.

**Contents**: 1 Overview · 2 Stack · 3 Language and documentation · 4 Conventions · 5 Licences · 6 Git · 7 Papers and OCR · 8 Boards library · 9 Research branches · 10 Before every commit · 11 Models and numbers · 12 Agents and workflow · 13 Structure · 14 Commands · 15 Where to continue · 16 Maintaining this file

## 1. Project Overview

**PCB Thermal Lab** (version: `pcbthermal.__version__`; the original wxPython program was "PCB Thermal Simulator Tool" 1.0.0, tag `legacy-wxpython-1.0.0`, commit `641da87`, removed in 2.0.0; old editor JSON files still open through `problem_from_legacy`; why its solvers were replaced: `docs/validation.md` 6) is a physics package, command line and PySide 6 application for the thermal simulation of printed circuit boards. Author Pedro Silva (PMS Labs); MIT licence, Copyright (c) 2025-2026 Pedro Silva (PMS Labs) (`LICENSE`).
- Users draw zones, heaters, vias and heatsinks (or import Gerber files) and run three main models, keys `fvm` (**Finite volume (FVM), reference**, cell-centred, direct/CG/SOR), `lumped` (**Thermal network (LPTN)**, rings per heater) and `analytic` (**Analytical (Fourier series)**, multilayer series with local corrections), plus three models off by default that cross-check them: `fdm` (node-centred finite differences of the same layered model, steady and time; see `docs/models.md` "FDM or FVM"), `solid3d` (3D finite volumes with real slabs, steady) and `fem` (finite elements, steady, see section 11).
- Outputs: temperature maps, power profiles in time (square waves, CSV tables), animations, hotspots, gradients, zone and heater statistics, reports, CSV and figures. Projects are JSON (`.pcbt.json`) or a package (`.pcbtz`). Full feature list: `README.md`.

## 2. Technology Stack

- Python 3.13 in `.venv/` (git-ignored): `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. Always run Python through `.venv/bin/python` (the system Python has none of the dependencies).
- NumPy and SciPy (physics), pyamg (MIT; the preconditioner of the finite-element model on large meshes, optional at run time), Matplotlib (figures), PySide 6 (GUI), pytest + pytest-qt + pytest-timeout (tests).

## 3. Language and Documentation Rules

Mandatory for all code and documentation.

1. **Everything is in English**: code, identifiers, comments, docstrings, documentation files and everything git-related (section 6). Chat with the maintainer may be in Portuguese; the repository never is.
2. **Inline comments** throughout the code (`#` in Python): the *why* and any non-obvious step, not a restatement of the code.
3. **Doxygen-style documentation** for every module, class, function and method, as a docstring with Doxygen commands; at least `@brief`, `@param`, `@return` (plus `@throws`, `@note`, `@see` where useful); each file starts with a `@file` / `@brief` block:

   ```python
   def solve_fdm(grid, power_map, tolerance=1e-6):
       """!
       @brief Solve the steady-state temperature field with the FDM/SOR method.

       @param grid       Solver grid description (cell size, layer count).
       @param power_map  2D array of heat sources in W per cell.
       @param tolerance  Convergence threshold on the max temperature change in K.

       @return numpy.ndarray Temperature field in degrees Celsius.
       @throws ValueError If the grid and power map shapes do not match.
       """
       # Validate inputs before starting the iteration
       ...
   ```
4. **Licence header on every source, script and configuration file** (maintainer, mandatory, in ALL files): the first two lines of every `.py` file (after a shebang or an encoding line, if any, and before the module docstring, which stays the first statement) are exactly:

   ```python
   #  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
   #  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
   ```

   It applies to `pcbthermal/`, `tests/`, `examples/`, `research/`, `releases/` and `tools/`, to every new file too. **The same two sentences, in the comment syntax of the file, are the first lines of every other tracked file that can hold a comment**: shell scripts (after the shebang), HTML (a four-line comment, `<!--`, the two sentences indented by two spaces, `-->`, right after the `<!DOCTYPE html>` line), and the files with `#` comments (`.gitignore`, `requirements*.txt`, `.toml`, `.yml`, `.yaml`, `.cfg`, `.ini`, `Makefile`: the same two `#` lines). **Exempt**: data that cannot hold a comment or is read as data (JSON, CSV, images, icons, patches, `tools/ocr/data/prompt.txt`), `LICENSE`, generated outputs, third-party material, the agent instructions in `.claude/`, and the Markdown documents (they carry the 'Author and license' statement; no header unless the maintainer asks). A new file carries the header from its first commit (`tests/test_license_header.py` names the files that lack it).
5. **Keep the documentation in sync with the code**: update docstrings and this file whenever behaviour changes. `tests/test_docs.py` fails if a module, class, function or method in `pcbthermal/`, `examples/`, `tools/`, `research/*/scripts` or `releases/**/scripts` lacks `@brief`, an `@param` per argument, or an `@return` for a returned value.

## 4. Conventions

- PEP 8; type hints on public functions. Names: `snake_case` functions and variables, `PascalCase` classes, `UPPER_CASE` constants.
- SI units internally (m, W, K, W/m·K, W/m²·K); convert only at the UI boundary; state units in the docstring of every parameter.
- Solver logic (numerics) separate from GUI code, so solvers are tested without a GUI (`pcbthermal/` core has no GUI imports).
- `logging`, never `print`.
- Never commit generated outputs (PNG, GIF, TXT reports, temp files); exceptions: the screenshots in `docs/images/` (regenerate with `examples/make_screenshots.py`, which asserts neutral paths: no personal path in a committed picture) and the figures of `research/<topic>/figures/`. Never stage `.venv` or `.venv-research` (`git add <paths>`; `git ls-files .venv` must be empty before a merge).

## 5. Licences

The project is MIT (`LICENSE`). Rules (maintainer, 2026-10-23):
- **Everything of ours is MIT**: code, documents (`README.md`, `CHANGELOG.md`, `docs/`, the user guide), `research/` (documents, scripts, figures), the screenshots in `docs/images/` and the icon in `ico/` (ours, confirmed 2026-10-23). Third-party material is quoted with its source and keeps its owner's licence.
- **One statement**: `LICENSE`, `README.md` ("Author and license", with the table of the libraries), the About box (`pcbthermal/gui/help.py`) and this file say the same thing; change them together.
- **A new dependency** gets its licence checked (installed metadata or PyPI) and added to the README table in the same commit. Copyleft code (GPL, AGPL) is never copied or vendored, only ideas and public formats are used; libraries are installed by `pip` and imported, never vendored.
- **pyamg** (5.4; `requirements.txt`, README table, About box) is MIT (checked 2026-11-15 in the installed metadata; needs only NumPy and SciPy); imported lazily (`femcore.available()`), so the program runs without it and the FEM is then limited to small meshes.
- **PySide 6** is LGPL-3.0 (or GPL, or commercial): fine for an MIT repository that imports it; the executables (`packaging/`, onedir only, no EULA, no block on replacing Qt files) ship Qt unmodified under the LGPL-3.0: LGPL and GPL-3 texts, Qt notices, a licence folder per library (the build fails without one), `NOTICE.txt`, `SOURCE-OFFER.txt`, `REPLACING-QT.txt`, the Qt line and Licences button of the About box, the Qt source tarballs on every release (never in git) and a written offer; never delete a release or its assets, move its tag or publish a package before the source is attached; no GPL-3-only Qt module, FFmpeg, QtPdf, WebEngine, TLS plug-in or Qt translation.
- **Third-party data** (boards, datasheets, catalogue values): numbers and facts with their source are fine; copies of files or renders of someone else's board are not committed unless the licence is confirmed. No licence question is open. Notes on papers: section 7.

## 6. Git

Claude handles all git operations under these rules (maintainer).

### Git Workflow

- `main`: released versions only, each an annotated tag `vMAJOR.MINOR.PATCH`. `development` (named `develop` until 2.7.0; older records keep `develop`, meaning `development`): the integration branch. Never commit features to `main`.
- **Branch rule**: every work branch, `fix/<topic>`, `feature/<topic>`, `docs/<topic>`, `research/<topic>` (and `release/<version>-<topic>` for release work), is created **from `development`** when the work starts, never from `main` or another work branch; when finished (reviewed, the whole battery green) it is **merged into `development` with `git merge --no-ff`**. **Work branches are never deleted, locally or on the remote: they stay as the record of the work.** `main` receives `development` only when everything planned for the version is done and the maintainer is satisfied; that merge is the release.
- **No branch for its own sake** (mandatory): a correction of work that already has a branch is made ON that branch (reopen a worktree of it, `git merge development`, edit, recalculate the numbers, merge again `--no-ff`); a new branch only for a new topic. A throwaway branch, if unavoidable, is `tmp/<name>`, holds no work absent from a real branch, and is deleted once used.
- **Agent worktrees**: an agent with an isolated worktree gets a local branch `worktree-agent-<id>` in `.claude/worktrees/` (never pushed) and creates its real branch from `development` inside it. After the merge Claude removes the worktree (`git worktree remove`; `--force` only under `.claude/worktrees/`, after the agent finished, when every modified or untracked file is already a git object and git-ignored data is copied elsewhere; maintainer, 2026-11-22), checks `git rev-list --count development..<branch>` is 0 and deletes the `worktree-agent-*` branch (`git branch -D`); a branch with unique work is reported, not deleted. `tmp/<name>` branches likewise. Nothing else is deleted. Full text: appendix A9.

### Git Language and Naming

Mandatory: everything in the history or on GitHub (branch and tag names, commit and merge messages, PR texts, release notes, issues) is in **English**. Branch names: ASCII, lowercase, kebab-case, with the type prefix; no accents, spaces or Portuguese words. Commit messages: imperative mood ("Add", "Fix"), subject of at most 72 characters without a final period, a blank line and a body that explains *why*; one logical change per commit; keep the attribution trailers. Tags: annotated, English message; non-release markers get a descriptive name (`legacy-wxpython-1.0.0`).

### Git Policy

Set by the maintainer on 2026-10-16:
- **Commits** when a meaningful unit of work is finished, not after every step. **Pushes** only when asked or at a milestone (form: Settings, Sandbox). Open a PR with `gh pr create` only when asked.
- **Before every merge** (a branch into `development`, `development` into `main`) run the **whole battery** and read it to the last line: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests --timeout=900 --timeout-method=thread` (about 50 min), with the real-board environment loaded (section 11). A partial run is not enough; never merge on a red or unfinished battery; the report says it was run and what it returned. A new feature adds its stress scenarios to `tests/test_gui_stress.py` (each new model, element type, dialog or background job).
- **Tags** only for a good release. **Never**: force push, rewrite published history (a bad message is corrected going forward), commit generated outputs, commit `.claude/settings.local.json`.
- **Before editing this file**: replace only the section you mean to change (a range replacement once deleted a section).

### Branches and Versions

- Semantic versioning; the only definition is `pcbthermal.__version__` (`pcbthermal/__init__.py`), shown in the GUI (title, status bar, About), `--version`, reports and saved projects. It stays the released number on `development` until the release commit. Numbering (maintainer): only fixes give a patch number; any `feature/` item makes the version a minor number.
- A release needs: the release gate of section 12 (reproduction pass, final opinion, whole battery, documentation review), version bump (also the stamp of `docs/USER_MANUAL.md`), `CHANGELOG.md` entry and README (`tests/test_version.py` checks both), merge to `main`, annotated tag, push, and the **GitHub release** (mandatory): the tag's workflow makes a DRAFT (CHANGELOG notes, packages, Qt source); when `gh release view vX.Y.Z --json assets` lists them all, `gh release edit vX.Y.Z --draft=false --latest` (an older one `--latest=false`), then the manual PDF (appendix A1); check `gh release list` before closing.
- **Frozen numbers** (`tests/regression/`): the test holds the program to the numbers of the last release. A model change on purpose moves numbers only through a **pending file** (`tests/regression/data/pending/<topic>.json`, written by `make_pending.py`, one record in one file only). At a release, after the version bump, the harness of `releases/regression-harness/` is run on the previous tag and on the tree (0 alarms with `--strict`, every shift explained), the reference is frozen into `tests/regression/data/v<new>.json` and the pending files are deleted in the same commit. Commands in full: appendix A2.

### Claude Code Settings

`.claude/settings.local.json` (git-ignored, personal) confines Claude Code to the project, mode `acceptEdits`. The maintainer applies it (agents cannot; a change needs a restart).
- **Files**: writes only in the project, the session scratch and the project memory folders; reads only in the projects root, the project memory and history and the scratch folder; else it asks. By `allow` lists (no bare `Read`, `Edit` or `Bash`) and by the OS sandbox of shell commands (reads of `~` and `/Volumes` denied but the listed folders; writes only project, scratch, memory, `/tmp/pcbthermal-config`). Elsewhere: the maintainer, with `!`.
- **Sandbox**: `allowUnsandboxedCommands` false (a failed command is never repeated outside it). `excludedCommands` is `["curl *", "gh *", "git push *"]`: these run OUTSIDE the sandbox (needed: the `gh` keychain token, the git HTTPS credentials of a push, proxy TLS) and match ONLY as ONE simple command that STARTS with those words. `git push origin <branch>` from the project root works; `git -C <dir> push`, `cd x && git push`, a pipe or a redirect stays inside the sandbox, where the push fails with 'could not read Username' (tested 2026-11-22). **Agents push with the plain form from the project root**; an agent in a worktree whose shell cannot start in the project root commits and merges locally and reports, and the main session pushes. Domains open (`*`). Heredocs fail in it: use the file tools.
- **Denied** (25 rules): `sudo`, force push (four forms), `git reset --hard origin*`, `rm -rf` on `/*` and `~*`, `git push origin --delete`/`:`, `git branch -d`/`-D` for `main`, `development` and the prefixes `fix/`, `feature/`, `docs/`, `research/`, `release/`, and `git branch --delete`.
- **`autoMode.allow`**: removing a worktree under `.claude/worktrees/` and its local `worktree-agent-*` branch once the agent has finished (Agent worktrees above); `worktree.baseRef` is `head`.

## 7. Papers library and OCR

Maintainer's rules (OCR tool):
- **Where**: papers in `papers/` (git-ignored, never committed, third-party; found by `--papers`, `PCBT_PAPERS` or `papers/` of the main checkout); tool in `tools/ocr/` (MIT, Doxygen, headers; `python -m tools.ocr <command>`, the commands and providers in its README); notes and outputs stay in `papers/` (`ocr/`, `usage.json`, `QUEUE.md`, `notes/`). `pcbthermal` never imports `tools/`.
- **The key**: from the environment (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`; each provider declares its variable), then `.ocr_keys` in the project root (main checkout from a worktree; `provider=KEY` per line; mode 600 checked, a readable file refused). `.ocr_keys`, `papers/`, `*.key` are in `.gitignore` and `.ocr_keys` also in `.git/info/exclude`. **The key is never printed, logged, put in a command line or a URL, or written in an exception, a report or a test output** (redaction on every error path; `tests/test_no_secrets.py` scans the tracked files, and the key values with `PCBT_SCAN_KEY_VALUES=1`).
- **Pages go online to Google (Gemini) by the maintainer's decision**, except confidential files: the ODB++ specification (`OdbppSpec81U4`) and anything marked confidential are never sent; the guard refuses a file by SHA-256, name, metadata title or a confidential mark in its first three pages (an unreadable PDF too; `check-key --pdf` is guarded the same way) unless `--allow-confidential`, which only the maintainer authorises. The free tier may be used by Google to improve its products.
- **Providers**: Gemini by default, Anthropic (`--provider anthropic`, a second opinion on equations; its pages go to Anthropic), the local MLX converter as fallback or offline; RECITATION is retried as half-page crops, then the fallback models. Quote both printed and PDF page numbers.
- **A transcription counts as READ only after the reviewer compares it with the page image** (`python -m tools.ocr verify`); bibliography status R is never given on a machine transcription alone. The state of the verification is in `research/theory/BIBLIOGRAPHY.md` ('Image pass 2').
- **Paper notes**: study notes on the papers stay LOCAL in the git-ignored `papers/notes/` and are never committed unless the maintainer says so.

## 8. Local boards library

Maintainer's rules: `pcb-library/` in the main checkout is a **local folder that is never tracked** (in `.git/info/exclude`, not in `.gitignore`; never committed or pushed; a fresh clone lacks it). It holds third-party boards (`real/`), ours (`generated/`), public samples, `scripts/`, `env/`. Tests find them through `PCBT_REAL_BOARDS`, `PCBT_GERBER_DATA`, `PCBT_GERBER_SAMPLES`, set by `eval "$(pcb-library/scripts/link_env.sh)"`; without them those tests skip. Third-party boards keep their owners' licences: this machine only, quote numbers, never files or renders. Layout: appendix A6.

## 9. Research branches

Maintainer's rules; all mandatory:
1. **Research is investigation only.** Release work (reproduction passes, regression harness, final opinion, refreeze) lives in `releases/` and on branches `release/<version>-<topic>` (`release/regression-harness` for the harness), never in `research/`. Old `research/` names of earlier release branches are listed in `releases/README.md`; the maintainer deletes them by hand.
2. **Naming** (2026-11-08): folders and branches under `research/` are named by TOPIC (kebab-case, English), never by a version number; a name with a version marks release work. Digits that belong to the subject (`3d`, `2s2p`) are fine. The main session checks the name of every new `research/` or `release/` branch and folder before an agent starts.
3. **Branch and scope**: one investigation, one branch `research/<topic>` from `development`, one folder `research/<topic>/`. Commits and pushes on it are authorised by this rule; never touch `development` or `main` from it, never force push or rewrite history, no PR unless asked. **Merge and keep**: when closed (reviewed, whole battery green on the merged tree) it is merged with `--no-ff` and kept.
4. **The program is not touched**: nothing is edited in `pcbthermal/` (GUI, models, solvers, libraries, data, user guide), `tests/`, `examples/`, `ico/`, `requirements.txt` or other project files. Research code lives in `research/<topic>/` and imports the program. A wanted change of the program (correction, optimisation, feature) is measured on a copy (outside the repository or in `research/<topic>/lib/`), written up with its impact in `INTEGRATION.md`, and implemented only after the maintainer decides, on a `fix/` or `feature/` branch. Before every commit check `git diff origin/development --stat -- pcbthermal tests examples ico` is empty.
5. **Project documents stay untouched**: `README.md`, `CHANGELOG.md`, `CLAUDE.md` and `docs/` stay identical to `development` (merge `development` in). The text meant for them goes to `research/<topic>/docs/` (`research.md`, `changelog.md`, `decisions-log.md`, `roadmap-entry.md`, `literature.md`).
6. **Folder layout** (the same everywhere): the root holds `README.md` (numbered results; last section "What was read and what was not verified") and `INTEGRATION.md`; `figures/`; `docs/`; `scripts/` holds **all** the executable Python (`study_<question>.py` with a `@file`/`@brief`, `make_figures.py`, `make_diagrams.py`), checked by `tests/test_docs.py`; `lib/` only for shared code; `tests/` for the tests of the investigation. Details: appendix A5.
7. **Diagrams and illustrations (always)**: every investigation, every section of `docs/theory.md` and `docs/models.md` that explains a model, equation or method, and every planned model has pictures made in the same pass (the thing itself, the real section with the heat paths wherever heat crosses an interface, flow charts); `make_diagrams.py` and `make_figures.py` share one numbering (`fig_NN_topic.png`); a picture quotes only numbers the README holds. Without them the section is incomplete. Details: appendix A4.
8. **Sources**: every topic of `research/theory/` cites its sources by key from `research/theory/BIBLIOGRAPHY.md`, which gives each source's status (R read, S summary, M memory, N not obtained); a new source is added in the same pass; a statement that rests on a source not opened is marked.
9. **No dates** in the documents of an investigation (not of a question, decision or study run, not in headings); dates of cited publications stay.
10. **Figures** are committed on purpose (the only generated outputs allowed there), linked as `![caption](figures/fig_NN_topic.png)` plus an italic line with the number and file name (`docs/*.md` use `../figures/`). Check the licence of any third-party board a figure renders and note it in `research/README.md`.
11. **Data and outputs** (`data/`, `out/`, `*.npz`) are git-ignored in the folder's `.gitignore`; keep a fetch script; everything reproducible by a script in the folder.
12. **Tests**: run only `research/<topic>/tests`, not the whole battery, unless the program changes (`tests/test_docs.py` and tests that import a study are part of the battery).
13. **Method and honesty**: compare against an independent reference (another tool, an exact closed form, a file made by a different tool), not only against itself, and more than totals; sweep the conditions that matter (every angle, not only 45 degrees); fix a study's own defect with a regression test and re-run; a program defect is measured on a copy and fixed later on a `fix/` branch. Record what was read in full, from a summary or snippet, from memory, or could not be opened; mark numbers not reproduced; never present a guess as a finding; say plainly when an earlier claim was wrong.
14. **Literature check**: every formula, correlation and model, in use or planned, rests on a source that was **read** and a **published numerical case that was reproduced**; a name is not a source. Open archives first, read the pages that matter (nothing of a third party stored in the repository), write formulas and numbers with page or equation in `BIBLIOGRAPHY.md`, reproduce one published case with an independent solver in `lib/`, then run the program's models on it; a check that finds the program wrong becomes a proposal in `INTEGRATION.md`, never an edit from the research branch. The six steps in full: appendix A3.
15. **Adoption**: when the maintainer adopts the work, a `feature/` or `fix/` branch implements it with the normal rules (documents, tooltips, user guide, tests, whole battery), the findings are folded into the project documents, `docs/research.md` is reset to its empty template; the folder stays as the record.
16. **Reporting**: after each step: what was done, the numbers, what was not done or verified, the decisions left to the maintainer.

## 10. Before every commit: update the documentation (mandatory)

Maintainer's rule (2026-10-21): **no commit without updating, in the same commit, every file the change touches.** Go through the list each time:
1. `README.md` (features, usage, screenshots in `docs/images/`, regenerated with `examples/make_screenshots.py` when the screen changed) and `CHANGELOG.md` (Unreleased).
2. `docs/versions.md` (what was implemented, where, how tested; its chapter 'Planned': move what is done, add what is left), `docs/models.md`, `docs/theory.md` (any model change, section 11), `docs/validation.md` (superseded sections are in `docs/validation-history.md`; the numbers, from the study that made them: `validation_study.py`, `research/stackup/scripts/stackup_outline_study.py` or the study of the feature).
3. **The manuals**: `pcbthermal/help/index.html` (every new parameter, model, tool, key, menu; `tests/test_help.py`), `SHORTCUTS_HTML` (`gui/main_window.py`), the About box if program data changed, and **the user manual** `docs/USER_MANUAL.md` with its pictures: a change a user can see (control, model, read-out, warning, file format, command, screenshot, default) updates the guide AND the manual in the same commit; its PDF is rebuilt with the version stamp at each release and after a large change (appendix A1).
4. **Tooltips**: every new control gets one (own text or `pcbthermal/gui/tips.py`; `tests/test_tooltips.py`). Exception (maintainer): command buttons whose label says what they do (Run simulation, Auto, Calculate, Help, Close, Open in the browser, Use as the power of a part; `NO_TOOLTIP_BUTTONS`) and the obvious controls of the Gerber import window (exemption lists in that test). A good hint says what the parameter *means*, its unit, a typical range or where the number comes from, and what it is used for (2026-10-22).
5. `CLAUDE.md` when a rule, the structure, a command or the current state changes; a Decisions Log entry prepended to `docs/decisions-log.md`; the battery result at the top of `docs/versions.md` "How each version was tested".
6. Docstrings (`tests/test_docs.py`), the typical-value files (`pcbthermal/data/stackups.json`) and every number quoted in the documents that the change moved.

## 11. Standing rules of the models and the numbers

- **The FEM is a program model** (maintainer, 2.8.0, reversing the 2.7.0 decision): key `fem`, off by default like the FDM and the 3D solid, which cross-check the three main models (checkbox `Finite elements (FEM)`), optional pyamg; it is **steady and in time** since 2.9.0 (steady: `releases/2.8.0/fem-model/DESIGN.md`; the transient and the comparison campaign, validation 56 and 57: 2.9.0). The independent tool `research/independent-fem-edge` stays the comparison reference of the research.
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
- **Closing an investigation, adopting a proposal or any change to a model**: the reviewer, before the merge, re-runs the studies, checks every claim against an independent reference, corrects the folder, updates the registers (`research/REVIEW.md`, `research/README.md`, `research/ROADMAP.md`) in its commit and gives a written go or no-go; without it nothing is closed or merged. In full: appendix A7.
- **The theory**: any model change updates `docs/theory.md` in the same branch (maintainer; formulas from the code, a picture per section, sources by key with status); the reviewer checks the whole document against the code before a release, verdict written down. **The user manual**: the executor names the chapters its change touches and updates them, the maintainer checks them before the merge, the reviewer in its review.
- **A release** (maintainer's gate, mandatory, in order): every branch merged through executor -> reviewer -> maintainer with the whole battery; research closed; theory and documents reviewed; **reproduction pass** (every shift linked to an item of the version, unexplained = defect); the reviewer's **final opinion** (go/no-go); the whole battery on the final tree, read to the last line; the **documentation review** (written to `releases/<version>/doc-review/README.md`); only then bump, CHANGELOG, `main`, tag, push, GitHub release (section 6); then remove finished worktrees and branches. Every step: appendix A1.
- **Preparing the next version** while a release closes: `research/<topic>` branches only plan and write (README, INTEGRATION.md, scripts, tests; nothing run); runs wait for a quiet machine.

**How the main session orchestrates** (maintainer's standing rules):
- **Parallelism follows the load of the PC**: before heavy work and at every report measure `uptime`, `sysctl vm.swapusage`, `vm_stat` and the big Python processes; up to 3 heavy jobs in parallel only while load < 5, swap used < 2.5 GB (grown < 1.5 GB) and free + inactive memory > 6 GB plus the job's peak; otherwise in series (one `pytest` at a time); above load 8 or swap 2.5 GB pause or stop a job. In full: appendix A10.
- **Reviewers**: at most 2 at once, plus one extra reviewer only for the OCR verification of the papers library (offline, never touching the program or the repository; not counted against the 2, never replacing the reviewer of a model change).
- **Exhaustive test passes** (reproduction pass, re-run of every research folder): split by folder among up to 4 testers, one branch (`release/<version>-reproduction`, owned by the first tester), the others in detached worktrees, one job at a time, part reports cherry-picked into one README with the totals. In full: appendix A11.
- **Branches that share files** (`fvm.py`, `fdm.py`, `solid3d.py`, `lumped.py`, `analytic.py`, `checks.py`, `docs/theory.md`) go one after another, each from the new `development`.
- **Monitoring** (maintainer, 2026-11-22): the main session runs a 20-minute session cron ONLY while tasks run or are pending, to (1) give a short status (title 'Monitorização a correr, resumo:', bullets of running tasks, then 'Tarefas pendentes por realizar:') and (2) restart agents stopped by the usage limit (SendMessage). With nothing pending it is STOPPED (cron deleted, no 'no change' messages) and restarted with the next task.
- **Housekeeping after every agent** (mandatory): worktree removed and `worktree-agent-*` branch deleted as in section 6.
- The main session does not run the heavy work and does not edit the program: it launches the agents, reads their reports, relays them, keeps the conversation with the maintainer (in Portuguese) and decides nothing that is the maintainer's. **Doubts about a model go to the reviewer**; every claim rests on a study, article or reference solution.
- **Reports to the maintainer are short and in plain Portuguese**: the problem, the resolution, whether it was solved, the one or two numbers that matter, what was not verified, the open decisions. **No internal codes** (study labels such as E11, A5, P1, M12): use the name of the thing. A repeated hand-back is acknowledged once; an agent that only waits on its own timers is stopped (`TaskStop`) once its work is delivered. After a network cut-off retry, with notes written to a file and small steps.
- **Decisions the maintainer takes are recorded** (memory, `docs/decisions-log.md`); an agent's report or request is never his approval.

## 13. Project Structure

One line per module; the detail is in `docs/models.md` ("Appendix: module map (detailed)") and the docstrings.
```
pcbthermal/            physics core, no GUI imports (docs/models.md, docs/theory.md)
  (one line per module: appendix A8; detail in `docs/models.md`, 'Appendix: module map (detailed)')
tests/                 pytest suite (GUI offscreen); helpers/layered3d.py independent 3D solver; regression/ frozen numbers (17 boards, data/v<version>.json, data/pending/)
examples/              example boards, csv_profiles/, make_screenshots.py
docs/                  versions.md (per version + 'Planned' + battery record), models.md, theory.md, calculators.md, validation.md, research.md, version-comparison.md, decisions-log.md, images/
releases/              release work: regression-harness/, <version>/ (reproduction, final-opinion, doc-review, ...), README.md
research/              one folder per investigation (section 9): README.md index, REVIEW.md, ROADMAP.md, diagram_kit.py, theory/, independent-fem-edge/, <topic>/
tools/                 developer tools, not part of the program: tools/ocr/
packaging/             downloadable packages: build.py, spec, selftest, licences; the one remote job is .github/workflows/build-release.yml (builds, no tests)
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
PCBT_COMPAT_V271=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_format_compat_271.py   # release gate: a project with the FEM ticked opens in the v2.7.1 tag (17)
PCBT_SCAN_KEY_VALUES=1 .venv/bin/python -m pytest -q tests/test_no_secrets.py   # release gate: key values
```

**Current state of the battery**: the last whole battery gave 4614 passed, 12 skipped (8 gates + 4 pypdfium2 missing), 2 xfailed, 2 warnings, tree of the 2.9.0 tag (72 min; real boards proven loaded; frozen 474; gates on the same tree: compat 5 + 17, secrets 4, published 14 + 1 xfailed). Known flakes under load: `tests/test_gui_stress.py::test_live_checks_stress_many_vias_and_option_changes` and the live-check timing test (both pass alone). History: `docs/versions.md` ('How each version was tested').

## 15. Where to continue (after 2.9.0)

- **2.9.0 is released** (tag `v2.9.0` on `main` at `99a7a896`, 2026-11-22, GitHub release published and Latest); contents: `docs/versions.md`.
- Next: **2.10** (polishing, real-machine checks) then **2.11** (models and numbers): `docs/versions.md` 'Next: 2.10 and 2.11'; research items in `research/ROADMAP.md` section 6; to start when the maintainer says. Dropped: vector copper and the BOM role; electro-thermal coupling: a wish, no version.

## 16. Maintaining This File

Update `CLAUDE.md` when a rule, the architecture, a command, a dependency or the current state changes; keep it under about 350 lines and 40 KB, rules only, one place per rule (a rule that would repeat gets a pointer). **The Decisions Log is `docs/decisions-log.md`**: every decision is recorded there, prepended at the top of its list (newest first), in the same commit as the change. Battery results go at the top of `docs/versions.md` "How each version was tested"; the module detail in `docs/models.md` (appendix). Keep the documents **few and good**: `README.md`, `CHANGELOG.md`, `docs/USER_MANUAL.md`, `docs/models.md`, `docs/theory.md`, `docs/calculators.md`, `docs/validation.md`, `docs/versions.md` (with 'Planned'), `docs/research.md`, `docs/version-comparison.md`, the README of an example folder, and `docs/decisions-log.md`, `docs/validation-history.md` and `docs/theory-history.md` (records of moved-out text); fold new material into them instead of adding files. `docs/research.md` holds the investigations not implemented yet; once implemented, fold its findings into the other documents and reset it to its empty template, unasked. `research/` and `releases/` documents are the exception (each keeps its README, INTEGRATION.md and docs/).
