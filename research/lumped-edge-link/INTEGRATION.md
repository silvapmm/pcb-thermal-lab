# Integration: the first link of the Lumped model near an edge (A27)

Status: a proposal measured on a copy (`lib/variants.py`, variants `first` and `first:zone`); nothing in `pcbthermal/` was changed. Evidence: README 3. **Reviewed (README 4): GO for the adoption below, with the corrections marked 'Review' in this file.**

## 1. Recommendation

**Adopt the correction of the first link as a `fix/lumped-edge-first-link` branch in 2.8.0, in the zone model as well, with the warning re-worded; do not adopt the potential links of ring to ring or the Robin reflection.** The reasons, from the data:

* the deficit of the part read-out is real and large (-9.4 % on average over 432 near-edge cases, -22 % worst; against an independent converged 3D -9.9 % on a part touching a side, -15.9 % in a corner), and the FVM reference is right to 0.2 %;
* the correction takes it to -2.5 % on average (worst cool -8.6 %), the far-from-every-side group from -3.1 to 0.0 %, at no real cost (0.02 to 0.6 s per part);
* its price is that every Lumped record of the frozen boards moves (51 of 51, -0.47 to +3.13 % of the rise, mean +0.67 %, mostly on the hot side) and 14 times (-19.9 to +1.1 %), because a different first link also shifts a centred part by about 2 points (the interior
  factor and the first-ring cap were fitted with the old link): that is a decided change of a model, so the pending file and the reviewer's go are part of the branch;
* what remains: 3 to 7 % cool at a gap of 1 to 5 mm and at a corner 2 to 5 mm (ring-to-ring links), up to +9.4 % hot on 5 of 432 cases at a cooled side (200 W/m2K) in a corner at 0.5 to 1 mm: stated in the warning, not corrected.

**Review** (README 4.2): the gain holds at the 1 mm cell (432 cases: -7.3 to -1.5 % on average, 209 to 2 beyond -8 %); on the 17 frozen boards the correction gives NO net gain against the FVM (mean absolute error of the part peaks 5.04 to 5.17 % at 1 mm), because
an interior part of the example board (U2) read right only by a cancellation of its own -4.8 % with the superposed network of U1 (it reads +4.2 % after the fix, +1.4 % alone); most of the gain away from a side is the chain of the first link, not the
images; the times to 63 % are fixed near an edge and 5 to 9 % short in the interior (safe side for the profile decision). The reviewer's decision (delegated): adopt now, no Robin restriction.

If the maintainer prefers not to move the Lumped numbers, the alternative is **only the re-measured warning** (section 4): the part touching a side is the only case where a smaller change (variant `expo_peak`: 3 frozen records, no time) helps, and it helps only
from -11.3 to -7.2 %.

## 2. What changes in the code (`pcbthermal/lumped.py`, the program's own functions)

Four edits, all in the first link (the exact text is `lib/variants.py` `image_source("first")` and `zone_patch`):

1. `_footprint_potentials(cov, dx, dy)`: the logarithmic potentials of the footprint (mean, boundary, minimum) include the eight mirror images in the sides of the board (one tiling, weight 1 each); cell-resolved up to 3600 cells (the earlier
   limit was 900 with block potentials and no image; above 3600 cells the plain potentials remain, the correction is then not applied: a 30 mm part at 0.5 mm is 3600 cells, so a larger part keeps the old behaviour, to be stated).
2. a new `_ring1_potential(cov, dx, dy, ny, nx, mask)`: the mean over the cells of ring 1 of `U(x) = mean over the footprint cells and the images of ln |x - source|`, floor 0.447 cell, at most 900 source cells (weights rescaled),
   the images weighted 1 (insulated side).
3. in `_one_node_network`: `link_resistance(l, 0) = f_r[l] max(phi_bnd - phi_mean, 1e-3) / (2 pi S_0) + max(U1 - phi_bnd, 0.1 half_k1 2 pi S_1) / (2 pi S_1)` in place of `... + half_k1` (the floor keeps the link positive when ring 1 is thinner than a cell);
   the peak term keeps its formula, but its value changes through the image potentials of item 1 (Review: this file said 'unchanged').
4. in `_zone_network`: the A to ring 1 link `annulus_out_resistance(...) + half ring` becomes `annulus_out_resistance(...) + max(U1 - phi_bnd, floor) / (2 pi S_2)` with `phi_bnd` the boundary potential of the whole footprint with the images and `U1` the mean over ring 1 (node 2).

Nothing else: the ring construction, the interior factor, the first-ring cap (`a_eq`), the micro peak, the via wells, the boards with a metal block (the block layers use the same first link), the other models. The Lumped on an outline board runs on the equivalent rectangle, whose sides carry the images (the
equivalent-rectangle path gains +3.1 % on `part_across_outline`; its own limit of -28 % is unchanged).

## 3. Test list

* `tests/test_lumped_edge_first_link.py` (new): (a) the mirror symmetry (a part at the left side and its mirror at the right read the same to 1e-9 K); (b) the ring-1 potential equals the brute-force field of the earlier prototype (1e-12) and the analytic potential of one source and its images;
  (c) a part on a side moves by more than 5 points and a part far from every side by less than its measured shift with a margin (Review: the 'less than 3 %' proposed here does not hold: far from every side the shift is +0.1 to +5.3 points at 0.5 mm, -5.7 to +6.3 at 1 mm; take the 100 x 80 mm, 6 mm centred case and the value measured on the branch); run the near-edge tests at 0.5 and 1 mm; (d) a board with no part near an edge (the 17 frozen boards) moves only by the amounts of the new pending file;
  (e) the hot-side bound: no case of the 432 of this study reads more than +10 % hot (the list of cases in `tests/data/`, as `lumped_near_edge_cases.json`); (f) the zoned board of 3.5 at gap 3 and 12 mm reads at least 2 points less cool; (g) the cost: a 30 mm part under 2 s.
* `tests/test_lumped_near_edge.py` (existing): the rates of the warning rule are measured on `tests/data/lumped_near_edge_cases.json` with the old program; they must be re-measured (section 4) and the file regenerated.
* The prototype's own tests are in `research/lumped-edge-link/tests/test_edge_link.py` (9 tests, they pass).

## 4. Warning text (`checks.check_lumped_near_edge`, `docs/validation.md` 35.2)

The rule (gap to the nearest side at most max(1 equivalent side, 5 mm)) stays: on the 432 cases it flags 336, 257 of the 262 that read beyond -8 % with the program; with the correction the flagged parts read -3.0 % on average (6 of 432 beyond -8 %, up to 9 % hot at a cooled side).
**If the correction is adopted** the text changes from "up to 22 % of the rise too cool (about 8 % on average)" to "up to 9 % of the rise too cool (about 3 % on average) and, with a side cooled by more than 100 W/m2K, up to 9 % too hot; a sample, not a bound"; the numbers are those of this study
and must be re-measured on the branch with the program itself. Review, at the 1 mm cell (README 4.2): the flagged cases -9.2 to -2.2 % [-8.5, +6.6], the others -0.6 to +1.0 % [-3.6, +7.0]; quote both cells or the worse. **If it is not adopted**, the text keeps its numbers: they were re-measured here (-11.0 % average flagged on a grid weighted to the edge, -22 % worst; the old text says 8 to 9.5 % and 22 %, the 22 % holds).

## 5. Frozen numbers and the pending file

`tests/regression/data/pending/lumped-part-readout.json` already holds all 51 Lumped steady records (17 boards x 2, 1, 0.5 mm) of the part read-out fix, and no time (`transients: 0`); `test_no_record_or_time_is_in_two_pending_files` forbids the same record or time in two pending files.
The correction moves the same 51 records again and 14 times. So the branch cannot add a second file with the same keys: either (a) it **regenerates `lumped-part-readout.json`** under a combined item (`make_pending.py` with the final numbers, one `why` for both, the part-readout and the first link), or
(b) it writes `lumped-first-link-edge.json` with the 51 records (final numbers, both changes) and the 14 times and **removes the 51 records from `lumped-part-readout.json`**, which then holds no record (delete it), as the 2.6.0 integration did for overlapping files. Recommended: (b), so that each file names one item; the new records
contain both effects (the part read-out is in the program already), so they are the live numbers of the branch. The part-readout's own evidence (`docs/validation.md` 48) is not affected. The shifts to expect, by board, are in README 3.6 (`out/frozen_effect_firstzone.txt`).
If the maintainer takes the alternative of adopting `expo_peak` only: 3 records (`part_across_outline`, +5.59 / +5.59 / +2.46 K), no time; the same rule applies (move them out of `lumped-part-readout.json`).

## 6. Risks

* A centred part moves by about +2 points (hot side): the user's Lumped result of any board changes; stated in the changelog, with the frozen table.
* The images assume an insulated side: at a cooled side in a corner the result can read up to +9.4 % hot (5 of 432 cases, the safe side). A reflection factor was tried (0.8: worse overall) and the Robin estimate failed (too small); not adopted.
* The correction does not reach a footprint of more than 3600 cells (the cell-resolved potentials), nor the ring-to-ring links: a part of 1 to 5 mm from a side is still 3 to 7 % cool.
* The time response of the corrected network (14 times move, -19.9 % for `example_board` U2): Review, against an FVM step response at 0.5 mm, near a side +19.9 to -5.2 % and in a corner +43.4 to +1.7 %, in the interior 5 to 9 % short (centred 6 mm +3.0 to -6.4 %, U2 +12.7 to -9.2 %); the frozen FVM times at 2 mm are not a reference for this.
* On boards with several parts the correction removes the deficit of each part's own network and shows the excess of the superposed networks (U2 above): no net gain on the 17 frozen boards; say so in the changelog.
* The zone model patch (`first:zone`) was measured on one family of dense groups (5 x 5 vias, 8 mm part) only.

## 7. What does not change

`pcbthermal/`, `tests/`, `examples/` and the project documents on this branch; the FVM, FDM, 3D solid and Analytic models; the first-ring cap, the interior factor, the zone decision (`will_be_zoned`), the raster rules (`cell_for`, `small_part_cell`).
