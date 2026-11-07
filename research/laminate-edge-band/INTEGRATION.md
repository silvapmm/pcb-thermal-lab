# Integration: the edge film of the laminate in the layered FVM and FDM

Proposal only; nothing in `pcbthermal/` was edited. Evidence: `README.md` (sections in brackets). Prototype: `lib/edge_rules.py`, written to be moved into `laminate.py`. **Not yet reviewed.**

## 1. Recommendation

Adopt **one rule with two parts**, on a `fix/` branch (it corrects a model that is 14 % low at 200 W/m2K, so a fix and a patch number, unless the maintainer wants it with the 2.6.0 laminate items, which it shares files with):

1. **Band of nodes along the edge** when `board.h_side > 0` and the gap is cut (`n0 > 1`): the cells that touch the edge (the border cells, or `edge_length_on_board > 0` for an outline) grown by `laminate.margin_cells(d, dx)` cells, ORed into `GapPlan.flagged` (README 5, 6.1). This is the edge item of `laminate-2-6` (B) with the wider band.
2. **The film of the laminate nodes behind half a cell** (README 4, cause 2): in `laminate.build`, the edge conductance of the interior nodes of the flagged cells, and the laminate part held by the copper nodes of the flagged cells, is multiplied by `f = 1 / (1 + h_side dx / (2 k_xy))` with `k_xy` of the gap and `dx` the cell (FVM) or node spacing (FDM). The factor is physical (the standard finite-volume boundary condition) and is the part that makes the result independent of the band width.

Result (README 3, 6): worst error **2.2 %** for `h_side` <= 200 W/m2K on 2-layer boards 0.8 to 3.2 mm, cells 1 to 0.25 mm, corner and centre (as is: 15.8 %); at 500 W/m2K 0.8 to 1.9 % up to 1.6 mm and 5 % at 3.2 mm. Do not take the eta rule (no unknowns, but 5 to 9 % at a corner on thick boards) and not the band of half a thickness (leans on a cancellation).

**Optional second step**: a separate sub-gap count for the band, `n_edge = min(16, ceil(d / 0.2 mm))`, for `h_side` above 200 W/m2K (3.2 mm, 500 / 2000 W/m2K: error 1.3 / 3.4 % with 8, 0.5 / 1.3 % with 16, README 6.3), at about 1.6 to 2.7 times the band's unknowns on a 30 x 20 mm board. The typical `h_side` of a PCB in air is 5 to 50 W/m2K, where the first step is enough.

## 2. Changes

* **`laminate.py`**: `plan_gaps(..., edge_cells=None)` takes a mask (computed in `fvm.Network` and `fdm.Network`, which already compute the edge lengths) and ORs it into `flagged` of every gap with `n0 > 1`, only if `h_side > 0`; `build` applies `f` as above. No new option; `h_side` None or 0 leaves everything bit for bit as it is. Boards with a metal block and one-layer boards keep the earlier treatment.
* **`fvm.py`, `fdm.py`**: pass the mask; `unknowns` and the memory guard already count from `plan_gaps`. The 2.6.0 tree already puts the edge film of the node in series with the sheet; the interior nodes are built after it, so the factor of this proposal must be applied once, to the laminate nodes only (to be checked in the code by the reviewer; README 6.7 measured the improvement there).
* **Not changed**: the Lumped, the Analytic (the per-layer edge of `analytic-2-6` is its own item), the 3D solid (reads hot at a coarse cell and converges from above, README 6.6), the vias.
* **Documents when adopted**: `docs/theory.md` 4 and 1.4 (the rule, the two causes, figures 01 to 03), `docs/validation.md` (the tables of README 3 and 6), `docs/versions.md`, `docs/models.md` limit text; the memory law factor for the extra unknowns (+15 to +92 % on a small board) is the guard's own count.

## 3. Acceptance tests (numbers of README 3 and 6; tolerance on the program)

1. `h_side` None: bit identical (all 17 harness boards at 2, 1, 0.5 mm).
2. 2 layers 3.2 mm, 30 x 20 mm, `h_side` 200, 10 mm part in the corner and at the centre, FVM 0.5 and 0.25 mm: within 3 % of the independent 3D solver (`study_reference.py` numbers 80.33 and 60.86 K); 1.6 and 0.8 mm within 2 %; and the result independent of the band width within 0.5 points between 1 gap thickness and 2.
3. Conservation: the edge conductance of a cell of the band equals the earlier `h_side x slab x edge` minus `(1 - f) h_side x laminate x edge` (the test of `tests/test_edge_rules.py`).
4. FDM within 3 % on the same cases (it is 1.1 % worst in the prototype).
5. The unknowns of the 30 x 20 mm, 3.2 mm board at 0.5 mm 1.92 times, of the harness boards at most 1.74 times at 2 mm.

## 4. Frozen records

Every FVM and FDM record of a board with `h_side` > 0 and a gap above 0.4 mm moves (12 of the 17 boards; README 8): +0.002 to +0.84 K, at most 0.41 % of the rise (`part_across_outline`); a pending file `tests/regression/data/pending/laminate-edge.json`, folded at the next refreeze. The Analytic per-layer edge test and the 2.6.0 FVM number tests that follow the edge film need the same look.

## 5. Risks and effort

Risks: the FDM justification is empirical; the transient was not measured; patterned copper at the edge and outlines beyond the harness were not swept; a very coarse cell (larger than the gap) overcorrects by up to 4 % at 500 W/m2K. Effort: 1 day for the executor with the tests (the prototype is about 60 lines), then the reviewer; the tester refreezes. Open for the maintainer: a `fix/` (patch) or with the laminate items of 2.6.0; whether the optional band count goes in at once.

## 6. Order and gates

1. The reviewer re-runs `study_reference.py --small`, `study_sweep.py --refs refs30 --cells 1,0.5,0.25`, `study_finer_laminate.py`, `study_harness_impact.py` and the tests, checks the half-cell factor against the code of `Network.__init__` of the integration tree, and gives the verdict.
2. Then the feature branch with the acceptance tests above; the tester runs the whole battery and the frozen numbers at 2, 1 and 0.5 mm.
