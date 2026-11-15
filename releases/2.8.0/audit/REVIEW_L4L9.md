# Review L4 and L9: cut cells (aperture links, edge film, exact cover) and the Analytic series (Robin edge, tiles, 64 modes)

Literature-to-code assignments L4 (formulas F-066 to F-071) and L9 (F-050 to F-057) of the claims register (`releases/2.8.0/audit/ASSIGNMENTS.md`, `formulas.csv`, `claims.csv` on `docs/audit-claims-register`), with the claims of `docs/theory.md` 1.3, 2.1.1, 2.5, 6 and `docs/validation.md` 4.1, 32, 40 and 47 that rest on them. Program: `development` 5fc91430 (2.7.1 plus documents). Branch `docs/audit-l4-l9`; nothing in `pcbthermal/` or `tests/` was edited (program and test items are in section 4). Method as `REVIEW_A1`, `REVIEW_A3` and `REVIEW_S1`: the formula as printed on the page image against the code, the numbers re-run, an independent reference for each conclusion, one heavy job at a time.

**Verdict of trust.** Cut-cell chapter (theory 2.1.1, validation 32, 40): **GO** for the formulas (each matches its source, as the program's own symmetric, two-point variant) and **GO with the corrections of this branch** for the numbers. Validation 32 described the program of 2.6.0 and is now marked stale, with the 2.7.1 numbers. The floor 0.25 no longer acts in the FVM, and the documents that said it binds were wrong. Analytic chapter (theory 6, validation 4.1): **GO** for the series, the Robin basis, the per-layer edge, the modes and the balance (formulas match the verified pages; the balance is narrower above 200 W/m²K). The accuracy statement was **misleading** and is corrected: the 0.117 % against the FVM is against the FVM without the edge band of 2.6.0. Against the program as shipped, the Analytic reads up to 11.4 % cool (14.9 % against the independent 3D solver) on a 3.2 mm board with a corner part at 200 W/m²K. This is warned, and it is a model decision for the maintainer (item P3).

## 1. Pages read on the image (papers library, read only, rendered with pypdfium2 to the scratchpad)

| source | file | pages | what was compared |
| :-- | :-- | :-- | :-- |
| Johansen and Colella (LBNL-39908, 1997) | `Johansen1997LBNL.pdf` | PDF 11, 12 (printed 8, 9) | eq. 13 (apertures), 14 (divergence over the cut volume), 15 (full face), 16 (partial face, interpolated gradient), 17 (Dirichlet front flux), Figs. 3, 4 |
| Bochkov thesis (holds Bochkov and Gibou 2019) | `eScholarship UC item 3qj3t08h.pdf` | PDF 37, 38, 54 (printed 22, 23, 39) | eqs. 1.10 to 1.14, the diagonal and RHS terms, condition 1.21 and the remark that the system stayed invertible without it |
| Yovanovich, Muzychka, Culham (1999) | `YovanovichMuzychkaCulham1999.pdf` | PDF 2, 5 (printed 496, 499) | eqs. 5 to 15 (compound channel, `φ(ζ)`), eqs. 20 to 28 and Table 2 |
| Muzychka, Culham, Yovanovich (2003, Part II) | `Muzychka2003Part2.pdf` | PDF 4 | eqs. 13 to 26 (eigen-equation 14 and 15, `φ_mn` 18, `R_t` 21) |

Not in the library, so not checked against the page: Barrett, Fogelson and Griffith (2022) (the bibliography says R from the arXiv preprint); Papac, Gibou and Ratsch (2010) (N); Carslaw and Jaeger (M). Download list in section 6.

## 2. Formulas: printed against coded

| id | formula | printed | coded | verdict |
| :-- | :-- | :-- | :-- | :-- |
| F-066 | aperture link `a S dy/dx` (`fvm._lateral_links`, `geometry.face_apertures`, `solid3d`) | JC eq. 15 `Δy β (φ_{i+1}−φ_i)/Δx`; eq. 16 `a Δy β [ (1+a)/2 (φ_{i+1,j}−φ_{i,j}) + (1−a)/2 (φ_{i+1,j+1}−φ_{i,j+1}) ]/Δx` (second order) | `a · harmonic(S/c) · Δy/Δx`: eq. 15 times the aperture, eq. 16 **without** the interpolation term | **narrower**: 'JC eq. 15 to 16' is the two-point (first-order at the cut face) form; second order is not claimed by the program; Schwartz et al. found the three-face interpolation unstable. Theory 2.1.1 corrected |
| F-067 | edge film `H L / max(1 + H d / S, 0.25)` (`fvm._cut_edge_film`, `solid3d`) | thesis eq. 1.14 diagonal `μ α L / (μ − α d)`, `d` signed distance from the grid node, positive outside; condition 1.21 `μ − α d > 0` | same expression with `μ = k`, `α = h_side`, `d` positive inside; FVM `d` from the centroid of the board part, clamped `≥ 0` (own choice); 3D solid from the cell centre, signed | **holds** (same expression, sign convention stated); the centroid is the program's own; the printed 1.14 has `+` before the `g` term where 1.13 gives `−` (no effect: `g = 0` here, as S1 found) |
| F-067 | floor 0.25 | none in the sources (1.21 is a sufficient condition; the thesis says the system stayed invertible without it) | `EDGE_FILM_FLOOR` in `fvm.py` and `solid3d.py` | **own rule**; in the FVM it **never acts since 2.7.0** (`d ≥ 0` gives a factor `≥ 1`; block layers have no edge film); in the 3D solid it can act. Theory 2.1.1 and validation 32.3 said it binds from about 1000 W/m²K: **false on the current program** (section 3) |
| F-068 | exact cover, part weights | own geometry | `geometry.exact_coverage`, `part_weights` | holds (shapely to 1e-12, CLAUDE.md log; not re-run) |
| F-069 | signed distance (k-d tree, 2e6 pieces) | own | `geometry.signed_distance_to_outline` | holds (validation 32.4, tests; `tests/test_cut_cell_links.py` passed here) |
| F-070 | edge length per cell nudged inward | own | `geometry.edge_length_on_board` | holds (not re-run) |
| F-071 | same-area rectangle for Lumped and Analytic | own | `Problem.equivalent_rectangle`, `analytic._equivalent_rectangle` | holds as an own approximation (warned; numbers are A2's) |

## 3. Re-runs (cut cells), printed numbers

| run | command | printed |
| :-- | :-- | :-- |
| film floor | `tests/helpers/cut_cell_study.py recess` | peak 140.735 / 104.872 / 98.075 / 92.712 °C at 200 / 1000 / 2000 / 5000 W/m²K for every floor 0.25 / 0.5 / 0.1 / 0.05 (validation 32.3 printed 139.148 / 102.675 / 96.089 / 91.298 with 0.06 to 0.15 K between floors) |
| sliver | `cut_cell_study.py sliver` | error against `two_sheet.py`: 200 W/m²K +5.47 to +6.49 K, 2000 +8.32 to +10.50 K; jump `c` 0.01 to 0.02: -0.40 / +0.54 / +0.92 K at 10 / 200 / 2000 |
| sliver, band off | same, `laminate.edge_band` patched to nothing (scratch `cut_noband.py`) | 200: 136.844 / 136.840 / 136.692 / 136.465 / 132.748 °C (32.1 'after' 136.844 / 136.757 / 136.613 / 136.389 / 132.748); jump -0.004 K; 2000: jump +0.409 K (printed -0.02) |
| frame spread | `cut_cell_study.py frame` | square 1 mm: bias / spread / worst +0.21/0.15/0.27, +1.89/0.26/2.02, +5.92/0.71/6.34, +7.63/0.87/8.11 K at 10/50/200/2000; strip 0.5 mm +0.69/0.10/0.73, +9.89/0.77/10.08, +12.83/0.64/13.00 |
| frame, band off | same, patched | square -0.03/0.13/0.11, -0.05/0.11/0.12, -0.06/0.13/0.15, -0.20/0.34/0.44; strip -0.09/0.11/0.17, -0.01/0.11/0.10, +0.09/0.25/0.13 |
| drawn film (validation 40) | `research/imported-copper-edge-film/scripts/study_drawn_film.py run` (sq_in, sq_wall, sq12, T_wall, L_wall, sq_4l) | every two-layer 'after' cell of 40.2 to the digit (e.g. T_wall 200 1 mm +1.19 / 1.48, L_wall +0.81 / 1.16, sq_wall 1000 -0.93 / 1.86); four layers moved: 200 -2.99 / 4.78 ; -2.28 / 2.56, 1000 -5.96 / 9.44 ; -4.38 / 5.18 (printed -3.30 / 5.03 ; -2.61 / 2.88 and -6.66 / 10.07 ; -5.11 / 5.93) |
| tests | `pytest tests/test_analytic_edge.py tests/test_cut_cell_links.py` | 131 passed (72 s) |

Independent reference for the sliver board: the 3D box of validation 33.4 (written for that review, not committed) gives 140.23 °C at 0.25 mm for the whole column (`c` = 1, 200 W/m²K); the program reads 138.79 °C at 1 mm, 1.3 % of the rise cool. `two_sheet.py` (133.32 °C) lacks the laminate at the edge, so the +5.5 K of the program against it is the reference's missing physics, not a program error.

## 4. The Analytic series (L9): formulas and re-runs

| id | formula | printed | coded | verdict |
| :-- | :-- | :-- | :-- | :-- |
| F-050 | multilayer modal system `A_mn = diag(S_l κ² + h_l) + g Λ` | YMC 1999 eqs. 14, 15: compound channel with `φ(ζ)`, the conduction through each layer's thickness (hyperbolic in `ζ t`) | one node per layer, the thin-sheet (fin) limit, layers joined by `g` | **misleading** as 'the construction is that of YMC 1999; Table 2 reproduced': Table 2 is the 2D strip on a semi-infinite channel (eqs. 24, 26 to 28), reproduced by a research script, not by the program; the program implements the thin-sheet limit. Theory 6 corrected |
| F-051 | Robin roots `δ tan δ = β L_h` (even), `δ cot δ = −β L_h` (odd), norms, `β = h_eff Σs / ΣS` | Muzychka 2003 Part II eq. 14 `δ sin δ = Bi_e cos δ`, `Bi_e = h_e c/k`; eq. 20 norm `sin(2δ)/2 + δ` | `_edge_root`, `_EdgeBasis` (pole-free forms and the four end asymptotes checked by hand) | **holds** symbol by symbol; the odd functions are not in the paper (Carslaw-Jaeger, M; checked against FD by the folder) |
| F-052 | per-layer edge mismatch source, GMRES | own (Green's identity) | `_edge_mismatch_source`, `_per_layer_edge` | holds as own; 4 to 9 products re-measured; balance **narrower** (below) |
| F-053 | influence fill `Σ P K0(r/λ_l)` | `K0(r/λ)/(2πS)` is the Green function of the fin equation (Carslaw-Jaeger, M: **cannot be checked from the source**, standard closed form) | `_influence` | holds; the weighting is own and fitted to the program's FVM |
| F-054 | Woodbury tile correction `(I + G C) y = y0`, 64 modes, tiles `min(max(λ/4, 2.5 mm), 5 mm)` | static condensation (S) | `solve_steady`: `lhs = G C + I`, `f = −C y` | holds (algebra checked by hand); the 64-mode cap is about 1 % on the via effect (`REVIEW_A3` finding 9: -4.3243 / -4.2762 / -4.2697 K at 64 / 128 / 256), not repeated |
| F-055 | modal propagator `ζ⁺ = e^{−μΔt} ζ + (1 − e^{−μΔt}) s/μ` | standard | `_ModalSet` (lines 1122, 1252) | holds (exact for a constant power over a step) |
| F-056 | local transient factor in [0.05, 20] by Brent on `ln s` | own | `analytic_local.FACTOR_BRACKET`, `brentq` | holds as coded; accuracy claims are A4's |
| F-057 | equal-area, equal-centroid rectangle | own | `_equivalent_rectangle` | holds as coded (bounding-box aspect, shifted inside) |

| run | command | printed |
| :-- | :-- | :-- |
| thin sheet against eq. 21 | scratch `eq21_sweep.py` (the test's `_eq21` and `_EdgeBasis`, 10 mm source on 50 mm, `h` 100, edge 50 / 200 / 1000) | k 385: -0.03 % (τ 0.02), -0.21 to -0.31 % (0.1), -0.65 to -1.62 % (0.3); k 50: -0.10, -0.98 to -1.10, -3.81 to -6.07 %; k 20: -0.17, -1.60 to -1.66, -6.93 to -8.59 % |
| 45 uniform boards of validation 4.1 | scratch `analytic_uniform_sample.py` (`research/analytic-edge-spatial/lib/cases.py`; Analytic 1 mm; FVM 0.5 mm with and without `laminate.edge_band`; `layered3d_side` 1 mm, 4 sub-slabs; 27 s, 0.92 GB) | Analytic vs FVM without band -0.33 to +0.01 %; vs FVM with band -0.09 to -11.40 % (30 x 20 x 1.6 mm corner 200: -6.30; 60 x 40 x 3.2 mm corner 200: -11.40; four layers at most -1.10); vs 3D -0.10 to -14.89 %; FVM with band vs 3D -0.01 to -3.94 % |
| balance and modes, unequal layers | scratch `an_balance.py` (60 x 40 mm, fills 1 / 0.2 and 0.2 / 1, corner part, 300 and 600 modes) | balance 1.000000 (10), 0.999973 / 1.000021 (200), 0.999837 / 1.000094 (500), 0.999449 / 1.000266 (1000) W/m²K; 300 to 600 modes at most +0.024 %; 4 to 9 GMRES products |
| validation 47.2 against `layered3d` | `research/fdm-inset-edge/scripts/study_independent_3d.py` (49 s, **4.5 GB peak**, above the 3 GB budget of this review) | every cell of the 47.2 table to the digit (plate_pad 335.493 / 330.066 K, FVM -2.12 / -1.66, FDM -7.31 / -4.32 -> -5.36 / -2.86 %; strips -11.77 / -9.58 / -8.22, -33.63 / -23.43 / -15.89 -> -23.05 / -15.00 / -10.37 %); then the script **crashes** writing `out/independent.json` (the folder `out/` does not exist and is not created) |

## 5. Claims: verdict and action

| id | claim (short) | verdict | action |
| :-- | :-- | :-- | :-- |
| theory 2.1.1 | links after JC eq. 15 to 16 and Barrett eq. 10 to 14 | **narrower** (eq. 16 without its interpolation; Barrett not in the library) | sentence added |
| theory 2.1.1 | film is the same expression as Bochkov eqs. 1.13, 1.14 | **holds** (sign of `d` reversed; centroid is own) | page reference and the own choice stated |
| theory 2.1.1, VB-086 (32.3) | floor binds from about 1000 W/m²K; 80 nodes at 2000; moves the peak 0.06 to 0.15 K | **false on the current program** (since 2.7.0 `d ≥ 0`; peak identical for floors 0.05 to 0.5) | theory rewritten; 32.3 marked superseded; head note of 32 |
| theory 2.5 | spread 0.03 to 0.15 K at 1 mm | **stale** (0.15 / 0.26 / 0.71 / 0.87 K with the band) | corrected |
| VB-084 (32.1) | jump -0.09 / -0.02 K after | **stale** (+0.54 / +0.92 K; +0.00 / +0.41 K without the band) | head note of 32 |
| VB-085 (32.2) | spread 0.09 / 0.07 K at 200 / 2000 | **stale** (0.71 / 0.87; 0.13 / 0.34 without the band) | head note |
| VB-087 (32.4) | FVM within 0.15 K of `two_sheet.py` on a rectangle | **false at 200 W/m²K on the current program** (the whole column `c` = 1 of the sliver board is a rectangle: +5.47 K; the reference lacks the edge laminate), **narrower** at 10 (-0.30 K) | head note (the reference is no longer the right one for a cooled edge; the 3D box of 33.4 is) |
| VB-090 (32.6) | imported copper keeps the earlier links | **stale** (sections 38, 39) | head note |
| VB-137 to VB-140 (40.2, 40.5) | drawn film: before/after table, the hot error of copper to the wall, the cancellation explanation withdrawn | **holds** for two layers (to the digit); four-layer rows **stale** (moved by section 43) | note with the new four-layer numbers |
| VB-177 (47.2) | FDM and FVM against `layered3d` | **holds** (to the digit) | none in the documents; study script item S1 |
| VA-031 (4.1) | 135 uniform boards 0.117 % / 0.324 % against the FVM | **holds against the FVM without the band; misleading as a statement about the program** (−11.4 % against the shipped FVM) | audit note under the table |
| VA-035 (4.1) | per-layer edge 4.07 % worst (4.91 % against today's FVM) | holds as stated (its own caveat); the 48 boards **not re-run** (no committed script prints them, as 4.1 says) | none |
| T-108, VA-039 | balance 0.99997 .. 1.00002 up to 500 W/m²K | **narrower**: that range holds to 200; 0.99984 .. 1.00009 at 500; 0.9995 at 1000 holds | theory 6 corrected |
| T-116, VA-046 | thin-sheet series within -0.03 to -1.1 % of eq. 21 for τ ≤ 0.1 | **holds, narrower**: the range depends on k as well (k 20: -1.6 % at τ 0.1) | theory 6 sentence extended |
| T-115 | YMC 1999 is the construction; Table 2 to four digits | **misleading** (see F-050) | theory 6 corrected |
| F-054 (theory 6.1 Limits) | 64 modes of `G_mod` | **holds** (about 1 %, A3) | none |

Claims of sections 31, 33 to 36, 43 to 46 and 50 are not L4/L9 formulas and stay with A2 and A4. The claims of section 47 checked here are 47.2 only; 47.1 rests on the finite-element limits, whose tool was not recreated (its environment is outside git).

## 6. Program, test and study items (not edited here)

| item | change | frozen-number risk |
| :-- | :-- | :-- |
| P1 | `fvm.py` lines 53 to 54 and the docstring of `_cut_edge_film` (430 to 433) say the floor is reached by bare-laminate nodes at about 1000 W/m²K: comment-only fix; the floor can stay as a safety net or go (the FVM is bit-identical either way on the recessed board) | none |
| P2 | `tests/helpers/cut_cell_study.py` `count_at_floor` counts with the cell-centre distance, which the FVM no longer uses: compute it from the network's own factor, or drop the column | none |
| P3 | the Analytic (and the Lumped) keep the edge film of the laminate at the copper temperature: up to -11.4 % against the shipped FVM and -14.9 % against the 3D solver (3.2 mm, corner, 200 W/m²K; warned from 150 W/m²K·mm). A possible fix: put the laminate half-thickness in series with the edge film inside `β_l`. **Maintainer's decision**; it would move every Analytic record with `h_side` | high (all Analytic records with an edge coefficient) |
| S1 | `research/fdm-inset-edge/scripts/study_independent_3d.py` crashes at the end: `os.makedirs(out, exist_ok=True)` before writing; also its peak of 4.5 GB is worth stating in its header | none |
| T1 | a battery test that the FVM peak does not depend on `EDGE_FILM_FLOOR` (recessed square, 2000 W/m²K, floors 0.05 and 0.5), so the theory statement stays true | none |
| T2 | a battery test of the program on the disc against the radial solver of 32.4 (the review's solver is not committed: commit it under `tests/helpers/`), the program's cut-cell order held against an independent closed form | none |
| T3 | Table 2 of YMC 1999 as a battery test (assignment L9, step 4): **not recommended**, it tests the paper's sums and not the program; the eq. 21 test (`test_thin_sheet_series_against_equation_21`) is the right one; add a row at k 20 W/mK, τ 0.1 (-1.6 %) to hold the stated range | none |
| T4 | the head note of validation 32 shows that `two_sheet.py` is not a valid reference with a cooled edge since the band; the cut-cell tests already switch the band off. Re-measure 32.1 and 32.2 against a 3D reference with the band on, or keep the band-off numbers as the cut-cell statement (decision for A2) | none |

## 7. Quantity compared (assignment step 5)

Johansen-Colella and Bochkov-Gibou measure the error of the whole field in a norm (maximum or L1) on a Dirichlet or Robin Poisson problem with a known solution; validation 32 and 40 compare the hottest cell or the heater mean rise against a reference of the same board. So the order of accuracy of the papers is not what the documents quote: the program's cut-cell statements are about one functional, the peak or the heater mean. Muzychka 2003 eq. 21 and YMC 1999 give the resistance from the source mean; the eq. 21 test computes the same source mean from the program's basis (same quantity), while validation 4.1 quotes the hottest temperature against the FVM (another quantity, same on both sides).

## 8. Sources to download (not in the local library)

* Barrett, Fogelson, Griffith (2022), J. Comput. Phys. 449, 110805 (arXiv 2102.07966, open): eqs. 10 to 14, cited by theory 2.1.1 and 4.
* Papac, Gibou, Ratsch (2010), J. Comput. Phys. 229, 875-889: the origin of the symmetric Robin scheme (N).
* Johansen and Colella, J. Comput. Phys. 147 (1998): the journal version (the library holds the LBNL report).
* Carslaw and Jaeger, Conduction of Heat in Solids: the Sturm-Liouville odd functions and the `K0` Green function (M).

## 9. What was not verified

The 48 unequal-layer boards of 4.1 (no committed script prints them); the disc against the radial solver (32.4); the finite-element limits of 46 and 47.1 (tool not recreated); the 3D solid cut cells (33) and the band (36); the transient and the local transient (A4); the exact cover, signed distance and edge-length formulas beyond the tests that passed here. The scratch scripts of this review are in the session scratchpad, not in the repository (the commands and printed numbers are above).
