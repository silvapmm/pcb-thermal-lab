# Integration of the laminate 2.6 proposals

Proposals only; nothing in `pcbthermal/` was edited. Evidence: `README.md` (sections in brackets). The prototype that measured A and B is `lib/local_laminate.py`, written to be moved into `laminate.py`.

## 1. Item A: local laminate rule (README 3), recommended

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
3. S = 2 mm bare, t = 3.2 mm, h = 1e3, FVM 0.25 mm: R' within 3 % of 419.08 K/W (now -16.6 %; prototype -1.1 %); pad: within 3 % of 347.39 (now -19.7 %; prototype -2.1 %); S = 5 mm bare, t = 0.8, 1.6, 3.2 mm within 1 % of equation 50.
4. Unknowns at most 2.2 times the default on those cases (prototype 1.08 to 2.14); the memory guard estimate within the safety factor of the measured peak (0.45 GB measured on the S = 2 pad 3.2 mm case).
5. Energy balance and the maximum principle on a board with two small parts close together (regions merging).

### 1.3 Frozen records

None moves in the harness (README 3.4). **Add a harness board with a 2 mm part on a 3.2 mm two-layer board with partial copper** so that the rule is frozen; its record is new, not a shift.

### 1.4 Risks and effort

Risk: the transition between levels (checked only by the equality tests and two margin scales); the part on an inner or bottom layer (grading direction is not used, depths are uniform, so symmetric); several parts (the level is the largest). Effort: 1 to 2 days for the executor with the tests, then the reviewer. **Recommendation: a `feature/laminate-local` branch in 2.6.0.**

## 2. Item B: nodes at the board edge (README 4), recommended with A

* **`laminate.py`** `plan_gaps(..., edge_cells=None)`: a boolean mask of the cells that touch the board edge (the cells of the rectangle border, or `geometry.edge_length_on_board(...) > 0` with an outline) grown by 1 cell, on the board; ORed into `flagged` of every gap with n0 > 1 **when `board.h_side > 0`**; no change when `h_side` is None or 0.
* **`fvm.py` / `fdm.py`**: pass the mask (the edge lengths are already computed in `_add_ladder`).
* Acceptance: 2 L 3.2 mm, 60 x 40 mm, `h_side` 200, part in the corner: hottest rise within 3.5 % of the 3D solver (now -14.3 %; prototype -0.6 %, and -3.5 % with nodes everywhere), also edge and centre positions; `h_side` None: bit-identical; the edge conductance of the copper nodes plus that of the interior nodes equals `h_side x slab x edge` of the node before the change (conservation test).
* **Frozen records**: every FVM and FDM record of a board with `h_side` > 0 and a gap above 0.4 mm moves (+0.000 to +0.59 K at `h_side` 10, README 4.3): a pending file `tests/regression/data/pending/laminate-edge.json`; the largest is `part_across_outline` +0.59 K (0.26 % of its rise) at 2 mm.
* Effort 0.5 day. Do not implement the efficiency factor (README 4.2: unsafe, grid dependent).
* **Open**: the 4-layer boards keep -3.5 / -6.0 %; investigate the simple stack-up allocation of three or more layers (`laminate.py` docstring) separately.

## 3. Item C: 3D solid slabs and the face term (README 5), recommended

* **`solid3d.py`**: `n_diel` becomes a per-gap array, `n_gap = clip(ceil(d / 0.2 mm), 4, 16)` (`rule_slabs` of `scripts/study_solid_slices.py`); `unknowns` and `Solid` use the same array; `solve_steady(..., n_diel=None)` means the rule (an int keeps the old meaning for the studies). `memory.estimate`/`check` take the array (the guard law is unknowns and thickness: pass the slab count).
* **Face term** in `solve_steady` for the part's mean and peak over bare laminate (as `laminate.face_terms` does for the layered models): `q'' t_cu / (2 k_z)`; **only together with the slab rule** (alone it makes the 4-slab solid worse: +9.2 against +5.5 %).
* `checks.check_small_part_laminate`: the solid's sub-layer becomes d / n_gap; text of the 3D warning updated; `docs/validation.md` 25 row of the solid ("within 1 % of 8 slabs") corrected (already wrong for small parts).
* Acceptance (README 5.1): solid equals the independent solver (`research/paper-case-studies`, `reference_3d` at the same pixel and slabs, face term included) to 0.01 %; S >= 5 mm bare within 1 % of equation 50 at 0.25 mm; S = 2 mm bare within +4 %, pad within +8 % at 0.25 mm; 2-layer 1.6 mm board memory estimate x3 (0.19 -> 0.61 GB at 100 x 80, 1 mm), 4-layer x1.3.
* **Frozen records**: every `solid3d` record of a two-layer or four-layer board (2-layer: -0.001 to -0.26 K plus the face term of bare parts; 4-layer templates (core 1.065 mm: 6 slabs): small); pending file `laminate-solid.json`.
* Effort 1 day. The 3D solid is a comparison model; the maintainer may take it in its own small branch.

## 4. Order and gates

1. A and B in one branch (one `laminate.py`, one pending file or two); C separately.
2. The reviewer re-runs `scripts/study_local_rule.py --round2`, `study_edge_film.py`, `study_solid_slices.py` and the new tests on the feature branch; the tester runs the whole battery and the frozen numbers at 2, 1 and 0.5 mm; the pending files are folded at the next refreeze.
3. Documents when adopted: `docs/theory.md` 1.4 and 4 (rule, edge nodes, solid slabs, with figures 01 to 03), `docs/validation.md` 21.2 and 25, `docs/versions.md`, the user guide (Preferences option), tooltips.
