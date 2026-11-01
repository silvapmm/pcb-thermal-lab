# Reproduction pass of release 2.4.5: the research folders on the current tree

The READMEs of the research folders hold numbers measured on the program of 2.4.4 or earlier. This pass re-runs the studies of the folders that import the program on
`develop` at `0d4159f` (the 2.4.5 candidate) and compares every printed table with the README. The items of 2.4.5 that can move a number: part across the outline
(`62afbb8`), board cover 8 x 8 (`7a5b0ee`), point via and block SOR (`5e93182`), Young relaxation factor (`d9216c4`, speed only), constriction of the heat on a via in the
Lumped and Analytic models (`f671868`), laminate rule with sub-gaps, face term and column SOR (`e9f4df2`), and the warnings (no shift). No README number of a folder was
rewritten by this pass; the corrections it made are listed in section 3.

## 1. Totals

Three testers worked in parallel (A, B, C) and counted in different units, so the totals are given per part and not forced into one number.

| Part | Folders | Counted in | Checked | Unchanged | EXPLAINED | UNEXPLAINED | NOT RUN |
| :-- | :-- | :-- | --: | --: | --: | --: | --: |
| A | analytic-partial-copper, bare-spot-under-source, gap-subdivision, lumped-via-groups, lumped-analytic-vias, via-fill | comparison units (rows of the table below) | 36 | 19 | 14 | 0 | 3 |
| A | the same | table cells (approximate) | about 1850 | about 1620 | about 235 | 0 | 3 scripts and 4 files |
| B | point-via-convergence, sor-with-via-couplings, rotated-square-3d, models-comparison, `docs/validation.md` sections 1, 2, 2.1, 5 | comparison units (about 2500 numbers inside) | 77 | 32 | 40 | 0 | 5 |
| C | outline, stackup, power-calculator, component-heatsink, block-and-fins, solid3d-verification, effective-conductivity, zone-union, plate-h-level, horizontal-plate-h, fin-channel, fin-channel-sources, theory-sources, via-real-board, laminate-nodes, young-omega-tiles, gerber-models | rows or values | about 430 | about 330 | about 95 | 0 | 5 scripts, about 90 not listed |

In units A and B together: 113 checked, 51 unchanged, 54 explained, 0 UNEXPLAINED, 8 not run. UNEXPLAINED is zero in all three parts: every number that moved was tied to one
item (by reading `docs/versions.md`, `CHANGELOG.md` and the `INTEGRATION.md` files and, where the item was not obvious, by running the same script on a `git archive` copy of
the tree before the suspected item). Two cases are explained as to the item but deserve the reviewer's eye (Part B, 3.1): a via whose centre is off the outline cools more than
before, and the 3D solid on a square board turned 45 degrees is further from the aligned value.

## 2. Reading the table of Part A

Most folders freeze the earlier program inside `lib/` (`lumped_patch.patched("off")`, `program_patch.patched("point")`, `layered.py` with `ladder=False`) so that their
columns named "program" keep meaning "the program up to `f2d5c03`". Those columns reproduce by construction: they test the library, not the 2.4.5 program. The columns that
call the current program directly (FVM, FDM, "program" in the validation rows) are the ones that moved.

## 3. What this pass changed (commits on this branch)

* Part C and Part B reports (cherry-picked from the tester branches) and this README; the runner `scripts/run_all.py` (one command, writes `out/reproduction.json`, git-ignored).
* `research/gap-subdivision/baseline/validation_impact.csv` regenerated (only the boards with vias moved: point via). `gap_nodes.csv` and `gap_grading.csv` were not regenerated: they need `out/refs_pads.json` (1.5 to 3 hours).
* Power Calculator numbers: `docs/calculators.md` 1.1b, 1.1c and table 2.2, `research/power-calculator/README.md` 4.7 and table, `DESIGN_COVERAGE` and the title of figure 6. The example band (drawn board = real board) is unchanged at the ring (2.00 / 1.62 / 2.31 W, default level 1.56 / 2.34) and the top best case moves 1.69 -> 1.68 W (default level 1.60 -> 1.58 W). The drawn boards of the coverage study moved by 0.002 to 0.05 W (point via, laminate rule). **The hatched-copper case leaves the band at the level Drawn by hand** (worst case 1.931 W against a true 2 W; it was 2.012 W); it is inside only at Estimated (2.012 W, 0.012 W from the edge). The missing-vias case is 0.002 W short without the design term and inside from the level Drawn from fabrication files. Cases inside: none 0 of 4 (was 1), cad 1 of 4, hand 1 of 4 (was 2), estimated 2 of 4. Band amplitudes unchanged.
* `research/component-heatsink` and `research/effective-conductivity`: the patch of the executor (package prototype built without the laminate rule and guarded instead of hanging, with a test; the corrections study passes the natural-convection form).
* `research/sor-with-via-couplings`: the library builds the network without the laminate nodes (`ladder=False`), as its stencil assumes, and asserts it; `study_real_board.py` now reproduces README 4.1 (60.225 K, 2260 / 2390 / 189 iterations; program 60000 and 20000 sweeps not converged) and `study_block_over.py` runs to the end (example board no-via row 2247 -> 813 sweeps, Young omega; block 2390 and over 2250 unchanged).
* `research/models-comparison/scripts/study_time_and_coefficients.py`: the exact-integrator check switches `laminate.uses_rule` off like `tests/test_fvm.py`; it prints the README digits (3.06 / 1.67 / 0.875 / 0.448 and 0.315 / 0.0772 / 0.0192 / 0.00479).
* Left alone on purpose: `docs/validation.md` section 5 and the point-via topics (reopened branches), the `checks.py` message for a via outside the outline, and the stale text listed at the end of Part B.

Tests run on this branch after the changes (one `pytest` at a time): `tests/test_docs.py`, `tests/test_license_header.py` (368 passed), `tests/test_calculator_design.py`, `tests/test_help.py` and `research/power-calculator` (376 passed), `research/component-heatsink/tests` and `research/effective-conductivity/tests` (385 passed with the docs and licence tests), `research/sor-with-via-couplings/tests` and `research/point-via-convergence/tests` (401 passed with the docs and licence tests). The research tests of the folders of each part are in the sections below.

## 4. How to run again

    .venv/bin/python research/reproduction-245/scripts/run_all.py [--folders a,b] [--timeout SECONDS] [--force] [--list]

`JOBS` lists the studies in order, `SKIP` the ones not run and why; every output goes to `research/reproduction-245/out/<folder>/<script>.txt` and a summary to `out/reproduction.json`.
A run can be resumed. A script that a folder README says needs more than about 20 minutes is in `SKIP`.


---

## Part A: analytic-partial-copper, bare-spot-under-source, gap-subdivision, lumped-via-groups, lumped-analytic-vias, via-fill

Program under test: `develop` at `0d4159f` (2.4.5 not yet released). Items of 2.4.5 that can move a number: part across the outline (`62afbb8`),
board cover 8 x 8 (`7a5b0ee`), point via and block SOR (`5e93182`), Young omega (`d9216c4`, speed only), constriction of the via in the Lumped and Analytic models
(`f671868`), laminate rule with sub-gaps, face term and column SOR (`e9f4df2`). Tolerance: the folder's own, or 0.5 % when it states none. Counts are cells of the
README tables that were compared (approximate: a cell is one number of a table or one quoted number).

Short names used below: PV = point via (`5e93182`), CON = constriction (`f671868`), LAM = laminate rule (`e9f4df2`).

A note that matters for reading the "unchanged" rows: most of these folders freeze the earlier program inside `lib/` (`lumped_patch.patched("off")`,
`program_patch.patched("point")`, `layered.py` with `ladder=False`), so that their columns named "program" keep meaning "the program up to `f2d5c03`".
Those columns reproduce by construction; they test the library, not the 2.4.5 program. The columns that call the current program directly (FVM, FDM, "program" in the
validation rows) are the ones that moved, and each shift below is tied to one item.

### Results

| Folder | README section | README | now | item | status |
| :-- | :-- | :-- | :-- | :-- | :-- |
| analytic-partial-copper | 3 (five models on 20 pad boards, error %) FVM column | -7.8 / -4.8 / -3.4 / -2.2 / -1.1 (1 layer, pads 6 to 30); -13.4 / -8.5 / -6.1 / -4.1 / -2.2 / -1.2 (2 layers bare); -18.0 / -9.2 / -5.2 / -2.5 (2 layers full) | -3.9 / -2.1 / -1.3 / -0.9 / -0.6; -3.9 / -2.3 / -1.7 / -1.1 / -0.6 / -0.1; -4.8 / -2.4 / -1.4 / -0.9 | LAM (sub-gaps where copper is absent) | EXPLAINED (16 cells moved, rows with full copper within 0.3) |
| analytic-partial-copper | 3, FDM column | -17.1 / -11.2 / -8.2 / -5.4 / -2.8 / -1.4; -20.7 / -13.7 / -10.1 / -6.8 / -3.6 / -1.9; -26.0 / -13.9 / -7.9 / -3.9 | -15.1 / -9.6 / -7.0 / -4.6 / -2.5 / -1.3; -15.0 / -9.7 / -7.1 / -4.6 / -2.3 / -1.0; -18.3 / -9.4 / -5.2 / -2.8 | LAM | EXPLAINED (14 cells) |
| analytic-partial-copper | 3, Lumped, Analytic, 3D solid columns | as printed | within 0.1 point on all 60 cells | none | OK |
| analytic-partial-copper | 4 (causes: parity, 600 modes, cell, fill, sheet and node costs) | 18 rows | identical (rows of `study_causes.py`) | none | OK (about 60 cells) |
| analytic-partial-copper | 5.2 (candidate n = 1, 2, 4, 8 on the 20 boards), 5.3 (out of sample), 5.4 (tile and nodes), 5.5 | as printed | identical to 0.1 point (candidate in `lib/defect.py` does not call the program FVM) | none | OK (about 130 cells) |
| analytic-partial-copper | 5.6 (52 pad rows and 44 uniform rows, Analytic and candidate) | min/max/mean, examples | identical; the program Analytic recomputed equals the committed column to 3.4e-7 | none | OK (about 60 cells) |
| analytic-partial-copper | 9.1 (second independent reference), FVM column | -3.8 / -1.8 / -6.9 / -1.7 / -13.7 | -1.6 / -0.7 / -1.6 / -0.3 / -2.9 (layered3d and resolved3d, Analytic and candidate unchanged) | LAM | EXPLAINED (5 cells; 20 other cells OK) |
| analytic-partial-copper | 9.2 (candidate against the program FVM with the same nodes, 10 rows x 6 tile counts) | e.g. 40/10/2 n=2: +2.5 / +2.1 / +0.3 / -0.2 / -0.3 / -0.3 | +0.1 / -0.3 / -2.0 / -2.5 / -2.6 / -2.6 (the first row; most of the 60 cells move by 0.5 to 6 points) | LAM (the README's own "Update for 2.4.5" says the same-nodes comparison needs the rule switched off) | EXPLAINED (about 50 of 60 cells) |
| analytic-partial-copper | 9.3 (pad edge inside a tile, candidate against the FVM n = 2 at 0.25 mm) | +0.2 / -7.7 / -5.8 / -2.9 / +0.2; +0.3 / -3.6 / -2.6 / -1.2; -0.3 / -3.3 / -0.3 | -2.6 / -10.2 / -8.2 / -5.4 / -2.2; -1.1 / -4.9 / -3.8 / -2.4; -2.9 / -5.7 / -2.6 | LAM | EXPLAINED (12 cells; the ordering and the conclusion do not change) |
| analytic-partial-copper | 9.4 (trigger of the warning, 119 boards) | program flag 60 warned / 59 silent / 5 beyond 5 %; larger of two spreads 70 / 49 / 0 | the program's flag now gives 70 / 49 / 0, the spread-at-`lambda_l`-only trigger 60 / 59 / 5; worst silent board -1.2 % (was -1.9 %, against the FVM) | the warning of 2.4.5 uses the larger of the two spreads (the README's "either"); LAM for the -1.9 -> -1.2 | EXPLAINED (about 15 cells) |
| bare-spot-under-source | 7.2 (19 validation scenarios, program / vert / n=2+v / n=4+v / 3D solid) | 85.81 / 88.91 / 94.67 / 79.97 (example board family) | 85.22 / 88.29 / 94.67 / 79.38 | PV (vias of the example board) | EXPLAINED (3 rows; "no vias" row identical) |
| bare-spot-under-source | 7.2, the other 15 rows (reference board, corner, 8 layers, straddling 143.89, no copper 150.16, island 92.38, hatched 105.78, ...) and the 3D solid column | as printed | identical to 0.01 K | none | OK (about 120 cells) |
| bare-spot-under-source | 9 (review: graded references, FVM 0.5 mm -17.6 / -21.2 / -6.3 / -3.4 / -3.4 %, vert, n=4+v, 3D solid centre and face, heat across the window edge) | as printed | identical | none | OK (about 45 cells) |
| bare-spot-under-source | 7.2 note: "program" column | the study's "program" is the copy of the 2.4.4 network (`ladder=False`) | so the laminate rule of the real program is not exercised by `study_validation_rows.py` | LAM (see `docs/validation.md` 21.2 for the program) | NOTE |
| gap-subdivision | baseline/uniform.csv (44 boards), baseline/pads.csv (52 boards) rerun with `rerun_baseline.py --update` | stored values | largest movement 0.0000 % (uniform) and 0.0001 % (pads) for the five models | none (`pads.csv` was already regenerated for 2.4.5) | OK (480 cells) |
| gap-subdivision | baseline/validation_impact.csv and README 6.1 (22 rows, FVM column and n=2, n=4 columns): example board FVM 60.81, no vias 69.67, project example/profile 60.81 | FVM 60.814 / 63.913 / 60.292 / 54.967; n=4 all 60.857 | 60.225 / 63.293 / 59.720 / 54.384; n=4 all 60.261 (the 3D solid column and the 18 other rows unchanged) | PV | EXPLAINED (6 rows with vias; the README table quotes 60.81 for 3 rows) |
| gap-subdivision | baseline/real_boards.csv and README 6.2 (three windows of a real board, 2 cell sizes, program fine / z and n = 2, 4, 8) | as printed | identical on the 6 rows (the table is made with the copy of the 2.4.4 network) | none | OK (48 cells) |
| gap-subdivision | baseline/gap_nodes.csv, baseline/gap_grading.csv, `study_review.py` | stored values | not run | needs `out/refs_pads.json`, the converged references of the pad boards (README: 1.5 to 3 hours the first time); a run without it reached the 25 minute limit | NOT RUN |
| lumped-via-groups | 4.1 (cluster in a cell, 16 rows x 6 columns) | E_ref 18.35 ... 63.78; L_prog +31.3 ... | identical | none | OK (96 cells) |
| lumped-via-groups | 3 (cell problem, R_link and closed forms) | as printed | identical | none | OK (about 50 cells) |
| lumped-via-groups | 8 (example board and three arrays, errors of E, gain, maximum temperatures) | E_ref 13.770 / 18.241 / 21.323 / 22.294 / 21.966 / 22.426 | 13.772 / 18.242 / 21.325 / 22.295 / 21.968 / 22.427 (0.01 %); every error column identical to 0.1 point | none (the E_ref of the 0.25 mm reference moves by 0.002 K) | OK (about 100 cells) |
| lumped-via-groups | 7 (vias outside the footprint: lone via 15.1 / 31.4 mean / max, row of five 8.0 / 10.9, L_prog 73.4 / 287.8 and 72.1 / 100.6) | as printed | the 32 rows give the same maxima and means | none | OK (10 cells) |
| lumped-via-groups | 4.2, 5, 6, 12 (family, holdout, zone sensitivity, review) | stored values | not run | `study_family.py` about 15 minutes plus fine-grid references that take about an hour the first time; `study_holdout.py` about 40 minutes; `study_zone_sensitivity.py` references 10 minutes the first time; `study_review.py` reads `out/family.json` and failed at once without it | NOT RUN |
| lumped-analytic-vias | 3.2 and 3.3 (24 rows of the unit cell: E_ref, closed form without constriction, Lumped program, with Krogh; radius of the barrel) | as printed | identical | none | OK (about 130 cells) |
| lumped-analytic-vias | 4.1 (unit cell, 120 cases, summary mean / max of the 9 variants) | 4.9 / 22.8, 0.3 / 1.1, 17.0 / 60.6, 1.4 / 4.5, 6.9 / 34.9, 5.0 / 22.0, 1.2 / 5.5, 0.4 / 1.3 | identical | none | OK (20 cells) |
| lumped-analytic-vias | 5.1 and 5.2 (rings, raster cell, tile, modes) | e.g. 3 x 3 3.5 mm program +23.4 to +28.1; cluster -1.1 to +3.6 | identical | none | OK (about 70 cells) |
| lumped-analytic-vias | 7 (example board and arrays, FVM / Lumped / Analytic and their patches, gain) except FVM of the 7 x 7 array | as printed (E_ref 9.573 ... 22.295) | identical | none | OK (about 85 cells) |
| lumped-analytic-vias | 7, FVM column of the 7 x 7 array at a 1 mm cell | -9.8 (open), -5.6 (copper); gain +95.5 | -6.7, -2.3; gain +95.5 % unchanged | PV: the program (not the patch) gives E = 19.234 / 21.042 K at v2.4.4 and at `5e93182~1` (the README values) and 21.051 / 22.236 K now | EXPLAINED (3 cells) |
| lumped-analytic-vias | 7 text and INTEGRATION 3 (`study_via_fill_rows.py`): copper-fill gain Lumped / Analytic program 6.79 / 6.32 K, patched 4.47 / 4.27 K, FVM_fix 4.20 K | as printed | -6.79 / -6.32 (frozen program), -4.47 / -4.27, -4.20 | none (frozen); the real program now gives -4.48 (Lumped) and -4.27 (Analytic) in the via-fill study | OK (10 cells) |
| lumped-analytic-vias | 4.4 (arrays under a source, 48 + 6 cases at a 0.1 mm reference) | stored values | not run | killed at the 25 minute limit (the pool uses the fine references) | NOT RUN |
| via-fill | 4.1 (resistance of one via by fill) | 192.4 / 192.1 / 183.7 / 58.8 K/W | identical | none | OK (12 cells) |
| via-fill | 4.2 (example board, 0.5 mm): Tmax open / epoxy / paste / copper; change vs open | 85.87 / 85.87 / 85.70 / 81.98; -0.01 / -0.18 / -3.89 | 85.18 / 85.17 / 85.00 / 80.99; -0.01 / -0.18 / -4.19 | PV (mean-potential well instead of the nearest-node via) | EXPLAINED (5 cells; 2 deltas unchanged) |
| via-fill | 4.5 (every model, every fill, two limits): copper fill, no vias and perfect vias rows of FVM, FDM, Lumped, Analytic at 0.5 and 1 mm | copper: -3.89 / -4.09 / -6.79 / -6.32 (0.5), -4.49 / -4.55 / -6.95 / -6.40 (1); no vias: +8.84 / +9.45 / +11.15 / +10.02, +8.86 / +10.20 / +11.85 / +9.91; perfect: -7.13 / -7.54 / -10.86 / -12.20, -8.31 / -8.38 / -12.25 / -12.32 | copper: -4.19 / -4.20 / -4.48 / -4.27 (0.5), -4.14 / -4.15 / -4.65 / -4.18 (1); no vias: +9.54 / +9.56 / +9.25 / +9.50, +9.45 / +9.46 / +9.88 / +9.46; perfect: -9.64 / -9.61 / -12.77 / -12.70, -9.72 / -9.65 / -14.22 / -12.75 | PV for the FVM and FDM, CON for the Lumped and Analytic (the copper-fill gain of the four models now agree within 0.3 K at 0.5 mm; README text "Lumped and Analytic give 40 to 75 % more effect" is no longer true) | EXPLAINED (about 36 cells) |
| via-fill | 4.5, epoxy rows and the 3D solid column (copper -4.49, no vias +8.93) | as printed | identical | none | OK (12 cells) |
| via-fill | 4.5, 3D solid perfect vias at 1 mm | -7.96 | -13.51 | not a 2.4.5 item: the program at v2.4.4 and at `5e93182~1` gives the same 72.46 K (open 85.98) | NOT A 2.4.5 SHIFT (the README value was already stale in 2.4.4; one cell) |
| via-fill | 4.6 (via-array board 21 x 21 mm, FVM / FDM / Lumped / Analytic / 3D solid at 1, 0.5, 0.25 mm): gain | FVM -4.78 / -4.38 / -3.98 / -3.64 / -3.34 (1, 0.5, 0.25, 0.125, 0.0625 mm); FDM -4.63 / -4.41; Lumped -6.68 / -6.77; Analytic -6.05 / -6.01 | FVM -4.50 / -4.47 / -4.49 / -4.49 / -4.49; FDM -4.42 / -4.51; Lumped -4.69 / -4.81; Analytic -4.54 / -4.48 | PV (the FVM now converges at 0.25 mm and below, the point of the item) and CON; the independent reference rows (-4.46, -4.44) and the 3D solid (-4.77, -4.35 -> -4.77, -4.51) are the same except the 3D solid at 0.5 mm | EXPLAINED (about 20 cells); 3D solid at 0.5 mm: README 40.80 / 36.46 / -4.35, now 40.67 / 36.16 / -4.51: the same board on the program at v2.4.4 and at `5e93182~1` gives 40.80 / 36.46 and at `5e93182` 40.67 / 36.16, so it is PV (that commit also changed `solid3d.py`) |
| via-fill | 4.6 text (FVM gain at 2, 1, 0.5 and 0.25 mm on the example board: -4.91 / -4.49 / -3.89 / -3.59 K) | as printed | -3.70 / -4.14 / -4.19 / -4.20 | PV | EXPLAINED (4 cells) |

### Research tests of the folders

| Command (from the repository root, `QT_QPA_PLATFORM=offscreen`, one at a time) | Result |
| :-- | :-- |
| `.venv/bin/python -m pytest -q research/analytic-partial-copper/tests` | 12 passed in 5.3 s |
| `.venv/bin/python -m pytest -q research/bare-spot-under-source/tests` | 12 passed in 46.7 s |
| `.venv/bin/python -m pytest -q research/gap-subdivision/tests` | 8 passed in 2.0 s |
| `.venv/bin/python -m pytest -q research/lumped-via-groups/tests` | 16 passed in 10.5 s |
| `.venv/bin/python -m pytest -q research/lumped-analytic-vias/tests` | 13 passed in 11.8 s |
| via-fill | no tests folder (its tests are `tests/test_via_fill.py`, in the battery) |

### Durations (seconds, `out/reproduction.json`)

analytic-partial-copper: baseline 358, causes 12, candidate 190, rows 85, review 321. bare-spot-under-source: validation rows 156, review about 600.
gap-subdivision: rerun_baseline 147, validation_impact 724, real_boards 68. lumped-via-groups: cluster 9, cell_link 0.3, example board 264, outside 609.
lumped-analytic-vias: causes 1027, via_fill_rows 71, discretisation 82, real_boards 147, unit_cell 39. via-fill: study_via_fill 21, study_via_model_checks 383.


---

## Reproduction of release 2.4.5, part B

Folders: `point-via-convergence`, `sor-with-via-couplings`, `rotated-square-3d`, `models-comparison` (and the two project documents that
`models-comparison/scripts/validation_study.py` and `solver_equivalence.py` feed: `docs/validation.md` sections 1, 2, 2.1 and 5).
Tree under test: `develop` at `0d4159f` (the 2.4.5 candidate). Branch `research/reproduction-245-b`, created from `research/reproduction-245`
(which had no commit holding `run_all.py` yet, so the file was copied from the first tester's worktree). No README number was rewritten.

### 1. Commands and durations

Runner (one job at a time, `OMP/OPENBLAS/MKL_NUM_THREADS=2`, `QT_QPA_PLATFORM=offscreen`, limit 1500 s per job):

    .venv/bin/python research/reproduction-245/scripts/run_all.py --folders point-via-convergence,sor-with-via-couplings,rotated-square-3d,models-comparison

| folder | script | result | seconds |
| :-- | :-- | :-- | --: |
| point-via-convergence | study_unit_cell | ok | 369 |
| | study_array_board --model fvm / fdm | ok / ok | 341 / 344 |
| | study_row_lone --model fvm / fdm | ok / ok | 80 / 69 |
| | study_example_board --model fvm / fdm | ok / ok | 191 / 199 |
| | study_solid3d | ok | 365 |
| | study_solvers, study_edge_via | ok, ok | 2, 8 |
| sor-with-via-couplings | study_variants | ok | 206 |
| | study_real_board | **failed** (IndexError, section 4.1) | 1 |
| | study_block_over | **failed** on its 6th row (same cause) | 32 |
| | study_stiffness, study_failure, study_review | ok | 106, 97, 50 |
| rotated-square-3d | study_regression, study_part_across_outline | ok, ok | 148, 261 |
| | study_remeasure, study_turned_part, study_edge_conductance | ok | 9, 9, 1 |
| | study_cut_cells, study_disc | ok | 39, 60 |
| | study_square_reference | **timeout 1500 s** (machine swapped, see 1.1); rerun alone: ok | 1500 / 197 |
| models-comparison | validation_study | ok | 306 |
| | solver_equivalence, study_lumped_rings | ok | 3, 4 |
| | study_time_and_coefficients, study_complex_boards_independent | ok | 52, 35 |

Scripts of the four folders that `run_all.py` does not list, run by hand one at a time with the same environment (outputs in the scratchpad, not committed):

| script | seconds |
| :-- | --: |
| models-comparison/study_offgrid_heater, accuracy_study, stress_study | 25, 4, 2 |
| models-comparison/study_complex_boards (current tree only) | 68 |
| rotated-square-3d/study_cut_cells --fine | 67 |
| point-via-convergence/study_array_board --sweep (fvm, fdm) | 70, 67 |
| point-via-convergence/study_example_board --model fvm --fine | 1312 |
| point-via-convergence/study_reference_3d, study_target_radius (and --k-inplane 0.9) | 263, 6, 7 |
| sor-with-via-couplings/study_block_over parts 2 and 3 only (part 1 crashes) | about 60 |

#### 1.1 Load

Around 22:40 the machine swapped (load average 40, swap 16 of 17 GB) while three testers ran; the job `study_square_reference` was stopped (SIGSTOP) for
about six minutes and then hit the 1500 s limit of the runner. Rerun alone on a quiet machine it needed 197 s and printed the whole table. The timings of this
section are therefore not benchmarks, and the per-via timings of `study_edge_via` (0.12 to 3.5 ms, README 0.06 to 1.9 ms) are load, not a change.

### 2. Result in one table

Counting is by comparison units (one README table or one numbered statement with numbers); a unit with several rows counts once, in the worst class of its rows.
Inside the units there are about 2500 individual numbers (the unit-cell study alone prints 12 cases x 12 treatments x 5 cells).

| folder | units | OK (equal within the folder's tolerance or 0.5 %) | EXPLAINED (moved, item known) | UNEXPLAINED | NOT RUN |
| :-- | --: | --: | --: | --: | --: |
| point-via-convergence | 15 | 3 | 12 | 0 | 0 |
| sor-with-via-couplings | 20 | 17 | 1 | 0 | 2 |
| rotated-square-3d | 17 | 5 | 12 | 0 | 0 |
| models-comparison (README) | 20 | 4 | 13 | 0 | 3 |
| docs/validation.md sections 1, 2, 2.1, 5 and the off-grid case | 5 | 3 | 2 | 0 | 0 |
| total | 77 | 32 | 40 | 0 | 5 |

Nothing is UNEXPLAINED: every number that moved was traced to an item of 2.4.5, by reading `docs/versions.md`, `CHANGELOG.md` and the folders' `INTEGRATION.md`
and, where the item was not obvious, by running the same script on a `git archive` copy of the commit before the suspected item (section 4).
Two of the explained shifts are behaviours the reviewer should look at (section 3.1): they are explained as to the item, not necessarily right.

### 3. Shifts, with the item that explains each

Items: PV = point via (`fix/point-via`, commit 5e93182, FVM, FDM, 3D solid and the block SOR); PAO = part across the outline (62afbb8); C8 = board cover 8 x 8
(7a5b0ee); SO = SOR relaxation factor (`fix/sor-omega`); VC = via constriction (Lumped, Analytic; f671868); LN = laminate nodes (e9f4df2).
"README" values are those of the README of the folder unless the document is named.

#### 3.1 Two shifts that deserve the reviewer's eye

1. **A via whose centre is off the outline but inside the bounding box still cools the board, and more than before.** Example board cut to the T preset
   (U1 over the cut-away corner; 2 of the 9 vias have their centre off the T), FVM, 1 mm, h_side 10: all 9 vias 107.55 (before PV, README 107.56) -> 104.88 now;
   only the 7 vias on the board: 108.39 before PV, 107.56 now; no vias 118.55 / 118.56. So the two off-board vias were worth 0.84 K before PV and are worth 2.68 K
   now (the footprint is restricted to the board and renormalised, so a via off the outline is moved onto the nearest board cells at full barrel conductance).
   `checks.py` (line 118) only warns about a via outside the bounding box, not outside the outline. The 3D solid did not move on this board (107.79 / 107.08),
   so the FVM-to-3D gap on the T went from 0.2 K to 2.0 K at 2/3 mm. Item: PV. Whether this is intended is for the maintainer; no other preset is affected
   (L, chamfer, ellipse, rounded have all 9 vias on the board; the chamfer/ellipse/rounded FVM values moved by -0.55 to -0.63 K, the same as the rectangular example,
   0.59 K).
2. **The 3D solid on a board turned 45 degrees got further from the aligned value, not nearer.** `study_cut_cells`, 20 mm board, h_side 2000, turned 45 minus
   aligned (K): 1 mm +6.75 -> +8.22, 0.5 mm +4.81 -> +5.12, 0.25 mm +3.78 -> +4.20 (README section 4). Run on the commit before each item: 62afbb8~1 reproduces the README
   to 0.01 K, 7a5b0ee~1 gives +7.22 (so PAO adds +0.47 K at 1 mm) and the rest, +1.0 K at 1 mm, is C8. The changelog claims a smoother edge-shift scatter of a small T
   (2.95 -> 1.47 K), which is a different case (shifted straight edge on a T); the turned-square case in the 3D solid was not mentioned. The cut-cell copy
   (the research proposal P1) is unaffected and stays within 0.8 K (README 9.4a says its columns move with C8).

#### 3.2 point-via-convergence

All the prototype treatments (peaceman, area, tuned, mw_*) print the README numbers to the digit: 4.1 unit cell 12 cases, 4.2 board (FVM and FDM), 4.4 lone via and row, 4.3
example board treatments, the fine sweep (`mw_disc@eta` -4.42 to -4.51 K, FVM -4.46 to -4.50), `study_reference_3d` (3D against layered: +0.06 / -0.66 / -1.06 %, ...),
`study_target_radius` (spot check of the ranges). The columns that run "the program" moved because the program now IS the adopted treatment (the README's last section
says so: "the columns that run the unpatched program now run the adopted treatment and move").

| README section | README value | now | item | status |
| :-- | :-- | :-- | :-- | :-- |
| 4.1 worst error of the via effect, program | 7.3 / 9.7 / 20.1 % at 1 / 0.5 / <= 0.25 mm | 0.7 / 0.5 / 0.4 % (= mw_disc@eta) | PV | EXPLAINED |
| 4.1 selected: p 4, 0.3 mm copper, program, 0.0625 mm | -10.8 % | -0.1 % | PV | EXPLAINED |
| 4.2 FVM program, open / gain at 1, 0.5, 0.25, 0.125, 0.0625 mm | 40.39 / -4.78 ... 41.65 / -3.34 | 40.52 / -4.50, 40.50 / -4.47, 40.48 / -4.49 (x3) | PV | EXPLAINED |
| 4.2 FDM program | 40.59 / -4.63 ... 41.63 / -3.34 | 40.41 / -4.42, 40.49 / -4.51, 40.48 / -4.49 (x3) | PV | EXPLAINED |
| 4.3 example board FVM program, 2 to 0.125 mm | 85.34 / -4.91 ... 86.17 / -3.29 | 85.07 / -3.70, 85.23 / -4.14, 85.18 / -4.19, 85.16 / -4.20, 85.15 / -4.21 | PV | EXPLAINED |
| 4.3 FDM program, 2 to 0.25 mm | 84.66 / -4.89 ... 85.67 / -3.68 | 84.27 / -3.57, 85.13 / -4.15, 85.12 / -4.20, 85.13 / -4.20 | PV | EXPLAINED |
| 4.3 example board without vias | 94.36, 94.67, 94.71, 94.72 | 94.37, 94.68, 94.72, 94.73 (+0.01 K, 0.01 %) | LN (bit-level) | OK |
| 4.3 mw_disc@eta rows | 85.22 / -4.14 (FVM 1 mm) etc. | equal within 0.01 K | | OK |
| 4.4 program worst error (FVM, 1 / 0.5 / 0.25 / 0.0625-0.125 mm) | 12.7 / 25.9 / 30.6 / 41.8 % | 8.6 / 3.5 / 1.5 / 1.0 % | PV | EXPLAINED |
| 4.4 FDM program | 33.2 / 15.7 / 27.0 / 41.1 % | 4.3 / 1.4 / 0.9 / 0.9 % | PV | EXPLAINED |
| 6 3D solid, program row at 1 / 0.5 / 0.25 / 0.1667 mm | 40.42 / -4.77, 40.80 / -4.35, 41.17 / -5.65, 41.46 / -5.34 | 40.42 / -4.77, 40.67 / -4.51, 40.58 / -4.54, 40.57 / -4.42 (= tuned_eta) | PV (one footprint rule) | EXPLAINED |
| 6 rows point, area, tuned | as README | equal | | OK |
| 6 position: the program "does not change at all" | | still -4.51 / -4.51 / -4.53 / -4.51 | | OK |
| 8 edge via, program, 1 to 0.0625 mm | 3.75 ... 2.59 K; outline 8.97 ... 6.34 K | 3.62 ... 3.15 K; 8.71 ... 7.54 K | PV | EXPLAINED |
| 8 edge via, mw_disc@eta | 3.62 ... 3.15; 8.39 ... 7.52 | equal | | OK |
| 9 SOR on the 3 x 3 board "19.4 to 21.9 K low" (`study_solvers`) | SOR warns, 19.4 to 21.9 K low | SOR - direct = -0.00, no warning | PV (block SOR) | EXPLAINED |
| 8 per-via time of the footprint | 0.06 to 1.9 ms | 0.12 to 3.5 ms | load (section 1.1) | OK (noise) |

#### 3.3 sor-with-via-couplings

The studies run on the folder's own in-memory copy of the program (`lib/sorvia.py`), so they are independent of the adopted SOR: `study_variants`, `study_failure`,
`study_stiffness` and `study_review` print the README numbers to the digit (sweeps of the program's rule, lagged, block, Woodbury, SSOR-CG, the omega table, the stiffness
tables including the divergence of (a) at s = 10, the structure of K, the spectral radii, tables A, B, C of the review).

| README section | README value | now | item | status |
| :-- | :-- | :-- | :-- | :-- |
| 5 the program's example board (`study_real_board`), 8 rows | table | **not reproduced**: `IndexError` in `lib/sorvia.py` `stencil_parts` (`gzz[a] += g`) | LN: `fvm.Network.extra_links` now holds links to the interior laminate node layers (non-adjacent layers), the library assumes `(a, a+1)`; the board is the only one with partial copper | NOT RUN |
| 8.2 example board row | 2247 / 2390 / 2250 sweeps | not reproduced (same crash) | LN | NOT RUN |
| 8.2 "no-via" column, 3 x 3 array 0.5 / 0.25 mm | 4169 / 8680 sweeps | 1002 / 2070 sweeps (program's own `solve_sor`) | SO | EXPLAINED |
| 8.3 text: no vias, example board 1 mm / 3 x 3 0.25 mm, formula omega | 2247 (omega 1.9391) / 8680 | 680 (1.9671) / 2070 (1.9781) | SO | EXPLAINED |
| 8.3 Young's omega rows, 8.2 block (c) and (c') columns, part 3 (1e4 stiffness: 3610 sweeps, 8.1e-9 K) | as README | equal | | OK |

Parts 2 and 3 of `study_block_over` were run through a wrapper (`scratchpad/block_parts23.py`) since part 1 crashes before them. A run of `study_real_board` on
the commit before PV and on the commit before LN failed too (the folder's library no longer matches either program), so the table of section 5 cannot be
reproduced without updating `lib/` (research code, not the program). The SOR of the program itself is covered: `study_solvers` of point-via-convergence and
`solver_equivalence` of models-comparison show it agreeing with the direct solver to 6e-9 K on the example board.

#### 3.4 rotated-square-3d

Unchanged: aligned values everywhere, every shifted row of `study_cut_cells` (the part and the board are shifted together on the grid), the rectangle rows of
`study_regression` (bit-identical, rectangle as an outline -0.0102 K), the independent references (`study_square_reference`: the whole ladder
91.822 ... 91.351, Richardson 91.349 and 91.344 for the diamond, 91.886 and 74.226 for the 40 mm boards, all to the digit), `study_turned_part` area kept (0.9444 / 0.9740 ...),
section 7 (layered models against the axisymmetric reference, 0.01 K), section 5 (`study_disc`, program 94.89 -> 94.83, 78.11 -> 78.14, 56.16 -> 56.29 K rise, within
0.2 %), section 6 energy balance.

| README section | README value | now | item | status |
| :-- | :-- | :-- | :-- | :-- |
| 2 remeasure, h_side 10 / 100 / 1000, rows with a turned part or board | e.g. 3D both 45 105.76, cut-cell both 45 105.95, 3D both 10 at 100: 92.73, board only 45 at 1000: 77.25 | 105.62, 105.61, 93.09, 77.59 (largest move 0.37 K, 0.4 % of the rise) | PAO + C8 | EXPLAINED |
| 3 total side conductance of the 3D solid, turned 20 degrees, h 100 / 1000 / 5000 | 22.08 mW/K (0.908), 117.79 (0.699), 235.24 (0.620) | 21.55 (0.887), 114.76 (0.681), 230.39 (0.607); 7a5b0ee~1 reproduces the README exactly | C8 | EXPLAINED |
| 4 cut cells, 3D program turned 20 / 45 at 1 mm | 100.06 / 97.77 | 100.60 / 99.24 | PAO (+0.01 / +0.47), C8 (+0.53 / +1.0), see 3.1 | EXPLAINED |
| 4 cut cells, FVM turned 20 / 45 at 1 mm | 79.28 / 79.54 | 79.40 / 79.82 | C8 (62afbb8~1 = README) | EXPLAINED |
| 4 cut cells 0.5 and 0.25 mm, 3D program turned | 97.42, 96.63; 95.19, 95.26 | 97.65, 96.94; 95.46, 95.68 | PAO + C8 | EXPLAINED |
| 4 0.125 mm (`--fine`), 3D turned 20 | 93.70 | 93.87 | C8 | EXPLAINED |
| 9.2 program 3D against the continuum, turned 20 / 45 at 0.5 / 0.25 / 0.125 mm | +6.07 / +5.28; +3.85 / +3.91; +2.35 / +1.45 K | +6.31 / +5.59; +4.12 / +4.33; +2.53 / +2.02 K | PAO + C8 | EXPLAINED |
| 9.2 cut-cell copy turned 45 against the continuum | +1.14 / +0.61 / +0.26 | +0.79 / +0.44 / +0.18 (= the README's "part sampled 8 x 8" column) | C8 (README 9.4a predicts it) | EXPLAINED |
| 9.2 40 mm board, program, turned 20 (board and part), h 100 / 1000 | +1.09 / +3.41 K | +1.25 / +3.52 K | PAO + C8 | EXPLAINED |
| 9.3 turned part, program minus aligned at 0.5 / 0.25 / 0.125 mm | +0.37 / +0.23 / +0.11 K (4 x 4 sampling) | +0.02 / +0.06 / +0.03 K | C8 (3D footprint 8 x 8) | EXPLAINED |
| 6 example board cut to presets, FVM: ellipse, chamfer, rounded (h 10 / 100) | 90.75 / 86.10; 86.44 / 82.95; 86.09 / 82.69 | 90.12 / 85.53; 85.85 / 82.40; 85.50 / 82.14 (-0.55 to -0.63 K) | PV (-0.59 K, as the rectangular example) | EXPLAINED |
| 6 L preset FVM | 109.76 / 101.39 | 109.77 / 101.41 | (the vias hardly matter on the L: 109.94 without them) | OK |
| 6 T preset FVM and 3D (h 10 / 100) | FVM 109.06 / 99.70, 3D 109.31 / 100.57 | FVM 104.88 / 95.74, 3D 107.79 / 99.05 | PAO (3D -1.5 K; FVM -1.5 K, 5e93182~1 gives 107.55) then PV (FVM -2.7 K, see 3.1) | EXPLAINED |
| 9.4 small T, FVM 1 / 0.5 / 0.25 / 0.125 mm | 233.08 / 237.65 / 230.46 / 231.16 (program of 2.4.4) | 231.87 / 230.17 / 230.02 / 229.86 | PAO, C8 (the Decisions Log says a residual of 0.5 to 0.7 K stays at 1 to 0.5 mm) | EXPLAINED |
| 9.4 small T, 3D | 234.27 / 239.16 / 231.56 / 232.34 | 233.02 / 231.31 / 231.11 / 230.96 | PAO, C8 | EXPLAINED |
| 9.4 example board T at 2/3 mm, FVM | 106.85 (outline on grid lines) | 105.08 | PV (not PAO: the outline is on grid lines) | EXPLAINED |

#### 3.5 models-comparison

`docs/validation.md` section 2 (20 rows x 5 models), section 2.1 (the grid table, 4 columns x 5 spacings), the off-grid heater (`study_offgrid_heater`) and the
whole of `accuracy_study` / `stress_study` print the project document to the digit. Section 1 of the document: FVM 85.17 and FDM 85.11 at 0.5 mm read 85.18 and
85.12 (0.01 K, rounding of the 0.5 mm run); Lumped 86.63 and Analytic 85.10 are equal.

The README of the folder was written before PV, VC and LN and its tables moved (its text says "re-run on 0ea5f07"); `docs/validation.md` already carries the new numbers.

| README section | README value | now | item | status |
| :-- | :-- | :-- | :-- | :-- |
| 4.1 / 4.2 example board, 1 mm: FVM, FDM, Lumped, Analytic | 85.81, 84.38, 84.66, 84.65 | 85.23, 85.13, 86.63, 85.10 | PV (FVM, FDM), VC (Lumped, Analytic) | EXPLAINED |
| 4.2 rows with vias (example, no heatsink, top copper full, only U1) | FVM 88.91, 85.29, 79.97; Lumped 87.60, 84.14, 77.82 | 88.30, 84.72, 79.39; 89.52, 86.10, 79.79 | PV, VC | EXPLAINED |
| 4.2 rows with copper absent next to the heater: straddling the edge; no copper on the heater layer; hatched 0.5 | FVM 143.89, 150.16, 105.78; FDM 139.77, 150.14 | 146.64, 152.36, 106.17; 142.45, 152.35 | LN (changelog: 143.89 -> 146.64 board field, 148.98 face) | EXPLAINED |
| 4.2 input check of "5 mm inside the edge" and "island" | "-" | warns | `fix/model-limit-warnings` (changelog "Warnings of the limits") | EXPLAINED |
| 4.2.1 grid, FVM at 4 / 2 / 1 / 0.5 / 0.25 mm | 83.00, 85.34, 85.81, 85.87, 85.95 | 83.53, 85.07, 85.23, 85.18, 85.16 (= docs 2.1) | PV | EXPLAINED |
| 4.2.1 FDM area / classic | 82.29 ... 85.67 / 85.36 ... 85.80 | 83.80 ... 85.13 / 86.69 ... 85.27 | PV | EXPLAINED |
| 4.4 solver table: sweeps 656, 3247, 2247, 2237, 1391 | | 306, 673, 676, 779, 636 | SO (docs 5 says 306, 673, 810, 779, 636) | EXPLAINED |
| 4.4 example board direct / SOR sweeps / max diff | 85.8143 / 2247 / 1.1e-8 | 85.2335 / 676 / 6.3e-9 | PV (temperature), SO + LN (sweeps: the SOR relaxes plan columns as blocks) | EXPLAINED |
| 4.5 "new" rows | 85.81, 84.38, 84.66, 84.65 | as 4.1 | PV, VC | EXPLAINED |
| 4.6 exact check of the integrator | Euler 3.06 / 1.67 / 0.875 / 0.448, CN 0.315 / 0.0772 / 0.0192 / 0.00479, energy within 0.01 % | script prints 1.57 / 1 / 1.39 / 1.58, 2.52 / 1.8 / 1.78 / 1.78, +5.38 % | **the script is stale**: it sets `laminate.LAMINATE_NODES = 0` only, while `tests/test_fvm.py` also sets `laminate.uses_rule = lambda p: False` (LN); with that line (`scratchpad/exact.py`) the script prints the README to the digit (3.06 / 1.67 / 0.875 / 0.448; 0.315 ... 0.00479; -0.01 %) | EXPLAINED (script to update) |
| 4.6 FVM against FDM animation, 2 mm | FVM 25.0 ... 77.0, FDM ... 76.3, largest diff 0.69 K, steady 85.34 / 84.66 | FVM ... 76.7, FDM ... 75.9, 0.81 K, steady 85.07 / 84.27 | PV | EXPLAINED |
| 4.6 FVM against Analytic, 1 mm | largest 2.2 K, 63 % at 19.2 s | 1.18 K, 19.9 s (Analytic 76.0 -> 76.4 at 120 s) | PV, VC | EXPLAINED |
| 4.6 profiles, 1 mm: steady at the average power FVM / Analytic / Lumped; bound | 85.8 / 84.8 / 84.7; 231.6 | 85.2 / 85.3 / 86.6; 229.8 | PV, VC | EXPLAINED |
| 4.6 CSV example: peak FVM / Lumped / Analytic; bound | 119.5 / 116.1 / 115.1; 201.6 | 117.7 / 121.5 / 116.3; 199.7 | PV, VC | EXPLAINED |
| 4.7 computed h, FVM 1 mm, typed / computed at 0.55 ... 22 W | 31.1 ... 268.3 / 31.9 ... 245.3 | 31.0 ... 265.9 / 31.8 ... 242.9 (differences -5.4 and -23.0 K unchanged) | PV (scales with the power) | EXPLAINED |
| 4.8 nine boards, error against the 3D solid (only the "after" column can be run): example board FVM / FDM / Lumped / Analytic | -0.3 / -2.6 / -2.2 / -2.2 % | -1.2 / -1.4 / +1.1 / -1.4 % | PV, VC | EXPLAINED |
| 4.8 one-layer boards, FVM (LED strip, 20 mm pad, full copper 3.2 mm) | -2.0, -3.5, -0.3 % | -1.2, -2.0, -1.0 % | LN (one-layer rule; changelog 10 mm pad -4.08 -> -1.80 %) | EXPLAINED |
| 4.8 independent check (FVM against the independent solver, isotropic boards) | -0.0, -1.7, -1.7 %; FDM -0.1, -8.1, -11.5 | -0.2, -0.8, -0.4 %; -0.2, -7.9, -11.2 | LN | EXPLAINED |
| 4.9 coupon, 10 / 20 / 40 rings; example board "now" | +0.2 to +0.4 %; -1.9 / -2.6 / -2.5 % | same; +2.3 / +1.6 / +1.7 % | VC, PV (example) | OK / EXPLAINED |
| 4.1 table of the finite-element solid (`validation_study.py --fem`) | | not run (scikit-fem is not in requirements) | | NOT RUN |
| 4.8 "before" column (a worktree of 1ffb4ef) | | not run (reproduces the old program, not the tree under test) | | NOT RUN |
| docs/validation.md section 5, example board row | 85.2249, 3.5e-09, 810 sweeps, "agree to 4e-9 K" | 85.2335, 6.3e-09, 676 sweeps | LN (the commit before LN, e9f4df2~1, prints 85.2249 and 810 exactly) | EXPLAINED (the document row is stale) |
| docs/validation.md section 5, the other four boards | | equal in temperatures and sweeps | | OK |

### 4. How the items were found (git archive copies)

Copies of `pcbthermal/` at the commit before each item, in new directories under the scratchpad, with the current `research/` folder on top; the script was run in
the copy. All printed the README (or the intermediate) value where the item predicts it:

| copy | script | what it showed |
| :-- | :-- | :-- |
| 62afbb8~1 (before PAO) | rotated `study_cut_cells` | turned rows equal to the README (79.28, 100.06, 97.77 ...) |
| 7a5b0ee~1 (after PAO, before C8) | rotated `study_cut_cells`, `study_edge_conductance` | 3D turned 45 at 1 mm 98.24 (PAO +0.47 K); edge conductance equal to the README (22.08, 117.79) |
| 5e93182~1 (before PV) | example board cut to the T, FVM 1 and 2/3 mm | 107.55 and 106.85 (README 107.56, 106.85); with only the 7 on-board vias 108.39 |
| e9f4df2~1 (before LN) | example board T; `solver_equivalence` | T 104.87 / 105.07 (PV explains the drop from 107.55 / 106.85); example board direct 85.2249, 810 sweeps |
| f671868~1 (before VC) | `solver_equivalence` | same as e9f4df2~1 (VC changes the Lumped and Analytic only) |

The `study_part_across_outline` script cannot run on the copies (its `rotsq` library refuses to build when `fvm.py` has no unmodified heater weight line: the
copies of the research folder no longer apply, as README 9.4a says), so the T example board was run with a short script (`scratchpad/exT.py`, `viasT2.py`).

### 5. Not run, and why

* `sor-with-via-couplings/study_real_board.py` and the example-board row of `study_block_over.py` part 1: the folder's library predates the laminate nodes and crashes
  (section 3.3). The research library needs an update; the program is not at fault.
* `models-comparison` `validation_study.py --fem` (scikit-fem is not in `requirements.txt`) and the "before" column of `study_complex_boards.py` (needs a worktree of the
  old commit).
* The tests of the research folders (`pytest research/<folder>/tests`) were not run in this part: the request was the studies and the tables. (The folders'
  tests import the same libraries and `lib/sorvia.py` would be expected to fail on a laminate board.)

### 6. Stale text found (for the maintainer, nothing edited)

* `docs/validation.md` section 5: example board row (85.2249, 3.5e-09, 810 sweeps) and the sentences "agree to 4e-9 K" and "in 810 sweeps"; now 85.2335, 6.3e-09, 676.
* `research/models-comparison/README.md` sections 4.1 to 4.9 carry the numbers of the program before PV, VC and LN.
* `research/models-comparison/scripts/study_time_and_coefficients.py`: add `laminate.uses_rule = lambda p: False` to the exact check, as `tests/test_fvm.py` does.
* `research/sor-with-via-couplings/lib/sorvia.py`: `stencil_parts` assumes extra links between adjacent layers.
* The `checks.py` message for a via outside the board tests only the bounding box (section 3.1, item 1).


---

## Reproduction pass for release 2.4.5, Part C

Folders of this part: outline, stackup, power-calculator, component-heatsink, block-and-fins, solid3d-verification, effective-conductivity, zone-union, plate-h-level, horizontal-plate-h, fin-channel, fin-channel-sources, theory-sources, via-real-board, laminate-nodes, young-omega-tiles, gerber-models.

Tree under test: `develop` at `0d4159f` (the 2.4.5 candidate), branch `research/reproduction-245-c`, run with `.venv/bin/python` (the shared virtual environment of the main checkout) and `.venv-research` for the Gerber studies and zone-union (shapely). The program, the tests, the examples and the project documents are untouched.

Unit of counting: one row of a README table, or one named value that a script prints. The counts are approximate (a row has several numbers; a row is "unchanged" when every number is within the folder's own tolerance, or 0.5 % when it has none).

### 1. Totals

| | rows or values |
| :-- | --: |
| Checked against a README number | about 430 |
| Unchanged (within tolerance) | about 330 |
| Moved and EXPLAINED by an item of 2.4.5 (or of 2.4.2 / 2.4.3 for stale READMEs) | about 95 |
| UNEXPLAINED | 0 |
| NOT RUN | 3 scripts that fail on the 2.4.5 program (stale research code), 1 script that never ends (node prototype), 1 long script, about 90 scripts that the pass did not list (section 6) |

Every number that moved was attributed to a commit of the version by running the same script on `git archive` copies of the tree before the suspected item (section 5). Nothing is UNEXPLAINED.

Tests of the folders (`.venv/bin/python -m pytest -q research/<folder>/tests --timeout=900 --timeout-method=thread`, one at a time; zone-union and gerber-models with `.venv-research`):

| folder | result |
| :-- | :-- |
| effective-conductivity | 14 passed (13 s) |
| plate-h-level | 15 passed (14 s) |
| horizontal-plate-h | 15 passed (29 s) |
| fin-channel | 18 passed (9 s) |
| theory-sources | 14 passed (2 s) |
| fin-channel-sources | 13 passed (1 s) |
| young-omega-tiles | 23 passed, 3 skipped (the three that install the old Analytic tile patch; the README says so) |
| zone-union | 9 passed (3 s) |
| laminate-nodes | 20 passed (5 s) |
| via-real-board | 26 passed (1 s) |
| gerber-models | 34 passed (48 s) |

Folders of this part that have no `tests/`: outline, stackup, power-calculator, component-heatsink, block-and-fins, solid3d-verification.

### 2. Commands and durations

Runner (resumable, one job at a time): `.venv/bin/python research/reproduction-245/scripts/run_all.py --python <venv python> --folders outline,stackup,power-calculator,component-heatsink,block-and-fins,solid3d-verification,zone-union,fin-channel-sources,via-real-board,laminate-nodes,young-omega-tiles,gerber-models`. (The runner expands a folder that has no script, such as effective-conductivity, into every script, so those folders were run by hand, below.)

| script | seconds | state |
| :-- | --: | :-- |
| outline: outline_rectangle_study / study_edge_on_grid_lines / study_outline_time_constant / study_disc_reference | 48 / 5 / 1 / 4 | ok |
| stackup: stackup_outline_study / study_dielectric_sensitivity / study_inner_copper_1oz | 18 / 20 / 24 | ok |
| power-calculator: calculator_validation / study_independent_datasheet_board / study_power_band | 228 / 22 / 101 | ok |
| component-heatsink: study_top_path_convergence | 1500 | **timeout**, see 4.1 |
| block-and-fins: study_finned_block_all_models / study_thick_plate_criterion / fin_validation | 2 / 2 / 0.4 | ok |
| solid3d-verification: study_one_layer_board | 57 | ok |
| zone-union: study_cost / study_cases / study_program (no argument) | 1 / 0 / 0 | failed: shapely is not in `.venv`; the studies need an argument (develop, variant, report). Re-run by hand, below |
| fin-channel-sources: study_source_checks | 8 | ok |
| via-real-board: study_validation_rows | 466 | ok |
| laminate-nodes: study_validation_rows / study_one_layer | 177 / 27 | ok |
| young-omega-tiles: study_s3_boards / study_s4_example | 113 / 34 | **failed**, see 4.3 |
| gerber-models: study_scalar_formulas / study_heater_size (with `.venv`) | 1 / 0 | failed: needs the downloaded boards and the research environment. Re-run by hand, below |

By hand, same machine, one at a time (outputs in `research/reproduction-245/out/<folder>/`, git-ignored):

| script (venv) | seconds |
| :-- | --: |
| gerber-models (`.venv-research`, `research/gerber-import/data` linked from the main checkout): study_import_end_to_end / study_scalar_formulas / study_heater_size / study_models_our_board / study_models_rect_board / study_rect_convergence | 29 / 12 / 64 / 77 / 53 / 87 |
| zone-union (`.venv-research`): study_program develop / study_cases develop / study_edge_cases / study_sampling | 66 / 4 / 1 / 20 |
| effective-conductivity: study_program_vs_coupon / study_natural_convection / study_lee_spreading / study_channel_correlations / study_one_layer_independent / study_corrections_impact / study_muzychka_2003 / study_biot_definitions | 49 / 1 / 4 / 0.1 / 45 / 8 (failed) / 13 / 124 |
| plate-h-level: study_board_effect / study_finned_block | 18 / 7 |
| horizontal-plate-h: study_board_effect / study_correlations | 29 / 1 |
| fin-channel: study_program_finned_block / study_warning_rule / study_channel_correlations / study_optimum_spacing | 11 / 0.5 / 64 / 1.5 |
| theory-sources: study_muzychka_more_cases / study_natural_convection_sources | 15 / 0.3 |
| component-heatsink: the table of study_top_path_convergence without the node prototype (a script of the pass, 8 rows) | about 4 minutes |

Bisection runs on `git archive` copies (scratchpad, new empty directories): v2.4.4 (`v2.4.4`), `7a5b0ee~1` (before the cover 8 x 8, includes the part across the outline), `5e93182~1` (before the point via), `e9f4df2~1` (before the laminate rule, includes point via, SOR and via constriction), and `e9f4df2` itself.

The load average was 3 to 27 during the pass (two other testers were running); no job of this part failed because of a timeout caused by load.

### 3. Moved numbers (EXPLAINED)

Items of 2.4.5 (`CHANGELOG.md` Unreleased): part across the outline `62afbb8`, cover 8 x 8 `7a5b0ee`, point via `5e93182` (FVM, FDM, 3D solid; block SOR), via constriction `f671868` (Lumped, Analytic), laminate rule `e9f4df2` (patterned copper, one-layer boards). Older items that the README of a folder predates: finned block sides (2.4.2), zone union (2.4.3).

| folder | README section | README value | now | 2.4.5 item that explains it | status |
| :-- | :-- | :-- | :-- | :-- | :-- |
| outline | 4.2 T, example | FVM 109.1 degC; same-area -17.8 / -16.0 % | 104.9; -11.4 / -12.0 | part across the outline: 109.1 -> 107.6 (archive `7a5b0ee~1`); point via: 107.6 -> 104.9 (archive `e9f4df2~1` reads 104.9) | EXPLAINED |
| outline | 4.2 ellipse, chamfer, rounded: example | 90.8 / 86.4 / 86.1; box -9.3 / -2.9 / -2.3 | 90.1 / 85.9 / 85.5; box -5.4 / +1.3 / +1.9 | point via (the example board has vias): archive `5e93182~1` still prints the README, `e9f4df2~1` prints the new values | EXPLAINED |
| outline | 4.2 near the edge (ellipse, L, chamfer, rounded) | 119.7 / 115.6 / 112.6 / 112.0 | 120.0 / 116.0 / 112.9 / 112.4 (+0.3 to +0.4 K, error columns 0.3 points) | laminate rule: the four rows are identical in `e9f4df2~1`, move only at `e9f4df2` | EXPLAINED |
| outline | 4.2 T centre, L, ellipse off-centre, chamfer/rounded off-centre and centre | within 0.2 points | unchanged | | OK |
| outline | 4.4, 4.5 (time constants, disc against the radial solution, 600 s mean) | 107.0 s, 108.10 s, 30.452 K/W, 15.548 K | identical, 30.471 K/W (0.06 %), 15.553 K | | OK |
| outline | 4.6 slice lost by the old rule (a local copy `edge_before`) | disc 3.1 / 3.3 %, ellipse 0.7 %, square 2.2 % | 1.6 / 2.1 / 0.0 / 0.1 % | the cover is sampled 8 x 8, so fewer cells are taken as off the board and the local copy of the old rule loses less; the counted edge, 240 mm and 187.8 mm, and the temperatures (93.009, 92.944, 93.393 degC) are identical | EXPLAINED |
| stackup | 4.1 A (all eight rows) | FVM 80.7 K; FDM -4.1, 3D -1.5, Lumped -3.2, Analytic +7.7 % | 78.9; -1.2, +0.8, +1.2, +3.5 % | `5e93182~1` prints the README to the digit; `e9f4df2~1` prints 78.9, Lumped +1.3, Analytic +3.6: point via (FVM/FDM/3D) and via constriction (Lumped, Analytic) | EXPLAINED |
| stackup | 4.2 C base rise | 84.5 K | 83.1 K (the percent changes move at most 0.2 points) | point via (same bisection) | EXPLAINED |
| stackup | 4.4 one-layer 20 mm pad; 4 layers with 9 vias | 216.1 K; 87.2 K | 219.0 K; 85.8 K | laminate rule (v2.4.4 prints 216.1); point via | EXPLAINED |
| stackup | 4.5 Tmax of the shipped templates | 90.40, 84.80, 79.72, 78.76, 78.22 degC (100.99 for 2 layers) | 90.05, 84.43, 79.35, 78.37, 77.83 (100.77) | point via (the example board has vias; this script was not run on the archives, the attribution is by the same board in the stackup_outline_study bisection); the differences between variants move at most 0.15 K | EXPLAINED |
| power-calculator | 4.1 CSD17308Q3 | 46.8 K/W, 0.983 W, -1.7 % | 47.5 K/W, 0.968 W, -3.2 % | laminate rule (the CHANGELOG states 0.983 -> 0.968 W) | EXPLAINED |
| power-calculator | 4.1 JEDEC 2s2p with vias; without vias | 31.6 K/W, 1.030 W, +3.0 %; 68.1 K/W | 31.3, 1.039 W, +3.9 %; 71.0 | laminate rule and point via (the no-vias row is cell-sensitive: 84 to 68 K/W in the README) | EXPLAINED |
| power-calculator | 4.6 FVM two layers / one layer; program's FR-4 | 47.74 / 48.23 K/W; 47.2 K/W RthetaJA | 48.54 / 48.53; 47.9 | laminate rule: the bare bottom of the two-layer drawing now gets laminate nodes, so the two drawings agree (-0.7 % both against the independent 3D solver) | EXPLAINED |
| power-calculator | 4.6 independent solver, 3D solid, affine test (+1.4, -6.0, -14.4 K) | 48.89, 48.95; +1.45, -6.03, -14.56 | identical | | OK |
| power-calculator | 4.7 band, ring and top of the package | 2.00 / 1.62 / 2.31 W; 2.00 / 1.69 / 2.27 W | ring identical; top best 1.68 (the README says "reproduced to the last digit") | point via, SOR and constriction batch (archive `e9f4df2~1` prints 1.68; `5e93182~1` and v2.4.4 print 1.69) | EXPLAINED |
| power-calculator | 4.7 drawn board that differs from the real one | hatched 1.735 / 1.474 / 1.956; no vias 1.780 / 1.505 / 2.014, **2 W inside: yes**; no planes 1.312 | hatched 1.686 / 1.445 / 1.885; no vias 1.766 / 1.493 / 1.998, **inside: no (by 0.002 W)**; no planes 1.297 | no vias and no planes move with the point-via batch (archive `e9f4df2~1` prints 1.766 / 1.998 / 1.301); the hatched row moves again with the laminate rule (1.738 -> 1.686). **The sentence "missing vias are inside at every level" and the count in README 4.7 / `docs/calculators.md` 1.1c need to be read again**; the model is not wrong, the margin was 0.012 W | EXPLAINED (a README conclusion changes) |
| component-heatsink | 4.11 (corrected program) Tj, 8 mm pad: MOSFET, LDO, Buck, Schottky | 90.9, 69.8, 59.4, 50.1 degC | 92.1, 70.6, 60.2, 50.7 (+0.6 to +1.2 K) | laminate rule: archive `e9f4df2~1` prints the README to 0.1 K. The claim "program equals exact root, settled, 1 iteration" holds on all 8 rows | EXPLAINED |
| component-heatsink | 4.11, 25 mm pad | 69.8, 56.7, 47.8, 43.7 | 70.3, 57.0, 48.0, 43.9 | laminate rule | EXPLAINED |
| block-and-fins | 4.1 finned block rise, FVM / FDM / 3D / Lumped / Analytic | 61.2 / 61.2 / 61.7 / 62.7 / 62.1 (fins 15, pitch 8); 66.4 and 53.2 (FVM) | 65.0 / 65.0 / 65.5 / 66.5 / 66.1; 70.0; 56.6 | side walls of a finned block no longer carry the fin ratio (2.4.2, `fix/finned-block-sides`; the README table predates it and its own section on the sides shows 61.2 -> 65.0). Not a 2.4.5 item | EXPLAINED |
| block-and-fins | 4.4 plain plate 88.3, thick-plate bound 0.07 / 0.34 / 0.50 / 1.78 %, 8 to 21 %, fin_validation 24 rows within 0.08 % | | identical | | OK |
| solid3d-verification | 4.4 one-layer board, full copper, FVM / FDM | 57.35 / 57.35 | 57.27 / 57.28 | laminate rule | EXPLAINED |
| solid3d-verification | 4.4 one-layer board, 20 mm pad, FVM / FDM | 79.94 / 76.49; -2.5 % against the independent solver | 80.81 / 76.78; -1.4 % | laminate rule (the CHANGELOG gives -4.08 -> -1.80 % for a 10 mm pad) | EXPLAINED |
| effective-conductivity | 4.11 one-layer 20 mm pad, FVM / FDM against the independent solver | 70.32 (-2.5 %) / 66.76 (-7.4 %) | 71.09 (-1.4 %) / 67.14 (-6.9 %) | laminate rule | EXPLAINED |
| zone-union | 4.2 (the old-rule column of the README is gone from the program) | one zone 143.08 / 143.08 / 144.42 / 142.22 / 143.14 K | 142.96 / 142.96 / 144.42 / 142.22 / 143.14; 40 strips now equal the one-zone value in all five models, overlapping pair of fill 0.5 = one zone of fill 0.5 (156.05), partly overlapping 149.52 / 149.07 | the union rule is in the program since 2.4.3, so the "program as it is" run prints the "per-point union" column of the README (0.1 %) | EXPLAINED |
| zone-union | 8.1 example boards, 1 mm: FVM / FDM / Lumped / Analytic / 3D | 60.814 / 59.383 / 59.659 / 59.652 / 60.975 | 60.234 / 60.126 / 61.628 / 60.102 / 60.975 | point via (FVM, FDM), via constriction (Lumped, Analytic); the 3D solid and the reference board are unchanged | EXPLAINED |
| plate-h-level | 7 example_board, vertical, general form | 61.3 K | 60.97 K | point via | EXPLAINED |
| horizontal-plate-h | study_board_effect example_board, program | 60.36 K | 60.06 K | point via (the other 14 cases print the README digits) | EXPLAINED |
| gerber-models | 4.31 Stormduino (program as it is, faces binary / coverage, lambda binary / coverage) | -15.1, -2.1, -5.3, -2.1, -5.1 % | -14.3, -1.7, -4.9, -1.8, -4.8 % | laminate rule (identical in `e9f4df2~1`; the 4.31 note says "unchanged" because it was re-run before the rule). Not in the executor's list of moved numbers, but the shift is the rule's | EXPLAINED |
| gerber-models | 4.31 our IC board | -4.8, +7.3, +5.2, +11.0, +10.0 % | -2.4, +7.3, +5.2, +11.0, +10.0 % | laminate rule; **confirms the "Update for the program of 2.4.5"** (-4.8 to -2.4, faces unchanged) | OK (confirmed) |
| gerber-models | 4.35 and 4.37 (rectangle board) | FDM 0.25 mm against FVM 0.1 mm -4.13 % / -2.87 %; FVM 1 mm +1.35 % / -6.9 %; 3D solid +8.5 %; Lumped -15.9 %; Analytic -26.4 % (shift 0.4 / 0) | -4.90 / -3.23 %; +2.2 % / -8.3 %; 3D +3.2 %; Lumped -20.0 %; Analytic -30.1 % | **confirms the Update** (-4.90 / -3.23, +2.20 / -8.3, +3.0 -> 3.2, -20.2 -> -20.0, -30.2 -> -30.1; the executor's 3D +3.0 is 3.2 here, 0.2 points) | OK (confirmed) |
| gerber-models | 4.37 table of the mean rise by cell: FVM 2 mm / 1 mm / 0.5 / 0.25 / 0.1 | 94.90 / 99.32 / 98.43 / 98.12 / 98.00 | 98.11 / 105.47 / 103.93 / 103.40 / 103.20 (FDM 83.45 -> 82.92 at 2 mm, 96.97 -> 101.91 at 0.1 mm) | laminate rule (the board has copper-free cells round the pads). The 3D solid column differs at 2 mm only (101.78 -> 100.50): v2.4.4 already prints 100.50, so the README line was older than 2.4.4 | EXPLAINED |
| gerber-models | 4.34 our board in the five models, fine mask / arithmetic fill, FVM and FDM | 130.5 / 124.3 and 123.0 / 110.8 K | 134.7 / 128.5 and 126.9 / 112.6 | laminate rule (one-layer board). **4.34 is not in the Update's list** (the Update lists 4.31, 4.35, 4.37): Lumped, Analytic and 3D solid are unchanged (115.9, 97.6, 131.5) | EXPLAINED (Update list incomplete) |
| gerber-models | 4.35 table: zones 0.1 mm, FVM / FDM; one layer | 98.0 / 96.9; 101.2 / 100.0 | 103.2 / 101.9; 103.7 / 102.3 | laminate rule | EXPLAINED |
| gerber-models | 4.5 scalar formulas (7 rows), 4.8 heater size (9 rows) | | identical | | OK |

### 4. Scripts that did not run, and why

#### 4.1 component-heatsink: study_top_path_convergence.py (timeout, 1500 s)

The runner printed the header and no row in 1500 s (the README says about 2 to 4 minutes). Cause, found by a probe in the scratchpad: the node prototype of the study (`package_prototype.solve`, `model="node"`) builds its own matrix from `fvm.Network` internals (`net.K`, `net._assemble()`, `net.Qw[0]`, `g_top`, `g_amb`) and adds a junction unknown; since the laminate rule (`e9f4df2`) the matrix is "exactly singular" and `scipy.sparse.linalg.spsolve` with `permc_spec="MMD_AT_PLUS_A"` does not return (a thread dump after 150 s sits in `spsolve`). Archives: v2.4.4, `7a5b0ee~1`, `5e93182~1` and `e9f4df2~1` run the prototype in 0.6 s and print 90.68 degC; `e9f4df2` hangs. So it is the research prototype that breaks on the new network, not the program: the program's own top-path solve works (first board solve 18 s at 0.5 mm, then about 1.4 s per solve; the 8 rows of 4.11 in about 4 minutes against 4 s per row before the rule, a cost of about 7 times). The 8 rows were printed by a script of the pass that leaves out the node prototype (table in section 3). **Not run: the node-prototype column (8 values).** The executor has to adapt `package_prototype.py` to the network (or the study to the new `Network`); the program is not at fault.

#### 4.2 effective-conductivity: study_corrections_impact.py (failed, 8 s)

`TypeError: laminar_patch.<locals>.patched() takes 3 positional arguments but 4 were given`: the study replaces `convection.h_natural_vertical` by a function of three arguments, and `board_h` has passed the form (`natural_form`) as a fourth argument since 2.4.2. Not a 2.4.5 item; the study has been stale since 2.4.2. Not run: the plate check against the cell size, the laminar form on the program, the thick-plate criterion on the 74 cases (the last is also printed by `block-and-fins/study_thick_plate_criterion.py`, which agrees with the README). `study_culham_1998.py` (about 15 minutes by the README, over the limit of 10) was not run.

#### 4.3 young-omega-tiles: study_s3_boards.py and study_s4_example.py (failed)

`study_s3_boards.py`: `IndexError` in `research/sor-with-via-couplings/lib/sorvia.py` `stencil_parts` (`gzz[a] += g`, "the program assumes (a, a + 1)", which the laminate gap nodes break). `study_s4_example.py`: `RuntimeError: line not found in analytic.solve_steady` (the tile patch rewrites lines of the old Analytic that the via constriction replaced). The README of the folder says the same ("the numbers of the README are those of the program before these changes and were not re-run"; three tests skipped). Not run; the folder's 23 tests pass.

#### 4.4 Folders whose studies compare a patch with the program

* via-real-board `study_validation_rows.py` re-ran sections 2, 2.1 and 18 of `docs/validation.md` twice, on the program and inside the patch: "(0 cells moved by more than 0.05)" in all three, because the patch is now the program. This confirms that the adopted program equals the proposal on those tables; it is not a comparison with a README number. Counted as 3 OK.
* laminate-nodes `study_validation_rows.py` prints "FVM program" (old rule, kept in the lib) against "FVM rule" for 22 boards: 143.89 -> 148.98 K for the heater straddling the copper edge, 150.16 -> 154.70 without copper under the heater, 105.78 -> 107.34 hatched; all other boards 0.00 to 0.05 K, the example board 85.22 -> 85.23. These are the numbers the CHANGELOG quotes; the FDM and Lumped columns print `n/a` and `TypeError` (the lib's Lumped hook no longer fits the program). `study_one_layer.py` prints the one-layer table with -4.08 -> -1.80 % for the 10 mm pad (the CHANGELOG's numbers), 12 rows. Counted as consistent with the CHANGELOG, not as an independent confirmation.
* zone-union: the `variant` mode applies the zone-union patch to a copy of a program that already has it, so only `develop` mode was run; `study_cost.py` (reads the `variant` output) and `study_real_board.py` (needs the fetched Stormduino) were not run.

### 5. Bisection used for the EXPLAINED rows

| script | v2.4.4 | `7a5b0ee~1` | `5e93182~1` | `e9f4df2~1` | now |
| :-- | :-- | :-- | :-- | :-- | :-- |
| outline_rectangle_study, T example | 109.1 (README) | 107.6 | 107.6 | 104.9 | 104.9 |
| outline_rectangle_study, ellipse example | 90.8 | 90.8 | 90.8 | 90.1 | 90.1 |
| outline_rectangle_study, ellipse near the edge | 119.7 | 119.7 | 119.7 | 119.7 | 120.0 |
| stackup_outline_study, FVM simple stack-up (K) | 80.7 (README) | | 80.7 | 78.9 | 78.9 |
| study_power_band, no vias worst case (W) | 2.014 | | 2.014 | 1.998 | 1.998 |
| study_power_band, hatched worst case (W) | 1.956 | | 1.956 | 1.959 | 1.885 |
| top path, MOSFET 8 mm, Tj (degC) | 90.9 (README) | | | 90.9 | 92.1 |
| study_import_end_to_end, Stormduino today (%) | | | -15.1 | -15.1 | -14.3 |
| study_rect_convergence, FVM 2 mm, shift 0 (K) | 93.83 | 93.83 (3D 100.50) | | | 98.11 |

(The `e9f4df2~1` column is the tree just before the laminate rule, so the move between that column and "now" is the rule; between `5e93182~1` and `e9f4df2~1` it is the point-via, SOR and constriction batch.)

### 6. Not listed in this pass

The runner's JOBS list of the first tester, and this part's hand-run list, leave out the scripts that do not print program numbers affected by 2.4.5 or that the READMEs rate long. Not run by this part, with the reason: outline `make_*`; stackup `stackup_vendor_check.py`, `study_real_1oz_stackups.py` (fabricator tables, no program); power-calculator `calculator_calibration_study.py`, `power_from_top_study.py`, `study_cell_size.py` (about 8 minutes, but outside the JOBS list), `study_design_term_coverage.py` (about 6 minutes); component-heatsink the other nine studies (prototype-based, see 4.1, or sweeps over parts); block-and-fins `block_equivalent_study.py` (74 cases, long), `study_why_coefficients_fail.py`; solid3d-verification eight other studies (FEM, GCI and cost studies; `study_solve_cost.py` is memory-heavy on a loaded machine); effective-conductivity `study_culham_1998.py`; zone-union `study_strips.py`, `study_cost.py`, `study_real_board.py`; plate-h-level `study_plate2d.py` (10 to 30 minutes per case), `study_similarity.py`, `study_air_data.py` (no program); horizontal-plate-h `study_plate_h2d.py`, `study_solver_checks.py`, `print_tables.py` (the solver, long, no program); fin-channel-sources `study_review_checks.py`; theory-sources eight literature scripts that do not call the program (`study_muzychka_more_cases.py` and `study_natural_convection_sources.py` were run); via-real-board the other thirteen studies (several GB, hours; the README says they were not re-run for the adoption); laminate-nodes eighteen further studies; young-omega-tiles seven further studies (patch-based, see 4.3); gerber-models `study_models_self.py` (needs a patched copy, 20 minutes), `study_diagonal_heldout.py` (30 minutes) and twenty-three other studies. Whether a study that is not listed would show a 2.4.5 shift is not known.

### 7. Points for the maintainer

1. No UNEXPLAINED number. Every moved number belongs to the laminate rule, the point via / constriction batch, or the part across the outline, and was located by running the script on the tree before the item.
2. Two README conclusions change with the numbers and should be re-read: power-calculator 4.7 (the true 2 W is now just outside the band for the board without vias, by 0.002 W; the README says inside) and the "reproduced to the last digit" sentences of 4.7; component-heatsink 4.11 (Tj of the 8 mm pads +0.6 to +1.2 K; the claim of the section, program equals the exact root, holds).
3. The "Update for the program of 2.4.5" of gerber-models is confirmed for 4.31, 4.35, 4.37 (one 0.2-point difference on the 3D solid), but the 4.34 table (FVM, FDM) and the Stormduino row of 4.31 also moved and are not in its list.
4. Research code that no longer runs on the 2.4.5 network: component-heatsink `package_prototype.py` (hangs in `spsolve`, no error), effective-conductivity `study_corrections_impact.py` (stale since 2.4.2), young-omega-tiles `study_s3_boards.py` and `study_s4_example.py`. A hang with no message is the worst case; the executor should make `package_prototype.solve` fail (or adapt it) before the next reproduction pass.
5. Cost of the laminate rule seen in passing: the top-path board at 0.5 mm went from about 4 s to about 30 s per row (7 times), the first solve of the Power Calculator style board takes 18 s; the CHANGELOG says 2.5 times the unknowns on a 2-layer board, so the time grows faster than the unknowns here.
6. Environment notes: the worktree has no `.venv`, so the shared `.venv` of the main checkout was used; zone-union and the Gerber studies need `.venv-research` (shapely); the Gerber boards come from `research/gerber-import/data` of the main checkout (a symlink was made in the worktree and is not committed); `timeout` does not exist on this macOS, so the time limits come from the runner.

