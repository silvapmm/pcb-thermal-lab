# Text for the project documents (when the work is adopted or the limit is documented)

## `docs/theory.md`, section of the 3D solid, edge loss on an outline (limit, valid today; the text recommended by the review)

**Limit: the 3D solid on an outline that cuts cells, with a high edge coefficient.** On a board with an outline the 3D solid gives every cell it cuts the conductance `1 / (1 / (h_side L dz) + 0.25 (dx + dy) / (kx L dz))` per slab, with `L` the outline length in the cell and `kx` the in-plane conductivity multiplied by the cover of the cell; the links between cells use that scaled conductivity too. For a cell the outline leaves whole this is exact; for a cut cell the path to the edge is too resistive (by up to `1 / cover`), so the edge of a board whose outline does not follow the grid lines (a turned, round or slanted outline, or a straight one between grid lines) loses too little heat. The effect grows with the edge coefficient: at the default 10 W/m2K it is 0.3 K or less; at 1 mm cells a 40 mm board turned against the grid reads +1.1 to +1.8 K (1.6 to 2.7 % of the rise) too hot at `h_side` 100 W/m2K and about +3.5 K (7 %) at 1000, a 40 mm round board +6.6 % at 1000 (+3.2 % at 0.25 mm); it falls slowly with the cell (about 0.55 per halving). The FVM and the FDM attach the edge film to the node and do not show it to that size (within 0.6 % of an axisymmetric reference at 1 mm). When the edge coefficient is 100 W/m2K or more on such an outline, read the FVM; the 3D solid then reads too hot near the edge and at the parts it drives (`research/rotated-square-3d/README.md` 2 to 5 and 10).

## `docs/validation.md`, a row for the outline

| case | 3D solid | FVM | FDM | note |
| :-- | --: | --: | --: | :-- |
| 40 mm square turned 20 degrees, 1 mm, `h_side` 10 / 100 / 1000, minus the aligned square | +0.06 / +1.28 / +3.12 K | +0.01 / +0.08 / +0.33 K | +0.00 / -0.00 / -0.01 K | part on the grid, 2 W in 6 mm |
| the same at `h_side` 100 / 1000, minus the continuum value of an independent solver (91.89 / 74.23 degC) | +1.31 / +3.63 K | | | review, README 9.2 |

## `docs/versions.md`, chapter 'Planned', an entry (after the decision)

* **Cut cells in the 3D solid** (`fix/solid3d-cut-cells`, after the investigation `research/rotated-square-3d`): the cover is sampled with the centroid of the board part and the aperture of every face; the links between cells run through the aperture over the distance between the centroids, the edge term over half the depth of the board strip; the conductivity is no longer multiplied by the cover. Evidence and measured impact: `research/rotated-square-3d/INTEGRATION.md`.

## `docs/versions.md`, chapter 'Planned', an entry for the defect found by the review (implemented in 2.4.5 by `fix/part-across-outline` and `fix/board-cover-8x8`; kept as the record, not to be added)

* **The power of a part that crosses the outline** (`fix/part-across-outline`, after `research/rotated-square-3d` README 9.4): the FVM, the FDM and the 3D solid give a cut cell the power of the part's cover of the whole cell; spread it over the intersection of the part and the board (sample-wise). Example board cut to a T at 1 mm and the default edge coefficient: FVM 109.06 degC, 106.85 at 2/3 mm where no cell is cut, 107.56 with the correction; re-run `docs/validation.md` 13. With it, sample the footprint of a part 8 x 8 in the 3D solid as the FVM does (README 9.3).

## `docs/versions.md`, chapter 'Planned', the entries of the cut cells of the FVM (after the decision; replace the text 'Cut cells treated by their real shape'; numbers of README 11 and the review 11.8)

* **Exact board cover** (`fix/exact-board-cover`, 2.6.0 if the maintainer agrees; after `research/rotated-square-3d` README 11.3 and 11.8): `Board.cover` by clipping each cut cell against the outline instead of 8 x 8 samples. The sampled cover misses the area of an edge that runs along a lattice direction (+0.64 % of a 20 mm square turned 45 degrees at 1 mm, -0.38 % at slope 1/3) and makes the hottest point depend on the turn of a board by about 1 K at the default `h_side` 10 and 1 mm; the exact cover brings that to 0.1 K. Moves the FVM records of `part_across_outline` (-0.55 K at 2 mm) and `round_outline` (+0.01 K); the 3D solid reads the same cover (not measured).
* **Cut-cell links in the layered FVM** (`feature/fvm-cut-cells`, 2.6.0, after the exact cover and after a choice of scheme; README 10, 11 and 11.8): the program's lateral link into a cut cell is a factor c (the cover) too small across the cut. Two-point links between the centroids through the aperture (`links`) cut the dependence on the position of the outline 2 to 9 times at `h_side` 100 and 2000 W/m2K (shift spread of a 20 mm square at 2000 and 1 mm: 2.8 to 0.34 K) and leave the default coefficient alone; on the closed form of a sheet with a rim film the face aperture with the boundary film of the literature is more accurate, so the scheme is chosen by a comparison first. The fill of a cut cell with patterned copper has no verdict yet (README 11.5). Moves the FVM records of `part_across_outline` (-1.43 K at 2 mm), `example_cut_to_T` and `round_outline` (below 0.03 K). The FDM and the 3D solid are separate items; the Lumped and Analytic are unaffected.

## `docs/validation.md` 23, the 'Limit' paragraph (replacement text, after the review)

A cut cell still conducts with its cover, so a part over a cut edge reads 0.5 to 0.7 K (about 1 % of the rise) hotter at 1 to 0.5 mm than with the edge on the grid lines. Two mechanisms are at work (`research/rotated-square-3d` README 11 and 11.8): the 8 x 8 cover, which misses the area of an edge along a lattice direction (+0.64 % of a 20 mm square at 45 degrees and 1 mm) and gives about 1 K of dependence on the turn of a board at the default `h_side` 10; and the lateral link into a cut cell, a factor c (the cover) smaller than that of a straight edge, which matters from `h_side` 100 W/m2K up (2.8 K of spread over the positions of a straight edge on a 20 mm square at 2000 W/m2K and 1 mm). An exact cover and cut-cell links are in the chapter 'Planned' of `versions.md`.

## `research/ROADMAP.md` (kept on the research side)

A3 closed by this folder once the maintainer decides P1 or P2; the open questions left: a patterned-copper board against an independent reference, and the 45 degree residual of the board turn in the copy (README 9.2); the T board +0.2 K is explained by the part across the outline (README 9.4).
