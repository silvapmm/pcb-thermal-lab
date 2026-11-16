# Reproduction pass 2.8.0, part D

Tree under test: `development` 232ba648 (branch `release/2.8.0-reproduction`, worktree `.claude/worktrees/repro-280`); reference: the same scripts run with `pcbthermal/` of `v2.7.1`. Method as in `PART-A.md`; two additions after the memory incident: every script runs under `runone.py` (timeout 300 s; kills the whole process group above 4 GB of resident memory, summed over the group; refuses scripts that mention `multiprocessing`, `Pool(` or `ProcessPoolExecutor`). `make_figures.py` / `make_diagrams.py` were not run (they would overwrite the committed figures); `gap-subdivision/study_validation_impact` was skipped by decision (about 731 s per tree). Machine: load 1.1 to 3.4, swap used 1.7 to 2.0 GB of 3 GB during the run (the 8.9 GB swap peak belongs to the incident below). Raw outputs in the git-ignored scratch (`raw/`).

## Totals of part D (18 folders, 121 study scripts, 18 test sets)

**Scripts: unchanged 26 (24 identical, 2 only timings or paths), explained 23, checked 18 (17 without a v2.7.1 baseline because the old package lacks a key or attribute of 2.8.0, 1 GUI study whose route B reaches the unchanged model check), not run 54, UNEXPLAINED 0.**
Not run: 19 memory (17 killed by the 4 GB watchdog in both trees: fdm-inset-edge/study_independent_3d, gap-subdivision rerun_baseline, study_baseline_uniform, study_review, lumped-ring-uniform-deficit (3), models-comparison (3), muzychka-case2-analytic/study_case2_reproduce, rotated-square-3d (2), theory/study_fvm_analytic_edges, via-partial-copper (2), lumped-analytic-vias/study_real_boards; 2 more where only one tree was killed), 4 parallel pool (`lumped-analytic-vias/study_arrays` killed by the orchestrator: pool of 8 workers of about 3.5 GB, about 28 GB, swap 8.9 GB, in both trees; `gap-subdivision` study_baseline_pads and study_gap_nodes and `lumped-analytic-vias/study_unit_cell` skipped by the new guard), 10 input missing (git-ignored `out/` files), 6 need an argument or mode, 4 script errors identical in both trees, 8 stale studies, 3 timeouts at 300 s, plus `study_validation_impact` (skipped by decision, not counted above). These are the heavy studies for the maintainer's decision.

## 1. Research tests

| folder | result | note |
| :-- | :-- | :-- |
| effective-conductivity | 14 passed | |
| fast-wave-oscillation | 13 passed | |
| fdm-inset-edge | 11 passed | |
| fem-amg-thin-layers | 21 passed, 1 skipped | |
| fin-channel-sources | 13 passed | |
| gap-subdivision | 8 passed | |
| laminate-slabs-and-local-rule | 7 passed | |
| **lumped-analytic-vias** | **6 failed, 7 passed** | 2 of the 6 fail identically on v2.7.1 (the tests `test_lumped_off_is_the_program_of_f2d5c03` and `test_analytic_off_is_the_program_of_f2d5c03` pin numbers of commit f2d5c03; tree 33.8217 against the pinned 33.8152, +0.0065 K; v2.7.1 fails them too). The other 4 raise `anchor not found`: the patch library copies the SOURCE TEXT of the Lumped network, which changed with M3. Stale tests, not a program defect |
| **lumped-near-edge** | **4 failed, 3 passed** | all 4 `anchor missing` (source copy of `lumped._footprint_potentials`, changed by M3); 7 passed on v2.7.1. Stale tests |
| **lumped-ring-uniform-deficit** | **1 failed, 5 passed** | `test_defaults_are_the_program`: the study's copy of the Lumped network no longer equals the program (temperatures differ by 4.6e-4 K); M3 changed the program, the copy is the old code. Stale test |
| muzychka-case2-analytic | 8 passed | |
| paper-case-studies | 31 passed | |
| rotated-square-3d | 34 passed | |
| theory | 5 passed | |
| transient-reference-boards | 8 passed | |
| via-partial-copper | 16 passed | |
| market-fem-comparison, models-comparison | no tests directory | |

## 2. Findings

1. The numbers that moved are of the items: Lumped columns (M3) in `models-comparison`, `lumped-near-edge`, `effective-conductivity`, `paper-case-studies`; the film term `q t/(2k)` (M1) on the thick plate of `muzychka-case2-analytic` (FVM, FDM, Analytic +0.93 to +0.94 K, exactly the 0.93 K the item table gives for a 10 mm plate); the FDM of the example board at 2 mm +0.10 K (M2, the same value in `models-comparison`, `via-partial-copper` and `small-model-defects`); every other FVM, FDM or Analytic number moves by at most 0.001 K.
2. `muzychka-case2-analytic/study_case2_gui` route B: in v2.7.1 the Board dock clamps the copper to 210 um, so the study could not type the paper's 10 mm plate; in 2.8.0 the boxes accept copper up to 20 000 um, thickness up to 100 mm and h up to 100 000 W/m2K, the 10 mm copper in a 10 mm board is typed, and the run fails with the dialog 'copper thickness must be smaller than the slab of its layer node (copper plus half of each adjacent gap)': the unchanged check of `fvm.py` (the same text exists in v2.7.1). The refusal is correct and states its cause; the maintainer may want the GUI limit of the copper to leave room for the board thickness.
3. `gap-subdivision/study_real_boards` OVERWRITES the tracked file `research/gap-subdivision/baseline/real_boards.csv` when it runs (restored with `git checkout`, nothing committed): a study that writes into a tracked folder.
4. Stale studies (documentation finding): the Lumped source copies of `lumped-analytic-vias`, `lumped-near-edge`, `lumped-ring-uniform-deficit` (see section 1).

## 3. Studies (folder | script | what was compared | class | item)

| folder | script | result | class | item |
| :-- | :-- | :-- | :-- | :-- |
| effective-conductivity | study_biot_definitions | identical output (timings ignored) | unchanged |  |
| effective-conductivity | study_channel_correlations | identical output (timings ignored) | unchanged |  |
| effective-conductivity | study_corrections_impact | identical output (timings ignored) | unchanged |  |
| effective-conductivity | study_culham_1998 | 300 s timeout in both trees | not run (timeout, heavy) |  |
| effective-conductivity | study_lee_spreading | identical output (timings ignored) | unchanged |  |
| effective-conductivity | study_muzychka_2003 | FVM centroid 79.94 -> 80.09 K, max 101.01 -> 101.18 K (+0.15 to +0.17 K), FDM +0.15 K, Lumped moves too; the plates are thick: film term q t/(2k) | explained | M1 (+M3 for Lumped) |
| effective-conductivity | study_natural_convection | identical output (timings ignored) | unchanged |  |
| effective-conductivity | study_one_layer_independent | one model column -1.6 % -> +1.2 % (Lumped, same column in every row); FVM, FDM, Analytic columns identical | explained | M3 |
| effective-conductivity | study_program_vs_coupon | one column moves by +0.1 to +0.5 points (Lumped); the others identical | explained | M3 |
| fast-wave-oscillation | study_correction | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| fast-wave-oscillation | study_estimator | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| fast-wave-oscillation | study_fast_wave_sweep | identical output (timings ignored) | unchanged |  |
| fast-wave-oscillation | study_impact | identical output (timings ignored) | unchanged |  |
| fast-wave-oscillation | study_resolved_curve | identical output (timings ignored) | unchanged |  |
| fast-wave-oscillation | study_review_reference | 300 s timeout in both trees | not run (timeout, heavy) |  |
| fast-wave-oscillation | study_review_tables | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| fast-wave-oscillation | study_ripple_review | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| fdm-inset-edge | study_cause | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| fdm-inset-edge | study_harness_shift | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| fdm-inset-edge | study_independent_3d | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| fem-amg-thin-layers | study_amg_variants | both trees stop with the same error: refusing to run a heavy study without --lock (CLAUDE.md 12) | not run (error in both trees) |  |
| fem-amg-thin-layers | study_extras | both trees stop with the same error: refusing to run without --lock | not run (error in both trees) |  |
| fem-amg-thin-layers | study_frozen_robustness | both trees stop with the same error: study_frozen_robustness.py: error: the following arguments are required: --lock, --variant | not run (needs argument or mode) |  |
| fem-amg-thin-layers | study_hierarchy_reuse | both trees stop with the same error: study_hierarchy_reuse.py: error: the following arguments are required: --lock | not run (needs argument or mode) |  |
| fem-amg-thin-layers | study_repeat | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| fin-channel-sources | study_review_checks | identical output (timings ignored) | unchanged |  |
| fin-channel-sources | study_source_checks | only the printed path of the written file differs | unchanged (noise) |  |
| gap-subdivision | rerun_baseline | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| gap-subdivision | study_baseline_pads | script or lib uses multiprocessing / Pool: skipped | not run (parallel pool) |  |
| gap-subdivision | study_baseline_uniform | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| gap-subdivision | study_gap_grading | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| gap-subdivision | study_gap_nodes | script or lib uses multiprocessing / Pool: skipped | not run (parallel pool) |  |
| gap-subdivision | study_real_boards | v2.7.1 stops (no baseline: the script reads a 2.8.0 key); tree runs and OVERWRITES the tracked file research/gap-subdivision/baseline/real_boards.csv (restored with git checkout, nothing committed) | checked, no v2.7.1 baseline |  |
| gap-subdivision | study_references | identical output (timings ignored) | unchanged |  |
| gap-subdivision | study_review | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| laminate-slabs-and-local-rule | _boot26 | identical output (timings ignored) | unchanged |  |
| laminate-slabs-and-local-rule | study_cost_one | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| laminate-slabs-and-local-rule | study_edge_film | identical output (timings ignored) | unchanged |  |
| laminate-slabs-and-local-rule | study_harness_impact | 0.001 K (85.294 -> 85.293 K) | explained | M1/M2 order |
| laminate-slabs-and-local-rule | study_local_rule | equation 50 error columns +0.1 to +0.2 points; temperatures identical to 0.001 K | explained | M1 order |
| laminate-slabs-and-local-rule | study_review_checks | identical output (timings ignored) | unchanged |  |
| laminate-slabs-and-local-rule | study_solid_harness | identical output (timings ignored) | unchanged |  |
| laminate-slabs-and-local-rule | study_solid_slices | identical output (timings ignored) | unchanged |  |
| lumped-analytic-vias | study_arrays | pool of 8 workers x 3.5 GB (about 28 GB, swap 8.9 GB) killed by the orchestrator in both trees | not run (parallel pool, killed) |  |
| lumped-analytic-vias | study_causes | v2.7.1 killed by the 4 GB watchdog (over 4 GB); tree stops with an error | not run (memory) |  |
| lumped-analytic-vias | study_discretisation | tree: RuntimeError anchor not found (lib/lumped_patch.py copies the Lumped source text, changed by M3); v2.7.1 ran | not run (stale study) | M3 (source copy) |
| lumped-analytic-vias | study_real_boards | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| lumped-analytic-vias | study_review | v2.7.1 killed by the 4 GB watchdog; tree stops with an error | not run (memory) |  |
| lumped-analytic-vias | study_unit_cell | script or lib uses multiprocessing / Pool: skipped | not run (parallel pool) |  |
| lumped-analytic-vias | study_via_fill_rows | same anchor error | not run (stale study) | M3 (source copy) |
| lumped-near-edge | smoke | tree: RuntimeError anchor missing (source copy of lumped._footprint_potentials); v2.7.1 ran | not run (stale study) | M3 (source copy) |
| lumped-near-edge | study_centre_sizes | tree: RuntimeError anchor missing (source copy of the Lumped network); v2.7.1 ran | not run (stale study) | M3 (source copy) |
| lumped-near-edge | study_edge_sweep | tree: RuntimeError anchor missing (source copy of the Lumped network); v2.7.1 ran | not run (stale study) | M3 (source copy) |
| lumped-near-edge | study_reference_cell | tree: RuntimeError anchor missing (source copy of the Lumped network); v2.7.1 ran | not run (stale study) | M3 (source copy) |
| lumped-near-edge | study_ring_diagnostic | tree: RuntimeError anchor missing (source copy of the Lumped network); v2.7.1 ran | not run (stale study) | M3 (source copy) |
| lumped-near-edge | study_rule | tree: input file of out/ absent; v2.7.1 ran from a stale file | not run (input missing) |  |
| lumped-near-edge | study_seri_lee | tree: RuntimeError anchor missing (source copy of the Lumped network); v2.7.1 ran | not run (stale study) | M3 (source copy) |
| lumped-near-edge | study_subcell | Lumped columns only (e.g. -19.4 -> other, -7.4 ...): the study measures the Lumped near an edge; FVM column identical | explained | M3 |
| lumped-near-edge | study_subcell_raster | Lumped columns only (e.g. -13.5 -> other %) | explained | M3 |
| lumped-ring-uniform-deficit | study_board_size_sweep | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-ring-uniform-deficit | study_edge_distance | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-ring-uniform-deficit | study_example_board_vias | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=1)); both trees alike | not run (memory, over 4 GB) |  |
| lumped-ring-uniform-deficit | study_frozen_impact | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-ring-uniform-deficit | study_frozen_patched_copy | both trees stop with the same error: both trees stop with the same error: | not run (error in both trees) |  |
| lumped-ring-uniform-deficit | study_imported_parts | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| lumped-ring-uniform-deficit | study_independent_3d | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=1)); both trees alike | not run (memory, over 4 GB) |  |
| lumped-ring-uniform-deficit | study_outline_and_vias | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-ring-uniform-deficit | study_ring_count | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-ring-uniform-deficit | study_ring_means | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-ring-uniform-deficit | study_sensitivity | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=1)); both trees alike | not run (memory, over 4 GB) |  |
| lumped-ring-uniform-deficit | study_shape_and_cell | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-ring-uniform-deficit | study_summary | identical output (timings ignored) | unchanged |  |
| lumped-ring-uniform-deficit | study_time_response | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-ring-uniform-deficit | study_via_boards_unchanged | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| market-fem-comparison | check_candidates | identical output (timings ignored) | unchanged |  |
| models-comparison | accuracy_study | Lumped columns only: reference board 89.69 -> 90.79 K (-0.7 -> +1.0 % of the rise), example board 86.87 -> 86.91 K; FVM and Analytic columns identical | explained | M3 |
| models-comparison | solver_equivalence | solver residual columns (3.1e-12 -> 1.9e-12), SOR 87.3953 -> 87.3954 K | explained | M1 order / noise |
| models-comparison | stress_study | Lumped column only; FVM and Analytic columns identical | explained | M3 |
| models-comparison | study_analytic_edge_transfer | identical output (timings ignored) | unchanged |  |
| models-comparison | study_complex_boards | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| models-comparison | study_complex_boards_independent | both trees stop with the same error: pcbthermal.memory.MemoryGuardError: the 3D solid (finite volumes) model would have 476000 | not run (error in both trees) |  |
| models-comparison | study_lumped_rings | Lumped ring table: one range +0.3 to +0.5 % -> +0.3 to +0.6 % | explained | M3 |
| models-comparison | study_offgrid_heater | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| models-comparison | study_time_and_coefficients | energy 3271.75 -> 3271.76 J; FDM frames +0.1 K; FDM steady maximum 84.52 -> 84.62 K (+0.10 K, the FDM of the example board at 2 mm: zone edges in cells) | explained | M2 (FDM) + M1 |
| models-comparison | validation_study | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| muzychka-case2-analytic | study_case2_followup | identical output (timings ignored) | unchanged |  |
| muzychka-case2-analytic | study_case2_gui | tree stops in route B: the Board dock now accepts copper up to 20000 um, thickness 100 mm, h 100000 (v2.7.1 clamped copper to 210 um); the typed 10 mm copper in a 10 mm board is then refused by the unchanged check of fvm.py ('copper thickness must be smaller than the slab of its layer node'), shown as a Simulation failed dialog with the cause. Route A identical to v2.7.1 | checked (GUI limits widened on purpose; the refusal is the old model check) | GUI limits of 2.8.0 |
| muzychka-case2-analytic | study_case2_h_sweep | FVM, FDM and Analytic error against the 3D surface S2 -5.54 -> -4.61 K (+0.93 K): the film term q t/(2k) of the 10 mm plate named in the item (0.93 K); Lumped moves with it | explained | M1 (+M3) |
| muzychka-case2-analytic | study_case2_reproduce | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| muzychka-case2-analytic | study_case2_review | FVM peak 95.09 -> 96.03 K (+0.94 K, gap to the 3D surface 1.77 -> 0.84 K); printed bound q t/(2k) 0.93 K | explained | M1 |
| paper-case-studies | study_measured_vias | FVM via-array resistance 2.7621 -> 2.7633 K/W (+0.04 %), FDM +0.001 K/W | explained | M1 (bound +0.34 %) |
| paper-case-studies | study_thick_laminate | 300 s timeout in both trees | not run (timeout, heavy) |  |
| paper-case-studies | study_vertical_plate | Lumped board maximum 85.34 -> 85.20 K (-0.2 %), Lumped part read-outs 85.62 -> 88.53 K (+2.9 K, own peak of the part) | explained | M3 |
| rotated-square-3d | study_block_exact_cover | identical output (timings ignored) | unchanged |  |
| rotated-square-3d | study_cut_cells | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| rotated-square-3d | study_cut_cells_fvm | +0.001 in the error table (0.785 -> 0.786 %) | explained | M1 order |
| rotated-square-3d | study_cutcell_capacity | identical output (timings ignored) | unchanged |  |
| rotated-square-3d | study_cutcell_sources | identical output (timings ignored) | unchanged |  |
| rotated-square-3d | study_cutcell_sweep | only timings | unchanged (noise) |  |
| rotated-square-3d | study_disc | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| rotated-square-3d | study_edge_conductance | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| rotated-square-3d | study_exact_cover | residual columns 3.0e-13 -> 1.4e-13 (round-off level) | explained | noise |
| rotated-square-3d | study_part_across_outline | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=1)); both trees alike | not run (memory, over 4 GB) |  |
| rotated-square-3d | study_regression | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| rotated-square-3d | study_remeasure | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| rotated-square-3d | study_square_reference | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| rotated-square-3d | study_turn_frame_reference | +0.001 K in one reference column (246.463 -> 246.464) | explained | M1 order |
| rotated-square-3d | study_turned_part | v2.7.1 stops (uses a read-out key or attribute of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| theory | check_correlations | identical output (timings ignored) | unchanged |  |
| theory | check_mapping_formulas | identical output (timings ignored) | unchanged |  |
| theory | study_fvm_analytic_edges | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| transient-reference-boards | report_transient_boards | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| transient-reference-boards | study_review_checks | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| transient-reference-boards | study_transient_boards | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| via-partial-copper | study_documented_case | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| via-partial-copper | study_frozen | FVM example board 85.294 -> 85.293 K; FDM 84.519 -> 84.623 K (+0.104 K at 2 mm, the same +0.10 K as in models-comparison and small-model-defects) | explained | M2 (FDM) + M1 |
| via-partial-copper | study_fullcopper | 0.001 K in one value | explained | M1 order |
| via-partial-copper | study_matrix | 0.001 K | explained | M1 order |
| via-partial-copper | study_reproduce | 0.001 K | explained | M1 order |
| via-partial-copper | study_variants | killed by the 4 GB watchdog (memory kill (tree EXIT=137, old EXIT=137)); both trees alike | not run (memory, over 4 GB) |  |
| via-partial-copper | study_warning | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
