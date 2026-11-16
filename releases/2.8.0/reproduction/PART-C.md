# Reproduction pass 2.8.0, part C

Tester part C (18 folders). Tree: `development` 77ed4822 (worktree `repro-280-C`, detached). Baseline: `git archive v2.7.1` in a scratch folder. Python of the main checkout (`.venv`, pyamg present; the two Gerber folders `.venv-research`), `QT_QPA_PLATFORM=offscreen`, `nice -n 10`, one job at a time, under the lock `heavy_lock_C`. Each study ran from its own tree root, `PYTHONPATH` = that tree, 300 s limit (tests 900 s), raw outputs `raw/<tree>__<folder>__<script>` kept in the scratchpad (not committed). Times, paths and 'seconds' values were ignored in the comparison.

Real-board environment: `PCBT_REAL_BOARDS` and `PCBT_GERBER_DATA` = `pcb-library/env/data`, `PCBT_GERBER_SAMPLES` = `pcb-library/env/samples` (`link_env.sh` not run). The Gerber studies read `research/gerber-import/data/` (git-ignored, filled by `fetch_boards.py` from the network): it was absent, so they are 'not run'.

Machine: start load 2.4, swap 1.1 GB of 2 GB, free + inactive about 9 GB; during the run load 1.8 to 6.9 (the peak of 6.9 coincided with other testers, about 04:00 to 04:10, and plate-h-level/plate2d), swap grew to 2.36 GB of 3 GB at the end (not caused by this job alone), free + inactive 10.8 GB at the end. Time: 01:59 to 05:58 for the driver (4 h), then the analysis and four bisect runs.

## Totals (studies, `scripts/study_*.py`; tests are separate)

Scripts checked: **122**. Unchanged **45**; explained **32** (+ 2 load or noise, all timings); checked in new folders without a v2.7.1 baseline **8**; not comparable **2**; not run **33**; **UNEXPLAINED: 0**.

Research tests (`research/<folder>/tests`): 17 of 18 folders pass fully, **1 folder fails: `lumped-zones-adoption` 3 failed, 17 passed** (explained, see section 1). `via-fill` has no tests.

| Folder | Tests |
| :-- | :-- |
| analytic-edge-and-transient | 9 passed |
| component-heatsink | 3 passed |
| convection-laws | 6 passed |
| cut-cell-links | 30 passed |
| face-down-convection | 5 passed |
| gerber-import | 49 passed, 2 skipped |
| gerber-nets | 18 passed |
| horizontal-plate-h | 15 passed |
| independent-fem-extensions | 7 passed |
| laminate-edge-band | 7 passed |
| lumped-zones-adoption | 3 failed, 17 passed |
| plate-h-level | 15 passed |
| published-cases-followup | 19 passed |
| readout-conventions | 5 passed |
| theory-sources | 32 passed |
| through-thickness-readout | 7 passed |
| via-real-board | 26 passed |

## 1. Findings that need a decision (none is a defect of the program)

1. **`research/lumped-zones-adoption` is stale against the 2.8.0 Lumped.** Its `lib/` holds its own zoned Lumped built on the 2.7.1 first link; `research/lumped-zones-adoption/tests/test_zoned_lumped.py::test_zone_code_off_or_without_vias_is_the_program`, `::test_group_outside_the_footprint_is_the_program` and `::test_fallback_decision_does_not_jump_with_the_raster` fail on the tree. Bisect (the folder's tests on archives of the merge commits): 20 passed on v2.7.1, on `e2b3b069` (part read-out) and on `ed6d9c99` (drawn copper); 3 failed on `43aeb1ad` (`fix/lumped-edge-first-link`, item M3) and on every later tree (the pre-film `3a894c41^` too). The program changed on purpose; the study's copy must follow the new first link (executor), or the folder's README must say that the equality checks hold for v2.7.1 only. Study outputs affected (all explained by M3): `study_invariants` (zones off against the program 7e-15 K becomes 0.19 K and 1.69 K on the example board), `study_edge_and_offcentre` (4 of 6 equal becomes 0 of 6), `study_frozen_impact`, `study_review`, and the Lumped columns of the others.

2. **M1 is larger than its frozen band on thick single-node layers**, as the mechanism says (the film is t/(2k) of the layer): 10 mm plate of k 150 (`theory-sources` muzychka case 2 and gci_references): +0.93 K (+1 %) on FVM, FDM and Analytic; 6 mm stainless block (`component-heatsink`): +0.7 K, aluminium +0.1 K, perfect-contact block +0.15 K; via-array resistances (`published-cases-followup/study_shen_vias`) +0.011 K/W (+0.34 %). Bisected on commit trees: every one is bit-identical to v2.7.1 up to `3a894c41^` and moves at the merge of `fix/face-film-half-slab`. The item table of the refreeze states its band from the frozen boards (copper 35 um: median 2e-5 K, maximum 0.04 K); the wording 'up to 0.04 K' should say that it grows with t/k of the layer (the documentation review).

3. **Two studies fail on both trees with an error that is not new** (pre-existing, not 2.8.0): `via-real-board/study_sor_real.py` (`sorvia.py` asserts the network was built with `ladder=False`) and `cut-cell-links/study_review.py` (zero-size array at line 267 after its tables). Stale studies; listed for the executor.

4. **Heavy studies for a separate decision** (300 s timeout reached, nothing compared): see the 'not run' rows marked heavy: `component-heatsink/study_top_path_convergence`, `convection-laws/study_plate_mac`, `cut-cell-links/study_interplay` and `study_scheme_sweep`, `horizontal-plate-h/study_plate_h2d` and `study_solver_checks`, `lumped-zones-adoption/study_core_raster`, `plate-h-level/study_plate2d`, `via-real-board/study_fillin` (5.3 GB reached, memory) and `study_validation_rows`, plus the three that finished in about 270 to 284 s on one tree and timed out on the other (`published-cases-followup/study_coupon_program`, `via-fill/study_via_model_checks`, `lumped-zones-adoption/study_zones_on_245`): they need a 900 s limit, 4 GB of room (fillin) and one run per tree.

5. Not run for lack of data or environment: `laminate-edge-band` (4 studies read `out/refs30.json` and `out/refs_review.json`, made by the scratch independent solver, not in the repository), `independent-fem-extensions` (6 studies need a mode argument and the scratch FEM environment, 'not re-run' as the gate foresaw; `study_plan_costs` ran), `gerber-import` (7) and `gerber-nets` (2): the git-ignored data folder / `out/` of the folder.

## 2. Items that explain the shifts (summary)

* M1 (face film half slab): every FVM, FDM, Lumped and Analytic number of the studies moved by 1e-6 to 4e-3 relative on 35 um copper boards, and by up to 1 % on thick single-node layers (section 1.2).
* M2 (drawn copper faces): `laminate-edge-band/study_harness_impact` example_cut_to_T FDM 2 mm 93.974 to 94.101 K, two_layer_partial FDM 161.325 to 163.131 K (+1.1 %); the new `drawn_*` boards (3 boards) appear as added rows in 5 studies (additions, no baseline).
* M3 (Lumped first link and part read-out): every Lumped column of `published-cases-followup` (near-edge Lumped error against the Seri Lee plate, centre -25.3/-5.3 % becomes -2.7/-2.1 % in the final tree: the intended effect), `lumped-zones-adoption`, `analytic-edge-and-transient/study_transient_both` ('lumped' rows only).
* Analytic transient hot point (`fix/analytic-transient-hot-point`, M0 of the table, no frozen record): `analytic-edge-and-transient/study_review` part 4: time to 63 % of 'vias+sink beside' +0.3 % to +3.2 % against the FVM (the FVM time 33.33 s is unchanged; the CHANGELOG quotes -9 to +3 %).
* M4: not isolated in these studies (`plate-h-level/study_finned_block` moves 0.1 K, within M1 plus M4).
* A1/A2 additions (FEM, surface read-outs): none of the part C studies prints them; no shift attributed to them.
* Report-format changes: none of the part C studies parses `report.txt`, `to_text()` or `to_markdown()`; no 'format change' row.

## 3. Per folder

### analytic-edge-and-transient
Tests: 9 passed. Scripts: unchanged 4, explained 3.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_4l_convergence.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_frozen_impact.py | 0 | 0 | explained | L8 / A: sign of a zero (+0.000 to -0.000) on 2 boards; 3 new rows are the drawn_* boards (addition) |
| study_frozen_transient.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_perlayer_edge.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_review.py | 0 | 0 | explained | Analytic transient time to 63 % of 'vias+sink beside' +0.3 % to +3.2 % of the FVM (FVM time 33.33 s unchanged): fix/analytic-transient-hot-point (CHANGELOG quotes -9 to +3 % at 1 mm); no frozen number |
| study_transient_both.py | 0 | 0 | explained | only the 'lumped' rows move (t63 error -2.6 to -3.6 %, rise 33.572 to 33.739 K, +0.5 %): M3 first link; FVM, FDM, Analytic rows identical |
| study_transient_edge_block.py | 0 | 0 | unchanged | identical output (times ignored) |

### component-heatsink
Tests: 3 passed. Scripts: explained 1, not run 1.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_notes_r2.py | 0 | 0 | explained | block Tj +0.1 K (aluminium) to +0.7 K (stainless 304, 71.7 to 72.4), perfect contact 94.48 to 94.63: M1; bisected on commit trees: unchanged up to ea7791be, moves exactly at 3a894c41 (fix/face-film-half-slab). Larger than the frozen band (0.04 K) because the film is t/(2k) of a 6 mm block of low k |
| study_top_path_convergence.py | timeout | timeout | not run | 300 s timeout in both trees (heavy: needs a separate decision) |

### convection-laws
Tests: 6 passed. Scripts: explained 1, load or noise 1, unchanged 2, not run 1.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_board_effect.py | 0 | 0 | explained | rise 128.96 to 129.13 K (two_layer_partial, +0.13 %, M2 at 2 mm), others 0.01 K: M1/M2 |
| study_cavity.py | 0 | 0 | load or noise | last column is a timing (ms/iterations 0 to 1, 14 to 17); temperatures identical |
| study_laws_table.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_measurement_prediction.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_plate_mac.py | timeout | timeout | not run | 300 s timeout in both trees (heavy: needs a separate decision) |

### cut-cell-links
Tests: 30 passed. Scripts: explained 3, unchanged 2, not run 2.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_across_reference.py | 0 | 0 | explained | 229.104 to 229.105 K (4e-6): M1 |
| study_disc_tee.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_harness_film.py | 0 | 0 | explained | plate_uniform 159.636 to 159.637, plate_pad 349.599 to 349.600 (M1, 1 mK); added rows for the 3 drawn_* boards (addition) |
| study_interplay.py | timeout | timeout | not run | 300 s timeout in both trees (heavy: needs a separate decision) |
| study_review.py | 1 | 1 | explained | tables printed before the common crash: 1 mK (-0.716 to -0.715): M1; both trees stop at the same line 267 (zero-size array), pre-existing |
| study_scheme_sweep.py | timeout | timeout | not run | 300 s timeout in both trees (heavy: needs a separate decision) |
| study_small_cells.py | 0 | 0 | unchanged | identical output (times ignored) |

### face-down-convection
Tests: 5 passed. Scripts: explained 1, unchanged 1.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_down_board_effect.py | 0 | 0 | explained | v271 output empty (the script needs functions missing in v2.7.1: LEN 0 vs 22); tree prints the table with the 3 drawn_* boards: addition. 4 other lines not comparable |
| study_down_laws.py | 0 | 0 | unchanged | identical output (times ignored) |

### gerber-import
Tests: 49 passed, 2 skipped. Scripts: not run 7, unchanged 2, not comparable 2.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_arc_tolerance.py | 1 | 1 | not run | both trees stop with the same error: gerber-import/data (git-ignored) absent: board not found / no usable board box |
| study_gerber_writer.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_kicad_nets.py | 1 | 1 | not run | both trees stop with the same error: gerber-import/data (git-ignored) absent: board not found / no usable board box |
| study_kicad_pixels.py | 1 | 1 | not run | both trees stop with the same error: gerber-import/data (git-ignored) absent: board not found / no usable board box |
| study_native_check.py | 1 | 1 | not run | both trees stop with the same error: gerber-import/data (git-ignored) absent: board not found / no usable board box |
| study_outline.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_reader_conformance.py | 1 | 0 | not comparable | v2.7.1 run stopped at HTTP 429 downloading the files (no data/ in the archive); tree run used data fetched into the git-ignored folder: 27 of 27 files agree within 3 % |
| study_reader_scope.py | 1 | 0 | not comparable | 3 against 14 layers: the v2.7.1 copy had no data folder; no model involved |
| study_render_compare.py | 1 | 1 | not run | both trees stop with the same error: gerber-import/data (git-ignored) absent: board not found / no usable board box |
| study_validation_boards.py | 1 | 1 | not run | both trees stop with the same error: gerber-import/data (git-ignored) absent: board not found / no usable board box |
| study_vias_nets.py | 1 | 1 | not run | both trees stop with the same error: gerber-import/data (git-ignored) absent: board not found / no usable board box |

### gerber-nets
Tests: 18 passed. Scripts: unchanged 2, not run 2.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_angles.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_net_joule.py | 1 | 1 | not run | both trees stop with the same error: input file or `out/` of the folder absent (git-ignored) |
| study_pdn_links.py | 1 | 1 | not run | both trees stop with the same error: input file or `out/` of the folder absent (git-ignored) |
| study_references.py | 0 | 0 | unchanged | identical output (times ignored) |

### horizontal-plate-h
Tests: 15 passed. Scripts: explained 1, unchanged 1, not run 2.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_board_effect.py | 0 | 0 | explained | 30 lines move by at most 0.01 K on rises of 7 to 15 K (1.3e-3 relative): M1/M2; the 3 drawn_* boards are added rows |
| study_correlations.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_plate_h2d.py | timeout | timeout | not run | 300 s timeout in both trees (heavy: needs a separate decision) |
| study_solver_checks.py | timeout | timeout | not run | 300 s timeout in both trees (heavy: needs a separate decision) |

### independent-fem-extensions
Tests: 7 passed. Scripts: not run 6, checked (new folder) 1.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_cluster.py | - | 1 | not run | rc 1 |
| study_hollow_barrel.py | - | 1 | not run | rc 1 |
| study_lshape.py | - | 1 | not run | rc 1 |
| study_plan_costs.py | - | 0 | checked (new folder) | tree only; README numbers found in the output where quoted at that precision |
| study_review_checks.py | - | 1 | not run | rc 1 |
| study_stripes.py | - | 1 | not run | rc 1 |
| study_transient.py | - | 1 | not run | rc 1 |

### laminate-edge-band
Tests: 7 passed. Scripts: unchanged 3, not run 4, explained 1.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_edge_loss_split.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_finer_laminate.py | 1 | 1 | not run | both trees stop with the same error: `out/refs30.json` / `out/refs_review.json` absent (made by the scratch independent solver) |
| study_harness_impact.py | 0 | 0 | explained | example_cut_to_T FDM 2 mm 93.974 to 94.101 K, two_layer_partial FDM 161.325 to 163.131 K (+1.1 %), FVM 162.808: M2 (cut drawn layers at 2 mm only; boards example_board, profile_board +0.005 K: M1); drawn_* rows added |
| study_reference.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_review_reference.py | 1 | 1 | not run | both trees stop with the same error: `out/refs30.json` / `out/refs_review.json` absent (made by the scratch independent solver) |
| study_review_variants.py | 1 | 1 | not run | both trees stop with the same error: `out/refs30.json` / `out/refs_review.json` absent (made by the scratch independent solver) |
| study_solid3d.py | 1 | 1 | not run | both trees stop with the same error: `out/refs30.json` / `out/refs_review.json` absent (made by the scratch independent solver) |
| study_sweep.py | 0 | 0 | unchanged | identical output (times ignored) |

### lumped-zones-adoption
Tests: 3 failed, 17 passed. Scripts: explained 11, not run 2, load or noise 1, unchanged 1.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_3d_barrels.py | 0 | 0 | explained | Lumped columns of the study move 0.1 to 0.3 points: M3 (the study's own Lumped copy and the program Lumped) |
| study_core_raster.py | timeout | timeout | not run | 300 s timeout in both trees (heavy: needs a separate decision) |
| study_cost.py | 0 | 0 | load or noise | times only (0.059 to 0.594 s) |
| study_edge_and_offcentre.py | 0 | 0 | explained | 'zone variants equal to the program on 4 of 6 boards' becomes 0 of 6; part rows +3.7 to +4.1 %: M3. The lib/ zoned Lumped of the study keeps the 2.7.1 first link, so it no longer equals the program. STUDY STALE |
| study_footprint_potential.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_frozen_impact.py | 0 | 0 | explained | zoned-Lumped minus program 4e-7 K becomes -0.040 K (example_board), -0.009 K (hatched_copper); drawn_* rows added (-0.587 K): M3 against the study's stale lib. STUDY STALE |
| study_invariants.py | 0 | 0 | explained | invariant 'zones off equals program' fails: 7e-15 K becomes 0.19 K (2 layers) and 1.69 K (example board, 9 vias); M3 (merge 43aeb1ad, bisected: tests pass at ed6d9c99 and e2b3b069, fail at 43aeb1ad). STUDY STALE: lib/ has the old first link |
| study_multigroup.py | 0 | 0 | explained | Lumped columns +0.4 to +0.5 points: M3 (up to 5 % relative on a small number) |
| study_profile.py | 0 | 0 | explained | Lumped columns -4.5 to -4.1 %, +9.6 to +9.9 %: M3 |
| study_raster.py | 0 | 0 | explained | P245 table counts and 0.03 to 0.04: M3 on the Lumped (and times) |
| study_review.py | 0 | 0 | explained | dead-via offset -1.61 to -1.80 K, max abs 13.1 to 13.9 K: M3 (Lumped first link) against the stale lib; FVM rows change by M1 only |
| study_shen.py | 0 | 0 | explained | FVM/FDM 145.147 to 145.150 K (M1, +3 mK); the Lumped-vs-FVM error columns move +0.3 points: M3 |
| study_solid3d_barrels.py | 0 | 0 | explained | Lumped columns +0.2 to +0.3 points: M3 |
| study_transient.py | 0 | 0 | explained | P245 Lumped times 11.339 to 11.376 s (+0.4 points): M3 |
| study_zones_on_245.py | timeout | 0 | not run | timeout in one tree only (v2.7.1 timeout, tree 0) |

### plate-h-level
Tests: 15 passed. Scripts: unchanged 2, explained 2, not run 1.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_air_data.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_board_effect.py | 0 | 0 | explained | at most 0.01 K on rises of 8 to 16 K (1.3e-3 relative): M1/M2 |
| study_finned_block.py | 0 | 0 | explained | 0.1 K on 65 to 97 K (finned block): M1/M4 (finned block +0.09 K Analytic) |
| study_plate2d.py | timeout | timeout | not run | 300 s timeout in both trees (heavy: needs a separate decision) |
| study_similarity.py | 0 | 0 | unchanged | identical output (times ignored) |

### published-cases-followup
Tests: 19 passed. Scripts: not run 1, explained 4.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_coupon_program.py | 0 | timeout | not run | tree timed out at 300 s while v2.7.1 took 274 s (rc 0): heavy, re-run with 900 s for a separate decision |
| study_lemczyk.py | 0 | 0 | explained | Lumped column (-2.2 to -0.9 %, -6.2 to -2.7 %, +10.5 to +7.6 %): M3 (first link, research lumped-edge-link); other columns identical |
| study_near_edge.py | 0 | 0 | explained | Lumped error at the centre of Seri Lee plate -2.3/-11.6 (v2.7.1) now +2.7/+2.2 on the pre-M1 tree: M3 (-25 to -2.7 %); the intended effect of fix/lumped-edge-first-link; FVM FDM 3D Analytic columns identical |
| study_shen_vias.py | 0 | 0 | explained | FVM, FDM, Analytic via-array resistances +0.011 K/W (3.2348 to 3.2457, +0.34 %): M1; bisected: identical to 2.7.1 on the pre-M1 tree (3a894c41^)  |
| study_table2_strip.py | 0 | 0 | explained | Lumped column only (-28.4 to -15.6 %, -42.2 to -33.6 %): M3 |

### readout-conventions
Tests: 5 passed. Scripts: checked (new folder) 3.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_biot_map.py | - | 0 | checked (new folder) | tree only; README numbers found in the output where quoted at that precision |
| study_thick_cases.py | - | 0 | checked (new folder) | tree only; README numbers found in the output where quoted at that precision |
| study_thin_copper_check.py | - | 0 | checked (new folder) | tree only; README numbers found in the output where quoted at that precision |

### theory-sources
Tests: 32 passed. Scripts: unchanged 18, explained 3.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_culham_truncation.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_effective_medium_sources.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_fill_prediction.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_flux_tube_sources.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_forced_and_air_sources.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_foster_cauer.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_gci_references.py | 0 | 0 | explained | FVM 97.814 to 98.748 K (1 mm), FDM +0.93 K, other case 79.113 to 79.364 K (+0.25 K): M1 of a 10 mm single-node plate (t/(2k)); bisected: pre-M1 tree gives the 2.7.1 numbers, 3a894c41 the new ones. Larger than the frozen band (copper 35 um): the band scales with t/k |
| study_gerber_spec_examples.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_horizontal_face_limits.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_lee_lemczyk_vias.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_lee_yovanovich_check.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_lemczyk_1992.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_multigrid_and_celik.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_muzychka_more_cases.py | 0 | 0 | explained | case 2 (10 mm k 150 plate) centroid 94.46 to 95.39 K for FVM, FDM and Analytic alike (+0.93 K, +1 %): M1; bisected like the line above; case 1b (2 mm layer) unchanged |
| study_natural_convection_sources.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_paper_review_checks.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_peaceman_nonsquare.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_plate_asymptotes_sources.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_strip_table_and_sor_omega.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_via_array_sources.py | 0 | 0 | explained | top minus bottom copper 1.5588 to 1.5591 K/W (2e-4): M1 |
| study_via_formulas_checks.py | 0 | 0 | unchanged | identical output (times ignored) |

### through-thickness-readout
Tests: 7 passed. Scripts: checked (new folder) 4.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_frozen_impact.py | - | 0 | checked (new folder) | tree only; README numbers found in the output where quoted at that precision |
| study_lee.py | - | 0 | checked (new folder) | tree only; README numbers found in the output where quoted at that precision |
| study_options.py | - | 0 | checked (new folder) | tree only; README numbers found in the output where quoted at that precision |
| study_sweep.py | - | 0 | checked (new folder) | tree only; README numbers found in the output where quoted at that precision |

### via-fill
Tests: no tests. Scripts: unchanged 1, not run 1.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_via_fill.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_via_model_checks.py | 0 | timeout | not run | tree timed out at 300 s while v2.7.1 took 284 s (rc 0): heavy, re-run with 900 s for a separate decision |

### via-real-board
Tests: 26 passed. Scripts: unchanged 6, not run 3, explained 1.

| Script | v2.7.1 rc | tree rc | Result | What was compared |
| :-- | :-: | :-: | :-- | :-- |
| study_block_limit.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_edge_distance.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_edge_outline.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_fillin.py | timeout | timeout | not run | 300 s timeout in both trees (heavy: needs a separate decision) |
| study_lumped_gzvia.py | 0 | 0 | explained | Lumped column 63.98 to 64.04 K (+0.06 K), error -1.5 to -1.4 %: M3/M1 |
| study_real_board_effect.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_real_vias_stats.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_solid3d_real.py | 0 | 0 | unchanged | identical output (times ignored) |
| study_sor_real.py | 1 | 1 | not run | both trees stop with the same error: stale study (see section 1.3) |
| study_validation_rows.py | timeout | timeout | not run | 300 s timeout in both trees (heavy: needs a separate decision) |

## 4. What was not verified

The studies that need the data above, the heavy ones, the Gerber folders. The README numbers of the three new folders were compared by search in the output (readout-conventions `study_thick_cases` 50 of 61 numbers at 3 decimals are quoted in the README; through-thickness-readout `study_lee` 10 of 13; the other tables are quoted rounded or in part): a spot check, not a line by line proof. Pending: the owner's totals README.
