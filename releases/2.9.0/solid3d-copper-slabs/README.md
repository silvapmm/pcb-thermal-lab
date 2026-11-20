# Copper slabs in the 3D solid: what moved and why (`feature/solid3d-copper-slabs`, item e2 of `releases/2.9.0/PLAN.md`)

**Rule implemented**: a copper layer of up to 105 um is one slab (as before); above it, `ceil(t / 70 um)` equal slabs, at most 8 (`solid3d.copper_slab_count`, equal to the FEM's `femmesh.copper_slab_count`; a test keeps them equal). The column of a layer is the mean of its slabs. The heat of a part on a thick OUTER copper layer enters the outer slab (the face the part sits on, as the FEM feeds a flux through that face); on an inner layer, or on one slab, it is spread over the slabs. Everything else of the 3D solid is unchanged: the cell, the memory guard before the run, steady state only, the interface pad slab, the via barrel in `k_z` of every slab.

**Trees and references**: before = `development` at `0d45660b`; after = this branch (the tree named in `docs/decisions-log.md`). References: the independent 3D solver `tests/helpers/layered3d.py` (imports nothing from the program; 0.5 mm cell, the same slabs through the metal, and the 1 um laminate that the program's one-layer plate has), and the program's FVM and FEM at 2 mm. Script: `scripts/study_copper_slabs.py run --tree <checkout> --out <json>` on each tree, then `compare before.json after.json` (the tables below are its output). Read-outs: **column** (the mean of the copper layer through its thickness, maximum over the cells under the source). "Outer slab" is the temperature of the outer slab, half a slab below the face: it is NOT the surface read-out (item e22).

## 1. The frozen boards do not move

Every board of the regression harness has 35 um copper: one slab before and after. The 3D solid at 2 mm and 1 mm (38 records under the harness cap of 150 000 unknowns) is **bit-identical**; the largest difference of `t_max` or of a layer mean is 0.000e+00 K, and the slab count is the same on every board (10 to 16). So `PCBT_FROZEN_CELLS=2 pytest tests/regression -k solid3d` passes (20 passed) with **no pending file**: `make_pending.py` would write zero records. The plan expected "others bit-identical" and "boards with copper above the slab threshold" for the moved ones; the harness has none. Consequence: the refuse-or-refreeze step of the release has nothing to fold in for this item, and the maintainer may add a thick-copper board to the harness (a decision, not made here).

## 2. Plates and the copper sweep (before and after)

Plates at 0.5 mm, column maximum under the source against the independent 3D solver, degC (ambient 25):

| plate | slabs before / after | solid before | solid after | independent (with the 1 um laminate) | before - ref (K) | after - ref (K) | outer slab after | independent surface |
| :-- | :-: | --: | --: | --: | --: | --: | --: | --: |
| case 2 (10 mm k150, a 10, h 400) | 5/12 | 53.965 | 53.976 | 53.976 | -0.010 | -0.000 | 57.438 | 58.480 |
| 1 mm Cu, a 2, h 10 | 5/12 | 66.224 | 66.224 | 66.224 | -0.000 | -0.000 | 66.387 | 66.428 |
| 3 mm Cu, a 5, h 100 | 5/12 | 67.843 | 67.844 | 67.844 | -0.000 | -0.000 | 68.615 | 68.809 |
| 10 mm Al, a 10, h 1000 | 5/12 | 76.840 | 76.897 | 76.897 | -0.056 | -0.000 | 87.301 | 90.426 |
| 10 mm Cu, a 10, h 400 | 5/12 | 67.518 | 67.520 | 67.520 | -0.003 | -0.000 | 69.676 | 70.326 |
| 5 mm Al, a 2, h 400 | 5/12 | 27.946 | 27.947 | 27.947 | -0.001 | -0.000 | 29.185 | 29.966 |
| 2 mm Cu + 1 mm FR-4, a 4, h 50 | 7/14 | 74.011 | 74.011 | 74.011 | -0.000 | -0.000 | 74.428 | 74.530 |
| 2 mm Cu + 1 mm FR-4, a 4, h 50, via | 7/14 | 73.857 | 73.857 | 73.842 | +0.015 | +0.015 | 74.288 | 74.381 |

Copper sweep at 2 mm (every layer set to the thickness, gaps kept), column maximum under the part, degC:

| board | Cu um | slabs before / after | solid before | solid after | FVM | FEM | after - FVM | after - FEM |
| :-- | --: | :-: | --: | --: | --: | --: | --: | --: |
| reference_board | 35 | 10/10 | 90.200 | 90.200 | 90.069 | 89.899 | +0.131 | +0.300 |
| reference_board | 70 | 10/10 | 71.806 | 71.806 | 71.740 | 71.621 | +0.066 | +0.185 |
| reference_board | 105 | 10/10 | 64.471 | 64.471 | 64.430 | 64.334 | +0.041 | +0.137 |
| reference_board | 140 | 10/12 | 60.436 | 60.436 | 60.406 | 60.326 | +0.029 | +0.110 |
| reference_board | 210 | 10/14 | 56.037 | 56.037 | 56.019 | 55.957 | +0.017 | +0.080 |
| reference_board | 350 | 10/18 | 52.110 | 52.110 | 52.101 | 52.058 | +0.009 | +0.053 |
| reference_board | 420 | 10/20 | 51.038 | 51.038 | 51.031 | 50.993 | +0.007 | +0.045 |
| example_board | 35 | 16/16 | 85.483 | 85.483 | 85.293 | 83.638 | +0.191 | +1.845 |
| example_board | 70 | 16/16 | 72.359 | 72.359 | 72.254 | 71.429 | +0.105 | +0.930 |
| example_board | 105 | 16/16 | 67.131 | 67.131 | 67.151 | 66.529 | -0.020 | +0.602 |
| example_board | 140 | 16/20 | 64.204 | 64.204 | 64.295 | 63.772 | -0.090 | +0.432 |
| example_board | 210 | 16/24 | 60.922 | 60.922 | 61.084 | 60.659 | -0.163 | +0.263 |
| example_board | 350 | 16/32 | 57.822 | 57.822 | 58.036 | 57.694 | -0.214 | +0.128 |
| example_board | 420 | 16/36 | 56.922 | 56.921 | 57.145 | 56.827 | -0.224 | +0.094 |

## 3. The memory law (`scripts/measure_solid3d_memory.py`, one fresh process per case)

Growth of the resident size over the build and the solve, against `memory.estimate_bytes("solid3d", n, cells, base=0)` (which carries the safety factor, so the ratio should stay below 1):

| layers | Cu um | cell mm | unknowns | slabs | growth GB | estimate GB | measured / estimate |
| --: | --: | --: | --: | --: | --: | --: | --: |
| 2 | 35 | 2 | 25 000 | 10 | 0.10 | 0.13 | 0.72 |
| 2 | 140 | 2 | 30 000 | 12 | 0.21 | 0.20 | 1.01 |
| 2 | 210 | 2 | 35 000 | 14 | 0.32 | 0.29 | 1.11 |
| 2 | 280 | 2 | 40 000 | 16 | 0.39 | 0.39 | 0.99 |
| 2 | 350 | 2 | 45 000 | 18 | 0.56 | 0.51 | 1.09 |
| 2 | 420 | 2 | 50 000 | 20 | 0.49 | 0.65 | 0.74 |
| 4 | 140 | 2 | 50 000 | 20 | 0.49 | 0.65 | 0.74 |
| 4 | 420 | 2 | 90 000 | 36 | 1.85 | 2.49 | 0.74 |
| 6 | 210 | 3 | 41 382 | 38 | 0.39 | 0.73 | 0.54 |
| 2 | 420 | 1.5 | 89 780 | 20 | 0.92 | 1.40 | 0.66 |
| 2 | 35 | 1 | 100 000 | 10 | 0.64 | 0.81 | 0.79 |

Control on the development tree's meaning of slabs: the same two-layer 35 um board with `n_diel` 12 and 16 (14 and 18 slabs of gap, no thick copper) took 0.321 and 0.558 GB at 35 000 and 45 000 unknowns, estimate 0.289 and 0.513: ratios 1.11 and 1.09, the same numbers as the thick-copper boards of the same unknown count. **The law needs no new constant**: a copper slab is a slab like a gap slab for the memory (the matrix has the same structure), the law reads the exact unknown count (`solid3d.unknowns`, which now counts the copper slabs; a test checks it equals the matrix) and the guard still refuses before anything is built (a test). The under-estimate of up to 11 % (0.00 to 0.05 GB) at 30 000 to 45 000 unknowns with 12 to 18 slabs exists today for gap slabs and belongs to the law (item e7, `fix/memory-law-measured`), not to this change.

## 4. Explanation of every shift (an unexplained shift would be a defect)

* **Frozen boards: no shift** (35 um, one slab, bit-identical).
* **Plates**: with 8 slabs through the metal the 3D solid and the independent solver (same slabs, same 1 um laminate) agree to 0.000 K (to 1e-6 K in the tests) on the seven plates without a via. The column moved up by 0.011 K (case 2), 0.056 K (10 mm Al), 0.003 K (10 mm Cu), 0.001 K (5 mm Al), less than 0.001 K on the others. Reason: with one slab the heat of the part entered at the middle of the plate; now it enters the face where it is, and the vertical gradient under a small part is resolved. The shift grows with `q t / k` under a source smaller than the plate (10 mm Al, 40 000 W/m2) and is zero where the plate is 1D. The earlier -0.056 K against the independent solver on the 10 mm aluminium plate is this effect. (The reference of the plain `plates.reference` leaves out the 1 um laminate of the program's plate; under a film of 1000 W/m2K at 40 000 W/m2 that is +0.13 K: a mapping artefact of that reference, not of the 3D solid, so the table uses the reference with the laminate.)
* **The plate with a via**: +0.015 K before and after; not a copper-slab effect (the barrel's copper area in `k_z` against the reference's 2 x 2 cell block).
* **Sweep**: the parts of both boards sit on copper; under a part over absent copper the column moves more (+0.84 K at 420 um, section 5). On these boards the column of the 3D solid moves by at most 0.001 K from 35 to 420 um of copper (56.922 to 56.921 on the example board at 420 um): the column mean of a 1D profile is the same with one node as with many, and the vertical gradient under these parts (10 to 20 mm on 100 mm boards) is small. The differences to the FVM (-0.224 to +0.191 K) and to the FEM (+0.045 to +1.845 K) are the ones the models already had at one slab (the FEM reads the coolest, 1.8 K at 35 um on the example board); they shrink with thick copper, as the models agree on a flat plate.
* **What the slabs give that the column cannot show**: the outer slab, 0.2 to 10 K above the column under the source (87.301 against 76.897 degC on the 10 mm aluminium plate, 66.387 against 66.224 on the 1 mm copper one) and below the independent surface (90.426): the surface needs the rule of item e22, not this branch.

## 5. Review: the face term, the convergence in the slabs, the FEM

**A defect of the first version, corrected.** Over absent copper the reported temperature under a part is the column plus the face term of `laminate.face_terms`. The first version passed the heat of a thick layer divided by its slab count, so the term was `q t / (2 n k)`; but it is added to the COLUMN (the mean of the slabs), not to the outer slab, and in 1D the face is `q t / (2 k)` above the column mean whatever `n` (the outer slab is `(n - 1) q t / (2 n k)` above the mean, the half outer slab adds `q t / (2 n k)`). The term is again the whole heat of the layer, the FVM's (`solid3d.solve_steady`; tests: the 1D closed form of a bare 420 um layer to 1e-6 and the arrays equal to the FVM's). `scripts/study_face_term.py --tree <checkout>` (40 x 40 mm, two layers, top bare, bottom full, a 4 x 4 mm part of 0.5 W, films 10 W/m2K, 1 mm cell), degC:

| copper | slabs | tree | column | outer slab | face term (K) | column + term (read-out) | outer slab + half slab (resolved face) | FVM column + term |
| --: | :-: | :-- | --: | --: | --: | --: | --: | --: |
| 140 um | 1 | `development` 0d45660b | 128.320 | 128.320 | 7.292 | 135.612 | 135.612 | 132.215 |
| 140 um | 2 | branch as first written | 128.380 | 131.708 | 3.646 | 132.026 | 135.353 | 132.215 |
| 140 um | 2 | branch after the review | 128.380 | 131.708 | 7.292 | 135.671 | 135.353 | 132.215 |
| 420 um | 1 | `development` 0d45660b | 118.291 | 118.291 | 21.875 | 140.166 | 140.166 | 135.910 |
| 420 um | 6 | branch as first written | 119.128 | 134.454 | 3.646 | **122.774** | 138.100 | 135.910 |
| 420 um | 6 | branch after the review | 119.128 | 134.454 | 21.875 | 141.003 | 138.100 | 135.910 |

The 35 um rows are identical on the three trees (137.275). The first version read the part over absent 420 um copper 17.4 K too cool, 13 K below the FVM; the earlier claim of this README that the solid moved by 0.001 K at most held for parts on copper only. After the review the read-out moves by +0.84 K at 420 um (the column: the bare laminate of a thick layer has a real gradient that one node did not see) and is 2.9 K above the face the solid resolves, the 1D term ignoring the sideways spreading in the bare laminate (hot side; the resolved face belongs to the surface read-out, item e22). The difference to the FVM (+5.1 K at 420 um) is the one the models had before (+4.3 K on `development`).

**The thick-plate warning.** With the 3D solid as the reference model `checks.check_thick_plates` used the words and the bound of the layered models (one temperature through the thickness, the half plate towards the laminate and the other copper layers missing). The 3D solid has those as slabs: the bound is now the through-thickness term only, worded against the column (test with a 2 mm, 5 W/mK layer).

**The column converges in the slabs** (independent solver `tests/helpers/layered3d.py`, 1 mm in the plane, 1 um laminate, `scripts/study_review_checks.py`): 10 mm aluminium plate 76.831 / 76.887 / 76.888 / 76.888 degC with 1 / 8 / 16 / 32 slabs through the metal, case 2 53.962 / 53.973 / 53.973 / 53.973, 10 mm copper 67.516 / 67.519 / 67.519 / 67.519. So the 0.056 K of the one-slab model is a real error of one slab, not an artefact of a reference cut like the program, and 8 slabs are converged to 0.001 K in the column (the surface is not: 90.388 / 90.245 / 90.209 on the aluminium plate).

**The FEM on the same plates** (`scripts/study_review_checks.py`; column maximum, program FEM with its copper slabs, degC; 3D solid in brackets): case 2 53.935 (54.039) at 2 mm, 53.947 (53.973) at 1 mm; 10 mm aluminium 76.777 (77.087), 76.810 (76.887); 10 mm copper 67.495 (67.560), 67.502 (67.519). Both resolve the plate and agree to 0.08 K of a 52 K rise at 1 mm, the FEM below and converging from below. The larger FEM differences of the sweep (+1.845 K on the example board at 35 um) are the known coarse-cell limit of the FEM on that board (FEM -2.7 % of the FVM at 2 mm and -1.3 % at 1 mm, `releases/2.8.0/fem-model/REVIEW_BRANCH5.md` 2.3; the converged independent value is 85.57 degC, `docs/validation.md`), not a defect of this branch; they shrink with thick copper because the spreading then dominates.

**Frozen numbers, decision of the review.** The harness cannot see the rule (every board is 35 um). A thick-copper board (two layers of 420 um, a part over absent copper beside copper, so the column, the face term and the slabs are all exercised) is added to `regress_boards.py` and its copy in `releases/regression-harness/lib/` at the 2.9.0 refreeze, as an addition (new records of every model, no previous number to compare, so no pending file now); cost: one board function and its name, a few seconds of harness time per cell, the records in `v2.9.0.json`. Until then the branch is guarded by its 14 tests.

**The memory law.** The under-estimate of up to 11 % (0.05 GB at most, at 30 000 to 45 000 unknowns) is small against the margin of the guard (60 % of the memory by default): safe, no fix in this branch (item e7). The heavy cases: the law estimates 3.7 GB for the two of 200 000 unknowns and 11.7 to 14.1 GB for the three of 250 000 to 425 000; on a 16 GB machine at the default fraction (9.6 GB) the guard of the constructor refuses those three before building anything. Order: the two 200 000 cases first, one at a time, on a quiet machine; the three larger only on a machine with more memory or with a raised fraction and swap watched. The light list of `measure_solid3d_memory.py` now holds the eleven cases of section 3 (four were run by `--one` before); the measurements were not re-run by the review.

## 6. What was not verified

* The heavy memory cases (200 000 to 425 000 unknowns): `scripts/measure_solid3d_memory.py --dry-run --heavy` lists them; not run.
* Thick copper with a metal block, an outline, imported copper or several parts against an independent solver (the energy balance with a via and parts on three layers is tested at 1 mm).
* The 3D solid against the FEM on a thick-copper board with a small part (where surface and column differ): item e22.
* `docs/validation.md` was not re-run; the review checked its tables: none quotes the 3D solid on copper above 105 um (the 3D solid tables are 35 um boards and metal blocks; the plates of 55.6 use `layered3d` and the FVM and FDM surface), so none needs a note.
* No GUI control changed, so no stress scenario was added.
