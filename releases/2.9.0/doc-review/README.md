# Documentation review of 2.9.0

Release gate step 6b of `releases/2.9.0/PLAN.md` section 5 (`CLAUDE.md` section 12). Tree: `development` b241b15e (feature-complete; `pcbthermal.__version__` still 2.8.0 until the release commit). Branch `docs/release-2.9.0-doc-review`. Reviewer: the project reviewer agent. Only light runs were made (the screenshot script, the document tests); the machine load stayed between 2.3 and 2.9.

**Verdict**: the documents are ready for the version bump once the items of section 4 are done in the release commit. Three findings were wrong numbers or wrong claims that a reader would act on (sections 2.1 to 2.3); they are corrected. Two items are left to the maintainer (section 5).

## 1. What was checked

| Item | How | Result |
| :-- | :-- | :-- |
| README features list against 2.9.0 | read line by line against the merges since `v2.8.0` (26 branches) and the CHANGELOG | four corrections (2.1, 2.4) |
| README pictures | every one of the 27 README pictures looked at; a crop of the status bar of all 121 pictures of `docs/images` read for the version | 5 window pictures still said v2.7.1, 2 surface pictures were older than the surface columns; regenerated (2.5) |
| `pcbthermal/help` picture copies | `tests/test_help.py` (byte-equal twins) and a `cmp` of every copy | equal after the regeneration |
| Tests badge | `README.md` line 6 against `CLAUDE.md` 14 | 4555 passed in both; `tests/test_version.py` passes |
| Author and license, library table | read against `requirements.txt`, `requirements-docs.txt` and the About box | complete (NumPy, SciPy, pyamg, Matplotlib, PySide 6, PyInstaller, pytest set, reportlab, pypdfium2); no change |
| Download section, Qt source offer | read against `packaging/build.py` (the text of `SOURCE-OFFER.txt`), `packaging/release_notes.py`, `pcbthermal/bundle_info.py` and the About box | the README sentence said the source is on the Qt Project servers; corrected (2.4); `SOURCE-OFFER.txt`, the release notes and the About box already say the tarballs are attached to the release; glibc 2.35 and the macOS Open Anyway steps present; no licence obligation removed |
| User guide `pcbthermal/help/index.html` and calculator help | `tests/test_help.py`; the 2.9.0 words searched (Difference to, Export statistics, Crank-Nicolson, FEM in time, the new warnings, capacity inventory, Summary table setting, the reference model line) | all present; one wrong picture caption and one stale number (2.3, 2.5) |
| Tooltips | `tests/test_tooltips.py`; the FEM tooltip read | one stale number (2.3) |
| `SHORTCUTS_HTML` | the diff of `pcbthermal/gui` since `v2.8.0` searched for new shortcuts | none added in 2.9.0; nothing to change |
| About box | `pcbthermal/gui/help.py`, `bundle_info.qt_sentence` | program data, Qt line and Licences button current; no change |
| User manual `docs/USER_MANUAL.md` | chapters 1 to 14 and appendix A numbered in order, figures 1 to 39 numbered in order and every image file present, dotted references point at existing sections; version stamp line 3 | two corrections (2.3, 2.5); the stamp stays 2.8.0 until the release commit (section 4) |
| CHANGELOG Unreleased | every 2.9.0 merge has an entry | two `### Added` headings merged into one; one stale sentence (2.4) |
| `docs/versions.md` | Unreleased chapter against the merges; 'Planned' | 'Planned: 2.9.0' still described the scope as in progress; replaced by the list of what the plan leaves for later (2.6) |
| `docs/models.md`, `docs/theory.md` | the 2.9.0 sections present: surface read-out 1.2c to 1.2e with figure 55, the FEM in time 4b, the default stepping 2.4, the copper slabs (figure 4b) and the pad `K_PAD_INPLANE` of the 3D solid in section 4 | present with formulas, source keys and pictures; one stale number in models.md (2.3); units normalised |
| `docs/validation.md` 56 and 57 | present; each names its tree (7886ac42 and its commits) and its references; the solvers of the tree were compared with b241b15e | `git diff 7886ac42 b241b15e -- pcbthermal/{fvm,fdm,fem,femcore,femmesh,solid3d,lumped,analytic,laminate,thickness}.py` changes only the copper-spread warning constant of `analytic.py` (no number), so the campaign numbers hold for the shipped tree |
| `docs/research.md` | read | the empty template |
| `research/README.md`, `REVIEW.md`, `ROADMAP.md` | every folder of `research/` is in the README index and the review register; the 2.9.0 rows read | two stale statuses corrected (2.7) |
| `releases/2.9.0/PLAN.md` | every row of 1.1 | the rows without a status have one now, with the list of what is not in 2.9.0 (2.6) |
| `docs/decisions-log.md` | the decisions of the 2.9.0 branches (FEM transient, campaign, Difference view, default stepping, surface models, copper slabs, pad, thin-copper source, exports, Models tab, summary setting, reference model, licences window, packages, icon, manual, badges, light screenshots, 3.0.0 revert) | all recorded; this review adds one entry |
| Read-out names (`CLAUDE.md` 11) | the window pictures and the guide read | maps, tables, cards and the Summary name their read-out; three status texts do not (section 5) |
| Units (µm, °C) | `um` and `degC` searched in the user documents | README, the 2.9.0 CHANGELOG entries, validation 56 and 57, theory.md and models.md corrected (2.8); the older history keeps its text |
| No dates in research documents | the 2.9.0 research folders and the three registers searched for dates | none |
| Document tests | `test_docs`, `test_help`, `test_license_header`, `test_no_fabricator_names`, `test_shortcuts`, `test_third_party_text`, `test_tooltips`, `test_typography`, `test_user_manual`, `test_version`, plus `test_fem_gui` | 976 passed before the changes, all pass after them (`test_fem_gui` 15 passed with the new tooltip assertion) |

## 2. What was corrected (commits on `docs/release-2.9.0-doc-review`)

### 2.1 The FEM agreement with the FVM (commit `bfee72ee`)

README, guide (section 9), manual (7.8), `docs/models.md` and the FEM tooltip (`gui/panels.py`) said the FEM reads **0.4 to 0.9 % below the FVM** on plain boards. That is a 2.8.0 number at a 2 mm cell, measured before the thin-copper source correction of 2.9.0; no script of 2.9.0 prints it. The comparison campaign prints, on its 14 plain boards at a 1 mm cell (hottest column, `releases/2.9.0/fem-campaign/tables/c1_steady_all_models.md`, 'without the drawn and the pad boards'): FVM -0.3 to +1.4 % of the FEM rise (0.60 % mean), 3D solid +0.1 to +2.2 %; at 2 mm on the example board the FVM is +2.8 %, so the old range does not hold at 2 mm either. The texts now quote the campaign; `tests/test_fem_gui.py` asserts the new number. The earlier claim was wrong for 2.9.0.

### 2.2 The campaign numbers were said to come from program 2.8.0 (commit `bfee72ee`)

The manual (7.1) and the guide ('How far each model is from the finite elements') said 'program 2.8.0'. The campaign ran on the 2.9.0 development tree 7886ac42 (its version string was still 2.8.0); they now say 'the models of 2.9.0, measured on its development tree'.

### 2.3 Pictures (commit `b7e728ef`)

* Regenerated with `examples/make_screenshots.py` in the light theme, one mode at a time (default, `--import`, `--views`, `--surface`, `--fem`; `--difference` and `--manual` were run and gave byte-equal files), each new picture looked at: `editor_imported`, `editor_imported_dark`, `editor_warnings`, `editor_overlay`, `editor_background` (said v2.7.1), `preferences_solver_gerber`, `import_step1`, `results_summary_imported`, `results_temperature_imported` (and `_dark`), `results_gradient`, `results_terrain`, `results_views` (and `_dark`), `outline_temperature`, `results_temperature`, `results_summary`, `stackup`, `stackup_inner_copper` (a few pixels of layout), `results_surface`, `results_surface_table` (the zone and hotspot tables had no surface column), `results_fem_surface`. The copies in `pcbthermal/help` are byte-equal.
* The warnings picture now shows 7 warnings: the README and the manual (figure 27) said 'Warnings (8)'; corrected. The guide caption of the same picture said 'a second source that lies half outside the board'; the picture shows the RP2040 board with a second source on the board; corrected.

### 2.4 README and CHANGELOG (commit `073e2d12`)

* README: the platform line called the packaging branch 'not yet merged' (merged in 2.9.0); the models bullet now says which three models are off by default and that the FEM also runs in time; the live checks list the three warnings of 2.9.0 (a part with a corner on bare laminate, the LPTN over varying copper, the FEM profile stretch); the animation bullet names the new default stepping; the source-offer sentence said the Qt source is on the Qt Project servers, it now says the tarballs are attached to the release page (as `SOURCE-OFFER.txt` already says).
* CHANGELOG Unreleased: two `### Added` headings made one (no entry lost: the sorted lines differ only by the removed heading); the campaign-warnings entry said `checks.trust_hint` 'waits for `feature/compare-differences`', which is merged; it now says the function was not built and the Difference view carries its own verdict.

### 2.5 Plan, 'Planned' and registers (commit `073e2d12`)

* `releases/2.9.0/PLAN.md`: every row of 1.1 has a status (done, not in 2.9.0, open); the second `e42` row is renamed `e42b`; a paragraph after 1.2 lists what is not in 2.9.0.
* `docs/versions.md` 'Planned': the paragraph that described the 2.9.0 scope as work in progress is replaced by 'Planned: what the 2.9.0 plan leaves for later'; the capacity-inventory row says it is done for the FEM.
* `research/ROADMAP.md` A52 and A55, `research/README.md` and `research/REVIEW.md` (`surface-readout-models/`): the adopted work is recorded.

### 2.6 Units (commit `073e2d12`)

`um` -> `µm` and `degC` -> `°C` in the README, the 2.9.0 entries of the CHANGELOG, validation 56 and 57, `docs/theory.md` and `docs/models.md`.

## 3. Not in 2.9.0 (the explicit list)

Of the five extras only the drawn-L warning is in (e41). Not in 2.9.0, to 2.10 unless the maintainer says otherwise: the projection of slanted and curved outlines in the FEM (d), the FEM on imported Gerber copper (e6), the memory law against measured peaks (e7), the regeneration of `docs/version-comparison.md` (e15), the transient surface rule (e23), the step aligned with a wave edge (e29), the optional e31, e32, e42 and e43, the first sample after a power edge of the implicit-Euler profile run, the Portuguese manual (e37). **Open before the refreeze**: the two harness boards of e33. The same list is in `releases/2.9.0/PLAN.md` (after 1.2) and `docs/versions.md` 'Planned'.

## 4. At the version bump (the release commit), not before

1. `pcbthermal/__init__.py` 2.8.0 -> 2.9.0; README version badge (line 5); manual stamp `docs/USER_MANUAL.md` line 3 ('Program version 2.9.0'), its line 207 and the `--version` row (line 1686) ('PCB Thermal Lab 2.9.0'), and line 413 ('With version 2.9.0': the numbers of that table are unchanged, checked against the regenerated `results_summary.png`: 85.47 / 86.91 / 84.80 °C).
2. **CHANGELOG**: `## [Unreleased]` becomes `## [2.9.0] - <date>` with a '2.9.0 in short' paragraph (draft below) and a new empty `## [Unreleased]`; `packaging/release_notes.py 2.9.0` then takes that section.
3. **README 'Versions'**: a 2.9.0 line first (draft below); the 2.8.0 line keeps its text.
4. **`docs/versions.md`**: 'Summary of the current version (2.9.0, <date>)' rewritten; 'Unreleased (2.9.0 work in progress)' becomes '2.9.0 - <date>: ...'; the battery of the final tree at the top of 'How each version was tested'.
5. **Pictures**: every window picture shows the version in its status bar, so all are regenerated AFTER the bump, one mode at a time, each looked at, then copied to `pcbthermal/help` where a twin exists: `python examples/make_screenshots.py` (14 pictures), `--import <rp2040 folder>` (`pcb-library/real/rp2040/original`), `--views <rp2040 folder>`, `--surface`, `--fem`, `--difference`, `--manual`. The 32 pictures that carry the version: animation, animation_underlay, editor, editor_background, editor_imported, editor_imported_dark, editor_overlay, editor_warnings, manual_start, manual_window_tour, outline, outline_temperature, power_profile, results_components, results_difference, results_fem_surface, results_gradient, results_models, results_power_profile, results_profile_cut, results_summary, results_summary_imported, results_surface, results_surface_table, results_temperature, results_temperature_imported, results_temperature_imported_dark, results_terrain, results_views, results_views_dark, stackup, stackup_inner_copper. Check the warning count of `editor_warnings` against the captions (README line 49, manual figure 27: 'Warnings (7)').
6. **Numbers to refresh at the bump**: the Tests badge and `CLAUDE.md` 14 from the final whole battery; the refreeze record (`tests/regression/data/v2.9.0.json`, the pending files deleted); the manual PDF rebuilt with the 2.9.0 stamp and attached to the release.
7. **`CLAUDE.md` section 15** (prepared text, the file is 40 336 bytes, under the 40 960 limit if the section stays this size):

   > ## 15. Where to continue (after 2.9.0)
   >
   > - **2.9.0 is released** (tag `v2.9.0` at `<commit>`, GitHub release published and Latest, `<date>`): the FEM in time, the Difference view, the comparison campaign (validation 56 and 57), copper slabs in the 3D solid, the surface read-out in the Analytic and the 3D solid, the exports named by read-out, the default Crank-Nicolson stepping, the packages and the user manual.
   > - Next: **2.10**, from the list 'Planned: what the 2.9.0 plan leaves for later' of `docs/versions.md` (FEM outline projection, FEM on imported copper, the measured memory law, the version comparison, the transient surface rule, the aligned step, the optional FEM items) and the corrections the campaign proposes (`releases/2.9.0/fem-campaign/INTEGRATION.md`); to start when the maintainer says. Dropped: vector copper and the BOM role; electro-thermal coupling: a wish, no version.

**Draft, CHANGELOG '2.9.0 in short'**: a version of features and of comparison. The finite-element model runs in time (animation, step responses, power profiles); every model is put against it in a comparison campaign (validation 56 and 57, with the published NAFEMS T3 transient reproduced) and the Difference view of the Temperature tab draws one model minus another with a verdict from those measured ranges; the 3D solid gets copper slabs and the Analytic and the 3D solid a surface read-out; the exports name every temperature by its read-out; the animation steps in Crank-Nicolson with a damped start; three new warnings; the Models tab compares the parts in every model; a user manual, a new icon and downloadable packages. Corrections that move numbers on purpose: the power of a part enters the FEM through its face at every copper thickness, and the interface pad of a metal block in the 3D solid conducts across only (0.002 K on the frozen boards).

**Draft, README 'Versions' line**: `- **2.9.0** (<date>): the finite-element model in time (animation, step responses, power profiles), the Difference view with a verdict from the comparison campaign of every model against the FEM (validation 56 and 57), copper slabs in the 3D solid, the surface read-out in the Analytic and the 3D solid, the exports named by read-out, Crank-Nicolson as the default stepping of the animation, three new warnings, the Models tab part by part, the user manual and the downloadable packages; two corrections that move numbers on purpose (the FEM source of a part on an outer layer, the interface pad of the 3D solid).`

## 5. Left open, with who decides

1. **(Fixed on `fix/readout-names-status-lines`, merged before the bump: the three texts now say '(column)'.) Three status texts showed a temperature without its read-out name** (`CLAUDE.md` 11; a program change, so not made on this documents branch): the status line and the Simulation dock after a run, `Done: FVM, Tmax 85.5 °C, Rθ 10.99 K/W` (`gui/main_window.py` 1867; the map card beside it says '(column)'); the Animation summary `Steady Tmax ... °C` (`gui/animation.py` 210); the `transient` command line `steady Tmax ... °C` (`cli.py` 194). Proposal: append '(column)' as the Summary and the maps do, on a `fix/` branch with the screenshots regenerated; the maintainer decides whether it goes into 2.9.0 (then before the bump, because the pictures show the status line) or 2.10.
2. **(Done on `release/2.9.0-bump`, before the refreeze: `thick_copper_gap` and `top_block_pad`, see `releases/2.9.0/PLAN.md` e33.) e33, the two harness boards**: not done; either added in one commit before the refreeze or moved to 2.10 (maintainer).
3. **e42b, release-build items** (the real QtGui swap test per system, the SHA-256 of the Qt source tarballs in the repository, a build trial from `development`): the maintainer's.
4. **Housekeeping** (main session): the worktree `.claude/worktrees/ver-300` holds the branch `release/3.0.0-version-number` of the reverted renumbering; it has no commit that `development` lacks (`git rev-list --count development..release/3.0.0-version-number` is 0) but holds uncommitted edits of `CHANGELOG.md`, `CLAUDE.md`, `README.md` and more; the main session asks the maintainer before removing it.
5. **Not verified**: the manual PDF was not rebuilt (it is rebuilt with the 2.9.0 stamp at the release); the dark pictures were regenerated but only the light ones of the README were looked at in full; the whole battery was not run on this branch (the release battery runs on the final tree).
