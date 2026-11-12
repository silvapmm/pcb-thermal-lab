# Laminate 2.6: a local rule for small parts, the edge film, and the slabs of the 3D solid

Status: reviewed (section 7). **Go for C (3D solid slabs and face term) as written; A (local rule) and B (edge nodes) are sound in direction but not as written: both need the corrections of 7.4 before a feature branch.** The program is not touched; every change below is a proposal measured on a copy (`lib/local_laminate.py` replaces three functions of `pcbthermal.laminate` for the duration of a run and edits nothing).

**Status (audit 2.6.1).** C is implemented in 2.6.0 (`feature/solid3d-slabs-by-thickness`), B in 2.6.0 in the corrected form of `research/laminate-edge-band` (`fix/laminate-edge-band`), A is open (A18 of `research/ROADMAP.md`). The folder was named `research/laminate-2-6/` before the 2.6.1 rename. Known defect of a study, not corrected by this audit: `scripts/study_solid_slices.py` counts the face term of the 3D solid twice on the 2.6.0 program (the program adds the face term itself since C was adopted).

## 1. The questions

Three linked limits of the layered models, found in 2.5.0 (`docs/versions.md` 'Planned', `docs/theory.md` 1.4 and 4, `research/paper-case-studies` 11 to 16, `research/analytic-edge-spatial` 8.4):

* **A. Small part over a thick laminate.** The laminate rule (sub-gaps of at most 0.4 mm, at most 4) is the same everywhere, so a part whose side is small against the sub-gap reads too cool (-4 to -9 % bare, -6 to -14 % over a pad at sub-gap / side 0.15 to 0.2; -12 to -24 % at 0.3 to 0.4). A global fine rule costs 3 times the unknowns. Question: a rule that is fine only under and around small parts.
* **B. Edge film.** The FVM and FDM put the edge film of a whole slab on the copper node, so with a large `h_side` on a thick board they read 13 to 17 % low against the independent 3D solver. Question: nodes for the laminate at the edge, or an edge conductance with an efficiency.
* **C. 3D solid.** It cuts each insulating gap into 4 slabs (reads +20 % bare / +27 % pad hot at 3.2 mm under a 2 mm part) and adds no face term. Question: slabs by thickness and the face term.

### 1.1 Diagrams

![sub-layers under a small part](figures/fig_01_small_part_sublayers.png)

*Figure 01 (`fig_01_small_part_sublayers.png`). Left: the default rule, 4 sub-gaps everywhere the copper is absent. Right: the local rule, 16 under the part, 8 around it, 4 elsewhere; the depths of the coarse cells are a subset of the fine ones.*

![edge film](figures/fig_02_edge_film.png)

*Figure 02 (`fig_02_edge_film.png`). Left: the film on the whole slab acts at the copper node temperature. Right: laminate nodes in the cells at the edge, so the laminate loses heat at its own, lower, temperature.*

![solid slabs](figures/fig_03_solid_slabs.png)

*Figure 03 (`fig_03_solid_slabs.png`). The slabs of the 3D solid across a gap, as built and as proposed, with the face term.*

## 2. References and method

* Bare laminate: equation 50 of Muzychka, Yovanovich and Culham (2004) through `paper-case-studies/lib/flux_channel.py`; for S = 2 mm, h = 1e3 also the extrapolated 3D numbers recorded there (README 16.4: bare 389.12 / 419.08, pad 316.37 / 347.39 K/W at 1.6 / 3.2 mm). The 389.12 was re-run here (389.117, 19 s, 3.2 GB: too heavy for the present machine, so the other extrapolations were **not** re-run).
* **Under a pad only S = 2 mm has an independent reference.** For S = 5 and 10 mm pad boards the tables compare with the global (0.1, 16) run of the program itself, which is a self-consistency check, not a reference (it overshoots the extrapolated reference by +1.7 % at S = 2, t = 1.6 mm).
* Edge: the independent 3D solver with the side film on every slab (`analytic-edge-spatial/lib/layered3d_side.py`, 1 mm cells, 4 and 8 sub-slabs: they differ by 0.02 to 0.9 %; the errors below are against 8).
* Machine: light runs only (peak under 2 GB, cells 0.25 mm only on 20 mm boards at S = 2 and 5 mm, a battery was running on the main checkout, load 5 to 8).

## 3. Item A: the local laminate rule

### 3.1 Design (prototype in `lib/local_laminate.py`)

* A **fine chain** of n_f sub-gaps per gap, nested: a cell at level n_c uses every (n_f / n_c)-th node, so the same layer index means the same depth in every cell and the lateral links between neighbouring cells join equal depths. The node of a cell holds the laminate half way to its two neighbours **in its own chain** (conserves the laminate cell by cell).
* **Where**: default level n0 in the cells the default rule flags; around a part whose *spread side* S_eff (the checks' `_spread_side`: the part, or the part grown by the copper around it on its layer) satisfies d / n0 > `TRIGGER` x S_eff the level rises to n_p = n0 x 2^m >= d / (`TARGET` x S_eff), at most 16, in the footprint grown by a margin of `ceil(d/dx) + 1` cells (the default margin), halving every further margin. Only cells the default rule already flags are refined.
* Uniform spacing; grading (ratio 1.3, fine at the face of the part) was tried and is **worse** (3.1).
* The drop mask of the ladder already leaves unused interior nodes out of the direct solve, so the cost is only the nodes that exist.

### 3.2 Tests (`tests/test_local_laminate.py`, 4 passed; 7 after the review, 7.2)

* A trigger that never fires gives the program's number bit for bit, bare and pad.
* A fine region that covers every flagged cell with a chain of 16 gives the global option (0.1 mm, 16) of the program to 1e-9: this checks the generalised `build` against `laminate.build`.
* The unknowns order default < local < global; the edge nodes raise a thick board with a large `h_side`.
* Added by the review: the edge margin 0 is the ring alone; the lateral laminate conductance at a change of chain (0.68) and at the boundary of the flagged cells (0.40).

### 3.3 Result (`scripts/study_local_rule.py`, FVM 0.25 mm, h = 1e3; error of R' in %, unknowns as a multiple of the default)

Candidate **L6**: trigger 0.05, target 0.05, cap 16, uniform, margin 1 (round 2: the first-round L1, trigger 0.10, differs only on S = 5 mm).

| S, t (mm) | board | default | G(0.2,8) | G(0.1,16) | L6 | L6 unknowns x | G(0.1,16) unknowns x |
| :-- | :-- | --: | --: | --: | --: | --: | --: |
| 2, 0.8 | bare | -6.8 | -1.8 | +0.2 | +1.1 | 1.10 | 3.00 |
| 2, 1.6 | bare | -6.5 | -1.5 | +0.5 | +1.0 | 1.28 | 3.40 |
| 2, 3.2 | bare | -16.6 | -6.3 | -1.5 | -1.1 | 1.68 | 3.40 |
| 5, 0.8 | bare | -3.2 | -1.5 | -0.8 | -0.9 | 1.08 | 3.00 |
| 5, 1.6 | bare | -2.5 | -0.9 | -0.3 | -0.5 | 1.15 | 3.40 |
| 5, 3.2 | bare | -6.0 | -2.1 | -0.6 | -0.3 | 2.14 | 3.40 |
| 2, 1.6 | pad | -9.0 | -2.1 | +1.7 | +2.3 | 1.28 | 3.40 |
| 2, 3.2 | pad | -19.7 | -9.0 | -2.5 | -2.1 | 1.68 | 3.40 |
| 5, 0.8 | pad (vs G16) | -6.0 | -2.1 | 0 | -1.1 | 1.08 | 3.00 |
| 5, 3.2 | pad (vs G16) | -9.3 | -3.3 | 0 | +0.4 | 2.14 | 3.40 |

Bare references: equation 50 (S = 5 and S = 2 at 0.8 mm) and the extrapolated 3D (S = 2 at 1.6, 3.2). Pad S = 2: extrapolated 3D; pad S = 5: vs G(0.1,16). The full tables are `out/study_local_rule.json` (first round, 8 rules, 8 cases) and `out/local_rule2.txt` with `out/study_local_rule2.json` (second round; there is no `out/local_rule.txt`, as the first version of this README said). **All of 3.3 is at the 0.25 mm cell; at 0.5 and 1 mm see the review, 7.2 (at 1 mm the local rule makes a 2 mm part 12 to 15 % too hot).**

![error against cost](figures/fig_04_local_rule_cost_error.png)

*Figure 04 (`fig_04_local_rule_cost_error.png`). Error of R' against the unknowns relative to the default, S = 2 and 5 mm on 20 mm, all thicknesses; green band +-3 %.*

* **L6 reaches +-3 % on every row with a reference (-2.1 to +2.3 %) at 1.08 to 2.14 times the unknowns; the global (0.1, 16) needs 3.0 to 3.4 times for -2.5 to +1.7 %.** The default is -16.6 / -19.7 % on the worst row.
* **Cost measured in fresh processes** (`scripts/study_cost_one.py`, 0.25 mm, S = 2 mm pad, t = 3.2 mm): default 0.26 s, 0.18 GB; global (0.1, 16) 5.5 s, 1.51 GB; **L6 1.07 s, 0.45 GB** (same error, -2.5 against -2.1 %). S = 5 mm bare, t = 3.2 mm: default 0.21 s / 0.17 GB, L6 1.86 s / 0.72 GB (R' 138.47 against 146.95; eq. 50 gives 147.37). The wall times of the sweeps vary with the load of the machine (a battery was running); the unknowns and the single-process figures are the trustworthy ones.
* **Margin**: x 0.5 is cheaper (1.05 to 1.53) but overshoots (+3.1 to +3.9 % at S = 2 mm, 0.8 and 1.6 mm); x 2 changes the error by 0.2 to 1 point and costs 1.2 to 1.8 times more. The default margin (one gap thickness plus a cell) stays.
* **Cap and target**: cap 32 or target 0.03 add 1.5 to 3 times the unknowns and *overshoot* the reference (+1.6 to +5 %), because at the 0.25 mm cell the layered model has its own positive pixel bias once the sub-gaps are fine; finer is not better. **Grading** (1.3) adds +0.5 to +3 points of overshoot for no saving.
* **Where it does nothing**: S = 10 mm parts on 40 mm boards (trigger not met: -1.5 % bare 1.6 mm, -2.7 % bare 3.2 mm stay; the pad rows at 5 to 10 mm are within the trigger band) and every part over a plane (the spread side is infinite).

### 3.4 Impact on the frozen boards (`scripts/study_harness_impact.py`, FVM at 2 and 1 mm)

The trigger fires on **none of the 14 supported harness boards** (the parts are 8 mm and larger; the two one-layer boards and the finned block are not supported by the prototype, and a one-layer board has no gap with two copper layers). **No frozen record moves for A.** It moves only boards with a small part over a thick laminate, which the harness has none of (add one: see INTEGRATION 1.4).

### 3.5 Limits

* The sub-gap at the cap is d / 16: 0.2 mm for a 3.2 mm board, so a part under about 4 mm on 3.2 mm boards is not fully resolved (S = 2 mm: -1.1 / -2.1 %, inside the pad band; smaller parts not tested).
* S_eff for a part on a pad of another shape and several parts close together (the regions merge; the level is the largest) were not tested.
* The test boards have the part on layer 1 over a bare second layer; parts on inner or bottom layers (the gap above the part, the grading direction) are covered by the code but not run.
* FDM: the same seam (`laminate.plan_gaps/build` is shared) but not run with the local rule.
* One-layer boards and boards with a metal block are outside the prototype.
* The residual overshoot at S = 2 mm (+1.0 to +2.3 %) is the 0.25 mm pixel (S/8): the independent 3D solver at the same pixel is +3.9 % high (paper-case-studies 16.4).

## 4. Item B: the edge film

### 4.1 Reproduction of the review's probe (`scripts/study_edge_film.py`)

Uniform full-copper boards, a 10 mm, 2 W part, faces 10 W/m2K, FVM 0.5 mm, error of the hottest rise against the 3D solver with the side film (8 sub-slabs, 1 mm cells), %:

| board | h_side | default | fill 0.9999 (nodes everywhere) | **edge nodes, margin 1** | edge nodes, margin 2 | efficiency eta |
| :-- | --: | --: | --: | --: | --: | --: |
| 2 L 1.6 mm, corner | 10 | -0.3 | -0.0 | -0.2 | -0.1 | -0.2 |
| 2 L 3.2 mm, corner | 10 | -1.3 | -0.1 | -0.7 | -0.7 | -0.7 |
| 2 L 1.6 mm, corner | 200 | -6.1 | -2.3 | -1.9 | -2.3 | +3.5 |
| 2 L 3.2 mm, corner | 50 | -4.3 | -0.8 | -0.9 | -1.2 | +2.6 |
| 2 L 3.2 mm, corner | 200 | **-14.3** | -3.5 | **-0.6** | -2.6 | +13.2 |
| 2 L 3.2 mm, edge | 200 | -9.1 | -2.3 | -0.1 | -1.6 | +11.4 |
| 2 L 3.2 mm, centre | 200 | -5.7 | -1.5 | +0.3 | -1.1 | +10.7 |
| 4 L 1.6 mm, corner | 200 | -4.0 | -3.5 | -3.5 | -3.5 | -2.4 |
| 4 L 3.2 mm, corner | 200 | -8.0 | -6.0 | -6.0 | -6.1 | -1.1 |
| 2 L 0.8 mm, corner | 200 | -2.7 | -2.0 | -2.0 | -2.0 | -0.7 |

(`out/edge_film.txt`, 13 boards. The review's -15.1 to -4.4 % on the 3.2 mm, 200 W/m2K board is reproduced at 0.5 mm in this form: -14.3 to -3.5 %.)

![edge variants](figures/fig_05_edge_variants.png)

*Figure 05 (`fig_05_edge_variants.png`). Error of the hottest rise against the 3D solver for the program, nodes everywhere, nodes at the edge (margin 1) and the efficiency model.*

### 4.2 Findings

* *Corrected by the review (7.2): the -0.6 % of margin 1 is a cancellation, not a converged number; the band that reproduces nodes everywhere gives -3.8 % (0.5 mm) and -4.2 % (1 mm) on this board; and "margin 0" below was nodes everywhere because of a defect of the prototype (fixed). The original text follows.*
* **Nodes in the cells at the board edge (and 1 cell beyond) bring the worst board from -14.3 to -0.6 %**, the edge and centre cases from -9.1 and -5.7 to -0.1 and +0.3 %, and cost **0 to +52 % of the unknowns** on the harness boards at 2 mm (+5 to +37 % on the rectangular ones, +17 to +52 % on the outline boards; +29 % on the 60 x 40 mm test board at 0.5 mm; the share falls as the cell shrinks: 1 mm +0 to +28 %), against 4.5 times for nodes everywhere. The nodes on the ring alone (margin 0) give exactly the nodes-everywhere number (**wrong**: `scipy.ndimage.binary_dilation(..., iterations=0)` floods the mask, so that column was nodes everywhere; the ring alone reads +4.2 % at 0.5 mm, review 7.2); margin 1 is better than both (-0.6 against -3.5 %) and margin 2 worse again (-2.6): the discretisation of the transition between a cell with interior nodes and one without gives a scatter of about +-2 points around the converged value, so **the claim is "within 3.5 %", not "to 0.6 %"**. A finer laminate (0.2 mm, 8, `out/edge_film_fine.txt`) gives the same picture (margin 1: +0.6 to +0.9 % on the 3.2 mm, 200 W/m2K boards).
* **The efficiency model is rejected.** `eta = tanh(mL)/(mL)` with L = d/2 and a penetration width delta = dx/2 depends on the cell and reads +10 to +13 % hot (the unsafe-low side is traded for a hot one) on the boards that matter; a width independent of the grid would need a 2-D corner solution. Nodes are the converging construction.
* **Not explained by the edge**: the 4-layer boards stay at -3.5 / -6.0 % with every variant, and the 0.8 mm and 30 x 20 mm boards at -2 to -3.6 %. Those are not the laminate film at the edge (nodes everywhere do not change them); the candidates are the simple stack-up slab allocation for three or more layers (a recorded separate item of `laminate.py`) and the sub-gap count; **not investigated here**.
* **Outlines**: the cells to flag are those the outline crosses (`geometry.edge_length_on_board > 0`), not the raster border. With them: round outline +0.016 / +0.023 K, T outline +0.109 / +0.055 K, part across the outline +0.59 / +0.42 K at 2 / 1 mm (h_side 10).

### 4.3 Impact on the frozen boards

At `h_side` 10 the shifts are small (example board < 0.001 K, `reference_board` +0.001, `plate_vias` +0.006 K, `t_outline` +0.109 K, `part_across_outline` +0.59 K at 2 mm), but the frozen tolerance is 1e-8 K: **every FVM and FDM record of a board with an edge coefficient and a gap above 0.4 mm moves** (pending file). Boards with `h_side` None (`plate_uniform`, `plate_pad`) do not.

## 5. Item C: the slabs of the 3D solid

### 5.1 Result (`scripts/study_solid_slices.py`, 0.25 mm, 20 mm board, h = 1e3)

* **The solid equals the independent solver at the same pixel and slabs to 0.00 %** on all 24 rows (`R` against `ref3d` at pixel S/8: -0.00 to +0.00 %), once the half layer of laminate between the node and the face is added on bare laminate (`(t_cu/2) / (k_z S^2)` = 14.58 K/W at S = 2 mm). So the slab count and the missing face term are the whole story, as the review found.
* Error against the reference (equation 50, or the extrapolated 3D), with the face term, %:

| case | 4 slabs | 8 | 16 |
| :-- | --: | --: | --: |
| S 2, 1.6 mm, bare | +9.2 | +4.1 | +2.6 |
| S 2, 3.2 mm, bare | +23.4 | +8.9 | +3.9 |
| S 2, 1.6 mm, pad | +14.7 | +9.0 | +6.9 |
| S 2, 3.2 mm, pad | +27.3 | +13.3 | +7.9 |
| S 5, 1.6 mm, bare | +2.5 | +1.1 | +0.6 |
| S 5, 3.2 mm, bare | +6.9 | +2.3 | +0.9 |

(`out/solid_slices.txt`; S = 5 mm pad rows have no reference.) Without the face term the S = 2 mm bare rows read +5.5 / +20.0 % at 4 slabs (the earlier review): the face term moves them by +3.7 / +3.4 points, so **adding it without more slabs makes the solid worse**; it is only right together with the slab rule. The +0.4 % of the earlier 16-slab bare number was two errors cancelling (3.5 % each).

![solid slabs](figures/fig_06_solid_slabs_error.png)

*Figure 06 (`fig_06_solid_slabs_error.png`). Error of the 3D solid against the reference against the slabs per gap.*

* **What remains at 16 slabs is the 0.25 mm pixel** (S/8): the independent solver at that pixel with 16 sub-slabs is +3.9 % above the extrapolated reference on the bare 3.2 mm board (paper-case-studies 16.4), and the pad rows add the residual of the slab error (about 1.7 % at 16 by Richardson from 8 and 16). So the **acceptance cannot be "within 3 % of the extrapolated reference at 0.25 mm for S = 2 mm"**; it is: (i) equal to the independent solver at the same pixel and slabs to 0.01 %; (ii) S >= 5 mm within 1 % of equation 50 at 16 slabs; (iii) S = 2 mm bare within +4 % and pad within +8 % (hot side) at 0.25 mm.

### 5.2 Cost of the rule n = clip(ceil(d / 0.2 mm), 4, 16) (`out/solid_slices_part2.txt`, `out/solid_harness.txt`)

* The shipped templates have gaps of 76 to 520 um except the core: **only the 2-layer board (1.53 mm gap: 8 slabs, 6 -> 10 node slabs, x1.67) and the 4-layer core (1.065 mm: 6 slabs, 16 -> 18, x1.12) change**; 6 to 10 layers keep 4 everywhere (x1.00). The memory guard law of the solid gives 0.19 -> 0.61 GB (2 layers, 100 x 80 mm, 1 mm cell) and 1.78 -> 2.33 GB (4 layers), 1 oz and 0.5 oz alike.
* On the 17 harness boards at 2 mm the rule moves the solid's hottest temperature by -0.001 to -0.26 K (the pad boards -0.26 and -0.22 K; the 3 four-layer examples 0.000), at 1.4 to 1.8 times the unknowns; the face term is not included in these numbers (it lowers nothing: it adds, only on bare laminate under a part). **Every solid record of a board with a gap above 0.8 mm moves** (pending file): on the harness these are the two-layer boards and the two one-layer boards (laminate 1.56 mm: 8 slabs, x1.80), not the 4-layer examples (simple stack-up, gaps of 0.49 mm).
* A thick uniform 3.2 mm board with 16 slabs: 5 to 8 s and 1.6 GB at 0.25 mm on the 20 mm test board (115 200 unknowns).

## 6. Summary and recommendation

| item | finding | cost | frozen records | effort | recommendation |
| :-- | :-- | :-- | :-- | :-- | :-- |
| A local laminate rule | -16.6 / -19.7 % -> -1.1 / -2.1 % (S = 2, 3.2 mm); within +-3 % on all rows with a reference | 1.08 to 2.14 x unknowns, one fifth the time and 0.3 x the memory of the global (0.1, 16) on the worst row | none moves (no small part in the harness) | `laminate.py` about 150 lines (the prototype is that code), `fvm._add_ladder`, `fdm`, `fvm.unknowns`, `checks`; 1 to 2 days with the tests | **feature branch for 2.6.0 only with the review's changes (7.4)**: apply the rule only to a part at least 4 cells wide, make the change of chain conservative (or use the margin x2), re-measure at 0.5 and 1 mm and on a board with many parts; add a small-part board to the harness |
| B edge nodes | -14.3 -> -3.8 / -4.2 % at 0.5 / 1 mm (3.2 mm, 200 W/m2K) with a band one gap thickness plus a cell wide (review 7.2; the -0.6 % of margin 1 was a cancellation) | +51 % (0.5 mm) / +66 % (1 mm) unknowns on the 60 x 40 mm board with that band (nodes everywhere +150 %) | every FVM/FDM record of a board with `h_side` and a gap > 0.4 mm (pending file) | `flag_cells` + edge mask in `plan_gaps`, 30 lines; 0.5 day | **include in the same branch, with the band `margin_cells(d, dx)` wide (not 1 cell)**; do not model an efficiency |
| C solid slabs and face term | solid = independent solver at the same pixel; error 23 -> 4 % (bare 3.2 mm, S = 2) | x1.67 slabs on 2-layer boards, x1.12 on 4-layer, x1.00 above | every solid record of a 2- or 4-layer board (pending file) | `solid3d.py` per-gap slab counts, `unknowns`, `memory` law input, face term in `solve_steady`; 1 day | **go: separate small branch; the face term only with the slab rule** |

## 7. Review

The reviewer re-ran every study of the folder on develop `c3acf0c` (after `git merge develop`; develop `0507e5c` merged again at the end, the cost and edge rows re-checked identical; the program untouched: `git diff develop -- pcbthermal tests examples ico` empty) and added `scripts/study_review_checks.py` (light, 66 s, at most about 1.5 GB) for the checks below.

### 7.1 What was re-run and reproduced

* `study_edge_film.py`: the 13 rows of 4.1 to the digit (default, fill 0.9999, margin 1 and 2, eta; the margin 0 column changes with the fix of the prototype, see 7.2). The 3D solver at 1 mm against 0.5 mm on the corner board: 74.069 against 73.766 K (+0.41 %), so the reference's own pixel error is small against the effects discussed.
* `study_cost_one.py`: R' 278.863 / 338.691 / 340.067 (default, global (0.1, 16), L6; S = 2 mm pad, 3.2 mm) and 146.954 (L6, S = 5 mm bare), unknowns and peak memory (0.17, 1.51, 0.45, 0.72 GB) identical; times 0.23 / 6.2 / 2.1 / 2.3 s under a load of 5 to 6.
* `study_solid_slices.py` (both parts) and `study_solid_harness.py`: every number of 5.1 and 5.2 to the digit; the solid and the independent solver agree to 0.00 %.
* `study_harness_impact.py`: the rows of 4.3 and 4.2 (outline boards: +0.016 / +0.023, +0.109 / +0.055, +0.588 / +0.419 K). `out/harness_impact.txt` of the first run held the outline rows before the outline edge cells were used (+0.346 K for the part across the outline); the README quoted the newer `out/harness_impact_outline.txt`, which is right.
* `study_local_rule.py --round2` was **not** re-run in full (about 40 runs at 0.25 mm, up to 1.5 GB each, on a machine shared with two other heavy jobs); its worst rows are reproduced by `study_cost_one.py` above and by the 0.5 and 1 mm runs below, which use the same code path.
* `tests/`: 4 passed before the review, 7 after (three tests added, below).

### 7.2 Findings

![lateral links at a change of chain](figures/fig_07_level_transition.png)

*Figure 07 (`fig_07_level_transition.png`). Left: a cell with 8 sub-gaps next to one with 4 (the local rule); every second node of the fine cell has no lateral neighbour. Right: a flagged cell next to one without interior nodes (the edge band and the program's own rule).*

![review checks](figures/fig_08_review_cells_and_band.png)

*Figure 08 (`fig_08_review_cells_and_band.png`). (a) Error of R' against the cell for the default, the global (0.1, 16) and the local rule L6, S = 2 mm on 3.2 mm (0.25 mm from `study_local_rule2.json`, 0.5 and 1 mm from the review). (b) The edge nodes against the width of the band (cells beyond the border cell) at 0.5 and 1 mm; thin lines: nodes everywhere.*

1. **Defect in the study (fixed): "margin 0" was nodes everywhere.** `lib/local_laminate.py` called `ndimage.binary_dilation(ring, iterations=edge_margin)`; with `iterations=0` scipy repeats the dilation until nothing changes, which flags every cell. The claim of 4.2 that "the ring alone gives exactly the nodes-everywhere number" was this defect. With the ring alone the corner board reads **+4.2 % at 0.5 mm and -0.9 % at 1 mm** (`out/edge_film.txt` re-run: the margin 0 column now +4.2 / +3.8 / +3.6 % on the three 3.2 mm, 200 W/m2K rows). Regression test `test_edge_margin_zero_is_the_ring_only`.
2. **The lateral laminate conductance is lost at every change of chain** (measured on the network, tests `test_level_transition_keeps_two_thirds_of_the_lateral_laminate` and `test_edge_band_boundary_keeps_two_fifths_of_the_lateral_laminate`). Across the face between a cell of level 2n and one of level n the conductances are the harmonic means of nodes of thickness s and 2s, and the odd depths of the fine cell have no neighbour: **0.68** of the slab's lateral conductance (each of the two transitions of L6 on the S = 2 mm board). Across the face between a flagged cell (4 sub-gaps) and a cell without interior nodes the copper nodes hold d/8 against d/2: **0.40**. The second face is also the boundary of the flagged region of the program's own rule (`laminate.build`), not only of the proposals: a limit of the program, not measured on the program's cases here (the copper usually dominates the lateral flow there).
3. **Consequence for A: part of the agreement of L6 is this artefact.** L6 reads 0.3 to 1.3 points above the global (0.1, 16) on every S = 2 mm row (0.25 mm: +0.9 / +1.3 points at 0.8 mm, +0.3 / +0.4 at 3.2 mm; 0.5 mm: +0.3 to +0.4), and the margin x0.5, with transitions nearer the part, reads another 1 to 3 points higher; with the margin x2 L6 equals the global rule within 0.03 points (0.5 and 1 mm). The direction is hot (safe); the size is below the residual pixel bias. "L6 reaches +-3 %" stands at 0.25 mm, but it rests on a fine region whose boundaries are 2/3 transparent.
4. **A at the cells a user runs** (`study_review_checks.py cells`; error of R' against the reference, %):

| case | cell | default | G(0.1,16) | L6 | L6 x2 | unknowns default / L6 / G |
| :-- | --: | --: | --: | --: | --: | :-- |
| S 2, 3.2 mm, bare | 0.5 | -13.98 | +2.06 | +2.38 | +2.08 | 8000 / 14480 / 27200 |
| S 2, 3.2 mm, bare | 1.0 | -5.09 | +12.03 | +12.32 | +12.03 | 2000 / 4240 / 6800 |
| S 2, 3.2 mm, pad | 0.5 | -17.66 | +1.82 | +2.21 | +1.84 | 8000 / 14480 / 27200 |
| S 2, 3.2 mm, pad | 1.0 | -11.41 | +12.94 | +13.30 | +12.94 | 2000 / 4240 / 6800 |
| S 2, 1.6 mm, bare | 0.5 | -2.98 | +4.28 | +4.71 | +4.31 | 8000 / 11056 / 27200 |
| S 2, 1.6 mm, bare | 1.0 | +7.64 | +14.71 | +15.27 | +14.74 | 2000 / 2912 / 6800 |
| S 5, 3.2 mm, bare | 0.5 | -5.30 | +0.32 | +0.61 | +0.32 | 8000 / 18400 / 27200 |
| S 5, 3.2 mm, bare | 1.0 | -10.03 | -5.73 | -5.57 | -5.73 | 2000 / 5328 / 6800 |

   At 0.5 mm (a 2 mm part is 4 cells) the rule turns -14 / -18 % into +2.4 / +2.2 %. **At 1 mm (2 cells) it turns -5 / -11 % into +12 / +13 % (and +7.6 into +15.3 % on 1.6 mm)**: the coarse pixel of a part two cells wide reads hot, and the default's coarse laminate was cancelling it. A 5 mm part at 1 mm (5 cells) improves (-10.0 to -5.6 %). So the rule helps only when the part is resolved in the plane; the claim of 8 that the proposal is the default at coarse cells was wrong.
5. **A on a board with many small parts** (`... many`: 60 x 40 mm, 1.6 mm, 40 parts of 1 to 3 mm on pads, a plane under 60 % of the second layer): the rule fires on most parts. Unknowns 12 000 / 29 784 / 40 800 at 1 mm and 48 000 / 110 736 / 163 200 at 0.5 mm (default / L6 / global (0.1, 16)): **2.3 to 2.5 times the default** (README 3.3 quotes 1.08 to 2.14 for one part on a board), 0.73 / 0.68 of the global; time 0.8 / 1.0 s and 3.8 / 14.0 s under load. The hottest part rises by 2.2 K (1 mm) and 1.8 K (0.5 mm) over the default, L6 0.3 K above the global (finding 3).
6. **B: margin 1 is a cancellation; the converged construction is 3 to 4 % low.** Corner board, 3.2 mm, h_side 200, against the 3D solver at 1 mm (`... edge`):

| variant | 0.5 mm | 1 mm | unknowns at 0.5 mm |
| :-- | --: | --: | --: |
| program (default) | -14.26 | -14.33 | 19 200 |
| ring alone (margin 0) | +4.17 | -0.88 | 20 388 |
| margin 1 (the proposal) | -0.63 | -3.88 | 21 552 |
| margin 2 | -2.55 | -4.36 | 22 692 |
| band one gap thickness plus a cell (8 / 5 cells) | -3.79 | -4.16 | 29 028 |
| nodes everywhere | -3.46 | -3.97 | 48 000 |
| nodes everywhere, laminate (0.1, 16) | -2.11 | -2.83 | |

   (Centre position: -5.71 -> +0.30 at margin 1, -2.62 with the band, -1.54 everywhere, -1.05 with (0.1, 16).) The ring alone is hot, a wide band tends towards nodes everywhere and sits 0.2 to 1.1 points below it: the edge band's inner boundary (finding 2, 0.40) sets the number for a narrow band, and margin 1 at 0.5 mm happens to sit near zero. The robust result is **-14.3 -> about -4 % (default laminate), -2 to -3 % with a fine laminate**, with the band one gap thickness plus a cell wide (the margin the program already uses, `laminate.margin_cells`) at +51 % / +66 % unknowns on this board, not +12 %.
7. **The 4-layer residual of 4.2 is partly the simple stack-up** (`... stack`): with nodes everywhere the 4-layer 1.6 mm board reads -3.49 % with the simple stack-up (outer slabs of 0.400 mm, i.e. 0.365 mm of laminate on the outer copper nodes) and -2.18 % with an advanced stack-up of the same three gaps (outer slabs 0.278 mm). About 1.3 points are the slab allocation item of `laminate.py`; the remaining -2 to -3 % that every variant shares (also the 0.8 mm boards: -1.7 % and -3.2 % with nodes everywhere and (0.1, 16)) is the layered model against the 3D solver with side films, not the edge nodes, and is **not explained** here (the 3D solver's own pixel and sub-slab errors are 0.4 and 0.9 %).
8. **C holds.** The slab rule and the face term are reproduced to the digit, the solid equals the independent solver at the same pixel and slabs to 0.00 % (an equality of two codes of the same discretisation, not a convergence proof), and the convergence in slabs is checked against equation 50 (independent) at S = 5 mm: +0.6 / +0.9 % at 16 slabs. Correction to INTEGRATION 3: the one-layer harness boards also move (8 slabs), the 4-layer examples do not.
9. **Smaller corrections**: `out/local_rule.txt` did not exist (3.3, fixed); the text for `docs/theory.md` in `docs/theory-text.md` quoted the -0.6 % and the "1.7 times" of one part, and garbled the board ("2 x 1.6 mm board of 3.2 mm"): rewritten; `research/ROADMAP.md` had two items labelled A16 (the small-part rule is now A18; A16 stays the edge, which the project documents cite).

### 7.3 Independent references used

Equation 50 of Muzychka, Yovanovich and Culham (2004) for the bare board (read and reproduced in `paper-case-studies`; status unchanged in `research/theory/BIBLIOGRAPHY.md`), the extrapolated 3D numbers of `paper-case-studies` 16.4 (one of them re-run by the study, 389.117), the independent 3D solver with side films (`analytic-edge-spatial/lib/layered3d_side.py`, checked here at 1 and 0.5 mm), and the network itself for the lateral conductances (finding 2). No new source was opened.

### 7.4 Verdict and recommendation for the program

* **Go for the merge of this folder** as a reviewed investigation (the prototypes, studies and the corrected text).
* **C, 3D solid slabs by thickness and the face term: go for 2.6.0 as written** (INTEGRATION 3, with the corrected list of moved records). First in order: it is small, it is checked against an independent solver and equation 50, and it is a comparison model.
* **B, edge nodes: go for 2.6.0 with one change**: the band `margin_cells(d, dx)` wide (not 1 cell), acceptance "within 5 % of the 3D solver at 0.5 and 1 mm, corner and centre" (measured: corner -3.8 / -4.2 %, centre -2.6 / -3.2 %; 0.2 to 1.1 points below nodes everywhere). It does not reach the "within 3.5 %" of INTEGRATION 2 at 1 mm. Second in order (every FVM and FDM record with an edge coefficient and a thick gap moves).
* **A, local rule: not as written.** Before the feature branch: (a) apply it only to a part at least 4 cells wide in the plane (at 2 cells it doubles the error to the hot side); below that keep the warning of `checks.check_small_part_laminate`; (b) make the change of chain conservative (link a coarse node to the fine nodes it spans, so the lateral laminate conductance is kept at the face; this would also remove the 0.40 face of B and of the program's own rule) or use the margin x2 (the global number within 0.03 points, at 0.64 to 1.00 of its unknowns on one part: little saving); (c) re-measure at 0.5 and 1 mm and on a board with many parts (the cost there is 2.3 to 2.5 times the default, not 1.1 to 2.1). Third in order.
* Open for the maintainer: whether a hot error of +12 % at 1 mm for a 2 mm part is acceptable if the gate (a) is not adopted; whether the transition fix of (b) should be made in the program's own rule first (it moves frozen records of boards with partial copper, not measured here).

## 8. What was read and what was not verified

* **Read for this study**: the program's `laminate.py`, `fvm.py` (laminate seam), `solid3d.py` (slab loop), `checks.py` (small-part ratios), the READMEs of `paper-case-studies` (11, 16), `analytic-edge-spatial` (8) and their scripts. No new external source was opened: the equation 50 of Muzychka, Yovanovich and Culham (2004) and the extrapolated 3D numbers are taken from `paper-case-studies`, where the equation was read from the page image and reproduced (their review); the bibliography statuses of `research/theory/BIBLIOGRAPHY.md` are unchanged and nothing was added.
* **Reproduced here**: the extrapolated 3D reference for S = 2, t = 1.6 bare (389.117 against 389.12); the program's default and global (0.1, 16) R' on S = 2, t = 3.2 (349.606 / 278.863 / 413.013 / 338.691, as in paper-case-studies 11.3 and 16.3); the solid's R' at 4 / 8 / 16 slabs (517.33, 456.21, 435.23 bare; 442.36, 393.72, 374.74 pad); the review's edge probe (fill 0.9999).
* **Not verified / limits**: extrapolated references for S = 5 and 10 mm and for pad boards other than S = 2 (not run: 3.2 GB each; the pad S = 5 rows are against the program's own G(0.1,16)); the FDM with the local rule and the edge nodes; the 3D solver reference of the edge has its own sub-slab and pixel error (0.02 to 0.9 % between 4 and 8 sub-slabs, not extrapolated); the 4-layer residual of -3.5 / -6.0 % at the edge is unexplained; boards with a part on an inner or bottom layer, several close small parts, one-layer boards and metal blocks were not run with the local rule; the memory estimate of the guard for the proposals was not run beyond the solid's law (the layered laws already read the unknowns); times are under a load of 5 to 8 and the sweep ratios are indicative.
* **My doubts** (answered by the review, 7.2): (i) at the 0.25 mm cell the +1 to +2.3 % overshoot of the local and global fine rules is a pixel bias, so the proposal's accuracy at coarser cells (1 mm and above, where the sub-gap is not the limit) is the default's (**wrong**: at 1 mm a 2 mm part moves from -5 / -11 % to +12 / +13 %, bare / pad, because the fine sub-gaps remove the cancellation of the coarse pixel's hot bias); (ii) the margin and the nested-depth transition were validated only by the equality to the global rule and by the two margin scales; (iii) the edge result's scatter (margin 0, 1, 2) shows the transition at a flagged border has a +-2 point effect that a reviewer may want to understand better (a graded margin of the edge nodes would be the next test).

## Audit 2.6.1

`scripts/study_solid_harness.py` re-run on the 2.6.1 tree (5 s): the slab rule moves the 3D solid's hottest temperature by -0.001 to -0.257 K on the harness boards at 2 mm (`plate_pad` -0.257 K, `part_top_path` -0.219 K, the four-layer examples 0.000 K), at 1.40 to 1.80 times the unknowns, as section 5.2 says. Since 2.6.0 the rule is the program's default (`solid3d.slab_rule`, `n_diel=None`); the script passes `n_diel` explicitly, so it still compares 4 slabs with the rule (without the face term, as written). The other studies were not re-run by the audit; `scripts/study_solid_slices.py` is known to count the face term of the 3D solid twice on the 2.6.0 program (see the status at the top).
