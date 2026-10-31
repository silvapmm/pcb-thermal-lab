# Integration of the zonal Lumped model into the program (design, not yet measured)

What would enter `pcbthermal/` if the maintainer adopts the zones after the 2.4.5 release, written against `develop` as it is (2.4.5: micro well per via, cluster well per group with the macro radius capped at 0.75 fin lengths, Kron reduced barrel nodes, `Network.gz_via` for the rings without vias). **Nothing is implemented and nothing has been measured**: the measured impact of each choice is the output of the studies of the README, to be pasted here after the run; the numbers quoted below are the earlier folder's, on the program up to 2.4.4. Adoption goes on a `feature/` branch off `develop` (a new model behaviour, so a minor number) with the reviewer and the whole battery. The prototype that the design follows is `lib/zoned_lumped.py`.

## 1. The two decisions that the first run settles

1. **The cluster well in the zone nodes** (README 4.1). The design below has a switch, `zone_macro`, with the default **`none`** (micro well only in the zone nodes, the cluster well kept for every group that touches a ring outside the footprint). Reason: the link A-C holds the convergence of the heat of A on the mean of the core including the core-internal term `1 / (8 pi S)`, and the cluster well of a group that fills its node describes the same convergence; the zones were also tuned and reviewed with the micro well alone. If the first run shows `Z_cap` better by 1 point of mean error or more on the sparse boards, the default becomes `cap` and the switch disappears (the 2.4.5 function is then used as it is). If it shows no difference, `none` stays because it is the simpler statement.
2. **The raster** (README 4.3): tie the raster to the core, or warn. The design supports both; the choice is the maintainer's after the numbers.

## 2. What changes, file by file

### `pcbthermal/viaconstriction.py`

* `ring_couplings(...)` gets two optional arguments, `zone_nodes=()` (nodes where the cluster-well term is left out) and `want_barrel=False` (return the barrel-only couplings and the cells of each group too, `(gz, via_gz, seen)`). With the defaults the function and its result are the present ones, bit for bit (a test).
* Two closed forms next to `krogh`: `annulus_out_resistance(S, r_c, a)` (mean-to-outer-wall of an annulus with a uniform source, inner side insulated) and `rim_minus_mean(S, R, a)` (the rim of the Krogh cell above the area mean, per watt taken by the via; used by the micro peak). Both derived and checked against integration in the earlier folder; both go in `docs/theory.md` 6.1 with the figure.

### `pcbthermal/lumped.py`

Function list (all private except the last, `cell_for_cores`):

| function | what |
| :-- | :-- |
| `_core_mask(net, cov, vias)` | groups of the program's `ViaSet`, cells within `0.7071` mean nearest-neighbour distances of the vias of a group with two or more vias in the footprint; `None` if there is no core |
| `_block_points(w, dx, dy, max_cells)` | the cells of a region aggregated in blocks (position, weight, self distance) |
| `_mutual_potentials(w_a, w_c, dx, dy)` | `2 phi_AC - phi_AA - phi_CC`, the link A-C of the real shapes |
| `_peak_fields(...)` | the matrix (points x 2) of the field of A per unit heat to C and to ring 1, and the bump coefficient of the core; computed once per network |
| `_ZonePeak` | a small class that holds those and the micro-peak data; `extra(theta)` and `__call__(theta)` give the peak above node A and the rise of the hottest point |
| `_heater_network` | gets the branch: the node index of the footprint is 0 (one node) or 0 and 1 (A and C); the sums by node (S, films, dielectric, barrels, capacities) are by zone; the links, the source split by area, the peak. The unit source vector, the `_ZonePeak` and the number of footprint nodes `nz` are returned in the dict (`source`, `peak`, `nz`) |
| `_footprint_potentials` | block decimation (section 5) |
| `_own_point(system, theta)` | `system["peak"](theta)` when present, else the present formula |
| `cell_for_cores(problem, cell_mm)` | the raster tied to the core (section 3) |

* **How the zone network sits on the 2.4.5 well.** The node index used by `ring_couplings` is the zone-aware one (`idx2`): vias in the core give wells at node C, vias in the rest of the footprint (a lone via not in a group) at node A, vias outside at the rings, exactly as the program places them in rings; groups that straddle the edge span C and rings, and the cluster well sees the area of the nodes the group touches (`a_touched`), unchanged. So: **a group that lies wholly outside the footprint is untouched by the zones** (a test: equal to the program). The micro well is the program's.
* **How the link A-C relates to the cluster well.** Chain for the heat of the rest of the footprint: A mean, link A-C, C mean, [cluster well, only if `zone_macro="cap"`], micro well, barrel. See decision 1. The cluster well inside the zone node is capped at 0.75 fin lengths by the program's rule; `R_macro` of a group that fills the core is the core's own radius, so the term vanishes for dense cores and is nonzero only for cores whose cells are not filled by the vias' cells.
* **Capacities for the transient.** `cap[l, node] = sum of net.C[l] over the cells of the node`, the same machinery as the rings (a footprint of two zones has two capacities per layer that add up to the program's footprint capacity; a test). No extra approximation: the zones are lumped capacities of their cells.
* **Source split.** `source[layer, A] = 1 - f_C`, `source[layer, C] = f_C` with `f_C` the coverage-weighted share of the footprint in the core. Replaces `Q[layer * R] = power` in the steady state and `src[layer * R] = powers[i]` in `_Stepper` users.
* **Transient entry points.** `step_responses` and `_LumpedAdapter` (`src[...] = powers[i]`, `_own_point`) read the source vector and the peak object from the system dict. The initial condition `theta.ravel() * p_init` and the cross-heating read `rho` and `theta[lay]` unchanged (`rho` stays increasing: `rho[0] = 0`, `rho[1] = 1e-9`). `profiles` is untouched.
* **Returned dict.** The same keys; `theta` has `nz - 1` more columns than before (the callers use index 0 as the footprint node and `rho` for the profile, so nothing else changes); `peak_extra` is relative to node A.
* **Temperature map.** The footprint cells all take the value of node A (`np.interp` at distance 0). A cosmetic change to paint the core cells with node C is left as an option: the map is then not the program's for a board with vias and the stored-value tests move.
* **The line count.** About 250 lines as a branch of `_heater_network` plus the four helper functions; the research copy is `lib/zoned_lumped.py` (about 850 lines with docstrings).

### `pcbthermal/checks.py` and `pcbthermal/api.py`

* The warnings of `zoned_lumped.zone_warnings` (an elongated footprint, a core off the centre, a core under ten cells across: two texts), raised after the run through the same path as `check_fin_channels` and `check_thick_plates` (the network is built in the run, the core is known there): *"the footprint of this part is elongated or its vias are off its centre: the via effect of this part can be 20 % too large (the part too cool)"* (side ratio above 1.5, or core centroid farther from the footprint centroid than a tenth of the smaller side), and *"the raster cell is coarser than a tenth of the core: the via effect of this part can be 20 % too small"* (not issued when the raster is tied). The rules were chosen on the 72 boards of the earlier folder on which they were checked; study 4 and study 3 count how many boards each flags and whether the bad boards are among them.
* `api` clips the Lumped cell to 0.5 to 1.0 mm. With the tied cell, the clip's lower limit stays 0.5 mm; `lumped.cell_for_cores(problem, cell_mm)` is called where the clip is applied (so that the steady state, the step responses and the profile runner use the same grid).

## 3. The raster

Two options, to be decided after study 3:

* **Tie** (design): `cell_for_cores` returns `min(cell_mm, max(0.5, width_of_the_narrowest_core / 10))`; the width of the core of a group is read from the bounding box of its vias in the footprint plus twice `0.7071 d_nn`. Cost: up to 4 times more cells than 1 mm for a board of cores of 5 mm; the Lumped model remains much cheaper than the FVM; the number is measured by study 3 on the example board. Risk: the Lumped result then depends on the vias through the grid, so changing a via can change the cell and the discretisation error together; a continuous rule (the cell proportional to the core, no thresholds) is the closest to that and the one proposed.
* **Warn** (cheaper): the second warning above, with the raster unchanged. The earlier folder measured 8.0 / 20.8 % at 1 mm against 3.6 / 9.1 % at 0.5 mm, misses on the safe side.

## 4. The transient and the profile runner

The zone network is a lumped system `C dtheta/dt + K theta = Q s` like the rings: the capacity vector is the sum of cell capacities (above), `s` the source vector, the peak a function of the state. `lib/zoned_lumped.step_responses_zoned` is the program's `step_responses` with the two substitutions, and `tests/test_zoned_lumped.py::test_step_response_ends_at_the_steady_value` is its first check; the response of the zoned footprint against the FVM in time is study 2. The profile runner (`run_profile`, `_LumpedAdapter`) needs the same two substitutions; **no profile run has been tried with the zones** (not verified).

## 5. The footprint potentials (an independent fix)

`lumped._footprint_potentials` keeps every step-th cell above 900. The block decimation of `_block_points` removes the aliasing; the earlier folder read the program's link to ring 1 short by 4 to 11 % on 20 to 30 mm footprints at 0.5 mm. It changes the result of every board with a large part (with or without vias), so it is **proposed as its own `fix/` item**, measured by study 5 on its own (the maximum temperature of a 4-layer board with a 20 and a 30 mm source), not folded into the zones. If the maintainer prefers one change, the zones already use blocks for their own integrals.

## 6. What does not change

The FVM, FDM, 3D solid, Analytic; the input files; the solvers; the GUI apart from the warnings; a board without vias (to rounding); a board whose vias lie in no footprint or form no group in it (to rounding); a footprint whose core covers more than 92 % of it or none of it (the program's network); the Lumped model on a board with an outline (it still runs the equivalent rectangle, whose via positions are scaled by the same factor as the board: the nearest-neighbour distances then change by that factor and with them the core, a limit that the 2.4.5 well already has).

## 7. Tests to add on adoption

From the earlier list, on the 2.4.5 well, plus the ones this design needs:

* equality with the program when no zone applies: no vias, vias outside, a core above 92 %, zones off (`tests/test_lumped.py`);
* `ring_couplings` with the new arguments at their defaults equals the old result; with `zone_nodes` the macro term is absent only there;
* vias that conduct nothing change the maximum by less than 6 % of the rise on a sparse array (the review's regression test);
* the peak integral against the annulus closed form within 3 % above 700 cells (blocks) and the stride shown to fail it;
* the link A-C of concentric discs equals Krogh plus `1 / (8 pi S)` within 3 %;
* the unit-cell cluster within 3 %; the 36 boards of the family (a subset of 6: mean under 6 %); energy balance of the zoned network (1e-9, 1e-6);
* capacities: the sum over the nodes of the footprint equals the program's footprint capacity; the step response ends at the steady value;
* the model without vias bit by bit (rounding); mirror symmetry; a raster guard; the three warnings on synthetic footprints;
* a stress scenario in `tests/test_gui_stress.py`: a footprint covered by 400 vias (core above 92 %, the fallback), a part with a 5 x 5 array under a larger footprint run with the Lumped model and a square-wave profile (zones with the transient), a board with two parts of which one has the core.

## 8. Documents that move

`docs/theory.md` 5 and 6.1 (the zone model: formulation, figures 1, 2 and 4 of this folder, the A-C link, the peak, the capacities, the limits and warnings; the sentence "a zonal Lumped model remains in 'Planned'" goes), `docs/validation.md` (the via scenarios of the Lumped model, the example board with its copper-fill gain, the new figures), `docs/models.md`, `docs/versions.md` (the item leaves 'Planned'), `CHANGELOG.md`, the user guide (`pcbthermal/help/index.html`: one paragraph on the zone model and the warnings, plus the words that `tests/test_help.py` must find), the warning texts, the Preferences if the macro switch were exposed (it is not proposed to expose it).

## 9. Risks

* The Lumped result of every board with a part over vias changes (the earlier folder: the example board moved -1.1 K to +4.7 K from the program up to 2.4.4; the move from 2.4.5 is what study 1 measures). A CHANGELOG entry and a re-run of `docs/validation.md` follow.
* The core radius `0.7071 d_nn`, the share 0.92 and the 700-point decimation are assumed constants (sensitivity in the earlier README 6); irregular groups, several groups of different pitch in one footprint, a guard ring, a block under the part and an L-shaped footprint were **not tested**.
* The error on the unsafe side (the part too cool) grows with an elongated footprint, a cluster off the centre and a sparse array, up to 20 %; the warning names them. The correction beyond that (an axisymmetric peak, a numerical cell solve per part) is a project of its own.
* Cost: two dense matrices of at most 700 x 700 per heater and per network build, and the `K0` of the kernel on the same size; the top-path loop and the power-coefficient loop of `api._solve_with_tc` rebuild the network at each iteration, so the cost multiplies by their iteration counts (3 to 7). Not measured (the earlier folder measured hundredths of a second on the example board and stated that this was not a result of its review); study 3 prints the time of the example board.
* A Gerber board with 100 or more vias was not run.
* The prototype was written without being run; the first runs of the tests are the first test of the prototype, and the numbers of the README are only valid after they pass.

## 10. Decisions left to the maintainer

1. The macro switch (decision 1): decided by the first run unless the maintainer wants a rule fixed beforehand.
2. Tie the raster or warn (section 3).
3. The footprint-potential fix with the zones or on its own (section 5; the recommendation is on its own).
4. Whether the temperature map paints the core with node C (section 2).
5. Whether the micro peak belongs also in the one-node fallback (the prototype leaves it out; the earlier folder had it).
6. A profile run with the zones: required before adoption, not yet tried.
