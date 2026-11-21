# Reproduction pass of 2.9.0: PARTIAL result (research tests complete; studies still running)

Tree: `development` b241b15e (`__version__` still 2.8.0). Branch `release/2.9.0-reproduction`, worktree `.claude/worktrees/repro-290`; the program, tests, examples and icon are untouched. One tester (not four), one heavy job at a time. Reference for the studies: the same scripts run with `pcbthermal/` of the tag `v2.8.0` (scratch copy of the tree with the old package). Studies run in scratch copies outside the repository, so no output is committed; `make_figures.py` and `make_diagrams.py` are not run (they overwrite the committed figures). Real-board environment loaded (`PCBT_REAL_BOARDS`, `PCBT_GERBER_DATA`, `PCBT_GERBER_SAMPLES` from `pcb-library/scripts/link_env.sh`). `.venv-research` exists (`research/gerber-import/requirements.txt` present; shapely 2.2.0) and is used for the `gerber-*` folders. Scripts in `scripts/`: `repro_tests.sh`, `repro_scripts.sh` (tree then v2.8.0 per script, timeout 75 s, a timeout on the tree skips the baseline), `compare_logs.py` (timings, paths and addresses ignored; classes identical / numeric / text).

## 1. Research tests (`research/<folder>/tests`, 69 folders with a tests directory; plus `research/theory/tests`)

Result: 67 of the 69 test sets pass on the first run; 5 fail on the tree and every one is a STALE TEST (a study copy of program source text, not a defect of the program), each linked to an item of 2.9.0 and confirmed by passing on the v2.8.0 package (except `lumped-ring-uniform-deficit`, which needs `git show v2.5.1` and cannot run in the scratch copy; the failure is the same `check_rings` message as `lumped-edge-link`): `lumped-edge-link` (10 failed), `lumped-ring-uniform-deficit` (4 failed), `memory-guard` (1 failed), `surface-readout-models` (2 failed), `through-thickness-readout` (1 failed). `rotated-square-3d` (6 failed in the first run) and the collection error of `lumped-ring-uniform-deficit` came from my scratch copy having no `.git` (`git show v2.5.1:...`); rerun in the worktree `rotated-square-3d` gives 34 passed.

Unexplained failures (defects): 0.

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