# Reproduction pass 2.8.0, part A

Tree under test: `development` 232ba648 (release/2.8.0-reproduction, worktree `.claude/worktrees/repro-280`); the studies ran on 77ed4822 plus the doc-only merge that followed (no program change). Reference: the same scripts run with `pcbthermal/` of the tag `v2.7.1` (scratch copy of the tree with the old package). Machine: load 1.1 to 3.8, swap used 1.1 to 1.7 GB of 2 to 3 GB, free+inactive about 8 GB at the start; one job at a time under `heavy_lock_A`, `nice -n 10`, `QT_QPA_PLATFORM=offscreen`, `PCBT_REAL_BOARDS` and `PCBT_GERBER_DATA` = `pcb-library/env/data`, `PCBT_GERBER_SAMPLES` = `.../env/samples` (`link_env.sh` not run). Timeout 300 s per script and tree. Raw outputs (git-ignored scratch, not committed): `raw/<tree|old>__<folder>__<script>.txt`.

Method: per folder the tests of the folder, then every study script (not the `make_figures.py` / `make_diagrams.py`: they would overwrite the committed figures) on the tree and on v2.7.1; outputs compared with times, paths and report text ignored; each difference linked to an item of `REFREEZE_PLAN.md` (M1 face film half copper, M2 drawn copper faces, M3 Lumped part read-out and first link, M4 block exact cover, memory law).

## Totals of part A (17 folders plus `gerber-models`, 134 study scripts, 15 test sets)

**Scripts: unchanged 30 (22 identical, 8 only timings), explained 40, checked without a v2.7.1 baseline 6, not run 58, UNEXPLAINED 0.**
Not run: 24 input missing (git-ignored `out/`, `data/` or board files absent: the same error in both trees), 14 need an argument or mode, 2 shapely missing, 3 other script errors identical in both trees, 4+2 timeouts at 300 s (heavy), 2 need the 300 s+ cache of `analytic-partial-copper/study_baseline`, 5 stale studies (see 2), 1 memory (study_review killed by the orchestrator at 3.4 GB), 1 memory guard (finding 3). A rerun of `study_baseline` at 1500 s was not made (it is the cache of two other studies and would exceed the 25 min and 4 GB the coordinator allowed).

## 1. Research tests

| folder | result | note |
| :-- | :-- | :-- |
| analytic-partial-copper | 12 passed | |
| bare-spot-under-source | 12 passed | |
| block-warning-remeasure | 2 passed | |
| bom-role-and-close-hook | 17 passed | |
| drawn-copper-faces | 5 passed | |
| gerber-models | 34 passed | |
| imported-copper-edge-film | 5 passed, 1 skipped | |
| lumped-dense-via-group | 5 passed | |
| lumped-edge-link | 13 passed | |
| **lumped-via-groups** | **7 failed, 9 passed** | stale test: `lib/lumped_patch.py` of `lumped-analytic-vias` copies the SOURCE TEXT of `lumped._one_node_network` and raises `anchor not found` since the Lumped first link changed (M3); on v2.7.1 all 16 pass. A study/test defect, not a program defect; same class as the one fixed for `lumped-zones-adoption` on `release/2.8.0-lumped-shifts` |
| **point-via-convergence** | **3 failed, 15 passed** | **already failing on v2.7.1** (same 3 tests: the pinned FVM mean 35.61075 K of commit f2d5c03 is not reproduced; v2.7.1 gives 35.62328, the tree 35.62346: shift tree against v2.7.1 +1.8e-4 K, M1). The pin is stale since an earlier release; not caused by 2.8.0 |
| small-model-defects | 9 passed | |
| sor-with-via-couplings | 15 passed | |
| via-contact-geometry | 8 passed | |
| block-and-fins, outline, stackup | no tests directory | |

## 2. Findings

1. Every shift of an FVM, FDM or Analytic number is at most a few 1e-4 K, except the M2 cases (zone edges inside cells at 2 mm: +1.0 K on `example_cut_to_T` FVM, +5.9 K FVM and +12.2 K FDM on the rectangle of `gerber-models/study_rect_convergence` at 2 mm, shrinking with the cell) and the M1 case with a tiny `k` (`block-and-fins/study_why_coefficients_fail`: the study sets the block `k` to 1e-6, the film now passes the half block `t/(2k)` and the column moves from +28.5 to +58.6 %; the premise of that column is stale).
2. Stale studies (documentation finding, not a defect of the program): `lumped-via-groups` (4 studies and 7 tests, source copy of the Lumped network), `block-and-fins/study_finned_block_all_models` (the monkeypatch `sides_without_fins.wrapped` takes no `board_cover`, the new argument of the block code, M4), `point-via-convergence` pinned tests (stale since before 2.8.0).
3. `point-via-convergence/study_array_board` at the cell 0.0625 mm (451 584 unknowns) is refused by the memory guard in the tree (estimate 10.4 GB against the 10.3 GB limit) and ran on v2.7.1. This is NOT a program change: the FVM/FDM memory law is identical in both trees for that board (6 237 B/unknown, 2.816 GB at 0.0625 mm; measured peaks 4 194 vs 4 223 B/unknown, +0.7 %). The guard reads the resident memory once at the first estimate and the study runs heavy independent 3D references first (process baseline about 7.55 GB in this run, 6.0 GB in the v2.7.1 run: 7.55 + 2.82 = 10.4 refused, 6.0 + 2.82 = 8.8 accepted). Not run: needs about 7 GB (`releases/2.8.0/memory-guard-check`, `MEMORY_GUARD_STUDY_ARRAY_BOARD.md`).
4. Studies whose v2.7.1 twin cannot run because they use an attribute or key of 2.8.0 (`Board.face_film_h`, `heater_peak`): listed as 'checked, no v2.7.1 baseline'.

## 3. Studies (folder | script | what was compared | class | item)

| folder | script | result | class | item |
| :-- | :-- | :-- | :-- | :-- |
| analytic-partial-copper | study_baseline | 300 s timeout in both trees (a rerun at 1500 s was not made: baseline alone is the cache of two other studies and takes more than 25 min) | not run (timeout, heavy) |  |
| analytic-partial-copper | study_candidate | needs the cache of study_baseline (300 s+) | not run (needs baseline cache) |  |
| analytic-partial-copper | study_causes | needs the cache of study_baseline (300 s+) | not run (needs baseline cache) |  |
| analytic-partial-copper | study_review | tree: prints rows then killed by the orchestrator at 3.4 GB (memory); v2.7.1 stops at once (AttributeError face_film_h, 2.8.0 attribute) | not run (memory) |  |
| analytic-partial-copper | study_rows | v2.7.1 stops (AttributeError face_film_h, an attribute of 2.8.0); tree runs, max relative gap program vs committed = 5.5e-3 | checked, no v2.7.1 baseline |  |
| bare-spot-under-source | make_tables | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| bare-spot-under-source | study_margin | identical output (timings ignored) | unchanged |  |
| bare-spot-under-source | study_real_stormduino | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| bare-spot-under-source | study_reference | identical output (timings ignored) | unchanged |  |
| bare-spot-under-source | study_review | 300 s timeout in both trees | not run (timeout, heavy) |  |
| bare-spot-under-source | study_skin | 6 numbers move by at most 1.3e-6 K (rel 6e-6) | explained | M1 |
| bare-spot-under-source | study_validation_rows | only timings differ | unchanged (noise) |  |
| bare-spot-under-source | study_window_sweep | 300 s timeout in both trees | not run (timeout, heavy) |  |
| block-and-fins | block_equivalent_study | Lumped columns +3 to +4 points of the rise (e.g. 12.7 -> 16.9 %), Analytic and FVM columns unchanged | explained | M3 |
| block-and-fins | fin_validation | identical output (timings ignored) | unchanged |  |
| block-and-fins | study_finned_block_all_models | tree: TypeError, the study monkeypatch wrapper sides_without_fins takes no board_cover keyword (new argument of the block code, M4); v2.7.1 ran | not run (stale study) | M4 (API) |
| block-and-fins | study_thick_plate_criterion | bound q t/(2k) quoted 0.34 -> 0.33 % | explained | M1 |
| block-and-fins | study_why_coefficients_fail | Lumped column +1.5 to +3.5 points; the column "FVM, block k t = 0" (+28.5 -> +58.6 %) moves because the study sets the block k to 1e-6 W/mK and the film now passes the half block t/(2k): the premise of the study (k enters only the sheet conductance) no longer holds | explained (study premise stale) | M3 + M1 (t/(2k) with k = 1e-6) |
| block-warning-remeasure | study_block_pads | Lumped columns only: L hot -4.4 -> +1.5 %, L part field max -13.5 -> -7.8 %; Analytic columns identical | explained | M3 |
| block-warning-remeasure | study_review_definitions | Lumped columns only (L part field -11.7 -> +1.2 %, L hot -1.0 -> +1.2 %); Analytic columns identical | explained | M3 |
| bom-role-and-close-hook | study_bom_roles | v2.7.1 copy has no pcb-library (scratch copy): stops; tree runs | checked, no v2.7.1 baseline |  |
| drawn-copper-faces | report_tables | identical output (timings ignored) | unchanged |  |
| drawn-copper-faces | study_adopted | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| drawn-copper-faces | study_cost | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| drawn-copper-faces | study_decomposition | drawn-edge rows FVM +1.95 % (was -8.67 %) at 1 mm, -0.03 % at 0.5 mm, 0.00 % at 0.25 mm: the adopted candidate (error shrinks with the cell) | explained | M2 |
| drawn-copper-faces | study_fem_reference | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| drawn-copper-faces | study_harness_shift | v2.7.1 prints max shifts (e.g. +8.17 K FDM drawn_stripes_pad) of the candidate vs the program; the tree prints 0.00000 K: the candidate is the program now. (Lines differ in 93 places) | explained | M2 |
| drawn-copper-faces | study_harness_t63 | the study compared the program with its candidate: v2.7.1 shows t63 shifts (e.g. +0.019 %), the tree shows 46 curves with 0 moves > 1e-6 (candidate adopted) | explained | M2 |
| drawn-copper-faces | study_outline_boards | study compares the program with the drawn-face candidate; v2.7.1 columns up to -11.8 / +14.6 % become the same as the candidate (-2.58 / 2.53 / 3.47 %) in the tree | explained | M2 |
| drawn-copper-faces | study_pixels | both trees stop with the same error: TypeError: 'NoneType' object is not subscriptable | not run (script error in both trees) |  |
| drawn-copper-faces | study_review | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| gerber-models | study_boards_matrix | both trees stop with the same error: ValueError: no usable board box | not run (input missing) |  |
| gerber-models | study_contrast | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_coverage | identical output (timings ignored) | unchanged |  |
| gerber-models | study_coverage_real | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_diagonal | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_diagonal_gate | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_diagonal_heldout | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_fine_scan | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_fix_impact | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| gerber-models | study_heater_size | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_import_end_to_end | both trees stop with the same error: ValueError: no usable board box | not run (input missing) |  |
| gerber-models | study_import_readers | both trees stop with the same error: ModuleNotFoundError: No module named 'shapely' | not run (module shapely missing) |  |
| gerber-models | study_laminate_reference | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_laminate_reference_reduced | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_lumped_analytic | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_mapping | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_mapping_options | both trees stop with the same error: ValueError: no usable board box | not run (input missing) |  |
| gerber-models | study_memory_estimate_inputs | law part 20.07 -> 20.06 GB (0.05 %) | explained | memory law re-measured |
| gerber-models | study_models_our_board | numbers equal; a memory-guard warning line appears (7.8 GB estimate vs 7.3 GB available now, load dependent) | unchanged (noise) |  |
| gerber-models | study_models_rect_board | Lumped column up to +0.6 K (83.3 -> 83.9); solid3d refusal text now uses the full model name | explained | M3 + report names |
| gerber-models | study_models_self | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_multilayer_real | both trees stop with the same error: KeyError: 'drill' | not run (input missing) |  |
| gerber-models | study_patterns | identical output (timings ignored) | unchanged |  |
| gerber-models | study_patterns_two_layer | identical output (timings ignored) | unchanged |  |
| gerber-models | study_post_board | identical output (timings ignored) | unchanged |  |
| gerber-models | study_raster_error | both trees stop with the same error: ModuleNotFoundError: No module named 'shapely' | not run (module shapely missing) |  |
| gerber-models | study_rect_convergence | at the 2 mm cell FVM 98.11 -> 104.05 K (+5.9 K), FDM 89.38 -> 101.63 K (+12.2 K), Lumped 84.26 -> 84.65; at 1, 0.5, 0.25, 0.1 mm FVM/FDM move <= 0.4 K and shrink with the cell (zone edges inside cells) | explained | M2 (FVM/FDM), M3 (Lumped) |
| gerber-models | study_sampson_boundary | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_scalar_formulas | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_track_width_angle | identical output (timings ignored) | unchanged |  |
| gerber-models | study_transient | both trees stop with the same error: KeyError: 'F' | not run (input missing) |  |
| gerber-models | study_two_layer | both trees stop with the same error: KeyError: 'drill' | not run (input missing) |  |
| imported-copper-edge-film | check_drawn_film_invariants | only network/solve times and RSS differ | unchanged (noise) |  |
| imported-copper-edge-film | study_candidates | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| imported-copper-edge-film | study_cell_effect | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| imported-copper-edge-film | study_decomposition | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| imported-copper-edge-film | study_drawn_film | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| imported-copper-edge-film | study_reference_gap | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| imported-copper-edge-film | study_robustness | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| imported-copper-edge-film | study_truth | both trees stop with the same error: IndexError: list index out of range | not run (needs argument or mode) |  |
| lumped-dense-via-group | study_array_edge | v2.7.1 stops with KeyError 'heater_peak' (read-out key of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-dense-via-group | study_definitions | v2.7.1 stops with KeyError 'heater_peak' (read-out key of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-dense-via-group | study_independent | tree 300 s timeout; v2.7.1 stops with KeyError 'heater_peak' | not run (timeout) |  |
| lumped-dense-via-group | study_layers | Lumped columns +0.9 to +1.0 points (e.g. 56.38 -> 57.40 K); FVM identical | explained | M3 |
| lumped-dense-via-group | study_link_scale | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| lumped-dense-via-group | study_nodes | Lumped values +0.1 to +0.9 K (52.51 -> 53.39 K, +1.7 % of the rise); FVM identical | explained | M3 |
| lumped-dense-via-group | study_placement | tree 300 s timeout; v2.7.1 stops with KeyError 'heater_peak' | not run (timeout) |  |
| lumped-dense-via-group | study_sweep | v2.7.1 stops with KeyError 'heater_peak' (read-out key of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-dense-via-group | study_variants | v2.7.1 stops with KeyError 'heater_peak' (read-out key of 2.8.0); tree runs | checked, no v2.7.1 baseline |  |
| lumped-edge-link | study_frozen_effect | Lumped shifts of the frozen boards (this is the study of the first link); FVM, FDM, Analytic columns identical | explained | M3 |
| lumped-edge-link | study_reference3d | numbers move by at most 1.6e-5 K | explained | M1 |
| lumped-edge-link | study_remeasure | 300 s timeout in both trees | not run (timeout, heavy) |  |
| lumped-edge-link | study_zoned_edge | the study measures the zoned Lumped against the program: program errors -6.3 -> -1.7 %, 5.1 % (first link adopted) | explained | M3 |
| lumped-edge-link | summarise | summary over 301 cases of Lumped errors: mean -15.1 % -> -9.3 % (first link adopted) | explained | M3 |
| lumped-via-groups | study_cell_link | identical output (timings ignored) | unchanged |  |
| lumped-via-groups | study_cluster_in_cell | tree: RuntimeError anchor not found (lib/lumped_patch.py copies the source text of lumped._one_node_network; the Lumped code changed in M3); v2.7.1 ran | not run (stale study) | M3 (source copy) |
| lumped-via-groups | study_example_board | same anchor error | not run (stale study) | M3 (source copy) |
| lumped-via-groups | study_family | both trees stop with the same error: /opt/homebrew/Cellar/python@3.13/3.13.5/Frameworks/Python.framework/Versions/3.13/lib/pyth | not run (error in both trees) |  |
| lumped-via-groups | study_fish_case | identical output (timings ignored) | unchanged |  |
| lumped-via-groups | study_holdout | both trees stop with the same error: /opt/homebrew/Cellar/python@3.13/3.13.5/Frameworks/Python.framework/Versions/3.13/lib/pyth | not run (error in both trees) |  |
| lumped-via-groups | study_outside | same anchor error | not run (stale study) | M3 (source copy) |
| lumped-via-groups | study_review | both trees stop with the same error: FileNotFoundError: [Errno 2] No such file or directory: '/Volumes/SSD/PROJETOS/pcb-thermal | not run (input missing) |  |
| lumped-via-groups | study_zone_sensitivity | same anchor error | not run (stale study) | M3 (source copy) |
| outline | outline_rectangle_study | Lumped error columns (e.g. -4.0 -> -0.7 %); FVM/FDM columns identical | explained | M3 |
| outline | study_disc_reference | lumped 1 mm +2.22 -> +1.15 %; fvm 0.5 mm -0.12 -> -0.11 %  | explained | M3, M1 |
| outline | study_edge_on_grid_lines | Lumped error columns -7.0 -> -4.0 %, -10.8 -> -10.1, -1.7 -> -1.3 | explained | M3 |
| outline | study_outline_time_constant | identical output (timings ignored) | unchanged |  |
| point-via-convergence | study_array_board | tree: MemoryGuardError at the finest cell (0.0625 mm): refused only because of the process baseline of the study's own earlier 3D work (7.55 GB + 2.82 GB > 10.3 GB limit); law identical in both trees; v2.7.1 ran with a 6.0 GB baseline | not run (memory guard, needs about 7 GB) | none (not a program change) |
| point-via-convergence | study_edge_via | footprint timings only (0.38 -> 0.37 ms) | unchanged (noise) |  |
| point-via-convergence | study_example_board | two numbers move by 0.01 K (rel 1.2e-4) | explained | M1 |
| point-via-convergence | study_reference_3d | identical output (timings ignored) | unchanged |  |
| point-via-convergence | study_row_lone | identical output (timings ignored) | unchanged |  |
| point-via-convergence | study_solid3d | identical output (timings ignored) | unchanged |  |
| point-via-convergence | study_solvers | 1.6e-11 K | unchanged (noise) |  |
| point-via-convergence | study_target_radius | identical output (timings ignored) | unchanged |  |
| point-via-convergence | study_unit_cell | identical output (timings ignored) | unchanged |  |
| small-model-defects | study_far_via | 0.736 -> 0.750 % | explained | M1 |
| small-model-defects | study_fdm_gap | the study compared the FDM arithmetic and the harmonic candidate; v2.7.1 differences (e.g. -18.9 / -5.7 %, +0.0396 K) vanish in the tree: harmonic (candidate) is adopted for the drawn cut faces | explained | M2 |
| small-model-defects | study_frozen_impact | FVM/FDM example_cut_to_T at 2 mm: 93.37 -> 94.39 K (+1.02 K, +1.5 % of the rise) | explained | M2 |
| small-model-defects | study_grouping_impact | Lumped lines only | explained | M3 |
| small-model-defects | study_separate_zones | Lumped column +1.9 K (59.56 -> 61.48 K); FVM, FDM, Analytic columns identical to 0.01 K | explained | M3 |
| small-model-defects | study_solid3d_gridline | only timings differ | unchanged (noise) |  |
| small-model-defects | study_solid3d_scatter | identical output (timings ignored) | unchanged |  |
| sor-with-via-couplings | study_block_over | sweeps 3610 -> 3620 (iteration count, 0.3 %) | explained | M1 |
| sor-with-via-couplings | study_failure | residual 5.931e-06 -> 5.930e-06; 494.964 -> 494.967 | explained | M1 |
| sor-with-via-couplings | study_real_board | time column 23.2 -> 23.3 s | unchanged (noise) |  |
| sor-with-via-couplings | study_review | deprecation-warning path only | unchanged (noise) |  |
| sor-with-via-couplings | study_stiffness | identical output (timings ignored) | unchanged |  |
| sor-with-via-couplings | study_variants | 0.01 in a table (rel 2e-5) | explained | M1 |
| stackup | stackup_outline_study | one column +1.2 -> +1.8 % (Lumped, same for every row); other columns identical | explained | M3 |
| stackup | study_dielectric_sensitivity | identical output (timings ignored) | unchanged |  |
| stackup | study_inner_copper_1oz | FVM Tmax 2-layer 100.82 -> 100.86 K (+0.04 K), 4-layer 90.14 -> 90.12 K (-0.02 K): the example-board zones sit on cells at 2 mm, so M2 moves it either way; M1 moves it hotter (<= 0.04 K) | explained | M1 + M2 |
| stackup | study_real_1oz_stackups | rises move by at most 0.1 K (72.33 -> 72.32 K) | explained | M1 + M2 |
| via-contact-geometry | study_barrel_length | FVM resistance error of the via unit cell +0.3 to +0.9 points (e.g. +9.9 -> +10.4 %); unit cell with h_bottom 1e7: the film 1/h adds t/(2k) of the copper layer, about 0.2 K/W in 28 K/W (+0.8 %); reference columns identical | explained | M1 |
| via-contact-geometry | study_barrel_reference3d | FVM error columns +0.3 to +0.9 points; reference 3D numbers identical | explained | M1 |
| via-contact-geometry | study_barrel_solid | FVM error column +0.9 points | explained | M1 |
| via-contact-geometry | study_contact_set | both trees stop with the same error: study_contact_set.py: error: the following arguments are required: mode | not run (needs argument or mode) |  |
| via-contact-geometry | study_documented_case | identical output (timings ignored) | unchanged |  |
| via-contact-geometry | study_frozen | FDM example_cut_to_T 93.974 -> 94.101 K (+0.127 K) | explained | M2 |
| via-contact-geometry | study_frozen_models | FVM/FDM example_cut_to_T +0.127 K, Lumped lines (21) | explained | M2, M3 |
| via-contact-geometry | study_reference_set | both trees stop with the same error: study_reference_set.py: error: the following arguments are required: mode | not run (needs argument or mode) |  |
| via-contact-geometry | study_well | identical output (timings ignored) | unchanged |  |
| via-contact-geometry | summarize_barrel | summary of the barrel-length table: +0.3 to +1.4 points (FVM column) | explained | M1 |
