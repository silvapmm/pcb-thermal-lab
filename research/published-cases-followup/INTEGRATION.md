# Integration: what the five checks would change in the program and in its documents

Nothing in `pcbthermal/`, `tests/`, `examples/` or `ico/` was edited; every proposal below was measured on the program as it is (`develop` at `fc91174a`) through its public API. Recommendations are for the maintainer; a change to a model goes on a `fix/` or `feature/` branch with the whole battery.

## 1. The Lumped model near an edge or a corner (measured, proposal)

**Measured** (README 7; the plate of Seri Lee, 100 x 100 x 1.3 mm aluminium, 25 mm source, exact thin-plate series as reference): on the mean temperature of the footprint the Lumped reads -5.3 % at the centre, -17.9 % at the edge midpoint, -21.6 % at the corner, -19 to -24 % at gaps of 2 to 6 mm from the edge or corner, recovering to -9 % at a gap of one source side (24 mm). The extra -13 to -17 points over the centre is the edge image that the ring network does not have. The FVM, FDM, 3D solid and Analytic follow the exact images to 0.5 % (FDM 1.6 % on the footprint mean) at every distance.

**Caveat.** One plate (high conductivity, large source on a small board), not a copper-and-laminate PCB. The size of the effect on a typical PCB is not measured here.

**Recommendation.** (a) A second measurement on two or three PCB-like boards (4-layer, partial copper) with the same sweep before any code change; (b) a warning text for the Lumped when a part lies within about one part side of a board edge or corner, quoting the measured range and "a sample, not a bound" (text only, like the existing via warnings), after (a); (c) a correction of the ring network (an image term, or the Analytic's cosine modes for the first ring) only after the maintainer decides; no candidate was prototyped here, so no impact number exists for a fix.

## 2. Via arrays in the FVM and FDM: -6 to -8 % of the array resistance (measured, open)

**Measured** (README 6.3): on n x n arrays under a uniform flux with a fixed bottom, the FVM reads the array resistance 6 to 8 % low for air-filled vias (2 to 7 % for solder, -2.0 % at phi 0.8 mm), grid-converged (-6.2, -7.4, -7.7, -7.6, -7.7 % for the cell pitch/2, /3, /4, /6, /9), the board without vias exact to -0.013 %; the FDM -4 to -9 %, the 3D solid -1 to -7 %. The reference was checked: the axisymmetric unit cell (equal-area disc) and a Cartesian 3D square cell agree to 0.1 to 0.5 %. Of the difference between Shen's paper cell and the layered idealisation about 2 % is explained (copper planes continuous over the drill, the heat over the whole top: `lib/via_cell.py`); the remaining -6 % in the FVM is the model. This is the non-conservative side: an array reads better than it is. It is the same order as the "-2.1 to +3.9 %" of the single-via calibration (`docs/theory.md` 2.6) but with a different sign and larger, so a dense array is outside that calibration.

**Not found.** Whether the cause is the footprint rule (a footprint enlarged to a lattice radius of 0.78 r_v covers a large share of a 3-cell pitch), the log kernel at that pitch, or the coupling of the plane to the barrel.

**Recommendation.** An investigation on its own branch before any change: vary the pitch in cells (p/3 to p/9 at fixed physical footprint), isolate the footprint rule by using a point well in a single-cell array, and compare with `lib/via_cell.py`/`lib/cart_cell.py`. Until then a sentence in the via text of the user guide and `docs/validation.md` 18: "in a dense array (pitch under about 4 via diameters at full copper) the FVM reads the resistance 6 to 8 % low against an independent unit cell". Open decision for the maintainer: whether to treat this as a defect (fix branch) or a documented limit.

## 3. Thick laminate under a small source: the layered models and the 3D solid (measured, documented limit)

README 3.3 and 5.3: for t/c >= 0.5 on bare laminate the layered models lose the through-thickness spreading (FVM and FDM -36 to -44 % of psi at t/c = 3, -4 % at 0.5), sixteen sub-gaps bring the FVM to -7 to -9 %, the 3D solid at its default four slabs is +66 to +96 % at t/c = 3 (+6 to +11 % with sixteen), the Lumped and Analytic -84 to -96 %. The totals (the temperature of the part) are within 2 to 9 % (FVM, FDM) and the thin-slab cases (t/c = 0.1) within 3 %. This is the known limit of `checks.check_small_part_laminate`; the strip here is a line source across the whole depth, which that rule may not test. **Recommendation:** none beyond checking that the existing warning fires for a strip-like part; not tested here.

## 4. The coupon base stack as a regression test (no program change)

The paper's base stack is representable with undrawn outer slots (README 4). FVM and FDM reproduce the independent solver to 0.6 % for sources of 10 to 52 % of the board (+2.3 % at epsilon 1: see 5), solid3d 2 %, Lumped and Analytic 4 to 5 %. A test along the lines of `research/published-cases-followup/tests/test_studies.py::test_coupon_program_matches_the_solver_on_the_base_stack` could join `tests/test_layered_vs_3d.py` (which has the Cu / FR-4 / Cu coupon) on a `fix/` or `feature/` branch; it exercises the undrawn-slot representation, which no test does today.

## 5. A possible over-correction of the heater face term with the film under the source (inference, to test)

At epsilon 1 on the base stack FVM and FDM read R_solid +2.3 % (solid3d -2.3 %). The likely cause: `analysis.heater_stats` adds `q'' t_slot / (2 k)` to the footprint mean with `q''` = P/A, but when a film also cools the source area about half of the heat does not go through the slot. The size is 0.02 K of a 1 K R_solid here; on a bare outer layer of a real board it is the same order as the face term itself (the face term of the profile curves is documented in `docs/theory.md`). Not tested by a dedicated case; **recommendation:** a small study with the heater over bare laminate and a film coefficient of 5 to 50 W/m2K, comparing the face term with the flux that actually enters the laminate; no change until it is measured.

## 6. Documents (text in `docs/for-the-project-documents.md`)

Corrections that do not move a number: the three inconsistencies of the sources (Yovanovich and others Table 3 mean row; Lemczyk and others case (c), Table 4 R and Table 1 duplicate row; Shen and others CFD conductivity and the Pattern II reductions); the Seri Lee corner 4.6 % above the exact plate. These belong in `research/theory/BIBLIOGRAPHY.md` and in the validation text wherever the printed numbers are quoted.

## 7. What does not change

The program's formulas for the convection, the air, the Peaceman well, the Krogh cell and the others of the audit are not touched by these checks. The coupon, the strip cells, the 3-layer board and the plate (except the Lumped) agree with independent references within the limits stated in the README.
