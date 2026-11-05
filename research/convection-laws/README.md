# convection-laws: the natural-convection laws of the horizontal faces of a board

Study S4 of the paper case studies, prepared for 2.6.0. The program's laws are `Nu = 0.54 Ra^(1/4)` (face up, then `0.15 Ra^(1/3)` above Ra = 1e7) and `Nu = 0.27 Ra^(1/4)` (face down),
with `L = A/P`, from textbook memory; what the sources say and what the program does with them is in `research/horizontal-plate-h`, `research/plate-h-level` and
`research/theory-sources/docs/models-evidence-and-gaps.md` (L1). This folder (1) tabulates the candidate laws over the Ra of the boards, (2) builds a second, independent numerical solver and asks what
it can say about a small hot horizontal plate, (3) measures on the program (on a copy in memory) how far the hottest temperature moves with each law on the 17 harness boards, (4) recommends,
and (5) writes the measurement that would decide (`docs/measurement-plan.md`). The program is untouched (`git diff origin/develop --stat -- pcbthermal tests examples ico` is empty).

**Summary in six lines**

1. Over the Ra of the boards (3e2 to 5e4 on the face, A/P) the program's up face is -7 % to +15 % of Raithby-Hollands (Lienhard 8.37a/b, range 1 < Ra < 1e7, read in the page image: -7 % at 3e2, +1 % at 1e3, +9 % at 1e4, +15 % at 1e5) and its down face is -20 % (Ra 1e3), -10 % (1e4), +1 % (1e5) of the mean Goldstein-Lau law `0.475 Ra^(1/5)` (read on page 8 of Yovanovich and Jafarpur 1993).
2. The new solver (`lib/mac2d.py`, primitive variables, staggered grid, imports nothing from the program or from the other plate solvers) reproduces the differentially heated cavity of de Vahl Davis to 0.0 / 0.2 / 0.25 % in Nu at Ra 1e3 / 1e4 / 1e5 on uniform grids of 96, 96 and 144 cells (midplane velocities within 0.1 %) and the two codes of this repository agree on the strip within 2 to 7 % in a cold box. **It cannot choose a law**: the two-dimensional steady symmetric flow is not the flow of a board above Ra of about 1e4, and the heat of the cold box is not the open air (section 5).
3. **With the 17 boards of the regression harness** the hottest rise changes by **-0.9 to +1.0 % (mean +0.26 %)** if the program used Raithby-Hollands above and Goldstein-Lau below (-1.7 to +2.9 % without radiation); the two faces nearly cancel (+0.2 to +1.7 % with the face up alone). For the three test boards at 35 K of rise (local heater) the change is at most 0.5 %.
4. A board with a local heater is blind to the law; a uniform plate with one bright face is not: the ratio of the rise face up to face down is 0.62 for the program, 0.69 for Raithby-Hollands with Goldstein-Lau, 0.66 with Fujii-Imura, 0.52 for Jaffer (section 8): a measurement of one afternoon decides.
5. Recommendation (INTEGRATION.md): measure first; if one must change before, the pair Raithby-Hollands (up) with the mean Goldstein-Lau (down) rests on equations that were read, costs -0.9 to +1.0 % of the rise, and its acceptance tests are written; otherwise keep the laws and write the limit.
6. Not verified: de Vahl Davis' numbers are from memory (the solver and the memory agree); the Goldstein-Lau paper was not obtained; no measurement exists.

## 1. The situation

![air paths and the laws of each face](figures/fig_01_air_paths_and_laws_of_a_horizontal_board.png)

*Figure 1 (`figures/fig_01_air_paths_and_laws_of_a_horizontal_board.png`): left, section of a horizontal board: the face up (hot layer under colder air, air running in along the face and rising in a plume above the centre, unsteady above Ra of about 1e4) and the face down (a stable layer against the board; flow to the edges, cold air entering at the sides); right, the laws compared.*

The question (S4 of `PLAN-PAPER-STUDIES`): the boards sit at Ra 3e2 to 5e4 on `L = A/P`; which published law is closest on each face, and does it matter for a temperature?
What would answer it: a table of the laws (section 3), an independent numerical reference for a small hot plate (section 4 and 5), the effect on the program's temperatures (section 6), a measurement (section 8).

## 2. Sources and how they were read

| key | what | status |
| :-- | :-- | :-- |
| [Lienhard2024] pp 435 and 436 (PDF 449, 450) | eq. 8.35 `0.14 Ra^(1/3) (1 + 0.0107 Pr)/(1 + 0.01 Pr)`, `Ra >= 1e7`; eq. 8.37a/b Raithby-Hollands, `L* = A/P`, correction `1.4/ln(1 + 1.4/Nu)` for `Nu <= 10`, "recommended for 1 < Ra < 1e7" | **R** (page images rendered and read in this study) |
| [YovanovichJafarpur1993] p 8 (PDF 8) | Goldstein-Lau: downward `C` 0.44 to 0.527, mean at Pr 0.71 `C = 0.475`, numerical strip `0.524 Ra^(1/5)`, 40 < Ra < 8e3; upward numerical strip `0.621 Ra^(1/5)` in the same range | **R** (page image); the Goldstein-Lau paper itself **N** |
| [Lienhard2024] p 437 | Fujii-Imura `0.58 Ra_W^(1/5)` on the width W (water, 2D, 1e6 to 1e11) | R in `research/horizontal-plate-h`, not re-read |
| Jaffer 2023 | eq. 30 (up) and 56 (down), through `research/horizontal-plate-h/lib/correlations.py` (reviewed there) | R there, not re-read |
| Lloyd and Moran 1974 | the program's 0.54 | M (via [YovanovichJafarpur1993] p 7: range 2.2e4 to 8e6) |
| de Vahl Davis 1983 | cavity benchmark: `Nu` 1.118, 2.243, 4.519, 8.800; midplane maxima | **M** (paper not obtained) |
| Churchill and Chu | vertical forms | R through Lienhard 8.13a/b in earlier folders |

Nothing of a third party is stored here. The correlations were not copied from `research/horizontal-plate-h/lib/correlations.py`: they are imported from it (it is in `develop`).

## 3. The candidate laws

`scripts/study_laws_table.py` (no solver; Pr 0.71, `L = A/P` for the horizontal faces, the height for the vertical ones). Ratio to the program in brackets; RH above 1e7 is outside its range.

### 3.1 Face up and face down over Ra 1e2 to 1e8

| Ra | program | Raithby-Hollands (1 < Ra < 1e7) | Jaffer 30 |
| --: | --: | --: | --: |
| 1e2 | 1.708 | 1.977 (1.16) | 2.071 (1.21) |
| 3e2 | 2.247 | 2.422 (1.08) | 2.558 (1.14) |
| 1e3 | 3.037 | 3.064 (1.01) | 3.283 (1.08) |
| 3e3 | 3.996 | 3.839 (0.96) | 4.191 (1.05) |
| 1e4 | 5.400 | 4.965 (0.92) | 5.567 (1.03) |
| 3e4 | 7.107 | 6.331 (0.89) | 7.314 (1.03) |
| 1e5 | 9.603 | 8.324 (0.87) | 10.003 (1.04) |
| 1e6 | 17.076 | 13.592 (0.80) | 18.853 (1.10) |
| 1e7 | 30.366 | 24.170 (0.80) | 36.880 (1.21) |

| Ra | program | 0.475 Ra^(1/5) (GL mean) | Fujii-Imura strip (w = 2) | Fujii-Imura square (w = 4) | Kadambi-Drake disc | Jaffer 56, square | Jaffer 56, strip |
| --: | --: | --: | --: | --: | --: | --: | --: |
| 1e2 | 0.854 | 1.193 (1.40) | 1.104 (1.29) | 0.837 (0.98) | 1.169 (1.37) | 1.022 (1.20) | 1.464 (1.72) |
| 3e2 | 1.124 | 1.486 (1.32) | 1.375 (1.22) | 1.042 (0.93) | 1.457 (1.30) | 1.231 (1.10) | 1.740 (1.55) |
| 1e3 | 1.518 | 1.891 (1.25) | 1.750 (1.15) | 1.326 (0.87) | 1.853 (1.22) | 1.520 (1.00) | 2.122 (1.40) |
| 3e3 | 1.998 | 2.356 (1.18) | 2.180 (1.09) | 1.652 (0.83) | 2.309 (1.16) | 1.851 (0.93) | 2.559 (1.28) |
| 1e4 | 2.700 | 2.997 (1.11) | 2.773 (1.03) | 2.102 (0.78) | 2.937 (1.09) | 2.309 (0.86) | 3.163 (1.17) |
| 3e4 | 3.553 | 3.734 (1.05) | 3.455 (0.97) | 2.618 (0.74) | 3.659 (1.03) | 2.835 (0.80) | 3.856 (1.09) |
| 1e5 | 4.801 | 4.750 (0.99) | 4.396 (0.92) | 3.331 (0.69) | 4.655 (0.97) | 3.560 (0.74) | 4.813 (1.00) |
| 1e6 | 8.538 | 7.528 (0.88) | 6.967 (0.82) | 5.280 (0.62) | 7.378 (0.86) | 5.542 (0.65) | 7.429 (0.87) |

![laws against the program](figures/fig_04_laws_against_the_program_over_ra.png)

*Figure 4 (`figures/fig_04_laws_against_the_program_over_ra.png`): each law divided by the program's, face up (left) and face down (right); the band is the Ra of the boards of 3.2. The kinks are the correction of Raithby-Hollands at Nu = 10 (about 3e5) and the program's switch at 1e7; Raithby-Hollands above 1e7 is outside its published range.*

The up face of the program is inside the published bracket (Raithby-Hollands below it above 1e3, Jaffer above it); the down face has the wrong exponent against every published form (1/4 against 1/5) and sits **inside** the bracket of the published levels at Ra 1e3 (Jaffer square) and below it at Ra 1e3 to 1e4 for the means (Goldstein-Lau, Fujii-Imura strip, Kadambi-Drake): the published forms differ from each other by 40 % at Ra 1e3 (0.87 to 1.40 of the program) and 30 % at 1e4 (0.78 to 1.17), so no law is "the" value. The Fujii-Imura numbers are the form of the book on a width W, evaluated on `A/P` with W a multiple of A/P, and the data are for water in two-dimensional plates (1e6 to 1e11): outside its range here.

### 3.2 The boards in Ra

| board | excess | A/P (mm) | Ra | h up, program | h up, RH | h down, program | h down, GL |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| 40 x 40 | 5 K | 10.0 | 4.7e2 | 6.60 | 6.93 | 3.30 | 4.27 |
| 40 x 40 | 80 K | 10.0 | 4.3e3 | 12.77 | 12.07 | 6.39 | 7.39 |
| 60 x 60 | 20 K | 15.0 | 5.6e3 | 8.38 | 7.85 | 4.19 | 4.79 |
| 100 x 80 | 5 K | 22.2 | 5.1e3 | 5.41 | 5.09 | 2.70 | 3.10 |
| 100 x 80 | 10 K | 22.2 | 9.8e3 | 6.41 | 5.90 | 3.21 | 3.56 |
| 100 x 80 | 40 K | 22.2 | 3.1e4 | 8.95 | 7.95 | 4.47 | 4.69 |
| 100 x 80 | 80 K | 22.2 | 4.7e4 | 10.46 | 9.20 | 5.23 | 5.37 |
| 160 x 100 | 20 K | 30.8 | 4.8e4 | 7.00 | 6.16 | 3.50 | 3.59 |
| 200 x 200 | 5 K | 50.0 | 5.8e4 | 4.41 | 3.87 | 2.21 | 2.24 |
| 200 x 200 | 80 K | 50.0 | 5.4e5 | 8.54 | 6.78 | 4.27 | 3.88 |

(W/m2K, convection only, 25 degC ambient; the full table of 30 rows is printed by the script.) A board of 40 to 200 mm at 5 to 80 K is at Ra 4e2 to 5e5; the band of the figure is 3e2 to 2e4 where most of the boards of the harness and of the examples at modest excess sit.

### 3.3 Vertical

Churchill and Chu: the laminar form (8.13a, the program's default for new projects) against the general one (8.13b): 0.993 (Ra 1e2), 1.043 (1e3), 1.072 (1e4), 1.066 (1e5), 1.023 (1e6), 0.948 (1e7), 0.853 (1e8) of the general. Already checked in `research/plate-h-level` and `research/effective-conductivity`; nothing changes here.

## 4. A second, independent solver

`lib/mac2d.py` (about 400 lines; documented; no import of the program or of `plate2d.py` / `plate_h2d.py`). Primitive variables on a staggered (MAC) grid, central fluxes, implicit diffusion (a factorised sparse matrix per field),
incremental pressure-correction projection, steady state by pseudo-time marching; closed box with no-slip walls or symmetry lines, an optional zero-thickness isothermal plate on `y = 0` with either or both faces hot.
The other two solvers of the repository are stream function and vorticity codes with free (open) boundaries; this one is a different formulation and a different boundary treatment, so an agreement is not the same code run twice.

![numerical domain and grid](figures/fig_02_numerical_domain_and_staggered_grid.png)

*Figure 2 (`figures/fig_02_numerical_domain_and_staggered_grid.png`): left, the half domain of the strip in a cold box (symmetry line at x = 0, plate half width 1 = A/P); right, the staggered arrangement of the unknowns.*

### 4.1 Validation on the published cavity (de Vahl Davis)

`scripts/study_cavity.py`: air, Pr 0.71, square cavity, hot wall on the left, cold on the right, adiabatic top and bottom; mean `Nu` of the hot wall against the benchmark values (M) and the maxima of the velocities on the midplanes.

CAVITY_TABLE

![cavity benchmark](figures/fig_05_cavity_benchmark_of_the_new_solver.png)

*Figure 5 (`figures/fig_05_cavity_benchmark_of_the_new_solver.png`): left, the error of the hot-wall Nusselt number against the uniform grid; right, the Nusselt number against Ra.*

Second order on uniform grids (0.64 to 0.07 % at Ra 1e3 from 48 to 96 cells... the table). The two walls carry the same heat (the energy balance) in every case. **A defect found on the way, fixed**: the first runs used a strongly graded grid (ratio 1.12 on 48 cells) and read +0.7 % at Ra 1e3 and +18 % at Ra 1e5; the central differences lose their second order on a stretched grid, so the validation is on uniform grids and the plate (which needs clustering at its tip) is run with milder grading (0.93 to 1.08 per cell) and its numbers carry a stated uncertainty (section 5); a graded grid of ratio 1.03 on 96 cells gave +1.7 % at Ra 1e5 against +0.5 % uniform.
Regression tests: `tests/test_convection_laws.py` (graded faces, exact conduction `Nu = 1`, the cavity at Ra 1e3 on 32 and 64 cells within 1 % and 0.4 %, the energy balance of the plate at Ra 100).

## 5. The hot strip

PLATE_SECTION

## 6. The effect on the program

`scripts/study_board_effect.py`: the program's own FVM (cell 2 mm), horizontal board (layer 1 up), computed h, emissivity 0.9, with `convection.h_natural_horizontal` replaced in memory by each pair of laws (`research/horizontal-plate-h/lib/correlations.py use_horizontal`; the program is not edited), on the **17 boards of the regression harness** (`tests/regression/regress_boards.py`).
(The rises of these boards are 30 to 400 K because the harness powers are large; the effect at the moderate rises of real boards is in section 6.2.)

BOARD_TABLE

![effect on the harness boards](figures/fig_07_effect_on_the_harness_boards.png)

*Figure 7 (`figures/fig_07_effect_on_the_harness_boards.png`): change of the hottest rise of the 17 boards for each pair of laws (with radiation).*

### 6.1 Reading

* The pair with **both faces changed** (RH up, GL down): -0.9 to +1.0 % of the rise, mean +0.26 %; with the up face alone +0.2 to +1.7 % (mean +0.99 %), because Raithby-Hollands is below the program's face up from Ra 1e3, and the Goldstein-Lau face down is above it below Ra 1e5 so that its cooling brings the sum back. Fujii-Imura strip (outside its range) +0.76 % mean; Jaffer +0.28 %.
* Convection only (emissivity zero): the same signs and 2.6 to 3.7 times larger (-1.7 to +2.9 % for RH + GL), which is the upper bound of the effect for a bright board; the doubling and halving of the power move the extremes by 0.3 points (tables above).
* In kelvin: 0.1 to 1 K for the boards of 60 to 80 K; up to 2.6 K for the 300 K plate with a pad (+0.8 %).
* The boards that move most (up face alone, +1.7 %) are the ones with the least copper spreading (`plate_pad`); the Lumped, Analytic, FDM and 3D solid take the same coefficients and move in the same direction (the coefficient is the same input; not re-run here for every model).

### 6.2 At the Ra of real boards

`scripts/study_measurement_prediction.py` (section 8): for the three test boards (100 x 80 mm, 35 K of rise, a local 8 x 8 mm heater) the pair RH + GL moves the hottest rise by +0.3 % (A), -0.1 % (B) and -0.2 % (C) horizontal, 0.0 % vertical; the other pairs by at most +0.6 %. A local heater on a copper board is dominated by the spreading resistance (the mean rise of board A is 5 K of the 35 K).

## 7. Reproduction of earlier numbers (consistency)

* The L1 ratios of the evidence file are reproduced: program against Raithby-Hollands -7 % at 3e2, -1 % at 1e3, +9 % at 1e4, +15 % at 1e5 (section 3.1: 2.247/2.422, 3.037/3.064, 5.400/4.965, 9.603/8.324); program down against 0.475 Ra^(1/5) -20 % at 1e3 and -10 % at 1e4.
* The isolated-face strip of the earlier open-domain solver (`research/horizontal-plate-h` section 5: up 2.309 / 3.673, down 2.322 / 3.483 at Ra 1e3 / 1e4) against the Goldstein-Lau numerical strip (0.621 and 0.524 Ra^(1/5), read on page 8): 2.47 / 3.92 and 2.09 / 3.31: the earlier solver is -6.5 / -6.3 % (up) and +11 / +5 % (down) of it; section 5 adds the third code.

## 8. The measurement (docs/measurement-plan.md)

![the test boards and set-up](figures/fig_03_test_boards_and_set_up.png)

*Figure 3 (`figures/fig_03_test_boards_and_set_up.png`): the three boards (full copper, 20 mm pad, pad with 3 x 3 vias) with the five thermocouples, and the set-up.*

`scripts/study_measurement_prediction.py` (the "true" film is a model, the numbers are predictions of the program, not measurements):

* Powers for a 35 K rise with the program's laws: A 1.52 W, B 0.62 W, C 0.66 W (3 x 3 vias of 0.3 mm on a 1.3 mm pitch: +6.2 % of the power for the same rise against the pad alone; 5 x 5 +9.4 %, 6 x 6 +10.4 %).
* The hottest rise of the three boards horizontal, turned over and vertical differs between the four sets of laws by at most 0.5 % (table in the script output): a board with a local heater cannot choose a law.
* A multiplier on h fitted on A to a film "RH + GL" (0.977) makes the program's laws predict B and C to 0.4 to 0.8 %; without it to 0.0 to 0.4 %: the multiplier hides the law.
* **A uniform plate with one bright face** (board D, back loss 1 W/m2K, emissivity 0.07; the program's own convection functions, a 1D balance, no board solver): rise up / rise down at 2, 4 and 8 W: program 0.629 / 0.625 / 0.624, RH + GL 0.699 / 0.693 / 0.691, RH + FI 0.665 / 0.659 / 0.658, Jaffer 0.533 / 0.521 / 0.518; the back loss (0.5 to 2 W/m2K) and the emissivity (0.05 to 0.10) move the ratios by 0.03 and 0.015 and keep the order. The spread between the laws is 5 times the resolution of a ratio of two runs (3 %).
* The protocol, the bill of materials, the uncertainty budget (2 to 3 % of the rise when the air is still; estimates, not measured) and the comparison list are in `docs/measurement-plan.md`.

## 9. Recommendation

In `INTEGRATION.md`: (1) measure board D first (a day, about 150 EUR); (2) if the maintainer prefers to change before, option B (Raithby-Hollands up, 0.475 Ra^(1/5) down) rests on read equations, moves the rise of the 17 boards by -0.9 to +1.0 %, and has acceptance tests; (3) otherwise keep the laws and write the limit (`docs/theory-text.md`).
The decision is the maintainer's.

## 10. Limits of this study

* The new solver is two-dimensional, steady and symmetric about the plate centre; it is validated on a closed cavity, not on a plate in free space. The strip results are in a **cold closed box**: the cold walls add cooling, the box is not the open air.
* The Ra 1e4 results carry a heat balance of 1.16 (the wall gradients at the singular tip of a zero-thickness plate): absolute `Nu` to about 15 %, ratios between cases on the same grid better.
* The effect on temperatures is the program's FVM at 2 mm with computed h; the other models take the same coefficients (not re-run here for every model); every number of section 6 is a **model change**, not a measurement.
* The measurement plan is not performed; its uncertainty budget is an estimate.

## 11. What was read and what was not verified

* **Read in full (page images, this study):** Lienhard 6.00 printed pages 435 and 436 (eq. 8.35, 8.37a/b with the correction and the range), Yovanovich and Jafarpur (1993) page 8 (Goldstein-Lau coefficients: 0.475, 0.524, 0.621, the ranges 40 < Ra < 8e3).
* **Read earlier (other folders, not re-read):** Lienhard p 437 (Fujii-Imura, Kadambi-Drake), Jaffer (2023) equations 30 and 56, Churchill-Chu forms.
* **From memory:** de Vahl Davis (1983) values (1.118, 2.243, 4.519, 8.800, midplane maxima) and Lloyd and Moran; the solver reproduces the first to 0.0 to 0.25 %.
* **Not obtained:** the paper of Goldstein and Lau (1983), the Raithby-Hollands chapter, Fujii and Imura (1972), Lloyd and Moran (1974), de Vahl Davis (1983).
* **Reproduced:** the cavity (section 4.1) with an independent solver written here; the program's L1 ratios (section 3.1); the program's numbers of section 6 are runs of the program on a copy in memory. **Not reproduced:** any published horizontal-plate number with a flow in free space.
* **Tests:** `research/convection-laws/tests/test_convection_laws.py`, 6 tests.
* **Reproduce:** `scripts/study_laws_table.py`, `study_cavity.py` (about 4 minutes), `study_plate_mac.py` (about an hour, two processes with `--both` and `--isolated`), `study_board_effect.py` (1 minute), `study_measurement_prediction.py` (2 minutes; `--vias`, `--faces`), `print_tables.py`, `make_diagrams.py`, `make_figures.py`.
