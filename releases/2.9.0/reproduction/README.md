# Reproduction pass of 2.9.0: PARTIAL, stopped after 30 minutes of waiting (load of another project)

**Status: 64 of the 91 scripts of the reduced scope are run (49 before, 15 of the core of 42 now); the batch stopped itself at `outline/study_disc_reference` because the guard waited 30 minutes (the load of the machine was 12 from other sessions, free+inactive memory 7.4 GB under the 8 GB the guard asks).** Not finished; no unexplained shift so far (0 defects). The final README (totals of 91 of 258 run) is written when the core ends.

Tree: `development` b241b15e (`__version__` still 2.8.0). Reference: the same scripts on the `pcbthermal/` of the tag `v2.8.0`. Branch `release/2.9.0-reproduction`, worktree `.claude/worktrees/repro-290`, one tester, ONE job at a time (two memory incidents with two jobs and with a study that forks workers: see `DECISION.md` Decision 2). Scope, rules and the classes of shift: `DECISION.md`. Studies run in scratch copies outside the repository; `make_figures` and `make_diagrams` are not run. Real-board environment loaded; `.venv-research` exists and is used for `gerber-*`. Tools in `scripts/`: `repro_tests.sh`, `run_subset.sh` (tree, v2.8.0 and, for class T, the tree with the old-stepping shim; caps 600 s for T and F, 300 s for the rest; 4 GB cap on the process tree; guard on swap, free memory and load), `select_scripts.py`, `compare_logs.py`, `core_42.tsv` (the core list), `first_48_done.tsv`.

## 1. Research tests (`research/<folder>/tests`, 69 folders with a tests directory; plus `research/theory/tests`)

Result: 67 of the 69 test sets pass on the first run; 5 fail on the tree and every one is a STALE TEST (a study copy of program source text, not a defect of the program), each linked to an item of 2.9.0 and confirmed by passing on the v2.8.0 package (except `lumped-ring-uniform-deficit`, which needs `git show v2.5.1` and cannot run in the scratch copy; the failure is the same `check_rings` message as `lumped-edge-link`): `lumped-edge-link` (10 failed), `lumped-ring-uniform-deficit` (4 failed), `memory-guard` (1 failed), `surface-readout-models` (2 failed), `through-thickness-readout` (1 failed). `rotated-square-3d` (6 failed in the first run) and the collection error of `lumped-ring-uniform-deficit` came from my scratch copy having no `.git` (`git show v2.5.1:...`); rerun in the worktree `rotated-square-3d` gives 34 passed.

Unexplained failures (defects): 0.

Stale-by-design register line: `research/REVIEW.md`. Rerun on the tree of record: `lumped-ring-uniform-deficit` 5 passed on a detached worktree of v2.8.0; `surface-readout-models` 11 passed on `0d45660b` (e3a2ba98^1, the `development` before the copper-slab merge); `lumped-edge-link` 13, `memory-guard` 58 + 1 skipped and `through-thickness-readout` 7 passed on the v2.8.0 package.

## 2. Studies: judged shifts (tree against v2.8.0; `compare_logs.py` plus a by-hand mask of wall-clock lines)

Direction of the comparison: v2.8.0 first, tree second. Bit-identical = every printed number the same.

| script | class | result | cause and item |
| :-- | :-- | :-- | :-- |
| 24 Analytic and steady folders of the first 48 (`analytic-edge-and-transient` 7 scripts, `analytic-edge-spatial`, `bochkov-robin-check`, `convection-laws`, `face-down-convection`, `fin-channel-sources`, `gerber-nets`, `gerber-real-boards/study_time_memory`, `horizontal-plate-h`, `laminate-nodes/study_vertical_face`, `power-calculator`, `stackup`, `through-thickness-readout/study_lee` and `study_sweep`, `via-contact-geometry`, `via-fill`, `lumped-via-groups`, `gerber-models/study_rect_convergence`) | S, sample, T | bit-identical except wall-clock columns | none: no steady FVM, FDM, Analytic or Lumped number moved, no Analytic transient number moved |
| `imported-copper-edge-film/check_drawn_film_invariants` | T | the FVM/FDM end of the time simulation 95.6296 K (v2.8.0) becomes 95.6320 K (+2.4 mK); the steady 95.6296 K is unchanged; with the old-stepping shim the output is bit-identical to v2.8.0 | EXPLAINED: the new default transient stepping (`fix/transient-default-stepping`, rule 4.2) |
| `muzychka-case2-analytic/study_case2_h_sweep` (and `study_case2_reproduce`, 18 lines differ) | SB | only the 3D solid lines move: error against the surface -4.67 -> -4.63 K at the highest h, mean -3.33 -> -3.32 K, the through-thickness term 0.05 -> 0.09 K; FVM, FDM, Analytic, Lumped bit-identical | EXPLAINED: the plate is 10 mm of copper (`copper_um` = 10 000 um > 105 um), the 3D solid copper slabs (rule 4.4) |
| `gerber-models/study_memory_estimate_inputs` | S | the 3D-solid estimate 16.28 -> 16.27 GB (law part 14.67 GB and base 1.61 GB printed the same; four lines) | load or noise: the base term is the resident size of the fresh process (rounded), the law of the 3D solid is unchanged by `memory.py` (its 2.9.0 change is the FEM time law); 0.06 % |
| `memory-guard/study_sor_block`, `study_via_law`, `laminate-slabs-and-local-rule/study_solid_slices`, `convection-laws/study_board_effect` | T, S | differences only in a wall-clock or peak-memory column (0.38 -> 0.39 s, peak 0.41 -> 0.42 GB, 0.N s -> 1.N s, 113 s -> 105 s) | load or noise |
| `lumped-edge-link/study_frozen_effect`, `study_reference3d`, `study_zoned_edge`, `summarise`, `study_remeasure` | T | tree stops with `no attribute 'check_rings'` (or a missing `out/` file), v2.8.0 runs; `study_remeasure` took 606 s on v2.8.0 and was capped | STALE STUDY (the pre-fix variant of `lumped.py`, item `fix/lumped-rings-guard`); not reproduced |
| `through-thickness-readout/study_options` | SB | tree: `RuntimeError: the copper-slab line of solid3d.py was not found exactly once`; v2.8.0 prints its tables | STALE STUDY, confirmed: the text patch of the copper-slab line (item `feature/solid3d-copper-slabs`); not reproduced |

Unexplained shifts (defects): **0**.

### Not reproduced (the same failure on both trees, or a cap)

- Same error on both trees (stale study or missing input): `lumped-analytic-vias/study_causes`, `study_discretisation`, `study_review`, `study_via_fill_rows` (`anchor not found`: the study copies the source text of the Lumped network, stale since 2.8.0), `memory-guard/study_class_fit` (missing `out/` input), and the 11 of the first 48 that failed identically (`bare-spot-under-source/make_tables`, `bom-role-and-close-hook`, `fast-wave-oscillation`, `gerber-cad-profiles`, `gerber-import`, `gerber-models/study_fix_impact` and `study_models_self`, `gerber-real-boards/study_transient_fine`, `imported-via-rim`, `laminate-edge-band`, `lumped-near-edge`, `lumped-ring-uniform-deficit`, `strong-edge-laminate`, `zone-union` x4).
- Memory cap (exit 137, killed at 6 GB in the first resume, 4 GB now): `laminate-nodes/study_transient` (both trees), `lumped-analytic-vias/study_real_boards` (both trees).
- Time (cap): `cut-cell-links/study_interplay` (both trees, under load; not re-run uncapped), `lumped-edge-link/study_remeasure` (v2.8.0 side capped).
- Launches parallel processes, not run by the second decision: `lumped-analytic-vias/study_arrays` and `study_unit_cell`, `lumped-zones-adoption/study_profile`, `gap-subdivision/study_baseline_pads` and `study_gap_nodes`, `gerber-models/study_lumped_analytic`, `point-via-convergence/study_row_lone` and `study_unit_cell`. (`study_arrays` is the one that pushed the swap to 9.4 GB when the memory cap saw only the parent process.)

## 3. Still to run (core of 42, `scripts/core_42.tsv`): 27 left

`outline` x2, `surface-readout-models/study_transient`, `transient-published-case/study_t3_and_plate` (T, 4 left of 19); the 8 FEM scripts (`drawn-ell-fvm-fdm/study_readouts`, `surface-readout-models/study_fem_thin_source`, `independent-fem-extensions/study_transient`, `independent-fem-edge/study_program`, `drawn-copper-faces/study_harness_shift`, `fem-amg-thin-layers/study_repeat`, `transient-reference-boards/study_review_checks`, `solid3d-verification/study_fem_hand_checks`); the 8 3D-solid scripts (`block-and-fins/study_finned_block_all_models` and `fin-channel/study_program_finned_block` and `component-heatsink/top_path_study` for the top block, `solid3d-verification/study_one_layer_board` and `effective-conductivity/study_program_vs_coupon` for copper and the laminate, `through-thickness-readout/study_frozen_impact` and `surface-readout-models/study_steady_plates` for the surface read-out, `small-model-defects/study_solid3d_gridline`); the 7 samples (`lumped-zone-placement`, `paper-notes-policy`, `plate-h-level`, `readout-conventions`, `reduced-models-imported-passives`, `sor-with-via-couplings`, `via-well-sheet-order`). No script of the core has a bottom block or a part on outer copper chosen by reading the script; the pick is by the folder's subject (`DECISION.md` 2.1 asks for them: to be confirmed when the outputs are read).

Not run in this pass (recorded, never as reproduced): 39 FEM, 124 3D-solid and the 4 excluded transient scripts of the 258 selected, with the reason "reduced scope after the memory incidents (Decision 2): covered by the frozen numbers and by the core of the class"; the 295 scripts outside the 2.9.0 paths (`select_scripts.py`).

## 4. Research tests, raw list

| folder | exit | time | last line | note |
| :-- | --: | --: | :-- | :-- |
| analytic-edge-and-transient | 0 | 5s | 9 passed in 4.14s |  |
| analytic-edge-spatial | 0 | 3s | 19 passed in 3.30s |  |
| analytic-partial-copper | 0 | 5s | 12 passed in 4.49s |  |
| bare-spot-under-source | 0 | 47s | 12 passed in 46.89s |  |
| block-warning-remeasure | 0 | 1s | 2 passed in 0.63s |  |
| bochkov-robin-check | 0 | 1s | 5 passed in 0.64s |  |
| bom-role-and-close-hook | 0 | 0s | 17 passed in 0.35s |  |
| component-heatsink | 0 | 1s | 3 passed in 0.42s |  |
| convection-laws | 0 | 3s | 6 passed in 2.93s |  |
| cut-cell-links | 0 | 5s | 30 passed in 4.42s |  |
| drawn-copper-faces | 0 | 1s | 5 passed in 0.72s |  |
| drawn-ell-fvm-fdm | 0 | 0s | 3 passed in 0.47s |  |
| effective-conductivity | 0 | 9s | 14 passed in 7.93s |  |
| face-down-convection | 0 | 0s | 5 passed in 0.34s |  |
| fast-wave-oscillation | 0 | 8s | 13 passed in 7.46s |  |
| fdm-inset-edge | 0 | 1s | 11 passed in 1.02s |  |
| fem-amg-thin-layers | 0 | 4s | 21 passed, 1 skipped in 3.92s | 21 passed, 1 skipped (the last log line is a pyamg message) |
| fin-channel-sources | 0 | 1s | 13 passed in 0.93s |  |
| fin-channel | 0 | 7s | 18 passed in 6.66s |  |
| gap-subdivision | 0 | 2s | 8 passed in 1.40s |  |
| gerber-cad-profiles | 0 | 2s | 36 passed, 1 skipped in 1.28s |  |
| gerber-import | 0 | 1s | 49 passed, 2 skipped in 1.34s |  |
| gerber-models | 0 | 44s | 34 passed in 43.14s |  |
| gerber-nets | 0 | 1s | 18 passed in 0.62s |  |
| gerber-real-boards | 0 | 8s | 50 passed, 7 skipped in 8.34s |  |
| horizontal-plate-h | 0 | 23s | 15 passed in 23.03s |  |
| imported-copper-edge-film | 0 | 3s | 5 passed, 1 skipped in 2.05s |  |
| imported-via-rim | 0 | 1s | 2 passed in 0.47s |  |
| independent-fem-edge | 0 | 3s | 11 passed, 1 skipped in 3.61s |  |
| independent-fem-extensions | 0 | 1s | 7 passed in 0.27s |  |
| laminate-edge-band | 0 | 1s | 7 passed in 0.67s |  |
| laminate-nodes | 0 | 4s | 20 passed in 3.66s |  |
| laminate-slabs-and-local-rule | 0 | 1s | 7 passed in 1.27s |  |
| lumped-analytic-vias | 0 | 15s | 10 passed in 14.55s |  |
| lumped-dense-via-group | 0 | 2s | 5 passed in 1.42s |  |
| lumped-edge-link | 1 | 0s | 10 failed, 3 passed, 25 warnings in 0.64s | STALE TEST, item e12 (lumped rings guard): the study copy of the pre-fix `lumped.py` has no `check_rings`; 13 passed on the v2.8.0 package |
| lumped-near-edge | 0 | 2s | 4 passed in 1.09s |  |
| lumped-ring-uniform-deficit | 2 | 0s | 1 error in 0.40s | STALE TEST, item e12: same `check_rings` missing in the study copy of `lumped.py` (4 failed; the first run in a scratch copy without .git gave a collection error: not a defect) |
| lumped-via-groups | 0 | 10s | 11 passed in 9.85s |  |
| lumped-zone-placement | 0 | 1s | 4 passed in 0.71s |  |
| lumped-zones-adoption | 0 | 2s | 20 passed in 1.72s |  |
| memory-guard | 1 | 2s | 1 failed, 58 passed in 1.94s | STALE TEST, transient stepping item: `review_copies.transient_from_network_one_factor` is a copy of the 2.8.0 stepping and takes no `first_stage_split`; 58 passed + 1 skipped on the v2.8.0 package |
| muzychka-case2-analytic | 0 | 12s | 8 passed in 11.27s |  |
| paper-case-studies | 0 | 3s | 31 passed in 2.32s |  |
| paper-notes-policy | 0 | 0s | 5 passed in 0.06s |  |
| plate-h-level | 0 | 10s | 15 passed in 10.48s |  |
| point-via-convergence | 0 | 11s | 17 passed in 9.92s |  |
| published-cases-followup | 0 | 4s | 19 passed in 4.43s |  |
| readout-conventions | 0 | 2s | 5 passed in 1.97s |  |
| reduced-models-imported-passives | 0 | 2s | 9 passed in 1.85s |  |
| rotated-square-3d | 1 | 3s | 6 failed, 28 passed in 1.93s | 6 failed only in the scratch copy without .git (`git show v2.5.1`); rerun in the worktree: 34 passed |
| small-model-defects | 0 | 2s | 9 passed in 1.68s |  |
| solid3d-verification | 0 | 0s | 1 passed in 0.35s |  |
| sor-with-via-couplings | 0 | 2s | 15 passed, 11 warnings in 2.13s |  |
| strong-edge-laminate | 0 | 2s | 6 passed in 1.60s |  |
| surface-readout-models | 1 | 2s | 2 failed, 9 passed in 2.08s | STALE TEST, item 3D solid copper slabs: the study patches the text of the copper-slab line of `solid3d.py` ("not found exactly once"); 11 passed on v2.8.0 |
| theory-sources | 0 | 5s | 32 passed in 3.92s |  |
| theory | 0 | 0s | 5 passed in 0.02s |  |
| through-thickness-readout | 1 | 1s | 1 failed, 6 passed in 0.57s | STALE TEST, item 3D solid copper slabs: same patch on `solid3d.py` text; 7 passed on v2.8.0 |
| transient-published-case | 0 | 1s | 8 passed in 0.85s |  |
| transient-reference-boards | 0 | 2s | 8 passed in 2.10s |  |
| via-contact-geometry | 0 | 1s | 8 passed in 0.49s |  |
| via-edge-image | 0 | 2s | 7 passed in 1.79s |  |
| via-partial-copper | 0 | 3s | 16 passed in 3.20s |  |
| via-real-board | 0 | 1s | 26 passed in 0.60s |  |
| via-well-sheet-order | 0 | 0s | 2 passed in 0.40s |  |
| young-omega-tiles | 0 | 1s | 23 passed in 0.59s |  |
| zone-union | 0 | 1s | 9 passed in 0.92s |  |
| theory | 0 | 1s | 5 passed in 0.02s |  |
| tests/test_docs.py | 0 | 2s | 921 passed in 2.56s |  |
| tests/test_license_header.py | 0 | 2s | 2 passed in 0.85s |  |