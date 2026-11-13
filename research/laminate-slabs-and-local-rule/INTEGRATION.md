# Integration of the laminate 2.6 proposals

**Status (audit 2.7.0).** Item C (3D solid slabs by thickness and the face term) is implemented in 2.6.0 (`feature/solid3d-slabs-by-thickness`, `solid3d.slab_rule`); item B (edge nodes) is implemented in 2.6.0 in the corrected form of `research/laminate-edge-band` (`fix/laminate-edge-band`: the band `margin_cells` wide, no film on the copper nodes); item A (the local rule) is not implemented (A18 of `research/ROADMAP.md`, `docs/versions.md` 'Planned'). 'Proposals only' below is the status when written.

Proposals only; nothing in `pcbthermal/` was edited. **Reviewed (README 7): C go as written; B go with a wider band (2.1); A not as written, three changes first (1.0).** Evidence: `README.md` (sections in brackets). The prototype that measured A and B is `lib/local_laminate.py`, written to be moved into `laminate.py`.

## 1. Item A: local laminate rule (README 3), recommended after the changes of 1.0

### 1.0 Review: changes required before the feature branch (README 7.2, 7.4)

1. **Gate on the cell**: apply the rule only to a part whose spread side is at least 4 cells; at 2 cells (a 2 mm part at 1 mm) it turns -5 / -11 % into +12 / +13 % (bare / pad). Below the gate keep the warning of `checks.check_small_part_laminate`.
2. **Conservative change of chain**: the lateral laminate conductance across a face between levels 2n and n is 0.68 of the slab's (and 0.40 between a flagged cell and one without interior nodes, also in the program's own rule). Link a coarse node to the fine nodes whose laminate it spans (overlap-weighted) so the face keeps the slab's conductance; or keep the margin x2 (equals the global rule within 0.03 points). Then re-run the tests of 1.2 and the margin sweep: the result must no longer depend on the margin.
3. **Cost on a real board**: on 40 small parts the rule costs 2.3 to 2.5 times the default (0.7 of the global rule), not 1.1 to 2.1; acceptance 4 below is for one part; add "at most 0.8 times the global (0.1, 16) on a board with many small parts".


### 1.1 Code changes

* **`laminate.py`**
  * New constants `LOCAL_TRIGGER = 0.05`, `LOCAL_TARGET = 0.05`, `LOCAL_N_MAX = 16`.
  * `GapPlan` gets `lvl` (int array (ny, nx): sub-gaps of the chain of each cell, 0 = one link) and `u` (depth fractions of the fine chain, uniform); `n` becomes the fine count n_f, `flagged = lvl > 0`.
  * `plan_gaps(board, fill, dx, active, s_max=None, n_max=None, sources=None)`: `sources` is a list of `(layer, footprint mask, spread side)`; for every gap next to the layer of a source with `d / n0 > LOCAL_TRIGGER x side` and a flagged cell under it, `n_p = n0 2^m >= d / (LOCAL_TARGET x side)` (cap `LOCAL_N_MAX`), and the level `n0 2^m'` is written on the flagged cells within `(levels - m' + 1)` x `margin_cells(d, dx)` cells of the footprint (`make_plan_gaps` in the prototype is this function). `sources=None` is the present behaviour bit for bit.
  * `build(...)`: replace by `build_local` of the prototype (per-cell chain, nested depths; a uniform level reproduces the present code, test of the prototype, 1e-9).
  * `count_unknowns`: unknowns of interior layer j = flagged cells whose stride divides j (`count_local`).
  * A helper `part_sources(problem, fill, dx, dy)` returning the sources; move the spread-side calculation of `checks._spread_side` here (checks imports it).
* **`fvm.py`** `Network._add_ladder` and `fvm.unknowns`, **`fdm.py`** (lines 190 and 383): pass `sources=laminate.part_sources(...)` to `plan_gaps`. The ladder, `drop` mask and links already carry ragged layers.
* **`api.py` / `SolverOptions`**: one bool `laminate_local` (default True), Preferences key and command-line `--no-laminate-local`; tooltip, user guide, `docs/theory.md` 1.4 (the rule) with the figure 01 of this folder.
* **`checks.py`**: `check_small_part_laminate` keeps its text but its sub-gap becomes the finest level that the local rule gives (`d / LOCAL_N_MAX` for a part meeting the trigger); the warning then fires only for parts under about d / (16 x 0.15), i.e. under 1.4 mm on a 3.2 mm board (to be recalibrated with the table of README 3.3); `memory.check` already takes the counts from `fvm.unknowns`.
* **Not changed**: one-layer boards (no gap between two copper layers), boards with a metal block (`uses_rule` False), the Lumped and Analytic models.

### 1.2 Acceptance tests (the numbers are those of README 3.3; tolerance on the program, not on the prototype)

1. `sources=None` or no small part: bit-identical to the present network (all 17 harness boards at 2, 1 and 0.5 mm).
2. Forced uniform level (a test option) equals the global option (0.1 mm, 16) to 1e-9.
3. S = 2 mm bare, t = 3.2 mm, h = 1e3, FVM 0.25 mm: R' within 3 % of 419.08 K/W (now -16.6 %; prototype -1.1 %); pad: within 3 % of 347.39 (now -19.7 %; prototype -2.1 %); S = 5 mm bare, t = 0.8, 1.6, 3.2 mm within 1 % of equation 50. **Also at 0.5 mm** (prototype +2.4 / +2.2 %, the global rule +2.1 / +1.8 %: within 3 %), and at 1 mm the S = 2 mm part must keep the default (the gate) and S = 5 mm improve (prototype -10.0 -> -5.6 %).
4. Unknowns at most 2.2 times the default on those cases (prototype 1.08 to 2.14); the memory guard estimate within the safety factor of the measured peak (0.45 GB measured on the S = 2 pad 3.2 mm case).
5. Energy balance and the maximum principle on a board with two small parts close together (regions merging).

### 1.3 Frozen records

None moves in the harness (README 3.4). **Add a harness board with a 2 mm part on a 3.2 mm two-layer board with partial copper** so that the rule is frozen; its record is new, not a shift.

### 1.4 Risks and effort

Risk: the transition between levels (checked only by the equality tests and two margin scales); the part on an inner or bottom layer (grading direction is not used, depths are uniform, so symmetric); several parts (the level is the largest). Effort: 1 to 2 days for the executor with the tests, then the reviewer; plus 1 day for the conservative transition. **Recommendation: a `feature/laminate-local` branch in 2.6.0, third after C and B, with the changes of 1.0.**

## 2. Item B: nodes at the board edge (README 4), recommended with a wider band

**Review (README 7.2, finding 6)**: the -0.6 % of margin 1 is a cancellation (margin 0 reads +4.2 %, margin 2 -2.6 %, nodes everywhere -3.5 %); use a band `laminate.margin_cells(d, dx)` cells wide (one gap thickness plus a cell): -3.8 / -4.2 % (corner, 0.5 / 1 mm), -2.6 / -3.2 % (centre), +51 / +66 % unknowns on the 60 x 40 mm board.

* **`laminate.py`** `plan_gaps(..., edge_cells=None)`: a boolean mask of the cells that touch the board edge (the cells of the rectangle border, or `geometry.edge_length_on_board(...) > 0` with an outline) grown by `margin_cells(d, dx)` cells (review; the study used 1 cell), on the board; ORed into `flagged` of every gap with n0 > 1 **when `board.h_side > 0`**; no change when `h_side` is None or 0.
* **`fvm.py` / `fdm.py`**: pass the mask (the edge lengths are already computed in `_add_ladder`).
* Acceptance (corrected by the review): 2 L 3.2 mm, 60 x 40 mm, `h_side` 200, part in the corner and at the centre: hottest rise within 5 % of the 3D solver at 0.5 and 1 mm (now -14.3 %; prototype with the band -3.8 / -4.2 %; the -0.6 % of margin 1 is not a target), and the result independent of the band width within 1 point beyond `margin_cells`; `h_side` None: bit-identical; the edge conductance of the copper nodes plus that of the interior nodes equals `h_side x slab x edge` of the node before the change (conservation test).
* **Frozen records**: every FVM and FDM record of a board with `h_side` > 0 and a gap above 0.4 mm moves (+0.000 to +0.59 K at `h_side` 10 with a 1-cell band, README 4.3; to be re-measured with the wider band): a pending file `tests/regression/data/pending/laminate-edge.json`; the largest is `part_across_outline` +0.59 K (0.26 % of its rise) at 2 mm.
* Effort 0.5 day. Do not implement the efficiency factor (README 4.2: unsafe, grid dependent).
* **Open**: the 4-layer boards keep -3.5 / -6.0 %; about 1.3 points of the first are the simple stack-up allocation of three or more layers (review: -2.2 % with an advanced stack-up of the same gaps); a shared -2 to -3 % of the layered model against the 3D solver with side films is not explained.

## 3. Item C: 3D solid slabs and the face term (README 5), recommended (review: go as written, first in order)

* **`solid3d.py`**: `n_diel` becomes a per-gap array, `n_gap = clip(ceil(d / 0.2 mm), 4, 16)` (`rule_slabs` of `scripts/study_solid_slices.py`); `unknowns` and `Solid` use the same array; `solve_steady(..., n_diel=None)` means the rule (an int keeps the old meaning for the studies). `memory.estimate`/`check` take the array (the guard law is unknowns and thickness: pass the slab count).
* **Face term** in `solve_steady` for the part's mean and peak over bare laminate (as `laminate.face_terms` does for the layered models): `q'' t_cu / (2 k_z)`; **only together with the slab rule** (alone it makes the 4-slab solid worse: +9.2 against +5.5 %).
* `checks.check_small_part_laminate`: the solid's sub-layer becomes d / n_gap; text of the 3D warning updated; `docs/validation.md` 25 row of the solid ("within 1 % of 8 slabs") corrected (already wrong for small parts).
* Acceptance (README 5.1): solid equals the independent solver (`research/paper-case-studies`, `reference_3d` at the same pixel and slabs, face term included) to 0.01 %; S >= 5 mm bare within 1 % of equation 50 at 0.25 mm; S = 2 mm bare within +4 %, pad within +8 % at 0.25 mm; 2-layer 1.6 mm board memory estimate x3 (0.19 -> 0.61 GB at 100 x 80, 1 mm), 4-layer x1.3.
* **Frozen records**: every `solid3d` record of a board with a gap (or a one-layer laminate) above 0.8 mm: on the harness the two-layer boards (-0.003 to -0.257 K) and the two one-layer boards (-0.001, -0.051 K), plus the face term of bare parts; not the 4-layer examples (simple stack-up, 0.49 mm gaps); a 4-layer advanced template (core 1.065 mm: 6 slabs) moves a little; pending file `laminate-solid.json` (corrected by the review: the first text said two- and four-layer boards).
* Effort 1 day. The 3D solid is a comparison model; the maintainer may take it in its own small branch.

## 4. Order and gates

1. Order recommended by the review: **C first** (small, comparison model, checked), **then B** with the wider band, **then A** after the changes of 1.0; A and B share `laminate.py` and the transition fix of 1.0 (2) would serve both, so B and A may be one branch if the transition fix is made first.
2. The reviewer re-runs `scripts/study_local_rule.py --round2`, `study_edge_film.py`, `study_solid_slices.py` and the new tests on the feature branch; the tester runs the whole battery and the frozen numbers at 2, 1 and 0.5 mm; the pending files are folded at the next refreeze.
3. Documents when adopted: `docs/theory.md` 1.4 and 4 (rule, edge nodes, solid slabs, with figures 01 to 03), `docs/validation.md` 21.2 and 25, `docs/versions.md`, the user guide (Preferences option), tooltips.
