# Integration of the zonal Lumped model into the program (design, measured impact, go / no-go)

What would enter `pcbthermal/` in 2.5.0 (the maintainer moved the zonal Lumped model into that version), written against `develop` as it is: the micro well per via, the cluster well per group with the macro radius capped at 0.75 fin lengths, Kron reduced barrel nodes (2.4.5); the footprint potentials aggregated in blocks (`fix/lumped-footprint-potentials`); the Lumped via warnings with their corrected bounds (`fix/lumped-via-warning-limits`). **Nothing is implemented in the program.** Every impact below was measured in this folder (README sections 4, 8 and 9). Adoption goes on a `feature/lumped-zones` branch off `develop` (a new model behaviour: a minor number, 2.5.0) with the reviewer and the whole battery. The prototype the design follows is `lib/zoned_lumped.py` (a copy of `lumped._heater_network` with the zone branch, replacing the program's functions in memory for the length of a context).

## 0. Go / no-go proposal

**Go, for 2.5.0, with the conditions in 0.2** (confirmed by the second review, README 10, with the corrections marked *second review* below). The decision rests on the hottest temperature, which is what the user reads, measured against references of three kinds.

### 0.1 The evidence in one table

Error against the reference, mean / maximum, percent; program = `develop`, zones = `Z_none` (micro well only in the zone nodes). Section numbers are those of the README.

| question | program | zones | where |
| :-- | --: | --: | :-- |
| via effect, 36 family boards, 0.5 mm | 10.8 / 31.8 (20 within 10 %) | 4.0 / 9.3 (36) | 4.1, 9.0 |
| via effect, 26 held-out boards | 18.2 / 108.9 (12 of 26) | 4.6 / 20.6 (23) | 4.1, 9.0 |
| **hottest temperature**, family / held-out (boards more than 2 % too cool) | 5.1 / 14.2 (9); 5.2 / 17.4 (8) | 2.6 / 7.2 (0); 1.6 / 7.6 (1) | 8.2, 9.0 |
| hottest rise against a **3D solver with the barrels drawn**, 6 cases | up to 14.0 % (the off-centre board) | up to 1.6 % | 9.4 |
| via effect against the same 3D solver | up to 32.9 % | up to 7.8 % | 9.4 |
| **square-wave profile**, peak against the FVM, 93 boards at 1 s (3 boards, 3 periods) | 9.6 / 28.9 (9.6 / 21.4) | 3.8 / 14.3 (2.0 / 5.4) | 9.2 |
| several groups under one footprint, 8 cases: effect / hottest rise | 14 to 74 % / up to 16.5 % | up to 19 % / up to 2.5 % | 9.5 |
| cost of a steady solve, example-type boards, in the loops | 0.05 to 0.12 s | 0.05 to 0.14 s | 9.6 |
| step response of the hottest point at 0.01 s | +63 to +74 % | +8 to +36 % | 4.2 |
| an array across the edge of the footprint (4.4 a) | 102 / 220 | 66 / 134 (**still far**; up to 16 % of the rise, profile as well) | 4.4, 9.2 |
| vias that conduct nothing, maximum against no vias | 0 | -1.5 to -6.1 % of the rise (cooler, unsafe) | 4.6, 8.2 |
| published case (Shen and others): the vertical path through a 12 x 12 array | -3 to +5 % of an independent solver | same (the fallback: a core above 92 %) | 9.3 |

### 0.2 Conditions of the go (what the implementation must contain)

1. **The profile runner changes in the same step** (README 9.2): `_LumpedAdapter.advance` and `lumped.step_responses` read the source vector and the zone peak of the system dict. A profile run with zones but the program's adapter puts the whole power on node A and reads the part up to 25 % of its rise too hot (measured, 93 boards: 11.5 / 31.3 %). This is not an option.
2. **A Lumped cell of 0.5 mm for any heater that will be zoned** (*second review*: not for every heater with a core: the nine vias of the program's example board are a core of 98 to 100 % of U1, which falls back to one node, and the rule "has a core" would move the example board by -1.18 K for nothing, README 10.5), plus the two zone warnings (4.3: at 1.0 mm the zones are 8.0 / 20.8 % in the effect against 3.9 / 9.1 % at 0.5 mm; the zones' hottest-rise error is 4.0 % at 1.0 mm and 2.9 % at 0.5 mm over the 93 boards, the program's 7.1 % at both). The cost is the 0.06 s of README 9.6.
3. **The decision between zones and the one-node network is made so that it does not jump with the raster** (*second review*: the count on the fine grid drops the vias outside the box of the footprint, README 10.4; it is also what `cell_for` reads, 11.3) (README 9.7: the inverted-T example board jumps 2.7 to 2.9 K between 1.0 and 0.5 mm with the share counted on the grid; the rule of 11.2 removes it) and **with a margin on both sides**: zones only when the core covers at most 92 % of the footprint on the grid AND on a fine grid (a core of 94 to 99 % leaves a handful of cells for A and the zone network reads the part 6 to 14 % hot: README 9.7).
4. **The one-node branch is the program's code, line for line**: the regression test of the frozen numbers (`tests/regression`, tolerance 1e-8 K) must pass on every board without a core. The research copy differs from the program by up to 1.3e-6 K on such boards (the peak coefficient of the single-node path is recomputed); the implementation does not recompute it (11.2).
5. **The warnings** of 11.4 and the user-guide text (the zone model is an approximation of the heat convergence on a core; its limits: an array across or just outside the footprint edge, dead vias, a raster coarser than a tenth of the core).
6. **The release notes may quote** the 3D check (three 16 mm boards, barrels drawn on a 0.125 mm grid: README 9.4) with its limit (a 0.3 mm barrel is about two cells across, so the constriction on a plated barrel is not resolved by it), not a gain on every board.
7. **The reviewer before the merge** and the checks of 11.6 on the final tree; the second review of this folder first.

### 0.3 What the proposal does not claim

* The published CFD number of Shen and others (1.86 K/W) was **not reproduced** (an independent unit-cell solver gives 1.461 K/W, equation (4) of the paper 1.587); only the vertical path was compared, and the program's models agree with the independent solver within 1 % (FVM, FDM) to 5 % (3D solid). No statement is made about the absolute error against that CFD (README 9.3).
* No board of this repository has been compared with a measurement. All errors are against fine-grid or 3D solvers of the same physics.
* The zones do not fix an array across or just outside the edge of the footprint (up to 16 % of the rise too cool in steady state and in a profile), nor the dead-via bias (the part read up to 6.1 % of the rise cool when the vias conduct nothing).
* The frozen-number records of the Lumped model move on the boards that have a core: of the 17 boards of the test only `plate_vias` (a 4 x 4 array under a pad) moves, by -4.30 K at the 2 mm setting with the cell of today and -4.12 K with the 0.5 mm cell of the design (README 9.8, 10.5); that is a model change on purpose and is refrozen at the 2.5.0 release. *Corrected by the review of `feature/lumped-zones`:* those two numbers are of `Z_none` (the cluster well left out of the zone nodes); the program implements the recommended `cap`, with which `plate_vias` moves from 140.3555 to 136.4534 degC at the 1 and 2 mm settings (**-3.90 K**) and from 140.1495 degC at the 0.5 mm setting (-3.70 K), and the time to 63 % of its part from 27.83 to 31.00 s (+11.4 %); the records are held by the pending shift `tests/regression/data/pending/lumped-zones.json` until the refreeze (11.7).

## 1. The two decisions that the first run settled, and the third that the checks add

1. **The cluster well in the zone nodes** (README 4.1, 9.5; *second review: recommendation changed to `cap`, README 10.8*). The design has a switch, `zone_macro`, with the default **`none`** (micro well only in the zone nodes; the cluster well stays for every group that touches a ring outside the footprint). By the rule written beforehand (the macro term in the zones must improve the mean by 1 point on the sparse boards; it improves it by 0.2) it is left out. The several-groups boards of 9.5 are the one place where `cap` is better by 3 to 6 points of the effect on four of eight cases (a group of 9 vias 10 mm from another one under a 20 mm part; four clusters at the corners of a square), with the hottest rise within 2.5 % either way. Either is safe. *Corrected by the second review:* the first text said that `cap` needs no change to `viaconstriction.ring_couplings`; the micro peak of both variants needs the barrel-only couplings and the cells of each group, so `want_barrel` is needed in both and only `zone_nodes` goes with `cap`. Decision of the maintainer (10.1); the recommendation of the second review is **`cap`** (README 10.8).
2. **The raster** (README 4.3): tie it to the core, or fix it at 0.5 mm for a heater with a core and warn. The recommendation stands: **0.5 mm**, because the tie leaves four boards above 10 % and costs the same.
3. **The fallback decision** (README 9.7): the share counted on the Lumped grid flips between rasters on 4 of 93 boards and on the inverted-T example board; the proposal is the two-sided rule of 11.2.

## 2. What changes, file by file

### `pcbthermal/viaconstriction.py`

* `ring_couplings(...)` gets two optional arguments, `zone_nodes=()` (nodes where the cluster-well term is left out; only with `zone_macro="none"`) and `want_barrel=False` (needed with either choice: the micro peak reads it) (return the barrel-only couplings and the cells of each group too, `(gz, via_gz, seen)`). With the defaults the function and its result are the present ones, bit for bit (a test).
* Two closed forms next to `krogh`: `annulus_out_resistance(S, r_c, a)` (mean-to-outer-wall of an annulus with a uniform source, inner side insulated) and `rim_minus_mean(S, R, a)` (the rim of the Krogh cell above the area mean, per watt taken by the via; used by the micro peak). Both derived and checked against integration in the earlier folder; both go in `docs/theory.md` 6.1 with the figure.

### `pcbthermal/lumped.py`

See 11.1 for the function list and the order. *Corrected by the second review:* if the maintainer chooses `zone_macro="cap"`, only `zone_nodes` disappears; `want_barrel` and the two closed forms stay.

### `pcbthermal/checks.py`, `pcbthermal/api.py`

See 11.4 and 11.3.

## 3. The raster

Fix a Lumped cell of 0.5 mm for any heater that will be zoned (*second review*: decided on the fine count of 11.2, before the grid exists; a heater whose core fills more than 92 % of the footprint keeps the clip, so the example boards stay bit-identical); keep the clip 0.5 to 1.0 mm for the others (a part without vias, or with one via per footprint, loses nothing at 1.0 mm). See 11.3 for the helper and the three call sites in `api.py`.

## 4. The transient and the profile runner (measured, README 9.2)

The zone network is a lumped system `C dtheta/dt + K theta = Q s` like the rings: the capacity vector is the sum of cell capacities (a test: the sum over the nodes of the footprint equals the program's footprint capacity), `s` the unit source vector, the peak a function of the state. Two substitutions in the program's code, both tested in this folder (`lib/zoned_lumped.py`: `_advance_zoned`, `step_responses_zoned`):

* `_LumpedAdapter.advance`: `src = power * system["source"]` (the unit source vector split between A and C by the footprint coverage) instead of `src[layer * R] = power`;
* `lumped.step_responses` (used for the decision average-or-resolve when the Lumped model is the reference) with the same source vector and `_own_point` = the zone peak.

The rest of the adapter is unchanged: `observe` and `_own_point` call the patched peak, the cross-heating reads `rho` (kept increasing: `rho[0] = 0`, `rho[1] = 1e-9`) and the state of the other heaters' rings, `begin` takes `theta * p_init` (the steady unit solution times the power). Square wave, three boards at 0.1, 1 and 10 s: peak within 5.4 % of the FVM's average steady rise (program 21.4 %); 93 boards at 1 s: 3.8 / 14.3 % against 9.6 / 28.9. Not run: a table profile, a one-shot profile, two parts with one of them zoned (the code path is the same but untested).

## 5. The footprint potentials (done in `develop`)

`fix/lumped-footprint-potentials` put the block aggregation into the program (`_footprint_potentials_blocks`): the program's link term is now 0.0 % and its peak term at most 1.0 % from every cell on the 24 cases of README 4.5 (re-run, 9.0). The zones' own integrals (the A-C link and the peak field of A) need their own block aggregation for a zone of more than 700 cells (`_block_points`), written against the same idea; reuse the program's helper where its interface fits (it aggregates one footprint with a boundary; the zones need two regions) and otherwise keep `_block_points`.

## 6. What does not change

The FVM, FDM, 3D solid, Analytic; the input files; the solvers; the GUI apart from the warnings and the Lumped cell; a board without vias (**bit for bit**, a test, 11.2); a board whose vias lie in no footprint or form no group in it; a footprint whose core covers more than 92 % of it or none of it (the program's network, bit for bit); the Lumped model on a board with an outline (it still runs the equivalent rectangle; the via positions scale with the box, so the nearest-neighbour distances and with them the core change: the inverted-T example board gets a core at 1.0 mm that the original has not, README 9.7); the Lumped time simulation on a board with an outline (not available, as now).

## 7. Tests to add on adoption

From the earlier list (kept) and the checks of this pass:

* equality with the program, **bit for bit (`==`)**, when no zone applies: no vias, vias outside every footprint, a core above 92 %, zones off (`tests/test_lumped.py`); the research test of this folder holds 1e-9 because its copy is not the program's code;
* `ring_couplings` with the new arguments at their defaults equals the old result; with `zone_nodes` the macro term is absent only there;
* vias that conduct nothing change the maximum by less than 6.5 % of the rise on a sparse array (the review's regression test: measured -6.1 % at most on 62 boards);
* the peak integral against the annulus closed form within 3 % above 700 cells (blocks), and the stride shown to fail it; the link A-C of concentric discs equals Krogh plus `1 / (8 pi S)` within 3 %; the unit-cell cluster within 3 %;
* the six family boards against stored references (mean under 6 %) **and the hottest-temperature metric on the same boards (no board more than 2 % too cool)**; energy balance of the zoned network (1e-9, 1e-6); mirror symmetry; capacities summing to the program's footprint capacity; the step response ends at the steady value;
* **new from this pass:** (a) a square-wave run with zones on the three boards of README 9.2 against stored FVM values (peak within 10 % of the rise) and a test that fails when `advance` puts the power on A alone (the control of 9.2 reads 13 to 25 % hot); (b) the fallback decision does not jump: the inverted-T example board gives the same Lumped maximum at 1.0, 0.75 and 0.5 mm within the rounding of the one-node branch (`test_fallback_decision_does_not_jump_with_the_raster` of this folder); (c) the cell of 0.5 mm is used for a heater with a core and the clip for the others; (d) the three warnings on synthetic footprints; (e) several groups under one footprint (README 9.5, the board (a) two clusters 10 mm apart within 20 % of the effect and 3 % of the rise);
* a stress scenario in `tests/test_gui_stress.py`: a footprint covered by 400 vias (core above 92 %, the fallback), a part with a 5 x 5 array under a larger footprint run with the Lumped model and a square-wave profile (zones with the transient), a board with two parts of which one has the core, a board with an outline and a core (the equivalent rectangle).

## 8. Documents that move

`docs/theory.md` 5 and 6.1 (the zone model: formulation, figures 1, 2, 4 and 12 of this folder, the A-C link, the peak, the capacities, the profile runner, the limits and the warnings; the sentence "a zonal Lumped model remains in 'Planned'" goes), `docs/validation.md` (the via scenarios of the Lumped model, the example board with its copper-fill gain, the new figures, **both metrics**: the via effect and the hottest temperature; the 3D check of 9.4 and the profile check of 9.2 with their limits), `docs/models.md`, `docs/versions.md` (the item leaves 'Planned'; the cut cells and the zonal model stay in 2.5.0 scope by the maintainer's decision), `CHANGELOG.md`, the user guide (`pcbthermal/help/index.html`: one paragraph on the zone model, the raster of 0.5 mm for a part with a core and the warnings, plus the words that `tests/test_help.py` must find), the warning texts, and the tooltips (11.5). The theory text and the changelog text are drafted in `docs/` of this folder.

## 9. Risks

* The Lumped result of every board with a part over a dense group of vias changes (README 9.8: of the 17 boards of the frozen test, one moves, by -3.90 K at the 2 mm setting with `cap` (-4.3 K was `Z_none` at the cell of today; review of `feature/lumped-zones`); the example board and its nine vias at 3.5 mm do not, because the core of the group of nine covers 98 to 100 % of the footprint and the heater falls back to one node; *second review*: the first text said "no core"). A CHANGELOG entry and a re-run of `docs/validation.md` follow. A user of an earlier version sees a different temperature for a part over a via array: it is nearer the FVM on all the boards measured (hottest rise 7.1 % to 4.0 % at 1.0 mm, 2.9 % at 0.5 mm over 93 boards) and hotter than the program on the boards where the program read too cool.
* The core radius `0.7071 d_nn`, the share 0.92 and the 700-point decimation are assumed constants. The share 0.92 was probed in this pass (README 9.7): **with the core between 94 and 99 % of the footprint the zone network reads the part 6 to 14 % hot**, so the threshold protects; no board of the 93 lies between 0.85 and 0.97 at 0.1 mm, so the constant is not exercised by them and the margin is untested on a board that does. Irregular groups, a guard ring, a block under the part, an L-shaped footprint and more than four groups under one footprint were **not tested**.
* The error on the unsafe side (the part too cool) grows with an array across or just outside the footprint edge, up to 16 % of the rise (README 4.4, 9.2); the warning names it. The correction beyond that (an angular resolution, a numerical cell solve per part) is a project of its own.
* Cost: nil measured (README 9.6, also inside the top-path and power-coefficient loops); a Gerber board with 100 or more vias and many groups was not run (`core_mask` loops over the groups and the `ViaSet` is built once per call).
* The independent 3D check could not resolve the barrel (README 9.4); the layered references share the idealisation with the models (README 8.6).
* The reference cell of the research references moved from 1/16 to 1/8 mm (peak memory), with changes of 0.1 to 1.2 points (README 9.0).

## 10. Decisions left to the maintainer

1. The macro switch: `none` or `cap` (closer by 3 to 6 points on four several-group cases; `zone_nodes` not needed). **Recommended by the second review: `cap`** (same accuracy on the 62 boards, better on several groups, one rule for every node; README 10.8).
2. Whether the temperature map paints the core cells with node C (the map shows the value of A in the whole footprint: the maximum and the profile read the peak, the map, zone statistics and hot-spot list read the field). **Recommended: yes**, in the step of the zone branch, with a test of the area mean (README 10.8).
3. Whether the micro peak belongs also in the one-node fallback (the prototype leaves it out so that the branch is the program's; the earlier folder had it and attributed 0.5 point of mean error to it in the zones). **Recommended: no** (the fallback stays the program's code; README 10.8).
4. The Lumped cell of 0.5 mm for a heater that will be zoned (proposed, as corrected by the second review) or a looser rule (a cell of a tenth of the core, with the four boards above 10 %). **Recommended: 0.5 mm for a zoned heater**; the cell is one per board, so the other heaters of that board move by the raster too (to be said in the CHANGELOG).
5. Whether the warning text of the program (the group past the edge, off centre, elongated) changes with the zones: 11.4 proposes a text for the zoned heaters and keeps the present one for the one-node ones. **Recommended: as 11.4**, post-run (README 10.8).

## 11. Implementation design for `pcbthermal/lumped.py`

Branch `feature/lumped-zones` off `develop`; five commits in this order, each with its tests and, before the merge, the whole battery. The code that is already written and tested (19 tests, the studies of README 4 and 9) is `lib/zoned_lumped.py`; the implementation is a port of it into the program's functions, not a rewrite, and the research copy stays as the record.

### 11.1 Functions of `pcbthermal/lumped.py`

| function | what | origin in `lib/zoned_lumped.py` |
| :-- | :-- | :-- |
| `_core_mask(net, cov, vias)` | cells of the footprint within `CORE_R * mean d_nn` of the vias of every group with two or more vias in the footprint; `None` when there is no group | `core_mask` |
| `_fine_core_share(net, cov, vias)` | the share counted on a grid of about 0.1 mm over the footprint box (the raster cell split by an integer factor, at most 600 fine cells a side; weighted by the coverage); the vias outside the box are dropped, not clipped onto its border (*second review*, README 10.4) | `fine_core_share` |
| `_block_points(w, dx, dy, max_cells)` | cells of a region aggregated in blocks (position, weight, self distance) | `block_points` |
| `_mutual_potentials(w_a, w_c, dx, dy)` | `2 phi_AC - phi_AA - phi_CC`, the link A-C of the real shapes | `mutual_potentials` |
| `_peak_fields(...)` | the matrix (points x 2) of the field of A per unit heat to C and to ring 1, and the bump coefficient of the core; computed once per network | `_peak_fields` |
| `_ZonePeak` | holds those and the micro-peak data; `__call__(theta)` gives the rise of the hottest point of the footprint | `ZonePeak` |
| `_heater_network` | gets the zone branch (below); the node index of the footprint is 0 (one node) or 0 and 1 (A and C); the sums by node are by zone; the dict gains `source`, `peak`, `nz` | the body of `heater_network` |
| `_own_point(system, theta)` | `system["peak"](theta)` when present, else the present formula | `_own_point` |
| `_LumpedAdapter.advance`, `step_responses` | the source vector and the peak (section 4 above) | `_advance_zoned`, `step_responses_zoned` |
| `cell_for(problem, cell_mm)` | 0.5 mm when a heater will be zoned (a group of two or more vias in its footprint and a fine share of at most `MAX_CORE`, counted on a 0.1 mm grid of the footprint box with the vias outside the box dropped; no Lumped grid needed), else `min(max(cell_mm, 0.5), 1.0)` (*second review*: "has a core" would move the example board, README 10.5) | `tied_cell_mm` (changed: the tie is replaced by 0.5 mm) |

Constants at the top of the module with their source in a comment: `CORE_R = 0.7071`, `MAX_CORE = 0.92`, `FINE_MM = 0.1`, `MAX_POTENTIAL_CELLS` (the 900 of the program) and `MAX_ZONE_CELLS = 700`.

### 11.2 The zone branch of `_heater_network`, and what stays bit-identical

* **Decision** (one place, at the top): `core = _core_mask(...)`; `zones = core is not None and core.sum() < foot.sum() and core.sum() <= MAX_CORE * foot.sum() and _fine_core_share(...) <= MAX_CORE`. Both counts must pass: the grid count keeps cells in A, the fine count does not jump with the raster (README 9.7). The fine count is computed only when the grid test passes (cost nil otherwise).
* **If not `zones`, the function runs the present code path unchanged** (`nz = 1`; the peak from the present `peak_coef`; `_footprint_potentials` as in `develop`): not a recomputation that agrees to 1e-6 but the same lines. The branch is written as `if not zones: <present body>` split into a private `_one_node_network(...)` that is the present body moved, so that the diff of the present code is a move and the tests of the frozen numbers (tolerance 1e-8) pass without a refreeze on boards without a core. The research copy re-implements the one-node path inside the zone function and differs from the program by up to 1.3e-6 K: do not port that part.
* **Zone branch**: node 0 = A, node 1 = C, rings from 2. `idx2 = where(idx == 0, where(core, 1, 0), idx + 1)`. The sums by node (S, films, dielectric gz, barrels, capacities) are `ring_sum` over `idx2`. The vias are placed by `viaconstriction.ring_couplings` on the zone-aware node index: vias in the core give wells at node C, the others at A or at the rings as in the program; a group wholly outside every footprint is untouched (a test: equal to the program, bit for bit); a group that straddles the edge spans C and rings and the cluster well sees the area of the nodes it touches. With `zone_macro="none"` the cluster-well term is left out of the two zone nodes only (`zone_nodes=(0, 1)`).
* **Links**: A-C: `pot / (2 pi S_A)` with `pot = _mutual_potentials(cov * (idx2 == 0), cov * (idx2 == 1), dx, dy)`; A to ring 1: `annulus_out_resistance(S_A, r_c, a_f)` plus the half ring of the program (the Bessel factor on this link is not applied: README 4.1, change below 0.2 point); rings outside as the program.
* **Source**: `source[layer, A] = 1 - f_C`, `source[layer, C] = f_C` with `f_C` the coverage-weighted share of the footprint in the core; the steady state uses `Q = power * source`.
* **Peak**: `_ZonePeak`: the largest of the hottest point of A (the field of A, `K0` kernel of the layer), the core mean plus the micro peak, and the core mean plus the micro peak plus the bump of a core hotter than A. The bump is essential (README 4.1: without it the maximum jumps from 9.1 to 20.1 %). `peak_extra` is relative to node A, as the program's relative to node 0, so `solve_steady` reads it unchanged.
* **Capacities**: `cap[l, node]` = sum of `net.C[l]` over the cells of the node (the same machinery as the rings).
* **Returned dict**: the same keys; `theta` has one more column; `rho[0] = 0`, `rho[1] = 1e-9` when `nz = 2` (keeps the profile for the temperature map increasing: the footprint cells take the value of node A); extra keys `source`, `peak`, `nz`, `warnings`.
* **Bit-identical, by construction and by test**: a board without vias; vias outside every footprint; one via (or no group) per footprint; a core above 92 % on either count; `zones` off (an internal switch for the tests, not a user setting); every other model; the input files.

### 11.3 `pcbthermal/api.py`

`min(max(o.cell_mm, 0.5), 1.0)` appears three times (steady, step response, profile: `api.py` lines 639, 756 and 802 on `develop`; the Analytic's calls on the lines next to them keep the clip): replace by `lumped.cell_for(problem, o.cell_mm)` so that the steady state, the step response and the profile runner use the same grid. The cell is one per board: one zoned heater moves the whole board to 0.5 mm, and the other heaters' results move by the raster (*second review*). Measure the cost of a 200 mm board with many heaters at 0.5 mm on the branch before the merge (the distance transforms of `_heater_network` run per heater over the whole grid). The Analytic keeps its clip. No new option in `SolverOptions` (the cell is a consequence of the geometry); the log line of the run states the cell used and why when it is 0.5 mm for a core.

### 11.4 Warnings (`pcbthermal/checks.py`)

* The existing `lumped_via_cool_warning` (group past the footprint edge, centre off by more than 0.1 of the smaller side, side ratio above 1.5) stays for the **edge** case (i) with the bound for the zoned model: "up to 16 % of the rise too cool" (README 4.4, 8.4: the zones' error for the 5 x 5 array across the edge, +0.4 to +6.6 K, 1 to 16 % of the rise) instead of "about 11 K, a quarter of the rise"; for the off-centre and elongated cases (ii) and (iii) the zoned heater gets a softer text (the zones measured 1 to 5 % and 2 to 4 % of the rise: README 8.4) while a heater that stays one node (no core, or a core above 92 %) keeps the present text. The text change needs the heater's zone state, known after the run: raise it with the other post-run checks (`check_fin_channels`, `check_thick_plates`) from the network of the run, not from `check_model_limits` before it.
* Two zone warnings, post-run, per zoned heater: *"the raster cell is coarser than a tenth of the core: the via effect of this part can be 20 % too small"* (core across fewer than ten cells; with the cell fixed at 0.5 mm it fires on 6 of 36 family boards and 4 of 26 held-out; at 1.0 mm on 32 and 21); and, **new, for the profile**, nothing more (the zones' time response has no warning of its own: the early excess at the switching edge is on the safe side, README 9.2).
* A stress case in the tests: a heater with 400 vias (core above 92 %) raises no zone warning and runs the one-node network.

### 11.5 Tooltips, user guide, Preferences

* No new control, hence no new tooltip required by `tests/test_tooltips.py`; the **Lumped model checkbox tooltip** (`gui/tips.py`) gets one sentence ("a part over a dense group of vias is split into the core of the vias and the rest of the footprint").
* The user guide (`pcbthermal/help/index.html`): in the Lumped model section, one paragraph and one figure (figure 1 of this folder: the footprint cut into A and C) describing the zone model, the cell of 0.5 mm for a part with a core, the three limits (an array across or just outside the footprint edge, dead vias, a raster coarser than a tenth of the core) and the warning; the words `core`, `zone`, `rest of the footprint` into `tests/test_help.py`. The Preferences do not expose the constants (`CORE_R`, `MAX_CORE`) and neither the macro switch.
* The Power Calculator runs the board model backwards with the models chosen there: when the Lumped model is chosen it gets the zones and the 0.5 mm cell like any run (check on the adoption branch that `inverse.py` calls `lumped.solve_steady` and not a copy of the clip).

### 11.6 Tests and the order of the work

1. **Footprint check**: the one-node move (`_one_node_network`) alone, no change of behaviour: the whole battery and the frozen numbers pass, `==` to the earlier values. Commit 1.
2. `viaconstriction.ring_couplings` with `zone_nodes` and `want_barrel` (if `none` is chosen) and the two closed forms with their tests. Commit 2.
3. The zone branch, steady state only: `_core_mask`, `_fine_core_share`, `_block_points`, `_mutual_potentials`, `_peak_fields`, `_ZonePeak`, the branch, with the tests of section 7 that do not involve the transient: six family boards (mean under 6 %), the hottest-temperature metric (no board more than 2 % too cool), the dead-via offset under 6.5 % of the rise, energy balance, symmetry, capacities, bit-for-bit equality when no zone applies, the fallback jump test. Commit 3.
4. The transient: `_LumpedAdapter.advance`, `step_responses`; the square-wave tests on the three boards of README 9.2 against stored FVM values and the control that fails on the unpatched source; a test that a constant power through the adapter ends on the steady peak (to 1e-9 with the split source; 5 to 17 % hot with the whole power on A, README 10.1); the stress scenario. Commit 4.
5. `cell_for` and its three call sites, the warnings, the guide, the tooltip text, the documents of section 8, the CHANGELOG. Commit 5, then the reviewer, then the whole battery, then the merge.
6. **Checks on the final tree** (the `tester`): `research/lumped-zones-adoption/scripts/run_all.py` plus `study_profile.py`, `study_shen.py`, `study_3d_barrels.py`, `study_multigroup.py` and `study_core_raster.py` against the program (the studies import the program, so they run on the merged tree); the reference numbers of README 9 compared with the ones the program then gives; every shift linked to an item.

### 11.7 Frozen numbers and the release

The regression test (`tests/regression`, tolerance 1e-8 K) is the guard of 11.2. Measured on the 17 boards (`out/study_frozen_impact.txt`, README 9.8): with the zones **one Lumped steady record moves materially** (`plate_vias`, a 4 x 4 array of 16 vias under a pad: -4.30 K at the 2 mm setting, -3.91 K at 0.5 mm); with the share counted only on the Lumped grid also the inverted-T example board (+2.71 K at 2 mm, 0 at 0.5 mm): the fine rule of 11.2 removes that one (+6.6e-7 K, rounding of the research copy). The times to 63 % of the step response of the Lumped model on `plate_vias` move too (not measured; the zoned step response differs by 8 to 36 % at 0.01 s and 0.3 to 36 % over the three boards of README 4.2). *Second review (README 10.5):* with `cell_for` as first written ("has a core") the example board and the profile board would move by -1.18 K, the inverted-T board by -0.20 K and `plate_vias` by -4.12 K at the 2 mm setting; with `cell_for` on "will be zoned" only `plate_vias` moves (-4.12 K: the zones at 0.5 mm instead of 1.0 mm) and the 63 % times of that board. At the release (after the version bump, `research/release-regression-245` procedure): the records that moved are refrozen with `expected_shifts_2.5.0.json` naming this item; any other record that moves is a defect until explained.

*Measured by the review of `feature/lumped-zones` (the program, `zone_macro` = `cap`, `cell_for` on "will be zoned"):* the numbers above are of `Z_none`. With `cap`, `plate_vias|lumped` moves at every setting to 136.4534 degC (all three settings run at 0.5 mm): -3.90 K from the 140.3555 degC of the 2 and 1 mm records, -3.70 K from the 140.1495 degC of the 0.5 mm record; its part's field maximum 131.79 -> 131.95 degC and mean 131.79 -> 129.97 degC (the core painted with node C), the field checksums with the raster; the time to 63 % of U 27.83 -> 31.00 s. Every other record of the 17 boards (the five models, 2, 1 and 0.5 mm) is unchanged, except `reference_board|lumped|0.5`, which moved before this branch (`fix/lumped-footprint-potentials`, a board without vias). Because the frozen file of 2.4.5 can only be remade after the version bump (`study_freeze_reference.py` refuses a run of another version) and the battery must stay green, the moved records are held between releases by a **pending shift**, `tests/regression/data/pending/lumped-zones.json` (written by `tests/regression/make_pending.py`: the item, the branch, why, the new numbers), which the test applies over `v2.4.5.json`; `v2.4.5.json` is not edited. At the 2.5.0 release the refreeze folds the shift in and the pending file is deleted (the test fails on a pending file of an older base version).

### 11.8 Open items inside the branch

* The cost on a Gerber board of 100 or more vias with many groups (measure `core_mask` and the fine count there before the merge).
* The start-from-steady-state criterion of README 9.2: evaluated by the second review and dropped (ill-posed: the first window runs 0.4 to 2.4 K above the last in every model, the FVM included, README 10.1).
* The cost of a 200 mm board with many heaters at the 0.5 mm cell (11.3).
* A table profile and a one-shot profile with a zoned heater, and two heaters with one of them zoned: run once on the branch.
* The `Z_cap` question for the several-group boards (10.1).

*Measured by the review of `feature/lumped-zones` (probes outside the repository, the program of the branch; FVM references at 0.25 or 0.5 mm):*

* **The implementation against the prototype:** `zoned_lumped.py` with `zone_macro="cap"` and the fine rule gives the same Lumped maximum as the program to the last bit (difference 0.0) on five boards (3 x 3 at 2.0 mm under 12 mm, 5 x 5 at 1.5 mm under 14 mm, 5 x 5 at 1.2 mm 2.5 mm off the centre of a 12 mm part, 3 x 3 under a 16 x 8 mm part, 4 x 4 at 1.0 mm under 20 mm); against the FVM at 0.25 mm the zones are +1.65, +1.97, +0.48, -1.90, +0.79 % of the rise and one node -1.94, -10.40, -19.95, -4.60, -7.84 %.
* **The fine share is not raster-free when it is counted on the raster of the run** (the fine grid replicates the support of the coarse cells): a 3 x 3 array at 2.35 mm under 8 mm counts 0.925 / 0.916 / 0.925 at 1.0 / 0.75 / 0.5 mm, so the 0.75 mm run zoned a part that `will_be_zoned` (counted on the 0.5 mm raster) keeps one node, and its hottest rise stepped from +2.6 to -1.9 % of the FVM's. Fixed: `solve_steady` and the transients pass the decision of `will_be_zoned` to `_heater_network` (`zone_ok`), and a board with an outline is decided on its equivalent rectangle (the board the Lumped model solves; a 3 x 3 array at 3.0 mm under 10 mm with a corner cut off counted 0.948 on the original box and 0.837 on the rectangle).
* **A part that `will_be_zoned` says zoned and that the 0.5 mm raster keeps one node** (the grid share above 0.92 while the fine share is 0.82 to 0.92; four boards found: 4 x 4 at 1.7 and 1.8 mm under 8 mm, 4 x 4 at 2.25 mm under 10 mm, 5 x 5 at 1.8 mm under 10 mm): the user gets the one-node network at 0.5 mm, within +0.07 to +0.93 % of the rise of the FVM at 0.25 mm (zones forced on the same boards +0.09 to +1.47 %); the board moves to 0.5 mm for nothing, and the post-run check now says that the footprint was kept as one node.
* **The profile outside a zoned footprint** was interpolated from C (the interval from the footprint to ring 1 read node 1, which lies inside), in the map, the frames of a profile and the cross-heating of the other parts; now from A (`lumped._radial`). The hottest temperatures do not move; the mean field of `plate_vias` moves by 0.009 K.
* **Profiles not run before:** a one-shot table on the 5 x 5 array under 14 mm, peak +6.7 % / valley +1.2 % of the FVM's average rise (one node -37.0 / -17.0 %); a periodic table +3.8 / +0.6 % (one node -7.9 / -12.1 %); two parts of which one is zoned, square waves of 1 and 2 s, -6.7 / -10.7 % with zones and -8.1 / -12.0 % with one node, the hottest part being the second, one-node part (its own steady error is -8 %), so the cross-heating of the zoned part is not the cause.
* **Cost and robustness on a Gerber-like board** (100 x 80 mm, four layers, 25 parts, 662 vias: arrays under 12 parts, stitching rows 0.6 mm from the edges, three vias at or across the edge, 250 scattered vias; and the same board with rounded corners): every run finished, energy balance 2e-13 W, 12 (11 with the outline) parts zoned; `cell_for` 0.01 s, the pre-run checks 0.04 s (0.10 s with the outline), the Lumped run 0.45 s (0.98 s) against 0.12 s (0.35 s) with one node at 1.0 mm, peak 0.21 GB; most of the difference is the 0.5 mm raster that one zoned part gives the whole board. A 200 x 200 mm board with 30 parts (5 x 5 arrays under 15 of them): 1.3 s against 0.3 s, 0.75 GB. The raster moves the parts that are not zoned too: on the Gerber-like board two small parts on bare laminate moved by 9 to 18 K between 1.0 and 0.5 mm (nearer the FVM at 0.5 mm).
* **Blocks, top path, power coefficient, computed h, 2 and 6 layers, a source on the bottom layer:** the zoned part runs and balances in every case (-0.5 to +5.7 % of the rise against the FVM at 0.5 mm, one node -12.6 to +8.8 %).
