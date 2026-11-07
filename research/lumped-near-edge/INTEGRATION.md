# Integration: the Lumped model near a side or a corner

Status: a proposal, measured on a copy (`lib/variants.py`); nothing in `pcbthermal/` was changed; the reviewer has not yet checked it.

## 1. What was found

* The Lumped reads a part near a side or a corner of the board too cool: on 180 cases (2 to 10 mm parts, gaps 0 to 30 mm, edge film 10 to 200, boards 40 x 40 and 100 x 80 mm) the hottest node is -6.6 % on average
  and as low as -22.0 % (10 mm part in a corner), the footprint mean -5.5 % and as low as -13.5 %; the FVM at 0.25 mm confirms the reference to 0.2 %.
* **The cause is not the clipping of the rings.** Ring areas, contour lengths and the edge loss are already those of the board (README 3.2). The deficit is made in the links from the footprint outwards: the
  interior link uses the log potential of the part alone (it lacks the mirror image of the side), and circle-shaped rings are crossed by a flux that a side pushes away from it, so
  `thickness / (S length)` is too small.
* The sub-cell spread is a grid effect shared with the FVM (-19 to +6 % at 0.5 mm for parts of 0.1 to 0.5 mm, position dependent); a raster of side / 2 (at least 0.125 mm) removes it to -3 % (README 3.3).

## 2. Proposals, in the order the maintainer may take them

1. **Warning (text only, no number moves; a `fix/`)**. For the Lumped, when the gap of a heat source (polygon) to the nearest side of the board (the equivalent rectangle on a board with an outline) is at
   most max(its equivalent side, 5 mm): "may read 5 to 20 % too cool near a side of the board (more at a corner); a sample of 180 cases and 120 random boards, not a bound; use the FVM or the FDM". Measured
   rates (bad = more than 8 % too cool on the hottest node): 57 of 58 on the sweep, 35 of 37 on 120 random boards (24 and 63 false alarms: the alarm fires where the deficit is 4 to 8 %), 2 of 2 near-edge boards of the
   17 frozen boards, one false alarm. Place: `checks.py` after the run (it needs the gap on the model's rectangle), text in the style of the existing Lumped limit warnings; add the case to the tests of
   the warning texts. Impact: none on a number.
2. **Raster refinement for small parts (a `feature/`; moves Lumped numbers of boards with a part under two cells)**: `lumped.cell_for` refines the Lumped raster to side / 2 (not below 0.125 mm) when a part is
   smaller than two cells. Cost 0.2 s and 0.84 GB (process peak) for a 0.5 mm part on 100 x 80 mm; the board of a very small part with a large area needs a cell-count guard (memory guard). Measured on 21
   cases only (README 3.3): needs the same check on the 17 frozen boards and a decision for the raster per board (the zoned boards already force 0.5 mm).
3. **Image and potential links (a `feature/`, only after a second review; moves frozen Lumped numbers)**: replace the ring-to-ring links and the footprint potentials by the log potentials of the part plus the
   mirror images in the sides (`lib/variants.py`, variants `image` and `potlinks`, about 70 lines). Measured: part-sized sources near a side: hottest node -6.6 to -1.7 %, 120 random boards -5.9 to -2.4 %
   (beyond -8 %: 31 to 1 %); centred parts -1.1 to -0.7 %. **Against it**: it does not fix Seri Lee's plate (25 mm source: -15 to -17 % remain on the mean), a 20 mm part gets 2 to 3 points worse, the outer rings
   read 4 to 7 % low, a cooled side (200 W/m2K) makes it read up to +8.6 % hot, and the outline boards (where the near-edge errors are -16 and -32 %) are not touched. Its frozen-number impact: the Lumped
   records of the 17 boards move by -2.1 to +1.0 points of the board maximum, `reference_board` by -2.1 (-1.2 to -3.3 %). My recommendation: **take proposal 1 now, proposal 2 after the frozen check, and
   leave proposal 3 in the register until a Robin image, the large-source case and the neighbour temperature have been studied**; the Analytic model (within 0.5 % of the exact plate near an edge, published-cases-followup 7) is
   the answer for the user who needs an edge result today.

## 3. What does not change

Nothing in `pcbthermal/`, `tests/`, `examples/` or the project documents on this branch. The models other than the Lumped are untouched; the FVM, FDM, 3D solid and Analytic follow the images by construction.

## 4. Frozen numbers

The prototype was not run through `tests/regression`. Proposal 1 moves nothing. Proposal 2 moves the Lumped records of boards that have a part under two cells (none of the 17 has one under 2 mm at 2 mm cell:
to be checked). Proposal 3 moves every Lumped record by up to 3 points (the 17-board table, README 6.1); a pending file would be needed (`tests/regression/make_pending.py`).

## 5. Doubts of the author, for the reviewer

* Is the potential link right for a ring whose mean `S` differs between rings (partial copper)? It was only checked on the 17 boards and the random boards with fill 0.4 to 1 (uniform).
* The footprint of more than 64 cells is sampled (every n-th cell, weights rescaled): this may be what makes the 20 mm part worse; not isolated.
* The "bad" threshold (8 %) and the false-alarm counts depend on the deficit that the tree has far from a side (-2 to -4 %): the first-ring branch is in the tree under test, `develop` has more.
* The sweep has the part centred along the side for the edge case; a part near a side but off-centre along it was only sampled by the random boards.
* The sub-cell spread and the near-edge deficit were run on the Lumped at 0.5 mm; at 1 mm (the Lumped's other allowed raster) the numbers were not run.
