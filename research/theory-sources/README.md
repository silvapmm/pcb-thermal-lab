# Theory sources: opening the sources the models rest on, and reproducing their published cases

The program's formulas and the planned methods rest on sources that had been named, summarised or remembered but not opened (`research/theory/BIBLIOGRAPHY.md`, statuses M, N and S). This folder carries the roadmap row 16 (items F1 to F8; F9, the old rows of the removed program, is left out as agreed): it opens what can be opened, writes down the equations, tables and numbers with their pages, reproduces published cases with solvers that import nothing of the program, then runs the program's models on the same cases or on the closest version they can represent. Where a source could not be obtained it says so and lists it for the maintainer.

The program is untouched (`git diff origin/develop --stat -- pcbthermal tests examples ico` is empty); the findings are proposals in `INTEGRATION.md`, the text for the project documents is in `docs/`.

## 1. The questions

| Item | Question | Where |
| :-- | :-- | :-- |
| F3 | Which natural and mixed convection forms does the program use, and are they what the sources print? The `ht` Hollands discrepancy. | 3.1 to 3.4 |
| F4 | The 2D Bruggeman, Hashin-Shtrikman and Keller-Dykhne formulas, with page and equation. | 3.5 |
| F1 | Culham and Yovanovich (1998) above Biot 60: reopen pages 460 to 467, test the series truncation. | 3.6 |
| F2 | The cases of Muzychka and others (compound plate, heat-sink base) and of Lemczyk. | 3.7 |
| F8 | Yovanovich's Table 3 and Lee's equations 1 and 2, previously seen in part. | 3.11 |
| F7 | A grid convergence index with three grids on each reference. | 3.10 |
| F6 | One source and one reproduced case for each planned topic 12 to 16. | 3.8, 3.9, 3.12 |
| F5 | The remaining M, N and S sources, in the order the other items needed them. | 3 (each section), last section |

### 1.1 The situations that the sections explain

![The trace cells of Lemczyk](figures/fig_06_lemczyk_trace_cells.png)

*Figure 6: `figures/fig_06_lemczyk_trace_cells.png`. Left, the surface trace (case a): the trace is held at the contact temperature Tc, the film h2 acts on the rest of the top face and h1 on the bottom; the ends are adiabatic. Right, the mid-buried trace (case b), solved as a half cell with twice the flow. Heat paths in red, films in blue. Section 3.7.*

![The coupon of Culham and Yovanovich and its cosine modes](figures/fig_07_culham_coupon_and_modes.png)

*Figure 7: `figures/fig_07_culham_coupon_and_modes.png`. Left, the five-layer coupon (FR4 0.5263 mm and copper 0.0356 mm, 50 x 50 mm, a centred 25 x 25 mm source of 2.5 W) with the films; right, the first cosine modes of the series solution and the shaded source (odd modes vanish for a centred source). Section 3.6.*

![Duality and effective medium](figures/fig_08_duality_and_effective_medium.png)

*Figure 8: `figures/fig_08_duality_and_effective_medium.png`. The checkerboard whose effective conductivity is sqrt(s1 s2), the array of disks used for the phase-interchange test, and the 90-degree rotation of Dykhne. Section 3.5.*

![Foster and Cauer networks](figures/fig_09_foster_and_cauer_networks.png)

*Figure 9: `figures/fig_09_foster_and_cauer_networks.png`. The Cauer ladder of the BUK7S1R0-40H (AN11261, page 6) and its Foster equivalent computed here. Section 3.8.*

![Gerber regions](figures/fig_10_gerber_spec_regions.png)

*Figure 10: `figures/fig_10_gerber_spec_regions.png`. The two contour examples of section 4.10.4.8 of the Gerber specification and the areas that follow from the coordinates (68 and 132 mm2). Section 3.9.*

![The two cases of Muzychka and others](figures/fig_11_muzychka_cases.png)

*Figure 11: `figures/fig_11_muzychka_cases.png`. Case 1 (b), a spreader of k 350 on a plate of k 10, and case 2, the baseplate of a heat sink with four sources. Section 3.7.*

## 2. Findings in short

* **The program's vertical-plate correlation is the printed one.** Both forms of Churchill and Chu are printed in the open textbook of Lienhard (equations 8.13a and 8.13b, pages 433 and 434); Example 8.1 gives Nu 47.33 and the formula gives 47.34, and the program's function equals the formula at its own Rayleigh number (3.1). The 1975 paper itself is paywalled and still not read.
* **The `ht` documentation has the wrong exponent, the code is right.** The ISO 15099 / Rohsenow form printed on page 5 of an open ASHRAE preprint has `k2 = Ra^(1/3)/450.5`, the Prandtl 0.71 limit of the 1984 constants; the code form is within 0.5 % of it for Ra 3e3 to 3e5 and the fifth-root form is 3.7 % low at Ra 1e7 (3.3). The Hollands papers themselves are not obtained.
* **The program's horizontal-plate correlations differ from Raithby and Hollands (Lienhard 8.35 to 8.38) by 3 to 11 % of the total coefficient** on upward-facing boards of 100 mm and more (the program is the cooler, so the board would be hotter), and the downward-facing correlation is 30 to 40 % below Fujii and Imura's where that is valid (the program is the hotter there). No change is made; the impact is in 3.4 and `INTEGRATION.md`.
* **Mixed convection:** the cube-root blend is inside the range 1.73 to 3 that Jaffer and Jaffer find for a vertical plate, but for a horizontal board in a level flow they find p = 2, and the program's p = 3 gives a convective coefficient 7 to 11 % lower (3.4). Churchill (1977) is still not read.
* **The 2D Bruggeman, Hashin-Shtrikman and Keller-Dykhne formulas are now tied to page and equation** (Milton 2002: 3.1 to 3.11 on pages 47 to 50, 7.9 and 7.10 on page 116, 10.31 and 10.32 on pages 195 and 196). Equation 7.10 for d = 2 equals the repository forms to 1e-15; the 2D Bruggeman form follows from the same step Milton takes for spheres and equals the repository function to 4e-14; an independent periodic solver puts a disk array above the lower bound and converges the checkerboard to sqrt(s1 s2) (3.5).
* **Culham and Yovanovich (1998), above Biot 60: the plateau is still not explained, but part of the excess is.** A cosine-series solution of the coupon converged to 7.8 W/mK at the base case against the paper's 8.28 and the independent 3D solver's 7.81 of `research/effective-conductivity` 4.2 (the series and the solver agree to 0.1 %); truncating the series at 5 to 7 modes per direction gives 8.50 to 8.14, so the paper's value is consistent with a coarse truncation (not proved). At Bi 625 the series gives 0.56 to 0.62 W/mK for every truncation: **truncation does not create the plateau of about 4.8** (3.6). The paper's equation 11 defines the effective conductivity through `A/L` that it does not quantify; the plateau remains unreproduced.
* **Muzychka and others:** case 1 (b) (compound plate) is reproduced by the independent solver within 0.03 K and by the FVM, FDM, 3D solid and Analytic within 0.05 K; case 2 (heat-sink base with four sources) is reproduced by the solver within 0.03 K at the centroids (97.41, 103.85, 101.31, 99.95 against 97.40, 103.82, 101.28, 99.94), and the program's one-layer models are 2.9 to 5.5 K low there, 67 to 89 % of the bound `q'' t / (2 k)` of the through-thickness gradient (3.7).
* **Lemczyk, Mack, Culham and Yovanovich (1992):** an independent 2D solver reproduces all sixteen heat flows of Table 1 within 0.5 % (one at 1.15 %) and the dimensionless factors of Tables 2 and 3 within 0.1 to 4 % for the cases a and b; for the cases c and d the largest difference is 8 to 10 %, and the paper's own one-dimensional limit for case c at Bi 0.01 (90.91) does not match the exact value 100 (3.7).
* **The Foster form is reproduced from a published model:** the Cauer ladder of AN11261 sums to 0.4000 K/W (datasheet 0.4), gives Zth(4 ms) = 0.264 K/W (paper 0.26), and its Foster equivalent equals it to 6e-15 K/W (3.8).
* **Grid convergence:** the Celik procedure is read and its Table 1 reproduced; the independent solver converges at order 1.99 to 2.00 in the plane, and through the thickness the sub-slab count matters more (case 2: 102.419, 102.525 and 102.875 K for 16, 8 and 4 sub-slabs, extrapolated 102.373 K against the paper's 102.33). The program's FVM and FDM show GCIs of 0.00 to 0.48 % in the cases run (3.10).
* **Lee's equations 1 and 2 and Yovanovich's Table 3 are read.** The example of Lee gives 0.6566 K/W (article 0.66) and the Bessel series reproduces Table 3's isoflux column to 1e-4 (3.11).

## 3. Results

How to run: from the repository root, `.venv/bin/python research/theory-sources/scripts/<script>.py`; the figures by `make_figures.py` and `make_diagrams.py`; the tests by `.venv/bin/python -m pytest -q research/theory-sources/tests` (12 pass). Every number below was printed by the script named in its section.

### 3.1 The vertical plate: Churchill and Chu (`study_natural_convection_sources.py`, part 1)

Source (**read**): Lienhard, *A Heat Transfer Textbook* 6.00 (open), page 433, equation 8.13a, `Nu = 0.68 + 0.670 Ra^(1/4) / [1 + (0.492/Pr)^(9/16)]^(4/9)` for Ra up to 1e9, and page 434, equation 8.13b, the all-range form `Nu = {0.825 + 0.387 Ra^(1/6) / [1 + (0.492/Pr)^(9/16)]^(8/27)}^2` ("can be used for all Ra and Pr, although 8.13a is more accurate for laminar conditions"). Example 8.1 (page 435): Pr 0.71, Ra 6.78e7, k 0.02672, L 0.30 m, Nu 47.33, h 4.22 W/m2K.

```
Churchill-Chu laminar form, Lienhard Example 8.1: book Nu 47.33 h 4.22 | formula Nu 47.34 h 4.22 | program Nu 49.7393 vs formula at the same Ra 49.7393 (Ra 8.315e+07)
```

The formula reproduces the book to 0.02 %; the program's `h_natural_vertical` equals the formula at its own Rayleigh number (its air properties differ from the book's, so its Ra differs). **Limit:** the original 1975 paper (Int. J. Heat Mass Transfer 18, 1323) is paywalled and was not opened; its conclusion about the all-range form is quoted in Jaffer (2023), page 3 ("provides a good representation ... over a complete range of Ra and Pr from 0 to infinity even though it fails to indicate a discrete transition"). Jaffer's Table 6 gives the root-mean-square relative errors of the form against the four data sets that Churchill and Chu used (King 13.5 %, Jakob 4.7 %, Cheesewright 16.4 %, Saunders 5.3 % for Jaffer's own formula, within 1 % of Churchill and Chu's).

### 3.2 The two forms against each other (Pr 0.71)

| Ra | laminar 8.13a | general 8.13b | laminar against general |
| --: | --: | --: | --: |
| 1e4 | 5.82 | 5.43 | +7.2 % |
| 1e5 | 9.82 | 9.21 | +6.6 % |
| 1e6 | 16.94 | 16.56 | +2.3 % |
| 1e7 | 29.60 | 31.21 | -5.2 % |
| 1e8 | 52.10 | 61.07 | -14.7 % |
| 1e9 | 92.13 | 122.86 | -25.0 % |

These repeat the numbers of `research/effective-conductivity` 4.7 from the printed equations, which now have a read source. The all-range form includes the turbulent rise, as Lienhard says.

### 3.3 The Hollands horizontal-layer equation: which exponent (`study_natural_convection_sources.py`, part 2)

Source (**read**, page 5 of the open ASHRAE preprint OR-05-4-3, as an image): equation 9, the Rohsenow et al. (1985) form `Nu = 1 + (1 - Ra_cr/Ra)* [k1 + 2 (k2)^(1 - ln k2)] + [(Ra/5830)^(1/3) - 1]* [1 - exp(-0.95 ((Ra_cr/Ra)^(1/3) - 1)*)]` with `k1 = 1.40`, `k2 = Ra^(1/3)/450.5`; equation 14, Hollands et al. (1976) for a wide layer, `Nu = 1 + 1.44 (1 - 1708/Ra)* + [(Ra/5830)^(1/3) - 1]*`.

```
Ra        | 1976 (eq 14) | ISO 15099 (eq 9) | ht code (1/3) | ht doc (1/5) | ht with 5830
2e+03     |  1.2102 |  1.2044 |  1.2045 |  1.2045 |  1.2045
1e+04     |  2.3911 |  2.3579 |  2.3604 |  2.3604 |  2.3585
1e+05     |  3.9944 |  3.9562 |  3.9610 |  3.9597 |  3.9570
1e+06     |  6.9937 |  6.9998 |  7.0115 |  6.9631 |  7.0029
1e+07     | 13.4102 | 13.9252 | 13.9621 | 13.3895 | 13.9435
```

* The **cube root** (the `ht` code) is the exponent of the printed ISO form (`k2` carries `Ra^(1/3)` explicitly); its constants are the Prandtl 0.71 values of the 1984 ones (75 exp(1.5/sqrt(0.71)) = 444.9 against 450.5; 1.44/(1 + 0.018/0.71 + 0.00136/0.71^2) = 1.40). The documentation's fifth root is a misprint: it is 3.7 % low at Ra 1e7 against the ISO form.
* The two printed forms differ from each other by 0.3 % up to Ra 1e5 and 3.8 % at 1e7; the 1976 equation has no logarithmic term.
* `ht` uses 5803 where the 1976 equation prints 5830 (a 0.03 % effect at Ra 1e4).
![Hollands forms](figures/fig_01_hollands_forms.png)

*Figure 1: `figures/fig_01_hollands_forms.png`. Left, the four forms at Pr 0.71; right, the difference of each from the ISO 15099 form (the fifth-root variant leaves it above Ra 3e5).*

* **Limit:** this decides the exponent by a secondary source that prints the Pr 0.71 form, not by Hollands (1984), which is not obtained. The program does not use the Hollands equation today (it is for the gap above 7 mm in `docs/research.md` R3).

### 3.4 Horizontal plates and the mixed-convection blend (`study_natural_convection_sources.py`, parts 3 and 4)

**Horizontal plates.** The program uses `Nu = 0.54 Ra^(1/4)` (up to 1e7) and `0.15 Ra^(1/3)` above for the face looking up, `0.27 Ra^(1/4)` for the face looking down, with `L = A/P` (McAdams, through `ht`; the original was not opened). Lienhard (pages 435 and 436) prints, for the same geometry, Raithby and Hollands: equation 8.37a `Nu = 0.560 Ra^(1/4) / [1 + (0.492/Pr)^(9/16)]^(4/9)` with the correction 8.37b `Nu = 1.4/ln(1 + 1.4/Nu)` when Nu is 10 or less (1 < Ra < 1e7, `L* = A/P`), equation 8.35 above Ra 1e7; for a hot face looking down, Fujii and Imura (8.38) `Nu = 0.58 Ra^(1/5)` (Ra 1e6 to 1e9, a two-dimensional plate within 3 degrees of horizontal).

```
a x b mm, dT, Ra | h up program, R&H, change of the total h (eps 0.9) | h down program, Fujii-Imura
  40 x  30 dT   5 Ra 317     | up  6.891  7.401 ( +4.2 %) | down  3.446  5.550
  40 x  30 dT  60 Ra 2.51e+03| up 12.513 12.092 ( -2.2 %) | down  6.256  9.086
 100 x  80 dT  20 Ra 1.96e+04| up  7.628  6.870 ( -5.7 %) | down  3.814  4.998
 160 x 100 dT  60 Ra 1.16e+05| up  9.090  7.846 ( -7.8 %) | down  4.545  5.449
 300 x 200 dT   5 Ra 1.09e+05| up  4.237  3.666 ( -6.0 %) | down  2.118  2.548
 300 x 200 dT  20 Ra 3.87e+05| up  5.950  4.734 (-10.4 %) | down  2.975  3.359
 300 x 200 dT  60 Ra 8.62e+05| up  7.693  6.115 (-10.8 %) | down  3.846  4.172
```

(the full table of twelve cases is printed by the script). For boards of 100 mm and more the program's up-face coefficient is 7 to 26 % above Raithby and Hollands' (the percentage in the third column is the change of the **total** h with radiation of emissivity 0.9 if the source were used: -3 to -11 %, so the board would be hotter). Fujii and Imura's correlation is outside its range here (Ra below 1e6) and is for a two-dimensional plate, so the 30 to 40 % excess of its h over the program's is a bound on how conservative the down face is, not a correction.

![Horizontal plate coefficient](figures/fig_02_horizontal_plate_h.png)

*Figure 2: `figures/fig_02_horizontal_plate_h.png`. The change of the total coefficient (with radiation of emissivity 0.9) if Raithby and Hollands replaced the program's up-face correlation, against the surface excess, for four board sizes.*

**Mixed convection.** Jaffer and Jaffer (arXiv 2401.09469, Table 4) combine natural and forced heat transfer as an l_p norm: `p` between sqrt(3) and 3 for a vertical plate (aiding and opposing), `p = 2` for a level flow over an upward-facing plate, `p = 5` for a downward-facing plate. The program uses `p = 3` for every orientation. For a hot 100 mm horizontal board (60 C in 20 C air, h_n 8.44 W/m2K):

| air speed (m/s) | h forced | h with p = 3 (program) | h with p = 2 | p = 3 against p = 2 |
| --: | --: | --: | --: | --: |
| 0.2 | 5.54 | 9.17 | 10.10 | -9.2 % |
| 0.5 | 8.76 | 10.84 | 12.16 | -10.9 % |
| 1.0 | 12.39 | 13.58 | 14.99 | -9.4 % |
| 2.0 | 17.52 | 18.15 | 19.45 | -6.7 % |

The program's convective coefficient is 7 to 11 % lower (the board hotter) than with the exponent that Jaffer finds for this orientation. **Limit:** Jaffer's p = 2 is a fit to data of a rough plate in a wind tunnel; Churchill (1977) is not obtained, so whether `Nu^3 = Nu_F^3 + Nu_N^3` is Churchill's rule is still not confirmed. The forced laminar form `Nu = 0.664 Re^(1/2) Pr^(1/3)` is read in Lienhard (page 311); the turbulent `0.037 Re^(4/5) - 871` is not in that book (the Reynolds number of a board in a fan flow is below 5e5 in practice).

### 3.5 Effective-medium formulas, with page and equation (`study_effective_medium_sources.py`, `lib/cond2d.py`)

Sources (**read**, Milton, *The Theory of Composites*, the author's open PDF): chapter 3, section 3.1 and 3.2, pages 47 to 50: equations 3.1 to 3.6 (the pointwise 90-degree rotation, `s' = 1/s` and `s*' = 1/s*`), 3.9 (Keller: `s*(s2, s1) = s1 s2 s*(s1, s2) / det s*(s1, s2)`), 3.10 and 3.11 (a phase-interchange-invariant isotropic medium has `det s* = s1 s2`; the checkerboard has `s* = sqrt(s1 s2)`), Figure 3.1. Page 116: equation 7.9 (coated cylinders, `s* = s2 + 2 f1 s2 (s1 - s2) / (2 s2 + f2 (s1 - s2))`) and 7.10 (the Hashin-Shtrikman bounds for d = 2 or 3, phases labelled s1 > s2). Pages 195 and 196: equations 10.31 (`f1 (e1 - e*)/(e1 + 2 e*) + f2 (e2 - e*)/(e2 + 2 e*) = 0`) and 10.32 (its solution) for **spherical** grains; the book prints no two-dimensional form. For disks the same step applied to equation 7.9 (the dilute limit `s* = s0 + 2 f s0 (s1 - s0)/(s1 + s0)`) gives `f1 (s1 - s*)/(s1 + s*) + f2 (s2 - s*)/(s2 + s*) = 0`, whose positive root is `s*^2 - (s1 - s2)(2 f1 - 1) s* - s1 s2 = 0` (**derived here, not read**: the derivation is the step of Milton's section 10.5 with d = 2).

```
1. Milton 7.10 (d = 2) against the repository forms: lower 2.22e-16, upper 1.55e-15 (relative); 13/7 = 1.857143, 28/13 = 2.153846; Bruggeman d=3 against 10.32: 4.44e-16
2. Bruggeman d = 2 (derived from 7.9) against the repository function: max relative difference 3.79e-14
3. Square array of disks f 0.3, ratio 10, grids 48/96/192: 1.6856, 1.6699, 1.6608 ; HS bounds (lower = coated cylinders 7.9) 1.6506 2.7168
   random 8 x 8 blocks, p1 0.3: mean 1.8228 std 0.1628 ; Bruggeman 2D 1.8387
4. Keller product s*(10,1) s*(1,10) / 10 on the disk array at 48/96/192: 1.0179, 1.0089, 1.0042
   checkerboard at 8/16/32/64 cells per square: 2.7752, 2.9305, 3.0251, 3.0817 ; sqrt(10) 3.1623 ; extrapolated 3.1656 (difference ratio 0.597)
```

* The `conduction.py` Hashin-Shtrikman forms equal the printed bounds (7.10) and the 2D Bruggeman root equals the repository function: the formulas written from memory are right.
* The independent periodic solver (`lib/cond2d.py`, a finite-volume solution with a mean gradient) lies inside the bounds, approaches the lower bound (coated cylinders) from above as the grid is refined (the Maxwell value is 1.6506), reproduces the phase-interchange product to 4 % at 192 cells and **converges to the checkerboard value sqrt(s1 s2)** with the corner-singularity rate of a first-order cell scheme (difference ratio 0.6; Richardson 3.166 against 3.162).
* The random medium of 8 x 8 blocks, 30 % phase 1, gives 1.82 +- 0.16 against Bruggeman's 1.84 (a statistical agreement, not a proof; a pixel-by-pixel random medium gives -18 % because the pixel discretisation of a random cell medium is not self-dual).
* **Limit:** the originals (Bruggeman 1935, Hashin and Shtrikman 1962, Keller 1964, Dykhne 1970) and Torquato's book were not obtained; the 2D Bruggeman form is derived, not read.

### 3.6 Culham and Yovanovich (1998) above Biot 60 (`study_culham_truncation.py`, `lib/cosine_stack.py`)

Pages 465 and 466 were re-read as images: Table 2, equation 11 `k_e = 1/(R_solid A/L)` ("when the heat flow is one-dimensional the cross-sectional flow area and the flow length are clearly defined but in two-dimensional flow these values are difficult to quantify"), the convective boundary-condition section (the wall temperature of equation 8 is the mean over the solid-fluid interface; Bi = h l / k1, l the side of the source), and Figure 5 (the plateau, about 4.8 W/mK for Bi above 100, read from the plot). The text says the effective conductivity "approaches a constant value above Bi = 100".

An independent cosine-series solution of the coupon (`lib/cosine_stack.py`: 2 x 2 transfer matrices per mode, film applied over the whole top face, the only separable case) gives, for the base case and the single layer of the same thickness and the same number of modes:

```
modes per direction | h = 5 W/m2K: R_solid, k_e (paper 8.28) | h = 1e4 W/m2K: R_solid, k_e (paper plot about 4.8)
   3 |  3.9544   8.496 |  0.1222   0.559
   7 |  4.2038   8.143 |  0.1366   0.596
  11 |  4.2830   8.014 |  0.1419   0.609
  21 |  4.3423   7.913 |  0.1463   0.615
  41 |  4.3801   7.847 |  0.1496   0.611
 201 |  4.3967   7.818 |  0.1520   0.595
```

* **The excess over the converged value at the base case.** The paper's 8.28 lies between the 5-mode (8.50) and 7-mode (8.14) truncations, and 6 % above the converged 7.82; the independent 3D solver of `research/effective-conductivity` 4.2 gives 7.81 for the same layer order, so the converged series and the solver agree to 0.1 %. The paper's series stops at an unrecorded number of terms (the first pages describe a minimised, truncated series), so a coarse truncation is a possible explanation of the 2 to 6 % by which this project's reproductions sit below the paper, not a proved one.
* **Combined with the thickness.** The 1.62 mm of the text instead of 1.6501 mm gives 8.03 W/mK in the solver (`research/effective-conductivity` 4.2); a truncation to 7 modes raises a converged value by 4 % (8.14 against 7.82), so 8.03 x 1.04 = 8.35 W/mK, within 1 % of the paper's 8.28: the two untested causes together are enough to account for the gap, which is still a hypothesis (the paper's number of terms is not printed in the pages read).
* **The plateau is not a truncation effect.** At Bi 625 the effective conductivity is 0.56 to 0.62 W/mK for every truncation from 3 to 201 modes; the series agrees with the FVM and the 3D solver (0.6) at the converged limit.
* The film under the source changes `R_solid` (4.40 against 5.12 K/W without it in the 3D solver) because it removes 0.4 of the 2.5 W at the 127 K rise, but little the effective conductivity (7.82 against the solver's 7.81 with no film under the source), because the single layer is computed the same way.
* **What stays open:** the plateau of Figure 5 (4.8 W/mK) is not reproduced by any definition, truncation or boundary treatment tried (see also `research/effective-conductivity` 4.9); the pages of the paper that define the series coefficients (equation 10, the spreading resistance as a function of Bi) are the next to read. The 1.62 mm of the text against 1.6501 mm of the stack explains about half of the shortfall of the base case.

![Series truncation](figures/fig_03_culham_series_truncation.png)

*Figure 3: `figures/fig_03_culham_series_truncation.png`. Effective conductivity against the number of series modes for h = 5 (left, the paper's 8.28 dashed) and 1e4 W/m2K (right, the paper's plateau read from Figure 5, dashed).*

### 3.7 Muzychka and others, and Lemczyk and others

**Muzychka, Culham and Yovanovich (2003), cases 1 (b) and 2** (`study_muzychka_more_cases.py`; Tables 2, 3 and 4 read in the text layer, pages 183 and 184). Case 1 (b): the plate of case 1 (a) (300 x 300 x 10 mm, k 10, h 10 on the bottom, 25 C, sources 10 W at (90, 90) and 15 W at (210, 210), 25 x 25 mm) with a 2 mm layer of k 350 on top. Case 2: a baseplate 50 x 50 x 10 mm, k 150, h 400 on the bottom, four 10 x 10 mm sources (10 W at (12.5, 12.5), 25 W at (37.5, 12.5), 20 W at (12.5, 37.5), 15 W at (37.5, 37.5) mm); the ambient is not in the extracted table and 25 C is assumed as in the other cases (the result reproduces the paper's centroids, which supports it).

```
Case 1b: paper centroid [56.55, 59.94], mean [56.05, 59.19]; Fourier series (Culham) centroid [56.63, 60.08]
  independent 3D solver: centroid [56.56, 59.97], mean [56.07, 59.23], bottom mean 52.78
  fvm: [56.52, 59.91] mean [56.03, 59.17]   fdm: [56.49, 59.88] [56.0, 59.14]   solid3d: [56.53, 59.92] [56.04, 59.18]   analytic: [56.52, 59.91] [56.05, 59.2]   lumped: [56.38, 58.77]
Case 2: paper centroid [97.4, 103.82, 101.28, 99.94], mean [96.85, 102.33, 100.1, 99.07]
  independent 3D solver: centroid [97.41, 103.85, 101.31, 99.95], mean [96.92, 102.53, 100.26, 99.19]
  fvm: centroid [94.46, 98.3, 96.62, 96.13]   fdm: [94.5, 98.26, 96.61, 96.14]   solid3d: [95.39, 99.23, 97.56, 97.07]   analytic: [94.46, 98.3, 96.63, 96.13]   lumped: [94.74, 97.56, 96.42, 95.88]
```

* The independent solver reproduces both cases (case 1 (b) within 0.03 K at the centroids; case 2 within 0.03 K; the means 0.07 to 0.2 K above the paper's, which section 3.10 explains by the sub-slab count). The first rows of case 2 were 102.53 K at 8 sub-slabs and extrapolate to 102.373 K against the paper's 102.33.
* The program's models reproduce the **compound plate** (case 1 (b)) within 0.05 K (a copper layer of 2 mm k 350 over a dielectric gap of 10 mm k 10: 0.1 % of the rise), the Lumped within 1.2 K in the second source.
* In **case 2** the one-layer models sit 2.9 to 5.5 K below the independent solver at the centroids (4 to 7 % of the rise) and the 3D solid 2.0 to 4.6 K (its slab is also one node thick). The bound `q'' t / (2 k)` of the through-thickness gradient (3.3, 8.3, 6.7 and 5.0 K for the four sources) is not exceeded: the observed shortfalls are 67 to 89 % of it. This is the effect measured in `research/effective-conductivity` 4.6; a 10 mm plate under 10 x 10 mm sources is where the thick-plate check applies.

**Lemczyk, Mack, Culham and Yovanovich (1992)** (`study_lemczyk_1992.py`, `lib/strip2d.py`): pages 414 to 417 read as images. The model is two-dimensional (Fig. 2 and 3): a cell of width L1 and thickness t, adiabatic ends, a trace of width w held at Tc on the top face (case a, film h2 over the whole top face, equation 27 `Q_a = k L2 Tc (Bi2 w/L1 + q_s/Tc)`), mid-buried (case b, half cell, `Q_b = 2 k L2 q_s`), with `h1 = 0` on the surface (case c) or on the bottom (case d); `Psi = k L2 R`. Table 1 gives dimensional heat flows (Tc 90 C above 20 C, h 10 W/m2K, L2 = 1 m).

```
Table 1: w t L1 (um), k | Q_a paper, solver (W) | difference
    10    10    20 0.2 | 0.036 0.0360 | -0.07 %      50  1000   100 0.4 | 0.178 0.1776 | -0.22 %
    10    10    50 0.2 | 0.089 0.0894 | +0.51 %      250 2000   500 0.4 | 0.884 0.8739 | -1.15 %
    50   100   100 0.2 | 0.179 0.1792 | +0.09 %      250 1000  1250 0.4 | 2.120 2.1243 | +0.20 %
```

(sixteen rows in all, 15 within 0.52 %). Tables 2 and 3, the `w/L1 = 0.1` rows: the solver differs from the paper by at most 4.1 % for case a, 9.1 % for b, 9.8 % for c and 8.2 % for d (typically 0.1 to 2 %); the larger values are at Bi 0.01 for c and at Bi 100 for b and d. **A published number that does not add up:** for a trace as wide as the cell (`w/L1 = 1`) case c is one-dimensional, `Q = h2 L1 Tc` and `Psi_c = 1/Bi2`, and the solver gives 100.000 at Bi 0.01 and 10.0000 at Bi 0.1 against the paper's 90.91 and 9.901 (the same table gives exactly 1/Bi at Bi 1 and 10); the paper's own approximate solution (a minimised, truncated series) is off by 9 % and 1 % in that limit, and the 8 to 10 % differences in the case c rows of Table 2 have the same size.

![Lemczyk tables](figures/fig_04_lemczyk_tables.png)

*Figure 4: `figures/fig_04_lemczyk_tables.png`. Left, the heat flows of Table 1 against the independent solver; right, the factors Psi of Tables 2 and 3 (cases a to d) against the solver, on logarithmic axes.*

**The program on the Lemczyk cells:** not run (the cells are 10 to 2000 micrometres; the program's smallest representable board and cell size make the thin-trace rows a different problem). The Muzychka and Culham reproductions of the earlier folder are the program-level test of the same physics.

### 3.8 The Foster chain (topic 12): Nexperia AN11261 (`study_foster_cauer.py`, `lib/rc_ladder.py`)

Source (**read**, Rev. 5.0, 18 March 2021, opened from a mirror because the vendor host refuses): page 4, equations 2 and 3, `Zth(t) = sum R_i [1 - exp(-t/tau_i)]`, `tau_i = R_i C_i`; the Foster values "are not geometrical" and the network cannot be connected to another; the Cauer network has its capacitors to the ambient and nodes of physical meaning; "an n-stage Cauer model can be derived from an n-stage Foster model and they will be equivalent". Page 6, Fig. 6: the Cauer netlist of the BUK7S1R0-40H (R 0.00272144, 0.0220255, 0.00713124, 0.185679, 0.182443 K/W; C 9.29451e-5, 5.14739e-4, 1.95047e-3, 3.05028e-3, 2.79554e-2 J/K); Table 1: Rth(j-mb) typical 0.35, maximum 0.4 K/W; example 2 (Table 3, Fig. 11 and 12): a 120 W pulse of 4 ms gives Zth = 0.26 K/W at Tmb = 125 C.

```
Sum of the Cauer resistances: 0.4000 K/W (datasheet Rth(j-mb): typical 0.35, maximum 0.4; Fig. 11 and 12: Rth = 0.4)
Foster equivalent: R_i [0.25439, 0.12357, 0.01792, 0.00218, 0.00194] K/W, tau_i [6.33e-3, 8.47e-4, 1.51e-5, 6.66e-6, 2.14e-7] s; sum 0.4000 K/W
Zth(t) of the ladder (matrix exponential) against the Foster form, largest difference 5.94e-15 K/W
First pulse of example 2: 120 W for 4 ms -> Zth(4 ms) = 0.2637 K/W (paper 0.26), rise 31.6 K, junction 156.6 C on the 125 C base
```

The ladder reproduces the published numbers, and the Foster form obtained by the pole decomposition equals the ladder to machine precision (the matrix exponential does not use the Foster formula). All Foster `R_i` and `tau_i` are positive. **The program's models** have no Foster chain (it is planned, topic 12); this is the check that a future implementation must pass. The rest of the note (examples 1 and 3, pages 12 and 13) was read for the SPICE set-up only.

![Foster and Cauer Zth](figures/fig_05_foster_cauer_zth.png)

*Figure 5: `figures/fig_05_foster_cauer_zth.png`. The step response of the ladder, its five Foster terms and the published 0.26 K/W at 4 ms.*

### 3.9 Gerber import (topic 15) and multigrid (topic 16)

**Gerber specification, revision 2026.05** (**read** where cited: the contents, section 2.11 pages 25 and 26, section 4.10.4.8 pages 112 and 113; downloaded from the Ucamco downloads page, 219 pages; the revision number is the one the earlier open item asked to be read). `study_gerber_spec_examples.py` runs three of its examples through the project's independent reader (`research/gerber-import/lib/native_gerber.py`) and compares the area with what the coordinates give:

```
Two square boxes: expected 0.39996 mm2 (two rings of the round stroke), reader 0.39995 mm2 (-0.00 %)
Two disjunct areas: expected 132 mm2, reader 131.990 mm2 (-0.01 %)
Region with hole: expected 68 mm2, reader 68.004 mm2 (0.01 %)
```

The reader handles contours with fully-coincident segments (a cut-in that makes a hole or two regions), as the specification defines. **Limit:** three examples of 219 pages; the rest of the specification (apertures macros, step and repeat, X2 attributes) was not re-read, and the program's own import does not exist yet (the reader is a research prototype).

**Multigrid** (topic 16, McCormick and Tamstorf, arXiv:2605.17828, 11 pages): the text around Algorithm 3 (the V-cycle) and the statement that iterative multigrid has "uniformly bounded convergence factors per cycle at a cost proportional to the number of degrees of freedom" were read. `lib/mg2d.py` writes Algorithm 3 for the five-point Poisson problem (red-black Gauss-Seidel V(2,1), full weighting, bilinear interpolation): the residual reduction per cycle is 0.06 at 15 points per side, 0.07 at 31, 63, 127 and 255 (independent of h), and the error of 63 points against the exact solution of `sin(pi x) sin(pi y)` is 2.0e-4 (second order). The primer prints no number to compare with, only the property, which is what is reproduced.

### 3.10 Grid convergence index with three grids (`study_gci_references.py`, `lib/gci.py`)

Source (**read**): Celik, Ghia, Roache and Freitas (2008), the open ASME copy, equations 3 to 7. `lib/gci.py` reproduces the three columns of its Table 1 (p 1.54, 0.75 and 1.51 against 1.53, 0.75 and 1.51; the extrapolated values to 4 digits; GCI 2.2, 1.1 and 0.5 %). It was then applied to the mean temperature of one source on three grids:

```
Case 2, mean temperature of the hottest source (25 W), 4 sub-slabs
  independent cells (0.125, 0.25, 0.5) mm: 102.863, 102.866, 102.875 K | p 1.99, extrapolated 102.863 K, GCI fine 0.00 % (0.001 K)
  fvm         cells (0.5, 1.0, 2.0) mm: 97.704, 97.814, 97.672 K | p 0.37, extrapolated 97.331 K, GCI fine 0.48 % (0.466 K)
  fdm         cells (0.5, 1.0, 2.0) mm: 97.716, 97.684, 97.685 K | p 5.91, extrapolated 97.717 K, GCI fine 0.00 % (0.001 K)
  independent, 0.5 mm cells, 16/8/4 sub-slabs through the thickness: 102.419, 102.525, 102.875 K | p 1.72, extrapolated 102.373 K, GCI fine 0.06 %
Case 3, mean temperature of the centre source
  independent cells (0.5, 1.0, 2.0) mm: 80.274, 80.276, 80.287 K | p 2.00, extrapolated 80.273 K, GCI fine 0.00 % (0.001 K)
  fvm         cells (0.5, 1.0, 2.0) mm: 79.111, 79.113, 79.123 K | p 2.01, extrapolated 79.110 K, GCI fine 0.00 % (0.001 K)
  fdm         cells (0.5, 1.0, 2.0) mm: 79.093, 79.076, 79.041 K | p 1.02, extrapolated 79.110 K, GCI fine 0.03 % (0.021 K)
```

* **The independent reference converges at second order in the plane (p 1.99 and 2.00), and the grid error of a source on cell edges is a thousandth of a kelvin.** The reference's uncertainty is in the **sub-slab count through the thickness**: 102.875 K (4), 102.525 K (8), 102.419 K (16); extrapolated 102.373 K, within 0.04 K of the paper's 102.33 K. The earlier "0.3 to 0.4 K overstatement of the 2.5 mm cells" of `research/models-comparison` and `research/effective-conductivity` 4.6 is at least partly this: a reference with few sub-slabs reads high by 0.1 to 0.5 K on a 10 mm plate.
* The program's FVM at case 3 converges at order 2.01 and the FDM at 1.02 (its node sampling), both to a thousandth of a kelvin at 0.5 mm; on case 2 the sources at 7.5 mm edges do not sit on cell edges of 1 or 2 mm, and the FVM series is not monotone (p 0.37, GCI 0.48 % = 0.47 K): for sources off the cell grid the order is not the formal one and the GCI is an upper estimate of the sampling noise.
* Run with `r = 2`; the guideline of the paper asks for `r > 1.3`.

### 3.11 Lee's equations and Yovanovich's Table 3 (`study_lee_yovanovich_check.py`)

Lee (Electronics Cooling, January 1998): the equation images (the page loads them lazily; the files were downloaded and read) give equation 1 `Rc = (sqrt(Ap) - sqrt(As)) / (k sqrt(pi Ap As)) (lam k Ap R0 + tanh(lam t)) / (1 + lam k Ap R0 tanh(lam t))` and equation 2 `lam = pi^(3/2)/sqrt(Ap) + 1/sqrt(As)`; the worked example (aluminium 100 x 100 x 1.3 mm, 25 x 25 mm source, R0 1.0 K/W) prints lam 95.68 1/m, tanh 0.124, `lam k Ap R0` 191.4 and Rc = 0.0846 x 7.743 = 0.66 K/W.

```
Lee 1998 example: lambda 95.68 1/m (article 95.68), Rc 0.6566 K/W (article 0.66 = 0.0846 x 7.743), total 1.657 K/W (article 1.66)
Yovanovich 2003 Table 3, isoflux column (m = 0): e | table | series | difference
  0.1 | 0.9401 | 0.9401 | -0.0000     0.5 | 0.4092 | 0.4092 | +0.0000
  0.2 | 0.8009 | 0.8010 | +0.0001     0.8 | 0.1008 | 0.1008 | +0.0000
```

The formulas are read and the example is reproduced; the program's plate model against the same example is `research/effective-conductivity` 4.4 (centre 0.668 against 0.66). Yovanovich (2003) Table 3 (page 174) was read in the text layer with all its columns (m = 1/2, 0, -1/2 and four reference solutions), and the isoflux column equals the Bessel series to 1e-4 at all eight radii.

### 3.12 Heatsink scenarios (topic 13) and the virtual JEDEC test (topic 14)

* **Topic 13.** Its source is the same as 3.11 (Lee, equations 1 to 4, the location factor `Cf` of the article's Figures 4 and 5, the corner and edge cases by the method of images) and Muzychka and others (2003) for the eccentric sources: the example of Lee (centre 0.66, edge midpoint 1.29, corner 2.38 K/W) was reproduced by the plate model in `research/effective-conductivity` 4.4 (0.668, 1.284, 2.275). Nothing new was run here.
* **Topic 14.** No open copy of JESD51-2A, -3, -7, -12 or -14 was found; the standards are the source of the planned virtual test, and the closest open material is the Nexperia note of 3.8 and the datasheet numbers already in `research/power-calculator`. **Not obtained, no case reproduced.**

## 4. Limits of the study

* The originals paywalled or not reachable are listed at the end of `research/theory/BIBLIOGRAPHY.md` (section 18); statuses were raised only where a page or equation was read.
* Equation numbers and tables were read from text layers or from images at 100 to 190 dpi; digits of Tables 2 and 3 of Lemczyk were read from an image.
* The series solver treats the film over the whole top face; the paper's treatment of the film under the source is not recorded.
* The independent solvers are finite-volume or cosine-series codes of this folder with their own tests; they share no code with the program, but the 3D solver of `research/effective-conductivity/lib/layered3d.py` is used for 3.7 and 3.10.
* Runs are modest (the largest 3D solve has 1.3 million cells).

## 5. What this means for the program

See `INTEGRATION.md`: no change is made; the findings are (a) a citation text for `convection.py` and `docs/theory.md`, (b) the horizontal-plate and mixed-convection differences with their measured size, (c) the validation rows (cases 1 (b), 2, Lemczyk) for `docs/validation.md`.

## What was read and what was not verified

**Read in full or at the pages named (R):** Lienhard, *A Heat Transfer Textbook* 6.00 (pages 311, 433 to 436, plus search of the whole text); ASHRAE preprint OR-05-4-3, page 5 (equations 9 to 14); Jaffer (arXiv 2201.02612, searched; page 5) and Jaffer and Jaffer (arXiv 2401.09469 / `blend.pdf`, searched and the passages quoted read); Milton, *The Theory of Composites*, pages 47 to 50, 116, 195 and 196; Culham and Yovanovich (1998), pages 465 and 466 as images; Lemczyk and others (1992), pages 414 to 417 as images (Tables 1 to 3 digits read at 190 dpi); Muzychka and others (2003), examples and Tables 1 to 4 (text layer); Yovanovich (2003), page 174 (Table 3) and the page of the series; Lee (1998), the article text and its two equation images; Celik and others (2008), pages 4 to 9; Nexperia AN11261 Rev. 5.0, pages 1 to 12; Ucamco Gerber specification 2026.05, contents and pages 25, 26, 112, 113; McCormick and Tamstorf (arXiv 2605.17828), the text around Algorithm 3 and section 8.

**Reproduced with an independent solver:** the vertical-plate Example 8.1 (formula); the ISO 15099 and `ht` Hollands forms (formula, no solver needed); the Hashin-Shtrikman bounds, the 2D Bruggeman equation, the checkerboard and the phase interchange (periodic finite-volume solver); the Culham coupon's `R_solid` and effective conductivity (cosine series, base case within 6 % of the paper's 8.28, plateau not reproduced); Muzychka and others cases 1 (b) and 2 (3D solver, centroids within 0.03 K); Lemczyk Tables 1 to 3 (2D solver); the Cauer and Foster forms of AN11261 (matrix exponential); three Gerber examples (the project's reader); a V-cycle (the property, no number); Celik Table 1; Lee's example and Yovanovich's Table 3 (series).

**Run on the program's models:** the Churchill-Chu form and the horizontal and mixed correlations of `convection.py`; the five models on Muzychka cases 1 (b) and 2; the FVM and FDM in the GCI study. Not run on the program: Lemczyk (scale), topics 12 to 16 (not in the program).

**Not verified, or from memory:** the original Churchill-Chu, Churchill, Hollands, Keller, Dykhne, Bruggeman, Hashin-Shtrikman papers and Torquato's book (not obtained); the 2D Bruggeman equation is derived, not read; Jaffer's p = 2 is a fit to a rough plate; the ambient of Muzychka's case 2 (25 C) is assumed; the plateau of the Culham figure 5 is not explained; the film treatment of the paper's series is not known; the exponent of `ht`'s fifth-root form is called a misprint from a secondary source; JEDEC, IPC, ASTM and ASME standards were not obtained (listed in the bibliography).
