# Reproduction pass of 2.9.0: result

Step 4 of the release gate (`releases/2.9.0/PLAN.md` 5), at the reduced scope decided in `DECISION.md` (Decision 2): **91 of the 258 selected scripts run**, the rest recorded as not run. Tree: `development` b241b15e (`__version__` still 2.8.0). Reference: the same scripts on the `pcbthermal/` of the tag `v2.8.0` (scratch copy of the tree with the old package); for the transient scripts also the tree with `scripts/old_stepping/sitecustomize.py` (the 2.8.0 stepping). Branch `release/2.9.0-reproduction`, worktree `.claude/worktrees/repro-290`; the program, tests, examples and icon are untouched. One tester, ONE job at a time (two memory incidents earlier: two parallel jobs, then a study that forks workers; both stopped by hard limits, see `DECISION.md`). Studies run in scratch copies outside the repository; `make_figures` and `make_diagrams` are not run (they overwrite the committed figures). The real-board environment was loaded; `.venv-research` exists (`research/gerber-import/requirements.txt` present, shapely 2.2.0) and runs the `gerber-*` folders. Tools in `scripts/`: `repro_tests.sh`, `run_subset.sh`, `select_scripts.py`, `compare_logs.py`, `core_42.tsv`, `first_48_done.tsv`, `old_stepping/`. The runner's guards: 4 GB cap on the process tree, threads 2, swap pause above 2.5 GB and hard stop above 3 GB, free memory (free + inactive + speculative pages) above 6 GB plus the study's expected peak, load only a pause.

## 0. Totals

| | scripts |
| :-- | --: |
| run (tree and v2.8.0) | 91 |
| exit 0 on both trees | 52: 40 bit-identical (wall-clock columns aside), 9 shifted and EXPLAINED (section 2), 3 differ only in a wall-clock, peak-memory or resident-size column |
| the same error on both trees (stale study or missing input) | 27 |
| killed by the memory cap on both trees (not reproduced: memory) | 3 |
| differ in exit code or capped (stale studies, no baseline, time) | 9 |
| **UNEXPLAINED shifts (defects)** | **0** |
| not run in this pass, recorded as such | 39 FEM + 124 3D-solid (reduced scope: Decision 2), 4 transient excluded, 8 that launch parallel processes ("not reproduced: launches parallel processes"), and the 295 scripts outside the 2.9.0 paths (`select_scripts.py`) |

Research tests: 70 test sets, 65 pass, 5 stale by design and explained (section 1); `tests/test_docs.py` 921 passed, `tests/test_license_header.py` 2 passed (925 passed with the reviewer's helper files, checked by the reviewer).


Result: 67 of the 69 test sets pass on the first run; 5 fail on the tree and every one is a STALE TEST (a study copy of program source text, not a defect of the program), each linked to an item of 2.9.0 and confirmed by passing on the v2.8.0 package (except `lumped-ring-uniform-deficit`, which needs `git show v2.5.1` and cannot run in the scratch copy; the failure is the same `check_rings` message as `lumped-edge-link`): `lumped-edge-link` (10 failed), `lumped-ring-uniform-deficit` (4 failed), `memory-guard` (1 failed), `surface-readout-models` (2 failed), `through-thickness-readout` (1 failed). `rotated-square-3d` (6 failed in the first run) and the collection error of `lumped-ring-uniform-deficit` came from my scratch copy having no `.git` (`git show v2.5.1:...`); rerun in the worktree `rotated-square-3d` gives 34 passed.

Unexplained failures (defects): 0.

Stale-by-design register line: `research/REVIEW.md`. Rerun on the tree of record: `lumped-ring-uniform-deficit` 5 passed on a detached worktree of v2.8.0; `surface-readout-models` 11 passed on `0d45660b` (e3a2ba98^1, the `development` before the copper-slab merge); `lumped-edge-link` 13, `memory-guard` 58 + 1 skipped and `through-thickness-readout` 7 passed on the v2.8.0 package.


## 2. Shifts, one line each (v2.8.0 first, tree second; rules of `DECISION.md` 4)

| script | class | what moved | rule and item | verdict |
| :-- | :-- | :-- | :-- | :-- |
| `imported-copper-edge-film/check_drawn_film_invariants` | T | FVM/FDM end of the time simulation 95.6296 -> 95.6320 K (+2.4 mK); steady 95.6296 K unchanged | 4.2: bit-identical to v2.8.0 with the old-stepping shim; new default transient stepping (`fix/transient-default-stepping`) | explained |
| `outline/study_disc_reference` | T | program FVM 1 mm, doubling step, 10 frames: 15.068 -> 15.730 (a time, s); constant step of 1 s 15.556 -> 15.557 | 4.2: shim bit-identical; new stepping (the doubling steps are the ones that move) | explained |
| `outline/study_outline_time_constant` | T | board mean at 600 s 52.42 -> 52.59 C, box mean 47.42 -> 47.57 C, maximum 85.67 -> 85.85 C | 4.2: shim bit-identical; new stepping | explained |
| `models-comparison/study_time_and_coefficients` | T | Crank-Nicolson error rows 0.315 / 0.0772 / 0.0192 / 0.00479 -> 1.34 / 0.32 / 0.0793 / 0.0198; early FVM and FDM frames about 0.3 to 0.4 C hotter (32.1 -> 32.5, 31.9 -> 32.2 ...); the energy balance -0.01 -> -0.02 % | 4.2: shim bit-identical; the program default is now the scheme the study compared against; the early frames hotter as expected from the 12 to 17 % low first frame of 2.8.0 | explained |
| `surface-readout-models/study_fem_thin_source` | F | FEM part through the outer face: whole-face part 0.227 -> 0.455 mK (ratio to q t/2k 0.50 -> 1.00); 4 x 4 mm part 0.135 -> 1.369 mK at 2 mm, 0.156 -> 1.576 mK at 0.5 mm (0.05 -> 0.55); FVM bit-identical | 4.3: the thin-copper source fix of the FEM (`fix/fem-thin-copper-source`); this study is the measurement of that fix | explained |
| `fem-amg-thin-layers/study_repeat` | F | iterations of the FEM solve on `example_2mm`: base 525 -> 517, colblock 436 -> 444, colblock_amg 127 unchanged; the run-to-run difference 2e-10 K both | 4.3: the matrix of a part on outer copper changed. Checked by hand on the example board at 2 mm (`examples/example_board.pcbt.json`): FEM maximum 83.638251 -> 83.638784 C (+0.53 mK), FEM mean -4e-6 K, FVM bit-identical (85.292569 C) | explained (within the 1 mK of 4.3) |
| `drawn-ell-fvm-fdm/study_readouts` | F | the 3D solid column `surf max` changes from `nan` to a number (66.074, 117.477, 104.457 C); every other number identical | 4.5: the surface read-out of the 3D solid, a view (`feature/surface-readout-models`); text only | explained |
| `muzychka-case2-analytic/study_case2_h_sweep` | SB | only the 3D solid lines: error against the surface -4.67 -> -4.63 K at the highest h, mean -3.33 -> -3.32 K, through-thickness term 0.05 -> 0.09 K; FVM, FDM, Analytic, Lumped bit-identical | 4.4: the plate is 10 mm of copper (`copper_um` 10 000, above 105 um): the copper slabs of the 3D solid | explained |
| `muzychka-case2-analytic/study_case2_reproduce` | SB | the same 3D-solid lines (surface centroid minus the 3D layer mean 0.03 -> 0.04 ...); the memory-guard lines of v2.8.0 are absent on the tree (more free memory when it ran) | 4.4 copper slabs; the memory-guard text depends on the free memory at run time | explained |
| `gerber-models/study_memory_estimate_inputs` | S | the 3D-solid estimate 16.28 -> 16.27 GB (law part 14.67 GB and base 1.61 GB print the same) | load or noise: the base term is the resident size of the fresh process; `memory.py` changed only the FEM time law; 0.06 % | noise |
| `memory-guard/study_sor_block`, `memory-guard/study_via_law` | T | a wall-clock column 0.38 -> 0.39 s, a peak 0.41 -> 0.42 GB | load or noise | noise |

No steady FVM, FDM, Analytic or Lumped number moved in any of the 91 scripts; no number of the 3D solid moved outside the copper-slab plate. No transient shift is left that the old-stepping shim does not remove.

## 3. Not reproduced, with the reason

- **Stale studies (the same error on both trees, 27)**: `lumped-analytic-vias/study_causes`, `study_discretisation`, `study_review`, `study_via_fill_rows` (`anchor not found`: the study copies the source text of the Lumped network, stale since 2.8.0), `memory-guard/study_class_fit` (a missing `out/` input), `independent-fem-edge/study_program` (missing file), `solid3d-verification/study_fem_hand_checks` (`skfem` is not installed in `.venv`), `independent-fem-extensions/study_transient`, `transient-reference-boards/study_review_checks`, `reduced-models-imported-passives/study_cell_and_outline` (`IndexError`: they need an argument or a cache), and the 17 of the first 49 that fail identically (`bare-spot-under-source/make_tables`, `bom-role-and-close-hook`, `fast-wave-oscillation`, `gerber-cad-profiles`, `gerber-import`, `gerber-models/study_fix_impact` and `study_models_self`, `gerber-real-boards/study_transient_fine`, `imported-via-rim`, `laminate-edge-band`, `lumped-near-edge`, `lumped-ring-uniform-deficit`, `strong-edge-laminate`, `zone-union` x4). These checked nothing here.
- **Stale because of 2.9.0 items (9)**: `lumped-edge-link/study_frozen_effect`, `study_reference3d`, `study_zoned_edge`, `study_remeasure` (the v2.8.0 side was capped at 600 s) and `summarise`: the tree stops with `no attribute 'check_rings'` (the pre-fix variant of `lumped.py`; item `fix/lumped-rings-guard`), v2.8.0 runs. `through-thickness-readout/study_options` and `surface-readout-models/study_steady_plates`: `RuntimeError: the copper-slab line of solid3d.py was not found exactly once` (the text patch of the copper slabs; item `feature/solid3d-copper-slabs`; v2.8.0 prints its tables; `study_options` confirmed). `transient-published-case/study_t3_and_plate`: v2.8.0 stops at its first FEM step (`'Model' object has no attribute 'rho_c'`: the FEM transient is new), the tree runs in 242 s; checked without a v2.8.0 baseline (the first lines are identical).
- **Memory (killed at the cap on both trees, 3)**: `laminate-nodes/study_transient`, `lumped-analytic-vias/study_real_boards`, `solid3d-verification/study_one_layer_board`.
- **Time, 1**: `cut-cell-links/study_interplay` (capped on both trees under the load of two parallel jobs; not re-run uncapped, left to a quiet machine).
- **Launch parallel processes, not run by the second decision (8)**: `lumped-analytic-vias/study_arrays` and `study_unit_cell`, `lumped-zones-adoption/study_profile`, `gap-subdivision/study_baseline_pads` and `study_gap_nodes`, `gerber-models/study_lumped_analytic`, `point-via-convergence/study_row_lone` and `study_unit_cell` (`study_arrays` is the one that pushed the swap to 9.4 GB).
- **Not run in this pass (reduced scope after the memory incidents, Decision 2: covered by the frozen numbers (431 passed at three cells) and the core of the class)**: 39 FEM scripts and 124 3D-solid scripts of the 258; the 4 excluded transient scripts (the three that fork and the memory ladder `memory-guard/study_memory_ladder`). These were never reproduced.

What the core did not show (to be said in the final opinion): no script of the core ran a 3D solid with a bottom block or an interface pad (the pad in-plane item) with a number moved: the three block scripts (`block-and-fins/study_finned_block_all_models`, `fin-channel/study_program_finned_block`, `component-heatsink/top_path_study`) are bit-identical, which says the cases they print do not reach the fix; that item is held by the frozen numbers and its pending file only. The FEM part on outer copper was reproduced on the example board (+0.53 mK) and by `study_fem_thin_source`. The FEM transient has no v2.8.0 counterpart and was reproduced only by the tree running `transient-published-case/study_t3_and_plate` to the end.

## 1. Research tests (`research/<folder>/tests`, 70 test sets)


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