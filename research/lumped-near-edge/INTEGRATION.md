# Integration: the Lumped model near a side or a corner

Status: a proposal, measured on a copy (`lib/variants.py`); nothing in `pcbthermal/` was changed. Reviewed (README 10): go for the merge of the folder; per decision below.

## 1. What was found

* The Lumped reads a part near a side or a corner of the board too cool: on 180 cases (2 to 10 mm parts, gaps 0 to 30 mm, edge film 10 to 200, boards 40 x 40 and 100 x 80 mm) the hottest node is -6.6 % on average
  and as low as -22.0 % (10 mm part in a corner), the footprint mean -5.5 % and as low as -13.5 %; the FVM at 0.25 mm confirms the reference to 0.2 %, and the independent 3D solver confirms the FVM to 0.2 % on
  five cases (README 10.1).
* **The cause is not the clipping of the rings.** Ring areas, contour lengths and the edge loss are already those of the board (README 3.2). The deficit is made in the links from the footprint outwards, mostly the
  footprint-to-ring-1 link, which uses the log potential of the part alone (it lacks the mirror image of the side) and a radial flux that a side pushes away (README 3.2, 10.3).
* The sub-cell spread is a grid effect shared with the FVM (-19 to +6 % at 0.5 mm for parts of 0.1 to 0.5 mm, position dependent); a raster of side / 2 (at least 0.125 mm) removes it (-0.8 to +1.6 %, README 10.4).

## 2. Proposals and the reviewer's recommendation for each decision

1. **Warning (text only, no number moves; a `fix/` for 2.6.0). Recommendation: adopt.** For the Lumped, when the gap of a heat source (polygon) to the nearest side of the board is at most max(its equivalent
   side, 5 mm). The gap is the exact distance from the polygon to the sides of the box, or to the real outline on a board with an outline (0 when the part crosses it), as the rates were measured. It needs only
   the geometry, so it belongs to the **live check** (`checks.check_input`, beside the Lumped via warnings, `_add(out, "heater", k, full, short)`), selected only when the Lumped runs. Proposed text (full, then short):

   ```text
   {name}: the part is {gap:.1f} mm from a side of the board; the Lumped model reads a part near a side or a corner of the board too cool, because its rings
   around the part do not see the side that sends the heat back: on 300 test boards the hottest temperature of such parts read up to 22 % of the rise too cool
   (about 8 % on average, most at a corner); a sample, not a bound; use the FVM or the FDM.
   ```

   ```text
   {name}: near a side of the board; the Lumped model reads it too cool (up to 22 % of the rise at a corner); use the FVM.
   ```

   Rates (bad = more than 8 % too cool on the hottest node): 57 of 58 on the sweep, 35 of 37 on 120 random boards (63 and 24 false alarms, mostly 4 to 8 % too cool), 2 of 2 near-edge boards of the 17 frozen boards and
   one false alarm (`example_cut_to_T`, -2.1 %). The threshold is the knee of the measured table (README 10.5). Add the case to the warning-text tests (no research or branch names in the text) and to the help.
   On an outline board the warning of the equivalent rectangle already fires; whether both are shown is the maintainer's choice of text. Impact: none on a number.
2. **Raster refinement for small parts (a `feature/`; moves only the Lumped numbers of boards with a part under two cells). Recommendation: adopt in 2.6.0 only together with a memory guard for the Lumped**:
   `lumped.cell_for` refines the raster to side / 2 (not below 0.125 mm) when a heat source is smaller than two cells. Measured -0.8 to +1.6 % on 15 cases against the FVM at 0.0625 mm. Cost about 1.7 KB per raster
   cell (0.97 GB and 0.5 s at 0.125 mm on 100 x 80 mm, 2.1 GB on 150 x 120 mm with 100 vias; about 3.3 GB on 200 x 150 mm and 6.5 GB on 300 x 200 mm, extrapolated). The raster is one per board, so one 0402
   part refines the whole board, and `memory.py` does not check the Lumped today: the guard (or a coarser floor when the board is large, which the study has not measured) must come first. **Frozen numbers: none
   moves** (the smallest source of the 17 boards is 6 mm). The other parts of a refined board move with the raster (not measured; the same effect as the zone raster). Until then, the warning that a part below
   two cells reads -19 to +6 % depending on its place in the cell is a text-only option.
3. **Image and potential links (a `feature/`, moves frozen Lumped numbers). Recommendation: do not adopt yet; keep A23 open.** After the review's correction of the candidate (README 10.2: a fallback without
   images above 900 footprint cells had made a 20 mm part 2 to 3 points cooler at the centre and -31 % in a corner) it reads the sweep -6.6 to -1.7 %, 120 random boards -5.9 to -2.4 % (beyond -8 %: 31 % to 1 %),
   centred parts -1.1 to +0.0 %, and moves the 17 frozen boards by -0.3 to +2.2 points of the board maximum. **Against it**: its centred agreement is a compensation of its two links (+1.9 % and -2.3 % alone on a
   5 mm part, README 10.3), the large lossy plate of Seri Lee keeps -14 to -17 % on the mean near a side (the image alone is better there), the outer rings read 4 to 7 % low (the temperature that the part causes
   at a neighbour was not measured), a cooled side (200 W/m2K) reads up to +8.6 % hot (no Robin image), and the outline boards are not touched. Next steps before a second review: recalibrate the interior-link factor
   and the first-ring cap with the new links (or keep the program's ring links and change only the first link, which carries most of the gain), a Robin image for a cooled side, the neighbour temperature, and a run on
   boards with vias and zoned footprints.

The Analytic model (within 0.5 % of the exact plate near an edge, published-cases-followup 7) is the answer for a user who needs an edge result on uniform copper today; the FVM and the FDM in every case.

## 3. What does not change

Nothing in `pcbthermal/`, `tests/`, `examples/` or the project documents on this branch. The models other than the Lumped are untouched; the FVM, FDM, 3D solid and Analytic follow the images by construction.

## 4. Frozen numbers

The prototype was not run through `tests/regression`. Proposal 1 moves nothing. Proposal 2 moves no record of the 17 boards (no source under 1 mm). Proposal 3 moves every Lumped record by up to about 2 points of the
board maximum (README 6.1, after the correction); a pending file would be needed (`tests/regression/make_pending.py`).

## 5. Open doubts after the review

* Is the potential link right for a ring whose mean `S` differs between rings (partial copper)? Checked only on the 17 boards and the random boards with fill 0.4 to 1 (uniform).
* The "bad" threshold (8 %) and the false-alarm counts depend on the deficit that the tree has far from a side (-2 to -4 %): the first-ring branch is in the tree under test, `develop` has more.
* The sweep has the part centred along the side for the edge case; a part near a side but off-centre along it was only sampled by the random boards.
* The sub-cell spread and the near-edge deficit were run on the Lumped at 0.5 mm; at 1 mm (the Lumped's other allowed raster) the numbers were not run.
* The review's question "is the 20 mm worsening the 64-cell sample?" is answered: no, it was the fallback of README 10.2 (corrected).
