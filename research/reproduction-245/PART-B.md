# Reproduction of release 2.4.5, part B

Folders: `point-via-convergence`, `sor-with-via-couplings`, `rotated-square-3d`, `models-comparison` (and the two project documents that
`models-comparison/scripts/validation_study.py` and `solver_equivalence.py` feed: `docs/validation.md` sections 1, 2, 2.1 and 5).
Tree under test: `develop` at `0d4159f` (the 2.4.5 candidate). Branch `research/reproduction-245-b`, created from `research/reproduction-245`
(which had no commit holding `run_all.py` yet, so the file was copied from the first tester's worktree). No README number was rewritten.

## 1. Commands and durations

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

### 1.1 Load

Around 22:40 the machine swapped (load average 40, swap 16 of 17 GB) while three testers ran; the job `study_square_reference` was stopped (SIGSTOP) for
about six minutes and then hit the 1500 s limit of the runner. Rerun alone on a quiet machine it needed 197 s and printed the whole table. The timings of this
section are therefore not benchmarks, and the per-via timings of `study_edge_via` (0.12 to 3.5 ms, README 0.06 to 1.9 ms) are load, not a change.

## 2. Result in one table

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

## 3. Shifts, with the item that explains each

Items: PV = point via (`fix/point-via`, commit 5e93182, FVM, FDM, 3D solid and the block SOR); PAO = part across the outline (62afbb8); C8 = board cover 8 x 8
(7a5b0ee); SO = SOR relaxation factor (`fix/sor-omega`); VC = via constriction (Lumped, Analytic; f671868); LN = laminate nodes (e9f4df2).
"README" values are those of the README of the folder unless the document is named.

### 3.1 Two shifts that deserve the reviewer's eye

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

### 3.2 point-via-convergence

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

### 3.3 sor-with-via-couplings

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

### 3.4 rotated-square-3d

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

### 3.5 models-comparison

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

## 4. How the items were found (git archive copies)

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

## 5. Not run, and why

* `sor-with-via-couplings/study_real_board.py` and the example-board row of `study_block_over.py` part 1: the folder's library predates the laminate nodes and crashes
  (section 3.3). The research library needs an update; the program is not at fault.
* `models-comparison` `validation_study.py --fem` (scikit-fem is not in `requirements.txt`) and the "before" column of `study_complex_boards.py` (needs a worktree of the
  old commit).
* The tests of the research folders (`pytest research/<folder>/tests`) were not run in this part: the request was the studies and the tables. (The folders'
  tests import the same libraries and `lib/sorvia.py` would be expected to fail on a laminate board.)

## 6. Stale text found (for the maintainer, nothing edited)

* `docs/validation.md` section 5: example board row (85.2249, 3.5e-09, 810 sweeps) and the sentences "agree to 4e-9 K" and "in 810 sweeps"; now 85.2335, 6.3e-09, 676.
* `research/models-comparison/README.md` sections 4.1 to 4.9 carry the numbers of the program before PV, VC and LN.
* `research/models-comparison/scripts/study_time_and_coefficients.py`: add `laminate.uses_rule = lambda p: False` to the exact check, as `tests/test_fvm.py` does.
* `research/sor-with-via-couplings/lib/sorvia.py`: `stencil_parts` assumes extra links between adjacent layers.
* The `checks.py` message for a via outside the board tests only the bounding box (section 3.1, item 1).
