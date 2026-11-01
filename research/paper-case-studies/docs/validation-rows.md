# Text for `docs/validation.md` when the studies have run (template)

Not adopted: the numbers marked `<...>` are to be filled from the printed tables of `study_measured_vias.py` and `study_thick_laminate.py`; nothing here has been run.

## A measurement of the through-plane conductivity of a via array

Soleymani Koohbanani (2016, Fig. 33) measured the through-plane conductivity of nine round samples (25.4 mm) with via arrays of four arrangements in a guarded heat-flux-meter test bed; the measurements exist only as four markers on a plot (read, +-0.2 W/mK). The independent unit-cell solver of `research/paper-case-studies` reproduces the thesis's closed form (equations 28 and 29) to `<1e-9>` for isothermal faces; the test bed's isothermal faces cannot be imposed in the program (a heater imposes a flux), so the models were run with the same condition as the solver and translated to the test bed by the solver's own ratio.

| Arrangement (spacing, pitch, mm) | measured (plot) | closed form over the samples | solver | fvm | fdm | solid3d | analytic | lumped |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| `<rows>` | | | | | | | | |

Limits: the thickness and the foil of the samples are not stated (1.6 mm and 35 um assumed); `<the group that is not usable and why>`.

## A published closed form for a source on a thick anisotropic laminate

Muzychka, Yovanovich and Culham (2004, equation 50, with the orthotropic transformation of equations 48 to 58) gives the spreading resistance of a rectangular source on an orthotropic channel with a cooled base. The resolved 3D reference of the project agrees with it to `<x %>` on `<33>` combinations (source 2 to 10 mm, thickness 0.8 to 3.2 mm, k_xy / k_z 1 to 9, film 10 to 1e6 W/m2K), and the laminate rule of 2.4.5 (at most 4 sub-gaps of 0.4 mm) differs from it by `<range>` of R' at 1.6 mm and `<range>` at 3.2 mm; `<the proposal or the limit text>`.
