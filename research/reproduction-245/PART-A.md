# Part A: analytic-partial-copper, bare-spot-under-source, gap-subdivision, lumped-via-groups, lumped-analytic-vias, via-fill

Program under test: `develop` at `0d4159f` (2.4.5 not yet released). Items of 2.4.5 that can move a number: part across the outline (`62afbb8`),
board cover 8 x 8 (`7a5b0ee`), point via and block SOR (`5e93182`), Young omega (`d9216c4`, speed only), constriction of the via in the Lumped and Analytic models
(`f671868`), laminate rule with sub-gaps, face term and column SOR (`e9f4df2`). Tolerance: the folder's own, or 0.5 % when it states none. Counts are cells of the
README tables that were compared (approximate: a cell is one number of a table or one quoted number).

Short names used below: PV = point via (`5e93182`), CON = constriction (`f671868`), LAM = laminate rule (`e9f4df2`).

A note that matters for reading the "unchanged" rows: most of these folders freeze the earlier program inside `lib/` (`lumped_patch.patched("off")`,
`program_patch.patched("point")`, `layered.py` with `ladder=False`), so that their columns named "program" keep meaning "the program up to `f2d5c03`".
Those columns reproduce by construction; they test the library, not the 2.4.5 program. The columns that call the current program directly (FVM, FDM, "program" in the
validation rows) are the ones that moved, and each shift below is tied to one item.

## Results

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

## Research tests of the folders

| Command (from the repository root, `QT_QPA_PLATFORM=offscreen`, one at a time) | Result |
| :-- | :-- |
| `.venv/bin/python -m pytest -q research/analytic-partial-copper/tests` | 12 passed in 5.3 s |
| `.venv/bin/python -m pytest -q research/bare-spot-under-source/tests` | 12 passed in 46.7 s |
| `.venv/bin/python -m pytest -q research/gap-subdivision/tests` | 8 passed in 2.0 s |
| `.venv/bin/python -m pytest -q research/lumped-via-groups/tests` | 16 passed in 10.5 s |
| `.venv/bin/python -m pytest -q research/lumped-analytic-vias/tests` | 13 passed in 11.8 s |
| via-fill | no tests folder (its tests are `tests/test_via_fill.py`, in the battery) |

## Durations (seconds, `out/reproduction.json`)

analytic-partial-copper: baseline 358, causes 12, candidate 190, rows 85, review 321. bare-spot-under-source: validation rows 156, review about 600.
gap-subdivision: rerun_baseline 147, validation_impact 724, real_boards 68. lumped-via-groups: cluster 9, cell_link 0.3, example board 264, outside 609.
lumped-analytic-vias: causes 1027, via_fill_rows 71, discretisation 82, real_boards 147, unit_cell 39. via-fill: study_via_fill 21, study_via_model_checks 383.
