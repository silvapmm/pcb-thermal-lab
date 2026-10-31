# Reproduction pass for release 2.4.5, Part C

Folders of this part: outline, stackup, power-calculator, component-heatsink, block-and-fins, solid3d-verification, effective-conductivity, zone-union, plate-h-level, horizontal-plate-h, fin-channel, fin-channel-sources, theory-sources, via-real-board, laminate-nodes, young-omega-tiles, gerber-models.

Tree under test: `develop` at `0d4159f` (the 2.4.5 candidate), branch `research/reproduction-245-c`, run with `.venv/bin/python` (the shared virtual environment of the main checkout) and `.venv-research` for the Gerber studies and zone-union (shapely). The program, the tests, the examples and the project documents are untouched.

Unit of counting: one row of a README table, or one named value that a script prints. The counts are approximate (a row has several numbers; a row is "unchanged" when every number is within the folder's own tolerance, or 0.5 % when it has none).

## 1. Totals

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

## 2. Commands and durations

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

## 3. Moved numbers (EXPLAINED)

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

## 4. Scripts that did not run, and why

### 4.1 component-heatsink: study_top_path_convergence.py (timeout, 1500 s)

The runner printed the header and no row in 1500 s (the README says about 2 to 4 minutes). Cause, found by a probe in the scratchpad: the node prototype of the study (`package_prototype.solve`, `model="node"`) builds its own matrix from `fvm.Network` internals (`net.K`, `net._assemble()`, `net.Qw[0]`, `g_top`, `g_amb`) and adds a junction unknown; since the laminate rule (`e9f4df2`) the matrix is "exactly singular" and `scipy.sparse.linalg.spsolve` with `permc_spec="MMD_AT_PLUS_A"` does not return (a thread dump after 150 s sits in `spsolve`). Archives: v2.4.4, `7a5b0ee~1`, `5e93182~1` and `e9f4df2~1` run the prototype in 0.6 s and print 90.68 degC; `e9f4df2` hangs. So it is the research prototype that breaks on the new network, not the program: the program's own top-path solve works (first board solve 18 s at 0.5 mm, then about 1.4 s per solve; the 8 rows of 4.11 in about 4 minutes against 4 s per row before the rule, a cost of about 7 times). The 8 rows were printed by a script of the pass that leaves out the node prototype (table in section 3). **Not run: the node-prototype column (8 values).** The executor has to adapt `package_prototype.py` to the network (or the study to the new `Network`); the program is not at fault.

### 4.2 effective-conductivity: study_corrections_impact.py (failed, 8 s)

`TypeError: laminar_patch.<locals>.patched() takes 3 positional arguments but 4 were given`: the study replaces `convection.h_natural_vertical` by a function of three arguments, and `board_h` has passed the form (`natural_form`) as a fourth argument since 2.4.2. Not a 2.4.5 item; the study has been stale since 2.4.2. Not run: the plate check against the cell size, the laminar form on the program, the thick-plate criterion on the 74 cases (the last is also printed by `block-and-fins/study_thick_plate_criterion.py`, which agrees with the README). `study_culham_1998.py` (about 15 minutes by the README, over the limit of 10) was not run.

### 4.3 young-omega-tiles: study_s3_boards.py and study_s4_example.py (failed)

`study_s3_boards.py`: `IndexError` in `research/sor-with-via-couplings/lib/sorvia.py` `stencil_parts` (`gzz[a] += g`, "the program assumes (a, a + 1)", which the laminate gap nodes break). `study_s4_example.py`: `RuntimeError: line not found in analytic.solve_steady` (the tile patch rewrites lines of the old Analytic that the via constriction replaced). The README of the folder says the same ("the numbers of the README are those of the program before these changes and were not re-run"; three tests skipped). Not run; the folder's 23 tests pass.

### 4.4 Folders whose studies compare a patch with the program

* via-real-board `study_validation_rows.py` re-ran sections 2, 2.1 and 18 of `docs/validation.md` twice, on the program and inside the patch: "(0 cells moved by more than 0.05)" in all three, because the patch is now the program. This confirms that the adopted program equals the proposal on those tables; it is not a comparison with a README number. Counted as 3 OK.
* laminate-nodes `study_validation_rows.py` prints "FVM program" (old rule, kept in the lib) against "FVM rule" for 22 boards: 143.89 -> 148.98 K for the heater straddling the copper edge, 150.16 -> 154.70 without copper under the heater, 105.78 -> 107.34 hatched; all other boards 0.00 to 0.05 K, the example board 85.22 -> 85.23. These are the numbers the CHANGELOG quotes; the FDM and Lumped columns print `n/a` and `TypeError` (the lib's Lumped hook no longer fits the program). `study_one_layer.py` prints the one-layer table with -4.08 -> -1.80 % for the 10 mm pad (the CHANGELOG's numbers), 12 rows. Counted as consistent with the CHANGELOG, not as an independent confirmation.
* zone-union: the `variant` mode applies the zone-union patch to a copy of a program that already has it, so only `develop` mode was run; `study_cost.py` (reads the `variant` output) and `study_real_board.py` (needs the fetched Stormduino) were not run.

## 5. Bisection used for the EXPLAINED rows

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

## 6. Not listed in this pass

The runner's JOBS list of the first tester, and this part's hand-run list, leave out the scripts that do not print program numbers affected by 2.4.5 or that the READMEs rate long. Not run by this part, with the reason: outline `make_*`; stackup `stackup_vendor_check.py`, `study_real_1oz_stackups.py` (fabricator tables, no program); power-calculator `calculator_calibration_study.py`, `power_from_top_study.py`, `study_cell_size.py` (about 8 minutes, but outside the JOBS list), `study_design_term_coverage.py` (about 6 minutes); component-heatsink the other nine studies (prototype-based, see 4.1, or sweeps over parts); block-and-fins `block_equivalent_study.py` (74 cases, long), `study_why_coefficients_fail.py`; solid3d-verification eight other studies (FEM, GCI and cost studies; `study_solve_cost.py` is memory-heavy on a loaded machine); effective-conductivity `study_culham_1998.py`; zone-union `study_strips.py`, `study_cost.py`, `study_real_board.py`; plate-h-level `study_plate2d.py` (10 to 30 minutes per case), `study_similarity.py`, `study_air_data.py` (no program); horizontal-plate-h `study_plate_h2d.py`, `study_solver_checks.py`, `print_tables.py` (the solver, long, no program); fin-channel-sources `study_review_checks.py`; theory-sources eight literature scripts that do not call the program (`study_muzychka_more_cases.py` and `study_natural_convection_sources.py` were run); via-real-board the other thirteen studies (several GB, hours; the README says they were not re-run for the adoption); laminate-nodes eighteen further studies; young-omega-tiles seven further studies (patch-based, see 4.3); gerber-models `study_models_self.py` (needs a patched copy, 20 minutes), `study_diagonal_heldout.py` (30 minutes) and twenty-three other studies. Whether a study that is not listed would show a 2.4.5 shift is not known.

## 7. Points for the maintainer

1. No UNEXPLAINED number. Every moved number belongs to the laminate rule, the point via / constriction batch, or the part across the outline, and was located by running the script on the tree before the item.
2. Two README conclusions change with the numbers and should be re-read: power-calculator 4.7 (the true 2 W is now just outside the band for the board without vias, by 0.002 W; the README says inside) and the "reproduced to the last digit" sentences of 4.7; component-heatsink 4.11 (Tj of the 8 mm pads +0.6 to +1.2 K; the claim of the section, program equals the exact root, holds).
3. The "Update for the program of 2.4.5" of gerber-models is confirmed for 4.31, 4.35, 4.37 (one 0.2-point difference on the 3D solid), but the 4.34 table (FVM, FDM) and the Stormduino row of 4.31 also moved and are not in its list.
4. Research code that no longer runs on the 2.4.5 network: component-heatsink `package_prototype.py` (hangs in `spsolve`, no error), effective-conductivity `study_corrections_impact.py` (stale since 2.4.2), young-omega-tiles `study_s3_boards.py` and `study_s4_example.py`. A hang with no message is the worst case; the executor should make `package_prototype.solve` fail (or adapt it) before the next reproduction pass.
5. Cost of the laminate rule seen in passing: the top-path board at 0.5 mm went from about 4 s to about 30 s per row (7 times), the first solve of the Power Calculator style board takes 18 s; the CHANGELOG says 2.5 times the unknowns on a 2-layer board, so the time grows faster than the unknowns here.
6. Environment notes: the worktree has no `.venv`, so the shared `.venv` of the main checkout was used; zone-union and the Gerber studies need `.venv-research` (shapely); the Gerber boards come from `research/gerber-import/data` of the main checkout (a symlink was made in the worktree and is not committed); `timeout` does not exist on this macOS, so the time limits come from the runner.
