# Integration: cut-cell links and the boundary film in the layered FVM (and what the FDM and the 3D solid need)

Status: a proposal measured on a prototype (`lib/cutlinks.py`); nothing of the program is changed. **Depends on `fix/exact-board-cover` being merged first** (the exact `Board.cover` and exact part weights): every number here is against that tree, and `aperture` equals the program bit for bit when no cell is cut.

## 1. What changes, in `pcbthermal/fvm.py`

1. **Geometry** (new function in `geometry.py`, vectorised; the prototype's loop is `lib/cutgeom.py`): for a board with an outline, the **aperture** of every interior face, i.e. the fraction of the face with board on both sides: `ax` (ny, nx-1) and `ay` (ny-1, nx). Build it as `exact_coverage` does (cumulative sums over the grid lines, explicit values only on the lines an edge crosses). Exact where the outline crosses a face once; a face crossed twice (a re-entrant corner cell) needs the sum of the open intervals, not the smaller of the two sides as the prototype has it.
2. **Lateral links** (`Network._assemble`, where `gx = harmonic(S[:, :, :-1], S[:, :, 1:]) dy/dx` and `gy`): for a board with an outline, `gx = ax * harmonic(Sphys_left, Sphys_right) * dy/dx` with `Sphys = S / cover` (the physical sheet, no cover factor), likewise `gy`. Without an outline, or where the aperture is 1 and the cover is 1 on both sides, the expression is the program's and the result is bit-identical (checked: `aperture` = program to 1e-9 K on an outline on grid lines; the prototype adds the difference to the program's matrix instead, which is not bit-identical; the production code replaces the expression).
3. **Edge film** (`Network.__init__`, where `g_side` is set from `edge_length_on_board`): `g_side <- g_side / max(1 + H d / S_phys, 0.25)` per node layer, with `H = g_side / L` (film per length of edge: `h_side` times the slab thickness), `d` the signed distance from the cell centre to the closest outline point (positive inside; for a cell whose centre is off the board d < 0), `L` cancels. Add the change to `g_amb` (the diagonal is `g_amb`) so that `power_out` still adds up. For a **rectangle** without an outline the factor is `1 + H (dx/2) / S_phys` on the left and right edges and `1 + H (dy/2) / S_phys` on the top and bottom (the prototype's `_film_rect`); a rectangle and the same rectangle as an outline then give the same network (checked).
4. **Not changed**: vertical links, vias (their wells use the cover-scaled sheet as before), capacities (`C` already uses the exact cover), films on the faces, heat sources (exact weights), the point SOR and CG (they build their own copy of the links in `solve_sor`: change it to call the same helper), the Lumped and Analytic models (equivalent rectangle, no grid).

Estimated size: 80 to 120 lines in `fvm.py` and `geometry.py` (the aperture function is the bulk), plus the SOR copy; tests below.

## 2. FDM (`pcbthermal/fdm.py`)

Not prototyped. The FDM is node-centred: the nodes lie on the grid lines, the control volume of a node is cut by the outline (`ncov = _node_average(exact_coverage)`), and the face between two nodes is a link of the mean of the two nodal sheets (`_mean(S[:, :, :-1], S[:, :, 1:], mean)`), the same cover-scaled form as the FVM. The same two changes apply in spirit (aperture of the dual face, i.e. the board fraction of the segment between two nodes along its own line; the film distance from the node to the outline), but the dual faces and the half control volumes at the edge need their own geometry; **do not copy the FVM code**. Recommendation: leave the FDM as it is (it is a comparison model) and say in `docs/theory.md` that it keeps the cover-scaled links, unless the maintainer wants the three grid models to agree on turned boards.

## 3. 3D solid (`pcbthermal/solid3d.py`)

Not prototyped here. `solid3d.py` multiplies the conductivity of every `cu` and `fr4` slab by the cover in all directions (`slabs[-1]["kx"] = kx * bcov`) and joins cells with the harmonic mean, so a cut cell has the same factor-c defect; the earlier folder (`rotated-square-3d`, `rotsq.CUT_LINKS`, sections 2 to 9) measured the effect and a cut-cell copy there. The consistent change is the same aperture on the in-plane faces of every slab and the boundary film on the side faces; the vertical links and the face films keep the cover. A decision for the maintainer: the 3D solid is the reference of the others, so changing it changes what the others are judged by; its own review is needed.

## 4. Tests to add on adoption (feature/fix branch)

* `aperture` links equal the program's for an outline on grid lines and for a rectangle (bit-identical matrix); the film factor of a whole edge cell and of a rectangle border (`tests/test_cutlinks.py` has them in the prototype's form).
* Aperture function: sum of apertures along the grid lines equals the exact length of the outline inside each cell (a disc, a turned square, a re-entrant corner); a face crossed twice.
* Energy balance (heat to air over the power = 1 to 1e-9) on a turned square and on a disc, steady and transient.
* Symmetry of K, no positive off-diagonal entry, symmetric LU accepted (no fallback warning), on a cover sweep from 0.002 to 1 (the sliver curve of figure 5 must be continuous: the hottest point may not jump by more than 0.3 K between c = 0.01 and 0.02 at `h_side` 200; the program jumps by 3.6 K).
* The spread over the positions of the outline of the 20 mm square at `h_side` 200 and 2000, 1 mm cell, against the frame reference (`lib/boards.py`): at most 0.1 K (program 1.06 and 1.93 K); the strip at most 0.2 K.
* The film floor: no film factor below 0.25, a positive diagonal at `h_side` 1e5.
* The frozen numbers: see section 5.

## 5. Impact on the frozen numbers (measured, README 6)

* `aperture` only (no film): `part_across_outline` -0.796 / -0.372 / -0.054 K at 2 / 1 / 0.5 mm, `example_cut_to_T` -0.014 K at 2 mm (0 at 1 and 0.5), `round_outline` -0.006 / -0.002 / -0.001 K; `t_outline` and all rectangles unchanged (bit-identical). Three of the 17 harness boards, all with an outline.
* With the film also on rectangles: every board with `h_side` > 0 moves, by at most 0.014 K (0.01 % of the rise; `part_top_path` +0.014, `two_layer_partial` +0.008, `hatched_copper` +0.007, `example_board` +0.002), so the whole frozen file is refrozen (a pending file per the CLAUDE.md rule) and every research folder that reads the program's numbers at the 1e-3 K level is affected.
* The Analytic and Lumped records do not move (they never see the grid); the FDM and the 3D solid do not move if left alone.
* The effect on the **results** at the program's defaults (`h_side` 10): the spread over the positions of the outline is 0.06 K at 1 mm for the centred square (program) and about the same after (0.03 K); the film changes nothing visible at `h_side` 10. The gain is at `h_side` of 50 and above and, at any `h_side`, in the sliver anomaly (0.09 K at 10, 3.5 K at 200 for a sliver of 0.02 cover).

## 6. Risks

* **The film outside its range**: `1 + H d/S` can reach zero when the centre is outside the board and the film is very stiff; the floor makes it safe and was not reached up to `h_side` 1e4, bound in 72 to 112 cells at 1e5 (the limit of `Board.validate`) with results within 0.1 K of the 0.1 and 0.5 floors. The paper (Bochkov and Gibou) was not read; this is a measured rule, not a derived one.
* **Aperture at a re-entrant corner** and at a face crossed several times: the prototype's rule is wrong there; the small T residual (README 3.2) was not explained and may involve it.
* **Imported copper**: the imported faces use a cell sheet scaled by the cell cover (`copper.lateral`); the aperture has to enter as a pixel-level board mask there, not as a factor on the face. Not tested; until done, the imported layers keep the program's links (the prototype refuses them), so a board with imported copper and a cut edge would mix two treatments.
* **Patterned copper at a cut edge** (copper edge held inside the outline): still 2 to 3 K spread at `h_side` 200 for every scheme: this proposal does not fix it (README 5.2).
* **Geometry cost** for a Gerber outline with tens of thousands of cut cells: only the vectorised aperture is acceptable (the prototype is 0.4 ms per cut cell).
* **Consistency of the models**: the 3D solid and the FDM keep the old treatment unless they are changed too; the validation tables that compare the models on outline boards then show the difference (`docs/validation.md` 13 and 23).
* The coarse cell of 2 mm: the schemes do not converge in order there; the harness record `part_across_outline` at 2 mm moves by -0.8 K (the program is nearer by luck of sign), a cell for which the warnings of the program already apply.

## 7. Effort

Prototype to production in `fvm.py`: 1 to 2 days including the vectorised aperture and the SOR helper; the frozen refreeze, the validation tables 13 and 23 (the outline sweeps) and `docs/theory.md` 2 (the FVM section, with a picture: figures 1 and 2 of this folder) one more day; the reviewer's independent check of the aperture function and of the film on a case the study did not use. The FDM and the 3D solid separately, each its own investigation.

## 8. Decisions for the maintainer (with the recommendation)

1. **Adopt the aperture links?** Recommended **yes, as a `fix/` item of 2.6.0** after `fix/exact-board-cover`: it removes a defect of the present program (the sliver anomaly: 3.5 K at `h_side` 200), cuts the spread over the position of the outline 5 to 40 times at `h_side` 200 to 2000 together with the film, moves three harness records and none of the rectangles, and keeps the matrix SPD and an M-matrix.
2. **Adopt the film (the Bochkov-Gibou/Barrett form)?** Recommended **yes, but as a separate decision** because it moves every record that has an edge film (at most 0.014 K): without it `aperture` alone leaves 0.25 to 0.46 K spread at `h_side` 200 to 2000 (0.04 K with it), which is the gain at stiff edges (an aluminium-core or heavily cooled edge). If the film is not adopted, the sliver anomaly is still fixed. If it is, put it on rectangles too (so that a rectangle and the same rectangle drawn as an outline agree).
3. **Which scheme**: `aperture` (+ `film`), not `links` (nodes at the centroids): the centroid schemes are worse on a thin strip with the film on the node and need more geometry; `links+film` is as good only where the strip is wide.
4. **The floor of the film denominator** (0.25): a safety net; keep it with a test, or choose another value (0.1 and 0.5 give the same results within 0.04 K at `h_side` 1e5).
5. **FDM and 3D solid**: leave as they are for 2.6.0, or open their own investigations (README 3.2 and section 2, 3 here).
6. **Before adoption** the reviewer should check what this study did not: the aperture at a re-entrant corner (the small T), imported copper, SOR and CG, and read Bochkov and Gibou if the paper can be obtained.
