# Analytic model: a spatial treatment of the convective board edge

## 1. Question

The Analytic model (`pcbthermal/analytic.py`, `docs/theory.md` 6) expands every layer in cosines, which have an insulated edge. Since `fix/analytic-edge-transfer` the edge loss
is moved to the faces, `h_edge,l = h_side P s_l / (W H)` (Muzychka, Culham and Yovanovich 2003, Part II, eq. 27 to 29), which is exact only if the edge is at the
board mean temperature. With a part in a corner or a large `h_side` the hottest rise reads up to +37 % (part at the edge) or -14 % (part at the centre) against the FVM.
Can a spatial treatment of the edge enter 2.5.0 without delaying it?

Three treatments are compared on the same steady solver (a copy of the program's, `lib/analytic_edge.py`, equal to `analytic.solve_steady` to 1e-9 K):

* **faces**: the program now.
* **none**: the edge left out.
* **robin**: the cosine basis is replaced by the eigenfunctions of the **convective edge**, `phi'' = -lam^2 phi`, `phi' = +-beta phi` at the ends, `beta = h_side s / S`
  (`lib/robin_basis.py`; even functions `cos(lam u)`, `lam Lh tan(lam Lh) = beta Lh`, odd functions `sin(lam u)`, `lam Lh cot(lam Lh) = -beta Lh`). Everything else is unchanged:
  the layers still decouple by mode into the tridiagonal `L x L` system, only `(m pi/L)^2` becomes `lam_m^2`, the cosine norm `L/eps_m` becomes the norm of the function, and
  the projections and evaluations use the new functions. One `beta` is common to all layers (`beta = h_side sum(slab) / sum(S)`, which keeps the total edge conductance).
* **strips**: the reviewer's prototype, the edge cells as local heatsinks in the Green-function correction (insulated cosine basis), tiles along the outline.

![Where the edge heat leaves in each treatment](figures/fig_01_edge_treatments.png)

*Figure 1 (`figures/fig_01_edge_treatments.png`): plan view with a part in a corner; the three treatments.*

![Section of the edge](figures/fig_02_edge_section.png)

*Figure 2 (`figures/fig_02_edge_section.png`): section at the edge nearest to the part, with the sideways heat path; the right panel is illustrative (the shape only).*

## 2. Published case reproduced (`scripts/study_muzychka_eq21.py`)

Equation 21 of Muzychka, Culham, Yovanovich Part II (rectangular flux channel with edge cooling, eigenvalues `delta tan delta = Bi_e`, read as an image of p. 4, the OCR text
being untrusted) is implemented in `lib/muzychka.py` and compared with an independent 3D finite-volume solver with side convection (`lib/layered3d_side.py`, tested against a
series circuit and an energy balance), 50 x 50 mm, 10 x 10 mm source, adiabatic top outside it, `h` = 100 W/m2K, 24 cases (k 50 and 385 W/mK, t 0.2, 1, 3 mm, `h_e` 0, 50, 200, 1000):

| quantity | result |
| :-- | :-- |
| equation 21 against the 3D solver | -0.16 to +1.06 % (k 50), -0.07 to +0.28 % (k 385) |
| thin-sheet series of the Robin basis (what the Analytic solves) against equation 21 | -0.03 to -0.59 % at tau = t/sqrt(A_s) up to 0.1; up to -6.1 % at tau 0.3, k 50, Bi_e 0.5 |

So the formula as printed holds, and the Robin basis is its fin limit; the gap at large tau is the through-thickness variation that no layered model has. The paper prints
no table for the rectangle (the 2006 journal version has plots for the disc only), so the numerical reproduction is against the independent solver. It treats a centred source
(even functions only); the board needs the odd functions too, which the code has.

## 3. Uniform boards (`scripts/study_edge_variants.py`)

135 boards: 30 x 20, 60 x 40, 100 x 80 mm; (layers, mm) 2 x 0.8, 2 x 1.6, 2 x 3.2, 4 x 1.6, 6 x 1.6; `h_side` 10, 50, 200; a 10 mm, 2 W part at the centre, a corner or the middle
of an edge; faces 10 W/m2K. Hottest rise against the FVM at 0.5 mm:

| treatment | mean abs. error | max abs. error | signed range | mean time |
| :-- | --: | --: | --: | --: |
| none | 38.2 % | 252 % | +0.1 to +252 % | |
| faces (program) | 3.36 % | 37.2 % | -14.4 to +37.2 % | 0.04 s |
| **robin** | **0.12 %** | **0.32 %** | -0.3 to +0.2 % | 0.05 s |
| strips, 1 mm tiles | 0.17 % | 0.65 % | -0.6 to +0.1 % | 0.5 s (max 3.3 s) |

By `h_side`: faces max 2.6, 12.1 and 37.2 % at 10, 50, 200 W/m2K; Robin 0.31, 0.32, 0.32 %. The Robin energy balance (faces plus edge) over the power is 1.0000 on every board.
Against the independent 3D solver (117 boards that fit 2 GB) the FVM is 0 to 17.4 % low, and the Robin Analytic 0.1 to 17.2 % low: **what is left is the layered idealisation**
(one node through the thickness at a thick board with a large edge coefficient), not the edge treatment.

![Profile through a corner part](figures/fig_04_profile_corner.png)

*Figure 4 (`figures/fig_04_profile_corner.png`): top layer through a corner part, 100 x 80 mm, 3.2 mm, `h_side` 200; faces reads 80 K at the part against 61 K.*

![Errors by treatment](figures/fig_05_errors_by_treatment.png)

*Figure 5 (`figures/fig_05_errors_by_treatment.png`): the errors of the 135 boards.*

![Robin modes](figures/fig_03_robin_modes.png)

*Figure 3 (`figures/fig_03_robin_modes.png`): first modes (cosine, Robin beta L = 4 and 30) and the wavenumbers; the Robin ones move up to (m+1) pi/L as the edge cools.*

### 3.1 The strips prototype (`scripts/study_strip_sensitivity.py`, 16 boards)

| variant | mean abs. | max abs. | time |
| :-- | --: | --: | --: |
| strips 5 mm, 64 modes | 1.46 % | 3.95 % | 0.05 s |
| strips 2.5 mm | 0.62 % | 1.73 % | 0.06 s |
| strips 1 mm (64 or 150 modes) | 0.27 % | 0.65 % | 0.13 to 0.22 s |
| robin | 0.13 % | 0.32 % | 0.04 s |

The tile size, not the mode count, sets the error (the tile mean stands for the edge value); a 1 mm ring needs a dense `Nt L` system (356 tiles x 6 layers on 100 x 80 mm) and
shares no grid with the via tiles. The Robin basis has no tile.

## 4. Unequal layers, vias, heatsinks, the example board (`scripts/study_edge_complications.py`)

**A. Unequal copper** (60 x 40, 4 layers, 16 boards, fills (1,1,1,1), (.5,1,1,.5), (.3,1,1,1), (.2,.2,1,1)). One `beta` for all layers is exact only when `slab_l/S_l` is the same;
the spread of that ratio is 1, 1.95, 3.14, 4.53 and the Robin error is up to 0.2, 1.2, 3.2, 5.4 % (faces: 8.1, 9.9, 10.3, 13.2 %). Moving the mismatch to the faces ("robin_res") gives
up to 4.0 % (better in the corner, worse at the centre). Two other rules for the common parameter, least squares and the heater layer, are worse (up to 12 and 30 %): the
flux-conserving one stays. Robin is better than faces in all 16.

**B. Vias and heatsinks** (60 x 40, 2 layers, 3 x 3 vias and/or a 20 x 20 mm heatsink, centre and corner, `h_side` 50 and 200, 12 boards): rise error faces up to 15.4 %, Robin
up to 0.25 %; error of the via/heatsink effect faces up to 30.4 %, Robin up to 4.6 % (the via model's own error, the same at `h_side` 0). The copy with faces equals the program to 3e-14 K.
Example board (100 x 80, partial top copper, 9 vias, heatsink), hottest rise against FVM 0.5 mm: `h_side` 10 / 50 / 200: faces -1.3 / -2.6 / -6.9 %, Robin -1.0 / -1.2 / -1.9 %
(the rest is the partial copper, present at `h_side` 10).

**C. Time** (uniform 2 x 1.6 mm boards, 12 cases). Time to 63 % of the unit step, FVM 2 mm cell as reference:

| treatment | error range |
| :-- | :-- |
| program now (faces) | -31.1 to +38.5 % |
| Robin | -3.3 to +6.0 % (nine of 12 within 2 %) |

The Robin step response differs from the FVM one by at most 1.5 % of the steady resistance, and its steady resistance is within 1.5 % of the FVM (faces: up to 23 %). The same modal machinery works because
the basis is common to the layers.

![Step response](figures/fig_06_step_response.png)

*Figure 6 (`figures/fig_06_step_response.png`): unit step, corner part, 60 x 40 mm, `h_side` 200.*

## 5. Impact on the frozen boards and outlines (`scripts/study_frozen_impact.py`)

On the harness boards that have an edge coefficient (all at 10 W/m2K) the Robin Analytic moves +0.29 to +0.70 % (10 boards, 2 mm frozen cell, equivalent rectangle for outlines, the
round and T outlines +0.44, +0.52) and -0.04 % on the part across the outline (11 boards); the error against the FVM improves or stays on every board (those with errors of -7 and -31 % are the copper
and T-arm limits, unchanged). The top-path and block boards are not covered by the copy. Boards without `h_side` are bit-identical (beta = 0 returns the cosines).

## 6. Verdict

* **Robin basis**: fits 2.5.0. Cost is nil (600 roots in 2 ms, same matrices), the error against the FVM is within 0.35 % on 135 uniform boards and 12 via/heatsink boards, the time
  response improves from -31/+38 % to -3/+6 %, it removes the warning's reason to exist for the uniform-copper case, and the faces transfer it replaces was merged in this release
  and never shipped, so the Analytic frozen numbers shift once (the second shift costs nothing extra now; after the release it is a visible change).
* **Strips as heatsinks**: not recommended (needs 1 mm tiles, 10 times the time, a dense system that grows with the perimeter and the layers, shares no grid with the via tiles).
* **Limit that stays**: unequal layers (spread of `slab/S` above about 3 with edge share above 20 %: up to 5 %): a warning, not a fix (a per-layer basis would couple the modes).
* **Not changed**: copper not uniform, outline (equivalent rectangle), the layered idealisation at thick boards (up to 17 % low against the 3D solid, existing warning).

`INTEGRATION.md` has the exact changes.

## 7. Tests

`tests/test_analytic_edge.py` (9): orthogonality and Robin condition of the basis, beta = 0 is the cosine, the copy equals the program (uniform and example board with vias and
heatsinks), the "none" copy equals the insulated board, the Robin energy balance, the series against 1D finite differences, the 3D solver's balance and series circuit, equation 21
against the 3D solver and the thin-sheet limit, the step response ends at the steady resistance. Run: `.venv/bin/python -m pytest -q research/analytic-edge-spatial/tests`.

## What was read and what was not verified

* **Muzychka, Culham, Yovanovich 2003 Part II (AIAA 2003-4188)**: pages 3 to 5 (eq. 6 to 31) read from the local page OCR (untrusted); eq. 21 checked numerically against an independent solver
  (status R for the formulas used, reproduced). The paper's own plots/tables for the rectangle: none printed; not reproduced.
* **Muzychka, Yovanovich, Culham 2006 (J. Thermophys. Heat Transfer)**: text extraction read around the edge-cooling section (S; the disc results are plots, not reproduced).
* **Sturm-Liouville eigenfunctions with Robin ends**, Carslaw and Jaeger: from memory (M); the eigenfunctions are verified numerically (orthogonality, boundary condition, 1D finite differences).
* Not verified: boards with metal blocks (the copy has none), the top-path split, the Lumped model (no analogue), a real measured board, the effect of `n_terms` below 300 on the Robin
  basis (tests use 120), the frozen-number refreeze itself (an estimate from 11 boards at 2 mm), unequal layers beyond a 4.5 spread, partial copper with an edge across the heater.
