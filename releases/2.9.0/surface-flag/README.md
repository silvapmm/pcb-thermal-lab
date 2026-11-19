# Surface flag: which length of the source governs t/a (item e13 of 2.9.0)

Branch `fix/surface-flag-narrow-part`, from `development` b80d2b71. Script: `scripts/study_flag_rule.py` (about 25 s). Reference: `tests/helpers/layered3d.py` (independent 3D layered solver, imports nothing from `pcbthermal`), 50 x 50 mm plate, 0.5 mm cells, 8 sub-slabs, bottom film 400 W/m2K, top insulated, centred rectangle b x c (b the narrow side).

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

Agreement of the flag with the measured overshoot: narrow side 17/19, sqrt(A) 14/19.

## Reading

* The ratio depends on the narrow side only: 2 x 10, 2 x 20, 2 x 40 mm on 2 mm all give 1.149 to 1.150; 5 x 10 and 5 x 20 both 1.006; 10 x 10 and 10 x 20 both 0.994. The long side does not enter. The conductivity does not either (150 and 385 W/mK give the same ratios at the same geometry, as the term scales with 1/k).
* sqrt(A) (the former rule) misses 5 real overshoots: 2 x 10, 2 x 20, 2 x 40 on 2 mm, 4 x 20 on 3 mm, and 2 x 20 at 150 W/mK (+15 % to +7.5 %).
* The narrow side misses none. The two cases where it flags and the overshoot is below 7 % (3 x 10 on 2 mm: 1.058; 5 x 10 on 3 mm: 1.043) are at t/b 0.6 to 0.67, on the safe side: the 0.5 threshold, measured on squares, is slightly early for these. The rows at t/b = 0.5 exactly (1.021, 1.028) are not flagged and are inside 7 %.
* The geometric mean is not the length of the problem (a rectangle 2 x 40 has the same overshoot as 2 x 10 although sqrt(A) differs by a factor 2).

## Rule chosen

`a = min(minimum width of the part, sqrt(A))`, `t/a > 0.5`. For a rectangle (any orientation) the minimum width is b; for a square it is the side (nothing changes); the cap by sqrt(A) means a part whose width exceeds its equivalent side (a disc: d against 0.886 d) keeps exactly the former flag, so no flag raised before is lost. `thickness.source_width` implements it (convex hull, minimum over the hull edges).

## No number moves

`scripts/study_regression_set.py` solves the 20 boards of `tests/regression/regress_boards.py` (FVM and FDM, 2 mm cells, 23 parts) on `development` and on the fix: `T_surface` and `T_surface_mean` are bit-identical on all 40 runs, 0 parts and 0 cells change flag (every part sits on 35 um copper, t/a is far below 0.5 by either rule, so the regression set cannot show the change; the new tests do). The frozen records (`tests/regression/data/v2.8.0.json`) store surface statistics, never the flag, so the frozen test cannot see the flag.

## Not verified

Non-rectangular parts (L, discs: only the cap by sqrt(A) is argued, not measured), other bottom films than 400 W/m2K, thicknesses above 3 mm, thick plates with sources near an edge, the FEM (its flag is always False).
