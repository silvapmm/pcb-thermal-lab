# horizontal-plate-h: which natural-convection level for a horizontal face

The question (C8 of `research/ROADMAP.md`, row 13c): the faces of the program's examples are horizontal, and `pcbthermal/convection.py` gives them textbook correlations, `Nu = 0.54 Ra^(1/4)` (then `0.15 Ra^(1/3)` above `Ra = 1e7`) for a hot face looking up and `Nu = 0.27 Ra^(1/4)` for a hot face looking down, with the characteristic length `L = A/P` (area over perimeter of one face). The vertical study (`research/plate-h-level`) did not cover them. What do the sources say about those two correlations, can an independent numerical solution reproduce a published case, and how much does the choice move the rise of a board and of the finned block with the fins hanging down? The program is not touched: everything runs on copies in memory (`lib/correlations.py`).

**Summary.** (1) The sources opened give two published theories and one fit for the horizontal faces: Schulenberg's own report (KIT, read: the strip and the disc below a hot plate; the strip formula as printed gives `0.4274 Ra^(1/5)` at `Pr` 0.71), Jaffer (2023, read: upper face `[0.642 + 0.370 Ra^(1/6)]^2`, lower face `0.341 + 0.550 (Ra/Xi_R)^(1/5)` with its own length `L_R`), and the textbook form of Lloyd and Moran (abstract only). The originals of the measurements, Fujii and Imura, Al-Arabi and El-Riedy and Raithby and Hollands were not obtained. (2) Over the Rayleigh numbers of the boards (`Ra` of `A/P` 1e3 to 5e5) **the program's upper-face correlation is 3 to 7 % below Jaffer's fit of the same measurements**, inside their scatter (about 5 %); **its lower-face correlation has the wrong exponent against the published forms (`Ra^(1/4)` against `Ra^(1/5)`) and no shape dependence**: against Jaffer's long strip it is 30 % low at `Ra` 1e3, equal at 1e5 and high above; against Jaffer's square (whose length is half the side, not `A/P`) it is equal at 1e3 and 15 to 43 % high from 1e4 to 3e5 (section 3.2). (3) Schulenberg's printed coefficient 1.156 is **not** the misprint that Jaffer says it is: the report's own limits (0.571 and 0.544) give `(0.571/0.544)^3 = 1.156`; Jaffer's "corrected" 0.631 and 1.56 replace the small-Prandtl asymptote by a number that is not in the report; at `Pr` 0.71 they differ by 5 % (section 3.1). (4) The independent solver (`lib/plate_h2d.py`: a thin strip and an axisymmetric disc in open air, solved with the full Boussinesq equations) puts the **lower face 7 to 19 % above Jaffer's fit** (and 29 to 61 % above Schulenberg's asymptotic theory, which has no conduction term) from `Ra` 1e2 to 1e4 and **reproduces the 1/5 power law** that Goldstein and Lau report for their strip (fitted exponents 0.14 to 0.20), but **cannot reproduce the measured upper face**: the isolated upper face of the steady symmetric solution is 12 to 36 % below the correlations at `Ra` 1e2 to 1e4 and the `Ra` 1e5 cases did not give a usable answer (the flow of a hot face looking up is unsteady and three-dimensional in the experiments, and the solver imposes symmetry), so the solver's upper face is a lower bound and not a result. (5) The solver does show a mechanism that the correlations leave out: with **both faces hot** (a board), the warm air that leaves the lower face at the edge joins the inflow of the upper face and the upper-face `Nu` falls to 0.56 to 0.70 of the isolated-face value (strip and disc, `Ra` 1e2 to 1e4); the lower face does not change (0.96 to 1.01). The size of this coupling in a real board is not established (the same solver is far from the measured isolated upper face). (6) The rise of a board moves by **-2.8 to +0.5 %** with Jaffer's forms instead of the program's (-4.0 to +1.7 % without radiation; the finned block with the fins down by -0.6 to -0.5 %), and would move by **+1.8 to +9.9 %** (+5.1 to +20.9 % without radiation; +3.2 to +5.3 % for the finned block) if the upper face lost 40 % of its coefficient (sections 6 and 7). (7) Recommendation in `INTEGRATION.md`: **no change of the coefficients; document the limit** (text for the project documents in `docs/`); Jaffer's forms stay an option for the maintainer. The maintainer's rule is that a limit of the model is lived with.

## 1. The situation

![the flow of a thin horizontal board](figures/fig_01_flow_paths_of_a_horizontal_board.png)

*Figure 1 (`figures/fig_01_flow_paths_of_a_horizontal_board.png`): the section of a thin horizontal board with both faces hot, the situation of the program's examples. Above, the air is drawn in along the face towards the centre, heated in a layer that thickens, and leaves in a plume; below, cold air meets the face at its centre (stagnation), flows out in a thin layer and rises at the edges, where it joins the inflow of the upper face.*

![the three situations compared](figures/fig_02_three_situations.png)

*Figure 2 (`figures/fig_02_three_situations.png`): the three situations of this study. (a) An isolated upper face (back insulated, or flush in an insulating surround): the plates of Lloyd and Moran, Goldstein et al. and Fujii and Imura. (b) An isolated lower face: the theory of Schulenberg and the experiments of Aihara et al. and Faw and Dullforce. (c) A thin free board with both faces hot: the program's board, and the solver of this study.*

![the characteristic length](figures/fig_04_characteristic_length.png)

*Figure 4 (`figures/fig_04_characteristic_length.png`): `L = A/P` for a long strip (half the width), a square (a quarter of the side: 25 mm for a 100 mm board) and a disc (half the radius). The solver works with `a` (strip) or `R` (disc) as unit length: `Nu_L = Nu_R / 2` and `Ra_L = Ra_R / 8` for the disc.*

The levels in `lib/correlations.py` (`Nu = h L / k`, `Ra = g beta dT L^3 / (nu alpha)`, `L = A/P` unless said):

| Level (function) | Nu | What it is |
| :-- | :-- | :-- |
| program up (`program_up`) | `0.54 Ra^(1/4)`, `0.15 Ra^(1/3)` above `Ra` 1e7 | the program (`h_natural_horizontal`); textbook form of Lloyd and Moran (1974) |
| program down (`program_down`) | `0.27 Ra^(1/4)` | the program |
| Jaffer up (`jaffer_up`) | `[0.642 + 0.370 Ra^(1/6)]^2` | Jaffer (2023) equation 30; no Prandtl number |
| Jaffer down (`jaffer_down`, `jaffer_down_shape`) | `0.341 + 0.550 (Ra / Xi_R)^(1/5)`, `Xi_R(Pr) = [1 + (0.477/Pr)^(3/5)]^(5/3)` | Jaffer equations 46, 51 and 56, written with `L_R` (half the shorter side of a rectangle, `2R/pi` of a disc); `q = L_R/(A/P)` is 1 for a long strip, 2 for a square, `4/pi` for a disc |
| Schulenberg strip (`schulenberg_strip`) | `0.571 Pr^(1/5) Ra^(1/5) / [1 + 1.156 Pr^(3/5)]^(1/3)` | KfK 3713 equation 92 (length: half the width); theory with the interpolation exponent set by the experiments of Aihara et al. |
| Schulenberg disc (`schulenberg_disc`) | `0.705 Pr^(1/5) Ra_R^(1/5) / [1 + 1.48 Pr^(3/5)]^(1/3)`, length `R` | equation 94; converted to `A/P = R/2` |

The Rayleigh numbers of the boards (`study_correlations.py`, part 1; air at the film temperature, ambient 20 degC): a square of 40 / 60 / 100 / 150 / 200 mm has `Ra` of `A/P` of 9.7e2 / 3.3e3 / 1.5e4 / 5.1e4 / 1.2e5 at 10 K, 2.5e3 / 8.4e3 / 3.9e4 / 1.3e5 / 3.1e5 at 30 K and 4.0e3 / 1.4e4 / 6.2e4 / 2.1e5 / 5.0e5 at 60 K; a long strip of 40 or 100 mm width (`L = w/2`) 7.7e3 to 3.2e4 and 1.2e5 to 5.0e5. So the range of interest is **`Ra` 1e3 to 5e5 of `A/P`**, far from the `Ra` of 1e7 where the program changes branch.

![the evidence ranges](figures/fig_05_evidence_ranges_against_the_boards.png)

*Figure 5 (`figures/fig_05_evidence_ranges_against_the_boards.png`): the Rayleigh ranges of the data sets that Jaffer lists (his Table 1, read) against the boards of the program. For the upper face only Goldstein et al. (sublimation, `Ra` up to 6.2e3) and the lowest points of Lloyd and Moran (from 2.6e4) reach the boards, and the two lowest points of Lloyd and Moran are 14 and 19 % above Jaffer's fit; for the lower face the squares of Goldstein and Lau (250 to 4500) reach the smallest boards and Faw and Dullforce and Aihara et al. (1e6 to 1e7) lie above them. The measured air data below `Ra` 1e5 are therefore few.*

## 2. Sources and how they were read

| Source | What it gave | Status |
| :-- | :-- | :-- |
| Schulenberg, KfK 3713 (1984), open copy KIT library | the whole text extracted; the pages with equations 42 to 46 (page 16) and 92 to 95 (page 31) read as images; equations 87 to 90 (page 30) from the text layer | **R** (pages named); figures 6 to 9 not read |
| Jaffer, arXiv:2201.02612v6 (2023) | Table 1 (ranges), section 3.4, sections 7 to 11, 15 to 17, Tables 3 and 7, references | **R** as extracted text for the pages named; the figures not viewed; the data are plot values |
| Lloyd and Moran (1974) | the correlations and the `A/P` rule, the transition at about `Ra` 8e6 | **S** (abstract by search results, and Jaffer's text) |
| Goldstein, Sparrow and Jones (1973); Goldstein and Lau (1983) | the abstracts: sublimation from horizontal plates; a finite-difference strip at `Pr` 0.7 with a 1/5 power law, 10 < `Ra` < 1e4 | **S**; no prefactor of the numerical solution was obtained (paywall) |
| Schulenberg (1985, the journal paper); Fujii and Imura (1972); Aihara et al.; Faw and Dullforce (1982) | their data and ranges through Jaffer's Table 1, the citations through Schulenberg's reference list | **S** |
| Al-Arabi and El-Riedy (1976); Raithby and Hollands (Handbook of Heat Transfer) | named by the task | **N** (not opened) |
| the Waterloo archive, arXiv, the publishers' open copies | searched: the Waterloo reports found are on vertical plates and channels; no open copy of the horizontal papers of Fujii and Imura, Al-Arabi or Lloyd and Moran was found | **N** |

The entries are in `research/theory/BIBLIOGRAPHY.md` (`[Schulenberg1984KfK]`, `[Schulenberg1985]`, `[GoldsteinSparrowJones1973]`, `[GoldsteinLau1983]`, `[FujiiImura1972]`, `[AiharaFaw]`, `[AlArabiElRiedy1976]`, `[RaithbyHollands]`, and the updated `[LloydMoran1974]` and `[Jaffer2023]`).

## 3. What the sources say, and what the program uses

**3.1 Schulenberg's strip and disc against Jaffer's correction** (`study_correlations.py`, part 3). The report gives the asymptotes: for `Pr -> 0` `Nu = 0.571 (Gr Pr^2)^(1/5)` (strip, equation 43) and `0.705 (Gr Pr^2)^(1/5)` (disc, equation 45); for `Pr -> infinity` `Nu = 0.544 Ra^(1/5)` (strip, equation 87) and `0.619 Ra^(1/5)` (disc, equation 89); and combines them with the exponent `n = 3` of Churchill and Usagi (page 31): `1/Nu^3 = 1/Nu_0^3 + 1/Nu_inf^3`. That gives `Nu/Ra^(1/5) = 0.571 Pr^(1/5) / [1 + (0.571/0.544)^3 Pr^(3/5)]^(1/3)` and `(0.571/0.544)^3 = 1.156`: **the printed 1.156 is what the asymptotes give**, and the disc is consistent in the same way (`(0.705/0.619)^3 = 1.48`). Jaffer (section 3.4) calls the 1.156 a misprint and uses 0.631 and 1.56, which have the same large-`Pr` limit (0.544) but a small-`Pr` coefficient (0.631) that is not the one of the report (0.571). At `Pr` 0.71 the printed form gives `0.4274 Ra^(1/5)` and Jaffer's `0.4483 Ra^(1/5)` (5 % higher). This study uses the printed form as the reading of the source and shows the other as a variant; the data that Jaffer fits cannot decide between them (his Table 7 gives 3.7 to 4.2 % RMSRE with his own, and it does not show the printed form's error).

**3.2 The levels against each other** (`study_correlations.py`, part 2; Nu of `L = A/P`, ratio to the program):

| Ra | program up | Jaffer up | ratio | program down | Jaffer down, strip | ratio | Jaffer down, square | ratio | Jaffer down, disc | ratio | Schulenberg strip | ratio | Schulenberg disc | ratio |
| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| 1e2 | 1.71 | 2.07 | 1.21 | 0.85 | 1.48 | 1.73 | 1.03 | 1.21 | 1.30 | 1.52 | 1.07 | 1.26 | 0.96 | 1.13 |
| 1e3 | 3.04 | 3.28 | 1.08 | 1.52 | 2.15 | 1.41 | 1.54 | 1.01 | 1.91 | 1.26 | 1.70 | 1.12 | 1.53 | 1.01 |
| 1e4 | 5.40 | 5.57 | 1.03 | 2.70 | 3.20 | 1.19 | 2.34 | 0.87 | 2.86 | 1.06 | 2.70 | 1.00 | 2.42 | 0.90 |
| 1e5 | 9.60 | 10.00 | 1.04 | 4.80 | 4.87 | 1.01 | 3.60 | 0.75 | 4.38 | 0.91 | 4.27 | 0.89 | 3.83 | 0.80 |
| 1e6 | 17.08 | 18.85 | 1.10 | 8.54 | 7.52 | 0.88 | 5.61 | 0.66 | 6.79 | 0.80 | 6.77 | 0.79 | 6.08 | 0.71 |
| 1e7 | 30.37 | 36.88 | 1.21 | 15.18 | 11.72 | 0.77 | 8.80 | 0.58 | 10.60 | 0.70 | 10.74 | 0.71 | 9.63 | 0.63 |

![levels in Nu and in ratio](figures/fig_06_levels_in_nu_and_in_ratio.png)

*Figure 6 (`figures/fig_06_levels_in_nu_and_in_ratio.png`): the levels in `Nu` (top) and their ratio to the program (bottom) against `Ra` of `L = A/P`, for the upper and lower face; the green band is the range of the boards.*

* **Upper face.** The program lies 3 to 7 % below Jaffer's fit over `Ra` 1e3 to 5e5 (ratio 1.08 at 1e3, 1.03 at 1e4, 1.04 at 1e5, 1.07 at 3e5), and 9 % below at 1e6; Jaffer's fit has an RMSRE of 4.9 % against the data of Lloyd and Moran (his Table 3), so the two agree within the scatter of the measurements. The program's branch change at `Ra` 1e7 is a 12 % jump (`0.15 Ra^(1/3)` against `0.54 Ra^(1/4)`) that is outside the boards' range. At `Ra` 1e2 or below, where only the sublimation data of Goldstein et al. exist, the program is 17 to 31 % low, because its `Ra^(1/4)` goes to zero and Jaffer's form goes to the conduction limit `2/pi`.
* **Lower face.** The published forms go as `Ra^(1/5)` and the program's as `Ra^(1/4)`: the program crosses Jaffer's long strip at `Ra` 1e5, Schulenberg's printed strip at 1e4, Jaffer's disc at 3e4 and Jaffer's square at 1e3, and is above them for larger `Ra`. In the boards' range it is **between 29 % below** Jaffer's long strip (`Ra` 1e3) **and 43 % above** Jaffer's square (3e5). The shape matters in the published forms (the length of the lower face is the distance from the middle line of the plate to its edge, `L_R`: `2 A/P` for a square, `A/P` for a long strip, `4/pi` times `A/P` for a disc, equation 57), and `A/P` does not carry it. For a 100 mm square at 30 K (`Ra` 3.9e4), convection only: program 4.08 W/m2K, Jaffer's square 3.24 (`study_correlations.py`, part 4).


## 4. The independent solver

`lib/plate_h2d.py` (imports nothing from the program; written for this folder, the model of the numerics being the vertical solver of `research/plate-h-level/lib/plate2d.py`) solves the steady laminar Boussinesq problem of a **thin isothermal plate across the buoyancy direction** in open air, upper and lower face at once: stream function and vorticity, `u = psi_y`, `v = -psi_x`, `omega = v_x - u_y`, `omega_t + u omega_x + v omega_y = Pr Laplacian(omega) + Ra Pr T_x`, `T_t + u T_x + v T_y = Laplacian(T)`; the plate lies on `y = 0` for `|x| <= 1` (zero thickness, `psi = 0`, `T = 1`, **two wall vorticities**, one per face, by Thom's formula under-relaxed); the flow is taken symmetric about `x = 0`; the boundaries are free (`T = 0`, `omega = 0`, zero normal derivative of `psi`: air enters freely at the side and the bottom; zero normal derivative of `T`, `omega` and `psi` at the top, where the plume leaves); stretched grids cluster at the plate and at its tip; pseudo-time marching with implicit diffusion (factorised matrices) and explicit central convection. With `axisym = True` the same code solves the axisymmetric problem (`x` is the radius; `u = psi_y/r`, `v = -psi_x/r`, the vortex stretching term `u omega/r`, the operators with `1/r` terms, the area weight `2 r` in `Nu` and in the balance). `hot_up = False` or `hot_down = False` makes a face insulated (the plate is a mirror for `T` on that side), which gives the isolated faces of the experiments. The unit length is `a` (strip: `L = A/P = a`) or `R` (disc: `A/P = R/2`, `Nu_L = Nu_R/2`, `Ra_L = Ra_R/8`); the numbers below are all for `L = A/P`, `Pr = 0.71`.

![the numerical domains](figures/fig_03_numerical_domains.png)

*Figure 3 (`figures/fig_03_numerical_domains.png`): the half domains and the boundary conditions of the strip (planar) and the disc (axisymmetric about `x = 0`).*

**Checks of the solver** (`tests/test_horizontal_plate_h.py`, 10 tests; `study_plate_h2d.py`):

* **Conduction limit** (`Ra` 0.01): the strip and the disc transfer the same heat from the two faces within 15 % (the box is taller above than below, 7 and 3.5 `L`) and the heat leaving the domain is 0.85 to 1.15 of the heat leaving the plate; the conduction `Nu_R` of the disc lies between the open-space value `4/pi` = 1.27 and 1.75 (the value of an outer sphere at five radii, the size of the box).
* **Direction of the flow**: at `Ra` 1e3 the air above the plate moves towards the centre and rises there, the air below moves outwards (Figure 1, Figure 10); the lower face has the larger `Nu`, and the local `Nu` of the lower face is highest at the centre (stagnation) while that of the upper face is lowest there (Figure 9).
* **Grid and domain** (strip, `Ra` 1e4, both faces / lower face alone): the finer grid (70 x 48 cells in the half plate and the outside, 90 above, 64 below, first cell 3e-3, tip 6e-3, against 48 x 32, 60, 44, 5e-3 and 1e-2) moves the upper face by +0.6 % (2.088 against 2.075) and the lower by -0.5 % / +0.1 % (3.485 against 3.501 / 3.483); a domain twice as wide and tall (width 10, 14 above, 7 below) moves them by -0.6 %, +0.5 % / +0.4 % (2.063, 3.519 / 3.497).
* **Energy balance** (heat leaving the domain over heat leaving the plate): 0.85 to 1.03 for the strip and 1.03 to 1.18 for the disc at `Ra` up to 1e4; 0.70 for the isolated upper face at `Ra` 1e5. The central, non-conservative convection of the stream-function form does not conserve the heat exactly; the balance is a limit of the numbers, about 10 % of the heat, and the local flux of the plate does not change with the grid (above). It was not made to close.
* **The `Ra` 1e5 strip** did not give usable numbers: the isolated lower face blew up at every step size tried (the central convection is unstable at that cell Peclet number on the base grid; the `Ra` 1e5 runs use a first cell of 4e-3), the isolated upper face "converged" with a balance of 0.70, and the case with both faces had not settled after 12 time units (the upper-face `Nu` drifting by 3 % over the last window and the field showing a detached vortex above the plate, a sign that the steady symmetric solution does not exist there in the sense of this solver). These cases are in `out/plate_h2d.json` and in the table below but are not used in any statement and are not plotted.
* **Symmetry and unsteadiness.** The flow is imposed symmetric about the centre line. A hot face looking up carries a hot layer under colder air, which becomes unstable above a local Rayleigh number of about 1700 (a rough estimate with a layer of thickness `L/Nu`, `Ra/Nu^3`: 1e4 / 2.1^3 = 1e3 at `Ra` 1e4, 1e5 / 3.6^3 = 2e3 at 1e5, using the solver's own `Nu`), so the symmetric steady solution can be physical only up to `Ra` of about 1e4 (all `Ra` 1e4 cases converged to 2e-5 with no oscillation); the experiments are unsteady and three-dimensional above that. This is the reason the solver is a lower bound for the upper face.

## 5. The numerical plates against the published levels

`study_plate_h2d.py` (`Nu` of `L = A/P`; "balance" is the heat leaving the domain over the heat leaving the plate; the ratios use the face that is hot in the case: `up` for the upper face, `down` for the lower; the Jaffer lower-face column uses `q` = 1 for the strip and `4/pi` for the disc, the Schulenberg column the strip or the disc formula):

| geometry | Ra | faces | grid | Nu up | Nu down | balance | converged | up / program | up / Jaffer | down / program | down / Jaffer (strip or disc) | down / Schulenberg |
| :-- | --: | :-- | :-- | --: | --: | --: | :-- | --: | --: | --: | --: | --: |
| disc | 1e+02 | both | base | 1.050 | 1.497 | 1.055 | True | 0.61 | 0.51 | 1.75 | 1.15 | 1.55 |
| disc | 1e+02 | down | base | 0.000 | 1.554 | 1.103 | True |  |  | 1.82 | 1.19 | 1.61 |
| disc | 1e+02 | up | base | 1.503 | 0.000 | 1.181 | True | 0.88 | 0.73 |  |  |  |
| disc | 1e+03 | both | base | 1.462 | 2.218 | 1.052 | True | 0.48 | 0.45 | 1.46 | 1.16 | 1.45 |
| disc | 1e+03 | down | base | 0.000 | 2.227 | 1.071 | True |  |  | 1.47 | 1.17 | 1.46 |
| disc | 1e+03 | up | base | 2.202 | 0.000 | 1.165 | True | 0.73 | 0.67 |  |  |  |
| disc | 1e+04 | both | base | 2.167 | 3.389 | 1.035 | True | 0.40 | 0.39 | 1.26 | 1.18 | 1.40 |
| disc | 1e+04 | down | base | 0.000 | 3.372 | 1.033 | True |  |  | 1.25 | 1.18 | 1.39 |
| disc | 1e+04 | up | base | 3.437 | 0.000 | 1.120 | True | 0.64 | 0.62 |  |  |  |
| strip | 1e+03 | both | base | 1.412 | 2.296 | 0.945 | True | 0.47 | 0.43 | 1.51 | 1.07 | 1.35 |
| strip | 1e+03 | down | base | 0.000 | 2.322 | 0.995 | True |  |  | 1.53 | 1.08 | 1.36 |
| strip | 1e+03 | up | base | 2.309 | 0.000 | 1.006 | True | 0.76 | 0.70 |  |  |  |
| strip | 1e+04 | both | base | 2.075 | 3.501 | 0.861 | True | 0.38 | 0.37 | 1.30 | 1.09 | 1.30 |
| strip | 1e+04 | both | fine | 2.088 | 3.485 | 0.895 | True | 0.39 | 0.38 | 1.29 | 1.09 | 1.29 |
| strip | 1e+04 | both | wide | 2.063 | 3.519 | 0.853 | True | 0.38 | 0.37 | 1.30 | 1.10 | 1.30 |
| strip | 1e+04 | down | base | 0.000 | 3.483 | 0.920 | True |  |  | 1.29 | 1.09 | 1.29 |
| strip | 1e+04 | down | fine | 0.000 | 3.485 | 0.949 | True |  |  | 1.29 | 1.09 | 1.29 |
| strip | 1e+04 | down | wide | 0.000 | 3.497 | 0.909 | True |  |  | 1.30 | 1.09 | 1.30 |
| strip | 1e+04 | up | base | 3.673 | 0.000 | 0.882 | True | 0.68 | 0.66 |  |  |  |
| strip | 1e+05 | both | base | 3.617 | 5.399 | 1.023 | False | 0.38 | 0.36 | 1.12 | 1.11 | 1.26 |
| strip | 1e+05 | down | base | nan | nan | nan | False |  |  | nan | nan | nan |
| strip | 1e+05 | up | base | 5.892 | 0.000 | 0.704 | True | 0.61 | 0.59 |  |  |  |

![the numerical plates against the levels](figures/fig_07_numerical_plates_against_the_levels.png)

*Figure 7 (`figures/fig_07_numerical_plates_against_the_levels.png`): `Nu` of the numerical plates (grey: filled both faces hot, open the isolated face; circles strip, squares disc) against the program, Jaffer and Schulenberg, for the upper face (left) and the lower (right). The `Ra` 1e5 strip cases that did not give usable numbers (not converged, blown up or with a balance of 0.70) are not drawn.*

* **Lower face, reproduction.** The solver is above Jaffer's fit by 7 to 9 % for the strip (`Ra` 1e3 and 1e4, grid-converged to 0.5 %) and by 15 to 19 % for the disc (1e2 to 1e4), and above Schulenberg's asymptotic theory by 29 to 36 % (strip) and 39 to 61 % (disc). The excess over the asymptotic theory is what a conduction term would add at these `Ra` (Jaffer's 0.341), and the box (the 2D strip has no finite conduction limit and the box is five lengths wide) adds to it at the lowest `Ra`; the excess over Jaffer's fit is within the 10 % uncertainty of the measurements that Jaffer's Table 1 lists for the squares of Goldstein and Lau (250 to 4500) for the strip and 5 to 9 points larger for the disc. **So the published lower face is reproduced within about 20 %, not to the digit, and the strip is closer than the disc.** Jaffer's own bound (his equation 46 is an upper bound for a square plate) cannot be checked with a strip or a disc. The fitted exponents of `Nu` against `Ra` between consecutive cases are 0.16 to 0.18 for the isolated lower face (strip and disc), 0.17 to 0.18 for the lower face with both faces hot, 0.17 to 0.20 for the isolated upper face and 0.14 to 0.17 for the upper face with both faces hot: close to the 1/5 power law that Goldstein and Lau report for their finite-difference strip at `Pr` 0.7 (`Ra` 10 to 1e4; their prefactor was not obtained, so only the exponent is compared) and not to the 1/4 of the program's correlations.
* **Upper face, no reproduction.** The isolated upper face is 24 % (strip, 1e3), 32 % (1e4), 12 % (disc 1e2), 27 % (1e3) and 36 % (1e4) below the program, and 30 to 38 % below Jaffer's fit from `Ra` 1e3; the gap grows with `Ra`, as it should if the experiments see the three-dimensional unsteady flow that the symmetric steady solution cannot. Nothing about the upper face of a board can be concluded from the absolute values of the solver.
* **Energy balance and uncertainty.** The balance of the cases is 0.86 to 1.18; the isolated-face disc cases are the worst (1.12 to 1.18). The numbers are good to a few percent between grids (above) and to about 10 % for the conservation of the heat.

## 6. What the other face does to a face

`study_plate_h2d.py` (Nu of a face with both faces hot over Nu of the same face alone, same grid):

| geometry | Ra | upper face: both / alone | lower face: both / alone |
| :-- | --: | --: | --: |
| strip | 1e+03 | 0.61 | 0.99 |
| strip | 1e+04 | 0.56 | 1.00 |
| disc | 1e+02 | 0.70 | 0.96 |
| disc | 1e+03 | 0.66 | 1.00 |
| disc | 1e+04 | 0.63 | 1.01 |

![the other face](figures/fig_08_the_other_face.png)

*Figure 8 (`figures/fig_08_the_other_face.png`): the ratio of `Nu` with both faces hot to `Nu` of the face alone, strip and disc, upper and lower face.*

![the local Nusselt number](figures/fig_09_local_nusselt_number_of_the_strip.png)

*Figure 9 (`figures/fig_09_local_nusselt_number_of_the_strip.png`): the local `Nu = h a / k` along the half strip with both faces hot, upper and lower face, `Ra` 1e3 and 1e4. The lower face is thinnest (highest `h`) at the centre, the upper thickest (lowest `h`); both rise at the edge, where the grid sees the singularity of the thin plate's tip (grid-dependent, integrable).*

![the computed fields](figures/fig_10_computed_fields_of_the_horizontal_plate.png)

*Figure 10 (`figures/fig_10_computed_fields_of_the_horizontal_plate.png`): temperature (colour, 0 to 1) and streamlines (black) near the plate with both faces hot: strip `Ra` 1e3 and 1e4, disc `Ra_L` 1e4. The plume over the centre, the inflow along the upper face, the thin layer under the lower face, and the warm layer that leaves the lower face at the edge and is drawn up into the inflow of the upper face.*

The lower face does not feel the upper one (0.96 to 1.01), and **the upper face of a board with both faces hot has 0.56 to 0.70 of the `Nu` of the same face alone**: 0.61 / 0.56 (strip, `Ra` 1e3 / 1e4) and 0.70 / 0.66 / 0.63 (disc, 1e2 / 1e3 / 1e4). The mechanism is the one of Figure 1 and is visible in Figure 10: the air that reaches the upper face has been warmed by the lower face at the edge. The effect is smaller for the disc than for the strip (the air reaches the edge of a disc from all sides and the warm layer is a ring). **Limits.** All of this is a steady symmetric solution that does not reproduce the measured isolated upper face (section 5), so the *size* of the coupling in a real board is not known: it can be smaller (turbulent mixing brings fresh air), larger, or not there in three dimensions where the warm air also leaves at the corners. What is robust is the sign and the mechanism, and that it is absent from all the published upper-face correlations, which are for an isolated face (back insulated or flush in a surround, Figure 2).

## 7. How much the choice moves the rise of a board and of the finned block

`study_board_effect.py`: the program's own FVM (cell 2 mm), horizontal board, computed `h` (`Board.h_mode = "computed"`, `orientation = "horizontal"`, emissivity 0.9, radiation to the ambient included as the program does), with `convection.h_natural_horizontal` replaced in memory (`correlations.use_horizontal`) by each level. The two example boards (100 x 80 mm with four layers, vias and a heatsink; 100 x 100 mm with two layers), two-layer square boards with full copper and one 10 x 10 mm part from 40 to 200 mm, and the finned block of `research/fin-channel` (60 x 40 mm board, 3 W, aluminium block 40 x 30 x 3 mm with 15 x 1.5 mm fins on the **bottom** face, so the fins hang down, with the program's uniform fin coefficient and the lower-face level; gaps 3.5, 6.5, 14.5 mm). Levels: `program`; `jaffer` (his upper face and his lower face with `q` of the board: 2 for a square, 1.8 for 100 x 80 mm); and the sensitivities `up x0.6` (the upper face loses 40 %, the size of the coupling of section 6), `down x1.3`, `up x0.6 down x1.3`, `up x1.2`, `down x0.7` (**the factors are bracketing runs, not results**). Rise of the hottest point in K for the program, and the change with each other level:

| case | program (K) | jaffer | up x0.6 | down x1.3 | up x0.6 down x1.3 | up x1.2 | down x0.7 |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| example_board (horizontal) | 60.36 | +0.4 % | +5.4 % | -1.5 % | +3.5 % | -2.2 % | +1.7 % |
| reference_board (horizontal) | 65.82 | +0.5 % | +5.1 % | -1.3 % | +3.5 % | -2.2 % | +1.4 % |
| 40 mm square, 0.2 W | 7.60 | -2.8 % | +9.3 % | -2.6 % | +5.9 % | -3.8 % | +2.8 % |
| 40 mm square, 0.8 W | 26.87 | -1.2 % | +9.9 % | -2.6 % | +6.4 % | -4.0 % | +2.9 % |
| 60 mm square, 0.4 W | 10.32 | -0.8 % | +6.5 % | -1.8 % | +4.2 % | -2.7 % | +1.9 % |
| 60 mm square, 1.5 W | 35.67 | -0.0 % | +6.8 % | -1.8 % | +4.4 % | -2.8 % | +2.0 % |
| 100 mm square, 1.0 W | 20.16 | +0.1 % | +3.5 % | -0.9 % | +2.3 % | -1.5 % | +1.0 % |
| 100 mm square, 3.0 W | 58.32 | +0.3 % | +3.6 % | -0.9 % | +2.5 % | -1.5 % | +1.0 % |
| 150 mm square, 2.0 W | 39.08 | +0.2 % | +2.1 % | -0.5 % | +1.5 % | -0.9 % | +0.6 % |
| 150 mm square, 6.0 W | 114.53 | +0.3 % | +2.3 % | -0.6 % | +1.7 % | -1.0 % | +0.6 % |
| 200 mm square, 3.0 W | 56.50 | +0.2 % | +1.8 % | -0.4 % | +1.3 % | -0.8 % | +0.5 % |
| 200 mm square, 10.0 W | 184.28 | +0.2 % | +2.0 % | -0.5 % | +1.4 % | -0.9 % | +0.5 % |
| finned block gap 3.5 mm | 54.46 | -0.6 % | +3.2 % | -2.4 % | +0.4 % | -1.5 % | +2.9 % |
| finned block gap 6.5 mm | 58.29 | -0.5 % | +4.1 % | -2.6 % | +1.1 % | -1.8 % | +3.0 % |
| finned block gap 14.5 mm | 63.14 | -0.5 % | +5.3 % | -2.6 % | +2.2 % | -2.3 % | +3.0 % |

![the effect on the rise](figures/fig_11_effect_on_the_rise_of_the_boards.png)

*Figure 11 (`figures/fig_11_effect_on_the_rise_of_the_boards.png`): the change of the rise with each level, with radiation (left) and without (right).*

The same with the emissivity at zero (convection only, boards only):

| case | program (K) | jaffer | up x0.6 | down x1.3 | up x0.6 down x1.3 | up x1.2 | down x0.7 |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| example_board (horizontal) | 77.61 | +1.2 % | +13.6 % | -3.5 % | +8.1 % | -4.8 % | +4.1 % |
| reference_board (horizontal) | 83.86 | +1.7 % | +13.5 % | -3.2 % | +8.1 % | -4.7 % | +3.8 % |
| 40 mm square, 0.2 W | 11.62 | -4.0 % | +20.9 % | -5.3 % | +12.3 % | -7.3 % | +6.3 % |
| 40 mm square, 0.8 W | 38.08 | -1.4 % | +20.9 % | -5.1 % | +12.4 % | -7.2 % | +6.1 % |
| 60 mm square, 0.4 W | 14.76 | -0.7 % | +17.4 % | -4.4 % | +10.2 % | -6.0 % | +5.2 % |
| 60 mm square, 1.5 W | 47.48 | +0.7 % | +16.6 % | -4.1 % | +9.9 % | -5.7 % | +4.8 % |
| 100 mm square, 1.0 W | 25.52 | +0.9 % | +11.3 % | -2.8 % | +6.7 % | -3.9 % | +3.3 % |
| 100 mm square, 3.0 W | 70.58 | +1.2 % | +10.4 % | -2.5 % | +6.2 % | -3.6 % | +3.0 % |
| 150 mm square, 2.0 W | 45.86 | +0.9 % | +7.1 % | -1.7 % | +4.3 % | -2.5 % | +2.0 % |
| 150 mm square, 6.0 W | 130.70 | +0.9 % | +6.5 % | -1.5 % | +4.0 % | -2.3 % | +1.8 % |
| 200 mm square, 3.0 W | 64.92 | +0.8 % | +5.4 % | -1.3 % | +3.3 % | -2.0 % | +1.5 % |
| 200 mm square, 10.0 W | 207.05 | +0.6 % | +5.1 % | -1.2 % | +3.2 % | -1.9 % | +1.4 % |

* **Jaffer's forms against the program**: -2.8 to +0.5 % of the rise with radiation (the largest, -2.8 %, is the 40 mm board at 0.2 W), -4.0 to +1.7 % without radiation, -0.6 to -0.5 % for the finned block with the fins down. The effect is small because the radiation is about half of the total coefficient and does not depend on the level, and because the copper spreads the heat.
* **The size of what could be wrong**: a 40 % loss of the upper face (`up x0.6`) would raise the rise by 5.4 and 5.1 % for the two examples, by 9.3 to 9.9 % for the 40 mm boards, 6.5 to 6.8 % for 60 mm, 3.5 % for 100 mm and 1.8 to 2.3 % for 150 and 200 mm; without radiation by 13.6 and 13.5 % for the examples and up to 20.9 %. For the finned block with the fins down, `up x0.6` gives +3.2, +4.1, +5.3 % (gaps 3.5, 6.5, 14.5 mm) and a lower face 30 % higher or lower changes the block by -2.4 to -2.6 % and +2.9 to +3.0 %. The small boards are the sensitive ones.

**C9, noted and not solved.** The fins of the finned block hang down: the program gives the whole fin array the lower-face coefficient times the fin ratio (`h_exp = h_face r_fin + h_extra`), which is a model of fins in free air, with no channel effect, and the radiation between the fins and to the ground (the computed `h` carries about half of its value as radiation with a simple view factor, which is smaller between close fins) is not corrected. The numerical plate of this study has no fins, so it says nothing about C9. The sensitivity above (the block's rise changes by 2 to 3 % for a 30 % change of the lower-face coefficient) is the only number this study adds; the view factors of a fin array and a numerical solution under a horizontal base with fins remain open (`research/ROADMAP.md` C9).

## 8. Decision

The maintainer's rule: if it is a limit of the model, we live with it. The numbers support that: the upper-face correlation is inside the scatter of the measurements, the lower-face correlation is wrong in the exponent and in the shape dependence but moves the rise of a board by less than 3 % with radiation (4 % without), and the one effect that could be larger (the coupling of the faces of a free board, a possible +2 to +10 % of the rise with radiation) is a numerical finding that this study could not tie to a measurement. **Recommended: no change of the program; document the limit** (`INTEGRATION.md` proposal A, text in `docs/`). Proposals B (Jaffer's forms as an option) and C (a correction for the other face) are written up with their measured impact and not recommended.

## 9. What was read and what was not verified

* **Read (the pages named)**: T. Schulenberg, KfK 3713 (the text layer of the whole report, the page images of pages 16 and 31); A. G. Jaffer, arXiv:2201.02612v6 (Table 1, sections 1, 3.4, 7 to 11, 15, 17 and the tables 3 and 7, as extracted text; the figures were not viewed).
* **From a summary only**: Lloyd and Moran (1974); Goldstein, Sparrow and Jones (1973); Goldstein and Lau (1983) (the abstract: 1/5 power law, `Ra` 10 to 1e4, no prefactor); Schulenberg (1985); Fujii and Imura (1972); Aihara et al.; Faw and Dullforce (1982): all through Jaffer's tables and the abstracts.
* **Not obtained**: Al-Arabi and El-Riedy (1976), Raithby and Hollands (the handbook chapter), the originals of the measurements (the data of Jaffer's Table 1 are plot values or his digitisation), any open copy of the horizontal-plate papers in the Waterloo archive or on arXiv. The statement that the textbook `0.54` and `0.27` are McAdams' and Lloyd and Moran's rests on the summaries and on the program's own docstring.
* **Reproduced**: the large- and small-Prandtl limits of Schulenberg's strip and disc and the consistency of his coefficient 1.156 (arithmetic from his own limits, section 3.1); the lower face of an independent numerical solution against Jaffer's fit within 7 to 19 % and the 1/5 exponent; **not reproduced**: any measured upper-face value (the solver is 12 to 36 % below the correlations from `Ra` 1e2 to 1e4, more above), the numerical prefactor of Goldstein and Lau (not obtained), the Fujii and Imura and Lloyd and Moran data (not obtained).
* **Mine, not a source**: the solver and its results, the coupling of the two faces and its mechanism, the reading of `A/P` against `L_R` in the board runs (`q` = 2 for a square: Jaffer's lower-face formula is written with `L_R`, the half of the shorter side), the recommendation.
* **Not done**: `Pr` other than 0.71; `Ra` above 1e4 (the strip at 1e5 failed or did not settle; the disc at 1e5 and the square plate were not run); three-dimensional flow, unsteadiness and the square; the fins; a measured case with both faces hot.
* **Tests**: `research/horizontal-plate-h/tests/test_horizontal_plate_h.py` (the program's levels against its own function, the branch change, the limits printed in the report, the shape scaling, the restoration of the program, the conduction limits of the strip and the disc and their balance, the direction of the flow, the isolated faces, the grid).
