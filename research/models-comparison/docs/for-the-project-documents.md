# Corrections for the project documents (from the review of 2026-10-24)

The project documents are not edited on a research branch. These are the changes the review of this folder found necessary in `docs/validation.md`; apply them on a `docs/` or `fix/` branch off `develop`. Every number below is printed by a script of this folder, run on the program at `0ea5f07` (README section 7).

Checked and **unchanged**: section 1 (example board), the 19-scenario table of section 2 and the grid table of 2.1 (`validation_study.py` prints them digit for digit), the four-board table of section 3 (`validation_study.py --fem`, digit for digit), the ring tables and the nine-board table of section 21 (`study_lumped_rings.py`, `study_complex_boards.py --compare`).

## Section 2, "Reading"

* "**Analytic** is exact on uniform boards and within 2.3 % with partial copper, ...": it is 0.3 to 1.0 % from the FVM on the uniform scenarios (the FVM has its own mesh error), and −4.3 % on the 30 × 30 mm copper island, which the sentence leaves out. Suggested: "**Analytic** is within 1 % of the FVM on uniform boards and within 2.3 % with partial copper, vias, heatsinks, corners, thin heaters and several heaters, except a copper island around the heater (−4.3 %, no warning); it fails (−25 %) ...".
* "the gap closes with the grid (section 2.1)": it narrows below 1 mm (−1.1 % at 0.5 mm, −0.5 % at 0.25 mm) but is −1.1 % at 2 mm and −2.4 % at 1 mm, so not monotonically.

## Section 2.1, the paragraph under the grid table

* "The classic point-sampled FDM jumps around it (±0.5 °C) ...; area sampling removes the jumps on geometry that is not aligned with the grid" is not what the table shows. Point sampling falls from +2.4 °C above the FVM at 4 mm to −0.7 °C at 1 mm and −0.15 °C at 0.25 mm; area sampling is below the FVM at every spacing (−0.3 to −1.4 °C) and not monotonic either (84.66 °C at 2 mm, 84.38 at 1 mm). Suggested: "The classic point-sampled FDM falls from above the FVM (+2.4 °C at 4 mm) to below it (−0.7 °C at 1 mm, −0.15 at 0.25 mm); area sampling stays 0.3 to 1.4 °C below the FVM and is not monotonic either (84.66 °C at 2 mm, 84.38 at 1 mm): with the via array it does not remove the dependence on the grid."
* "within 0.2 % from 1 mm": 0.23 % of the rise against the 0.25 mm value; say "within 0.25 %".
* The off-grid heater sentence (FVM 103.59, FDM area 103.18, point 105.69) is printed by no script, and "a 10.4 × 10.7 mm heater at 30.3 mm" does not define the board (three readings give an FVM of 102.01, 104.70 and 100.70 °C at 1 mm). Either state the polygon and add it to `validation_study.py`, or remove it.
* The 3D solid column is not monotonic (85.98 °C at 1 mm, 85.56 at 0.5 mm); worth a clause, since the text reads the FVM column only.

## Section 1

* "Every model closes the energy balance below 1e-11": true (FVM and FDM −1.4e-12, 3D solid −1.1e-13, Lumped and Analytic about 1e-15); "below 2e-12" is the current bound.

## Section 3

* The command `validation_study.py --fem` failed with an import error until this review (the finite-element solid moved to `research/solid3d-verification/scripts/`); fixed on `research/gerbers`. No change to the text is needed once the fix is merged.

## Section 5 (linear solvers)

Replace the table with the printed output (`solver_equivalence.py`): the old one shows CG on one board only, leaves out the fifth board (reference, insulated edges) although the text says "all five boards", and its timings are from before the symmetric ordering.

| Board | Solver | Tmax [°C] | max abs diff to direct [K] | Residual | Sweeps | Time [s] |
| :-- | :-- | --: | --: | --: | --: | --: |
| reference, 2 layers | direct (sparse LU) | 90.0657 | 0.0e+00 | 3e-14 | - | 0.01 |
| reference, 2 layers | cg (Jacobi) | 90.0657 | 3.3e-12 | 9e-13 | - | 0.01 |
| reference, 2 layers | SOR, residual 1e-9, auto omega | 90.0657 | 7.6e-09 | 1e-09 | 656 | 0.06 |
| reference, 2 layers | SOR, step 0.01 K, omega 1.5 (original rule) | 87.3447 | 2.7e+00 | 6e-02 | 369 | 0.03 |
| reference, 8 layers | direct (sparse LU) | 65.6612 | 0.0e+00 | 8e-14 | - | 0.13 |
| reference, 8 layers | cg (Jacobi) | 65.6612 | 4.6e-12 | 1e-12 | - | 0.03 |
| reference, 8 layers | SOR, residual 1e-9, auto omega | 65.6612 | 1.7e-08 | 1e-09 | 3247 | 0.79 |
| reference, 8 layers | SOR, step 0.01 K, omega 1.5 (original rule) | 53.1158 | 1.3e+01 | 1e-01 | 384 | 0.10 |
| example board (vias, heatsink, 2 heaters) | direct (sparse LU) | 85.8143 | 0.0e+00 | 1e-13 | - | 0.15 |
| example board (vias, heatsink, 2 heaters) | cg (Jacobi) | 85.8143 | 2.5e-11 | 1e-12 | - | 0.09 |
| example board (vias, heatsink, 2 heaters) | SOR, residual 1e-9, auto omega | 85.8143 | 1.1e-08 | 1e-09 | 2247 | 0.91 |
| example board (vias, heatsink, 2 heaters) | SOR, step 0.01 K, omega 1.5 (original rule) | 69.6449 | 1.6e+01 | 1e-01 | 562 | 0.23 |
| weak cooling (h = 2 W/m²K, 200 mm) | direct (sparse LU) | 44.2990 | 0.0e+00 | 1e-13 | - | 0.04 |
| weak cooling (h = 2 W/m²K, 200 mm) | cg (Jacobi) | 44.2990 | 6.6e-12 | 1e-12 | - | 0.03 |
| weak cooling (h = 2 W/m²K, 200 mm) | SOR, residual 1e-9, auto omega | 44.2990 | 2.6e-09 | 1e-09 | 2237 | 0.60 |
| weak cooling (h = 2 W/m²K, 200 mm) | SOR, step 0.01 K, omega 1.5 (original rule) | 37.5624 | 6.7e+00 | 3e-01 | 162 | 0.05 |
| reference, insulated edges | direct (sparse LU) | 90.3925 | 0.0e+00 | 2e-13 | - | 0.04 |
| reference, insulated edges | cg (Jacobi) | 90.3925 | 5.6e-12 | 1e-12 | - | 0.04 |
| reference, insulated edges | SOR, residual 1e-9, auto omega | 90.3925 | 3.9e-09 | 1e-09 | 1391 | 0.36 |
| reference, insulated edges | SOR, step 0.01 K, omega 1.5 (original rule) | 80.3174 | 1.0e+01 | 2e-01 | 550 | 0.14 |

Text: "agree to **1e-8 K** or better" → "**2e-8 K** or better" (SOR on 8 layers: 1.7e-8); "(3 to 30 times faster than a correct SOR)" → "(6 to 15 times faster than a correct SOR on these boards)"; drop "(After this table was made the direct solver got a symmetric ordering ...)".

## Section 6

* "A correct FDM (section 2) lands within about 1 % of the FVM" sits under a table where the FDM is −2.4 % at 1 mm. Suggested: "within 2.4 % of the FVM on this board at 1 mm and 1.1 % at 0.5 mm (within 0.1 % where there are no vias)".
* "energy balance −7e-13" of the new FVM row: it is −1.4e-12 now.

## Section 7 (time-dependent results)

Printed by `research/models-comparison/scripts/study_time_and_coefficients.py` (no script printed them before):

* Step animation, FVM against FDM (2 mm): FVM 25.0, 30.6, 44.0, 53.6, 61.5, 70.9, 77.0 (was 30.4, 43.6, 53.3, 61.3, 70.7, 76.6); FDM 25.0, 30.5, 43.6, 53.0, 60.8, 70.2, 76.3 (was 30.3, 43.1, 52.7, 60.6, 70.0, 75.9); "within 0.7 °C" holds (0.69 °C).
* Step animation, FVM against Analytic (1 mm): FVM 25.0, 30.7, 37.8, 44.4, 49.7, 54.0, 58.0, 61.9, 66.3, 71.4, 77.4 (was 30.5, 37.4, 44.0, 49.3, 53.7, 57.7, 61.7, 66.1, 71.2, 77.1); the Analytic row is unchanged; "within 2 °C" → "within 2.2 °C". The 63 % time is 19.2 s.
* Power-profile example: name the cell (1 mm) for "FVM 135.3 °C" (134.2 at 2 mm, the value of the FVM-FDM sentence); U2's oscillation is 84.9 °C, not 84.8.
* Exact check: "within 0.2 %" holds (−0.01 % with a trapezoidal integral of the loss); the errors are 3.06 / 1.67 / 0.875 / 0.448 and 0.315 / 0.0772 / 0.0192 / 0.00479 (rounded as quoted).
* CSV example: "within 4 %" is on the temperature; on the rise the Analytic is 4.7 % and the Lumped 3.6 % below the FVM. Say which.

## Section 8 (computed coefficients)

* Unchanged at 1 mm except the 11 W row: 2 m/s air 121.4 (was 121.5), convection × 0.8 145.2 (was 145.3). The power of the second row is 1.375 W (quoted 1.4). Name the cell (1 mm) and the script.
* "the three models agree on the coefficients within 0.1 W/m²K": confirmed, 0.07 W/m²K at 0.55, 5.5 and 22 W.

## Section 21 (nine boards)

* "a little hotter where it was already too hot (partial copper, where its uniform sheet spreads the heat too far: ...)" has the wrong sign: a sheet that spreads the heat too far gives a cool answer. The LED strip, power board and round board were already too hot (+3.3, +5.4, +8.7 %) and the series film raised every one-layer result. Suggested: "a little hotter on the partial-copper boards where it was already too hot (LED strip +3.3 → +5.9 %, round board +8.7 → +10.0 %): the series film raises every one-layer result, which helps where the model was cool and hurts where it was hot; why it is hot on those boards was not isolated."
* The reference of that table is the 3D solid at 1 mm. Add: "At 1 mm the 3D solid is within 1.4 % of the independent solver on three of these boards made isotropic (0.2 % at 0.5 mm); halving its cell moves the 20 mm pad by 0.8 % (`research/models-comparison/scripts/study_complex_boards_independent.py`)."
