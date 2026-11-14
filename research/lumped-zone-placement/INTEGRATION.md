# Integration: the zoned Lumped footprint and its position on the raster (A46)

Nothing here is implemented in the program. Everything was measured on a copy (`lib/placement.py`, monkeypatches inside a context manager); `pcbthermal/`, `tests/`, `examples/` and the project documents are untouched.

## 0. Recommendation of the review (README 10)

* **No model change in 2.8.0.** R1 (section 1) is not adopted: end to end it moves no frozen number, keeps the mean absolute error (2.6 to 2.7 points at the shifted placements) and halves the largest placement spread (10.7 to 6.0 points), but it makes the worst cool (unsafe) case cooler (-7.2 to -8.8 %) and makes a new decision flip at a core share of 0.77, near its own threshold. The 0.25 mm zone raster is not adopted: it removes most of the noise but moves the level 1.3 to 2 points cooler, away from a converged independent 3D, and `plate_vias` 2.68 K cooler. The zones are not dropped for dense groups: as shipped they are the closest of the three readings to the converged 3D on the boards measured (-0.8 to +0.8 %), and one node, on the safe side, is +2.5 to +3.1 %.
* **Next step: documents only**, a branch `docs/lumped-zone-placement-limits` off `development`, small (a paragraph in each of `docs/theory.md` 5.2 'Limits' and `docs/validation.md` 48 or a new section, and a line in `docs/versions.md`): (1) the zoned reading of a dense group depends on where the part and the array fall on the 0.5 mm raster, 1 to 3 points of the part peak (up to 10.7 points on one case through a decision flip); (2) with its own raster converged the zone construction reads the peak 1.7 to 2.4 % cool against an independent 3D converged at 0.0625 mm, and the 0.5 mm raster adds +1.6 to +2.4 points, so the raster is part of the calibration and must not be refined alone; (3) one node reads +2.5 to +3.1 %. No code, no test, no warning text change (the cases measured here are covered by the existing Lumped via warnings; README 10.2), no pending file: `lumped-part-readout.json` (51 records) is untouched.
* **A27** goes ahead on its own Lumped `fix/` branch, measured on the program as it ships (boards without vias, or the aligned placement with the 1 to 3 point noise stated); if a later change of the zones is ever wanted, it goes in that same branch, after A27, and its moved records leave `lumped-part-readout.json` for the branch's own pending file (one record in one file).
* For the maintainer: whether to state the converged cool level of the zones as a limit only (recommended) or to reopen the zone construction (fractional node weights, untested) in a later version.

## 1. Rule R1 as proposed by the study (not adopted, see section 0)

In `lumped.py`:

1. **Membership.** In `_core_mask`, a via counts for its group when its position is in the footprint, tested on the closed boundary of the touched cells with a 1 micrometre tolerance (or better, on the heater polygon with the same tolerance): not by the cell that holds it having coverage above zero.
2. **Core mask.** A cell is core when at least half of its sub-grid of 0.1 mm lies within `CORE_R d_nn` of a via position of the group (area vote); no seed cell, no `distance_transform_edt`. `_fine_core_share` becomes the same vote with the coverage weights (the replicated-cell kron goes away).
3. **Gate.** In `_heater_network`, `n_core < n_foot and n_core <= MAX_CORE * n_foot` becomes the coverage-weighted share (a sliver of the footprint counts by its area): `share < 1 and share <= MAX_CORE`.
4. **Threshold.** `MAX_CORE` 0.8 on that exact share (flat optimum 0.6 to 0.92 on the 66 cases; 0.8 separates the thin-A regime, exact share 0.83 to 0.91, from the dense groups, 0.44 to 0.67).

**Measured effect** (README 4, 6): no frozen Lumped record moves (12 records, one time); 66 cases at four placements: mean absolute peak error 1.52 against 1.51 at the aligned placement, 2.64 to 2.67 against 2.59 to 2.81 elsewhere; the largest spread of one case over the placements 6.0 against 10.7 points; the vias-on-the-edge board range 13.1 to 3.6 points and no +4 to +10 % hot placement. **It does not remove the 2 to 3 point quantisation noise of the dense groups at 0.5 mm.**

**Tests it needs**: a test that the exact core share is invariant (1 %) under sub-cell translation for a 5 x 5 array under an 8 mm part; that the decision does not flip across 0.0625 mm shifts of a board whose vias lie on the part edge; the old frozen numbers (no record moves); one test per mask on the symmetry of a centred array.

**Documents if adopted**: `docs/theory.md` 5.2 (the membership and the share, the 0.92 sentence becomes 0.8 on the exact share), `docs/validation.md` 31 and 42/48 (the placement noise as a stated limit: 1 to 3 points of the part peak at 0.5 mm).

## 2. Options for the noise itself (a decision for the maintainer, with the reviewer)

| option | noise (range over the 22 placements) | level against the independent 3D | cost and frozen risk |
| :-- | :-- | :-- | :-- |
| R1 at 0.5 mm (above) | 1.1 to 2.9 points | +0.5 to -1.6 % against the 3D at 0.25 mm (raster bias) | none; no record moves; a new decision flip at share 0.77 (README 10.3) |
| R1 with zone raster 0.25 mm | 0.8 to 1.1 points (3D shifts 0.26 to 0.37) | -1.3 to -2.5 % | 4 times the cells (Lumped is light); moves `plate_vias|lumped` at 2, 1, 0.5 mm by 2.68 K and its time to 63 % (30.94 to 33.10 s); `lumped-part-readout.json` must give those 3 records and 1 time to the new file |
| fractional node weights | expected to approach the 0.125 mm column (0.4 to 0.9) | -2.0 to -2.8 % (against the converged 3D: -1.5 to -2.4 %, README 10.2) | rewrite of `_zone_network` sums and `viaconstriction.ring_couplings`; not built |
| drop the zones, keep one node | 0.3 to 0.6 points | +2.1 to +2.9 % (converged 3D: +2.5 to +3.1 %; safe side) | moves every zoned record (not measured here) and contradicts the earlier decision to adopt the zones |

**Finding to weigh**: against the raster-free reference the converged zones read -2.0 to -2.8 %, one node +2.1 to +2.9 %: the zones are not closer than one node once the raster is converged, and they are on the unsafe side. The earlier conclusion that the zones read the peak 'closer' rests on the 0.5 mm raster's positive bias (README 5). The study first recommended R1; the review (section 0, README 10) recommends no model change and the statement of the noise and of the converged level as limits.

## 3. The single Lumped branch (A46 + A27)

* The two items are additive and separable (README 7): the zoned minus one-node offset changes by 2 points between 3 and 25 mm from a side and the placement noise does not grow near the edge. Order: A46 first (R1, optionally the 0.25 mm zone raster), then A27 measured on the fixed zones, so that a 2 to 5 point A27 gain is not blurred by a 1 to 3 point placement noise.
* **Pending file rule.** `tests/regression/data/pending/lumped-part-readout.json` already holds all 51 Lumped records of the 17 boards at three cells and its times. A later Lumped fix takes its moved records out of that file into its own, or regenerates that one file under the combined item (`test_no_record_or_time_is_in_two_pending_files`). R1 alone moves none; the 0.25 mm raster would take three records and one time; A27's records come from its own study. One Lumped branch, not two in parallel.
* Memory: the Lumped with a 0.25 mm zone raster on a 100 x 80 mm board has 4 times the cells (`lumped.small_part_cell` and the zone raster `ZONE_CELL_MM` interplay: a board with a part narrower than two cells already gets a finer raster); the guard of that function (1.7 KB per cell, 1 GB) would need to cover it.

## 4. What does not change

Nothing in the program, the tests, the examples or the documents. The research tests: `python -m pytest research/lumped-zone-placement/tests -q` (4 tests).
