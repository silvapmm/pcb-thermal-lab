# Effective conductivity, spreading resistance and the layered idealisation: published test cases reproduced

Status: **open, no change to the program required**; two optional proposals and a reference solver are in `INTEGRATION.md`. Studies: `study_culham_1998.py`, `study_lee_spreading.py`, `study_program_vs_coupon.py`, `study_muzychka_2003.py`, `study_natural_convection.py`; solver: `lib/layered3d.py`; figures: `make_figures.py` (data) and `make_diagrams.py` (schematics), one numbering.

## 1. The questions

1. Can the published numerical cases on the effective conductivity of a laminated board (Culham and Yovanovich) and on the spreading resistance of a source on a plate (Seri Lee; Muzychka, Culham and Yovanovich) be reproduced with an **independent** solver, so that the solver can serve as a reference for the program?
2. Do the five models of the program agree with that reference on a board of the same kind?
3. Where does the layered idealisation (one temperature node per layer) stop being valid?
4. Does the natural convection of a vertical board in the program agree with its source, and what would the other form of the same correlation change?

## 2. Findings in short

* **The solver reproduces the publications.** Seri Lee's plate: centre 0.668 against 0.66 K/W (+1.2 %), edge midpoint 1.284 against 1.29 (-0.4 %), corner 2.275 against 2.38 (-4.4 %; the article claims about 5 %). The cross of five sources of Muzychka and others: maximum 80.62 against 80.61 C and area-weighted mean source temperature 78.90 against 78.87. Their first case within 1 % of the rise, between the paper's two solutions. The five layer orders of Culham and Yovanovich: 2 to 6 % below the paper (14.67, 11.30, 7.81, 6.99, 4.74 against 15.02, about 11.6, 8.28, about 7.4, 5.00 W/mK).
* **The layer order changes the effective conductivity by a factor of 3** (15 to 5 W/mK for the same copper and FR4), the source size and position and the film coefficient change it too, and none of the averages of the series and parallel conductivities is a good estimate (the geometric mean, 2.7 W/mK, can be 70 % off). The program does not homogenise a stack: every copper layer is a node and every gap a resistor, so the order is represented; an effective conductivity should stay out of the program.
* **The five models of the program agree with the solver within 0.3 %** (FDM 1.2 % for a 5 mm source on 50 mm) on the Cu / FR4 / Cu version of the coupon, for sources of 1 % to 100 % of the board area.
* **One node through the thickness falls short by about q'' t / (2 k) at the surface under a source**: 2.3 % of the rise for a 10 mm plate of k = 50, 13 % for k = 10 (predicted 13.2 % and observed 12.8 %); irrelevant for a 35 um copper layer.
* **Natural convection:** the program's vertical-plate formula is the general Churchill and Chu form and reproduces the worked example of the library `ht` to the digit; the laminar form of the same authors differs from +7 % (Ra 1e4) to -25 % (Ra 1e9), and in the coefficient of a 50 to 200 mm board by +6.5 % to -10 %. No change is proposed until the paper is read.
* **Not explained:** at a Biot number above about 60 the solver's effective conductivity falls (0.75 W/mK) while the paper's plot stays at about 4.8; the paper's mean base temperature of case 1 (53.06 C) is 0.28 K above the energy balance (52.78 C).

## 3. Folder layout

| File | What it is |
| :-- | :-- |
| `lib/layered3d.py` | The independent 3D finite-volume solver of a laminated block (about 120 lines, SciPy only). |
| `scripts/study_culham_1998.py` | The coupon of Culham and Yovanovich: limits, layer orders, source size and position, film coefficient (about 15 minutes). |
| `scripts/study_lee_spreading.py` | Seri Lee's plate: centre, edge, corner, in 3D and as a thin plate (seconds). |
| `scripts/study_program_vs_coupon.py` | The five models of the program against the solver on the Cu / FR4 / Cu coupon (about 40 seconds). |
| `scripts/study_muzychka_2003.py` | The cases of Muzychka and others, and the thickness sweep (about 15 seconds). |
| `scripts/study_natural_convection.py` | The two forms of Churchill and Chu and the effect on h (seconds). |
| `scripts/make_figures.py`, `scripts/make_diagrams.py` | The data figures (read `out/*.json`, written by the studies) and the schematics. |
| `tests/test_layered3d.py` | The solver against a series circuit, an exact energy balance, a uniform layer and three published numbers. |
| `INTEGRATION.md`, `docs/for-the-project-documents.md` | Optional proposals; corrections and text for the project documents. |

## 4. How to run, and the results

```sh
.venv/bin/python research/effective-conductivity/scripts/study_culham_1998.py      # about 15 minutes, writes out/
.venv/bin/python research/effective-conductivity/scripts/study_lee_spreading.py
.venv/bin/python research/effective-conductivity/scripts/study_program_vs_coupon.py
.venv/bin/python research/effective-conductivity/scripts/study_muzychka_2003.py
.venv/bin/python research/effective-conductivity/scripts/study_natural_convection.py
.venv/bin/python research/effective-conductivity/scripts/make_figures.py           # then make_diagrams.py
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/effective-conductivity/tests
```

The tables below are the output of those scripts.

### 4.1 The coupon and what the effective conductivity means

The coupon of Culham and Yovanovich (1998): 50 x 50 mm, five layers (FR4 0.5263 mm of k 0.4, copper 0.0356 mm of k 400), a concentric source of 25 x 25 mm and 2.5 W on the top face, a film coefficient of 5 W/m2K on the free top face and on the bottom, insulated sides. The **solid-body resistance** is `R_solid = (T_source,mean - T_walls,mean) / Q = R_bulk + R_spread`, and the **effective conductivity** is that of the single layer of the same thickness and boundary conditions that gives the same `R_solid`. The solver measures the same quantities and finds the single layer by bisection.

![The coupon and the definition of the effective conductivity](figures/fig_01_coupon_and_definition.png)

*Figure 1: `figures/fig_01_coupon_and_definition.png`.*

Limits (paper: 17.62, 0.42, 9.02, 2.71, 0.82): in-plane 17.64, cross-plane 0.418, arithmetic 9.03, geometric 2.72, harmonic 0.82; the layers add to 1.6501 mm (the paper says 1.62)

The layers add to 1.6501 mm; the paper says 1.62 mm.

### 4.2 The order of the layers (the paper's Table 2)

![The five layer orders](figures/fig_02_five_layer_orders.png)

*Figure 2: `figures/fig_02_five_layer_orders.png`.*

| Case (layers from the top) | this work (W/mK) | paper (W/mK) | source of the paper value | difference |
| :-- | --: | --: | :-- | --: |
| 1: Cu-Cu-FR4-FR4-FR4 | 14.67 | 15.02 | text | -2.3 % |
| 2: Cu-FR4-FR4-FR4-Cu | 11.30 | 11.6 | plot | -2.6 % |
| 3: FR4-Cu-FR4-Cu-FR4 | 7.81 | 8.28 | text | -5.7 % |
| 4: FR4-Cu-Cu-FR4 | 6.99 | 7.4 | plot | -5.6 % |
| 5: FR4-FR4-FR4-Cu-Cu | 4.74 | 5.0 | text | -5.2 % |

Cases 1, 3 and 5 are quoted in the text of the paper; cases 2 and 4 are read from its Figure 2 (about 0.5 W/mK). The solver is below the paper by 2.3 to 5.7 %, steadily; the likely causes (none tested) are the total thickness, the definition of the mean wall temperature and the truncation of the paper's series. The ranking and the spread (15 to 5) are reproduced.

![Effective conductivity of the five layer orders](figures/fig_03_layer_orders_k_eff.png)

*Figure 3: `figures/fig_03_layer_orders_k_eff.png`.*

### 4.3 Source size, source position and film coefficient

| epsilon (source area / board area) | side (mm) | this work (W/mK) | paper (W/mK) | source | difference |
| --: | --: | --: | --: | :-- | --: |
| 0.01 | 5.0 | 3.04 | 3.4 | plot | -10.5 % |
| 0.1 | 16.0 | 7.17 | 7.6 | plot | -5.6 % |
| 0.25 | 25.0 | 7.81 | 8.28 | text | -5.7 % |
| 0.5 | 35.5 | 6.17 | 6.8 | plot | -9.2 % |
| 1.0 | 50.0 | 0.42 | 0.42 | text | -0.5 % |

| source position (assumed layouts) | this work (W/mK) | paper | difference |
| :-- | --: | --: | --: |
| flush with one edge, centred on it (case 2?) | 11.01 | 11.76 (+42 % / +67 % of 8.28) | -6.4 % |
| in a corner (case 3?) | 12.96 | 13.83 (+42 % / +67 % of 8.28) | -6.3 % |

The two layouts of the source position are **assumed** (the text says "a translation along one axis" and "along two axes"; the pictures were not decoded): flush with one edge, centred on it, and in a corner. They give 11.01 and 12.96 against 11.76 and 13.83, the same 6 % below as the base case, which supports the guess.

| film coefficient h (W/m2K) | Biot = h L / k1, L = 25 mm, k1 = 0.4 | this work (W/mK) | paper (plot) |
| --: | --: | --: | --: |
| 0.1 | 0.00625 | 7.98 | 8.6 at the lowest Bi, 4.8 above Bi = 100 |
| 1 | 0.0625 | 7.95 | 8.6 at the lowest Bi, 4.8 above Bi = 100 |
| 10 | 0.625 | 7.63 | 8.6 at the lowest Bi, 4.8 above Bi = 100 |
| 100 | 6.25 | 4.74 | 8.6 at the lowest Bi, 4.8 above Bi = 100 |
| 1000 | 62.5 | 0.75 | 8.6 at the lowest Bi, 4.8 above Bi = 100 |
| 10000 | 625 | 0.61 | 8.6 at the lowest Bi, 4.8 above Bi = 100 |

Up to a Biot number of about 6 the solver follows the paper (7.6 at Bi 0.6, 4.7 at Bi 6; the paper's plot has about 8.2 and 6.0, and 4.8 above Bi 100). **Above Bi 60 the solver gives 0.75 and 0.61 W/mK where the paper's plot stays at 4.8.** It is not a mesh effect (0.77, 0.76 and 0.75 W/mK with cells of 2.5, 1.25 and 0.625 mm at h = 1000). With an isothermal top face touching the edge of the source the heat has a very short path, which lowers the equivalent conductivity; the paper's value cannot be reproduced and is **not explained**. The paper itself says that most electronics applications have Biot numbers of 0.01 to 1.

![Size, position and film coefficient](figures/fig_04_size_location_biot.png)

*Figure 4: `figures/fig_04_size_location_biot.png`.*

### 4.4 Seri Lee's plate: a source at the centre, the edge and the corner

An aluminium base of 100 x 100 x 1.3 mm, a 25 x 25 mm source, a catalogue resistance of 1.0 K/W on the fin side (here a film coefficient on the bottom face), the top outside the source insulated. The constriction resistance is the maximum source temperature minus the mean temperature of the film face, per watt.

![The three source positions](figures/fig_05_plate_source_positions.png)

*Figure 5: `figures/fig_05_plate_source_positions.png`.*

| source position | paper Rc (K/W) | 3D solver | difference | thin plate (2D) | difference |
| :-- | --: | --: | --: | --: | --: |
| centre | 0.66 | 0.668 | +1.2 % | 0.664 | +0.6 % |
| edge midpoint | 1.29 | 1.284 | -0.4 % | 1.280 | -0.8 % |
| corner | 2.38 | 2.275 | -4.4 % | 2.270 | -4.6 % |

The article states that its correlation is accurate to about 5 % for aspect ratios up to 2.5; the corner is at -4.4 %. The thin-plate version (lateral conductance `k t`, the model of the program's plate) gives the same numbers: for a 1.3 mm aluminium plate the through-thickness gradient is negligible.

![Constriction resistance of the three positions](figures/fig_06_lee_spreading.png)

*Figure 6: `figures/fig_06_lee_spreading.png`.*

### 4.5 The five models of the program on the Cu / FR4 / Cu coupon

Most of the paper's cases have an outer FR4 layer above the top copper, which the layered models cannot represent (the outer faces belong to copper). Its case 2, copper / FR4 / copper, can. The board is the same coupon (isotropic FR4 of k 0.4 and copper of 400 W/mK, 35.6 um layers, a gap of 1.5789 mm, 50 x 50 mm, h = 5 W/m2K on both faces, insulated sides, 2.5 W); the film also acts under the source, as in the program, so the solver does the same. The metric is the mean temperature rise of the top copper under the source.

| side (mm) | epsilon | independent 3D (K) | fvm | fdm | solid3d | lumped | analytic |
| --: | --: | --: | --: | --: | --: | --: | --: |
| 5 | 0.010 | 139.85 | 139.70 (-0.1 %) | 138.21 (-1.2 %) | 139.86 (+0.0 %) | 139.37 (-0.3 %) | 139.54 (-0.2 %) |
| 16 | 0.102 | 113.94 | 113.92 (-0.0 %) | 113.62 (-0.3 %) | 113.94 (+0.0 %) | 114.13 (+0.2 %) | 113.91 (-0.0 %) |
| 25 | 0.250 | 106.75 | 106.74 (-0.0 %) | 106.60 (-0.1 %) | 106.75 (+0.0 %) | 106.69 (-0.1 %) | 106.74 (-0.0 %) |
| 35.5 | 0.504 | 102.72 | 102.78 (+0.1 %) | 102.71 (-0.0 %) | 102.78 (+0.1 %) | 102.61 (-0.1 %) | 102.78 (+0.1 %) |
| 50 | 1.000 | 100.98 | 100.98 (-0.0 %) | 100.98 (-0.0 %) | 100.98 (+0.0 %) | 100.98 (-0.0 %) | 100.98 (-0.0 %) |

![Models of the program against the solver](figures/fig_07_program_vs_coupon.png)

*Figure 7: `figures/fig_07_program_vs_coupon.png`.*

### 4.6 The cases of Muzychka and others, and where one node through the thickness stops being valid

Case 1 (a): a 300 x 300 x 10 mm plate of k 10 with h = 10 W/m2K on the bottom and two sources (10 W and 15 W); case 3: five 20 x 20 mm sources in a cross on a 100 x 100 x 10 mm plate of k 50, h = 50. The program represents the plate as one copper layer of the plate's thickness and conductivity.

```
Case 1a: paper {'centroid': [84.97, 108.43], 'mean': [80.56, 101.81], 'base': 53.06}
  independent 3D solver: centroid [85.48, 109.2], mean [81.07, 102.56], base 52.78, max 109.27
  fvm: centroid [77.75, 97.35], mean [74.29, 92.14], max 97.41
  fdm: centroid [77.52, 97.08], mean [74.06, 91.87], max 97.35
  solid3d: centroid [80.09, 101.11], mean [76.32, 95.44], max 101.18
  lumped: centroid [74.84, 90.02], mean [74.83, 90.02], max 90.92
  analytic: centroid [77.76, 97.36], mean [74.45, 92.37], max 97.38

Case 3: paper {'max_centre': 80.61, 'mean_area': 78.87}
  independent 3D solver: centroid [80.62, 78.95, 78.95, 78.95, 78.95], mean [80.28, 78.55, 78.55, 78.55, 78.55], base 75.00, max 80.62
  fvm: centroid [79.36, 77.75, 77.75, 77.75, 77.75], mean [79.03, 77.44, 77.44, 77.44, 77.44], max 79.36
  fdm: centroid [79.35, 77.68, 77.68, 77.68, 77.68], mean [79.0, 77.34, 77.34, 77.34, 77.34], max 79.36
  solid3d: centroid [79.69, 78.05, 78.05, 78.05, 78.05], mean [79.36, 77.73, 77.73, 77.73, 77.73], max 79.69
  lumped: centroid [79.02, 77.92, 77.92, 77.92, 77.92], mean [79.33, 77.98, 77.98, 77.98, 77.98], max 80.10
  analytic: centroid [79.36, 77.75, 77.75, 77.75, 77.75], mean [79.03, 77.44, 77.44, 77.44, 77.44], max 79.36

Case 3 plate, growing thickness (rise of the centre of the cross):
  t = 0.1 mm: independent 195.17 K; fvm 194.30 (-0.4 %), fdm 194.16 (-0.5 %), solid3d 195.15 (-0.0 %), analytic 194.25 (-0.5 %)
  t = 0.5 mm: independent 113.23 K; fvm 112.37 (-0.8 %), fdm 112.31 (-0.8 %), solid3d 113.18 (-0.0 %), analytic 112.34 (-0.8 %)
  t = 1 mm: independent 87.30 K; fvm 86.63 (-0.8 %), fdm 86.59 (-0.8 %), solid3d 87.20 (-0.1 %), analytic 86.61 (-0.8 %)
  t = 2 mm: independent 70.66 K; fvm 70.09 (-0.8 %), fdm 70.07 (-0.8 %), solid3d 70.47 (-0.3 %), analytic 70.08 (-0.8 %)
  t = 5 mm: independent 59.28 K; fvm 58.53 (-1.3 %), fdm 58.53 (-1.3 %), solid3d 58.81 (-0.8 %), analytic 58.53 (-1.3 %)
  t = 10 mm: independent 55.62 K; fvm 54.36 (-2.3 %), fdm 54.35 (-2.3 %), solid3d 54.69 (-1.7 %), analytic 54.36 (-2.3 %)
```

The solver reproduces the cross (maximum 80.62 against 80.61 C, mean 78.90 against 78.87) and case 1 within 1 % of the rise (85.48 and 109.20 against 84.97 and 108.43 by the paper's method and 85.95 and 109.92 by the Fourier series). The program's models are **below** the reference: 0.9 to 2.3 % of the rise on the cross (solid3d 1.7 %, FVM, FDM and Analytic 2.3 %, Lumped 0.9 % at its maximum) and 9 to 18 % on case 1 (solid3d 9 %, FVM and Analytic 13 %, FDM 13 %, Lumped 18 %). The shortfall is the through-thickness gradient that one node cannot show: with the heat entering at the top and leaving at the bottom the surface is hotter than the layer's mean by `q'' t / (2 k)`; the prediction (13.2 % and 14.3 % of the rise of the two sources of case 1, against 12.8 % and 14.1 % observed; 2.3 % against 2.25 % for the cross at 10 mm) follows the measurements.

![Why one node falls short at the surface](figures/fig_09_through_thickness_gradient.png)

*Figure 9: `figures/fig_09_through_thickness_gradient.png`.*

![The cases of Muzychka and others and the thickness rule](figures/fig_08_muzychka_and_the_thickness_rule.png)

*Figure 8: `figures/fig_08_muzychka_and_the_thickness_rule.png`.*

### 4.7 Natural convection of a vertical board: two forms of one correlation

Worked example of the library `ht` (Pr 0.69, Grashof 2.63e9, Ra = Gr Pr): general form gives 147.16 (library: 147.16)

| Ra | laminar form / general form - 1 (Pr 0.71) |
| --: | --: |
| 1e+04 | +7.2 % |
| 1e+05 | +6.6 % |
| 1e+06 | +2.3 % |
| 1e+07 | -5.2 % |
| 1e+08 | -14.7 % |
| 1e+09 | -25.0 % |

| board height (mm) | rise (K) | Ra | h general (program) | h laminar | difference |
| --: | --: | --: | --: | --: | --: |
| 50 | 10 | 1.1e+05 | 5.02 | 5.35 | +6.5 % |
| 50 | 30 | 2.9e+05 | 6.54 | 6.87 | +5.1 % |
| 50 | 60 | 4.6e+05 | 7.69 | 8.01 | +4.2 % |
| 50 | 80 | 5.4e+05 | 8.20 | 8.51 | +3.8 % |
| 100 | 10 | 9e+05 | 4.26 | 4.37 | +2.6 % |
| 100 | 30 | 2.3e+06 | 5.65 | 5.65 | -0.1 % |
| 100 | 60 | 3.7e+06 | 6.71 | 6.60 | -1.6 % |
| 100 | 80 | 4.3e+06 | 7.18 | 7.02 | -2.1 % |
| 200 | 10 | 7.2e+06 | 3.76 | 3.61 | -3.9 % |
| 200 | 30 | 1.8e+07 | 5.07 | 4.69 | -7.5 % |
| 200 | 60 | 3e+07 | 6.06 | 5.49 | -9.5 % |
| 200 | 80 | 3.5e+07 | 6.49 | 5.84 | -10.1 % |

![The two forms of Churchill and Chu and the effect on h](figures/fig_10_natural_convection_forms.png)

*Figure 10: `figures/fig_10_natural_convection_forms.png`.*

## 5. What this means for the program

The models need no change for the boards they are made for. The optional proposals (an input check for a thick, poorly conducting plate; the laminar form of Churchill and Chu as an option; the solver as a test helper) and what should stay out (an effective conductivity of the stack) are in `INTEGRATION.md`; the corrections and text for the project documents are in `docs/for-the-project-documents.md`.

## 6. Limits

* The independent solver is checked against the publications only to 2 to 6 % on the layer orders; the cause of the steady shortfall is not isolated. The figures read from plots are good to about 0.5 W/mK.
* The five models were compared on a board that they can represent; the paper's cases with an outer dielectric above the copper could not be run in them.
* The Biot study above 60 and the paper's mean base temperature are not reproduced.
* No measurement of a physical board.

## 7. Sources

Culham and Yovanovich (1998); Muzychka, Culham and Yovanovich (2003); Lemczyk, Mack, Culham and Yovanovich (1992); Seri Lee (Electronics Cooling, 1998); Churchill and Chu (1975) and the library `ht`, for the correlations; Milton (2002) for the bounds of composites, read for chapter 3 and section 23.1. The entries, with what was read of each, are in `research/theory/BIBLIOGRAPHY.md` (`[CulhamYovanovich1998]`, `[Muzychka2003]`, `[Lemczyk1992]`, `[EC1998Spreading]`, `[ChurchillChu1975]`, `[HtLibrary]`, `[Milton2002]`, `[MHTLArchive]`).

## What was read and what was not verified

* **Read as images (a scan):** pages 460 to 466 of Culham and Yovanovich (1998); the first two pages of Lemczyk and others (1992), whose results were not read; the last page of Culham and Yovanovich (the references) was not read.
* **Read as text:** the three worked cases of Muzychka and others (2003) and their method of images for edge and corner sources (the series coefficients were not checked); the Electronics Cooling article of Seri Lee (its equations 1 and 2 and Figure 4 are images and did not come through; its numbers and statements were read).
* **Taken from the compilation of sources and the library `ht`, not from the papers:** the general and the laminar forms of Churchill and Chu; the paper was not opened. The general form reproduces the library's worked example (the library takes the Grashof number as its argument).
* **Downloaded, abstract only:** Yovanovich, Culham and Teertstra (1998), Yovanovich, Muzychka and Culham (1999), Muzychka and others (2004), Teertstra and others (2004); and other papers of the same archive that could not be read as text (listed in the bibliography).
* **Values read from plots** (cases 2 and 4 of the layer orders, the source size curve, the Biot curve): marked "plot", about 0.5 W/mK; the source positions of the paper are assumed.
* **Reproduced:** Seri Lee's three positions, the cross and case 1 of Muzychka and others, the five layer orders and the series and parallel limits of Culham and Yovanovich, the library's worked example; the solver's own tests (series circuit, energy balance to 1e-9, uniform layer).
* **Not reproduced or not explained:** the effective conductivity above Biot 60; the paper's mean base temperature of 53.06 C against the energy balance of 52.78 C; the 1.62 mm thickness stated against the layers' 1.6501 mm; the second case of Muzychka and others (a heat-sink base with four sources) and their compound-plate case 1 (b) were not run.
