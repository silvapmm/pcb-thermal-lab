# Reproduction pass of release 2.5.0, part D

Tester D, detached worktree of `develop` at `e97b62f` (program version string 2.4.5, the 2.5.0 candidate). Folders of this part: outline, paper-case-studies, plate-h-level,
point-via-convergence, power-calculator, releases/regression-harness, rotated-square-3d, solid3d-verification, sor-with-via-couplings, stackup, theory-sources, theory,
via-edge-image, via-fill, via-partial-copper, via-real-board, young-omega-tiles, zone-union. Interpreter `.venv` of the main checkout (`.venv-research` for the
zone-union studies that import shapely). The program was not touched.

## 1. Method

* One job at a time, 2 threads, a per-job limit of 15 to 30 minutes of running time (a job paused for load does not count). The runner paused the job when the load average
  was above 8.5 or the free plus inactive memory below 1.2 GB. Deviation from the brief: the swap figure on this machine was 10 to 13 GB for the whole pass (left by
  other jobs), so the rule "swap used above 3 GB" could not be used (it stopped the runner for good); the load rule was relaxed from 7 / 5 to 8.5 / 6.5 because four
  testers kept the load at 5 to 7 all the time (peak 21 once). Eight pauses in total.
* **Comparison with the previous release is made by running the same script on the program of v2.4.5** (`git archive v2.4.5` with the research folders of this tree
  copied over it, so the scripts are the same and only `pcbthermal/` differs) and diffing the printed lines. That separates a 2.5.0 shift from a README that was already
  stale before (the READMEs of several folders still hold pre-2.4.5 digits, as the reproduction pass of 2.4.5 left them on purpose). Where no baseline was run, the printed
  numbers were compared with the README by eye on the key rows, and this is said.
* The shifts are tied to the items of 2.5.0 by name: **ROBIN** (Analytic Robin edge), **ZONES** (zonal Lumped, including its decision on the equivalent rectangle of an outline),
  **FOOT** (Lumped footprint potentials in blocks), **EDGEIMG** (mirror image of a straight board edge in the via well), **GUARD** (memory guard), **HLIM** (edge coefficient
  limit 1e5 W/m2K in `Board.validate`), **SYMLU** (symmetric LU, last bits only).
* The machine: load average 1.5 at the start, 5 to 7 during the pass (peak 21), 4.3 at the end; swap used 1.1 GB at the start, 10 to 13 GB from the second hour (not mine).

## 2. Totals (units: one test run, one harness result set, or one study script)

| | Checked | Unchanged | EXPLAINED | UNEXPLAINED | Not run / failed for a stated reason |
| :-- | --: | --: | --: | --: | --: |
| Tests (frozen numbers at 2, 1 and 0.5 mm, the folder's own tests, docs and licence gates) | 16 | 16 | 0 | 0 | 1 (outline has no tests folder) |
| Harness result sets (255 steady records, 68 transient parts) | 2 | 0 | 2 | 0 | 0 |
| Study scripts (run on the tree and compared with v2.4.5 or the README) | 52 | 39 | 13 | 0 | about 77 (section 5) |
| **All units** | **70** | **55** | **15** | **0** | about 77 scripts, 1 test folder not applicable |

Scripts that failed on the tree failed on v2.4.5 too (two in young-omega-tiles) or stopped on the 1e5 edge-coefficient limit (one, explained): counted as checked, unchanged
or explained as stated in their rows. `study_cost`, `study_strips`, `study_square_reference` ran to the end but were not diffed against v2.4.5 (timings, or all-zero tables).
**UNEXPLAINED: 0.**

## 3. releases/regression-harness (priority 1): the frozen reference and the version comparison

Commands (from the repository root of the worktree):

    PCBT_FROZEN_CELLS=2,1,0.5 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/regression      -> 317 passed in 92.5 s
    .venv/bin/python -m pytest -q releases/regression-harness/tests                                    -> 24 passed
    study_baseline_release.py --tag v2.4.5 --label v2.4.5   (git archive of the tag)                        -> out/v2.4.5.json (255 records, 68 transients)
    study_run_suite.py --label tip                                                                           -> out/tip.json   (255 records, 68 transients)

The frozen test is green at all three cells **with the four pending files applied** (analytic-edge, lumped-zones, lumped-footprint-potentials, via-edge-image), which is its design.
The classified diff of the two result sets (`study_diff.py` with the table of 2.4.5, which does not know the items of 2.5.0, so its 613 alarms are not meaningful) was
replaced by a direct comparison of the hottest point of every record:

| class of the 255 steady records | records |
| :-- | --: |
| identical in every digit | 117 |
| last bits only (below 1e-8 K; SYMLU and library noise) | 89 |
| moved, all explained | 45 |
| skipped in both sets (3D solid above its cap) | 4 |

The 45 moved records, with the old and the new hottest point:

| item | records | old -> new (degC) |
| :-- | :-- | :-- |
| ROBIN (Analytic, every board with an edge coefficient, 13 boards x 3 cells = 39) | e.g. example_board 85.1021 -> 84.5774 (-0.52 K, 1 and 2 mm; 85.2167 -> 84.6916 at 0.5 mm); example_cut_to_T 91.9041 -> 90.8872; finned_block 130.6275 -> 129.7004; hatched_copper 112.4150 -> 111.5034; part_across_outline 216.0332 -> 208.9276 (-7.1 K, the largest); part_top_path 69.5730 -> 69.2227; plate_lone_via 152.1101 -> 150.3321; plate_vias 137.6411 -> 135.8748; profile_board = example_board; reference_board 90.3488 -> 90.0904; round_outline 178.3478 -> 175.3291; t_outline 141.0696 -> 136.7720; two_layer_partial 153.9638 -> 152.7090 | all 39 equal the pending file `analytic-edge.json`; the document `docs/version-comparison.md` prints the same numbers |
| ZONES (Lumped, plate_vias, the only board with a zoned part) | 3 (0.5, 1 and 2 mm) | 140.1495 -> 136.4534 at 0.5 mm (-3.70 K); 140.3555 -> 136.4534 at 1 and 2 mm (-3.90 K); `lumped-zones.json` |
| FOOT (Lumped, reference_board at 0.5 mm) | 1 | 89.0933 -> 89.3632 (+0.27 K); `lumped-footprint-potentials.json` |
| EDGEIMG (FVM, example_cut_to_T) | 2 | 94.4545 -> 94.4442 at 2 mm (-0.0103 K), 94.5009 -> 94.5008 at 1 mm (-0.0001 K), 0 at 0.5 mm; `via-edge-image.json` |

Transients (times to 63 % and board resistance of the 68 parts): 24 values on 12 records moved, all on the same items: Analytic at 1 mm on 8 boards (ROBIN, e.g. example_board U1
t63 13.475 -> 12.815 s, rth 13.534 -> 13.433 K/W; plate_vias U 33.638 -> 31.011 s), Lumped plate_vias U (ZONES, 27.828 -> 31.000 s, the number of the pending file), FVM example_cut_to_T U1
(EDGEIMG, 15.986 -> 15.995 s). Every other record of every other model (FVM, FDM, 3D solid, and the SOR runs) is identical or at the last bits. **No unexplained shift.**
Nothing in the harness is moved by the memory guard, the laminate options, the face term, imported copper or the laminar default (the boards of the harness do not reach them, as
`docs/version-comparison.md` says).

## 4. The study scripts

Reading the columns: **base** is the same script on the program of v2.4.5 (diff of the printed lines), **README** the comparison with the folder's README only.

| Folder / script | Compared with | Result | Item |
| :-- | :-- | :-- | :-- |
| solid3d-verification / `solid3d_verification` | base | UNCHANGED (Yovanovich table, GCI 1.14 %, 1.68 order; only a guard line added, the README column 0.8076 is the 2.4.5 value 0.8062) | GUARD (message) |
| solid3d-verification / `study_one_layer_board` | base + README | FVM, FDM, 3D solid, Lumped columns unchanged (57.27 / 57.28 / 57.38 / 57.77 and 80.81 / 76.78 / 81.92 / 75.82 match the README update); Analytic 57.09 -> 56.78 and 75.64 -> 75.01 | EXPLAINED, ROBIN |
| solid3d-verification / `study_spreading_axisymmetric` | base | UNCHANGED | |
| solid3d-verification / `copper_dissipation` | base | FVM, FDM, 3D solid columns unchanged; Analytic column -0.2 to -0.3 K on 6 rows (201.1 -> 200.9, 150.3 -> 150.0, 143.6 -> 143.3) | EXPLAINED, ROBIN |
| solid3d-verification / `study_small_pad_convergence` | README | UNCHANGED: all 8 cells of part 1 and the 6 rows of part 2 equal the README digits (829.2 / 806.3, 362.7 / 357.8, FEM 762.0 / 773.5, 348.5 / 350.9); the memory guard warned (5.1 GB against 2.9 GB free) | |
| solid3d-verification / `study_block_against_fem` | base | UNCHANGED (identical to v2.4.5; the README first row 133.2 / 132.6 is older than 2.4.5, printed 133.6 / 132.9 since the laminate rule) | stale README, not 2.5.0 |
| solid3d-verification / `study_fem_hand_checks` | README | rows printed equal the README (example board 1 mm 85.567 degC, the 0.5 mm row 90.569); the run ended after the example row (no traceback in the output, ended under memory pressure), counted as partial | |
| solid3d-verification / `study_solve_cost` | | NOT RUN to the end: stopped by me after 7 minutes (timings only, load dependent); the first rows printed (solid3d 247 884 unknowns 4.5 s, 0.99 GB) | |
| outline / `outline_rectangle_study` | base | FVM unchanged except the T example (106.81 -> 106.87, +0.06 K); Analytic columns moved by -0.4 to -1.6 points on 8 rows; Lumped on the T example same-area box -12.7 -> -10.8 % | EXPLAINED: ROBIN (Analytic), EDGEIMG (FVM T), ZONES (the equivalent rectangle scales the 9 vias of U1 by 0.8165 and `will_be_zoned` turns True for U1, False at scale 1: checked) |
| outline / `study_edge_on_grid_lines` | base | perimeter and tau rows unchanged; Lumped / Analytic error of the L, T example and T centre moved (L near edge Analytic 0.0 -> -1.4, T example -12.7 / -13.3 -> -10.8 / -14.9) | EXPLAINED: ROBIN, ZONES, EDGEIMG |
| outline / `study_outline_time_constant` | base | UNCHANGED | |
| outline / `study_disc_reference` | base | one row: Analytic at 1 mm 50.687 (+0.46 %) -> 50.337 (-0.24 %) and 16.034 (+2.68 %) -> 15.618 (+0.02 %); the rest unchanged | EXPLAINED, ROBIN |
| stackup / `stackup_outline_study` | base | Analytic column of table A +3.5 -> +0.3 % (8 rows); table B, L shape: FVM 102.0 -> 103.2 K (+1.2 %), FDM -0.3 -> -1.4 %, 3D solid -1.9 -> -3.1 %. Cause of the L shape row proved by a run with the image switched off in the tip tree (`viawell.image_walls` returning no wall): 102.026 K, identical to v2.4.5; with it 103.208; without the four vias that sit on the notch walls, v2.4.5 and tip agree to 0.001 K (109.506 / 109.507); with no vias 121.992 both | EXPLAINED, ROBIN (A), EDGEIMG (B, vias exactly on a straight wall; the harness board moves only 0.01 K because its vias are 4.5 to 11.5 mm from the wall) |
| stackup / `study_dielectric_sensitivity`, `study_inner_copper_1oz`, `study_real_1oz_stackups` | base | UNCHANGED (3 scripts) | |
| via-fill / `study_via_fill` | base | UNCHANGED | |
| via-fill / `study_via_model_checks` | base | 12 lines moved, all in the Analytic column (85.22 -> 84.69 open; copper 80.94 -> 80.42; no vias 94.71 -> 94.18); FVM, FDM, Lumped and 3D solid columns, the barrel-conductance check and the cell-size sweeps identical | EXPLAINED, ROBIN |
| power-calculator / `calculator_validation` | docs/calculators.md | UNCHANGED (47.5 K/W, 0.968 W, -3.2 %; 31.3 K/W, 1.039 W, +3.9 %; 71.0 K/W) | |
| power-calculator / `study_independent_datasheet_board`, `study_power_band`, `study_design_term_coverage`, `power_from_top_study` | base | UNCHANGED (4 scripts; band 2.00 / 1.62 / 2.31 W ring, 1.68 / 2.27 W top; coverage rows; recovered powers 1.686, 1.521, 1.297, 1.766, 2.127) | |
| power-calculator / `calculator_calibration_study` | base | UNCHANGED (only the sign of a zero: `+0.0 %` -> `-0.0 %`) | SYMLU (last bits) |
| power-calculator / `study_cell_size` | docs | TIMEOUT at 15 minutes (the README says 8 minutes on a quiet machine; the machine was shared); the rows printed (CSD17308Q3 47.2 / 47.5 / 48.0 / 47.9 K/W) equal docs/calculators.md, the README table of 4.5 (46.4 / 46.8 / 47.2 / 47.1) is the pre-2.4.5 one | partial |
| via-edge-image / `study_adoption_impact` | pending file | UNCHANGED: example_cut_to_T -0.0103 / -0.0001 / 0.0000 K at 2 / 1 / 0.5 mm, every other board 0; equal to `via-edge-image.json` | |
| via-edge-image / `study_edge_absolute` | README | rows equal the README (error -0.094 K at 1 mm for the nearest via with the image; -0.006 at 0.5 mm) | |
| via-edge-image / `study_edge_sweep` | README | the tables of `h_side` 0 to 1e5 print and agree (+0.8 / +0.2 % program rows); **the run ends with `ValueError: the edge heat transfer coefficient must not exceed 100000 W/m2K`** at the last table: the script's default list of `--h-side` ends at 1e6 | EXPLAINED, HLIM; a script to adjust (see 6) |
| via-partial-copper / `study_documented_case` | README | UNCHANGED (3D solid effect 0.70 / 2.86 / 7.20 / 10.74 K; FVM current cold spot -7.94 K at 0.5 mm, -14.43 K at 0.25 mm; FVM effect 7.67 K) | |
| via-partial-copper / `study_frozen` | base | only example_cut_to_T FVM at 2 mm moved: 94.454 -> 94.444 | EXPLAINED, EDGEIMG |
| via-partial-copper / `study_fullcopper`, `study_matrix`, `study_reproduce`, `study_variants`, `study_warning` | README key numbers | run to the end (5 scripts); the gain of the copper fill, the cold spots and the matrix properties print the README digits where the README quotes them; not diffed digit by digit | |
| zone-union / `study_edge_cases` | base | 3 lines moved, all in the Lumped column of the T board (103.574 -> 103.254, 103.850 -> 103.355) | EXPLAINED, ZONES |
| zone-union / `study_sampling` | base | UNCHANGED | |
| zone-union / `study_program` develop, variant, report (`.venv-research`) | base | the four cases of gerber-models 4.39 identical to v2.4.5 (FVM and FDM 142.96, README 4.2 still prints 143.08, a pre-2.4.5 digit); example boards: Analytic 60.102 -> 59.577 (1 mm) and 65.349 -> 65.090 (reference_board), Lumped reference_board 0.5 mm 64.093 -> 64.363, and the 3D solid at 0.5 mm now stops with `MemoryGuard` where v2.4.5 raised `ValueError` | EXPLAINED: ROBIN, FOOT, GUARD |
| zone-union / `study_cost`, `study_strips` develop, variant, report | | ran (`.venv-research`); strips tables all 0.00 as in the README; cost prints timings (machine dependent) | not diffed |
| zone-union / `study_cases`, `study_real_board` | | not run: need `study_cases.py reference`, the independent solver, and downloaded boards | NOT RUN |
| sor-with-via-couplings / `study_variants`, `study_real_board`, `study_block_over`, `study_stiffness`, `study_failure` | README | sweep counts identical to the README (26 350, 51 270, 4 140, 8 780, 2 610, 4 170; real board 60.225 K, 2 260 / 2 390 / 189; example board 813 -> 2 390 -> 2 250); residuals in the 1e-10 columns differ in the last digit (4.2e-10 against 4.3e-10) | UNCHANGED, SYMLU (last bits of the direct reference) |
| young-omega-tiles / `study_s3_exact` | README | ran; the Poisson table is pure mathematics | UNCHANGED |
| young-omega-tiles / `study_s4_example` | base | **FAILED on v2.4.5 too**: `RuntimeError: line not found in analytic.solve_steady` (`lib/tilerule.py` patches a source line that the Analytic code no longer has) | stale library, not 2.5.0 (see 6) |
| young-omega-tiles / `study_s3_boards` | base | **FAILED on v2.4.5 too**: `AssertionError: sorvia.py needs the network without the laminate nodes` (the library of this folder builds the network with the laminate rule, as the 2.4.5 pass fixed in sor-with-via-couplings) | stale library, not 2.5.0 (see 6) |
| rotated-square-3d / `study_regression`, `study_part_across_outline` | base | only the FVM of the example board cut to a T moved: 106.81 -> 106.87 (h_side 10), 97.43 -> 97.49 (h_side 100), 106.56 -> 106.59 at 0.6667 mm; every 3D solid and cut-cell column, the aligned and rectangle rows identical | EXPLAINED, EDGEIMG (the README still prints 106.809) |
| rotated-square-3d / `study_remeasure`, `study_turned_part`, `study_edge_conductance`, `study_disc` | base | UNCHANGED (4 scripts) | |
| rotated-square-3d / `study_square_reference` | | ran to the end (270 s), not diffed | |

## 5. Not run (and why)

* point-via-convergence: only `study_unit_cell` ran (finished, 204 lines, equal in the rows checked to the README); `study_array_board`, `study_row_lone`, `study_example_board`,
  `study_solid3d`, `study_solvers`, `study_edge_via`, `study_target_radius`, `study_reference_3d` were not reached in the time (each takes minutes; the folder's tests, 18, pass).
* via-real-board (12 studies, need `PCBT_REAL_BOARDS`), plate-h-level (5), paper-case-studies (3), young-omega-tiles `study_s4_*` and `study_s3_block_more`, rotated-square-3d cut-cell
  studies (`study_cut_cells*`, `study_cutcell_*`, `study_square_reference`, `study_turn_frame_reference`), stackup `stackup_vendor_check`, solid3d-verification `fem3d_validation`,
  power-calculator, zone-union `study_cases` / `study_real_board`, theory `check_*` and `study_fvm_analytic_edges`, theory-sources (21 scripts): not reached or, for theory and
  theory-sources, tests only as agreed. Their tests all pass (section 2).

## 6. Findings for the maintainer and the executor (nothing changed in this pass)

1. `research/via-edge-image/scripts/study_edge_sweep.py`: its default `--h-side` list ends at 1e6, which `Board.validate` now refuses (1e5 limit, item HLIM); the script dies at the last table. Run it with `--h-side 0 10 100 1e3 1e4 1e5`, or cap the list.
2. `research/young-omega-tiles`: `lib/tilerule.py` (line patch of `analytic.solve_steady`) and the SOR library (laminate nodes) no longer fit the program; both studies fail on v2.4.5 as well, so the failure is older than 2.5.0.
3. `research/solid3d-verification/README.md` 4.2 (the 0.8076 in the Yovanovich table), `research/zone-union/README.md` 4.2 (143.08) and `research/power-calculator/README.md` 4.5 (46.4 / 46.8 / 47.2 / 47.1)
   still hold pre-2.4.5 digits (the program prints 0.8062, 142.96, 47.2 / 47.5 / 48.0 / 47.9). These are not 2.5.0 shifts; the same notice as in the pass of 2.4.5.
4. The stackup validation table (`docs/validation.md` and `research/stackup`) L shape row moves by +1.2 % in the FVM with 2.5.0 (EDGEIMG): vias that lie exactly on a straight wall of the notch. Its size is larger than the 0.01 K quoted for the frozen board, and the sign (hotter) is that of the correction the item describes, but a reader of `docs/validation.md` should know.
5. The memory guard prints a warning line into the output of every large study on a loaded machine (`memory guard: the estimate of N GB is above M GB available now`); harmless, but it shifts the lines of a printed table in a text diff.

## 7. Files

`/private/tmp/claude-501/-Volumes-SSD-PROJETOS-pcb-thermal-lab/4c68d1f4-0ccc-466a-9ac6-5ee052402f79/scratchpad/runD/` holds the runner (`runner2.py`), the job lists and the outputs of this pass (`out/` for the tree under test, `outbase/` for v2.4.5); it is not in the repository.
