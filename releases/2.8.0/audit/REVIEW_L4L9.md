# Review L4 and L9: cut cells (aperture links, edge film, exact cover) and the Analytic series (Robin edge, tiles, 64 modes)

Literature-to-code assignments L4 (formulas F-066 to F-071) and L9 (F-050 to F-057) of the claims register (`releases/2.8.0/audit/ASSIGNMENTS.md`, `formulas.csv`, `claims.csv` on `docs/audit-claims-register`), with the claims of `docs/theory.md` 1.3, 2.1.1, 2.5, 6 and `docs/validation.md` 4.1, 32, 40 and 47 that rest on them. Program: `development` 5fc91430 (2.7.1 plus documents). Branch `docs/audit-l4-l9`; nothing in `pcbthermal/` or `tests/` was edited (program and test items are in section 4). Method as `REVIEW_A1`, `REVIEW_A3` and `REVIEW_S1`: the formula as printed on the page image against the code, the numbers re-run, an independent reference for each conclusion, one heavy job at a time.

Status: IN PROGRESS (group 1, cut cells, written; group 2, Analytic, runs pending).

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
