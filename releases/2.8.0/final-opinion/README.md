# Final opinion of the reviewer on 2.8.0

Step 5 of the release gate (`CLAUDE.md` section 12; `releases/2.8.0/RELEASE_GATE.md` section 5). Tree reviewed: `development` at `b4ee3955` (it holds `release/2.8.0-reproduction` and `release/2.8.0-lumped-shifts`, both merged before this review was written; `git merge-base --is-ancestor` checked) against the tag `v2.7.1`. The diff is 771 files, of which 82 under `pcbthermal/` (6156 insertions, 887 deletions) and 104 under `tests/`. `pcbthermal.__version__` is still `2.7.1`; `tests/regression/data/v2.8.0.json` is in place (332 records, 70 transients, 28 skipped, 20 boards) and `tests/regression/data/pending/` is gone.

## 1. Verdict

**NO-GO for tagging the current tree. GO after one fix**, on these conditions:

1. **Blocking**: the FEM puts the side-wall film of a metal block on the walls of the block's interface pad slab, a slab that has no physical height (section 3.1). Fix it on a `fix/` branch (one condition in `pcbthermal/femmesh.py:1324`, a regression test, a pending file for the two frozen FEM records of `finned_block`, the documents that quote the FEM against the FVM on the finned block), through executor, reviewer and maintainer with its whole battery, then refreeze only those records.
2. The whole battery on the final tree (after the fix), real-board environment proven loaded, read to its last line, plus the gates of `RELEASE_GATE.md` 6 **and** `PCBT_COMPAT_V271=1` (section 3.4).
3. The release commit makes every change of section 6.

Everything else read in this review is fit to release: the model corrections are documented, the reproduction pass found 0 unexplained shifts, the refreeze found 0 alarms, the project file format is unchanged and a 2.8.0 project with the FEM opens in v2.7.1 (re-run here), and the non-blocking items of section 3.2 can wait for 2.9.0.

## 2. What entered `development` since v2.7.1

| Category | Branches | Moves a number |
| :-- | :-- | :-- |
| Model corrections | `fix/face-film-half-slab` (M1), `fix/drawn-copper-faces` (M2), `fix/lumped-part-readout` and `fix/lumped-edge-first-link` (M3), `fix/block-exact-cover` (M4), `fix/analytic-transient-hot-point` | yes, on purpose; frozen through the pending files, now folded into `v2.8.0.json` |
| New model and read-out | `feature/fem-core`, `feature/fem-mesh-and-guard`, `feature/fem-model`, `fix/fem-solve-speed`, `feature/fem-gui`, `fix/thick-plate-surface-estimate`, `feature/surface-always-both` | additions only (FEM records, surface metrics) |
| Interface | `feature/gui-panel-polish`, `feature/gui-results-warnings`, `fix/gui-review-rest`, `feature/element-tree-filter`, `fix/board-dock-write-back` | no (the dock fix stops a silent clamp of the copper thickness of a loaded project) |
| Texts and warnings | `fix/convection-warnings`, `fix/horizontal-face-laws`, `fix/thick-plate-warning-bound`, `fix/via-and-edge-warning-texts`, `fix/typical-values-marks`, `fix/calculator-audit-items`, `fix/audit-leftovers`, `fix/housekeeping-280` | no |
| Tests and tools | `fix/published-case-tests`, `fix/muzychka-case2-tests`, `fix/profiles-cut-overlay-flake`, `fix/ocr-map-reading-status` | no |
| Investigations | `research/` lumped-edge-link, drawn-copper-faces, muzychka-case2-analytic, block-warning-remeasure, independent-fem-extensions, lumped-dense-via-group, lumped-zone-placement, market-fem-comparison, transient-reference-boards, through-thickness-readout, readout-conventions, fem-amg-thin-layers, drawn-ell-fvm-fdm | no (program untouched) |
| Documents and release records | about 45 `docs/*` branches (audit, final review, design, plans, GUI reviews), `release/2.8.0-gate`, `-refreeze`, `-reproduction`, `-lumped-shifts` | no |

Every non-`docs/` branch merged since v2.7.1 (`git log --merges --first-parent v2.7.1..development`) was ticked against `CHANGELOG.md` [Unreleased]: every `fix/` and `feature/` branch has its entry (`fix/via-and-edge-warning-texts`, `fix/housekeeping-280` and `fix/audit-leftovers` without their branch name, by content). Five investigations were missing from the Docs line (through-thickness-readout, readout-conventions, muzychka-case2-analytic, drawn-ell-fvm-fdm, fem-amg-thin-layers): **added by this review**.

## 3. Findings

### 3.1 Blocking: the FEM gives the interface pad of a block side-wall films (defect in the program)

`pcbthermal/femmesh.py:1324`:

```python
slab_ids = [s for s, sl in enumerate(zs) if sl["region"] == "blk" and sl["face"] == face]
```

selects the block slabs **and** the pad slab (`kind "pad"`, also `region "blk"`, lines 827 and 834), and line 1327 puts the wall film `blocks.wall_h` (the face coefficient plus `h_extra`) on the walls of every one of them. The pad is the interface resistance drawn as a slab of height `R'' x K_PAD` (`K_PAD` = 1 W/mK, `femmesh.py:60`; `docs/theory.md` 4a): 0.5 mm for the default `contact_r` 5e-4 m2K/W, 5 mm for 5e-3 m2K/W. Its walls are not a surface of the real assembly, so the FEM opens a heat path around the interface that does not exist. The 3D solid, whose pad rule the FEM copies, puts the wall film only on `kind == "blk"` (`solid3d.py:393`). `docs/theory.md` 4a ('the films ... on every wall slab') does not say whether the pad is one; the code of the reference model says it is not.

Evidence (program at `b4ee3955`, `nice`, < 2 GB, scripts in the review's scratchpad; 'copy' = the same program with `and sl["kind"] != "pad"` added to that line, measured on a copy, nothing edited):

| Board (cell 1 mm) | contact_r m2K/W | FVM | 3D solid | FEM (program) | FEM (copy) |
| :-- | --: | --: | --: | --: | --: |
| one-dimensional column: 20 x 20 mm, 2 layers, 400 um, 4 W over the whole top, top insulated, block 3 mm over the whole bottom, `h_extra` 390 | 5e-4 | 72.434 | 72.441 | 71.199 | 72.446 |
| same | 5e-3 | 117.434 | 117.441 | **83.734** | 117.446 |
| 40 x 30 mm, 2 layers, 400 um, 3 W 6 mm part on top, block 20 x 14 x 3 mm on the bottom, `h_extra` 20 | 5e-4 | 112.211 | 112.224 | 110.166 | 112.143 |
| same | 5e-3 | 117.963 | 117.978 | **102.572** | 117.896 |
| 40 x 30 mm, 35 um, 1 W, block on the TOP face | 5e-4 | 59.568 | 59.591 | 58.696 | 59.455 |
| same | 5e-3 | 65.840 | 65.637 | **58.970** | 64.825 |
| `finned_block` (frozen board), cell 2 mm / 1 mm | 5e-4 | 129.687 (2 mm) | | 128.806 / 129.918 | 129.096 / 130.208 |
| `example_block_board`, cell 2 mm | 5e-4 | 77.106 | | 74.931 | 75.183 |

With the condition the FEM meets the FVM and the 3D solid to 0.07 K on the plain boards (0.012 K on the column, the closed-form case) instead of 1.2 to 2.0 K (1.5 to 2.4 % of the rise) at the default interface and 15 to 34 K (13 to 29 % of the rise) with a 5e-3 m2K/W interface (for example a 1 mm gap pad of 0.2 W/mK), always on the cool, unsafe side. Nothing else moves: the FVM, FDM, LPTN, Analytic and 3D solid do not read `femmesh`; the frozen records that move are `finned_block|fem|1` (+0.29 K) and `finned_block|fem|2` (+0.29 K); `finned_block|fem|0.5` is skipped in the frozen file.

Why it blocks: the FEM is the new model of this version and is presented as the structurally independent method against which the others are compared; on a board with a block and a thick pad it would tell the user that the FVM and the 3D solid are 13 to 29 % hot when they are right. The fix is one condition; no test of the battery covers a block with a large interface in the FEM (`tests/test_fem_model.py::test_a_block_is_read_like_the_other_models` uses `rel=0.05` at 5e-4, which the defect passes). Regression test proposed: the one-dimensional column above at 5e-3 m2K/W, FEM equal to the FVM and the 3D solid within 0.05 K. Documents to touch in the fix: `CHANGELOG.md` (an entry), `docs/theory.md` 4a (the pad has no wall film, as in the 3D solid), `WHAT_MOVED.md` 3 and `CHANGELOG` summary where they quote `finned_block` FEM -0.02 % of the FVM at 1 mm (it becomes about +0.25 %: FEM 130.208 against FVM 129.941 °C; the block and point metrics of the two records move too), `docs/versions.md`.

If the maintainer prefers to release without the fix, the minimum is a warning of the FEM for any block with a contact resistance and a line in the CHANGELOG and the guide; this review does not recommend it (the warning would be longer than the fix).

### 3.2 Non-blocking

| # | Class | Finding | Evidence | Action |
| --: | :-- | :-- | :-- | :-- |
| 1 | stale document (program docstring) | `pcbthermal/femcore.py:13` says the FEM is 'Not selectable in the program yet' and that there is no mesh builder from a Problem 'here' | the model is selectable (`api.COMPARISON_MODELS`, the Models box) | correct with the fix of 3.1 (same module family, no number moves); not edited here (program) |
| 2 | stale document | `docs/validation.md` 55.6: the 1 mm FVM surface of case 2 (+0.51 / +1.26 / +1.01 / +0.77 K over the independent 3D surface) is not reproduced: the 1 mm cell centred on the centroid reads +0.56 / +1.26 / +1.03 / +0.80 K (the values quoted for 0.5 mm) | run here on `b4ee3955`: FVM surface 97.97 / 105.11 / 102.34 / 100.75 °C, column 95.44 / 99.23 / 97.57 / 97.10 °C | **corrected by this review** (a note in 55.6 with the tree and the read-out); the 0.05 K does not change a conclusion or a test band (`test_t3b` accepts 0.3 to 1.6 K over the paper) |
| 3 | stale document | `CHANGELOG.md` Docs line lacked five investigations of the cycle | section 2 | **corrected by this review** |
| 4 | stale document | `CLAUDE.md` 14 says 'frozen numbers 347 ... (317 old intact)' and 15 lists the pending files and the steps left as if the refreeze and the reproduction were still to come; `docs/versions.md` 'Unreleased (2.8.0, in progress)' says the numbers are 'held by the pending files ... until the refreeze' and 'Next: 2.8.0 (investigations that may become features)' | the refreeze is done (332 records, pending folder deleted) | the release commit (section 6) |
| 5 | release process | `RELEASE_GATE.md` 6 and `CLAUDE.md` 14 list four gates; the new gate `PCBT_COMPAT_V271=1 tests/test_format_compat_271.py` (a 2.8.0 project with the FEM opened by the v2.7.1 tag) is in neither | run here: `PCBT_COMPAT_V271=1 PCBT_COMPAT_V245=1 ... pytest tests/test_format_compat_271.py tests/test_format_compat_245.py tests/test_docs.py tests/test_license_header.py tests/test_version.py tests/test_help.py` 896 passed; `test_format_compat_271.py` + `test_fem_gui.py` 31 passed | add the command to `CLAUDE.md` 14 and run it in step 6 |
| 6 | limit to record | `api.py:153`: the reader of 2.8.0 refuses a `comparison_models` list with any item other than `fem`; a 2.9.0 file that adds another comparison model there will be refused by 2.8.0 (the key was made so that an older reader would not refuse) | read in the code | 2.9.0: put new models under a key 2.8.0 drops, or accept and drop unknown items there; record in `releases/2.9.0/PLAN.md` |
| 7 | process | the CLI scenario of this review (`run --model compare --surface-files` on the example board) peaked at 3.3 GB (the 3D solid and the FEM in one process), above the 2 GB asked for the light runs of this review | `/usr/bin/time -l` | none (the memory guard allowed it; noted for honesty) |
| 8 | already planned | e12 (Lumped `rings` guard), e13 (`sqrt(A)` flag of the surface for an elongated part), e14 (Power profile message without the FEM) of `releases/2.9.0/PLAN.md` | read, not re-measured | stay in 2.9.0 (confirmed, section 5) |

### 3.3 Interactions checked

| Pair | Scenario run here | Result |
| :-- | :-- | :-- |
| face film (M1) x surface read-out x FEM, thick plate | case 2 of Muzychka (50 x 50 x 10 mm, k 150, `h` 400, four sources) at 1 mm in FVM, FDM, FEM through `api.simulate` | FEM surface 97.47 / 103.85 / 101.33 / 99.99 °C at the centred cells, column 95.44 / 99.23 / 97.57 / 97.10, equal to `REVIEW_BRANCH4.md` to 0.01 K; the paper 97.40 / 103.82 / 101.28 / 99.94 within +0.07 K (the 1 um film of the Problem); FVM and FDM columns equal the FEM column to 0.05 K; FVM surface +0.56 to +1.26 K above the 3D surface, flagged upper side (as documented, see 3.2 #2) |
| thick plate x block x FEM x surface x save/load | 40 x 30 mm, 400 um, 3 W, 3 mm block; all five steady models; saved and re-opened | every model re-runs bit-identical (FEM 2e-10 K); the file writes the FEM under `comparison_models` and re-opens it; FVM / FDM surface +0.029 K over the column; **FEM 2.04 K low: the defect of 3.1** |
| block x FEM without a block | the same board without the block, cell 1 and 0.5 mm | FVM 145.615 / 145.621, 3D 145.635 / 145.636, FEM 145.534 / 145.608: the thick-copper plate itself agrees, so the gap of 3.1 is the block alone |
| CLI x model names x report text | `python -m pcbthermal run examples/example_board.pcbt.json --model compare --surface-files` | exit 0; Summary with `Tmax [°C] (column)`, `Tmax [°C] (surface)`, `ΔT [K]`, `Rθ [K/W]`, balance `0.00 %`, names FVM, LPTN, Analytic, FDM, 3D solid, FEM; FVM 85.47, LPTN 86.91, Analytic 84.80 °C as the doc review; surface lines 'estimate' for FVM and FDM, 'resolved' for the FEM; `surface_fvm/fdm/fem.csv` written, none for the 3D solid (no surface read-out, `n/a` in the table) |
| project file across versions | `PCBT_COMPAT_V271=1`, `PCBT_COMPAT_V245=1` | passed (a FEM-only project opens in v2.7.1 and runs the FVM there, as `comparison_only` says) |
| M1 x M2 x M3 x M4 on the same records | not re-run: the refreeze (`refreeze/REPORT.md`: 0 alarms, 3882 shifts by 13 rules, rules R1 to R7 combine the items) and the reproduction pass (0 unexplained of the compared scripts) cover it | accepted |
| GUI branches A, B, C x report text | `tests/test_help.py`, the doc review's CLI run, this CLI run | consistent; the Markdown header of the CLI writes `[°C]`, the window `°C (column)`: both are documented forms |
| units, model names, run state | the diff scanned (section 4) | no leftover |

### 3.4 What a user meets when upgrading from 2.7.1

* **Files**: `project.py` and `fileschema.py` are unchanged since v2.7.1; `model.py` adds a method (`Board.face_film_h`) and text only. A 2.7.1 project opens and saves the same in 2.8.0. A 2.8.0 project opens in 2.7.1; its FEM tick is dropped there (a FEM-only project runs the FVM). The Board dock no longer clamps a stored copper thickness above 210 um on the first edit, so a 2.7.1 user who saved a thick-plate project after such an edit has a file with the clamped value; 2.8.0 shows it as stored (it cannot know the old value): worth one sentence in the release notes.
* **Numbers** (`WHAT_MOVED.md`, `refreeze/REPORT.md`): FVM, FDM, Analytic 1e-5 K typical, at most +0.13 K on the frozen boards except where a drawn copper edge cuts a cell at 2 mm (FVM up to +17.9 K, FDM up to +19 K on the new `drawn_*` boards; +0.19 / +1.9 K on the old ones); a thick plate +0.93 K (10 mm, 150 W/mK, 400 W/m2K); the LPTN board maximum -3.1 to +3.1 % of the rise and part rows up to +14.9 K (the part's own peak); the calculator's JEDEC board without vias 74.6 to 83.5 K/W; the 3D solid unchanged. The surprise most likely to be reported: a LPTN part row up to about 10 % hotter, on the safe side, explained in the CHANGELOG summary.
* **Window**: names changed ('Lumped' is 'LPTN' everywhere), the Summary headers name the read-out, differences are in K, a surface column appears for every FVM and FDM result. No workflow is removed.

## 4. The program: scan of the diff

* `print` in the added lines: four, all in `cli.py` (user output of the command line, as before). No `TODO`, `FIXME`, `breakpoint`, debugger, personal path or bare `except:` in the added lines of `pcbthermal/`.
* FEM and pyamg: `femcore.available()` and `_import_pyamg` catch only `ImportError`; `fem.solve_steady` re-raises `FemUnavailable` and `FemCancelled` and turns a non-converged `RuntimeError` into a `ValueError` with the reason; `api.py:1283` turns `ValueError` and `FemUnavailable` into a skipped model with a warning. Nothing is swallowed silently.
* User-facing 'comparison' wording: none left in the window, the guide or the CLI help (the only hits are code comments in `api.py`).
* Doxygen, licence headers, version tests, help words: `tests/test_docs.py`, `test_license_header.py`, `test_version.py`, `test_help.py` pass (896 with the compat gates).
* `git ls-files .venv .venv-research`: empty.
* The jobs path: one character changed in `jobs.py`; the FEM receives the cancel callable of the job and checks it between assembly chunks. Not driven in a real window here (the GUI is tested offscreen only; the real-screen checklist `fem-model/GUI_TEST_CHECKLIST.md` is not done).

## 5. Decisions of the orchestrator, confirmed or reversed

| Decision | Opinion |
| :-- | :-- |
| Documentation simplification (`docs/simplify-*`) after the release | **Confirmed.** It moves no number and is six branches in series; doing it now would reopen documents that two reviews have just closed. |
| The record branches (`docs/*` reviews, release records) merged at the end | **Confirmed.** They hold documents and figures only; the rule keeps every branch. |
| Heavy studies not run in the reproduction pass (about 205 scripts, about 30 of part B open) | **Confirmed, with a caveat written down**: the pass compares the program with v2.7.1 and so cannot find a defect in what is new; the defect of 3.1 was found by an independent reference (the 3D solid and the FVM), not by the pass. The risk of the old models is covered by the frozen numbers (332 records at three cells) and the battery. |
| The three small items e12, e13, e14 in 2.9.0 | **Confirmed**: text, a guard and a flag; no number moves; none is a wrong number on the safe side of a decision. |
| `CLAUDE.md` stays about 48 KB | **Confirmed for the release** (it is rules); section 16 still says 40 KB, so either the maintainer moves section 12 or 13 out after the release or section 16 says 50 KB. A maintainer's decision. |

## 6. The release commit of 2.8.0 (after the fix of 3.1 and the battery)

1. `pcbthermal/__init__.py`: `__version__ = "2.8.0"` (the only definition: title, status bar, About box, `--version`, reports and saved projects follow it; `tests/test_version.py` needs `## [2.8.0]` in `CHANGELOG.md` and `2.8.0` in `README.md`).
2. `CHANGELOG.md`: `## [Unreleased]` becomes `## [2.8.0] - <date>`, a new empty `## [Unreleased]` above it; the summary paragraph keeps its numbers (and gains the FEM pad fix).
3. `README.md`: version badge `2.7.1` -> `2.8.0`; tests badge from the final battery (today `4013 passed`); the line '**2.8.0** (in preparation, not released)' -> '**2.8.0** (<date>)'; the release note about a thick-plate project saved after the dock clamp (3.4), if the maintainer wants it.
4. `docs/versions.md`: the summary at the top ('Summary of the current version (2.7.1 ...)', 'Released in 2.7.1', 'Next: 2.8.0') -> 2.8.0 and 'Next: 2.9.0'; the heading 'Unreleased (2.8.0, in progress)' -> '2.8.0 - <date>' with its first paragraph no longer saying the numbers are held by pending files; 'How each version was tested': the final battery line and the four (five) gates.
5. `CLAUDE.md`: section 14 'Current state of the battery' (final battery; frozen **332** records; compat 5 + the v2.7.1 gate; the `PCBT_COMPAT_V271=1` command in the list of commands); section 15 'Where to continue' (released v2.8.0, next 2.9.0 with `releases/2.9.0/PLAN.md`; remove the pending-file list).
6. `docs/decisions-log.md`: the release entry prepended.
7. Nothing for the About box or the help pages: they read `__version__` (`gui/help.py`); `tests/test_help.py` passes with either version.
8. Not in the commit: `tests/regression/data/v2.8.0.json` is already the frozen file (only the records of the fix of 3.1 change, through their own pending file and the harness, before the bump or with it: the harness refuses a run of another version, see `refreeze/REPORT.md`); `docs/version-comparison.md` stays stale with its note (item e15 of 2.9.0); `research/README.md` needs no version line.
9. After the commit: merge to `main` with `--no-ff`, annotated tag `v2.8.0`, push, `gh release create v2.8.0 --notes-file <the CHANGELOG section> --verify-tag`, `gh release list` (CLAUDE.md section 6), only with the maintainer's word.

## 7. Open decisions for the maintainer

1. Fix the FEM pad walls before the tag (recommended; one condition, one test, two frozen FEM records +0.29 K) or release with a warning (not recommended).
2. The real-screen checklist of the window (about one hour of his hands) before the word or after.
3. `CLAUDE.md` size rule (section 5 above).
4. Whether the release notes say that a thick-plate project saved under 2.7.1 after a dock edit may hold the clamped 210 um copper.

## What was read and what was not verified

* **Read**: the diff stat and the program diff of `project.py`, `fileschema.py`, `model.py`, `jobs.py`, the FEM block code of `femmesh.py` (lines 800 to 840, 1190 to 1330) against `solid3d.py` (the pad and walls), the exception paths of `fem.py`, `femcore.py`, `api.py`; `RELEASE_GATE.md`, `reproduction/README.md`, `refreeze/REPORT.md`, `theory-review/README.md` (sections 1 to 5), `doc-review/README.md`, `fem-model/REVIEW_BRANCH4.md` (sections 2 to 4), the CHANGELOG [Unreleased], `docs/theory.md` 4a (mesh, films), `docs/validation.md` 55.6, `releases/2.9.0/PLAN.md` e10 to e15, the registers of the 13 new research folders (each has its 'what was read / verified' section and its rows in `research/REVIEW.md` and `research/README.md`).
* **Read only in part or from the reports**: `WHAT_MOVED.md` (headline and the FEM paragraph), `DIFF_v2.7.1_vs_final.md` (through the refreeze report), `LUMPED_SHIFTS_REVIEW.md`, `STALE_TESTS_DECISIONS.md`, `MEMORY_GUARD_STUDY_ARRAY_BOARD.md`, the other FEM reviews (`REVIEW_SURFACE_ALWAYS`, `REVIEW_SPEED`, `REVIEW_GUI_*`), `audit/FINAL.md`, the GUI diff (`gui/*`, about 2000 lines), `checks.py`, `copper.py`, `lumped.py`, `analytic*.py`, `memory.py` diffs: not re-read line by line; their reviewers' verdicts are taken as given.
* **Re-run here**: the six scenarios of section 3.3 and the measurements of 3.1 (program and a copy of the one line), the compat gates for 2.4.5 and 2.7.1, the document tests. **Not re-run**: the whole battery (the tester's step), the frozen numbers at three cells, the published-case and secret gates, any research study, the GUI in a real window, the FEM on boards larger than 60 x 40 mm, the FEM of a block with fins and a large interface together, the transient models.
