# Integration: the through-thickness read-out in the program

Design for entering the program if the maintainer adopts the recommendation of `README.md` section 9. Nothing here is implemented; every size and impact comes from `README.md` (the studies) or is marked as to be measured in the branch.

## 1. What changes and what does not

| Item | Changes | Does not change |
| :-- | :-- | :-- |
| the solved temperatures of the FVM, FDM, Lumped, Analytic (A) | nothing | every node, balance, time to 63 %, the frozen records |
| the 3D solid (C) | the copper slab of a layer above a threshold becomes `n_cu` slabs; the layer temperature is read as the mean of them | the harness boards (35 um copper): bit-identical |
| the results (A) | the array `T_surface` (2, ny, nx: top face of layer 1, bottom face of layer L, absolute temperatures; the same array and name as the FEM design, `releases/2.8.0/fem-model/DESIGN.md` 5.4), a surface peak and mean per part, and a flag per heater `thick_estimate` (t/a above 0.5: upper estimate) | `t_max`, `t_min`, `layer_mean`, the heater rows' default read-out |
| the heater table and the report (A) | a 'T surface' column and a line per part, shown only when a thick layer or block is under a part | the columns of every ordinary board |
| the warning `check_thick_plates` | says the estimate and the range, not only the bound | its 5 % threshold and its trigger |
| the interface | a read-out choice 'Column' (default) / 'Surface' (the FEM design's names column / surface / point); Layer-box entries 'Surface (top)' and 'Surface (bottom)' after the layers when any exists | the project format: an optional key `solver.readout`, written only when it is not 'column' (as the laminate options are written only when not default); never an entry of `solver.models` (decision 3 below) |

## 2. The branches, in order

1. **`fix/thick-plate-surface-estimate` (option A; size M).**
   * New module `pcbthermal/thickness.py`: `through_terms(board, fill, q_in, theta, h_faces, cell, dx)` returning `(peak, mean)` offsets per outer face, turned into `T_surface` by the caller, with `offsets` as `research/through-thickness-readout/lib/surface_readout.py` (parabola; no cap: with heat in on top and out below it never exceeds the bound, README 3; the flag `thick_estimate` above `t/a = 0.5` instead). The fill weighting: for the MEAN the copper term times the fill and the laminate `face_terms` mean times 1 - fill; for the PEAK the larger of the copper term and the `face_terms` peak (which already takes the full laminate term in a partly filled cell), never their sum (README 7.1). Only layers with `t_cu` above a threshold (proposal: above 105 um, the threshold of the FEM design's copper rule; the layers of 35 to 105 um get zeros without computing) and blocks.
   * Called from `fvm.attach_face_terms` (line 919), `fdm.py` (line 496), the Analytic result builder and the Lumped (bracket `q'' t/3k` to `q'' t/2k`: no per-cell flux).
   * `analysis.heater_stats` (213) and `zone_stats` (146): read the surface arrays when `SolverOptions.readout == "surface"`; the default stays the node.
   * `checks.check_thick_plates` (1327) and `thick_plate_bound`: the text; the test strings of `tests/test_docs.py` and `tests/test_warning_texts_plain.py` follow.
   * GUI: the Simulation settings choice with its tooltip (`gui/tips.py`), the part table column, the Layer-box entry (`gui/layerchoice.py`; the FEM design needs the same entry), `pcbthermal/help/index.html`, `SHORTCUTS_HTML` unchanged; CLI `--readout`.
   * Frozen numbers: none moves (to be confirmed by `PCBT_FROZEN_CELLS=2,1,0.5`).
2. **`feature/solid3d-copper-slabs` (option C; size S).** `solid3d.py` line 270 (a loop of `n_cu` slabs with the FEM design's copper rule, `n_cu = 1` up to 105 um, else `min(ceil(t / 70 um), 8)` (DESIGN 3.2), so that both 3D models resolve the same copper; the first text had `clip(ceil(t / 0.25 mm), 1, 8)`; case 2 of README 4.1 is at 8 either way), `unknowns` (line 123), `solve_steady` (line 457; the layer temperature as the mean of the sub-slabs, the first slab for the surface array), `memory.py` row `solid3d` (the law is in the unknowns; re-measure on a 10 mm plate). Frozen: bit-identical, asserted by a test on the 20 boards. `docs/validation.md` section 55 states the 3D solid's surface on case 2.
3. **The FEM branches** (design `releases/2.8.0/fem-model/DESIGN.md`): add the case 2 test with the surface read-out within 0.1 K and the single 'Surface' Layer-box entry shared with branch 1.
4. **`feature/thick-layer-sublayers` (option B; size L), only on the maintainer's word.** A module that expands the thick, fully filled layers of a Problem into N sub-layers and collapses the result (`research/through-thickness-readout/lib/sublayers.py` is the prototype), wrapped in `api.simulate` around the FVM, FDM and Analytic; the Lumped excluded; thickness threshold and N rule from t and the source size (proposal `N = clip(ceil(t / 1.25 mm), 2, 8)`, from the case 2 table: N = 4 is +0.2 K, N = 8 is exact); the fill-aware vertical link is the precondition for patterned thick layers.

## 3. Tests to add

* `tests/test_thickness.py` (branch 1): the closed forms (`offsets` for `q_bot = -q`, 0 and the sum identity); the plate of the study (20 x 20 x 2 mm) against `tests/helpers/layered3d.py` within 8 %; case 2 within +1.5 K of the 3D surface and below the bound; Lee's three positions within 1 %; a cell with fill 0.5 (no double count: the mean takes the copper term times 0.5 plus the laminate term times 0.5, the peak the larger of the two; against the independent 3D with patterned copper); thin copper: the arrays are below 5 mK and the heater rows equal their old values bit for bit; the default `readout` leaves `t_max` unchanged; the Lumped bracket; a one-layer board; a block (the flux into the block); a board with an outline.
* `tests/test_solid3d_copper_slabs.py` (branch 2): `n_cu = 1` identical to the old solid on the 20 boards (unknown counts and temperatures); `unknowns` equals the built size for a thick plate; case 2 N = 4 / 8 against the 3D surface; the memory guard counts the slabs.
* `tests/test_gui_stress.py`: the readout choice in the scenario of every model; `tests/test_tooltips.py`, `tests/test_help.py` for the new words; the frozen-number test untouched.
* The research tests (`research/through-thickness-readout/tests`) stay as the record.

## 4. Documents to change at adoption

`docs/theory.md` 1.2 (the through-thickness read-out next to the film term: text in `docs/theory-text.md`), 4 (the 3D solid's copper slabs), 7.5 and 11 (the Muzychka case: surface read-out), `docs/models.md` (the read-out choice), `docs/validation.md` (a section with the tables 4.1, 4.2 and 4.4 of the README, `docs/validation-text.md`), the user guide and tooltips, `CHANGELOG.md`, `docs/versions.md` (the chapter 'Planned' entry in `docs/roadmap-entry.md`), the warning text of `check_thick_plates`.

## 5. Risks and decisions left to the maintainer

1. **Default read-out**: the node (like for like with the other models, no frozen number moves) or the surface (a physical truth for the part's face; moves every heater record by 0.57 to 3.79 mK on the harness and the Tj of every part). Recommended: the node as default, the surface as a choice.
2. **Tj and the margin**: keep them on the node (the user's `theta_JB` may already include the plate), show the offset beside them.
3. **Saved in the project or a machine preference**: it changes what a result says, so saving it in the project is safer (the project format is unchanged if the key is optional and written only when 'surface'). Checked by the review against the v2.7.1 tag (README 11.5): a `solver.readout` key is opened by 2.7.1 and dropped when 2.7.1 saves the project again; an unknown entry of `solver.models` is refused by 2.7.1, so the read-out must never be expressed as a model. The branch adds a compatibility test behind an environment variable, as `tests/test_format_compat_245.py` and the FEM design's `tests/test_fem_project_compat.py` do.
4. **The threshold**: 0.2 mm copper (so the 35 to 105 um boards never compute it) and blocks of any thickness; the harness block (3 mm aluminium) reads 0.03 to 0.06 K of the surface term.
5. **B is not recommended now**: its cost (N times the unknowns), the vertical-link fill problem and the Lumped exclusion; the 3D solid and the FEM already resolve a thick plate.
6. **Memory**: A adds two arrays of the size of the result; C follows the memory law (to be re-measured, branch 2).
