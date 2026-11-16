# Reproduction pass 2.8.0, part B (in progress)

Tree: development 77ed4822, detached worktree. Machine at start: load 2.5, swap used 1.1 GB of 2 GB, free+inactive about 9 GB. One job at a time, nice 10.

## 1. Research tests (research/<folder>/tests)

| folder | result |
| :-- | :-- |
| analytic-edge-spatial | 19 passed in 3.67s (unchanged) |
| fin-channel | 18 passed in 6.61s (unchanged) |
| gerber-cad-profiles | 36 passed, 1 skipped in 0.37s (unchanged) |
| gerber-real-boards | 50 passed, 7 skipped in 7.27s (unchanged) |
| imported-via-rim | 2 passed in 0.43s (unchanged) |
| independent-fem-edge | 11 passed, 1 skipped in 3.50s (unchanged) |
| laminate-nodes | 20 passed in 3.65s (unchanged) |
| lumped-zone-placement | 4 passed in 0.73s (unchanged) |
| memory-guard | 59 passed in 2.24s (unchanged) |
| reduced-models-imported-passives | 9 passed in 2.32s (unchanged) |
| strong-edge-laminate | 6 passed in 1.63s (unchanged) |
| via-edge-image | 7 passed in 1.94s (unchanged) |
| via-well-sheet-order | 2 passed in 0.46s (unchanged) |
| young-omega-tiles | 23 passed, 3 skipped in 0.67s (unchanged) |
| zone-union | 9 passed in 1.26s (unchanged) |
ALLDONE
| power-calculator, solid3d-verification | no tests directory |

Studies (section 2) are running; the table is filled when they end.

## 2. Incident and guards

| folder | script | result |
| :-- | :-- | :-- |
| laminate-nodes | study_transient | not run: memory (reached 18 GB; killed by the orchestrator); listed with the heavy studies; its v2.7.1 twin was not run either |

From that point a watchdog (`scratchpad/B/watchdog.py`, a separate process; the running queue was not edited) kills any study child above 4 GB RSS (log `watchdog.log`) and suspends it while swap used is above 2.5 GB. A study that hits the 300 s limit while suspended is recorded as 'not run (timeout or paused)', not as a result.

## 3. Studies, new tree against v2.7.1 (comparison partial: the v2.7.1 run was still going when this was written)

Method: each script run on the tree and on a copy of development with `pcbthermal/` replaced by the v2.7.1 one; times, paths and report text ignored. 107 scripts on the tree: 63 rc=0 with output, 38 rc=1, 5 timeouts (300 s), 1 killed (memory). Compared so far: 34 pairs, 24 identical, 10 differ.

### Shifts (10)
| folder | script | what moved | item | class |
| :-- | :-- | :-- | :-- | :-- |
| fin-channel | study_program_finned_block | Analytic finned block rise, 0.1 K in a few rows (60.6 vs 60.6 ... 64.4 vs 64.3) | M4 (+0.09 K) with M1 | explained |
| gerber-real-boards | study_whole_board_reduced_models | Lumped error column only, 0.1 to 2.6 points (e.g. C1 -47.1 to -46.6 %); FVM and Analytic identical | M3 | explained |
| lumped-zone-placement | study_frozen | Lumped 'largest change' 2.681 to 1.64 K (study compares with the frozen Lumped) | M3 | explained (model only) |
| memory-guard | study_sor_block | memory columns 0.01 to 0.05 GB | none needed: peak-memory read-out, load noise | noise |
| power-calculator | calculator_validation | RthetaJA 46.7 to 47.1, 45.6 to 46.1, 31.6 to 31.9 K/W; board without vias 74.6 to 83.5 K/W (+12 %) | M1/M2 (FVM) and M3 (Lumped) | explained for the first rows; the +12 % no-via row is larger than the item ranges (M3 part rows up to about 10 %): TO CONFIRM by the reviewer |
| power-calculator | study_independent_datasheet_board | FVM 47.65 to 47.73 K/W (+0.08 K), coefficients 42.60 to 42.65 | M1 + M2 (FVM, zone edges in cells); larger than M1 alone (0.04 K), not isolated | explained (not isolated) |
| solid3d-verification | study_one_layer_board | Lumped column only 57.77 to 58.09 K (+0.55 %), 75.82 to 76.13; other models identical | M3 (range -0.5 to +3.1 %) | explained |
| solid3d-verification | copper_dissipation | Lumped column only: 652.7 to 795.0 K (+22 %) at the 10 mm pad, +25 % at 20 mm, FVM, FDM, 3D, Analytic identical | M3 by model, but size exceeds the item range on frozen boards (+3.1 %) | TO CONFIRM by the reviewer (candidate UNEXPLAINED) |
| laminate-nodes | study_windows_cell, study_windows_reconcile | not comparable: need `windows_native.npz` (LAMNODES_GERBER_OUT), absent | | not run |

No difference of FVM, FDM, 3D solid or Analytic (except the finned block) was found outside the items.

### Not comparable (rc=1 in the tree; cause in the last line of the raw output)
- missing data from earlier runs (`out/`, git-ignored, not in the worktree): gerber-cad-profiles (3), independent-fem-edge (4), memory-guard/study_class_fit, reduced-models-imported-passives (constriction_factor, fin_check), strong-edge-laminate/study_review_slabs, zone-union (program, real_board, strips).
- missing board data (`fetch_boards.py` not run, `rp2040` not a folder): gerber-real-boards (conformance_rare, fine_copper_warning, heater_margin, heater_shape, odb_structure).
- missing module (shapely: gerber-cad-profiles/study_reader, zone-union/study_cost; skfem: solid3d-verification fem3d_validation, study_block_against_fem).
- obsolete prototype patch (`analytic.solve_steady` no longer has the lines; obsolete since fix/via-constriction): young-omega-tiles study_s4_arrays, heldout, rule, tile; 'anchor not found' in s4_example, s4_lumped. A documentation finding (stale studies), not a defect of the program.
- script errors in the tree: imported-via-rim study_real_boards (IndexError), study_synthetic (TypeError: a patched lambda takes 4 arguments, 5 given: the program's function gained an argument); reduced-models-imported-passives cell_and_outline, cell_convergence (IndexError), rule_search (empty array). Not isolated; to look at by the executor.
- timeouts at 300 s: laminate-nodes/study_validation_rows, power-calculator (study_cell_size, study_jedec_board_readings), reduced-models-imported-passives/study_error_decomposition, strong-edge-laminate/study_thin_laminate.

### Heavy studies, not run (separate decision)
gerber-real-boards copper_mapping (about 2 h), lumped_analytic_rule (30 min), paste_footprints (15 min), transient_fine (20 min), rule_network_split (2.4 to 4.5 GB), program_cells; memory-guard memory_ladder (1 h); independent-fem-edge thin_laminate (40 min, scratch FEM environment) and fem_cases (2.5 GB); laminate-nodes windows_real (8 GB) and study_transient (reached 18 GB, killed by the orchestrator); zone-union study_cases (4 GB); solid3d-verification fem_hand_checks (1.1 million nodes) and small_pad_convergence (scikit-fem missing); analytic-edge-spatial edge_variants (15 min). make_figures and make_diagrams of every folder: not run.

### Still open
The v2.7.1 run was still going (about 30 scripts: via-edge-image, via-well-sheet-order, young-omega-tiles s3, zone-union edge_cases and sampling, strong-edge-laminate, solid3d solve_cost, ...); their comparison is not in this file. Watchdog log: empty (no kill, no recorded pause).

Totals so far: checked 15 test sets + 34 compared studies; unchanged 15 + 24; explained 7 (one not isolated); to confirm 2 (calculator no-via row, copper_dissipation Lumped +22 %); unexplained 0 proven; not run or not comparable: 14 heavy + 38 rc=1 + 5 timeouts + 1 killed.
