# Part E: the long studies that the first pass did not run

Program under test: `develop` at `c0dc633`, detached worktree, main `.venv`, `QT_QPA_PLATFORM=offscreen`, library env from `pcb-library/scripts/link_env.sh`. One study at a time (the MAC sweep in at most two shard processes); load 2 to 7 and swap used 0.17 GB (of 1 GB) throughout. No code was changed.

## Totals

Checked 4 studies (4 of 4 run), 41 result groups: UNCHANGED 4 studies, EXPLAINED 0, UNEXPLAINED 0, not run 0.

| Study | Time | Result | Status |
| :-- | --: | :-- | :-- |
| `convection-laws/scripts/study_plate_mac.py` (shards `--both`, `--isolated`, `--big`) | about 15 min wall (README says about an hour) | all 11 rows of README 5 equal to the printed digit: Ra 3e2 1.225 / 1.717 / 1.003 (74854 steps), Ra 1e3 1.447 / 2.182 / 1.046, Ra 3e3 1.490 / 2.766 / 1.098, Ra 1e4 2.036 / 3.248 / 1.160, fine grid 1.439 / 2.170 / 1.049, s=2 Ra 1e3 1.460 / 2.204 / 1.133, s=2 Ra 1e4 2.166 / 3.372 / 1.248 not converged (400000 steps), isolated up 1e3 2.563, down 1e3 2.248, up 1e4 3.859, down 1e4 3.376 (balance and step counts also equal) | UNCHANGED |
| `bare-spot-under-source/scripts/study_real_stormduino.py reference`, then `treat` | reference about 3 min, treat about 4 min | reference peaks 133.14 / 151.16, 118.60 / 124.28, 173.79 / 181.99 K at 0.25 / 0.125 mm as README 7.1; all 18 rows of the treat table (3 windows x 2 cells x program, vert, n=2,3,4,6, cell-fill solver 104.25 / 120.82, 103.33 / 104.22, 151.97 / 158.53) equal README 7.1 | UNCHANGED |
| `bare-spot-under-source/scripts/study_review.py` (to its end) | about 8 min | graded converged peaks 150.06 / 99.84 / 126.03 / 96.26 / 86.68 K and the FVM, vert and n=4+v percentages, 3D solid slab and face (-1.61 % / +0.26 % ...), heat across the window edge (0.707 / 0.475 W), the 1D column (56.9289 K, -0.054 %, +0.087 %), the three bare-spot rows (143.89, 150.16, 105.78 degC and their link, face and 3D columns) equal README 9 and 6 | UNCHANGED |
| `component-heatsink/scripts/base_spreading_study.py` | about 3 min (README: 1.5 min) | the nine-row table and the mesh check (aluminium 1 mm 1.730 / 1.717 +0.8 %, aluminium 6 mm 0.781 / 0.730 +7.0 %, steel 1 mm 6.464 / 6.413 +0.8 %) equal the README | UNCHANGED |

## Notes

* The first-pass failures were handling, not defects: `study_real_stormduino.py` needs `reference` before `treat`; the worktree is not under the main checkout, so the git-ignored Stormduino file was copied into the worktree (`research/gerber-import/data/storm/`, ignored by git) because `real_board.find_file` searches only parents of the worktree. The timeouts of `study_review.py` and `base_spreading_study.py` in the first pass came from a loaded machine (paused time counted in the limit): alone they finish in 8 and 3 minutes.
* The `--both` shard also contains the s=2 cases, which `--big` runs; it was stopped after the fine-grid row to avoid running them twice.
* The memory guard prints "estimate above the available memory" lines in `study_review.py` (3D solid at 0.25 and 0.5 mm); harmless, as in the first pass.
* Outputs are in `research/*/out/` of the worktree (git-ignored); nothing tracked was rewritten.
