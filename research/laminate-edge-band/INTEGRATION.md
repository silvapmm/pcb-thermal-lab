# Integration: the edge film of the laminate in the layered FVM and FDM

Proposal only; nothing in `pcbthermal/` was edited. Evidence: `README.md` (sections in brackets). Prototype: `lib/edge_rules.py`. **Reviewed** (README 11): the first version of this file recommended a film term on the copper nodes that has no physical basis and that counted twice on the 2.6.0 tree; it is replaced below.

## 1. Recommendation (reviewed)

Adopt in **2.6.0**, on top of the cut-cell branch, as one `feature/` (it shares `laminate.py` and `fvm.py` with the 2.6.0 laminate and cut-cell items and moves frozen numbers):

1. **FVM and FDM: a band of laminate nodes along the edge** when `board.h_side > 0` and the gap is cut (`n0 > 1`): the cells (nodes) that touch the edge (the border, or `edge_length_on_board > 0` for an outline) grown by `laminate.margin_cells(d, dx)` = `ceil(d / dx) + 1` cells, ORed into `GapPlan.flagged` (README 5, 6.1; the width does not matter from one gap thickness on once the film below is in).
2. **FVM: the film of the interior laminate nodes behind half a cell**, `g' = g / (1 + h_side dx / (2 k_xy))`. **On the 2.6.0 tree this is already done** by `fvm.Network._cut_edge_film`, which runs after `_add_ladder` on every node layer (README 11.4): nothing to add there; on `develop` it would be added to the interior nodes only. **Not** on the laminate held by the copper nodes (README 11.2: no physical basis; it only cancels the sub-gap error and reads up to +11.6 % hot at a 1 mm cell).
3. **FDM: no film term** (its node is on the edge, README 11.5).

Result against the reviewed reference (README 11.1, 11.2, 11.4, 11.5): for `h_side` <= 200 W/m2K, 2-layer boards 0.8 to 3.2 mm, cells 1 to 0.25 mm, corner and centre, worst error **-2.4 % (FVM) and -2.6 % (FDM)** with the program's four sub-gaps (as is: -15.3 %); the 60 cases of the first sweep give -2.6 / -2.9 % against the study's reference, which is 0.25 % high. At 500 W/m2K -5.5 % (FVM, 3.2 mm) with four sub-gaps.

**Sub-gaps for `h_side` above 200 W/m2K (second step, optional).** The residual is the 1 / n of the sub-gaps: 8 sub-gaps give -2.0 % at 500 W/m2K and +1.5 / -0.9 % at 200, 16 give -0.8 % at 500 and -2.8 % at 2000 W/m2K on 3.2 mm at 0.25 mm (README 11.2). The program has **one** sub-gap count per gap (`GapPlan.n`), so a separate count for the band is a change of the plan (two counts per gap, a transition between them) and was **not** prototyped; the cheaper route is the existing option `laminate_n_max` (8 or 16, `laminate_s_max_mm` small enough), which costs the same chain everywhere the gap is cut. Recommendation: no separate count in 2.6.0; a warning when `h_side` > 200 W/m2K and a gap is cut (FVM/FDM about 5 % low at 500 with the defaults on 3.2 mm, more at 2000, and the cell must also be at most 0.25 to 0.5 mm there, because a half cell larger than the gap over-corrects: +7 % at 2000 W/m2K, 0.8 mm, 1 mm cell, 8 sub-gaps). A PCB in air has `h_side` 5 to 50 W/m2K, where step 1 is enough.

Do not take the eta rule (README 9) or the band of half a thickness (6.1).

## 2. Changes

* **`laminate.py`**: `plan_gaps(..., edge_cells=None)` ORs the mask into `flagged` of every gap with `n0 > 1`, only if `h_side > 0`; `h_side` None or 0 leaves everything bit for bit as it is; one-layer boards and boards with a metal block keep the earlier treatment (`uses_rule`).
* **`fvm.py`, `fdm.py`**: compute the mask (they have the edge lengths) and pass it; `unknowns` and the memory guard already count from `plan_gaps`. FVM on 2.6.0: no film change (the tree's `_cut_edge_film` covers the interior nodes; check in the review of the feature that it still runs after `_add_ladder` and on all node layers). FDM: none.
* **Not changed**: the Lumped, the Analytic, the 3D solid (reads hot at a coarse cell and converges from above, README 6.6, not re-run by the review), the vias.
* **Documents when adopted**: `docs/theory.md` (the laminate rule: the band, why, the half-cell film of the cut-cell section covering the laminate nodes; figures 01 to 03 and 07), `docs/validation.md` (README 11.2 and 11.4 tables), `docs/versions.md`, `docs/models.md` limit text (the edge above 200 W/m2K).

## 3. Acceptance tests (reviewed reference, `out/refs_review.json`)

1. `h_side` None: bit identical (all 17 harness boards at 2, 1, 0.5 mm).
2. 2 layers 3.2 mm, 30 x 20 mm, `h_side` 200, 10 mm part in the corner and at the centre, FVM and FDM at 0.5 and 0.25 mm: within 3 % of 80.112 / 60.708 K (`lib/graded3d.py`); 1.6 mm (92.150 K) and 0.8 mm (111.893 K) corner within 2 %.
3. Band width independence: within 0.5 point between one gap thickness and the margin.
4. The FVM film is applied once: the edge conductance of an interior node equals `h_side th edge / (1 + h_side dx / (2 k_xy))` (a test on the network arrays; it fails if the factor is applied twice).
5. Unknowns: the 30 x 20 mm, 3.2 mm board at 0.5 mm 1.92 times; the harness boards at most 1.74 times at 2 mm.

## 4. Frozen records and tests that move (measured on the 2.6.0 tree, README 11.6)

`tests/regression` at 2 mm: the FVM and FDM records and their times to 63 % of `example_board`, `profile_board`, `reference_board`, `example_cut_to_T`, `part_across_outline`, `plate_vias`, `plate_lone_via`, `round_outline`, `t_outline` (36 tests; hottest +0.001 to +0.82 K, at most 0.40 % of the rise on develop, README 11.3); a pending file `tests/regression/data/pending/laminate-edge.json`. The other integration tests that move are listed in README 11.6. **Before**: the integration tree's own frozen test fails 4 tests without this change (a record in two pending files, three records off): that must be fixed first, by the owner of the integration.

## 5. Risks and effort

Risks: patterned copper at the edge, outlines beyond the harness, a part at the middle of an edge and the transient were not swept; four-layer boards were measured only with the prototype (README 6.4; the 3.2 mm, 4-layer case stays about -4 % from the simple stack-up allocation, not an edge item). Effort: half a day for the executor (the band is about 20 lines; no film code on 2.6.0), then the reviewer; the tester writes the pending file.

## 6. Open for the maintainer

1. Adopt in 2.6.0 (recommended: yes, the band only on the 2.6.0 tree).
2. A separate sub-gap count in the band (recommended: no, a warning above 200 W/m2K instead).
