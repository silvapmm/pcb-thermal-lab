# What moved between 2.7.x and 2.8.0, board by board

This page says which numbers of the program change between v2.7.1 and 2.8.0, by how much, and why, so that a user who compares a result of their own board with one of 2.7.x knows what to expect. Every number below names its tree and its reference.

* **Reference (old numbers)**: the frozen numbers of the last release, `tests/regression/data/v2.7.0.json` (17 boards, five models, cells 2, 1 and 0.5 mm). v2.7.1 moved no frozen number (`releases/2.7.1/final-opinion/README.md` 3), so these are also the numbers of v2.7.1.
* **New numbers**: the pending files of 2.8.0, `tests/regression/data/pending/*.json`, measured by each correction on its branch and carried to `development` (each moved record is in one file with its final value; the other items that moved it are named by `also_moved_by`). The refreeze of 2.8.0 (`releases/2.8.0/REFREEZE_PLAN.md`) re-runs the harness on the final tree and must reproduce them within its table; until then the tables below are the pending files, **not a new run** of the solvers.
* **Script**: `releases/2.8.0/reproduction/scripts/what_moved.py` (reads JSON only, runs no solver, takes a second): `.venv/bin/python releases/2.8.0/reproduction/scripts/what_moved.py`. Section 7 is its output, verbatim.
* **Outside the frozen boards**: the reproduction pass of 2.8.0 (`releases/2.8.0/reproduction/`, parts B and C on `development` 77ed4822 against `git archive v2.7.1`, and `LUMPED_SHIFTS_REVIEW.md`) re-ran the studies of the research folders on both trees; the numbers of section 4 come from those reports and are quoted, not re-run here.

## 1. In short

| Item | What changed | Models | On the 17 frozen boards (2.7.0 to 2.8.0) | On other boards (reproduction pass) |
| :-- | :-- | :-- | :-- | :-- |
| M1 face film through the half copper layer (`fix/face-film-half-slab`) | the film of an outer face starts at the face, not at the middle of the copper layer: `h_eff = 1 / (1/h + t/(2k))` | FVM, FDM, Lumped, Analytic (3D solid already had it) | every record, all hotter: median about 2e-5 K, at most +0.040 K (the finned block, at every cell) | grows with t/k of the outer layer: **+0.93 K (+1 %) on a 10 mm plate of 150 W/mK** at 400 W/m2K and a 70 K rise, +0.7 K under a 6 mm stainless block, +0.1 K under an aluminium block, +0.34 % on a via-array resistance |
| M2 drawn copper read as imported copper (`fix/drawn-copper-faces`) | a drawn copper edge inside a cell gives its exact area share and flow-based faces | FVM, FDM | only at 2 mm, four boards: the FVM -0.004 to +0.186 K, the FDM up to +1.865 K (`two_layer_partial`, +1.3 % of the rise on the board maximum); nothing at 1 and 0.5 mm (their copper edges lie on cell lines) | where a drawn edge cuts a cell: up to +12.5 % of a part's rise at 0.5 mm; the calculator's JEDEC board without vias 74.6 to **83.5 K/W** (+12.0 %, the converged value: 74.6 was a grid error of the cut land); the other calculator rows +0.9 to +1.1 % |
| M3 Lumped part read-out and first link (`fix/lumped-part-readout`, `fix/lumped-edge-first-link`) | the part rows read the part's own peak (they read the footprint node, about 10 % of the rise cool); the first ring link sees the mirror images of the board sides | Lumped (LPTN) | every Lumped record: part rows up to +14.9 K (a lone part's peak instead of its node), board maximum -3.1 to +3.1 % of the rise; 12 Lumped times to 63 % (up to -20 % on the small part of the example board) | an isolated part whose copper is only its own footprint **+7.1 %** of the rise on the board maximum; pads of 20 to 80 mm +1.6 to +3.3 %; over the frozen boards and the studies the board maximum moved -3.1 to +7.5 % of the rise |
| M4 exact cover of a metal block (`fix/block-exact-cover`) | the block takes its exact area on the cells | Analytic; FVM, FDM and 3D solid only where a block edge cuts a cell or the outline | Analytic `finned_block` +0.126 K with M1 (+0.09 K of it is M4); nothing else | up to 0.15 K (FVM) and 0.21 K (FDM) on rises of 72 to 90 K with a block across an outline (`docs/validation.md` 54) |
| Analytic transient hot point (`fix/analytic-transient-hot-point`) | the Analytic time curves read the hot point of the steady solution with vias or heatsinks | Analytic, transient only | no frozen record (the Analytic times of the harness move by less than 0.001 %) | time to 63 % of 'vias and heatsink beside' +0.3 % to +3.2 % against the FVM; range of the warning -9 % to +3 % at 1 mm |
| A1 finite-element model (`feature/fem-model`) | a new comparison model, key `fem` | FEM | **addition**: 29 new records, no old number moves | - |
| A2 surface read-out (`feature/surface-always-both`) | the top and bottom face temperature beside the column mean, always computed and shown | FVM, FDM (FEM resolved) | **addition**: 102 records gain surface metrics, no old number moves; on 35 um copper the part surface is 1.4 mK above the column (median), at most 3.3 mK | thick plates: the surface is above the column by up to `q t / (2k)`-like terms (`docs/theory.md` 1.2c) |

**What did not move**: the 3D solid on the 17 frozen boards (348 read-outs, all bit-identical; its block code changed with M4 but every block of the harness lies on cell lines); the Analytic and FVM/FDM times to 63 % except those listed in section 7; the convection laws below Ra 1e7 (the face-up branch above it now follows Lienhard eq. 8.35; no frozen board reaches it); the Gerber reader (text only: the sign ×); and every display or text change of the window (units in K for differences, model labels, the Summary table, the warning rows, the first-step hints): these move no number. The memory guard has a new law (the FEM) and a new term (the raster of drawn copper with cut cells); its verdicts move only for those runs.

## 2. What a user sees on their own board

* **Every layered model reads very slightly hotter** (M1). On a normal PCB (35 to 70 um copper) the change is a few hundred-thousandths of a kelvin: invisible. It is the size of the film term `q t / (2k)` of the outer layer, so it matters only for thick outer metal: a 10 mm aluminium or copper plate modelled as a one-layer board reads about 1 K hotter at a 70 K rise, a thick block of a poor conductor (stainless) about 0.7 K. The 3D solid already had the term, so the layered models now agree with it there.
* **A drawn copper edge that falls inside a cell is read exactly** (M2). With the default 1 mm cell and a board drawn on a millimetre grid nothing changes; with a coarse cell (2 mm) or an edge between cell lines the FVM and the FDM read slightly hotter and closer to a converged reference (the FDM up to 1.3 % of the rise on the harness boards, the calculator's JEDEC board without vias 12 % at 0.5 mm, which was a grid error of the old faces). A board with cut cells takes 2.5 to 4 times longer and 0.15 to 1 GB more memory.
* **The Lumped (LPTN) part rows are hotter** (M3). With the Lumped as the only model the rows of a part (its temperature, Tj, the margin, the power limit, the Power Calculator) now read the part's own peak; in 2.7.x they read the footprint node, about 10 % of the rise cool for a lone part. The board maximum moves by -3 to +3 % of the rise on the harness boards; a part near a side reads closer to the reference (the worst case near a side from -22 % to -7.5 %), a part away from the sides reads hotter, on average about 2 points of the rise at 1 mm and 4 at 0.5 mm (up to 6.4) against the FVM (`docs/validation.md` 53). When the FVM is in the same run, the part rows read the FVM as before.
* **A metal block that does not fit the cells** (M4) changes by a tenth of a kelvin at most in the Analytic.
* **The Analytic transient** with vias or heatsinks reads a slightly different time constant (the hot point of the steady solution); the steady numbers do not change.
* **New, nothing to compare**: the finite-element model (FEM) is a new comparison model; the surface read-out is a second number shown beside the column mean (on thin copper the two differ by a few mK; on a thick plate by up to about `q t / (2k)`, which the warning quotes).

## 3. The 17 frozen boards, model by model (headline of section 7)

Read-out: every temperature of a record (board maximum, mean and minimum, the mean of each copper layer, the peak, mean and junction of each part, the block mean and maximum); a read-out 'moved' when it changed by more than 1e-8 K (the round-off bound of the harness). Shift = 2.8.0 minus 2.7.0, positive is hotter; the rise is the 2.7.0 board maximum over the 25 °C ambient.

| Model | Read-outs moved (2 / 1 / 0.5 mm) | Median shift of the moved | Largest shift | Board maximum, % of the rise | Items |
| :-- | :-- | --: | :-- | :-- | :-- |
| FVM | 138 / 138 / 138 of 138 each | 1.5e-5 K (4.4e-5 K at 2 mm) | +0.186 K (`two_layer_partial`, 2 mm, M2); +0.040 K at 1 and 0.5 mm (`finned_block`, M1) | -0.006 to +0.13 % | M1 every board; M2 four boards at 2 mm |
| FDM | 138 / 138 / 138 | 1.5e-5 K (4.4e-5 K at 2 mm) | +1.865 K (`two_layer_partial`, 2 mm, part mean, M2); +0.040 K at 1 and 0.5 mm | up to +1.32 % (`two_layer_partial`, 2 mm) | M1; M2 four boards at 2 mm |
| Lumped (LPTN) | 136 / 136 / 136 of 136 | 0.03 to 0.04 K | +14.9 K (a part row, node to own peak) | -3.07 % (`part_top_path`, 0.5 mm) to +3.13 % (`part_across_outline`, 2 and 1 mm) | M1 and M3 on every board |
| Analytic | 136 / 136 / 136 of 136 | 1.8e-5 K | +0.126 K (`finned_block`, M1 + M4) | up to +0.12 % (`finned_block`) | M1; M4 on the finned block |
| 3D solid | 0 of 136 / 136 / 76 | 0 | 0 | 0 | none (it already had the half-layer film) |

The FVM and the FDM agree with the 2.7.0 numbers to 1e-4 K on every board at 1 and 0.5 mm except the finned block (+0.040 K, the film through half of a 3 mm aluminium block). The 2 mm differences of `example_board`, `profile_board`, `example_cut_to_T` and `two_layer_partial` are the drawn copper edge inside a 2 mm cell (their copper edges lie on the lines of the 1 and 0.5 mm grids). The Lumped part rows move most because they changed read-out (node to own peak); its board maximum moves -3.1 to +3.1 %.

**Times to 63 %** (harness, 1 mm): 38 of 58 are held in a pending file; 18 of them moved by less than 0.001 %. The ones that matter: the Lumped of the example board's small part U2 2.43 to 1.94 s (-19.9 %, M3), the other Lumped times -3.3 to +1.1 %; the FDM of the example board and its profile twin +0.3 / +1.1 % (U1 / U2; the pending files credit M1 and M2, the split is not recorded); the FVM within 0.17 %. The Analytic times move by less than 1e-3 %.

**Additions** (no old number moves): 29 FEM records (2 mm: 16 boards, 1 mm: 12, 0.5 mm: 1; the others exceed the harness cap of the FEM); on them the FEM board maximum (column read-out) is 0.0 to 2.7 % of the rise below the FVM at 1 mm (`finned_block` -0.02 %, `one_layer_pad` -2.67 %, `plate_pad` -2.53 %), and 0.3 to 7.5 % below at 2 mm, where the FVM is coarse and converges from above (`docs/validation.md` 46 and `CHANGELOG.md`). 102 FVM and FDM records gain the surface read-out: on these 35 to 70 um copper boards the part surface peak is above the column peak by 1.4 mK (median of 120 part read-outs) and at most 3.3 mK.

## 4. Outside the frozen boards (reproduction pass, quoted)

The reproduction pass ran the studies of the research folders on `development` 77ed4822 and on `git archive v2.7.1` (part B: `releases/2.8.0/reproduction/PART-B.md`, branch of the pass; part C: `PART-C.md`; the review of the two shifts left to confirm: `LUMPED_SHIFTS_REVIEW.md` on this tree). Part C: 122 scripts, 45 unchanged, 32 explained, 0 unexplained; part B: 34 pairs compared, 24 identical, 10 explained (two of them after the review), 0 unexplained. The shifts larger than the frozen bands:

| Where | 2.7.1 | 2.8.0 | Item | Evidence |
| :-- | --: | --: | :-- | :-- |
| 10 mm plate of 150 W/mK, 400 W/m2K, 70 K rise (Muzychka case 2), FVM, FDM, Analytic | 0.85 to 0.89 K below the 3D column | within 0.10 K of it (+0.93 K, +1 %) | M1 | PART-C 1.2, `docs/validation.md` 55 |
| 6 mm stainless block, junction | 71.7 °C | 72.4 °C (+0.7 K) | M1 | PART-C (`component-heatsink`) |
| aluminium block / perfect contact | - | +0.1 K / +0.15 K | M1 | PART-C |
| via-array resistance (Shen) | - | +0.011 K/W (+0.34 %) | M1 | PART-C (`published-cases-followup`) |
| Lumped, 10 mm heater on its own pad, bare laminate (100 x 80 mm, 5 W) | 494.5 °C | 527.6 °C (+7.1 % of the rise) | M3 | LUMPED_SHIFTS_REVIEW 1 (against the FVM: -3.0 % before, +3.9 % now; mean absolute error over six pads 4.92 % to 3.89 %) |
| Lumped, pads 20 to 80 mm on the same board | 249.7 ... 142.6 °C | 253.3 ... 146.5 °C (+1.6 to +3.3 %) | M3 | LUMPED_SHIFTS_REVIEW 1 |
| Calculator, JEDEC 2s2p board without vias, FVM 0.5 mm | 74.6 K/W | 83.5 K/W (+12.0 %) | M2 | LUMPED_SHIFTS_REVIEW 2: converged value (163.66 K at 0.1 mm on a window; 2.8.0 within 0.4 % from 0.5 mm down, 2.7.1 5 % low at 0.5 mm) |
| Calculator, the other three rows | 46.7 / 45.6 / 31.6 K/W | 47.1 / 46.1 / 31.9 K/W | M2 (with M1) | PART-B |
| Seri Lee plate, Lumped near-edge error (centre) | -25.3 / -5.3 % | -2.7 / -2.1 % | M3 (the intended effect) | PART-C |
| Analytic transient, 'vias and heatsink beside', time to 63 % against the FVM | +0.3 % | +3.2 % | Analytic hot point | PART-C, `docs/validation.md` 4.1 |

Two study defects found on the way (not program defects): `research/solid3d-verification/scripts/copper_dissipation.py` ran a one-ring Lumped (its +22 % was that network; corrected, `LUMPED_SHIFTS_REVIEW.md` 4), and `research/lumped-zones-adoption` holds a copy of the 2.7.1 first link whose equality tests fail on 2.8.0 (stale against M3, PART-C 1.1).

## 5. The three new harness boards

`drawn_inset_square`, `drawn_stripes_pad` and `drawn_ell` (20 x 20 mm, two layers, drawn copper with edges between the cell lines, 200 W/m2K edge film) are new in 2.8.0 and are in no frozen file: they have no 2.7.0 number and no pending record. Their FVM and FDM numbers at 1 and 0.5 mm are held by `tests/test_drawn_copper_faces.py` until the refreeze; against an independent finite-element solution the FVM heater mean at 1 / 0.5 mm moved from -1.2 / -2.8 % to +0.1 / -1.4 % (inset), -8.0 / -4.1 % to -0.6 / -1.9 % (stripes and a pad) and -1.4 / -4.1 % to -0.0 / -2.5 % (an L) (`docs/validation.md` 51.1, measured on the branch of M2, not re-run here). The refreeze runs them on both trees and lists their shifts under M2 (`REFREEZE_PLAN.md` 3, trap 4).

## 6. Limits of this page

* The 2.8.0 numbers of sections 3 and 7 are the pending files, written by each branch at its merge; the harness has not been re-run on the final tree (the refreeze does it and must find the same numbers within its table, `REFREEZE_PLAN.md` 5).
* The attribution to items is the one the pending files record (`also_moved_by`); where two items act on one record (M1 with M2, M3 or M4) the split between them is not in the files: the CHANGELOG and `docs/validation.md` 51, 53, 54 and 55 give each item alone on its branch.
* The heavy studies of the reproduction pass (about 25 scripts above 300 s or 4 GB, listed in PART-B and PART-C) were not run on either tree; the Gerber studies whose data is not in the repository were not run. Part A of the pass and its totals were not available when this page was written.
* No number here is a measurement of a physical board.

## 7. Output of `what_moved.py`

Reference: `tests/regression/data/v2.7.0.json` (version 2.7.0); pending files: `tests/regression/data/pending` (204 moved records, 38 moved times to 63 %, additions: fem-records 29, surface-records 102).
Moved records without a frozen record (should be none): 0.

### 7.1 Summary per model and cell (frozen boards, temperature read-outs)

| Model | Cell (mm) | Records | Records moved | Read-outs moved / all | Median shift of the moved (K) | Largest shift (K) | Where | Largest board-maximum shift (% of rise) | Items |
| :-- | --: | --: | --: | --: | --: | --: | :-- | --: | :-- |
| fvm | 2 | 17 | 17 | 138 / 138 | +4.4e-05 | +0.186 | two_layer_partial `part:U:t_mean` | +0.13 | M1, M2 |
| fvm | 1 | 17 | 17 | 138 / 138 | +1.5e-05 | +0.040 | finned_block `part:U:t_max` | +0.04 | M1 |
| fvm | 0.5 | 17 | 17 | 138 / 138 | +1.5e-05 | +0.040 | finned_block `part:U:t_max` | +0.04 | M1 |
| fdm | 2 | 17 | 17 | 138 / 138 | +4.4e-05 | +1.865 | two_layer_partial `part:U:t_mean` | +1.32 | M1, M2 |
| fdm | 1 | 17 | 17 | 138 / 138 | +1.5e-05 | +0.040 | finned_block `part:U:t_max` | +0.04 | M1 |
| fdm | 0.5 | 17 | 17 | 138 / 138 | +1.5e-05 | +0.040 | finned_block `part:U:t_max` | +0.04 | M1 |
| lumped | 2 | 17 | 17 | 136 / 136 | +0.039 | +14.407 | part_across_outline `part:U:t_max` | +3.13 | M1, M3 |
| lumped | 1 | 17 | 17 | 136 / 136 | +0.039 | +14.407 | part_across_outline `part:U:t_max` | +3.13 | M1, M3 |
| lumped | 0.5 | 17 | 17 | 136 / 136 | +0.027 | +14.915 | two_layer_partial `part:U:t_max` | -3.07 | M1, M3 |
| analytic | 2 | 17 | 17 | 136 / 136 | +1.8e-05 | +0.126 | finned_block `part:U:t_max` | +0.12 | M1, M4 |
| analytic | 1 | 17 | 17 | 136 / 136 | +1.8e-05 | +0.126 | finned_block `part:U:t_max` | +0.12 | M1, M4 |
| analytic | 0.5 | 17 | 17 | 136 / 136 | +1.8e-05 | +0.126 | finned_block `part:U:t_max` | +0.12 | M1, M4 |
| solid3d | 2 | 17 | 0 | 0 / 136 | 0 | 0 | - | +0.00 | - |
| solid3d | 1 | 17 | 0 | 0 / 136 | 0 | 0 | - | +0.00 | - |
| solid3d | 0.5 | 11 | 0 | 0 / 76 | 0 | 0 | - | +0.00 | - |

### 7.2 fvm: board by board (largest signed shift of any read-out at each cell, K; board maximum in % of its rise)

| Board | 2 mm | 1 mm | 0.5 mm | Board maximum, % of rise (2 / 1 / 0.5 mm) | Read-outs moved | Items |
| :-- | --: | --: | --: | :-- | --: | :-- |
| example_board | -0.001 | +1.2e-05 | +1.2e-05 | -0.0020 / +0.0000 / +0.0000 | 39 / 39 | M1, M2 |
| example_cut_to_T | -0.004 | +1.5e-05 | +1.5e-05 | -0.0055 / +0.0000 / +0.0000 | 39 / 39 | M1, M2 |
| finned_block | +0.040 | +0.040 | +0.040 | +0.0378 / +0.0377 / +0.0377 | 27 / 27 | M1 |
| hatched_copper | +1.2e-05 | +1.2e-05 | +1.2e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| one_layer_full | +7.2e-06 | +7.2e-06 | +7.2e-06 | +0.0000 / +0.0000 / +0.0000 | 18 / 18 | M1 |
| one_layer_pad | +1.9e-05 | +1.8e-05 | +1.8e-05 | +0.0000 / +0.0000 / +0.0000 | 18 / 18 | M1 |
| part_across_outline | +5.7e-05 | +5.7e-05 | +5.7e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| part_top_path | +5.2e-06 | +5.3e-06 | +5.3e-06 | +0.0000 / +0.0000 / +0.0000 | 24 / 24 | M1 |
| plate_lone_via | +3.1e-05 | +3.1e-05 | +3.1e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| plate_pad | +9.0e-05 | +8.4e-05 | +8.1e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| plate_uniform | +3.3e-05 | +3.3e-05 | +3.3e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| plate_vias | +3.1e-05 | +3.1e-05 | +3.1e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| profile_board | -0.001 | +1.2e-05 | +1.2e-05 | -0.0020 / +0.0000 / +0.0000 | 39 / 39 | M1, M2 |
| reference_board | +1.3e-05 | +1.3e-05 | +1.3e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| round_outline | +4.4e-05 | +4.4e-05 | +4.4e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| t_outline | +4.7e-05 | +4.7e-05 | +4.8e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| two_layer_partial | +0.186 | +2.2e-05 | +2.1e-05 | +0.1323 / +0.0000 / +0.0000 | 21 / 21 | M1, M2 |

### 7.3 fdm: board by board (largest signed shift of any read-out at each cell, K; board maximum in % of its rise)

| Board | 2 mm | 1 mm | 0.5 mm | Board maximum, % of rise (2 / 1 / 0.5 mm) | Read-outs moved | Items |
| :-- | --: | --: | --: | :-- | --: | :-- |
| example_board | +0.112 | +1.2e-05 | +1.2e-05 | +0.1742 / +0.0000 / +0.0000 | 39 / 39 | M1, M2 |
| example_cut_to_T | +0.136 | +1.5e-05 | +1.5e-05 | +0.1843 / +0.0000 / +0.0000 | 39 / 39 | M1, M2 |
| finned_block | +0.040 | +0.040 | +0.040 | +0.0379 / +0.0377 / +0.0377 | 27 / 27 | M1 |
| hatched_copper | +1.2e-05 | +1.2e-05 | +1.2e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| one_layer_full | +7.2e-06 | +7.2e-06 | +7.2e-06 | +0.0000 / +0.0000 / +0.0000 | 18 / 18 | M1 |
| one_layer_pad | +1.6e-05 | +1.7e-05 | +1.7e-05 | +0.0000 / +0.0000 / +0.0000 | 18 / 18 | M1 |
| part_across_outline | +5.7e-05 | +5.7e-05 | +5.7e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| part_top_path | +5.4e-06 | +5.4e-06 | +5.3e-06 | +0.0000 / +0.0000 / +0.0000 | 24 / 24 | M1 |
| plate_lone_via | +3.1e-05 | +3.1e-05 | +3.1e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| plate_pad | +7.4e-05 | +7.7e-05 | +7.9e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| plate_uniform | +3.3e-05 | +3.3e-05 | +3.3e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| plate_vias | +3.1e-05 | +3.1e-05 | +3.1e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| profile_board | +0.112 | +1.2e-05 | +1.2e-05 | +0.1742 / +0.0000 / +0.0000 | 39 / 39 | M1, M2 |
| reference_board | +1.3e-05 | +1.3e-05 | +1.3e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| round_outline | +4.4e-05 | +4.4e-05 | +4.4e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| t_outline | +4.7e-05 | +4.8e-05 | +4.8e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| two_layer_partial | +1.865 | +2.1e-05 | +2.1e-05 | +1.3247 / +0.0000 / +0.0000 | 21 / 21 | M1, M2 |

### 7.4 lumped: board by board (largest signed shift of any read-out at each cell, K; board maximum in % of its rise)

| Board | 2 mm | 1 mm | 0.5 mm | Board maximum, % of rise (2 / 1 / 0.5 mm) | Read-outs moved | Items |
| :-- | --: | --: | --: | :-- | --: | :-- |
| example_board | +4.810 | +4.810 | +5.908 | +0.0638 / +0.0638 / +1.2594 | 39 / 39 | M1, M3 |
| example_cut_to_T | +6.011 | +6.011 | +5.586 | +1.4919 / +1.4919 / +0.7477 | 39 / 39 | M1, M3 |
| finned_block | +12.699 | +12.699 | +13.545 | +0.6327 / +0.6327 / +0.9397 | 21 / 21 | M1, M3 |
| hatched_copper | +11.259 | +11.259 | +11.103 | +0.6300 / +0.6300 / +0.0105 | 21 / 21 | M1, M3 |
| one_layer_full | +2.928 | +2.928 | +2.614 | +0.9935 / +0.9935 / -0.4702 | 18 / 18 | M1, M3 |
| one_layer_pad | +2.768 | +2.768 | +2.496 | +0.4414 / +0.4414 / -0.2137 | 18 / 18 | M1, M3 |
| part_across_outline | +14.407 | +14.407 | +13.534 | +3.1268 / +3.1268 / +2.4610 | 21 / 21 | M1, M3 |
| part_top_path | -1.345 | -1.345 | -1.508 | -2.7222 / -2.7222 / -3.0682 | 24 / 24 | M1, M3 |
| plate_lone_via | +12.282 | +12.282 | +11.172 | +0.8792 / +0.8792 / -0.4152 | 21 / 21 | M1, M3 |
| plate_pad | +12.612 | +12.612 | +11.517 | +0.4046 / +0.4046 / -0.1939 | 21 / 21 | M1, M3 |
| plate_uniform | +13.112 | +13.112 | +11.890 | +0.9157 / +0.9157 / -0.4322 | 21 / 21 | M1, M3 |
| plate_vias | +4.132 | +4.132 | +4.132 | -0.3443 / -0.3443 / -0.3443 | 21 / 21 | M1, M3 |
| profile_board | +4.810 | +4.810 | +5.908 | +0.0638 / +0.0638 / +1.2594 | 39 / 39 | M1, M3 |
| reference_board | +10.416 | +10.416 | +9.950 | +1.7076 / +1.7076 / +0.8714 | 21 / 21 | M1, M3 |
| round_outline | +12.625 | +12.625 | +14.030 | +0.7687 / +0.7687 / +1.2446 | 21 / 21 | M1, M3 |
| t_outline | +9.546 | +9.546 | +9.160 | +1.0196 / +1.0196 / +0.4850 | 21 / 21 | M1, M3 |
| two_layer_partial | +12.403 | +12.403 | +14.915 | -0.3943 / -0.3943 / +1.1214 | 21 / 21 | M1, M3 |

### 7.5 analytic: board by board (largest signed shift of any read-out at each cell, K; board maximum in % of its rise)

| Board | 2 mm | 1 mm | 0.5 mm | Board maximum, % of rise (2 / 1 / 0.5 mm) | Read-outs moved | Items |
| :-- | --: | --: | --: | :-- | --: | :-- |
| example_board | +1.4e-05 | +1.4e-05 | +1.4e-05 | +0.0000 / +0.0000 / +0.0000 | 39 / 39 | M1 |
| example_cut_to_T | +1.8e-05 | +1.8e-05 | +1.8e-05 | +0.0000 / +0.0000 / +0.0000 | 39 / 39 | M1 |
| finned_block | +0.126 | +0.126 | +0.126 | +0.1202 / +0.1202 / +0.1200 | 21 / 21 | M1, M4 |
| hatched_copper | +1.2e-05 | +1.2e-05 | +1.2e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| one_layer_full | +7.2e-06 | +7.2e-06 | +7.2e-06 | +0.0000 / +0.0000 / +0.0000 | 18 / 18 | M1 |
| one_layer_pad | +4.3e-06 | +4.3e-06 | +4.3e-06 | +0.0000 / +0.0000 / +0.0000 | 18 / 18 | M1 |
| part_across_outline | +5.7e-05 | +5.7e-05 | +5.7e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| part_top_path | +7.6e-06 | +7.6e-06 | +7.6e-06 | +0.0000 / +0.0000 / +0.0000 | 24 / 24 | M1 |
| plate_lone_via | +3.1e-05 | +3.1e-05 | +3.1e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| plate_pad | +2.0e-05 | +2.0e-05 | +2.0e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| plate_uniform | +3.3e-05 | +3.3e-05 | +3.3e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| plate_vias | +3.1e-05 | +3.1e-05 | +3.1e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| profile_board | +1.4e-05 | +1.4e-05 | +1.4e-05 | +0.0000 / +0.0000 / +0.0000 | 39 / 39 | M1 |
| reference_board | +1.3e-05 | +1.3e-05 | +1.3e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| round_outline | +4.4e-05 | +4.4e-05 | +4.4e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| t_outline | +3.5e-05 | +3.5e-05 | +3.5e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |
| two_layer_partial | +2.3e-05 | +2.3e-05 | +2.3e-05 | +0.0000 / +0.0000 / +0.0000 | 21 / 21 | M1 |

### 7.6 solid3d: board by board (largest signed shift of any read-out at each cell, K; board maximum in % of its rise)

| Board | 2 mm | 1 mm | 0.5 mm | Board maximum, % of rise (2 / 1 / 0.5 mm) | Read-outs moved | Items |
| :-- | --: | --: | --: | :-- | --: | :-- |
| example_board | 0 | 0 | not frozen | +0.0000 / +0.0000 / - | 0 / 26 | none |
| example_cut_to_T | 0 | 0 | not frozen | +0.0000 / +0.0000 / - | 0 / 26 | none |
| finned_block | 0 | 0 | 0 | +0.0000 / +0.0000 / +0.0000 | 0 / 21 | none |
| hatched_copper | 0 | 0 | 0 | +0.0000 / +0.0000 / +0.0000 | 0 / 21 | none |
| one_layer_full | 0 | 0 | 0 | +0.0000 / +0.0000 / +0.0000 | 0 / 18 | none |
| one_layer_pad | 0 | 0 | 0 | +0.0000 / +0.0000 / +0.0000 | 0 / 18 | none |
| part_across_outline | 0 | 0 | 0 | +0.0000 / +0.0000 / +0.0000 | 0 / 21 | none |
| part_top_path | 0 | 0 | 0 | +0.0000 / +0.0000 / +0.0000 | 0 / 24 | none |
| plate_lone_via | 0 | 0 | 0 | +0.0000 / +0.0000 / +0.0000 | 0 / 21 | none |
| plate_pad | 0 | 0 | 0 | +0.0000 / +0.0000 / +0.0000 | 0 / 21 | none |
| plate_uniform | 0 | 0 | 0 | +0.0000 / +0.0000 / +0.0000 | 0 / 21 | none |
| plate_vias | 0 | 0 | 0 | +0.0000 / +0.0000 / +0.0000 | 0 / 21 | none |
| profile_board | 0 | 0 | not frozen | +0.0000 / +0.0000 / - | 0 / 26 | none |
| reference_board | 0 | 0 | not frozen | +0.0000 / +0.0000 / - | 0 / 14 | none |
| round_outline | 0 | 0 | 0 | +0.0000 / +0.0000 / +0.0000 | 0 / 21 | none |
| t_outline | 0 | 0 | not frozen | +0.0000 / +0.0000 / - | 0 / 14 | none |
| two_layer_partial | 0 | 0 | not frozen | +0.0000 / +0.0000 / - | 0 / 14 | none |

### 7.7 Times to 63 % (transient boards of the harness, 1 mm)

| Board, model | Part | 2.7.0 (s) | 2.8.0 (s) | Shift (%) | Items |
| :-- | :-- | --: | --: | --: | :-- |
| example_board, fdm | U1 | 10.9542 | 10.9879 | +0.308 | M1, M2 |
| example_board, fdm | U2 | 2.6494 | 2.6790 | +1.116 | M1, M2 |
| example_board, fvm | U1 | 10.5222 | 10.5242 | +0.019 | M1, M2 |
| example_board, fvm | U2 | 2.3099 | 2.3096 | -0.013 | M1, M2 |
| example_board, lumped | U1 | 8.8431 | 8.8142 | -0.327 | M1, M3 |
| example_board, lumped | U2 | 2.4262 | 1.9428 | -19.924 | M1, M3 |
| example_cut_to_T, fdm | U1 | 16.3414 | 16.3242 | -0.105 | M1, M2 |
| example_cut_to_T, fdm | U2 | 4.4649 | 4.4907 | +0.578 | M1, M2 |
| example_cut_to_T, fvm | U1 | 15.6473 | 15.6516 | +0.027 | M1, M2 |
| example_cut_to_T, fvm | U2 | 3.8936 | 3.8937 | +0.002 | M1, M2 |
| finned_block, fdm | U | 15.3284 | 15.3423 | +0.090 | M1 |
| finned_block, fvm | U | 15.3326 | 15.3464 | +0.090 | M1 |
| hatched_copper, lumped | U | 17.1747 | 16.9882 | -1.085 | M3 |
| one_layer_full, lumped | U | 20.5766 | 20.1530 | -2.059 | M3 |
| one_layer_pad, lumped | U | 57.4293 | 57.1022 | -0.569 | M3 |
| part_top_path, lumped | Q1 | 17.5500 | 17.2504 | -1.707 | M3 |
| plate_lone_via, lumped | U | 18.7897 | 18.2001 | -3.138 | M1, M3 |
| plate_pad, lumped | U | 56.1936 | 55.8772 | -0.563 | M3 |
| plate_uniform, lumped | U | 18.4632 | 17.8537 | -3.302 | M1, M3 |
| plate_vias, lumped | U | 30.9420 | 31.2798 | +1.092 | M1, M3 |
| profile_board, fdm | U1 | 10.9542 | 10.9879 | +0.308 | M1, M2 |
| profile_board, fdm | U2 | 2.6494 | 2.6790 | +1.116 | M1, M2 |
| profile_board, fvm | U1 | 10.5222 | 10.5242 | +0.019 | M1, M2 |
| profile_board, fvm | U2 | 2.3099 | 2.3096 | -0.013 | M1, M2 |
| profile_board, lumped | U1 | 8.8431 | 8.8142 | -0.327 | M1, M3 |
| profile_board, lumped | U2 | 2.4262 | 1.9428 | -19.924 | M1, M3 |
| reference_board, lumped | Heater 1 | 17.9389 | 17.6314 | -1.714 | M3 |
| two_layer_partial, fdm | U | 24.4132 | 24.3850 | -0.116 | M2 |
| two_layer_partial, fvm | U | 24.5375 | 24.5781 | +0.165 | M2 |
| two_layer_partial, lumped | U | 22.7737 | 22.9727 | +0.874 | M3 |

Parts whose time moved by less than 0.001 % (listed in a pending file, not shown): 18.

Times to 63 % not moved: 20 of 58 (analytic, fdm, fvm).

### 7.8 Additions (new records or new metrics; no old number moves)

* `fem-records`: 29 records; fem 0.5 mm: 1, fem 1 mm: 12, fem 2 mm: 16

  | Board | Cell (mm) | FEM board maximum (degC) | FVM board maximum (degC) | FEM - FVM, % of the FVM rise |
  | :-- | --: | --: | --: | --: |
  | example_board | 2 | 83.638 | 85.293 | -2.74 |
  | example_cut_to_T | 2 | 92.713 | 94.669 | -2.81 |
  | finned_block | 2 | 128.806 | 129.687 | -0.84 |
  | finned_block | 1 | 129.918 | 129.941 | -0.02 |
  | hatched_copper | 2 | 110.933 | 112.012 | -1.24 |
  | hatched_copper | 1 | 111.910 | 112.240 | -0.38 |
  | one_layer_full | 2 | 54.679 | 55.355 | -2.23 |
  | one_layer_full | 1 | 55.278 | 55.441 | -0.54 |
  | one_layer_pad | 2 | 90.303 | 95.565 | -7.46 |
  | one_layer_pad | 1 | 91.883 | 93.716 | -2.67 |
  | part_across_outline | 2 | 227.274 | 229.398 | -1.04 |
  | part_across_outline | 1 | 229.491 | 229.829 | -0.17 |
  | part_across_outline | 0.5 | 229.941 | 229.764 | +0.09 |
  | part_top_path | 2 | 73.643 | 74.711 | -2.15 |
  | part_top_path | 1 | 73.820 | 74.099 | -0.57 |
  | plate_lone_via | 2 | 148.916 | 151.569 | -2.10 |
  | plate_lone_via | 1 | 149.855 | 150.432 | -0.46 |
  | plate_pad | 2 | 339.060 | 362.607 | -6.97 |
  | plate_pad | 1 | 345.087 | 353.384 | -2.53 |
  | plate_uniform | 2 | 156.407 | 159.052 | -1.97 |
  | plate_uniform | 1 | 159.006 | 159.516 | -0.38 |
  | plate_vias | 2 | 133.625 | 137.815 | -3.71 |
  | plate_vias | 1 | 134.672 | 135.682 | -0.91 |
  | profile_board | 2 | 83.638 | 85.293 | -2.74 |
  | reference_board | 2 | 89.899 | 90.069 | -0.26 |
  | t_outline | 2 | 186.083 | 187.209 | -0.69 |
  | t_outline | 1 | 186.793 | 186.987 | -0.12 |
  | two_layer_partial | 2 | 161.279 | 162.808 | -1.11 |
  | two_layer_partial | 1 | 162.827 | 163.474 | -0.47 |
* `surface-records`: 102 records; fdm 0.5 mm: 17, fdm 1 mm: 17, fdm 2 mm: 17, fvm 0.5 mm: 17, fvm 1 mm: 17, fvm 2 mm: 17
  part peak, surface minus column mean over 120 part read-outs: median 1.38e-03 K, largest +0.0033 K (plate_vias|fdm|2 `part:U:t_max_surface`)
