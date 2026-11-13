# Reviewer's opinion: the centroid edge film on drawn layers

Branch `fix/drawn-layers-edge-film-centroid` (study 184929fd, program change 0eac0a94 and the executor's follow-up commits). Question of the maintainer: extend the edge film measured from the centroid of the board part of a cut cell (series film, `d >= 0`, floor 0.25) from the imported layers to the drawn layers of a board with an outline.

**Verdict: GO, accept with the limit written down (no new warning).** The change is better on every case where the copper stops short of the outline, which is the common real case (copper is held back from a routed edge), and its only failure is a small error on the SAFE side (hot, at most +1.5 % against the 3D truth, about +2 % against the program's own converged answer, at a 1 mm cell, halving with the cell). But the explanation that the branch gives for that failure is wrong and must be corrected (section 3).

## 1. What was re-run

All runs on copies of the two trees (`git archive develop pcbthermal` and `git archive HEAD pcbthermal` of the branch, which differ only in `pcbthermal/fvm.py`), with a private configuration, one job at a time, below 1.5 GB.

* `study_drawn_film.py run` on the two trees for `T_wall`, `L_wall`, `T_in`, `sq_wall` (200 and 1000 W/m2K), `sq_in` (10 to 1000), `mixed_2l`, `mixed_4l`, `imp_2l`: every mean, spread and worst of the table of `docs/validation.md` 40.1 reproduced to the second decimal (for example T wall 1 mm -0.27 to +1.19, L wall -0.55 to +0.81, square wall at 1000 W/m2K -3.65 to -0.93, copper inside at 200 W/m2K -4.76 to -3.15).
* `check_drawn_film_invariants.py` on the branch tree: K symmetric (difference 0), no positive off-diagonal entry (so the maximum principle holds), a constant field reproduced to 1.8e-17 of the ambient conductance for `h_side` 10 to 1e5, balance at most 1.4e-12; the 200 x 150 mm outline board peaks at 1.49 GB at 0.5 mm. With `d >= 0` the film factor `1 + H d / S` is at least 1, so the 0.25 floor can no longer bind on any layer: the film of a cut cell is never stiffened above `H L`.
* A new convergence test (below): the same boards at 1, 0.5, 0.25 and 0.125 mm, with the laminate in 4 sub-gaps (the default) and in 8.

## 2. Convergence: against the 3D truth and against the program's own limit

Error of the heater mean against the 3D truth, %, for the aligned board (0 degrees) and two turned ones (22.5 and 45 degrees), shift 0. The aligned board at 0.125 mm is the program's converged answer: its distance from the truth is the idealisation of the layered model (one node per copper layer, the laminate in n sub-gaps), not the edge film.

| Board, h_side, sub-gaps | cell mm | develop: 0 / 22.5 / 45 | branch: 0 / 22.5 / 45 |
| :-- | :-- | :-- | :-- |
| L, copper to the wall, 200, 4 | 1 | -0.10 / -0.53 / -0.49 | -0.10 / +0.93 / +1.16 |
| | 0.5 | -0.98 / -0.58 / -0.60 | -0.98 / +0.17 / +0.16 |
| | 0.25 | -0.84 / -0.71 / -0.65 | -0.84 / -0.34 / -0.25 |
| | 0.125 | -0.86 / -0.74 / -0.68 | -0.86 / -0.55 / -0.53 |
| L, copper to the wall, 200, 8 | 1 | +0.81 / +0.04 / +0.15 | +0.81 / +1.76 / +1.97 |
| | 0.125 | -0.26 / -0.14 / -0.08 | -0.26 / +0.09 / +0.10 |
| T, copper to the wall, 200, 4 | 1 | +0.16 / -0.34 / -0.37 | +0.83 / +1.19 / +1.30 |
| | 0.125 | -0.81 / -0.75 / -0.70 | -0.76 / -0.55 / -0.52 |
| T, copper to the wall, 200, 8 | 1 | +0.97 / +0.26 / +0.26 | +1.77 / +2.06 / +2.17 |
| | 0.5 | +0.07 / +0.12 / +0.13 | +0.38 / +1.05 / +1.03 |
| | 0.125 | -0.16 / -0.11 / -0.05 | -0.11 / +0.12 / +0.15 |
| square, copper to the wall, 200, 4 | 1 | +0.90 / -1.42 / -1.50 | +0.90 / +0.05 / +0.15 |
| | 0.125 | -0.82 / -0.82 / -0.78 | -0.82 / -0.63 / -0.65 |
| square, copper to the wall, 1000, 4 | 1 | -0.17 / -4.13 / -4.65 | -0.17 / -1.20 / -0.98 |
| | 0.125 | -3.08 / -3.08 / -3.00 | -3.08 / -2.71 / -2.77 |
| square, copper to the wall, 200, 8 | 1 | +1.76 / -0.91 / -0.92 | +1.76 / +0.81 / +0.89 |
| | 0.125 | -0.25 / -0.25 / -0.20 | -0.25 / -0.03 / -0.05 |
| square, copper 1.2 mm inside, 200, 4 | 1 | -1.38 / -5.71 / -6.36 | -1.38 / -3.95 / -4.62 |
| | 0.125 | -2.27 / -2.11 / -2.31 | -2.27 / -1.89 / -2.15 |
| square, copper 1.2 mm inside, 1000, 4 | 1 | -2.91 / -10.83 / -12.15 | -2.91 / -6.90 / -8.39 |
| | 0.125 | -4.03 / -3.76 / -4.11 | -4.03 / -3.26 / -3.75 |

Read against the program's own converged answer (the aligned board at 0.125 mm), the turned boards at 1 mm with copper to the wall are:

* develop: -0.6 to -0.7 (square, 200), -1.0 to -1.6 (square, 1000), +0.3 to +0.4 (L), +0.4 to +0.5 (T);
* branch: +0.9 to +1.0 (square, 200), +1.9 to +2.1 (square, 1000), +1.8 to +2.0 (L), +2.0 to +2.1 (T);

and with the copper 1.2 mm inside: develop -3.4 to -8.1, branch -1.7 to -4.4 (better). The branch's hot excess falls about as the cell (+1.0 at 0.5 mm, +0.5 at 0.25, +0.3 at 0.125 on the L): a first-order discretisation error of the film from the centroid, on the safe side.

## 3. The explanation of the T and L failure was wrong

`docs/validation.md` 40.1 (as first written on the branch) said that the film from the centroid 'converges from above' and that the earlier scheme was near the truth only by a cancellation with the -2 % of the four laminate sub-gaps. Measured:

* The idealisation of the T and L with copper to the wall is about -0.8 %, not -2 % (aligned board at 0.125 mm, 4 sub-gaps), and develop's turned boards lie within 0.5 point of it at every cell: there was no cancellation to lose.
* The suggested test: with 8 sub-gaps (idealisation about -0.2 %) the hot excess does NOT disappear, it grows: the turned T reads +2.06 / +2.17 % at 1 mm and +1.05 % at 0.5 mm against the truth (develop: +0.26 % and +0.12 %).
* So the excess is a new error of the scheme (the film from the centroid, with the physical sheet of the cell, is too weak on a cut cell whose copper reaches the wall), not an old one uncovered. The same error is present on the copper-to-wall SQUARE, where it is hidden: there the idealisation is cooler (-0.8 % at 200, -3.1 % at 1000 W/m2K) and the hot excess of the branch cancels it. The improvement of the copper-to-wall square at 1000 W/m2K (-3.65 to -0.93 %) is that cancellation, not a better film (against the program's own limit it goes from -1.3 to +2.0).

Where the branch is genuinely better is the copper held inside the outline (bare laminate in the cut cells), at every `h_side` and cell, and the agreement of drawn and imported layers (the same film on both, see 4).

## 4. Mixed boards

On the branch every layer and every laminate node of an outline board takes the distance from the centroid (only metal-block layers keep the centre); the per-layer switch and `laminate_neighbours` of develop are gone, so a board whose layers change from drawn to imported has no switch in the edge film any more. Means at 200 W/m2K, 1 / 0.5 mm: drawn -3.15 / -2.76 (develop -4.76 / -3.57), top imported -1.73 / -1.89 (develop -1.97 / -2.00), both imported -0.93 / -1.46 (unchanged). The gap that remains between drawn and imported copper is by construction not the film (the film is now the same); it is the drawn layers' cell fill and links against the imported faces. No discontinuity was found.

## 5. Frozen numbers

The pending file `tests/regression/data/pending/drawn-layers-edge-film-centroid.json` holds the FVM of the three outline boards: `part_across_outline` +0.0086 / +0.0083 / +0.0024 K, `round_outline` +0.0091 / +0.0050 / +0.0025 K, `example_cut_to_T` +0.0009 K at 2 mm, times to 63 % +0.01 to +0.03 %; every move is hot and under 0.01 K. Checked against `v2.6.0.json`.

## 6. Recommendation and what the documents must say

* Accept. The error is hot, at most about 2 % at 1 mm with copper to the wall (1 % at 0.5 mm), the copper-inside case (the usual one) gains 1.6 to 3.5 points at 1 mm, drawn and imported layers now share one film, and every invariant holds. A new warning is not needed: the edge-laminate warning already fires above 200 W/m2K and the effect at 10 to 50 W/m2K is below 0.4 point.
* Done by the review in `docs/validation.md` 40.1, 40.4 and 40.5, `docs/versions.md` and `CHANGELOG.md`: the cancellation explanation is withdrawn and the documents say: the film from the centroid is first order and hot where the copper of a cut cell reaches the outline (+1 to +2 % against the program's converged answer at 1 mm, about half at 0.5 mm, measured on T, L and square outlines, also with 8 laminate sub-gaps); the improvement of the copper-to-wall square at high `h_side` against the truth is partly a cancellation with the cool idealisation of the layered model; the genuine gain is the copper held inside the outline.
* `docs/theory.md` 2.1.1 (the cut-cell film): the same limit in one sentence (done by the review).

## 7. Not verified

* The hottest point (only the heater mean, the study metric, was compared), the FDM (unchanged, no centroid film), outlines with slanted or curved sides against a truth (the truth solver is axis-aligned; only the round frozen board moves).
* Why the film from the centroid is too weak where the copper reaches the wall was not derived; a candidate correction (for example the distance from the centroid of the cut face, or a weight by the edge length) is a question for a later study, not this branch.

## 8. Open decision for the maintainer

Accept the hot first-order error on copper-to-wall outline boards (recommended), or keep the film from the cell centre on drawn layers whose copper reaches the outline (two rules again, and the mixed-board switch comes back).
