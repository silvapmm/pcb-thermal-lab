# Surface flag: which length of the source governs t/a (item e13 of 2.9.0)

Branch `fix/surface-flag-narrow-part`, from `development` b80d2b71. Scripts: `scripts/study_flag_rule.py` (about 35 s) and, added in the review, `scripts/study_exact_series.py` (exact cosine series, about 10 s). Reference: `tests/helpers/layered3d.py` (independent 3D layered solver, imports nothing from `pcbthermal`), 50 x 50 mm plate, 0.5 mm cells, 8 sub-slabs, bottom film 400 W/m2K, top insulated, centred rectangle b x c (b the narrow side).

True term = surface minus column mean at the source centre (as `research/through-thickness-readout/scripts/study_sweep.py`). Prediction = `thickness.offsets` with the program's fluxes (q = P/A, film through the half layer). A case overshoots when prediction / true > 1.07 (the 7 % tolerance quoted for the parabola up to t/a 0.5). A rule flags when t/a > 0.5.

| k W/mK | t mm | b x c mm | t/b | t/sqrt(bc) | parabola / true | overshoot > 7 % | flag, narrow side | flag, sqrt(A) |
|--|--|--|--|--|--|--|--|--|
| 385 | 1.0 | 2 x 20 | 0.50 | 0.16 | 1.028 | False | False | False |
| 385 | 1.0 | 2 x 10 | 0.50 | 0.22 | 1.028 | False | False | False |
| 385 | 1.0 | 5 x 10 | 0.20 | 0.14 | 0.993 | False | False | False |
| 385 | 1.0 | 10 x 10 | 0.10 | 0.10 | 0.993 | False | False | False |
| 385 | 2.0 | 2 x 20 | 1.00 | 0.32 | 1.149 | True | True | False |
| 385 | 2.0 | 2 x 10 | 1.00 | 0.45 | 1.150 | True | True | False |
| 385 | 2.0 | 2 x 40 | 1.00 | 0.22 | 1.148 | True | True | False |
| 385 | 2.0 | 3 x 10 | 0.67 | 0.37 | 1.058 | False | True | False |
| 385 | 2.0 | 4 x 20 | 0.50 | 0.22 | 1.021 | False | False | False |
| 385 | 2.0 | 5 x 10 | 0.40 | 0.28 | 1.006 | False | False | False |
| 385 | 2.0 | 5 x 20 | 0.40 | 0.20 | 1.006 | False | False | False |
| 385 | 2.0 | 10 x 10 | 0.20 | 0.20 | 0.994 | False | False | False |
| 385 | 2.0 | 10 x 20 | 0.20 | 0.14 | 0.994 | False | False | False |
| 385 | 2.0 | 20 x 20 | 0.10 | 0.10 | 0.994 | False | False | False |
| 385 | 3.0 | 5 x 10 | 0.60 | 0.42 | 1.043 | False | True | False |
| 385 | 3.0 | 4 x 20 | 0.75 | 0.34 | 1.075 | True | True | False |
| 150 | 2.0 | 2 x 20 | 1.00 | 0.32 | 1.149 | True | True | False |
| 150 | 2.0 | 5 x 10 | 0.40 | 0.28 | 1.007 | False | False | False |
| 150 | 2.0 | 10 x 10 | 0.20 | 0.20 | 0.994 | False | False | False |

Agreement of the flag with the measured overshoot: narrow side 17/19, sqrt(A) 14/19 (re-run in the review: the same table and score).

## Reading

* The ratio depends on the narrow side only: 2 x 10, 2 x 20, 2 x 40 mm on 2 mm all give 1.149 to 1.150; 5 x 10 and 5 x 20 both 1.006; 10 x 10 and 10 x 20 both 0.994. The long side does not enter once it is 3 times the narrow one or more (all the rectangles of the table are; a shorter part overshoots more, up to the square: see the exact series below). The conductivity does not either (150 and 385 W/mK give the same ratios at the same geometry, as the term scales with 1/k).
* sqrt(A) (the former rule) misses 5 real overshoots: 2 x 10, 2 x 20, 2 x 40 on 2 mm, 4 x 20 on 3 mm, and 2 x 20 at 150 W/mK (+15 % to +7.5 %).
* The narrow side misses none. The two cases where it flags and the overshoot is below 7 % (3 x 10 on 2 mm: 1.058; 5 x 10 on 3 mm: 1.043) are at t/b 0.6 to 0.67, on the safe side: the 0.5 threshold, measured on squares, is slightly early for these. The rows at t/b = 0.5 exactly (1.021, 1.028) are not flagged and are inside 7 %.
* The geometric mean is not the length of the problem (a rectangle 2 x 40 has the same overshoot as 2 x 10 although sqrt(A) differs by a factor 2).

## Second reference: the exact cosine series (review)

`scripts/study_exact_series.py` (about 10 s) solves the same plate as an exact double cosine series (top insulated except the source, film 400 W/m2K below, adiabatic edges; surface, column mean and bottom of every mode in closed form; nothing shared with the finite volumes). The parabola is `thickness.offsets` with the exact fluxes.

* **The table above holds.** The 19 rectangles give the same overshoot / no-overshoot verdict as the 3D solver; the series reads 0.003 to 0.008 higher (1.000 instead of 0.994 for the wide parts, 1.153 instead of 1.149 for 2 x 20 on 2 mm, 1.082 instead of 1.075 for 4 x 20 on 3 mm: the 3D solver's 0.5 mm cells and 8 sub-slabs), and 1500 and 3000 modes agree to 0.0002.
* **The threshold.** The ratio crosses 1.07 at about `t/a` 0.55 for a square (1.052 at 0.5, 1.069 at 0.55, 1.088 at 0.6) and at about 0.70 for an infinite strip of width `a` (1.026 at 0.5, 1.069 at 0.7, 1.081 at 0.75). So 0.5 is early for every rectangle, by a little for a square and by more for a long strip: the flag errs early, never late. The two early flags of the table (3 x 10 on 2 mm, 5 x 10 on 3 mm) are this margin.
* **The long side.** At a fixed narrow side the overshoot falls as the part gets longer and is flat beyond about `c` = 3 `b`: at `t/b` = 1, 1.284 (square), 1.203 (`c/b` 1.5), 1.174 (2), 1.157 (3), 1.154 (5), 1.151 (20). So "the long side does not enter" holds for `c` of 3 `b` or more; below that a shorter part overshoots MORE, which the narrow side (the square's own side) still flags at the same `t/b`. The worst rectangle at a given `b` is the square.
* **Non-rectangular parts, and a defect of the first version of the fix.** The minimum width of the convex HULL bridges the notch of a concave part. An L of 2 mm arms (20 mm long) on 2 mm copper has a hull 8.7 mm wide and `sqrt(A)` 8.7 mm, so the first version gave `t/a` 0.23 and no flag, while the exact series reads 1.193 (U of 2 mm arms: 1.165; L of 3 mm arms: 1.107). That was a late flag, the wrong direction. **Corrected in the review**: `source_width` is now the smallest of the hull width, `sqrt(A)` and the narrowest local width of the polygon itself (`thickness._local_width`: chords cast inwards, normal to each edge, from three points of every edge; a chord that runs outside the part, through the slit of a keyhole outline, or is shorter than a millionth of the size, is ignored).

| part on 2 mm copper, k 385 W/mK | t/sqrt(A) | t/a, a = source_width | exact parabola / true | overshoot > 7 % | flag |
|--|--|--|--|--|--|
| L, arms 2 x 20 mm | 0.23 | 1.00 | 1.193 | True | True |
| L, arms 3 x 20 mm | 0.19 | 0.67 | 1.107 | True | True |
| L, arms 4 x 20 mm | 0.17 | 0.50 | 1.056 | False | False |
| U, arms 2 x 20 mm | 0.19 | 1.00 | 1.165 | True | True |
| strip 2 x 20 mm at 45 deg | 0.32 | 1.00 | 1.153 | True | True |
| strip 2 x 20 mm at 17 deg | 0.32 | 1.00 | 1.153 | True | True |
| disc d 4 mm | 0.56 | 0.56 | 1.070 | True | True |
| disc d 3 mm | 0.75 | 0.75 | 1.151 | True | True |
| 10 x 10 mm square with a 1 x 4 mm tab | 0.20 | 2.00 | 1.001 | False | True (early) |

For the non-rectangular parts the ratio is the hottest parabolic surface minus the hottest column over the part, against the same for the exact surface. Every overshoot is flagged. The cap by `sqrt(A)` is needed: a disc's width `d` alone would leave the 4 mm disc (`t/d` 0.5, ratio 1.070) unflagged. The price of the local width is an early flag for a compact part with a thin appendage (the square with a tab: the tab, 1 mm wide, sets `a`, although the hottest point, in the square, does not overshoot).

**The program on the same plate** (FVM, 0.5 mm cells, 10 W, same table of the script): the L of 2 mm arms reads a surface term of 0.232 K against 0.194 K exact (1.19 times; column maximum 11.897 against 11.890 K of rise), the 2 x 20 mm strip at 45 deg 0.439 K against 0.379 K (1.16 times; column 12.532 against 12.513 K); both are flagged on the corrected tree. The column of the program agrees with the series to 0.02 K, so both sides model the same board.

## Rule chosen

`a = min(minimum width of the convex hull, narrowest local width of the polygon, sqrt(A))`, `t/a > 0.5`; the local width is taken only for a concave part (a convex part is its own hull, and the chords of a triangle would be shorter than its width), so every convex part keeps the hull rule. For a rectangle (any orientation) this is `b`; for a square its side (nothing changes); for an L or a U the width of the narrowest arm; the cap by `sqrt(A)` means a part whose width exceeds its equivalent side (a disc: d against 0.886 d) keeps exactly the former flag, so no flag raised before is lost (every term is at most `sqrt(A)`). `thickness.source_width` implements it.

## No number moves

`scripts/study_regression_set.py` solves the 20 boards of `tests/regression/regress_boards.py` (FVM and FDM, 2 mm cells, 23 parts) on `development` and on the fix: `T_surface` and `T_surface_mean` are bit-identical on all 40 runs, 0 parts and 0 cells change flag, also with the local width added in the review (re-run: 0 runs and 0 cells change; every part sits on 35 um copper, t/a is far below 0.5 by either rule, so the regression set cannot show the change; the new tests do). The frozen records (`tests/regression/data/v2.8.0.json`) store surface statistics, never the flag, so the frozen test cannot see the flag.

## Not verified

Other bottom films than 400 W/m2K, thicknesses above 3 mm, thick plates with sources near an edge, sources on both faces, parts on a multilayer board (the shapes were measured on a one-layer plate), the FEM (its flag is always False: it resolves the face). A part with a real hole cannot be drawn as one polygon; a keyhole outline is handled (tested) but its overshoot was not measured. The local width is taken from chords at three points of every edge: a staircase outline (many short steps) would give short chords near its rim and flag early.
