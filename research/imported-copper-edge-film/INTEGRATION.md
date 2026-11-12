# Integration: the edge film of imported copper on an outline

Evidence and numbers: `README.md` (sections in brackets). Nothing of `pcbthermal/` was edited; every candidate is a copy in `lib/variants.py`.

## 1. Recommendation

**Adopt the centroid film (decision for the maintainer, after the reviewer and the three runs listed in 4).** In `fvm.Network._cut_edge_film`, take the distance of the series film from the **centroid of the board part of the cell** to the closest outline point, `d_c = max(distance, 0)`, instead of the signed distance from the cell centre, and apply the series film also to imported layers on an outline (remove the `self.cut_edge = False` of the imported branch in `Network.__init__`). Keep the floor 0.25 and the rule that the change goes into `g_amb`.

**Reviewer's recommendation (README 8): go for the imported layers, as implemented on `fix/imported-copper-edge-film-centroid` with the review's two fixes (a laminate node takes the centroid only next to an imported layer; centroid strips of 16 rows). Copper reaching the outline needs no exception (README 8.3). For the drawn layers: adopt only with the frozen-number refreeze and after the same copper-to-the-wall check with the drawn film as the 'before' (a decision for the maintainer, `docs/versions.md` 'Planned' 21).**

Measured on copies against a 3D reference (2 layers, copper 1.2 mm inside the wall, ten turned and shifted boards, [3.1, 3.2]): mean error / worst at 1 mm, `h_side` 200: -3.00 / 3.85 % to **-0.94 / 1.87 %**; `h_side` 500: -4.90 / 6.75 to -1.13 / 2.55; `h_side` 1000: -6.36 / 8.78 to -1.26 / 3.02; at 0.5 mm and 1000: -4.78 / 6.88 to -2.33 / 2.84; at `h_side` 10 no change (0.05 points). Cost: no unknowns, no new matrix entries, symmetric, no positive off-diagonal entry, heat balance 1e-13, aligned run 0.4 s unchanged; one exact cover at 8 x 8 per cut cell (to be vectorised and restricted to the cells with edge length; the cost on a 200 mm board was not measured).

Why not the others: the film in series from the centre (the reviewer's) changes only the aligned board (+3.6 points at 1 mm, +0.1 to +0.35 on the turned ones) and raises the spread at 1 mm from 1.9 to 3.6 %; scaling the distance by a constant cannot suit both; graded sub-gaps recover 0.4 points of the 1.1 that n = 16 gives; more sub-gaps cost 1.4 (n 8) to 2.3 (n 16) times the unknowns and leave the spread.

## 2. What it does not change

* The idealisation error: the program at n = 4 sub-gaps is -2.0 % below the resolved 3D laminate at any cell, drawn or imported, rectangle or outline (README 2.1). It is not an edge-film effect. Options: leave it (it is the known 1/n behaviour of `research/laminate-nodes`), or raise the default `laminate_n_max` for boards with a bare edge band (centroid film plus n = 16: +0.22 % mean, worst 1.25 % at 1 mm, 2.3 times the unknowns; not recommended as a default).
* The spread over the angles at 1 mm (1.8 %) and at 2 mm (9 to 13 % at `h_side` 500 to 1000): cut-cell scatter of a cell as big as the part.
* The FDM, 3D solid, Lumped and Analytic.

## 3. Alternative: accept as a limit

If the maintainer prefers no change: write into the documents that on a board with an outline and imported copper the heater rise reads **0.4 % cool at `h_side` 10, 1.1 % at 50, 3.0 % at 200 (worst 3.85 %), 4.9 % at 500 and 6.4 % at 1000 at the 1 mm cell** (0.4 to 4.8 % at 0.5 mm), of which about 2 points are the laminate idealisation and the rest the cell error (README 3.1, 3.2). These are mean errors on a two-layer, full-copper, 1.2 mm-inset board.

## 4. Before adoption (review status in README 8)

1. *(Review: the striped board and four layers run on the program, README 8.4; the four-layer truth not run.)* The 4-layer truth and the striped board (stripes and pad with the frame reference): paused runs, `scripts/study_truth.py 4 1.2 200,1000,50` and the last rows of `scripts/study_robustness.py`.
2. *(Review: T, L, oswlight and rp2040 run, README 8.4; copper reaching the wall against the truth, README 8.3: no exception needed; the disc not run.)* A T and an L outline, a disc against an axisymmetric reference, a real imported outline board (oswlight, rp2040, storm of the local library): the largest move of the change should be reported.
3. The drawn layers: the centroid film also reduces their error (-3.39 to -1.76 % at 1 mm in the frame reference, README 3.3); adopting it for them moves frozen numbers of drawn outline boards (`part_across_outline`, `round_outline`, `example_cut_to_T`) and needs a pending file and the refreeze: a separate decision.
4. *(Done: `fix/imported-copper-edge-film-centroid`, reviewed GO with two fixes.)* A `fix/` branch off `develop` with tests (the film of a whole cell unchanged, a constant field exact, the centroid inside the board part, `d_c` zero for a sliver), the whole battery, the validation section 38 update (its "series film rejected" paragraph and the converged values) and the reviewer.

## 5. Risks

The argument for the centroid is geometric, not a proof (README 4); the aligned board is still +0.5 % hot with it in the frame reference. The truth has 0.1 to 0.3 % of extrapolation uncertainty, so differences below 0.3 points are not resolved. The constants are not fitted: there is no free parameter in the recommended candidate (the `alpha` and graded variants were tried and rejected).
