# Integration of the via constriction into the Lumped and Analytic models

What would enter `pcbthermal/` if the maintainer decides to adopt the work, with the measured impact of each proposal. Nothing here is implemented; the measurements are on copies in memory (`lib/lumped_patch.py`, `lib/analytic_patch.py`). Adoption goes on a `fix/via-constriction` branch off `develop` with the whole battery (the missing constriction is a defect of the two models, not a feature).

## 1. What changes

### 1.1 `pcbthermal/lumped.py`

* **The barrel conductance of the vias is kept apart** from the dielectric in the network (`fvm.Network` gets `gz_via`, or `lumped` rebuilds it from `problem.vias` as the patch does: the cells of the vias are those of `cell_index_of_point`).
* **Groups of vias**: nearest-neighbour distance of every via (`scipy.spatial.cKDTree`), two vias joined if their distance is at most twice the larger nearest-neighbour distance (`scipy.sparse.csgraph.connected_components`).
* **Per ring and group** (n vias in the ring, N_g in the group, the rings the group touches): micro radius `r_c = min(sqrt(A_ring / (pi n_ring)), d_nn / sqrt(pi))`; target radius `a = e^(-1/4) r_v`; cluster radius `r_cl = sqrt(N_g) r_c`; macro radius `R = sqrt(sum of the areas of the touched rings / pi)`; the well of the plane `l`: `R_w(l) = Krogh(S_l, r_c, a) + N_g Krogh(S_l, R, r_cl)` (the second term only if `N_g > 1` and `R > r_cl`), `Krogh` the closed form of `lib/constriction.py`.
* **Kron reduction** of the star (plane l -- well -- barrel node l -- barrel conductance -- barrel node l+1 ...) per ring: `GZ[(l, m)]` couplings between sheets, replacing `gz` (adjacent only) in the matrix and in the effective-loss sums of the interior factors. The matrix keeps its size.
* About 120 lines; the mode "off" (legacy) reproduces the present results bit by bit (tested).
* **Not proposed**: the cap of the macro radius at 0.75 fin lengths (calibrated, worsens the gain of the fill), the inward-flow term of the peak (worse), a cap on the cell of a lone via (no effect).

### 1.2 `pcbthermal/analytic.py`

* **Tiles of 1 mm around vias** when there are vias: `_tile_grid` returns tiles of at most 1 mm (coarsened so that no more than 1200 tiles are active: `sqrt(estimate / 1200)` on the size; `MAX_ACTIVE` in the patch).
* **Spread of the barrel conductance over the four nearest tiles** with bilinear weights between tile centres (replaces `c_via[bb, a] += ...`), except for a via with a neighbour closer than 0.7 tiles (a cluster keeps its tile) and for a via outside the heater footprints and closer than half a tile to one.
* **Self-term** added to the diagonal of `G` (the modal response of the tile means) for every tile with vias, per layer: for a tile with `n <= 1` (a fraction of a via): `[ln(R_blk / a) - 1/4] / (2 pi S n)`, `R_blk = R_tile / sqrt(n)`; for `n > 1`: `ln(R_tile / r_cl) / (2 pi S) + Krogh(S, r_c, a) / n`, `r_c = min(R_tile / sqrt(n), d_nn / sqrt(pi))`, `r_cl = sqrt(n) r_c`.
* About 90 lines; mode "off" reproduces the present results bit by bit (tested). The transient of the Analytic model smears the vias and scales them to the steady maximum: it inherits the corrected steady value, no change.

### 1.3 What does not change

The FVM, FDM, 3D solid, the input files, the GUI, the solvers, the Lumped/Analytic handling of heatsinks, blocks, outline and parts. `docs/theory.md` sections 6 and 7 (Lumped and Analytic) and `docs/models.md` get the text of `docs/`; `docs/validation.md` the new numbers (3 below).

## 2. Measured impact

Over the simple boards of this folder (error of the via effect, percent; mean and maximum, `README.md` 4 and 6):

| board kind | Lumped program | Lumped proposed | Analytic program | Analytic proposed |
| :-- | :-- | :-- | :-- | :-- |
| unit cell (about 100) | 17.0 / 60.6 | 1.4 / 4.5 | 6.9 / 34.9 | 0.4 / 1.3 |
| lone via | 73.4 / 287.8 | 15.1 / 31.4 | 83.6 / 236.2 | 2.3 / 4.0 |
| row of five | 72.1 / 100.6 | 8.0 / 10.9 | 36.3 / 56.8 | 0.7 / 1.4 |
| 3 x 3 arrays (48) | 26.8 / 69.7 | 11.0 / 24.1 | 11.0 / 42.3 | 0.3 / 1.1 |
| thermal pads (6) | 8.1 / 17.4 | 6.1 / 14.2 | 4.5 / 9.8 | 1.4 / 2.0 |

The proposed Lumped model is on the safe side (the via effect underestimated) for dense arrays and clusters; the lone via is the limit.

## 3. Impact on the documents and tests

**`docs/validation.md`** (the via scenarios, the example board): maximum temperature of the example board with open vias (degC) and the change of the fills, `study_via_fill_rows.py`:

| | FVM 1 mm | FVM_fix 0.25 | Lumped program | Lumped proposed | Analytic program | Analytic proposed |
| :-- | --: | --: | --: | --: | --: | --: |
| T_max, open vias | 85.81 | 85.15 | 83.54 | 85.45 | 84.69 | 85.22 |
| conductive paste, change K | -0.20 | -0.19 | -0.28 | -0.20 | -0.25 | -0.19 |
| copper fill, change K | -4.49 | -4.20 | -6.79 | -4.47 | -6.32 | -4.27 |
| no vias, change K | +8.86 | +9.57 | +11.15 | +9.25 | +10.02 | +9.50 |

The figures that quote "Lumped and Analytic 6.3 to 7.0 K" (`docs/validation.md`, `docs/models.md`, `research/via-fill`) change to about 4.3 to 4.5 K; the statement that the five models agree on the order of the fills but not on the size of the copper gain becomes true to 0.3 K. The example board's T_max in the Lumped model rises by 1.9 K, in the Analytic by 0.5 K (they moved towards the FVM).

**Tests** that exist and were run with the proposal installed for the whole session (`QT_QPA_PLATFORM=offscreen`, 173 tests of the program that run the models, listed in README 1): all pass; none of them pins the Lumped or Analytic copper gain. To add on adoption: the unit-cell identity (the program's Lumped model equals the one-cell closed form without the constriction; with it, within 5 % of the fine-grid reference: `tests/test_via_constriction.py` of this folder is the model), the example-board gain (4.2 +/- 0.5 K for both models), "off" bit by bit, the 5 x 5 pad within 3 % of the independent solver for the Analytic, the row of five within 12 % for the Lumped, a stress scenario (400 vias on a 40 mm board) in `tests/test_gui_stress.py` for the Analytic coarsening. The whole battery (about 8 minutes) before merging.

## 4. The old behaviour: keep it, warn, then remove

* **Keep as an option for one release**: `SolverOptions.via_model = "constriction"` (default) or `"legacy"` (present results; saved in the project so that an old file reopens with the numbers of the version that made it). The reason is traceability, not quality: the legacy gain of a copper fill is 35 to 60 % too large and the effect of any via cluster 10 to 70 % too large in these models.
* **Warning when "legacy" is chosen with vias on the board** (the Results summary, like the other model warnings): *"Legacy via model: the Lumped and Analytic models join the planes through the barrel conductance only and leave out the resistance of the heat converging on the barrel; the effect of copper-filled vias is overstated by 35 to 60 % (example board: 6.8 K against 4.2 K). Use the default."*
* **Warnings for the limits that stay** (new model, vias present): *Lumped*: a via (or row) outside the footprint of every heater: *"the Lumped model treats a via outside the footprint as a sink spread over a ring: its effect can be 10 to 30 % off; use the FVM"*; *Analytic*: more than 1200 tiles needed: *"tiles coarsened near the vias (many vias): the via effect is less accurate"*.
* **Option to remove the legacy** after one release (decision of the maintainer).

## 5. Risks

* The Lumped proposal underestimates the effect of dense arrays of open barrels by 8 to 24 % (the safe side, but a user comparing with the FVM sees a difference); the cause is the footprint-ring physics (README 5.4), and a more accurate macro term was not found.
* The Analytic 1 mm tiles rest on every via spacing tested being at least 0.8 mm; at 0.5 mm pitch the cluster formula is applied inside tiles larger than the pitch (not tested).
* The constants assumed, not derived: the isolation 0.7 of a tile, the guard of half a tile near a heater, the coarsening at 1200 tiles, the group linkage at twice the nearest-neighbour distance.
* A model of the via that is closer to the FVM changes every saved result of a board with vias in these two models (0.5 to 2 K): a CHANGELOG entry and a re-run of `docs/validation.md`.
* The via is still a point feature of the layered model: the barrel of a real board (drilled planes, thick copper pads, plating of the pad) is up to 4 to 27 % off (`point-via-convergence` 3.3).

## 6. Decisions left to the maintainer

1. Adopt the two proposals (and on which branch), or only the Analytic one (the cheaper and nearly exact) and a warning for the Lumped model.
2. Keep the legacy option for one release or remove it at once.
3. The Lumped model: accept the safe-side error of dense arrays, or study the macro term further (a roadmap item: the footprint ring against a sink at its centre).
4. Gerber boards: repeat the study on a real board with 100 or more vias (needs the research environment of `gerber-import`).
