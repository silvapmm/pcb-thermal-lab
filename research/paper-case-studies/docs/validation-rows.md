# Text for `docs/validation.md` (not adopted; numbers from the runs of this folder)

Numbers marked "plot" were read from a figure of the source. All rows come from `research/paper-case-studies` (README sections 10 to 13).

## A measurement of the through-plane conductivity of a via array

Soleymani Koohbanani (2016, Fig. 33) measured the through-plane conductivity of nine round samples (25.4 mm) with via arrays of four arrangements in a guarded heat-flux-meter test bed; the measurements exist only as four markers on a plot (read, +-0.2 W/mK). The independent unit-cell solver of `research/paper-case-studies/lib/axisym_cell.py` equals the thesis's equations 28 and 29 to 1e-15 to 2e-13, and the program's models on a periodic patch of each sample (6 x 6 cells, foil 35 um, flux condition) agree with the solver as follows (error of the resistance, finest grid):

| Arrangement (spacing mm, samples of Table 9) | measured (plot, W/mK) | closed form over the samples | fvm | fdm | solid3d | analytic | lumped |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| straight 2.5 (1 to 3) | 2.50 | 1.795 to 2.752 | 0.8 to 1.0 % | 0.8 to 1.0 % | 1.1 to 1.3 % | 8.3 to 11.5 % | 6.7 to 9.5 % |
| staggered 2.5 (4 to 6) | 4.30 | 3.259 to 5.174 | 1.0 to 1.2 % | 1.0 to 1.3 % | 1.3 to 1.6 % | 9.7 to 13.1 % | 6.0 to 8.2 % |
| straight 1.25 (7) | 7.00 (not usable: eq. 28 gives 10.02, +43 %) | 10.018 | 0.8 % | 0.8 % | 1.2 % | 12.0 % | 6.6 % |
| straight 1.0 (8, 9) | 12.90 | 9.483 to 13.078 | 0.5 to 0.6 % | 0.5 to 0.6 % | 1.0 % | 8.2 to 9.4 % | 4.1 to 5.0 % |

Limits: the thickness (1.6 mm assumed) and the foil (35 um assumed) of the samples are not stated; the test bed imposes isothermal faces, the program a face flux (the solver puts the difference at 1.1 to 7.3 % of the node resistance); the thesis does not say which diameter each marker is; the Analytic and Lumped overstate the resistance (the safe side).

## A published closed form for a source on a thick anisotropic laminate

Muzychka, Yovanovich and Culham (2004, equation 50, with the orthotropic transformation of equations 48 to 58) gives the spreading resistance of a rectangular source on an orthotropic channel with a cooled base. The project's 3D finite-volume reference, extrapolated in the number of sub-slabs (error falling as 1/n^2) and in the pixel (quadratic in 1/pixel), agrees with it to -1.15 to -0.07 % of R' on 33 combinations (S = 2, 5, 10 mm; t = 0.8, 1.6, 3.2 mm; FR-4 0.3 to 2.7 W/mK in plane, 0.3 through; film 10 to 1e6 W/m2K); a single grid at pixel S/16 and 16 sub-slabs is 0.5 to 2.6 % high. Against that reference the laminate rule of 2.4.5 (0.4 mm, 4 sub-gaps) gives, for the FVM at 0.25 mm, errors of -0.3 to -3.7 % (bare laminate) and -2.0 to -6.0 % (a copper pad under the source) for sources of 5 mm and above on boards up to 1.6 mm, and -16.6 % (bare) and -19.8 % (pad) for a 2 mm source on a 3.2 mm board (the program too cool). (0.2, 8) and (0.1, 16) reduce the worst rows to -6.3 / -9.0 % and -1.5 / -2.5 % at 1.7 to 1.8 and 3.0 to 3.4 times the node layers.

## A vertical plate with two strip sources against a published numerical case and measurements

Lee and Yovanovich (1989; measurements of Zinnes 1969): glass (k 1.032 W/mK, eps 0.387) and ceramic (28.38, 0.366) plates of 96.52 x 2.286 mm with two 5.08 mm strips of 3875 W/m2 per face. An independent solver (one-dimensional plate with radiation and a marching boundary layer, `lib/vertical_plate.py`) reproduces the curves of the paper within the plot reading (13 of 16 compared values within 5 %, the others 6.2 to 7.4 %, 1 to 6 K). The program with computed coefficients (one per face) gives the mean strip excess 10.3 % above the conjugate solution on the glass plate (+8.6 points from the uniform coefficient) and 2.0 % below it on the ceramic plate.
