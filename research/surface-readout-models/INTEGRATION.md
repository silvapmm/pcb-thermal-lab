# Integration: the surface read-out in the Analytic, the 3D solid, the transient and the Lumped

What to change in the program, where, what it costs, what it was measured to do, and the decisions that belong to the maintainer. Nothing here is implemented: every rule was written on a copy (`lib/rules.py`, `lib/transient.py`) and run on the program's own results; the numbers are those of `README.md` (section numbers in brackets). The branch would be `feature/surface-readout-models` (plan item e1), after `feature/solid3d-copper-slabs` (e2) for the 3D solid.

## 1. The proposals, one by one

| # | Model | Proposal | Where | Size | Measured |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | Analytic | **Rule F**: the surface of the two outer faces from the model's own field and the uniform conductances of its sheet, the parabola of `thickness.offsets`; arrays `T_surface`, `T_surface_mean` (equal: the sheet has no partial cells), `T_surface_flag` (`t/a` > 0.5), extras as `thickness._finish` | a new function in `thickness.py` (`attach_field(res, problem, sheet)`; the sheet is the dict of `analytic._effective_sheet`, which already holds `g_diel`, `h_top_eff`, `h_bottom_eff`); called from `analytic.solve_steady` and its adapter | S to M | within 0.03 K of the FVM parabola on the plates and case 2 [4.1, 4.2]; -0.02 to +1.06 of the true term against the independent 3D; 0.42 to 2.57 mK on the harness boards, within 1 mK of the FVM's on 20 of 22 [4.4]; 5 ms |
| 2 | 3D solid | With copper slabs (e2): surface = first slab + `q_top dz / (2 k)`, computed; with one slab (every copper up to 105 um): **rule S**, the parabola fed with the solid's own z links | `solid3d.solve_steady` after `theta_all`; `Solid.board_slab`; arrays as the FVM | S (after e2) | 8 slabs within -0.00 to +0.13 K of the independent surface on the eight plates, +0.09 K on case 2 (the solid's column offset); 4 slabs +0.01 to +0.73 K; 1 slab = the FVM parabola to 0.002 K [4.1, 4.2, 4.5] |
| 3 | Transient (FVM, FDM) | **Rule T**: the same parabola on every kept frame; the integrator keeps the full node vector for the rows of the outer layer and reads the fluxes as `thickness.attach` does (the source, the film, the couplings of `K` to nodes of other layers); new optional field `surface` (frames, 2, ny, nx) of `TransientResult`; the headline stays the column | `fvm.transient_from_network` (in its time loop `x` is the full vector; today only `[:nb]` is stored, so the laminate sub-nodes are lost), `fdm` likewise, `thickness.frame_offsets` new | M | 1D boards: exact from Fo >= 0.3, upper estimate below (1.27 to 5.66 times the term at Fo 0.003 to 0.1), within 3 % from Fo = 1; from Fo = 1 the surface error differs from the node error by at most 0.0095 K [4.7] |
| 4 | Analytic transient | rule F on every frame (`analytic.solve_transient` already returns the frames) | as 1 | S | same as 3 on three 1D boards [4.7] |
| 5 | Lumped | **No absolute surface.** The Layer entry and the part-table cell say, for a part on an outer face of a thick layer: 'the surface is at most `q'' t / 2k` = X K above this model's column value; the Lumped has no face flux' (text only, the bound already computed by `checks.check_thick_plates`) | `checks.py`, `plots.py`/`gui/results_view.py` text (tooltip of the `n/a`), the guide | S | the bound on the TERM is above the true term on 8 of 8 plates and case 2, and on 21 of 22 harness parts (not over absent copper); the absolute 'upper bound' fails on 8 of 22 parts (up to 50 K) [4.3] |
| 6 | Lumped transient | none | | | not run |

## 2. Design of each proposal

**2.1 `thickness.attach_field` (Analytic; the Lumped is NOT a client).** Inputs: the result (`T` per layer), the problem, the sheet. Steps: `q_src` per layer from the parts (`rules.source_flux`: power over footprint area on the cells of the footprint); top face of layer 1 `q_top = q_src - h_top_eff theta_1`, `q_bot = -g_diel[0] (theta_1 - theta_2)` (`-h_bottom_eff theta_1` for one layer); bottom face of layer L likewise (`lib/rules.py` `field_rule`, 35 lines); `offsets`; fill the arrays through the existing `_finish` with `fill=None` (written for a model without partial cells). The part-over-absent-copper trap: the Analytic's column already holds `laminate.face_terms`? This was **not checked**; before implementing, read how `analytic.py` reads a part over a copper window (the Analytic averages the fill in an effective sheet, README 4.4); the surface there is the sheet's, with its limits.

**2.2 3D solid.** `solid_rule` (`lib/rules.py`): for `n_cu` = 1, `q_down` = the sum over the couplings of slab `s0` to slab `s0 + 1` of `-K[r, c] (theta_r - theta_c)` per cell area, `q_top` = source minus the film `g_top theta`, then `offsets`; for `n_cu` > 1 face = `theta[s0] + q_src (t / n_cu) / (2 k)`. The slab count follows item e2's rule (1 up to 105 um, `min(ceil(t / 70 um), 8)` above, the FEM's rule of `DESIGN.md` 3.2). The column of the layer becomes the mean over the sub-slabs (the earlier folder's patched module, `through-thickness-readout` 5); that moves nothing for 35 to 105 um (one slab).

**2.3 Transient.** In `transient_from_network` the vector `x` has every node. At each kept frame, for the outer-layer rows only (`ny x nx` cells): `inner = sum over columns of K outside layer 1 (-K[r,c] (x_r - x_c))`, `film = (g_top + g_heatsink) x_r`, `q_top = Q/area - film - block`, `q_bot = -inner - film_bottom - block` (the code of `thickness.attach`, written per frame: `thickness.attach` itself takes a steady `theta`, so a refactor into `frame_offsets(net, theta, problem)` returning `d_top`, `d_bottom` lets `attach` call it too). Frames store `T + d`. Cost: a sparse product per kept frame (n_out about 40 to 400). The estimate flag per frame: raised for the first `t^2/(0.3 alpha)` after a change of the power of the part (0.9 s for 10 mm of copper, 36 ms for 2 mm, 10 us for 35 um): for ordinary copper never visible; drawn from the thickness and `k / (rho c)` of the copper layer only. The headline of profiles, animations, graphs and the Difference view stays the column (decision 5, `SURFACE_DECISIONS.md` 4 and 8, which already say it for the transient).

**2.4 Lumped wording.** Text only (proposal 5). The words proposed (to be reviewed): *'This model has no heat flux through the face of the copper, so it gives no surface temperature. For a part on an outer face of a thick layer the surface is at most `q'' t / 2k` = X K above the column value of this model (a bound on the through-thickness term only; it does not contain this model's own error). Use the FVM, the FDM, the FEM or the 3D solid for the surface.'* The number X exists in `checks.check_thick_plates`.

## 3. The wording that carries the risk

The audit's error pattern is an 'upper bound' that is not one. Three statements must be numbered in the text of the program: (a) the Lumped bound is a bound on the **term** (surface minus column), true on 8 of 8 plates and 21 of 22 harness parts, **not** where the part sits over absent copper (the bare laminate under it adds the laminate face term, 105 to 1029 mK on `drawn_ell`) and **not** a bound on the temperature; (b) the parabola is an upper estimate for `t/a` > 0.5 (the flag exists) and for a frame below Fo = 0.3; (c) the Analytic and the Lumped carry their own column error into the number, so a surface there is `column + term`, never better than the column.

## 4. Impact on the numbers

* **No frozen number moves** by design: every proposal adds arrays that nothing reads (the rule of 2.8.0: Tj, margin, power limit, top path, the Power Calculator and the calibration stay on the column, `SURFACE_DECISIONS.md` 7). It was argued, not measured, here: the feature branch runs `PCBT_FROZEN_CELLS=2,1,0.5` and the test that the non-surface numbers are bit-identical with the arrays switched off (as `tests/test_thickness.py` does for the FVM and FDM).
* **3D solid with slabs moves numbers only above 105 um** of copper (no harness board has any): the e2 branch's own pending file.
* Memory: `TransientResult.surface` adds `2 / layers` of the frames; the Analytic and solid arrays are `2 x ny x nx` floats.

## 5. Tests the feature branch needs

1. Closed forms: a 1D board (a part over the whole face, insulated): rule F, rule S and rule T give `q t / 2k` on every outer face (the pattern of `tests/test_rules.py` of this folder).
2. Case 2 of Muzychka and others at 1 mm: the Analytic and the 3D solid (1 slab) against the program's FVM parabola within 0.05 K; the 3D solid with 8 slabs against the independent surface within 0.15 K (+0.09 K column offset); the paper's Table 4 through the independent solver.
3. The six plates and the via plate of `lib/plates.py`.
4. Transient: the frame rule at steady state equals `thickness.attach` (1e-6 K, `tests/test_transient.py` of this folder); a 10 mm copper plate at Fo 0.1, 1 against the column solver (ratios 1.30 and 1.00).
5. The Lumped refuses an absolute surface (the array is absent), the text carries the bound and the sentence that it is not a bound on the temperature.
6. Nothing that decides a number reads the new arrays (monkeypatch test of 2.8.0).
7. Stress scenarios in `tests/test_gui_stress.py` for the new Layer entries of the Analytic and the solid, and for a transient run with the frame surface.
8. Documents: `docs/theory.md` 1.2 (the text of `docs/theory.md` of this folder), the user guide (`pcbthermal/help/index.html` and `tests/test_help.py`), the tooltip of the `n/a`, `docs/validation.md` 55 (the numbers of this folder), `CHANGELOG.md`, the Decisions Log.

## 6. Order

1. `feature/solid3d-copper-slabs` (e2), as planned. 2. `feature/surface-readout-models` (e1): Analytic rule F and the Lumped text first (S to M, no number can move), the 3D solid rule second (on top of e2), the transient last (it touches the integrator). The Lumped text and the Analytic can ship without the transient.

## 7. Decisions for the maintainer

| # | Decision | Recommendation |
| :-- | :-- | :-- |
| 4 (plan) | The Lumped surface as an upper bound | **Not offered as a temperature.** The plan's condition (never below the FEM surface on the plates and the harness boards) fails: 8 of 22 parts (9 at 1 mm), up to 50 K, because of the Lumped column (outlines, copper windows). Offer only the bound on the term, worded as such, in the Layer entry (proposal 5) |
| 5 (plan) | Headline of the transient and the Difference view | **Column**, confirmed by the measurement (4.7 and section 5 answer 4): a difference between models is a difference of column |
| A | Rule F for the Analytic, flagged 'estimate' | Yes (S to M); the harness numbers are mK, the plates within 0.03 K of the FVM; the part over a copper window needs a check first (2.1) |
| B | Rule T for the transient frames of the FVM and the FDM | Yes if the time is there; it is the only item that touches an integrator; else leave `n/a` and say so, which is the 2.8.0 behaviour |
| C | The Lumped and Analytic frames | Analytic yes (proposal 4); Lumped frames no number, leave `n/a` |
| D | The FEM's thin-copper terms are 2 to 37 times smaller than the FVM's | Send to the comparison campaign (cause not investigated; mK) |

## 8. What this folder did not decide

The slab rule of e2 (its own research); a block under the part; the bottom face; real boards; local sources in time against a 3D transient (none exists in the repository, a research tool would have to be written: a time-stepping version of `layered3d`).
