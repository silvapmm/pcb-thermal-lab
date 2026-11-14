# Review A4 with L11: the Lumped and Analytic models, the transient, and the formulas of the Lumped network

Assignment A4 (45 claims of risk 3) and the literature-to-code assignment L11 (formulas F-058 to F-065, with F-039 and F-040 that the zones share) of the claims register (`releases/2.8.0/audit/ASSIGNMENTS.md`, `claims.csv`, `formulas.csv` on `docs/audit-claims-register`). Program: `development` 5fc91430 (2.7.1 plus documents). While this review ran, `development` moved to 35eeb773 (five fix branches merged, among them `fix/analytic-transient-hot-point`, and the audit documents of A1, A3, L1+L5, L4+L9, A2+L7 and the decisions); this branch was not merged with it, so the maintainer will resolve the document conflicts (validation 4.1, 18, 32; theory 6) at the merge. Branch `docs/audit-a4`; nothing in `pcbthermal/` or `tests/` was edited (program and test items are in section 7). Method as `REVIEW_A1`, `REVIEW_A3`, `REVIEW_S1`, `REVIEW_L1L5` and `REVIEW_L4L9`: the formula as printed on the page image rendered from the PDF of the papers library against the code, the numbers re-run on the program, an independent reference for each conclusion (here `research/analytic-edge-spatial/lib/layered3d_side.py`, the side-film version of `tests/helpers/layered3d.py`; closed forms; the reviewed finite-element transient of `research/transient-reference-boards`), one heavy job at a time under the lock. Decision 3 of `DECISIONS.md` (branch `docs/audit-decisions`) is applied: every accuracy figure is given against an independent reference first and against the FVM second, named as the model the constants were fitted to.

**Verdict of trust.**
* **Lumped network (theory 5, L11): GO for the formulas.** Every closed form of the network (the Bessel factors, the log-potential self distance 0.447, the annulus link, the Krogh mean and rim) was derived again and matches an independent numerical solve to 5 to 7 digits; the Bessel interior is the `I₀` branch of Shen eq. 19, read on the page. **GO with the corrections of this branch for the numbers**: the accuracy figures are against the FVM the constants were fitted to; the near-edge level was stale (-6.6 to -7.4 % on average, -22.2 % at worst against the FVM, -26 % against the 3D solver), and the independent checks of the zones remain one resolved cluster.
* **Analytic steady (theory 6): GO**, with the open model decision P3 (the laminate edge film on the copper node: -11.4 % against the shipped FVM, -14.9 % against the 3D solver at 200 W/m²K on 3.2 mm; warned on every such board of the sample).
* **Transient (theory 2.4, 5, 6, 10; validation 4.1, 7, 31.3, 18.2): CONDITIONAL.** Plateau and time to 63 % of every model are within -1 to +4 % of the independent finite elements at 0.5 mm; the statements of validation 7 and the Robin 'Time' paragraph were stale or against an unconverged FVM (corrected). **The Analytic transient of a part over vias** was a NO-GO on the base of this review (-22 % at 0.3 s, swing -11 %); its fix was merged into `development` meanwhile, so the GO waits only for the re-run of P1, and the first-seconds limit of every layered model (-58 % at 0.3 s on two layers) must be stated where the step response and the animation are described (P2, D2).

*This file was written progressively.*

## 1. Pages read on the image (papers library, read only; pages rendered from the PDF with pypdfium2 of `.venv-research` into the scratchpad)

| source | file | page | what was compared | claims |
| :-- | :-- | :-- | :-- | :-- |
| Shen, Wang and others (IEEE TPEL, accepted version) | `papers/pdf/ShenWang2019Vias.pdf` | PDF 10 | eqs. 15 to 19: the fin equation of a thin circular PCB (17), the general solution `ΔT = a I₀(z) + b K₀(z)`, `z = r √(h/(kt))` (19) | F-061, F-053 |
| Muzychka, Culham, Yovanovich (2003, Part II) | `papers/pdf/Muzychka2003Part2.pdf` | PDF 4 (right column) | eq. 21 (`R_t` with the edge eigenvalues and `φ_mn`), eqs. 22 to 26 | RCC-021 |
| Shen eq. (4) and Fig. 18(a) | `papers/pdf/ShenWang2019Vias.pdf` | PDF 5, 14 | taken from `REVIEW_A3` (rendered and read there; not repeated) | RCA-009 |

Not in the library, so **cannot be checked from the source** (download list in section 9): Seri Lee, 'Calculating spreading resistance in heat sinks', Electronics Cooling, January 1998 (`EC1998Spreading`, claim RCA-025); Carslaw and Jaeger, *Conduction of Heat in Solids* (the disc solution, the method of images, the Sturm-Liouville odd functions; status M); J. C. Maxwell, *Treatise*, the geometric mean distance of a rectangle (the 0.447 of F-060); Krogh (1919) (the cell of the via).

## 2. L11: the Lumped network, formula printed (or derived) against coded

| id | formula | source as printed or derived | coded | numerical check (independent) | verdict |
| :-- | :-- | :-- | :-- | :-- | :-- |
| F-058 | ring edges, first ring capped at `a_eq = √(N₀ Δx Δy/π)` (theory 5.1) | own; no source | `lumped.ring_edges`, `_equivalent_radius`: `rho1 = max(1.5 min(dx,dy), 0.04 rho_max)`, then `min(rho1, max(1.5 min, a_eq))`, then `min(rho1, rho_max/2)`; geometric series; edges closer than `RING_MIN_WIDTH max(dx,dy)` merged | theory (5.1) equals the code term by term; accuracy below (section 4) | **holds as coded**; own rule fitted for no effect on the existing boards, not tuned (theory says so) |
| F-059 | lateral ring resistance `Δ/(2SL) + Δ/(2SL)`, `L = NΔxΔy/Δ` (5.2) | own (strip approximation) | `_one_node_network` | the strip against the annulus is 0.43 to 0.79 (theory 5.1, closed form); not re-run | **holds as an own approximation** |
| F-060 | self term of a square cell `ln(0.447 √(ΔxΔy))` | geometric mean distance of a square to itself, Maxwell: `ln g = ln a + (1/3) ln 2 + π/3 − 25/12`, `g = 0.44705 a` (from memory, closed form; Maxwell not in the library) | `0.447 √(dx dy)` in `_footprint_potentials`, `_footprint_potentials_blocks`, the zone blocks | Monte Carlo (4 million pairs) `exp(mean ln d) = 0.44718`; closed form 0.44705 | **holds** (0.447 is the constant to 1e-4 relative; the log moves by 1e-4) |
| F-061 | Bessel factors `f_R = 4(I₀ − 2I₁/x)/(x I₁)`, `f_P = 4(2/x² − 1/(x I₁))` (5.4) | the interior of a uniformly heated disc on a leaking sheet, `θ = q/g + A₀ I₀(r/λ)`: the `I₀` branch of Shen eq. 19 (read on the PDF page 10 image; Shen's sheet has no source, the particular solution `q/g` is added) | `_interior_factors` (exponentially scaled Bessel functions; `x < 0.01` gives 1) | derivation redone here (mean, boundary and centre of the disc, lateral outflow `Q_lat = −2π a S θ'(a)`) gives exactly the coded forms; a radial finite-volume solve (4000 rings) gives f_R = 0.99990 / 0.99627 / 0.96077 / 0.86625 / 0.65805 / 0.40962 and f_P = 0.99979 / 0.99255 / 0.92235 / 0.74264 / 0.39754 / 0.12375 at x = 0.05 / 0.3 / 1 / 2 / 4 / 8, equal to the code to the 5th digit | **holds** (the disc is assumed for every footprint shape: an own approximation, stated in theory 5). Side finding: Shen's printed eq. 19 writes `P = −2πktz[aI₁(z) + bK₁(z)]`; the derivative of `K₀` gives `−bK₁`: a sign misprint of the paper on the `K` branch, not used by the Lumped (`b = 0` in a disc); the Analytic influence uses `K₀(r/λ)` itself, not the flux |
| F-062 | peak `θ_peak = θ_ring0 + Q_lat f_P (φ_mean − φ_min)/(2πS₀)`; the part reads `max(peak, drawn field)` (5.5) | own (the lossless disc limit is `Q/(8πS)` centre to mean: checked, it is the `x → 0` limit of `f_P`) | `lumped.py`, `analysis.heater_stats` | lossless limit exact; the potentials sum against every cell within 0.1 / 0.15 % (theory 5; `tests/test_lumped_footprint.py`) | **holds as coded**; quantity: section 6 |
| F-039 | annulus link (5.8) and micro peak (5.9) | own derivations (Krogh cell; Krogh not opened) | `viaconstriction.annulus_out_resistance`, `rim_minus_mean`, `krogh` | derivation redone here; a radial finite-volume solve gives 2.890542 / 1.890403 / 0.196437 K/W for the annulus (r_in / r_out 0.2 / 2, 1 / 2, 1.9 / 2 mm, S = 0.0135 W/K), equal to the code to 7 digits; Krogh mean-to-wall 9.360216 / 22.008500 (numeric 22.008504) and rim minus mean 2.178093 / 2.806937 K/W, equal | **holds** (A3 also checked by quadrature) |
| F-040 | core radius `0.7071 d_nn`, the 92 % | own assumed | `CORE_R`, `MAX_CORE` | `REVIEW_A3`: the one resolved zoned cluster -2.4 / +1.0 % | holds on the one resolved board (A3) |
| F-063 | sub-cell raster (half the side, floor 0.125 mm, 1.7 KB per cell) | own | `lumped.small_part_cell` | validation 35.3 (on the program): 0.2 to 0.3 mm parts stay 3.5 to 6.7 % cool; the -0.8 to +1.6 % of the research folder is of another tree (RCA-024) | **holds, fitted range**: parts of 0.2 to 2 mm, 24 x 24 mm board, two layers, against the FVM at 0.0625 mm |
| F-064 | near-edge rule `gap ≤ max(side, 5 mm)` | own | `checks.check_lumped_near_edge` | re-run of the 180-case sweep on 2.7.1 (section 4.2): 70 cases more than 8 % cool, 69 flagged, 51 false alarms (printed 58 / 57 / 63) | **holds, fitted range** (two-layer full-copper boards of 40 x 40 and 100 x 80 mm, against the FVM) |
| F-065 | via-cool warning (array past the footprint edge, centroid offset 0.1, side ratio 1.5) | own | `checks.lumped_via_cool_warning` | fitted on 28 boards against the FVM at 1/8 mm (validation 18.1); not re-run | **holds as an own rule, fitted range** (7 silent cases of 28, up to 14 % of the rise) |

A detail of the code not in the theory: `lumped.py` line 322 clamps `φ_boundary − φ_mean` at 1e-3 before (5.3) (a floor for a footprint of one cell); harmless, worth a word in theory 5 (item D1).

## 3. Re-runs: printed numbers

| run | command (`releases/2.8.0/audit/scripts/`, run from the repository root with the root as the first argument) | printed |
| :-- | :-- | :-- |
| R1, uniform boards | `study_a4_uniform.py` (the 45 boards of the L4L9 sample: 30 x 20, 60 x 40, 100 x 80 mm, two layers of 1.6 mm, 60 x 40 also 3.2 mm and four layers; a 10 mm, 2 W part at the centre, the middle of a side or a corner; `h_side` 10 / 50 / 200; Lumped at 0.5 and 1 mm, Analytic at 1 mm, FVM as shipped at 0.5 mm, `layered3d_side` at 1 mm, at 0.5 mm on 30 x 20 mm; 0.88 GB, about 4 min) | section 4.1 |
| R2, closed forms | `study_a4_closed_forms.py` | section 2 |
| R3, validation 2 and 2.1 | `research/models-comparison/scripts/validation_study.py` (295 s; **peak 8.3 GB**, the 3D solid at 0.5 mm of the grid table: above the 3 GB budget of this review, run alone under the lock; the 2.7.0 audit had measured 6.7 GB) | the new tables are in `docs/validation.md` 2 and 2.1; the FVM moved by +0.06 to +2.04 K since the printed tables (physical slabs of section 43, drawn-layer film of section 40), the 3D solid column did not move |
| R4, near-edge sweep | `study_a4_near_edge.py` (the 180 cases of validation 35.1 through `api.simulate`; 57 s, 0.36 GB) | all -7.4 [-22.2, -0.8] %, footprint mean -6.4 [-13.8, -0.8]; side gap 0 / 5 / 30 mm -10.4 / -5.0 / -2.5 %; corner -17.1 / -8.2 / -2.7 %; rule: 70 bad, 69 flagged and bad, 51 false alarms; flagged -9.4 %, others -3.6 % |
| R5, local transient | `study_a4_local_transient.py` (the ten boards of validation 4.1 through `fvm.step_responses` at 0.5 mm, `analytic.step_responses` at 1 mm, `lumped.step_responses`; 41 s, 1.5 GB) | Analytic time to 63 % -9.1 to +0.6 % of the FVM on the older tree, **-9.1 % to +3.2 % after the hot-point fix** (4 L vias + 300 W/m²K heatsink -9.1 %); FVM of that board 11.21 s at 0.5 mm, 11.22 s at 0.25 mm; Lumped -41.4 to +13.3 % |
| R6, validation 7 | `research/models-comparison/scripts/study_time_and_coefficients.py` (73 s, 0.7 GB) | FVM against Analytic within 0.51 K (printed 2.2 °C), FVM t63 19.5 s (19.2); FVM against FDM 0.78 K (0.69); profile peaks 136.5 / 133.0 / 135.8 °C (135.3 / 131.8 / 134.7); CSV peaks 120.3 / 124.0 / 119.8 °C (119.5 / 116.1 / 115.1); the new numbers are in `docs/validation.md` 7 |
| R7, warnings on R1 | `study_a4_warnings.py` | `check_reduced_edge_laminate` fires on every board at 200 W/m²K and on the 3.2 mm boards at 50; the Lumped near-edge warning on every side and corner case and on the 30 x 20 mm centre (5 mm gap); the Analytic edge warning on none (uniform copper, as designed) |
| R8, per-layer edge | `research/analytic-edge-and-transient/scripts/study_perlayer_edge.py --part 2` (28 s, 0.88 GB; waited for another agent's lock) | 48 boards of two or more layers: worst 4.91 %, mean 1.19 %, signed -4.91 to -0.01 % against the shipped FVM at 0.5 mm (the 2.7.0 audit to the digit); one layer at 200 W/m²K, corner -7.83 % (printed -7.3 %) |

## 4. Accuracy of the Lumped and the Analytic, both numbers

### 4.1 Uniform boards (R1)

The independent 3D solver at 1 mm reads 0.3 to 0.9 % hotter than at 0.5 mm on the 30 x 20 mm boards at 200 W/m²K (74.70 against 74.08 K at the centre), less at lower `h_side`; the '3D' errors at 200 W/m²K below are therefore about 0.5 to 0.9 point too negative. Error of the hottest rise, %:

| case | Analytic vs FVM | Analytic vs 3D | Lumped 0.5 mm vs FVM | Lumped 0.5 mm vs 3D | FVM vs 3D |
| :-- | --: | --: | --: | --: | --: |
| part at the centre, all boards and `h_side` | -5.68 to -0.15 | -8.07 to -0.19 | -5.64 to +0.17 | -8.04 to +0.16 | -2.54 to -0.01 |
| part at the middle of a side | -7.11 to -0.14 | -9.66 to -0.16 | -13.91 to -2.61 | -16.28 to -2.69 | -2.75 to -0.02 |
| part in a corner | -11.40 to -0.09 | -14.89 to -0.10 | -23.12 to -8.28 | -26.15 to -8.35 | -3.94 to -0.02 |
| only `h_side` 10 W/m²K | -1.04 to -0.09 | -1.40 to -0.10 | -21.51 to +0.17 | -19.20 to +0.16 | -0.96 to -0.01 |

(The 100 x 80 mm rows have no 3D value; the Lumped at 1 mm is 0.3 to 2.6 points warmer than at 0.5 mm, e.g. the 60 x 40 mm corner at 200 W/m²K -16.56 against -18.15 %.)

What this says:
* The Analytic is within 1.4 % of both references at the default `h_side` 10 W/m²K. At 200 W/m²K it reads cool by 2.4 to 11.4 % against the shipped FVM and 3.7 to 14.9 % against the 3D solver: the laminate edge film at the copper temperature (`REVIEW_L4L9` P3); the warning `checks.check_reduced_edge_laminate` covers it from 150 W/m²K·mm.
* The Lumped reproduces the Analytic at the centre (within 0.6 point); near a side or in a corner it reads 3 to 23 % cool against the FVM (up to 26 % against the 3D solver), at every `h_side`: the near-edge limit of theory 5 ('up to -22 %'), here **narrower**: -23.1 % on a 3.2 mm board in a corner at 200 W/m²K against the FVM, and the 100 x 80 mm corner at 10 W/m²K reads -21.5 %.
* The FVM itself is within 1 % of the 3D solver at 10 W/m²K and 1.3 to 3.9 % cool at 200 W/m²K (the 3D at 1 mm; about 0.8 point less at 0.5 mm).

### 4.2 Near a side or a corner: the 180 cases of validation 35.1 (R4)

On 2.7.1 the sweep prints the numbers of the 2.7.0 audit to the digit (-7.4 [-22.2, -0.8] %), not the -6.6 [-22.0, +1.4] % of validation 35.1 and of the study (they were against the FVM before the laminate band of 2.6.0). Against the FVM, the model the rings were built against. The independent 3D solver (R1) adds 0.1 to 3 points at 200 W/m²K: a 10 mm part in a corner of a 3.2 mm board -26.2 % (FVM -23.1 %). The warning text (`checks.py` 725, 730, 735) quotes '8 to 9.5 %' on average for flagged parts (now -9.4 %: holds) and 'up to 22 %' (now -22.2 % against the FVM, -26 % against the 3D solver: **narrower**, item W3).

## 5. The transient against the independent finite-element reference

The reference is `research/transient-reference-boards` (reviewed GO; finite-element transient of `research/independent-fem-extensions`, Crank-Nicolson, five boards, the hottest top node, mesh-converged to 0.05 % in the plateau and 0.2 % in the time to 63 %). Its numbers were read, not re-run here (its environment is outside git); the program side of its Table 2 was reproduced bit for bit by its own review. The documents' transient claims against it:

| claim (where) | as written (reference) | against the finite elements | verdict |
| :-- | :-- | :-- | :-- |
| Analytic local transient: t63 -8.1 to +0.5 % on 12 boards (theory 6, validation 4.1, the heatsink warning) | FVM at 0.5 mm | re-run (R5): -9.1 to +0.6 % of the FVM (FVM converged, 11.21 / 11.22 s); finite elements (other boards): t63 +1.0 to +3.9 % at 0.5 mm, +0.9 to +7.4 % at 1 mm, plateau -0.3 to -1.0 % | **narrower** (-9.1 %, the warning says -8 %: item W1); the independent figure is new |
| square-wave peak within 1.7 %, swing within 3.6 % (validation 4.1) | FVM | finite elements: peak -2.1 to -3.4 %, swing -3.5 to -5.0 % on the via-free boards; on the via board the swing is -11.2 % (the read-out point, RB-152) | **narrower / misleading as accuracy**: the agreement with the FVM is real, both are cool against the reference |
| Lumped zoned step response within 4 to 10 % of the FVM from 0.01 to 100 s (RCA-004, validation 18.2) | FVM 0.5 mm | finite elements, `vias` board (6 mm part over a 4 x 4 cluster): the Lumped +2.5 / +3.5 / +2.2 / +1.7 % at 0.3 / 1 / 3 / 10 s, t63 -0.4 % (0.5 mm); but no layered model is right in the first seconds on a two-layer board (two2: Lumped -47 % at 0.3 s) | **holds on the one via board, with the first-seconds limit**; whether that board is zoned in the Lumped was not checked here |
| the profile peak of the zones within 5.4 % (RCA-011) | FVM 0.25 mm | finite elements: Lumped wave peak -2.8 % (simple4), -1.7 % (two2), +0.5 % (vias) at 0.5 mm | holds on these boards (self-comparison replaced by an independent number) |
| Robin edge t63 -3.3 to +5.9 % (validation 4.1 'Time', RCC-030) | FVM at 2 mm | the FVM at 2 mm reads t63 up to +28 % off the finite elements (simple4, a misaligned 6 mm part; +2.4 % aligned, `transient-reference-boards` 4.4); at 1 mm +3.2 % | **misleading**: the reference is not converged in time; note added |
| animation FVM against Analytic within 2.2 °C 'after calibrating the vias per heater' (validation 7, VA-053) | FVM 1 mm | re-run (R6): within 0.51 K; the mechanism is the local transient | **stale** (updated) |
| first ring: Lumped t63 0.92 to 1.03 times the FVM's (validation 31.3) | FVM | not on the reference's boards | **cannot be checked** independently here |
| the Analytic transient with vias (RB-152) | finite elements | -21.7 % at 0.3 s, swing -11.2 %: the step response is read at the hottest point of the board WITHOUT the vias; at the steady hottest cell -7.9 % and -1.9 % | **defect, fixed after the base of this review**: `fix/analytic-transient-hot-point` was merged into `development` (35eeb773) while this review ran on 5fc91430; the R5 numbers are of the code before the fix (item P1: re-run) |
| the first seconds (all layered models) | finite elements | -58 / -30 / -9 / -1.4 % at 0.3 / 1 / 3 / 10 s on a two-layer board, every model and cell: one node per layer holds the copper and half the gap | **limit to record**: no document of the program states it for the step response and the animation (item D2) |

## 6. Quantity compared (L11 step 5)

* The Lumped network carries ring means; the footprint node is the area mean of ring 0, and the part reading is the peak (5.5) or the hottest drawn cell, whichever is larger (`analysis.heater_stats`, validation 48). Every Lumped figure in this review (R1, R4, R5) is the board maximum `t_max`, which for one powered part is the part peak; the footprint mean is given in R4. The zone studies (validation 18.2, 50) quote both the via effect (a difference of two maxima) and the hottest temperature; the warning `checks.py` 868 leads with the via effect (RCA-001, item W2).
* The Analytic quotes the hottest temperature of the field on the 1 mm cell; the independent 3D solver of R1 reports the hottest node of the top copper slab; the FVM the hottest cell. Same quantity, different cells (0.5 to 1 mm): the 3D at 1 mm is up to 0.9 % hotter than at 0.5 mm (section 4.1).
* The transient reference reads a node (the hottest top node of the footprint); the program's step responses read the hottest cell (FVM, FDM), the part peak (Lumped) or the point of the board without vias (Analytic, the defect of RB-152).
* Shen eq. 19 gives a temperature and a flow at a radius of a thin disc; the program uses its interior (`I₀`) branch for means, boundary values and the centre of a uniformly heated footprint: the same quantity, derived here.

## 7. Program, test and study items (not edited here)

| item | change | frozen-number risk |
| :-- | :-- | :-- |
| P1 (**STALE**: `DECISIONS_2.md` 9 and 10: the fix moved no frozen number and its pending file was removed; the re-measured Analytic range is -9.1 % to +3.2 % of the FVM, not -9.1 to +0.6 %) | `fix/analytic-transient-hot-point` (RB-152) is merged into `development` (35eeb773) after the base of this review: re-run `study_a4_local_transient.py` on the merged tree (the via boards of validation 4.1 move; example board U1 +0.69 % plateau, -1.0 % t63), update the -9.1 % and the heatsink warning key with those numbers, and measure whether the '5 to 7 % low' square-wave peaks of the heatsink warning are the same defect | Analytic transient records of the boards with vias (example board U1 plateau +0.69 %, t63 -1.0 %) |
| P2 | the first seconds of a step (one node per layer holds copper and half the gap): a warning or a stated limit in the animation and the step response, like the closed-form floor of fast waves (`research/transient-reference-boards` INTEGRATION 1) | none for a text; a model change would move every transient record |
| P3 | (from `REVIEW_L4L9` P3, confirmed here) the Analytic and the Lumped keep the laminate edge film on the copper node: -2.4 to -11.4 % against the shipped FVM at 200 W/m²K, -3.7 to -14.9 % against the 3D solver; warned | high (every record with `h_side`) |
| W1 | `analytic.HEATSINK_TRANSIENT_KEY` '-8 % to +1 %' and the text at `analytic.py` 1191: the re-run gives -9.1 % on the 4 L board; quote '-9 % to +1 % against the converged FVM' and the independent '+1 to +4 % at 0.5 mm (finite elements, five boards)' (decision 3 of `DECISIONS.md`); tests look for the key | none (text; `tests/test_analytic_transient_warning.py` and the Results-summary tests) |
| W2 | `checks.py` 866 to 872 (zoned Lumped): leads with 'via effect 4.0 to 4.6 % off on average (up to 21 %)', a comparison with a fine-grid layered solver that is partly two errors cancelling (RCA-001); lead with the hottest temperature (1.6 to 2.6 % of the rise, up to 7.6 %) and name the reference; the placement noise of 1 to 3 points (validation 50) | none (text) |
| W3 | `checks.py` 730, 735 'up to 22 % of the rise at a corner': -22.2 % against the FVM, up to -26 % against an independent 3D solver at 200 W/m²K; the docstring at 697 already has -7.4 / -22.0 | none (text) |
| W4 | `copper.REDUCED_MODEL_WARNING` (RCB-025): measured before the capped first ring; re-measure with A5 | none (text) |
| D1 | theory 5: state the floor `max(φ_boundary − φ_mean, 1e-3)` of `lumped.py` 322 | none |
| D2 | theory 2.4 / 6 / user guide: the first-seconds limit of the step response and the animation (P2) | none |
| M1 | `CLAUDE.md` (Decisions Log, the first-ring entry) quotes '-13.7 % to +0.3 %': against the FVM at 0.25 mm and partly a cancellation; same-cell -13.1 / +1.0 % (RCB-018). For the maintainer | none |
| S1 | `research/analytic-edge-and-transient/lib/calib_variants.py` reads `analytic._calibrated_dynamics` at import (removed in 2.6.0), so `study_transient_both.py`, `study_4l_convergence.py` and every script that imports them fail on the program: point them at `lib/analytic_v251.py` or the program's `step_responses` (as `study_a4_local_transient.py` of this review) | none |
| S2 | the 29 + 17 via boards of validation 18.1 and the 54 unlike-layer boards of 4.1 have no committed script (`REVIEW_A3` T5, `REVIEW_L4L9`); commit them and re-run against an independent reference | none |
| T1 | a closed-form test of the disc factors: `lumped._interior_factors(x)` against the radial finite-volume values of section 2 (x = 0.3 / 1 / 4: f_R 0.99627 / 0.96077 / 0.65805, f_P 0.99255 / 0.92235 / 0.39754, 1e-4), and the 0.447 against Maxwell's 0.44705 | none |
| T2 | the null-via test of the zones (RCB-011): vias with plating 1e-12 m read within 6.1 % of the rise of the no-via board (the bias the theory states) | none |
| T3 | a battery test of the near-edge level (`tests/data/lumped_near_edge_cases.json` holds the 2.6.0 numbers): re-baseline it to the 2.7.1 sweep of R4 (-7.4 % mean; 70 / 69 / 51) | none (test data) |
| T5 | `tests/test_analytic_perlayer.py` 121: the docstring says -4.07 to +0.06 %; on 2.7.1 -4.91 to -0.01 % (bound of the test unchanged) | none |
| T4 | the Analytic local transient on the 4 L board: time to 63 % within -10 % and 0 % of the FVM at 0.5 mm (now -9.1 %), so the stated range of the warning stays true | none |

## 8. Claims: verdict and action

Checked on the PDF page image: F-061 (Shen p. 10), RCC-021 (Muzychka Part II p. 4), RCA-009 (Shen pp. 5, 14, by `REVIEW_A3`). Cannot be checked from the source (not in the library): RCA-025 (Seri Lee), F-060 (Maxwell), the disc and image solutions (Carslaw-Jaeger), Krogh. Every other claim of A4 is an own derivation or a measurement, checked by re-run or against an independent solver as said.

| id | claim (short) | verdict | action |
| :-- | :-- | :-- | :-- |
| T-097 | Lumped via arrays: up to 16 % of the rise with zones; 18.1 says 8 to 26 % | **holds against the layered references** (FVM 0.25 mm, fine-grid layered solver); the 8 to 26 % of 18.1 is the one-node footprint before the zones (no contradiction) | sentence in theory 5.1 |
| T-100 | zones: bump essential, cluster well kept, whole power on A 25 % hot | **holds as a self-comparison** (the fitting target); one independent zoned cluster -2.4 / +1.0 % (`REVIEW_A3`) | none; S2 |
| T-113 | Analytic edge warning fires on every board above 3 % | **narrower**: true against the FVM; against the 3D solver the uniform boards (silent by design) reach -14.9 %, each covered by `check_reduced_edge_laminate` on the 45-board sample (R7) | note in validation 4.1 |
| T-120 | Analytic via tiles: 20 -> 1.8 %, held-out 2.9 % | **holds only against the program's FVM, stale (pre-2.6.0)**; not re-run (no committed script) | A3 note in 18.1; S2 |
| VA-006 | 3D solid column of validation 2 | **holds** (re-run: the column does not move); it is the program's solid, not an independent reference | table re-run, note in 2 |
| VA-007 | hatched board: field 0.05 % from the 3D solid, face term 2.33 K | **stale**: the field now +0.3 % (106.50 against 106.23 °C); face readings not re-run | note in 2 |
| VA-035, RCC-002 | per-layer edge 8.64 -> 4.07 % (4.91 % against today's FVM) | **holds as restated** (R8: 4.91 / 1.19 % on 2.7.1); the 4.07 / 0.90 % are of the FVM before 2.6.0 and are still quoted in `tests/test_analytic_perlayer.py` 121, CLAUDE.md, `research/analytic-edge-and-transient` INTEGRATION 9 and `docs/for-the-project-documents.md`; one-layer row narrower (-7.83 %) | note in validation 4.1; item T5 (test docstring), M1 |
| VA-043 | local transient t63 -8.1 to +0.5 %, reference converged | **narrower**: -9.1 to +0.6 % on 2.7.1; the reference **is** converged (11.21 / 11.22 s); independent t63 +1.0 to +3.9 % | notes in theory 6 and validation 4.1; W1, T4 |
| VA-048, RCC-025 | FVM 13 to 17 % low at 200 W/m²K at the edge | **superseded** by the band of 2.6.0 (-0.4 to -6.2 % against finite elements; -0.01 to -3.94 % against `layered3d_side` here) | note in 4.1 |
| VA-053 | animation FVM-Analytic within 2.2 °C after the per-heater calibration | **stale**: 0.51 K with the local transient; t63 19.5 s | validation 7 updated |
| RB-152 | Analytic transient reads the point of the board without vias | **true defect, fixed** on `development` after this review's base (confirmed by the reference's numbers, not re-run on the fix) | P1 |
| RCA-001 | zones 3.9 / 9.1 % on 36, 4.5 / 20.2 % held-out | **holds as model-to-model** (sheets2d shares the idealisation; partly cancelling errors, review 8.2); the warning leads with it | W2 |
| RCA-004 | zoned step response within 4 to 10 % of the FVM | **holds on the one independent via board** (Lumped +1.7 to +3.5 % early, t63 -0.4 %), with the first-seconds limit on two layers | section 5 |
| RCA-005 | stride decimation always slightly cool | **superseded** (corrected inline; no document quotes it) | none |
| RCA-006 | example board 'no core' | **corrected** (one node, core 98 to 100 %) | none |
| RCA-009 | Shen Fig. 18(a) within +5 to -2 % | **a one-parameter fit** (5.0 mm pad), stated as such in the README (472) and by A3 | none |
| RCA-011 | profile peak with zones within 5.4 % | **holds** against the finite elements on three boards (-2.8 to +0.5 %) | section 5 |
| RCA-019 | near edge -6.6 [-22.0, +1.4] % | **stale**: -7.4 [-22.2, -0.8] % on 2.7.1 (R4) | validation 35.1, theory 5, README/INTEGRATION notes; W3, T3 |
| RCA-024 | sub-cell raster -0.8 to +1.6 % | **stale in the folder** (program: 0.2 to 0.3 mm parts 3.5 to 6.7 % cool, validation 35.3) | INTEGRATION notes |
| RCA-025 | Seri Lee plate, exact series 0.664 / 1.280 / 2.270 against printed 0.66 / 1.29 / 2.38 | **cannot be checked from the source** (not in the library); the -4.6 % on the corner stays unexplained | download (section 9) |
| RCA-029 | deficit falls with the edge film | **superseded** (flat with the band: -7.8 / -7.3 / -7.2 %) | README 3.1 note, validation 35.1 note |
| RCA-046 | zoned peak -1.1 % mean, max 7.3 % | **holds as corrected** (placement-averaged -2.9 to -3.2 %, max 6.9 to 7.2 %; no project document quotes the single placement) | none |
| RCA-048, RCA-050, RCA-051 | FVM equals the 3D without vias; regime (b); MAX_CORE 0.75 | **corrected by the review**, kept | none |
| RCB-005 | example-board arrays within -7.1 to 0 % of the corrected FVM | **model-to-model** (the program's FVM); the two ranges are the same table rounded | README note |
| RCB-011 | dead vias 5.0 % here, 6.1 % in theory 5.2 | **holds**: two different implementations (the researcher's zones here, the adopted ones in `lumped-zones-adoption` 4.6, where 1.5 to 6.1 %) | T2 |
| RCB-014 | option C moves the example board -1.1 to +4.7 K | **holds** (corrected value, FVM-based) | none |
| RCB-018 | -13.7 / +0.3 % (100 x 80) | **narrower**: against the FVM at 0.25 mm; same cell -13.1 / +1.0 %; partly a cancellation | theory-text note; M1 |
| RCB-025 | imported-copper warning measured before the cap | **stale, not re-measured here** | W4 (with A5) |
| RCB-028 | 'the Analytic is exact there' | **false** (within 0.6 % of the FVM) | INTEGRATION and theory-text corrected |
| RCB-044 | zones and one node 'equally far' at 0.25 mm | **superseded** by the converged reference (-1.7 to -2.4 / +2.5 to +3.1 %) | README 5 and INTEGRATION 2 corrected |
| RCB-053 | reference 0.4 to 0.7 % above converged | **corrected to 0.3 to 0.7 %** | README section 7 corrected |
| RCB-059 | FVM -0.5 to -18 % columns of analytic-partial-copper 3 | **stale (pre-2.4.5), not re-run** (needs `resolved3d` at 0.25 mm on several boards) | S2 |
| RCB-064 | spread > 0.25 trigger | **corrected** inline; none | none |
| RCC-008 | one factor on all of C: +52.2 % | **superseded first proposal**; no document quotes it as the program | none |
| RCC-021 | eq. 21 'read as an image of p. 4' | **was false; now true**: read on the PDF page image by L4L9 and this review, matches `lib/muzychka.py` | README section 2 and limits corrected |
| RCC-023 | 135 uniform boards 0.12 / 0.32 % | **misleading** as accuracy (against the FVM without the band; R1: -0.09 to -11.40 % against the shipped FVM, -0.10 to -14.89 % against the 3D solver) | `REVIEW_L4L9` note (on its branch) |
| RCC-028 | unequal copper 5.4 % above spread 3 | **corrected**; no document carries the old rule | none |
| RCC-030 | Robin t63 -3.3 to +5.9 % against the FVM at 2 mm | **misleading** (unconverged reference: the FVM at 2 mm is up to +28 % off in t63) | note in 4.1 |
| RD-069 | Findings: models within a few % of the FVM | **stale and self-comparison** | README note with 2.7.1 numbers |
| RD-070 | finite-element table of four boards | **stale (0ea5f07), unrefined**, not re-run | README note |
| RD-072 | validation 2 and 2.1 print pre-2.6.0 numbers | **true finding; fixed** (tables re-run on 2.7.1) | validation 1, 2, 2.1 |

## 9. Sources to download

* Seri Lee, Electronics Cooling, January 1998 (the plate cases of RCA-025).
* Carslaw and Jaeger, *Conduction of Heat in Solids* (2nd ed.): the disc, the images, the odd eigenfunctions.
* Maxwell, *A Treatise on Electricity and Magnetism*, vol. 2, the geometric mean distance (0.44705).
* Krogh (1919), J. Physiol. 52: the cell of a capillary (the closed forms of 5.8 and 5.9 are own derivations, checked numerically here).

## 10. What was not verified

* The 29 + 17 via boards of validation 18.1 and the 54 unlike-layer boards of validation 4.1 (no committed script; S2); the 36 + 26 family boards of the zones (`lumped-zones-adoption`; fine-grid layered solver, not independent of the idealisation).
* The finite-element transient was read from `research/transient-reference-boards`, not re-run (its environment is outside git); whether its `vias` board is zoned in the Lumped was not checked.
* The section 3 finite-element table of validation (`--fem`) and RD-070: not re-run.
* RCB-059 (the FVM columns of `analytic-partial-copper` 3) and RCB-025 (the imported-copper warning numbers): not re-run.
* Seri Lee (1998), Carslaw and Jaeger, Maxwell, Krogh: not in the library (section 9).
* Memory: the run of `validation_study.py` peaked at 8.3 GB (the 3D solid at 0.5 mm), above the 3 GB budget of this review; it ran alone under the lock. The other runs stayed under 1.5 GB.
