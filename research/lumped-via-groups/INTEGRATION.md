# Integration of the via group treatment into the Lumped model

What would enter `pcbthermal/` if the maintainer decides to adopt the work, with the measured impact of each choice. Nothing here is implemented; the measurements are on copies in memory (`lib/lumped_groups.py` on `research/lumped-analytic-vias/lib/lumped_patch.py`, `lib/lumped_zones.py`). Adoption goes on a `fix/` or `feature/` branch off `develop` with the whole battery. **All of it presupposes the micro well of `research/lumped-analytic-vias/INTEGRATION.md` 1.1** (the Krogh well per plane in series with the barrel, Kron reduced, `GZ` as a dictionary of couplings between sheets): without it the zones have no via model to join.

## 1. The three options

| Option | What | Mean / max error of the via effect, 36 simple boards | Example board, 8 boards | Cost |
| :-- | :-- | --: | --: | :-- |
| **A. Micro well and a warning** | micro well only (`L_nn`); the group term is not added; warning when a part has two or more vias | 13.6 / 62.5 % (too cool, up to +62 %) | -11.4 to -0.4 % | the micro well (120 lines), a check and a text |
| **B. Micro well, group term outside the footprint only** | `L_out`: the micro well in ring 0, the group term for the groups in the rings outside it (rows) | the same as A for arrays in the footprint (13.6 / 62.5 %); rows 8.0 / 10.9 % (against 34.6 / 50.2 % for A) | -11.4 to -0.9 % | A plus the group code, 40 lines |
| **C. Two zones in the footprint** | `L_zone` (README 5) | **4.4 / 20.1 %** | **-7.1 to -0.1 %** | A plus about 250 lines, 3 new functions |

The series group term of the earlier investigation (`L_grp0`, 18.0 / 38.7 % on the simple boards, -0.4 to -31.6 % on the example board) is **not** an option: the hypothesis of double counting inside the footprint is rejected (README 4.3), and the term is wrong in structure (a series resistance for a path with a vertical alternative).

**Recommendation of the researcher** (the reviewer has not seen it): option C if the Lumped model is corrected for the 2.5.0 branch; it is the only one that is within 10 % on the simple boards (35 of 36) and on the example board, and its failures are on the safe side on the example board and in the dense cases. If the effort is not wanted now, option A with the warning, never B (B adds the group code for rows only and leaves the arrays under a part at 13.6 / 62.5 %).

## 2. What changes for option C (`pcbthermal/lumped.py`)

* **A function `_core_mask(net, cov, vias)`**: groups of vias by single linkage on the nearest-neighbour distance (`scipy.spatial.cKDTree`, `scipy.sparse.csgraph.connected_components`, linkage at twice the larger nearest-neighbour distance, as in the earlier investigation); for each group of two or more vias in the footprint the cells within `0.7071 d_nn` of a via; the union is the core. No core, or a core above 92 % of the footprint: the network is the program's with the micro wells (and the micro peak).
* **In `_heater_network`**: the ring index gets two zone nodes (A = 0, C = 1, outside rings from 2); the sums by ring (S, films, dielectric, barrels, source) are by zone; links A-C and A-ring 1 as in `README` 5; the peak. About 250 lines of `lib/lumped_zones.py` are written as a copy of the function; in the program they would be a branch of it with the zone arrays built once.
* **Three functions**: `mutual_potentials` (the link of the real shapes, `(2 phi_AC - phi_AA - phi_CC) / (2 pi S)` over at most 700 cells per zone, one dense matrix product), `potential_excess` (the peak, with the `K0` kernel), `micro_peak` (the rim-to-mean resistance of the cell of one via times the heat it takes). Cost: 0.03 to 0.05 s on the example board.
* **Returned dict**: the same keys (`theta` of shape `(layers, rings + 1)`, `rho` increasing, `peak_extra`, `out`, `residual`); `solve_steady` and the peak search already use index 0 as the hottest footprint node.
* **Transient**: the zoned network was **not** given `K` and `C` (the time models of the Lumped model build the network through the same function). Until it is, the transient models must call the network with zones switched off (the micro wells only), or the zone network must be extended with the capacities of A and C (the capacities are sums of the cells, the same machinery as the rings). Left to the branch.
* **Tests to add on adoption**: the unit-cell cluster within 3 %; the 36 boards of `study_family.py` (a subset of 6: mean under 6 %); energy balance; the model without vias bit by bit; the logarithmic-potential link equal to Krogh plus `1 / (8 pi)` for concentric discs; a raster guard; a stress scenario with a footprint covered by 400 vias (`tests/test_gui_stress.py`).
* **Not changed**: the FVM, FDM, 3D solid, Analytic, the input files, the GUI (except the warning), the solvers.

## 3. Measured impact

Error of the via effect against the fine-grid layered reference (simple boards) and the corrected FVM (example board), percent; mean / maximum over each set.

| set | `L_prog` (program) | A: `L_nn` | `L_grp0` (earlier group term) | **C: `L_zone`** |
| :-- | --: | --: | --: | --: |
| cluster in a cell (16, README 4.1) | 14 to 56, max 55.9 | 4.0 to 28.3 | 3.2 to 8.2 | -0.6 to +2.4 |
| arrays under a footprint (36, 4.2) | 20.9 / 72.2 | 13.6 / 62.5 | 18.0 / 38.7 | **4.4 / 20.1** |
| the 30 of them with a partial core | 21.5 / 72.2 | 15.4 / 62.5 | 20.8 / 38.7 | 4.8 / 20.1 |
| layouts of README 6 (12) | 5.7 to 141 | 0.4 to 108 | -1.4 to -18.7, +13.8 | -2.6 to +19.9 |
| row of five (8) / lone via (24) | 72 / 73 (max 101 / 288) | 35 / 15 (max 50 / 31) | 8 / 15 (max 11 / 31) | 8 / 15 (the same) |
| example board (8) | -6 to +30 | -11.4 to -0.4 | -0.4 to -31.6 | -7.1 to -0.1 |

The maximum temperature of the example board in the Lumped model (`study_example_board.py`, degC; `FVM_fix` is the corrected FVM, rise 25 degC above the ambient added):

| board | fill | `L_prog` | A: `L_nn` | `L_grp0` | C: `L_zone` | `FVM_fix` |
| :-- | :-- | --: | --: | --: | --: | --: |
| 9 vias at 3.5 mm | open | 83.54 | 85.45 | 85.45 | 85.80 | 85.15 |
| 9 vias at 3.5 mm | Cu | 76.75 | 80.97 | 80.98 | 81.48 | 80.95 |
| 5 x 5 at 1.2 mm | open | 77.58 | 78.53 | 81.89 | 76.51 | 76.48 |
| 5 x 5 at 1.2 mm | Cu | 72.93 | 74.40 | 79.30 | 74.80 | 74.21 |
| 7 x 7 at 1.0 mm | open | 74.55 | 75.14 | 78.48 | 74.04 | 73.40 |
| 7 x 7 at 1.0 mm | Cu | 72.72 | 72.73 | 76.51 | 72.79 | 72.43 |
| 20 x 20 at 1.0 mm | open | 72.64 | 72.97 | 79.66 | 72.75 | 72.76 |
| 20 x 20 at 1.0 mm | Cu | 72.61 | 72.62 | 79.02 | 72.73 | 72.30 |

Option C moves the Lumped maximum of the example board by +2.3 K (open 9 vias) to -1.0 K (open 5 x 5) from the program's, towards the FVM; the series group term moves the dense arrays by +4 to +7 K away from it, which is the defect the review of the earlier investigation found.

## 4. Warnings

* **Always (Lumped model, vias present)**: for a via or a row outside the footprint of every heater, *"the Lumped model treats a via outside the footprint as a sink spread over a ring: its effect can be 10 to 30 % off on an effect of 0.1 to 2 K; use the FVM"* (already in `lumped-analytic-vias/INTEGRATION.md` 4).
* **Option A**: a part with two or more vias in its footprint: *"the Lumped model treats the vias of this part as one node: the via effect can be up to 60 % too small or 30 % too large depending on how much of the footprint they cover; use the FVM for via design"* (the extremes are from the 36 boards: +62.5 and -18.1 % for `L_nn`).
* **Option C**: *"the vias of this part are farther apart than the fin length of the top plane, or the footprint is elongated or the cluster is off its centre: the via effect of this part can be 20 % too small"* when `d_nn` exceeds 0.7 of the fin length `sqrt(S / g)` of the source layer under the footprint, or the aspect of the footprint exceeds 1.5, or the core centroid is farther from the footprint centroid than a quarter of the footprint's smaller side (rules from 3 boards of README 6, not stress-tested); and *"the raster cell is coarser than a tenth of the core"* when the core is under ten cells across (README 6, raster).

## 5. Risks

* The result of every Lumped run on a board with a part over vias changes by 0.5 to 5 K (the example board: +2.3 to -1.0 K from the program's); a CHANGELOG entry and a re-run of `docs/validation.md` follow (the via scenarios).
* The group (single linkage) and the core radius `0.7071 d_nn` are tested on regular arrays; irregular groups, several groups of different pitch in one footprint, vias on a ring (a guard ring) and a block under the part were **not** tested.
* The zone network reads the footprint polygon through coverage cells: a footprint that is not a rectangle (an L-shaped part) was not tested.
* The error on the unsafe side grows with an elongated footprint, a cluster off its centre and a sparse array (to +20 %); the warning names them, the correction is a project of its own (an axisymmetric peak, or a numerical cell solve per part).
* A Gerber board with 100 or more vias was not run (README 10).

## 6. Decisions left to the maintainer

1. Option A, B or C (or none: record the 13.6 / 62.5 % and the warning as the limit of the Lumped model); the researcher's recommendation is C, then A; B is not recommended.
2. If C: transient with zones (extend the network with capacities) or keep the transient on the micro wells only.
3. The raster rule: a guard or a note (the program's `Auto` cell size is not tied to the core).
4. The micro peak and the zone model go only in the Lumped model; whether the same `rim - mean` term belongs in the FVM-family peak read-out is a different question (the FVM reads cell means; its peak is a cell mean).
5. A reviewer before any adoption (the investigation has not been reviewed).
