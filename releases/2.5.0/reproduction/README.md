# Reproduction pass of release 2.5.0: the research folders on the final tree

The READMEs of the research folders hold numbers measured on older programs. This pass re-runs the studies of the folders that import the program on `develop` at `e97b62f` (the 2.5.0 candidate, version string still 2.4.5) and compares every printed table with the folder README and with the pass of 2.4.5 (`releases/2.4.5/reproduction/README.md`); the frozen reference numbers of the release harness were compared with a run on the tag v2.4.5 (Part D). The program was not touched. Four testers worked in parallel, one job at a time each: A (this branch's owner), B, C, D (detached worktrees); a fifth, F, was given the long convection sweep and did not run it.

Items of 2.5.0 that can move a number: zonal Lumped (ZONES), Lumped footprint potentials (FOOT), Robin Analytic edge (ROBIN), laminate options, face term in the profile curves, via edge image (EDGEIMG), symmetric LU (SYMLU, last bits and memory), memory guard (GUARD), imported copper, laminar default for new projects, edge coefficient limit (HLIM), partial-copper warning.

## 1. Totals

Units differ by part (a study script, a table group, a harness result set), so the parts are shown separately and the overall line adds the units as counted by each tester.

| Part | Folders | Unit | Checked | Unchanged | EXPLAINED | UNEXPLAINED | Not run |
| :-- | :-- | :-- | --: | --: | --: | --: | --: |
| A | analytic-2-6 (now analytic-edge-and-transient), analytic-edge-spatial, analytic-partial-copper, bare-spot-under-source, block-and-fins, component-heatsink, convection-laws, effective-conductivity, fin-channel, fin-channel-sources, gap-subdivision | study script | 62 | 58 | 4 | 0 | 4 |
| B | gerber-cad-profiles, gerber-import, gerber-models, gerber-nets, gerber-real-boards | table group or output file | 35 | 20 | 15 | 0 | the scripts that do not import the program (about 30), 2 that need patched copies of the program |
| C | horizontal-plate-h, laminate-2-6 (now laminate-slabs-and-local-rule), models-comparison, lumped-analytic-vias, lumped-via-groups, lumped-zones-adoption, laminate-nodes, memory-guard | study | 62 compared (76 run) | 60 | 2 groups | 0 | 7 |
| D | outline, paper-case-studies, plate-h-level, point-via-convergence, power-calculator, releases/regression-harness, rotated-square-3d, solid3d-verification, sor-with-via-couplings, stackup, theory-sources, theory, via-edge-image, via-fill, via-partial-copper, via-real-board, young-omega-tiles, zone-union | test run, harness result set or study | 70 | 55 | 15 | 0 | about 77 scripts (their tests pass) |
| **all** | | | **229** | **193** | **36** | **0** | |

**UNEXPLAINED: 0** in every part. Tests: B 197 passed; D 16 test runs green (frozen numbers 317 passed at 2, 1 and 0.5 mm, 24 passed in `releases/regression-harness/tests`, the folders' own tests and the docs and licence gates); C and A ran studies only (the folders' tests were not run in those parts).

Not run, with the reason (overall): `convection-laws/study_plate_mac.py` (about an hour, own solvers; given to tester F, whose shards were paused because the machine was out of swap; it does not import the program except for the law tables); the end of `bare-spot-under-source/study_review.py`, the mesh check of `component-heatsink/base_spreading_study.py` and `bare-spot-under-source/study_real_stormduino.py` (the last needs a one-hour reference run first) in Part A, stopped on the coordinator's order for a tight machine; the three `memory-guard` studies and `laminate-nodes/study_analytic.py` in Part C; the studies listed in Part D section 5 and Part B section 4.

## 2. What moved, and why (by item)

| Item | Where it shows | Numbers |
| :-- | :-- | :-- |
| ROBIN (Analytic edge) | every Analytic column of a board with an edge coefficient | harness: 39 records, e.g. example_board 85.1021 -> 84.5774 degC (-0.52 K), part_across_outline 216.03 -> 208.93 (-7.1 K, the largest); `models-comparison/validation_study` Analytic column in all 19 rows (example board 85.10 -> 84.58); `block-and-fins` Analytic column (plain plate 91.5 -> 88.5 K rise, fins 66.1 -> 65.2); `lumped-analytic-vias` 0.1 point; `analytic-edge-spatial/study_frozen_impact` now reads 0.00 where the README says +0.29 to +0.70 % |
| ZONES (zonal Lumped) | the Lumped of a board with a group of vias under a part | harness: plate_vias Lumped 140.1495 -> 136.4534 (0.5 mm), 140.3555 -> 136.4534 (1 and 2 mm); transient time to 63 % 27.83 -> 31.00 s; pending file `lumped-zones.json` |
| FOOT (footprint potentials) | the Lumped of a big source at a fine cell | harness reference_board 0.5 mm 89.0933 -> 89.3632 (+0.27 K); `gap-subdivision/rerun_baseline`: uniform board "source L2 gap 1.6" +0.042 % (59.497 -> 59.522 K) |
| EDGEIMG (via edge image) | vias on a straight board wall | harness example_cut_to_T FVM 94.4545 -> 94.4442 at 2 mm (-0.0103 K), -0.0001 K at 1 mm, 0 at 0.5 mm; stackup L-shape row +1.2 % (Part D finding 4) |
| SYMLU (symmetric LU) | last bits, speed, memory peaks | 89 harness records change below 1e-8 K; `rerun_baseline` pad boards 1e-4 %; `validation_impact.csv` 2e-15 relative; peak memory of the finest laminate rule 1.51 -> 1.34 GB; via memory peaks equal to the board without vias |
| GUARD, laminate options, face term, imported copper, laminar default, HLIM, partial-copper warning | no study number moves | the harness boards do not reach them; HLIM stops one script (finding 1 below) |

Shifts that are not 2.5.0 items (the laminate rule, the point via, the finned-block sides of 2.4.2) keep the explanation of the 2.4.5 pass; Part A found the same values as that pass to 0.1 point. One shift is tied to its item without a run on the older tree: the FVM equivalent-coefficient columns of `block-and-fins/block_equivalent_study` (+0.4 point) are the laminate rule of 2.4.5 (probable, not bisected) and the Analytic shift of `lumped-analytic-vias` is the Robin edge (Part C did not run it on the 2.4.5 tree).

## 3. Harness comparison against v2.4.5 (Part D, section 3)

`PCBT_FROZEN_CELLS=2,1,0.5 pytest -q tests/regression` gives 317 passed in 92.5 s, with the four pending files applied (analytic-edge, lumped-zones, lumped-footprint-potentials, via-edge-image), which is its design. Running the harness on the tag v2.4.5 and on the tree (255 steady records, 68 transient parts each): 117 identical in every digit, 89 at the last bits only (below 1e-8 K), **45 moved, all explained** (39 ROBIN, 3 ZONES, 1 FOOT, 2 EDGEIMG), 4 skipped in both (3D solid above its cap). Transients: 24 values on 12 records moved, on the same items (Analytic at 1 mm on 8 boards, Lumped plate_vias, FVM example_cut_to_T). No unexplained shift.

## 4. Defects and stale text found (nothing was changed in the program or the READMEs)

Program: none.

For the maintainer and the READMEs, on their own branches (Part D section 6, Part B section 4):

1. `research/via-edge-image/scripts/study_edge_sweep.py`: its default `--h-side` list ends at 1e6, which `Board.validate` now refuses (HLIM, 1e5); the script dies at its last table. Run with `--h-side 0 10 100 1e3 1e4 1e5` or cap the list.
2. `research/laminate-nodes/scripts/study_analytic.py` fails with a `TypeError` (its lambda lacks `**kw` for the `ladder` argument that the network takes now): a study defect (Part C).
3. `research/young-omega-tiles`: `lib/tilerule.py` and the SOR library no longer fit the program; the two studies fail on v2.4.5 too (older than 2.5.0).
4. Pre-2.4.5 digits still in `research/solid3d-verification/README.md` 4.2 (0.8076; the program prints 0.8062), `research/zone-union/README.md` 4.2 (143.08; 142.96), `research/power-calculator/README.md` 4.5 (46.4 / 46.8 / 47.2 / 47.1; 47.2 / 47.5 / 48.0 / 47.9), and the FVM and FDM columns of `analytic-partial-copper` 3 and the body of `component-heatsink` 4.11 (the 2.4.5 values are in its "Re-run on 2.4.5" paragraph).
5. `block-and-fins` README 4.1 to 4.3: the Analytic column (and the Analytic entries of 4.2) predate the Robin edge: plain plate 91.5 -> 88.5, fins 66.1 / 70.2 / 56.7 (the sides rows are the 2.4.2 values from the 2.4.5 pass).
6. `docs/validation.md` and `research/stackup`: the L-shape row moves by +1.2 % in the FVM with EDGEIMG (vias exactly on a straight wall of the notch), larger than the 0.01 K quoted for the frozen board (Part D finding 4).
7. `gerber-models` README 4.14, 4.16, 4.27, R2, 4.31, 4.34 to 4.37 quote numbers from before the 2.4.5 laminate rule; 4.34 and 4.35 say "refused by the limit of 250 000 unknowns" (now `MemoryGuardError`); `gerber-real-boards` `study_project_file.py` and README 4.8 describe the flat project layout, which the program no longer reads (Part B).
8. The memory guard prints a warning line into the output of every large study on a loaded machine, which shifts the lines of a printed table in a text diff (harmless).
9. Pass handling, not the program: studies that rewrite tracked files (`gap-subdivision/baseline/*.csv`) change the tree when run; they were compared and restored. The first-pass limit of 30 minutes counted paused time.

## 5. Parts

* [`PART-A.md`](PART-A.md): the eleven folders of Part A, per folder and per script group; runner `scripts/run_part_a.py` (outputs in `out/`, git-ignored).
* [`PART-B.md`](PART-B.md): the Gerber folders, with the bisection of the shifts on `git archive` copies (section 3 of that file).
* [`PART-C.md`](PART-C.md): the Analytic and Lumped folders, models-comparison and memory-guard.
* [`PART-D.md`](PART-D.md): the tests, the release harness comparison against v2.4.5 and eighteen folders.

Load of the machine during the pass: 1.5 at the start of Part A, 4 to 7 during, peaks of 13 to 38 when the other testers ran their jobs (the runners paused by the load rule); swap used rose to 4.8 GB at the end.

## 6. How to run again

    .venv/bin/python releases/2.5.0/reproduction/scripts/run_part_a.py [--only folder] [--late] [--force] --python .venv/bin/python

`JOBS` lists the first pass, `LATE` the long jobs (the long gap-subdivision chain builds `out/refs_pads.json` and rewrites tracked CSV files: restore them with `git checkout`).
