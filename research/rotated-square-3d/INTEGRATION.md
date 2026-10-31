# Entering the program: the cells that the outline cuts in the 3D solid

Nothing in `pcbthermal/` was edited. The proposals were measured on a copy of `pcbthermal/solid3d.py` made in memory by `lib/rotsq.py` (a text replacement of four expressions, refused when the source changes). Numbers are in `README.md`; the maintainer decides.

## What changes in the program, if P1 is adopted

Only `pcbthermal/solid3d.py`, only for a board with an outline (`Board.has_outline()`); the rectangular branches (no outline) are untouched and give bit-identical results (README 6).

1. **The cover and the geometry of the cut cells.** `bcov = b.cover(nx, ny, dx, dy)` is replaced by a sampling of every cell on a 16 x 16 lattice that returns, besides the cover, the centroid of the board part of the cell and the board fraction ("aperture") of every face between two cells (`lib/cutcell.py`, `cut_geometry`; about 40 lines using `geometry.points_in_polygon`).
2. **No scaling of the in-plane conductivity by the cover.** The line `slabs[-1]["kx"] = np.maximum(slabs[-1]["kx"] * bcov, ...)` keeps the physical conductivity; the cross-section of a link is carried by the aperture.
3. **The links between cells** (the loop over slabs): between two board cells the conductance is `min(dz) * face_length * aperture / (d1/k1 + d2/k2)`, with `d1`, `d2` the distances from the face to the centroids of the two board parts (a whole pair of cells: `dx/2 + dx/2`, the program's value); a face off the board has no link.
4. **The edge term** of a cell on the outline: `1 / (1/(h L dz) + d / (k L dz))` with `d = c dx dy / (2 L)`, half the depth of the strip of board behind the outline in the cell (a whole edge cell: `dx/2`, the program's value), the physical `k`, instead of `0.25 (dx + dy)` through `k * cover`.

The code of the copy is in `lib/rotsq.py` (`CUT_COVER`, `CUT_LINKS`, `STRIP_EDGE`) and is what the measurements below ran. A tidy implementation would vectorise the sampling and keep the documentation, tooltips and tests of the program; the cost of the sampling was not measured.

## Measured impact

| where | program | copy (P1) | README |
| :-- | --: | --: | :-- |
| 40 mm square turned 20 degrees, 1 mm cells, `h_side` 1000, board only | +3.12 K above aligned | -0.18 K | 2 |
| same, `h_side` 100 | +1.28 K | -0.04 K | 2 |
| same, `h_side` 10 (default) | +0.06 K | -0.00 K | 2 |
| 20 mm square, half-cell shift, `h_side` 2000, 40 / 80 / 160 cells per side | +5.78 / +3.58 / +2.03 K | -0.23 / -0.04 / -0.01 K | 4 |
| same, turned 20 degrees | +5.59 / +3.72 / +2.32 K | -0.27 / -0.00 / +0.03 K | 4 |
| same, turned 45 degrees | +4.81 / +3.78 K at 40 / 80 | +0.69 / +0.49 K | 4 |
| round board 40 mm against the (r, z) reference, 1 mm, `h_side` 1000 / 5000 | +6.6 / +5.9 % | +0.5 / +0.6 % | 5 |
| round board, 0.25 mm, `h_side` 1000 / 5000 | +3.2 / +2.7 % | +0.1 / +0.2 % | 5 |
| round board, `h_side` 10 (default), 1 mm | -0.3 % | -0.3 % | 5 |
| example board with the five outline presets, `h_side` 10 | | within 0.20 K (T), 0.01 K (the others) | 6 |
| same, `h_side` 100 | | within 0.38 K (ellipse), 0.11 K (T), 0.05 K (the others) | 6 |
| rectangular board, no outline | | bit-identical | 6 |

What changes for the user: results of the 3D solid on a board with an outline that is not on the grid lines, at an edge coefficient from about 100 W/m2K up, move by 1 to 12 K at the cells in use towards the grid-independent value; at the default 10 W/m2K and on a rectangle nothing moves by more than 0.4 K. The 3D solid is a comparison model; the FVM, FDM, Lumped and Analytic are not touched.

## Risks and what to check before adopting

* The scheme is a standard cut-cell finite-volume idea written from scratch; no source was opened for it (README 10). Its energy balance is exact (checked on a turned square to 1e-9) and it reproduces an independent axisymmetric reference on a round board, but patterned copper, vias and metal blocks on the outline were only run in the regression (no independent reference).
* The T board at the default coefficient moves by +0.2 K. *Review*: the cause is not the edge term but a part that crosses the outline (P0 below); with the power of the part on the board part of each cell the program and the copy agree on the T.
* The 45 degree turn keeps +0.5 to +0.7 K at 40 to 80 cells per side; *review*: part of it is the 3D solid's 4 x 4 sampling of the footprint of a part (README 9.3), the rest (+0.44 / +0.18 K at 80 / 160 cells per side against the continuum value, README 9.2) is the board turn and stays with P1.
* A change of the 3D solid changes the numbers of `docs/validation.md` for the outline cases and of the tests that compare the 3D solid with the other models on an outline; the whole battery has to run.
* The 16 x 16 sampling grows the set-up by a sampling pass over every cell (measured nowhere here).

## Alternatives

* **P2, a documented limit instead** (no code change): `docs/validation.md` and `docs/theory.md` say that the 3D solid on an outline that is not on the grid lines depends on the position of the edge by up to 1 to 3 K at `h_side` 100 to 1000 W/m2K and 1 mm cells (and 2 K at 160 cells per side), 0.3 K or less at the default coefficient; the layered models do not show it to that size. The text for the documents is in `docs/for-the-project-documents.md`.
* **P1a, the minimum change** (the edge term only, no new links): the physical conductivity and the distance of the strip (`strip` in the copy) remove about 70 % of the error at 40 cells per side and 60 % at 80 (README 4: 5.78 -> 1.67 K at 40, 3.58 -> 1.43 K at 80), but not the shift invariance; it needs the cell cover only and is a two-line change. Not recommended alone.

## P0, found by the review: the power of a part that crosses the outline (FVM, FDM and 3D solid)

Not part of A3, and a defect of the reference model at the default edge coefficient (README 9.4). The FVM (`fvm.py`, `cov = coverage_fraction(h.polygon, nx, ny, dx, dy, samples=8) * self.active`), the FDM (`fdm.py`, the heater weights around line 246) and the 3D solid (`solid3d.py`, `w = cover(h.polygon, 4) * self.active`) weight a board cell by the part's cover of the whole cell, so where a part crosses the outline the board part of a cut cell gets 1 / cover of the power density. Measured on copies (`rotsq.fvm_part_on_board`, variant `program_part_on_board`) with the weight "part cover times board cover": the example board cut to a T at 1 mm and `h_side` 10 goes from 109.06 to 107.56 degC in the FVM (value at 2/3 mm, where no cell is cut: 106.85) and from 109.31 to 107.79 in the 3D solid (107.08); a small T with the part over the re-entrant corner goes from +0.5 to +7.7 K above its grid-line value to within 0.1 to 0.9 K. The clean form is the sample-wise intersection of the part and the board (one lattice, both tests per sample); a `fix/part-across-outline` branch with a regression test (a part over a re-entrant corner, cut against grid-line cells) and the re-run of `docs/validation.md` 13 (its "T, example" FVM reference 109.1 degC is about 2.2 K high). The FDM was not run with the correction. Smaller, same branch or a separate one: sample the footprint of a part 8 x 8 in the 3D solid, as the FVM does (README 9.3).

## Recommendation of the review

P2 for A3 (README 9.5): the effect needs an outline off the grid lines and a typed `h_side` of about 100 W/m2K or more (default 10, where it is 0.3 K or less); at 1 mm it is +1.1 to +1.8 K (1.6 to 2.7 %) at 100 and about 7 % at 1000 in a comparison model, while the FVM, the reference, is within 0.6 % of its own reference there; P1 rewrites four expressions of the 3D solid, moves every 3D outline number and still leaves 0.2 to 0.5 K at 45 degrees. Keep P1 in 'Planned' as an option. Do P0.

## Decisions for the maintainer

1. P1 (the cut-cell scheme in `solid3d.py`, on a `fix/` branch, with the 3D tests re-measured), P2 (document the limit) or both in order; the review recommends P2.
2. P0 (the power of a part that crosses the outline, in the FVM, FDM and 3D solid): a `fix/` branch, recommended by the review.
3. Whether the FVM and the FDM keep their treatment of the edge (no change proposed: README 7; P0 is a different matter).
4. If P1: a regression test of the program equal to `test_shift_invariance_is_restored_by_the_cut_cells` and the disc against the axisymmetric reference (both exist in `tests/test_rotated_square.py` of this folder and can be copied).
