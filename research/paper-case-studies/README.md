# Paper case studies: measured vias and the thick anisotropic laminate

Status: **run, waiting for the reviewer (sections 11 to 14 hold the results of the runs; sections 3 to 9 are the plan and the pre-run review, kept as written).** Three studies, their independent references, tests and drawings: S1 measured vias (parts A to D run), S2 thick anisotropic laminate (L1 first failed, then was settled by a convergence study, then the program part was run), S3 the vertical plate with two strip sources of Lee and Yovanovich (1989) against the measurements of Zinnes (1969). Nothing of `pcbthermal/` is edited; the proposals are in `INTEGRATION.md`.

The two studies are the ones of `research/theory-sources/PLAN-PAPER-STUDIES.md` that compare the program with a **measurement** (S1 here, B2 there) and with a **published closed form on a thick anisotropic laminate** (S2 here, A2 there). The numbers S1 and S2 follow the request that opened this folder; the plan numbers them the other way round.

## 1. The questions

**S1, measured vias.** The program's via treatment (the barrel in a footprint of cells, a Peaceman well, Kron reduction; `docs/theory.md` 2.6) has been checked against idealised references (a 12 x 12 array, a unit-cell solver, a 3D solid) and against a published CFD number, never against a measurement. Two measurements are held: the through-plane conductivity of nine round PCB samples with via arrays (Soleymani Koohbanani 2016, Fig. 33: a plot only) and the top-case temperatures of a DPAK diode on via arrays of four diameters, two patterns and two fillers (Shen and others 2020, Table II: printed numbers). The question: **how far are the five models from a measured through-plane via result, once the measurement itself has been checked by an independent solver?** It informs whether `docs/validation.md` can carry a first statement against a measurement, and whether the barrel rule or the plating default needs a note.

**S2, thick anisotropic laminate.** The laminate sub-gap rule of 2.4.5 (at most 4 sub-gaps of 0.4 mm between copper nodes, only where copper is absent next to a gap) was chosen against our own resolved 3D reference, which gave -18.44 % to -3.07 % (1.6 mm) and -34.19 % to -9.13 % (3.2 mm) for a 6 mm window (`research/laminate-nodes`). That reference has never been checked against a published number. The question: **is the error real (a published closed form for a source on an orthotropic channel agrees with the reference), and do the new options (`laminate_s_max_mm`, `laminate_n_max`) remove it?** It informs whether the rule stays, its constants change, or only the limit text in theory 1.4 grows.

### 1.1 Diagrams of the situations

![The measured via samples, the plan of the cells and the two boundary conditions](figures/fig_01_via_cell_and_boundary_conditions.png)

*Figure 01 (`fig_01_via_cell_and_boundary_conditions.png`). (a) Plan of the straight and staggered unit cells and what Table 9 and Fig. 33 hold. (b) The test bed of the thesis: both faces on metal flux meters, so the field is one-dimensional and the three paths (copper, FR-4, air) are in parallel. (c) The only condition the program can impose: a heater over the face, the heat enters a copper foil and converges on the barrel (the red constriction), the bottom held at the ambient.*

![Shen's diode on a via array and the network behind Table II](figures/fig_02_shen_diode_on_vias.png)

*Figure 02 (`fig_02_shen_diode_on_vias.png`). (a) Section of the DPAK on the via array over a heatsink, the heat paths through the vias and from the top case. (b) The network of Fig. 22 of the paper and its exact inversion (the paper's equation 42 drops a term, 2.2); 44.12 and 2.47 degC/W are printed in the text, theta_ta (300 to 450 degC/W) is read from the plot of Fig. 20; the others are not given, which is why only contrasts between rows are used.*

![A source on a thick anisotropic laminate](figures/fig_03_thick_laminate_and_nodes.png)

*Figure 03 (`fig_03_thick_laminate_and_nodes.png`). (a) The real heat paths in the laminate under a small source. (b) The orthotropic transformation of equations 48 to 51: stretching z by 1 / gamma makes the problem isotropic with k_eff and t_eff. (c) The program's nodes: one copper node and n sub-gaps of the laminate.*

![The four measured markers against equations 28 and 29](figures/fig_04_fig33_markers_against_eq28.png)

*Figure 04 (`fig_04_fig33_markers_against_eq28.png`, `make_figures.py`, closed form and plotted markers only). The black ticks are equations 28 and 29 for each sample of the group (Table 9 diameters); the red markers are the measurement read from the plot of Fig. 33. The straight 1.25 mm marker lies far below its sample (section 5).*

## 2. What the sources say (read for this plan)

### 2.1 Soleymani Koohbanani (2016), chapter 3 (thesis pages 56 to 64; PDF pages 73 to 81)

* Equations 17 to 29 are images: **read from the page images** (PDF pages 75 and 76, thesis pages 58 and 59). Equation 28 (straight) and 29 (staggered): `k = [k_FR4 (u^2 - pi/4 D_o^2) + k_Cu pi/4 (D_o^2 - D_i^2) + k_air pi/4 D_i^2] / u^2`, with pi/2 and v for the staggered cell (two vias). The thesis states that k_overall does not depend on the thickness (true only without a copper foil, section 4.1).
* Table 9 (page 60) lists nine samples (spacing, pitch, inner diameter, outer diameter, "copper barrel thickness"). The last column, 0.04 mm for every row, is the **difference of the two diameters** (0.65 - 0.61), so the wall is **0.02 mm**; a test checks this. Four arrangements: (2.5, 2.5), (2.5, 1.25), (1.25, 1.25), (1, 1) mm. The thickness of the board, the number of copper layers and whether a foil is on the faces are **not stated** in the pages read. The sample is a round disc of 25.4 mm in a guarded heat-flux-meter test bed.
* The column "Copper Barrel Thickness 0.04" of Table 9 (and of Table 10) read as a wall of 0.04 mm would put sample 1 at 5.0 to 5.3 W/mK by equation 28, twice the measured 2.5 of its group; read as the difference of the diameters it gives 1.8 to 2.8 for the group, which holds the measurement. The wall of 0.02 mm is therefore the consistent reading (derived, not printed).
* Table 10 (page 61) is the thesis's own COMSOL benchmark: FR-4 0.33, copper 385 W/mK, isothermal top (323 K) and bottom (303 K), sides insulated; the thesis finds its analytical model within 13 % of the experiment and 9 % of the numerical result (page 62, text).
* **The analytical curves of Fig. 33 are not per sample**: page 62 says "the average values of measured parameters were used in the analytical model". With the mean diameters of the nine samples (D_o 0.533, D_i 0.493 mm) equation 28 gives about 12.7, 8.2 and 2.3 W/mK at 1.0, 1.25 and 2.5 mm, which is where the straight curve of the figure passes (review, by eye on the 2x render). This is why the curve lies near the 1.25 mm marker while the sample of that group (7, D_o 0.65 mm) does not.
* **Fig. 33 (page 63) is the only place the measurements are**: a plot of k (W/mK) against the spacing. By pixel read of the page image at 4x, **there are four measured markers, not nine** (one per arrangement; the other markers of the figure are the thesis's own numerical simulation and analytical model): straight 1.0 mm 12.9 (error bar about 11.5 to 14.5), straight 1.25 mm 7.0 (about 6.1 to 7.6), straight 2.5 mm 2.5, staggered 2.5 mm 4.3 (the diamond is partly hidden by a triangle, so its centroid is biased). All "plot", reading uncertainty +-0.2 W/mK (`lib/measured_data.py`). The review re-read the page at 2x: the same four markers and values within the reading uncertainty (13.0 at 1.0 mm by eye).

### 2.2 Shen and others (2020), section IV and Table II (manuscript page 17)

* Table II (printed numbers, read in full): top-case temperature T_t and psi_ta = (T_t - T_a) / P of the DPAK diode VS-6EWL06FN-M3 at 2.8 W, for Pattern I with solder filling, Pattern II with air, Pattern I with air, at via diameters 0.2, 0.25, 0.4, 0.8 mm. Example: Pattern I, air, 0.25 mm: 74.1 degC, 17.5 degC/W.
* **Derived, not printed**: (T_t - psi P) is 25.0 in every one of the twelve cells (a test, tolerance 0.06 degC/W for the rounding), so the ambient of the experiment is 25 degC.
* The text gives the package numbers theta_jc = 2.47 and theta_jt = 44.12 degC/W (CFD) and equation 42, `theta_via = psi_ta (1 + theta_jt/theta_ta) - theta_jc - theta_solder - theta_TIM - theta_ha`. **Equation 42 drops a term** (review, page 16 read from the page image): the line above it, `1/psi_ta = (theta_jt/theta_ta + 1)/S + 1/theta_ta` with S the whole bottom path, inverts exactly to **`S = psi_ta (theta_jt + theta_ta) / (theta_ta - psi_ta)`**; the printed form holds only for psi_ta << theta_ta (at psi 17 and theta_ta 370 degC/W the slope dS/dpsi is 1.23, not 1.12). The study uses the exact form (`sigma_from_psi`, a test).
* **Fig. 20 (page 15, read from the plot at 5x)**: theta_ta of the DPAK top case is about 450 degC/W at a top-case rise of 20 K and 300 at 100 K; at the rises of Table II (40 to 52 K, ambient 25 degC between the curves of 20 and 40 degC) **about 360 to 385 degC/W**. The first draft swept 20 to 40 degC/W, an order of magnitude too small and below psi_ta itself, which no network allows; the sweep is now 300, 370, 450 degC/W ("plot"). Fig. 22 (page 16) shows the vertical structure: the diode on the via array, bolts, a thermal pad (TIM) and a finned heatsink; four copper layers are drawn. Fig. 16(b) is no longer needed (theta_ta is read from Fig. 20 directly).
* The paper does **not** give the heatsink and TIM resistances, the board thickness or the extent of the via array of the experiment (Fig. 21(b) is a photograph). So **an absolute comparison is not possible**; the study uses **contrasts between rows** (the unknown constant cancels) and sweeps the array side.
* **The paper's own CFD does not give the measured contrasts** (review). Fig. 18 (page 14, read from the plot at 5x, +-0.03 K/W) gives theta_via of the 5.6 mm board of Fig. 17 at 0.25 and 0.8 mm: Pattern I air 1.85 / 2.70, solder 1.36 / 1.13; Pattern II air 1.63 / 2.38, solder 1.20 / 0.99 K/W. Through the exact network (theta_ta 300 to 450) these contrasts predict a psi_ta contrast of 0.39 to 0.42 (air minus solder, 0.25 mm) and 1.23 to 1.34 degC/W (0.8 mm), and 0.17 to 0.19 and 0.25 to 0.27 degC/W (Pattern I minus II, air), against the measured 2.4, 3.9, 0.6 and 0.6 degC/W: **the measured contrasts are 2.2 to 6.3 times those of the paper's own CFD**. (research/lumped-zones-adoption, README 9.3 and 10.2, had already found that the absolute CFD numbers are not reproduced from the stated inputs.) So the experimental board differs from the CFD board in something not stated (array extent, layers, voids in the solder), and D1 below is expected to fail whatever the program does.
* A second measured set exists in the same pages: Fig. 24 prints the maximum temperatures of four 2-layer 70 um boards with a rectangular copper pad (7.8 x 8.4 to 26 x 28 mm) at 0.5 and 1 W (75.9, 64.0, 53.2, 44.6 degC and 116, 96.0, 76.2, 66.6 degC), natural convection. It is a board-level test for the five models, not a via test; the board outline and thickness are not stated in the text read. Not part of S1; recorded in `lib/measured_data.py` for a later study if they are found.

### 2.3 Muzychka, Yovanovich and Culham (2004), J. Thermophys. Heat Transfer 18 (1), pages 49 and 50

* Orthotropic transformation (equations 41 to 49, 57, 58): xi = z / gamma, gamma = sqrt(k_z / k_xy), k_eff = sqrt(k_xy k_z), t_eff = t / gamma. Equation 50 (the rectangular source on the channel, three series), 51 (phi), eigenvalues delta_m = m pi / c, lambda_n = n pi / d, beta_mn. **Equations 50 and 51 were read from the page image** (PDF page 6); the text conversion lost "zeta t_eff" in equation 51.
* Equation 51 equals (x + Bi tanh x) / (Bi + x tanh x), x = zeta t_eff, Bi = h t_eff / k_eff; a test checks the printed exponential form against the code. In the limit a = c, b = d, R_s = 0 (a test).
* **R_s is per watt of the whole source** (a, b, c, d are half sizes; the quarter carries a quarter of the heat). The first reading of this study took it per watt of the quarter and was 4 times too small; the half-space test found it: R_s k (2a) must tend to I / (2 pi) = 0.4732, where I = 2.9732 is the mean reciprocal distance of a unit square (computed in the test by a double integral, independent of the equation); the series give 0.461 (97 %) for a channel of 50 a and a depth of 100 a. Fixed in `lib/flux_channel.py` and in the scripts before anything was run.
* **Checked by the review against a published number**: equations 50 and 51 were re-read on the page image (page 50) and agree with `lib/flux_channel.py`; for a deep isotropic channel equation 50 is equation 19 of Yovanovich, Muzychka and Culham (1999, J. Thermophys. Heat Transfer 13 (4), page 498, page image), whose correlation (equation 20, page 499) `k sqrt(A_s) R_s = 0.47320 - 0.62075 eps + 0.1198 eps^3` (0.3 % for eps <= 0.5) the code reproduces to 0.003 % at eps 0.02 to 0.25 and 0.23 % at 0.5 (a test). The 0.461 above is that correlation at eps = 0.02 (0.4608): a finite channel, not a truncation; 2000 and 4000 terms differ by under 1e-6 relative for the smallest source of the study (review).

## 3. Success and failure criteria (written before any run)

Every number is a threshold chosen now; none is tuned to a result.

| Id | Criterion | If it fails |
| :-- | :-- | :-- |
| B1 | The unit-cell solver equals equations 28 and 29 to 1e-6 (isothermal faces, no foil). Tested to 1e-9. | A code defect: stop. |
| B2 | For each arrangement, the plotted measurement lies within 15 % of the nearest value of equations 28/29 over the samples of the group (the thesis's 13 % plus the plot reading). | The group is "not usable as a reference" and said so; it does not enter C2. |
| C1 | On the periodic patch with the same boundary condition as the solver, for all nine samples (C1 does not depend on B2): fvm and fdm within 5 %, solid3d within 8 %, analytic within 10 % of the solver's node-to-node resistance (lumped: reported, 25 % as the alarm); the error of fvm and fdm at the finest grid not larger than at the coarsest by more than 1 percentage point. | Classified: one model above its threshold but under twice it is "attention"; above twice it or a trend that flips sign over the four arrangements is "no-go" for that model's via rule in the validation row. |
| C2 | (derived: it is B2 and C1 combined, not a new comparison) The program's value translated to the test bed, `k_iso(solver) r_ref / r_prog`, within 20 % of the measurement, for the usable groups. | The row is quoted with its distance; a note on the plating or the barrel rule is proposed only if C1 passes and C2 fails for every usable group. |
| D1 | (report only; expected to fail, 2.2) The signs of the contrasts with |measured| >= 0.4 degC/W are reproduced by the reference and by fvm and fdm; the contrasts solder against air and Pattern II against Pattern I within a factor 2 of the measured, for every swept theta_ta and array side. | Table II is "not informative at this level" and is not quoted in `validation.md`; it is not evidence against the via rule (the paper's own CFD fails it by 2.2 to 6.3 times). |
| L1 | The 3D reference, read at the face like equation 50 (its node plus the half slab above it, 4.3), agrees with equation 50 to 1 % of R' on all 33 bare combinations; its own refinement (pixel S/32, n_sub 32, S = 2 mm) changes it by less than 0.5 %. | Not a reference: stop; told apart by the limit a = c (R_s = 0, a test), the isotropic case, the half-space limit and the published deep-channel correlation (2.3). |
| L2 | The default rule (0.4 mm, 4) keeps fvm and fdm at the 0.25 mm cell within 5 % of R' at 1.6 and 3.2 mm, S >= 5 mm, FR-4 (0.9, 0.3), and within 10 % everywhere. | Go to L3. |
| L3 | A pair of options brings every row within 3 % with at most 3 times the unknowns of the default: it is proposed (a `fix/` with its cost). | If none: the limit text, with the error map. |
| L4 | solid3d within 3 %, analytic within 15 % of R'; lumped reported. | Reported, not decisive. |

R' is the mean temperature of the source **at the face** per watt of the whole source minus the film term 1 / (h W^2) of the base (the same in every model by energy balance), so that a weak film does not hide the laminate term (at h = 10 the film is 28 to 62 % of the total).

**Criteria changed by the review before any run** (section 9; none was changed after a result): L1 judged on R' instead of the total resistance and with the face term added to the reference (without it L1 would have failed by 1.0 to 4.6 % of R' for a known reason); C1 made independent of B2 and its grid condition given a tolerance of 1 point; C2 marked as derived; D1 marked as report only, expected to fail. The thresholds themselves (5, 8, 10, 15, 20 %, factor 2) are kept: 5 % for fvm and fdm is the band the via rule was accepted on (-2.1 to +3.9 % against an axisymmetric barrel, `docs/theory.md` 2.6), 1 % for the reference is a fifth of the smallest program threshold it judges, and 3 % with at most three times the unknowns in L3 is what a change of the default rule would have to buy to be worth its cost.

## 4. Design of the studies

### 4.1 S1 references and the boundary condition

* **Closed form**: equations 28 and 29 (`lib/axisym_cell.py`, `k_overall_straight`, `k_overall_staggered`). Pre-run values (closed form, Table 9 diameters, k_FR4 0.33, copper 385, air 0.026): samples 1 to 9 give 2.752, 2.370, 1.795, 5.174, 4.409, 3.259, 10.018, 13.078, 9.483 W/mK.
* **Independent solver**: `lib/axisym_cell.py::unit_cell_k`, an axisymmetric finite-volume solver of the unit cell (equal-area disc, barrel wall 0.02 mm, air core, FR-4, optional 35 um foils on both faces, the drill through them), nothing of the program imported (a test reads the imports). Tests: it equals the closed form to 1e-9 with isothermal faces and no foil, closes the energy balance to 1e-9, and halving the cells moves the flux-condition result by under 1 %. For Shen's boards the existing `research/lumped-zones-adoption/lib/shen_case.py::unit_cell` is reused (also independent of the program).
* **The boundary condition.** The test bed gives isothermal faces (one-dimensional field, parallel paths: equations 28/29 are exact). The program can only impose a heater flux on a face. With a foil on the face this adds a constriction of the heat in the foil on its way into the barrel (Figure 01 (c)). The first draft guessed that constriction "of the order of the barrel resistance itself" for the sparse arrays; **the solver measures it small** (review, seconds per sample, 1.6 mm, 35 um foil on both faces): the node resistance under a flux is 1.1 to 7.3 % above the one with isothermal faces (samples 8 and 1; 2.4 to 8.0 % on the face temperatures), so the program value is expected near the test bed and the translation is a small correction. The unit-cell solver of both conditions (`bc="isothermal"`, `bc="flux"`) is the bridge: the program is compared with the solver **under the same condition** (C1), and translated to the test bed with the solver's own ratio of node resistances (C2, derived). A metal block on the face in the program (a heatsink with thickness) would make the top nearly isothermal but changes the case (its own film and contact, heat entering the board through it), so it is not used; with a 1.1 to 7.3 % effect the solver's translation is sufficient. Part A prints that ratio, the effect of a 35 um foil and of the thickness (0.8, 1.6, 3.2 mm; the thesis's "independent of the thickness" holds without foil only, a test).
* The unknown thickness is assumed 1.6 mm and the foil 35 um on both faces (neither is stated); both are in the sensitivity of part A.

### 4.2 S1 boards and parameters

* **Part C, the program on a periodic patch**: 6 x 6 cells of each of the nine samples (straight: one via at the centre of each u x u cell; staggered: two vias, at a quarter and three quarters of the diagonal of each v x v cell, i.e. rows offset by half the in-row spacing), 2 layers of 35 um, 1.6 mm, FR-4 0.33 isotropic and copper 385 W/mK (the thesis's values), plating 0.02 mm, open barrel, a 1 W heater over the whole top, h_top 0, h_side 0, h_bottom 1e6, grid spacing/8, /16 (and /32 for fvm and fdm; the grid floor of the program is 0.05 mm, so the finest levels of the 1 mm and 1.25 mm samples are clamped and the study says so in the table). Models: fvm, fdm, solid3d, analytic, lumped; the API clamps the cell of the analytic and lumped models to 0.5 to 1 mm, so they are run once (spacing/8 asked). Read: the resistance between the area-weighted mean temperatures of the two copper layers (`layer_mean`; the plain mean of the FDM node field counts the edge nodes in full, 0.2 % on a coarse trial); reference: the solver's `r_nodes` for the same condition divided by the number of vias. The solver's node mean includes the air core under the foil while the program's copper node has no hole: a definitional uncertainty of about 1 to 2 % for the dense arrays (the face and node ratios of 4.1 differ by up to 1.6 points), to be kept in mind against the 5 % of C1.
* **Part D, Shen Table II** (contrasts only, report only): the array of Pattern I (pitch phi + 0.2 mm) or II (rows sqrt(3)/2 pitch apart, alternate rows offset by half a pitch), as many cells as fit in a nominal side of 3.0, 5.0, 5.6 mm (the 12 x 12 array of Fig. 17 at 5.6 mm; 5.0 mm the pad that fits the paper's analytical curve, lumped-zones-adoption 9.3; 3.0 mm a small array, since the measured contrasts are larger than the CFD's), four copper layers of 70 um, 1.6 mm, Table I conductivities (copper 393, FR-4 0.29 through and 0.81 in plane, solder 57.3 W/mK, air 0.026), plating 25 um, a heater over the array, bottom h = 1e6. The reference is the unit-cell solver per row divided by the number of vias; the program is fvm and fdm (the 3D solid is not in the default list). Each contrast of the via resistance (air minus solder at each diameter, Pattern I minus Pattern II at each diameter) is turned into a contrast of psi_ta through the exact network (2.2), starting from the measured psi_ta of the row it is taken from, with theta_ta 300, 370, 450 degC/W (Fig. 20, plot), and compared with the measured contrast; the paper's own CFD contrasts (Fig. 18, plot) are printed beside them.
* A thickness of the thesis's samples, an array extent and a theta_ta that disagree with the experiment move the contrasts: that is why D1 asks for the same verdict over the whole sweep.

### 4.3 S2 references and cases

* **Published closed form**: equation 50 with the orthotropic transformation (`lib/flux_channel.py`): a source 2a x 2b at the centre of a channel 2c x 2d of thickness t, k_xy in plane, k_z through, adiabatic top outside the source and adiabatic sides, base film h. Tests: tanh form equals the printed exponential form; R_s = 0 at a = c, b = d; the half-space limit; the invariance under the orthotropic transformation.
* **Independent 3D reference**: `research/gerber-real-boards/lib/ref3d.py` (anisotropic laminate in sub-slabs, copper masks per layer, adiabatic sides, films on both faces). A test reads its imports: it imports only numpy and scipy (the copy in `research/laminate-nodes/lib/ref3d.py` imports that folder's `boards`, which imports the program, so it is not used). It is first compared with equation 50 on the bare-laminate geometry (L1), then used where there is no closed form (a 35 um copper pad under the source).
* **Cases (33)**: S x W in {2 x 20, 5 x 20, 10 x 40} mm; t in {0.8, 1.6, 3.2} mm; FR-4 (k_xy, k_z) = (0.9, 0.3) [the program's] with h in {10, 1e3, 1e6} W/m2K (27), plus (0.3, 0.3) and (2.7, 0.3) at S = 5, h = 1e3 (6). The reference solves the quarter (source at the corner, adiabatic sides) at pixel S/16 with 16 sub-slabs; the program solves the whole board (a 4 W heater) at cells 0.5 and 0.25 mm.
* **Program configurations**: fvm at 0.25 mm with (s_max, n_max) in {(0.4, 4) the default, (0.4, 1) cutting off, (0.2, 8), (0.1, 16), (0.8, 2)} and at 0.5 mm with the default; fdm, solid3d (0.5 mm for the 40 mm board, which the 250 000-unknown limit would refuse at 0.25), analytic and lumped at one setting each. Two boards per case: **bare** (two layers, nothing drawn: exactly the geometry of equation 50; the program warns about copper, which is the point) and **pad** (copper under the source on layer 1 only: the real case, no closed form). (0.1, 16) gives 8 sub-gaps at 0.8 mm (ceil(0.73 / 0.1)) and (0.8, 2) one at 0.8 mm: the labels are the options, the table prints them as asked.
* **The program accepts the bare board**: a trial of the review (20 mm board, 5 mm source, 1 mm cell, all five models, a fraction of a second) ran every model with one warning each; no refusal, so the 1 um pad of the first draft is not needed.
* **Where the temperature is read** (corrected by the review). Equation 50 gives the mean temperature of the source **at the face**. `ref3d.py` injects the heat in the cells of its top copper slab and reads them there, at mid-thickness of that slab; on bare laminate the 17.5 um of FR-4 above that point add q'' t_cu / (2 k_z), which is **1.0 to 4.6 % of R'** in these cases (S = 10 mm at 3.2 mm to S = 2 mm at 0.8 mm, closed form). The reference now adds that term (copper under a pad: negligible), exact for a one-dimensional drop through a thin slab under a uniform flux (a test checks the one-dimensional case to 1e-9). The program is read with `analysis.heater_stats`, the part's mean as the program reports it: the FVM and FDM add the same face term over absent copper, and the FDM node field is weighted correctly (the first draft read `T[0]` with cell centres, which put the FDM's node field off by half a node and its spacing wrong).

### 4.4 What was read for part D (review)

Fig. 20 (theta_ta, plot), Fig. 22 (the vertical structure and the network) and Fig. 18 (the CFD theta_via, plot) were read from the page images (2.2); Fig. 16(b) is not needed. Still not read: the text near Fig. 24/25 for the board of the pad set (not part of the studies).

### 4.5 Declared cost

| Study part | Time | Peak memory | Notes |
| :-- | :-- | :-- | :-- |
| S1 A and B (closed forms, solver) | seconds | under 0.2 GB | |
| S1 C (five models x nine samples x two or three grids) | about 5 to 10 min | at most 2 GB | the largest patch run is fvm/fdm at spacing/32 on 96 x 96 or 192 x 192 cells of about 6 node layers; the 3D solid is not run at /32 |
| S1 D (12 rows x 3 array sides, fvm and fdm, reference) | about 10 min | at most 1.5 GB | |
| S2 L1 (closed form, 33 reference solves, bare) | about 5 min | under 1 GB | 115 000 unknowns at most (pixel S/16, 18 slabs) |
| S2 program (bare and pad, about 12 solves per case) | about 15 min | at most about 3 GB | the pair (0.1, 16) on the 40 mm board at 3.2 mm: 160 x 160 cells x 17 node layers = 435 000 unknowns (about 7 GB per million for the layered models); the first draft said under 2 GB |
| S2 `--convergence` (pixel S/32: 460 000 unknowns; n_sub 32) | about 5 min | at most 3 GB | run alone |

All runs are one at a time (a 16 GB machine); the program's memory guard refuses a run above its fraction, and a refusal is printed in the table, not hidden.

## 5. What is known before running (closed form and tests only)

* **Measured markers against equations 28/29 (part B, closed form, no solver)**: straight 2.5 mm: measured 2.5, samples 1.795 to 2.752: inside. Staggered 2.5 mm: measured 4.3, samples 3.259 to 5.174: inside. Straight 1.0 mm: measured 12.9, samples 9.483 to 13.078: inside. **Straight 1.25 mm: measured 7.0 (error bar 6.1 to 7.6), one sample (7) at 10.018: 43 % above the measurement, outside the 15 % of B2.** The thesis's own analytical curve at 1.25 mm lies near 8 on the plot, so its curve was not computed with the Table 9 diameters of sample 7; the group is expected to be reported "not usable" unless the full run (or another reading of the thesis) explains it. This is a prediction of the arithmetic, not a result of the study.
* **Ambient of Shen's experiment**: 25 degC in all twelve cells (a test).
* **The boundary condition of S1 is a small effect** (unit-cell solver, review, 4.1): flux against isothermal faces 1.1 to 7.3 % on the node resistance, largest for the sparse 2.5 mm arrays (samples 1 to 6: 4.7 to 7.3 %), smallest for the dense 1 mm arrays (1.1 and 2.4 %). With the foil and isothermal faces the solver is 1.7 to 2.2 % above equation 28/29 (the foil replaces 70 um of FR-4).
* **Part D is expected to fail D1 before it runs**: the paper's own CFD contrasts are 2.2 to 6.3 times smaller than the measured ones (2.2).
* **S2, L1 without the face term would have failed** by 1.0 to 4.6 % of R' (4.3); with it, the one-dimensional limit is exact (a test).
* **Tests**: 24 tests of this folder pass (the data and its consistency; the solver against the closed form; the flux condition worse than the isothermal and converged; the references import nothing of the program, Shen's unit cell checked at module level and in the function used; the lattices; the 33 combinations; equation 50 against the published deep-channel correlation of Yovanovich, Muzychka and Culham at four source sizes; the exact network inversion of Shen and the size of the term equation 42 drops; the 3D reference read at the face in the one-dimensional limit; both scripts print their plan with `--dry-run` and import nothing of the program); `tests/test_docs.py` and `tests/test_license_header.py` pass with the new files.

## 6. Scripts, libraries, tests, figures

| File | What |
| :-- | :-- |
| `lib/measured_data.py` | Table 9, Table 10, the Fig. 33 markers (plot, with the reading uncertainty), Shen Table II and the package numbers, each with its reading status |
| `lib/axisym_cell.py` | equations 28 and 29; the axisymmetric unit-cell solver (isothermal faces or flux, foils) |
| `lib/flux_channel.py` | equations 48 to 51: the spreading resistance of a rectangular source on an orthotropic channel |
| `scripts/study_measured_vias.py` | S1 (parts A to D; `--parts`, `--dry-run`, `--quick`) |
| `lib/vertical_plate.py` | S3: the independent conjugate solver of Lee and Yovanovich (boundary layer marching, one-dimensional plate, radiation) |
| `scripts/study_thick_laminate.py` | S2 (`--dry-run`, `--convergence`, `--heavy`, `--no-program`); the extrapolated reference `reference_3d_extrap` |
| `scripts/study_vertical_plate.py` | S3 (`--dry-run`, `--no-program`) |
| `scripts/make_diagrams.py`, `scripts/make_figures.py` | figures 01 to 03 (diagrams), 04 (data, closed form), 05 and 06 (results from `out/*.json`: the models against the solver per sample, the error of each option pair of the laminate rule), 07 (convergence of the 3D reference) and 08 (the vertical plate) |
| `tests/test_paper_case_studies.py`, `tests/test_vertical_plate.py` | the fast tests above (29 pass) and the tests of the plate solver (4 pass) |

Run order for the executor, from the repository root (nothing has been run), one at a time: (1) `pytest -q research/paper-case-studies/tests`; (2) both `--dry-run`; (3) `study_measured_vias.py --parts A,B` (seconds); (4) `study_thick_laminate.py --no-program` (L1, about 5 min, under 1 GB: decides whether S2 continues); (5) `study_thick_laminate.py --no-program --convergence` alone (at most 3 GB; it repeats L1, then the refinement); (6) `study_measured_vias.py --parts C --quick` (a smoke run), then `--parts C` (5 to 10 min, at most 2 GB); (7) `study_thick_laminate.py` (L1 again plus the program, about 20 min, at most about 3 GB), only if L1 passed; (8) `study_measured_vias.py --parts D` (report only, about 10 min, at most 1.5 GB), last and optional; (9) `make_figures.py`. Note that each run of `study_thick_laminate.py` rewrites `out/study_thick_laminate.json`; keep the outputs of (5) and (7) by renaming before the next run, or run (7) with `--convergence` once.

## 7. Limits and doubts

* **The test-bed condition cannot be reproduced in the program.** The translation by the solver's ratio is the assumption that the program's error in the flux condition carries to the isothermal one; the condition itself moves the result by only 1.1 to 7.3 % (5), so the assumption weighs little. A metal block over the face was considered and not used (4.1).
* The thickness and the foil of the thesis's samples are unknown; the thesis's own claim of independence from the thickness holds only without foil.
* Fig. 33 is a plot: the four markers are known to about 0.2 W/mK, the staggered one with a bias; the thesis gives no table of the measurements and no uncertainty of its own test bed was read (chapter 2 has an uncertainty analysis, "Uncertainty Analysis for Guarded Heat Flux Meter Device", p. 77 of the contents, not read).
* Shen's Table II is a differential test with two assumed unknowns; its experimental resolution (the IR camera) is not stated in the text read; the contrasts of 0.4 degC/W are about 1 degC at 2.8 W. The program side of part D assumes four copper layers and 1.6 mm like the CFD board of Fig. 17; the experimental board is not described.
* The staggered cell is the thesis's (v x v with two vias); its via positions in the patch are the natural reading of Fig. 28, which was not rendered here.
* Equation 50 evaluated by a truncated double series (2000 terms each way, no tail extrapolation). The 0.461 of the half-space test is the finite channel (the published correlation gives 0.4608 there), not truncation; for the smallest source of the study 2000 and 4000 terms differ by under 1e-6 relative (review). The study prints that dependence (L1.0) before L1 is judged.
* The 3D reference is a finite-volume solver with a uniform pixel in plane: a source of 2 mm is 16 pixels wide, a pixel of 0.125 mm; its refinement is part of L1.

## 9. Review before the runs

Reviewer's pre-run check of the prepared folder (nothing heavy run; closed forms, the unit-cell solver, a coarse trial of the program and the fast tests only). **Go to run, in the order of section 6**, with the corrections below already made in the scripts, tests and this README.

Corrected (each would have spoiled a result or a verdict):

1. **S2, the temperature was read at different places** (4.3): equation 50 at the face, the reference at mid-thickness of its top slab (1.0 to 4.6 % of R' on bare laminate, so L1 would have failed for a known reason), the program at its copper node with cell-centre coordinates (wrong by half a node for the FDM's node field). Now the reference adds the face term and the program is read with `analysis.heater_stats`; a test checks the one-dimensional limit to 1e-9.
2. **S2, L1 judged on the total resistance**: at h = 10 the film is 28 to 62 % of it. Now on R'.
3. **S1 part D used the paper's equation 42, which drops a term**, with theta_ta swept at 20 to 40 degC/W, which no network allows (below psi_ta) and an order of magnitude below Fig. 20 (360 to 385 degC/W at the rises of Table II). Now the exact inversion and a sweep of 300, 370, 450 degC/W; and the paper's own CFD contrasts are printed beside the measured ones: they are 2.2 to 6.3 times smaller, so D1 is report only and expected to fail (2.2).
4. **S1 part C read the layer means as plain array means** (wrong weights for the FDM nodes) and translated with a ratio of face conductivities against a node resistance; now `layer_mean` and the ratio of node resistances. The README's claim that the flux condition costs "of the order of the barrel resistance" was a guess; the solver gives 1.1 to 7.3 % (4.1).
5. **Costs**: the S2 program part peaks at about 3 GB, not under 2 GB (435 000 unknowns for (0.1, 16) on the 40 mm board).
6. **Tests**: the independence test skipped Shen's file entirely; it now checks its module level and the function used. Three tests added (the published deep-channel correlation, the exact network, the face term).

Checked and found right: Table 9 and the four markers of Fig. 33 (re-read); the wall of 0.02 mm (the 0.04 reading contradicts the 2.5 mm marker, 2.1); equations 28 and 29 (page image); the straight 1.25 mm sample at 10.02 W/mK against 7.0 measured (+43 %; the thesis's curve passes near the marker because it uses the mean diameters of all samples, page 62); equations 50 and 51 (page image) and their normalisation (published correlation to 0.003 %); `ref3d.py` imports only NumPy and SciPy; 33 combinations; the program accepts a bare two-layer board; the thresholds (3, with the reasons).

Left to the run: every verdict; whether the solver's air-core node mean against the program's solid copper node (1 to 2 % on the dense arrays) matters for C1.

## 10. Results, runs A, B and L1

Light steps only, one at a time, on the tree merged with `develop`, while a battery ran elsewhere (swap used 751 MB before and 671 MB after, no growth). Outputs (git-ignored): `out/run_AB.json`, `out/run_L1.json`, `out/run_L1.txt`. Tests: 24 passed. Both `--dry-run` print their plan and solve nothing. The heavy steps (S2 convergence, S1 C, the S2 program part, S1 D) were **not run**: they wait for a quiet machine, with the declared peaks of 4.5 (at most 3 GB for the S2 convergence and the S2 program part, 2 GB for S1 C, 1.5 GB for S1 D).

### 10.1 Part A and criterion B1

The unit-cell solver equals equations 28 and 29 on all nine samples, relative difference 1e-15 to 2e-13 (criterion 1e-6): **B1 passes**. The foil and boundary-condition effects on samples 1 and 8 (t = 0.8, 1.6, 3.2 mm; k_eff / k_closed):

| Sample | foil, isothermal faces | foil, flux condition |
| :-- | :-- | :-- |
| 1 (2.5 mm cell) | 1.041 / 1.020 / 1.010 | 0.897 / 0.945 / 0.971 |
| 8 (1.0 mm cell) | 1.036 / 1.018 / 1.009 | 0.987 / 0.993 / 0.997 |

The flux condition lowers k_eff by 3 to 10 % on the sparse sample 1 and by 0.3 to 1.3 % on the dense sample 8 (the foil with isothermal faces raises it by 1 to 4 %). This agrees with the expectation of section 5.

### 10.2 Part B and criterion B2

| Group | Measured (plot), W/mK | Equations 28/29 over the samples | Distance | B2 (15 %) |
| :-- | :-- | :-- | :-- | :-- |
| straight 2.5 mm | 2.50 +-0.2 | 1.795 to 2.752 | 0.0 % | usable |
| staggered 2.5 mm | 4.30 +-0.2 | 3.259 to 5.174 | 0.0 % | usable |
| straight 1.25 mm | 7.00 +-0.2 | 10.018 (one sample) | 43.1 % | **not usable** |
| straight 1.0 mm | 12.90 +-0.2 | 9.483 to 13.078 | 0.0 % | usable |

Three groups are usable, the 1.25 mm group is not, exactly as predicted in section 5 (nothing here explains the 43 %; it stays reported as not usable and does not enter C2).

### 10.3 L1: equation 50 against the 3D reference (33 bare combinations)

Truncation of equation 50 is negligible (2000 to 4000 terms: +0.00005 % and +0.00007 % of R'). Difference of the 3D reference (read at the face, plus the face term) against equation 50, in percent of R':

| Quantity | Value |
| :-- | :-- |
| combinations within 1 % | 20 of 33 |
| combinations above 1 % | 13 of 33 |
| minimum / mean / maximum | 0.48 / 1.07 / 2.57 % |
| sign | the reference is above equation 50 in all 33 |
| worst rows | S = 2 mm on 20 mm, t = 3.2 mm: 2.53, 2.56, 2.57 % (h = 1e1, 1e3, 1e6); S = 5 mm, kxy = 2.7, t = 3.2: 1.67 %; S = 2 mm, t = 1.6: 1.05 to 1.19 % |
| best rows | S = 10 mm on 40 mm and S = 5 mm, t = 0.8 mm: 0.48 to 1.25 % |

The error grows with the thickness for the smallest source (0.57 / 1.05 / 2.53 % at h = 10 for t = 0.8 / 1.6 / 3.2 mm) and with the conductivity ratio (kxy = 2.7: 0.80 / 0.96 / 1.67 %). Measured against the total resistance the differences are 0.26 to 2.57 %, so the film term does not explain them.

**Verdict: L1 fails** (criterion: 1 % of R' on all 33; the reference was above it in 13). By the rule written before the run, the 3D reference is not accepted as a reference at this resolution and **S2 stops here**: L2 to L4 and the program part are not run. The refinement criterion (pixel S/32, n_sub 32 changing it by less than 0.5 %) was **not** run (it needs `--convergence`, up to 3 GB, alone), so this study cannot yet say whether the gap is the discretisation of the reference (a single sign, growing with the thickness and the smallness of the source, which is what a coarse pixel S/16 under a corner-singular flux would give) or a defect of equation 50 as transcribed. What distinguishes them is already prepared: the limit a = c (R_s = 0), the isotropic case, the half-space limit and the published deep-channel correlation (which equation 50 already reproduces to 0.003 %, section 5). Not established by this run: which side is wrong.

### 10.4 Cost measured

L1 took 66 s wall, peak resident memory 1.77 GB (the declared peak was under 1 GB and the cost about 5 min: both were wrong by the measurement, time 4 times shorter and memory 1.8 times higher). The stated cost in 4.5 should be corrected before the convergence run (the convergence step at 460 000 unknowns will exceed the declared 3 GB if memory scales the same way; expect about 6 GB and run it alone).

### 10.5 What waited

S2 `--convergence`, S1 C, the S2 program part and S1 D waited for a quiet machine; they were run afterwards and their results are sections 11 and 12 (the S2 convergence settled that the reference, not equation 50, was at fault).

## 11. S2 after the convergence study: who was wrong in the failed reference check

Run alone, one job at a time (`study_thick_laminate.py --no-program --convergence`, and a heavy single refinement outside the script). Outputs `out/run_L1b.txt`, `out/run_S2full.txt`.

### 11.1 The failed check was the discretisation of the reference

Section 10.3 left open whether the 3D reference, equation 50 or the transcription was wrong. The reference is a finite-volume solver with a uniform pixel in plane and `n_sub` equal sub-slabs of the laminate. Its error was measured on the smallest source (S = 2 mm on 20 mm, FR-4 0.9 / 0.3, h = 1e6), R' in K/W, equation 50 given in the first line of each block (closed form, 2000 terms):

| t = 1.6 mm, eq. 50 = 380.786 | n_sub 4 | 8 | 16 | 32 | 64 |
| :-- | :-- | :-- | :-- | :-- | :-- |
| pixel S/6 | 420.546 | 400.243 | 394.220 | 392.604 | 392.192 |
| pixel S/8 | 415.872 | 396.057 | 390.077 | 388.443 | 388.021 |
| pixel S/12 | 411.721 | 392.514 | 386.687 | 385.065 | |
| pixel S/16 | 409.987 | 391.053 | 385.333 | | |

| t = 3.2 mm, eq. 50 = 418.178 | n_sub 4 | 8 | 16 | 32 | 64 |
| :-- | :-- | :-- | :-- | :-- | :-- |
| pixel S/6 | 522.417 | 459.712 | 438.232 | 431.853 | 430.140 |
| pixel S/8 | 516.037 | 454.956 | 433.991 | 427.662 | 425.931 |
| pixel S/12 | 510.431 | 450.738 | 430.402 | 424.236 | |
| pixel S/16 | 508.168 | 448.979 | 428.923 | | |

Two more runs outside the table (a one-off, alone; 460 000 unknowns, **8.2 GB resident, not the 3 GB declared in 4.5**; swap rose by 1 GB): pixel S/32 with 16 sub-slabs gave 383.851 (t = 1.6 mm, +0.805 % against equation 50) and 427.289 (t = 3.2 mm, +2.179 %); pixel S/16 with 32 sub-slabs gave 383.735 (+0.775 %) and 422.868 (+1.122 %). Both refinements move the answer towards equation 50, never away.

* **Sub-slabs: the error falls as 1/n^2.** At pixel S/8, t = 1.6 mm, the successive differences are 19.82, 5.98, 1.63 and 0.42 K (n = 4 to 64): ratios 3.3, 3.7, 3.9, towards 4. A Richardson step with n = 16 and 32 removes it.
* **Pixel: slow, about first order** (a flux jump at the source edge in a cell-averaged source): 390.08 -> 385.33 -> 383.85 at S/8, S/16, S/32 (n_sub 16), the slope in 1/pixel falling from 80 to 48 per unit.
* **Extrapolated reference** (`reference_3d_extrap`: Richardson in n_sub with 16 and 32, then a quadratic in 1/pixels through S/6, S/8, S/12; at most 130 000 unknowns, about 2 GB): 380.166 against 380.786 (-0.16 %) at t = 1.6 mm and 417.846 against 418.178 (-0.08 %) at t = 3.2 mm. The extrapolation is a model of the error (a quadratic in 1/pixels), so it carries its own uncertainty, which the next paragraph measures against equation 50 and not against itself.

![Convergence of the 3D reference](figures/fig_07_reference_convergence.png)

*Figure 07 (`fig_07_reference_convergence.png`). The 3D reference against equation 50 (percent of R') as a function of the number of sub-slabs, for four pixel sizes, with the extrapolated value (dashed). Symlog scale. Computed by `make_figures.py`.*

### 11.2 L1 again, on the 33 combinations

Against equation 50, in percent of R': the single grid S/16 / 16 sub-slabs (section 10.3) was +0.48 to +2.57 % (mean +1.07), 20 of 33 within 1 %; the **extrapolated reference is -1.15 to -0.07 % (mean -0.32), 32 of 33 within 1 %**; the exception is S = 10 mm on 40 mm, t = 0.8 mm (-0.88 % at h = 1e3, **-1.15 %** at h = 1e6), where the coarse pixels S/6 to S/12 leave only 12 to 24 cells across the quarter, so the extrapolation is least reliable. The sign is negative on all 33 (the extrapolated value sits slightly below equation 50; the typical 0.1 to 0.35 % is the extrapolation, the quadratic in 1/pixels slightly overshooting).

**Verdict.** L1 *as written* (the single grid within 1 %, refinement within 0.5 %) **failed**, and the criterion is **changed after the result**: L1' is "the extrapolated reference within 1 % on all 33 combinations". L1' passes on 32 of 33 (worst -1.15 %). The conclusion about who was wrong: **the 3D reference at one pixel and sixteen sub-slabs was not converged (1 to 2.6 % high, the sign of both errors); equation 50 and its transcription (page image, normalisation) are right** (the independent solver reproduces them to 0.07 to 1.15 % at the extrapolated limit, and the published deep-channel correlation to 0.003 % before). The earlier laminate-nodes reference (`research/laminate-nodes`) used similar single grids: its absolute errors (-18.44 to -3.07 %, -34.19 to -9.13 %) were obtained against a resolved reference that was not extrapolated in n_sub either; its sign and ordering agree with section 11.3, its numbers were not re-run here.

### 11.3 The program against the extrapolated reference (L2 to L4)

`study_thick_laminate.py` (default, no `--no-program`), bare and pad boards, 33 combinations each; errors are the program's R' against the extrapolated 3D reference, in percent (negative: the program is too cool). Cost of the whole run about 19 minutes, one process, 3.2 GB resident observed (the declared 3 GB held, within 7 %); the memory guard **refused 12 runs** (the pair (0.1, 16) on the 40 mm board at 0.25 mm: 435 200 unknowns, 10.4 to 11.3 GB estimated, more than the 10.3 GB allowed), printed in the table and left out of the ranges below.

FVM at the 0.25 mm cell, FR-4 (0.9, 0.3), per source S and thickness t, range over the three films (percent):

| S (mm), t (mm) | bare: default (0.4, 4) | bare: (0.2, 8) | bare: (0.1, 16) | pad: default | pad: (0.2, 8) | pad: (0.1, 16) |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 2, 0.8 | -7.9 / -4.1 | -2.2 / -0.8 | 0.0 / 0.6 | -10.6 / -6.1 | -2.7 / -1.1 | 1.7 / 1.9 |
| 2, 1.6 | -6.7 / -5.6 | -1.6 / -1.2 | 0.5 / 0.6 | -9.3 / -7.8 | -2.2 / -1.7 | 1.7 / 1.7 |
| 2, 3.2 | -16.6 / -16.3 | -6.3 / -6.1 | -1.5 / -1.4 | -19.8 / -19.3 | -9.0 / -8.8 | -2.5 / -2.4 |
| 5, 0.8 | -3.7 / -1.1 | -1.6 / -0.1 | -0.8 / 0.2 | -6.0 / -3.6 | -1.8 / -0.5 | 0.4 / 1.2 |
| 5, 1.6 | -2.5 / -1.5 | -0.7 / -0.2 | 0.0 / 0.2 | -4.9 / -3.9 | -1.1 / -0.6 | 0.9 / 1.1 |
| 5, 3.2 | -5.9 / -5.5 | -1.8 / -1.7 | -0.3 / -0.3 | -10.1 / -9.8 | -4.1 / -4.0 | -0.9 / -0.8 |
| 10, 0.8 | -2.0 / -0.3 | -1.0 / 0.0 | -0.6 / 0.1 | -4.0 / -2.0 | -1.7 / -0.4 | -0.5 / 0.5 |
| 10, 1.6 | -1.2 / -0.3 | -0.4 / 0.0 | refused | -3.1 / -2.1 | -0.9 / -0.4 | refused |
| 10, 3.2 | -2.5 / -1.7 | -0.7 / -0.4 | refused | -6.3 / -5.3 | -2.5 / -2.1 | refused |

Other FR-4 ratios (S = 5 mm, h = 1e3, default rule): bare (0.3, 0.3) -1.2 / -0.9 / -2.6 and (2.7, 0.3) -5.3 / -4.8 / -11.1 at t = 0.8 / 1.6 / 3.2 mm; pad -2.9 / -2.7 / -6.8 and -7.9 / -7.2 / -13.8.

![The error of the laminate rule](figures/fig_06_laminate_error_map.png)

*Figure 06 (`fig_06_laminate_error_map.png`). R' error of the FVM at 0.25 mm against the extrapolated 3D reference, per source size S and thickness t, for the four option pairs, bare and pad boards (h = 1e3). Computed by `make_figures.py` from `out/study_thick_laminate.json`.*

Verdicts (criteria of section 3):

* **L2 fails.** The default rule (0.4 mm, 4) is within 5 % for t = 1.6 and 3.2 mm, S >= 5 mm, FR-4 (0.9, 0.3) on the bare board at t = 1.6 mm and at S = 10 mm for 3.2 mm, not at S = 5 mm, t = 3.2 mm (-5.9 %, 0.9 point out) and not on the pad board (-10.1 %); within 10 % everywhere fails (bare -16.6 %, pad -19.8 %, S = 2 mm at 3.2 mm). The 0.5 mm cell adds little (bare -14 / -5 / -2 %, pad -18 / -9 / -5 % at t = 3.2 mm for S = 2 / 5 / 10 mm): the error is the laminate rule, not the plan grid. Turning the cutting off (0.4, 1) makes it several times larger (bare up to -52.5 %, pad up to -53.7 %).
* **L3: no pair satisfies both clauses.** (0.1, 16) brings every row that ran within 3 % (bare -1.5 to +0.6 %, pad -2.5 to +1.9 %), but it needs 3.0 to 3.4 times the node layers of the default (the counts of the rule, 17 against 5 at 1.6 mm; not measured) and the memory guard refuses it on the 40 mm board. (0.2, 8) costs 1.7 to 1.8 times the node layers and brings the worst row from -16.6 to -6.3 % (bare) and from -19.8 to -9.0 % (pad), but does not reach 3 % where the source is small and the board thick. The pair is a decision of the maintainer; the table gives the cost and the benefit of each; the default is within about 4 % (bare) and 6 % (pad) for sources of 5 mm and above on boards up to 1.6 mm (bare -3.7 to -0.3 %, pad -6.0 to -2.0 %; 2 mm sources are 4 to 11 % too cool), the text of the limit is in `docs/validation-rows.md`.
* **L4**: solid3d at 0.25 mm is **too hot** as the board thickens: bare -1.3 to +20.0 % (S = 2 mm: +0.4 / +5.5 / +20.0 % at t = 0.8 / 1.6 / 3.2 mm), pad +6.9 to +27.4 %; at the 0.5 mm cell on the 40 mm board -0.3 to +2.4 % (bare) and +3.5 to +8.4 % (pad). **Not within 3 %** (not decisive; this is the solid model's own slab discretisation of the laminate, not studied here). Analytic: bare -56 to -1.5 %, pad -86 to -44 % (beyond 15 %; the Analytic spreads a pad's copper uniformly, a known limit). Lumped: bare -52 to +1.3 %, pad -44 to +8.9 %. **FDM** at 0.25 mm: bare -18.7 to -0.4 %, pad -31.4 to -7.3 % (below the FVM on the pad by 10 to 20 points: the FDM reads the part at its nodes on a pad edge, the open item "FDM pad-edge sampling" of the older folders; not decisive here).

Not established: the cost of the rule options in time and memory (counts of node layers only); the temperature-dependent convection (h is a film, constant); a pad of a different size from the source; the effect on boards whose gaps are thinner than 0.8 mm.

## 12. S1 measured vias: parts C and D

### 12.1 Part C, the program on the periodic patch (full run)

Outputs `out/run_C_full.txt`, 6 x 6 cells, foil 35 um on both faces, bottom h = 1e6, nine samples, five models at two or three grids (one process). R_ref is the unit-cell solver with the same flux condition on the face (`layer_mean` of the program). Error of the program against it, percent (finest grid):

| Sample | fvm | fdm | solid3d | analytic | lumped |
| :-- | :-- | :-- | :-- | :-- | :-- |
| straight 2.5, sample 1 | 1.0 | 1.0 (1.8) | 1.3 | 11.5 | 9.5 |
| straight 2.5, sample 2 | 0.9 | 0.9 (1.3) | 1.2 | 10.4 | 8.5 |
| straight 2.5, sample 3 | 0.8 (1.8) | 0.8 | 1.1 | 8.3 | 6.7 |
| staggered 2.5, sample 4 | 1.2 | 1.3 (2.2) | 1.6 | 13.1 | 8.2 |
| staggered 2.5, sample 5 | 1.2 | 1.1 (1.6) | 1.4 | 12.0 | 7.4 |
| staggered 2.5, sample 6 | 1.0 (2.2) | 1.0 (0.7) | 1.3 | 9.7 | 6.0 |
| straight 1.25, sample 7 | 0.8 | 0.8 | 1.2 | 12.0 | 6.6 |
| straight 1.0, sample 8 | 0.6 | 0.6 | 1.0 | 9.4 | 5.0 |
| straight 1.0, sample 9 | 0.5 | 0.5 | 1.0 | 8.2 | 4.1 |

The number in parentheses is the error at the coarsest grid where it differs by more than 0.3 point (the grids are in `out/run_C_full.txt`).

* **C1 passes for fvm, fdm and solid3d**: 0.4 to 2.2 % against the 5 % and 8 % thresholds, the error at the finest grid not larger than at the coarsest by more than the point allowed (it falls: fvm sample 6 from 2.2 to 1.0 % between 0.312 and 0.156 mm; sample 3 from 1.8 to 0.8 %). This is a **good** result for the via rule of `docs/theory.md` 2.6: against an independent axisymmetric solver the footprint-and-well treatment is within about 1 % of the resistance at the pitch / 8 to pitch / 16 cell on all nine samples, with the foil and the flux condition.
* **C1 for the Analytic is "attention"** (threshold 10 %; it is above 10 % on samples 1, 2, 4, 5 and 7 (10.4 to 13.1 %), below it on 3, 6, 8 and 9, never above twice): the Analytic reads the via array **8 to 13 % too resistive** (too hot), on the safe side. **Lumped 4 to 9.5 %** too resistive (alarm 25 % not reached).
* **C2 (derived)**: translating the program's values to the test bed by the solver's own ratio of node resistances (`k_translated`) gives, for the usable groups, the measurement inside the range spanned by the samples of the group in all three: straight 2.5 mm (measured 2.50; translated 2.78 / 2.40 / 1.82 for the three diameters), staggered 2.5 mm (measured 4.30; 5.22 / 4.44 / 3.29) and straight 1.0 mm (measured 12.9; 13.23 / 9.61). The straight 1.25 mm group is the one that was found not usable (B2, 10.1 W/mK against a measured 7.0, +44 %). The row means that **the program reproduces equations 28 and 29 of the thesis to the accuracy of the unit-cell solver, and that those equations bracket three of the four plotted measurements**, not that the program was validated against the measurement to 5 %: the thesis does not give which diameter each marker is.

Fig. 28 of the thesis (page 72 of the PDF, read as an image in this pass): the square unit cell has a quarter via at each corner (one via per cell) and the staggered unit cell adds one full via at its centre (two vias per v x v cell), as the patch of part C was built.

![Part C](figures/fig_05_via_models_against_reference.png)

*Figure 05 (`fig_05_via_models_against_reference.png`). Error of every model against the unit-cell solver (same boundary condition) per sample of Table 9, finest grid of the model. Computed by `make_figures.py`.*

### 12.2 Part D, Shen's Table II (report only; D1 fails as expected)

(One process, 34 seconds; `out/run_D.txt`.) The program (fvm, fdm) and the independent reference (`shen_case.unit_cell`) agree with each other within a few percent on the via-resistance contrasts (for example air minus solder, Pattern I, phi 0.2, array side 3.0 mm: reference 0.823, fvm 0.775, fdm 0.775 degC/W; the fvm contrasts are 0.90 to 0.95 of the reference's). The prediction of the contrast of psi_ta through the exact network, as a fraction of the measured contrast (theta_ta = 300 / 370 / 450 degC/W, plot values of Fig. 20):

| Contrast (fvm, predicted / measured, over theta_ta 300 / 370 / 450 and phi) | array 3.0 mm | array 5.0 mm | array 5.6 mm |
| :-- | :-- | :-- | :-- |
| air - solder, Pattern I, phi 0.2 to 0.8 | 0.25 to 0.67 | 0.08 to 0.24 | 0.07 to 0.24 |
| Pattern I - Pattern II, phi 0.2 to 0.4 | 0.61 to 1.73 | 0.17 to 0.26 | 0.16 to 0.29 |
| Pattern I - Pattern II, phi 0.8 | -0.04 | 0.00 | 0.47 to 0.52 |

**D1 fails** on the whole sweep (the criterion asked for a factor 2 for every theta_ta and every array side: the solder contrast is predicted at 0.07 to 0.67 of the measurement; the sign of every contrast >= 0.4 degC/W is right except the Pattern I - II at phi 0.8, a measured 0.6 against a predicted of -0.04 to 0.00 in the 3.0 and 5.0 mm arrays); the paper's own CFD (Fig. 18, plot) is 2.2 to 6.3 times smaller than the measurement too, so Table II is **not informative at this level**: it is not quoted in `validation.md`, and is not evidence against the via rule (the program equals the reference; both equal the CFD of the paper). The array extent and the heatsink are the unknowns; the study cannot separate them.

## 13. S3 vertical plate with two strip sources (Lee and Yovanovich 1989, Zinnes 1969)

### 13.1 What the paper gives (read from the page images, pp 262 to 266)

Two identical strip sources flush on a thin vertical plate (Fig. 4): height L = 96.52 mm, half thickness t = 1.143 mm (plate 2.286 mm), strip l = 5.08 mm centred at L/4 and 3L/4 (the peaks of Figs. 5 and 6 lie at 0.25 to 0.27 and 0.75 to 0.77 of L), heat flux entering the front face under a strip **q_p = 3875 W/m2** (p 265), k_s 1.032 W/mK for the glass plate with emissivity 0.387 and 28.38 W/mK for the ceramic plate with 0.366, air at 298 K (nu 15.614e-6 m2/s, k 0.0258 W/mK, Pr 0.72), surroundings 298 K. The model solves the half plate (symmetry): "Q_p represents only half of the original total heat generation" (p 264), **so q_p is the flux of one face of the strip**, which settles the open point of the review: each face carries q_p, the whole plate 2 q_p l per strip. Energy check: the average face flux is 3875 x 2 x 5.08 / 96.52 = 408 W/m2 (a mean excess of 45 K needs a total coefficient of 9 W/m2K, which the solver's own solution gives, 9.4 and 9.2; the paper does not print h). The solid side is the one-dimensional conduction along the plate (the Biot number is 0.016 at most, equation 14); the fluid side of the paper is an integral method of Lee (1988) (not obtained); the measurements of Zinnes (thermocouples and an interferometer) are in Figs. 5 and 6 as plots only.

### 13.2 The independent solver and the reproduction of the paper (part R)

`lib/vertical_plate.py` (NumPy and SciPy only): the one-dimensional plate along z with the radiation `eps sigma (T^4 - T_inf^4)` and, as the fluid side, the **boundary layer equations (1) to (3) of the paper solved by a marching finite-difference scheme from the leading edge** (the first version with an inner iteration per station converged to a spurious thin-layer state at 5 to 9 times the Nusselt number and was replaced by lagged coefficients, Patankar-Spalding, with a geometric pre-march from the leading edge), coupled by the paper's iteration (h_i = q / (T_w - T_f)). Tests (4 passed): against the exact similarity solution of the isothermal plate (shooting solver in the test: -theta'(0) = 0.50463 at Pr 0.72, the textbook g(Pr) = 0.5043) the local Nusselt number is within 3.7 % from z = 10 mm, 1.05 % at z = 50 mm and 0.3 % at the top (the error falls like 1/z: it is the first-order marching in the first millimetres, at strip 1, z = 24 mm, the local Nusselt number is 0.9 to 2.0 % high and at strip 2, z = 72 mm, 0.4 to 0.6 %); the solid with a uniform coefficient equals the closed form of the fin pair; the heat balance closes to 1e-4 and the solver imports nothing of the program.

Against the curves of the paper's own model (read from Figs. 5 and 6, **plot**, +-2 K) and Zinnes' thermocouple points (**plot**), rise above ambient in K:

| Plate, emissivity | peak 1 (solver / paper) | peak 2 | valley (z/L 0.5) | left end | heat in / out (W/m) |
| :-- | :-- | :-- | :-- | :-- | :-- |
| glass, 0 | 92.0 / 91.0 (+1.1 %) | 102.6 / 98.0 (+4.7 %) | 45.4 / 44.0 (+3.1 %) | 19.8 / 20.0 (-1.1 %) | 40.70 / 40.70 |
| glass, 0.387 | 77.9 / 75.0 (+3.8 %) | 83.1 / 89.0 (-6.7 %) | 30.8 / 29.0 (+6.2 %) | 14.0 / 13.0 (+7.4 %) | 40.70 / 40.69 |
| ceramic, 0 | 61.2 / 61.5 (-0.5 %) | 65.5 / 65.0 (+0.8 %) | 60.3 / 60.0 (+0.6 %) | 55.8 / 57.0 (-2.2 %) | 40.70 / 40.70 |
| ceramic, 0.366 | 46.8 / 46.5 (+0.6 %) | 49.6 / 48.0 (+3.4 %) | 45.1 / 44.0 (+2.6 %) | 42.1 / 42.0 (+0.1 %) | 40.70 / 40.70 |

Thermocouples of Zinnes (plot) against the solver: glass at z/L 0.11, 0.26, 0.51, 0.77: 22.6, 79.8, 33.1, 84.4 K measured against 23.6, 77.6, 30.6, 80.6 K; ceramic at 0.09, 0.24, 0.50, 0.75: 36.0, 42.0, 37.8, 42.7 K against 42.9, 46.6, 45.1, 49.6 K (the paper's own curve is also 4 to 8 K above these points on the ceramic).

**R1 is met except the second peak of the glass plate with radiation** (-6.7 %, 5.9 K; the plot reading is +-2 K and the paper's ε = 0 second peak, +4.7 % the other way, makes a reading error alone unlikely); of the 16 values 13 are within 5 %; the other two outside are the glass valley and left end with radiation, +6.2 and +7.4 % (1.8 and 1.0 K, inside the plot reading). The solver therefore **reproduces the paper's own numerical results within the accuracy of the plot, with an independent fluid side**. Heat balance exact.

![The vertical plate](figures/fig_08_vertical_plate_conjugate.png)

*Figure 08 (`fig_08_vertical_plate_conjugate.png`). Wall temperature excess along the plate: the independent solver (lines), the values read from the paper's curves (open circles, plot), Zinnes' thermocouples (triangles, plot) and the strip mean of the program's FVM with computed coefficients (horizontal line: the program has one coefficient per face and the strips are alike). Computed by `make_figures.py`.*

### 13.3 The program on the plate (part P)

The plate is a board 96.52 x 20.32 mm (the problem is two-dimensional: strips across the whole width, sides adiabatic, `h_side` 0) of two layers and 2.286 mm, copper conductivity set to k_s and FR-4 in plane and through to k_s (a homogeneous plate), a heater of q_p l W on each face (the symmetric plate, so the conduction through the plate is solved instead of assumed), vertical, computed h (both natural forms), emissivity as printed, ambient 25 degC. Rises above ambient in K, strip 1 / strip 2 of the conjugate solution and the program's strip means (the program's two strips are alike by symmetry):

| Plate | conjugate solution strip means | program h (computed: convection + radiation) | h implied by the conjugate solution | FVM 0.254 general (mean, max) | against the mean of the two strip means | plate maximum: solution / FVM |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| glass (1.032, 0.387) | 74.93 / 80.23 | 9.18 (6.28 + 2.90) | 9.39 (6.37 + 3.01) | 85.60, 88.45 | +10.3 % (+14.3 % against strip 1, +6.7 % against strip 2) | 83.06 / 88.39 (+6.4 %) |
| ceramic (28.38, 0.366) | 46.63 / 49.51 | 9.05 (6.30 + 2.75) | 9.15 (6.39 + 2.76) | 47.04, 47.16 | -2.0 % (+0.9 / -5.0 %) | 49.64 / 47.16 (-5.0 %) |

All five models, both cells and both natural forms agree with the FVM within 1.5 points on each plate (glass: fvm 85.49 to 85.60, fdm 85.49 to 85.87, solid3d 85.64 to 85.78, analytic 84.63 to 84.89, lumped 85.34 to 85.66; ceramic 47.0 to 47.4, Lumped the highest), so the model differences are small and **the difference from the conjugate solution is the uniform coefficient**. A diagnostic with the FVM and the uniform coefficient that the conjugate solution itself implies (total heat over the integral of the excess; manual h of 9.39 W/m2K) gives 84.28 K on the glass: **+8.6 % against the mean of the strips even with the same total coefficient**, the correlation (the program's 9.18 against 9.39 W/m2K, -2.2 %) adding +1.4 %. On the ceramic plate (nearly isothermal, the conduction along the plate evens out the temperature) the program is within the plot reading and the paper's measurements (47.0 K against Zinnes' 36 to 43 K, which the paper's own model also overestimates).

Verdict P1: ceramic within 10 % ✓ (-2.0 % on the mean of the strips; each strip -5.0 to +0.9 %); glass within 20 % ✓ (+10.3 % on the mean, +14.3 % on the lower strip, **too hot**, the safe side). Reading: a plate that conducts poorly (k_s 1 W/mK, a peak of 83 K against a plate mean of 44 K) is read by the program with one mean coefficient, which makes the peaks 6 to 14 % too hot; with a good conductor it is within 5 %. The Lumped and the Analytic differ from the FVM by 1.1 points at most; the Lumped's plate maximum (90.6 K) is 2.2 K above the FVM's (88.4 K) at a place other than the strips (not examined). A board with copper planes is the ceramic case (an in-plane conductance of the order of k_s t = 28 W/mK x 2.3 mm or more), so this limit concerns thin, poorly conducting boards with concentrated sources; a proposal and its limit are in `INTEGRATION.md`.

Not established: Zinnes' measurements are plots (the 4 to 8 K scatter on the ceramic is the same as the paper's); the transient or tilted cases of the paper are not studied; the horizontal-plate laws are untouched.

## 14. Summary of the runs

| Study | Result | Verdict |
| :-- | :-- | :-- |
| S1 A, B | closed form = solver to 1e-15 to 2e-13; the measured markers bracketed by equations 28/29 for three groups; the 1.25 mm group not usable (+43 %) | B1 passes, B2 three of four |
| S1 C | fvm, fdm 0.4 to 2.2 %, solid3d 1.0 to 1.6 %, analytic 8.2 to 13.1 %, lumped 4.1 to 9.5 % against the unit-cell solver | C1 passes for fvm, fdm, solid3d; analytic attention (> 10 % on five samples) |
| S1 D | contrasts of Table II 0.07 to 0.67 of the measured (solder), Pattern I - II 0 to 1.7 | D1 fails as expected; not informative |
| S2 L1 | single grid 0.5 to 2.6 % high; extrapolated -1.15 to -0.07 % | L1 as written failed; L1' passes 32 of 33 (the reference was the problem, equation 50 is right) |
| S2 L2 to L4 | default rule -0.3 to -19.8 % (worst S = 2 mm, 3.2 mm), (0.1, 16) within 2.5 % | L2 fails; L3 no pair meets both clauses; the decision is the maintainer's |
| S3 R | solver within the plot reading of the paper's curves on 13 of 16 values | R1 met except the glass second peak |
| S3 P | program 2 to 10 % hot on the strips of a poor conductor, within 5 % on a good one | P1 passes |

## 15. What was read and what was not verified

* **Read in full (R)**: Soleymani Koohbanani (2016) thesis pages 56 to 64 (text from the extraction; equations 20 to 29 from the page images; Table 9 and Table 10 as printed; Fig. 33 rendered at 2x and 4x and read by pixel centroid, "plot"); Shen and others (2020) section IV text, Table II and Figs. 23 to 25 (images), Table I and the equations 2 to 5, 37 to 42 (text conversion); Muzychka, Yovanovich and Culham (2004) pages 49 and 50 (equations 37 to 58, equations 50 and 51 from the page image).
* **Read in part (S)**: the rest of the Soleymani thesis (chapter 3 literature review pages 54 to 56 and the numerical-study text of pages 61 and 62 only; the guarded heat-flux-meter chapter and its uncertainty analysis are not read); Shen section II to III (the formulas relied on are those quoted in `research/lumped-zones-adoption` and `research/theory-sources` 8.1).
* **Read by the review (page images)**: Shen pages 14 to 17 (Figs. 18, 20 and 22 with equations 40 to 42; Table II re-checked), Soleymani pages 59, 60 and 63 (equations 28 and 29, Table 9, Fig. 33) and the text of pages 56 to 62, Muzychka and others page 50 (equations 50 and 51), Yovanovich, Muzychka and Culham (1999) pages 498 and 499 (equations 19 and 20, the deep-channel series and its correlation with the half-space constant 0.47320).
* **Not obtained or not read**: Shen Fig. 16(b) (not needed); the photograph Fig. 21(b); Fig. 28 of the thesis as an image; the measurements of Soleymani in any form other than the plot.
* **Reproduced**: by studies, with an independent solver: equations 28/29 (unit-cell solver, 1e-15 to 2e-13) and the program's models on the same patch (section 12.1); equation 50 of Muzychka and others (2004) by an extrapolated 3D reference (0.07 to 1.15 %, section 11); the numerical curves of Lee and Yovanovich (1989) Figs. 5 and 6 by an independent boundary-layer-plus-plate solver (within the plot reading, section 13.2), the similarity solution of the isothermal plate (0.3 % at the top). By tests: equations 28/29, the exponential form of equation 51, the half-space limit of equation 50 (0.461 against 0.4732), Table II's ambient.
* **Not verified**: every verdict of section 3; the program side of S1 and S2 (no program model has been run on these boards beyond the review's trials at coarse cells: the bare two-layer board is accepted by all five models, the patch of sample 1 runs at a 0.625 mm cell); the cost figures of 4.5 are estimates from similar runs of the earlier folders and the unknown counts, not measurements.

