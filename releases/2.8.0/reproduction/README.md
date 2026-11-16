# Reproduction pass of 2.8.0: result

Step 4 of the release gate (`releases/2.8.0/RELEASE_GATE.md` section 4): the studies of every research folder that imports the program, run on the tree under test and on the package of the previous release `v2.7.1`, the outputs compared (times, paths and report text ignored), every shift linked to an item of `REFREEZE_PLAN.md`. Tree: `development` 232ba648 (the program is the one of 77ed4822: the later merges are documents). Branch `release/2.8.0-reproduction`; the program, tests, examples and icon are untouched (`git diff development...release/2.8.0-reproduction --stat -- pcbthermal tests examples ico` is empty). Four testers: part A (this file's author, `PART-A.md`), B (`PART-B.md`), C (`PART-C.md`), D (`PART-D.md`); detail, raw numbers and the table of every script are in those files.

## 1. Totals (scripts of the studies; `make_figures` / `make_diagrams` not run in any part: they would overwrite the committed figures)

| part | folders | scripts | unchanged | explained | checked without a v2.7.1 baseline | not run | UNEXPLAINED |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| A | 17 | 134 | 30 | 40 | 6 | 58 | 0 |
| B | 17 | 107 on the tree; 34 compared | 24 | 9 (7 + the 2 'to confirm' of the part, explained by `LUMPED_SHIFTS_REVIEW.md`) | 0 | 58 not comparable + about 30 whose v2.7.1 twin had not finished when the part was written | 0 (proven) |
| C | 18 | 122 | 47 (45 + 2 noise) | 32 | 8 | 35 | 0 |
| D | 18 | 121 | 26 | 23 | 18 | 54 | 0 |
| **A to D** | **70** | **484** | **127** | **104** | **32** | **205 and about 30 open in B** | **0** |

Research tests (`research/<folder>/tests`, never the whole battery): 70 folders; all pass except the stale ones listed in section 4 (`lumped-via-groups` 7, `point-via-convergence` 3 (also failing on v2.7.1), `lumped-analytic-vias` 6 (2 also on v2.7.1), `lumped-near-edge` 4, `lumped-ring-uniform-deficit` 1, `lumped-zones-adoption` 3 (fixed on `release/2.8.0-lumped-shifts`)). `tests/test_docs.py`, `tests/test_license_header.py` and `research/theory/tests` are part of the battery of step 6 and were not rerun here (`research/theory/tests`: 5 passed in part D).

**Explained shifts, by item** (every row has its folder and script in the part files): M1 (face film half copper: every FVM, FDM, Analytic number by 1e-5 to 1e-3 K; 0.04 K on the finned block; +0.93 K on the 10 mm plate of `muzychka-case2-analytic`, the value the item table gives; +0.04 % on a via array resistance; +0.3 to +0.9 points on the FVM resistance of a via unit cell with h = 1e7), M2 (drawn copper faces: FVM +1.0 K on `example_cut_to_T` at 2 mm, +5.9 K FVM and +12.2 K FDM on the rectangle of `gerber-models/study_rect_convergence` at 2 mm, shrinking with the cell; FDM of the example board +0.10 K at 2 mm; the studies that compared the program with the drawn-face candidate now show the candidate equal to the program), M3 (every Lumped column: board maximum -3.1 to +3.1 % of the rise on the frozen boards, up to +7.5 % outside them, parts up to 14.9 K; the two shifts that exceeded the item table, `copper_dissipation` +22 % of a one-ring study call and the calculator row without vias +12 %, are reviewed in `LUMPED_SHIFTS_REVIEW.md`: legitimate effects of the first-link merge, not defects), M4 (Analytic finned block +0.09 K), the memory-guard law (estimates, 0.05 %), report names and wording. No FVM, FDM, 3D solid or Analytic number moved outside these items.

## 2. Table per research folder

Columns: scripts per class (u = unchanged, e = explained, nb = checked without a v2.7.1 baseline, nr = not run) as in the part file; the items that explain the shifts. Parts B and C keep their own counting in their files (B: comparison partial).

| folder | part | research tests | u | e | nb | nr | items |
| :-- | :-- | :-- | --: | --: | --: | --: | :-- |
| analytic-edge-and-transient | C | 9 passed | 4 | 3 | 0 | 0 | see PART-C.md |
| analytic-edge-spatial | B | 19 passed in 3.67s | see PART-B.md | | | | - |
| analytic-partial-copper | A | 12 passed in 7.72s | 0 | 0 | 1 | 4 | - |
| bare-spot-under-source | A | 12 passed in 63.27s (0:01:03) | 3 | 1 | 0 | 4 | M1 |
| block-and-fins | A | no tests dir | 1 | 3 | 0 | 1 | M1, M3, M3 + M1, M4 |
| block-warning-remeasure | A | 2 passed in 0.57s | 0 | 2 | 0 | 0 | M3 |
| bom-role-and-close-hook | A | 17 passed in 0.35s | 0 | 0 | 1 | 0 | - |
| component-heatsink | C | 3 passed | 0 | 1 | 0 | 1 | see PART-C.md |
| convection-laws | C | 6 passed | 3 | 1 | 0 | 1 | see PART-C.md |
| cut-cell-links | C | 30 passed | 2 | 3 | 0 | 2 | see PART-C.md |
| drawn-copper-faces | A | 5 passed in 0.86s | 1 | 4 | 0 | 5 | M2 |
| effective-conductivity | D | 14 passed in 7.98s | 5 | 3 | 0 | 1 | M1, M3 |
| face-down-convection | C | 5 passed | 1 | 1 | 0 | 0 | see PART-C.md |
| fast-wave-oscillation | D | 13 passed in 7.43s | 3 | 0 | 0 | 5 | - |
| fdm-inset-edge | D | 11 passed in 0.99s | 0 | 0 | 0 | 3 | - |
| fem-amg-thin-layers | D | 21 passed, 1 skipped | 0 | 0 | 1 | 4 | - |
| fin-channel | B | 18 passed in 6.61s | see PART-B.md | | | | M4 (+0.09 K) with M1 |
| fin-channel-sources | D | 13 passed in 1.11s | 2 | 0 | 0 | 0 | - |
| gap-subdivision | D | 8 passed in 1.43s | 1 | 0 | 1 | 6 | - |
| gerber-cad-profiles | B | 36 passed, 1 skipped in 0.37s | see PART-B.md | | | | - |
| gerber-import | C | 49 passed, 2 skipped | 2 | 0 | 0 | 9 | see PART-C.md |
| gerber-models | A | 34 passed | 6 | 3 | 0 | 23 | M2, M3 + report names, memory law re-measured |
| gerber-nets | C | 18 passed | 2 | 0 | 0 | 2 | see PART-C.md |
| gerber-real-boards | B | 50 passed, 7 skipped in 7.27s | see PART-B.md | | | | M3 |
| horizontal-plate-h | C | 15 passed | 1 | 1 | 0 | 2 | see PART-C.md |
| imported-copper-edge-film | A | 5 passed, 1 skipped in 1.87s | 1 | 0 | 0 | 7 | - |
| imported-via-rim | B | 2 passed in 0.43s | see PART-B.md | | | | - |
| independent-fem-edge | B | 11 passed, 1 skipped in 3.50s | see PART-B.md | | | | - |
| independent-fem-extensions | C | 7 passed | 0 | 0 | 0 | 6 | see PART-C.md |
| laminate-edge-band | C | 7 passed | 3 | 1 | 0 | 4 | see PART-C.md |
| laminate-nodes | B | 20 passed in 3.65s | see PART-B.md | | | | - |
| laminate-slabs-and-local-rule | D | 7 passed in 1.18s | 5 | 2 | 0 | 1 | M1 order, M1/M2 order |
| lumped-analytic-vias | D | 6 failed, 7 passed in 10.70s | 0 | 0 | 0 | 7 | M3 |
| lumped-dense-via-group | A | 5 passed in 1.48s | 0 | 2 | 4 | 3 | M3 |
| lumped-edge-link | A | 13 passed, 25 warnings in 1.60s | 0 | 4 | 0 | 1 | M1, M3 |
| lumped-near-edge | D | 4 failed, 3 passed in 0.96s | 0 | 2 | 0 | 7 | M3 |
| lumped-ring-uniform-deficit | D | 1 failed, 5 passed in 2.22s | 1 | 0 | 9 | 5 | - |
| lumped-via-groups | A | 7 failed, 9 passed in 10.42s | 2 | 0 | 0 | 7 | M3 |
| lumped-zone-placement | B | 4 passed in 0.73s | see PART-B.md | | | | M3 |
| lumped-zones-adoption | C | 3 failed, 17 passed | 2 | 11 | 0 | 2 | see PART-C.md |
| market-fem-comparison | D | no tests dir | 1 | 0 | 0 | 0 | - |
| memory-guard | B | 59 passed in 2.24s | see PART-B.md | | | | noise |
| models-comparison | D | no tests dir | 1 | 5 | 0 | 4 | M1 order / noise, M2, M3 |
| muzychka-case2-analytic | D | 8 passed in 11.98s | 1 | 2 | 1 | 1 | GUI limits of 2.8.0, M1 |
| outline | A | no tests dir | 1 | 3 | 0 | 0 | M3, M3, M1 |
| paper-case-studies | D | 31 passed in 2.41s | 0 | 2 | 0 | 1 | M1, M3 |
| plate-h-level | C | 15 passed | 2 | 2 | 0 | 1 | see PART-C.md |
| point-via-convergence | A | 3 failed, 15 passed in 4.63s | 7 | 1 | 0 | 1 | M1, memory law |
| power-calculator | B | calculator_validation | see PART-B.md | | | | M1/M2/M3 (no-via row +12 %: see LUMPED_SHIFTS_REVIEW.md, explained M3) |
| published-cases-followup | C | 19 passed | 0 | 4 | 0 | 1 | see PART-C.md |
| readout-conventions | C | 5 passed | 0 | 0 | 0 | 0 | see PART-C.md |
| reduced-models-imported-passives | B | 9 passed in 2.32s | see PART-B.md | | | | - |
| rotated-square-3d | D | 34 passed in 2.75s | 4 | 3 | 6 | 2 | M1 order, noise |
| small-model-defects | A | 9 passed in 1.53s | 2 | 5 | 0 | 0 | M1, M2, M3 |
| solid3d-verification | B | study_one_layer_board | see PART-B.md | | | | M3 (copper_dissipation +22 % of the one-ring study call: LUMPED_SHIFTS_REVIEW.md) |
| sor-with-via-couplings | A | 15 passed, 11 warnings in 2.09s | 3 | 3 | 0 | 0 | M1 |
| stackup | A | no tests dir | 1 | 3 | 0 | 0 | M1 + M2, M3 |
| strong-edge-laminate | B | 6 passed in 1.63s | see PART-B.md | | | | - |
| theory | D | 5 passed in 0.03s | 2 | 0 | 0 | 1 | - |
| theory-sources | C | 32 passed | 18 | 3 | 0 | 0 | see PART-C.md |
| through-thickness-readout | C | 7 passed | 0 | 0 | 0 | 0 | see PART-C.md |
| transient-reference-boards | D | 8 passed in 2.10s | 0 | 0 | 0 | 3 | - |
| via-contact-geometry | A | 8 passed in 0.47s | 2 | 6 | 0 | 2 | M1, M2, M2, M3 |
| via-edge-image | B | 7 passed in 1.94s | see PART-B.md | | | | - |
| via-fill | C | no tests | 1 | 0 | 0 | 1 | see PART-C.md |
| via-partial-copper | D | 16 passed in 3.21s | 0 | 4 | 0 | 3 | M1 order, M2 |
| via-real-board | C | 26 passed | 6 | 1 | 0 | 3 | see PART-C.md |
| via-well-sheet-order | B | 2 passed in 0.46s | see PART-B.md | | | | - |
| young-omega-tiles | B | 23 passed, 3 skipped in 0.67s | see PART-B.md | | | | - |
| zone-union | B | 9 passed in 1.26s | see PART-B.md | | | | - |

## 3. Incidents

* `laminate-nodes/study_transient` (part B) reached 18 GB and was killed by the orchestrator; its v2.7.1 twin was not run. From that point part B ran with a watchdog (4 GB per process).
* `lumped-analytic-vias/study_arrays` (part D) starts a multiprocessing pool of 8 workers of about 3.5 GB (about 28 GB, swap 8.9 GB); killed by the orchestrator in both trees; the per-process watchdog did not see it (each worker below 4 GB). Afterwards the watchdog sums the whole process group and the runner refuses scripts that use a pool (`runone.py`, scratch).
* Swap pauses: swap grew to 2.36 GB (part C) and 8.9 GB (the pool above); the runs were paused or stopped by the orchestrator.
* `point-via-convergence/study_array_board` is refused by the memory guard at the cell 0.0625 mm only because of the process baseline of the study's own earlier 3D work (about 7.55 GB against 6.0 GB in the old run; 7.55 + 2.82 > 10.3 GB); the FVM/FDM law is identical in both trees (`MEMORY_GUARD_STUDY_ARRAY_BOARD.md`). Not a program change; the study needs about 7 GB.
* `analytic-partial-copper/study_review` was killed at 3.4 GB; `study_baseline` timed out in both trees (its cache is needed by two more studies).
* Stale studies and tests (documentation finding, not defects of the program): source copies of the Lumped network (`lumped-via-groups`, `lumped-analytic-vias`, `lumped-near-edge`, `lumped-ring-uniform-deficit`, `lumped-zones-adoption`, `young-omega-tiles` prototypes), `block-and-fins/study_finned_block_all_models` (a wrapper without the new `board_cover` argument), `block-and-fins/study_why_coefficients_fail` (sets the block k to 1e-6: the film now passes the half block, so the column that tests 'no lateral conduction' moved from +28.5 to +58.6 %), the pins of `point-via-convergence` and `lumped-analytic-vias` to commit f2d5c03 (already failing on v2.7.1).
* `gap-subdivision/study_real_boards` overwrites a tracked file (`research/gap-subdivision/baseline/real_boards.csv`); restored, nothing committed.

## 4. Heavy studies not run, by decision

About 205 scripts (listed by reason in the part files): timeouts at 300 s in both trees, scripts killed above 4 GB, scripts that need 4 to 28 GB or a pool, `gap-subdivision/study_validation_impact` (about 731 s per tree), the independent-FEM and Gerber studies that need data or tools outside the repository (`out/` files, `fetch_boards.py` data, shapely, skfem), and the studies that need an argument or a mode. Decision of the maintainer: low risk, because parts A, B, C and D found 0 unexplained shifts among the scripts compared, and because the same models are exercised by the whole battery and by the frozen numbers (317 at 2, 1 and 0.5 mm). Not verified here: the numbers of the heavy studies; the ones of part B still open (about 30 scripts).

## 5. Documentation edits still to do (for the maintainer agent)

1. `docs/theory.md`, memory guard limits: add the sentence 'in a script that does heavy work before the first estimate, that memory enters the base' (the guard reads the resident memory once, at the first estimate; the study of `MEMORY_GUARD_STUDY_ARRAY_BOARD.md`).
2. Mark or fix the stale studies of section 3 (their READMEs are records of their run and stay; the source copies of the Lumped network need an update or an 'obsolete since M3' note, as done for `lumped-zones-adoption`).
3. `research/gap-subdivision/scripts/study_real_boards.py`: write its output to `out/`, not to the tracked `baseline/`.
4. GUI (decision, no document): the Board dock accepts a copper thickness equal to the board thickness and the run then fails with a clear dialog; consider a limit that leaves room for the gaps.
5. The research READMEs that quote the old report table (`lumped-zone-placement`, `fdm-inset-edge`) stay as records of their run (state it in the documentation review).

## 6. Verdict

**GO for the reproduction pass.** Of the studies that ran in both trees (A 134 scripts, B 34 pairs, C 122, D 121, less those that could not run), every shift is the effect of an item of 2.8.0 (M1 to M4, the memory law, the report names), none is unexplained; the Lumped shifts that exceeded the item table were reviewed (`LUMPED_SHIFTS_REVIEW.md`) and are legitimate; the failing research tests are stale source copies or pins already failing before the version, none is a defect of the program. Conditions: the documentation edits of section 5 and the maintainer's acceptance of the heavy studies not run (section 4). Part B's comparison was committed as partial (34 pairs; about 30 scripts open): if the maintainer wants it complete, part B has to be resumed.
