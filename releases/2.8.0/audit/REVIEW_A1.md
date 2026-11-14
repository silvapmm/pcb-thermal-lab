# Review A1: thick plates, published cases, convection, metal blocks (with L2)

Assignment A1 of the claims register (`releases/2.8.0/audit/ASSIGNMENTS.md` and `claims.csv` on `docs/audit-claims-register`), the 24 claims of risk 3, and the literature-to-code group L2 (formulas F-017 to F-024 of `formulas.csv`). Program: `development` 5fc91430 (2.7.1 plus documents). Branch `docs/audit-a1`; nothing in `pcbthermal/` or `tests/` was edited: the program and test changes are items of section 4.

## 1. What was re-run and what it printed

| run | where | printed (the numbers this review quotes) |
| :-- | :-- | :-- |
| Seri Lee's plate through `blocks.py` (never done before) | `scripts/study_lee_blocks.py` (this folder) | Rc centre / edge / corner, K/W: FVM 0.5 mm 0.6637 / 1.2796 / 2.2690; FDM 0.6650 / 1.2797 / 2.2679; 3D solid 0.6637 / 1.2796 / 2.2691; printed 0.66 / 1.29 / 2.38 (+0.6 / −0.8 / −4.7 %); exact thin-plate series 0.6637 / 1.2799 / 2.2700 (FVM and 3D solid within 0.05 %, FDM 0.2 %); R0 0.9995 (FVM). 2 and 1 mm: FVM +0.2 / −1.0 / −4.8 and +0.4 / −0.9 / −4.7 % |
| Muzychka et al. 2003, case 1 (a) and the cross (case 3) | `research/effective-conductivity/scripts/study_muzychka_2003.py` (12 s, 1.2 GB) | 1 (a): independent 85.48 / 109.20 C (paper 84.97 / 108.43); FVM 79.94 / 100.95, FDM 79.69 / 100.65, 3D solid 80.09 / 101.11, Analytic 79.95 / 100.96, Lumped 76.65 / 93.01. Cross: independent max 80.62 (paper 80.61), area mean 78.90 (78.87); FVM, FDM, Analytic 79.44; 3D solid 79.69; Lumped 80.19 max |
| case 1 (b) and case 2 | `research/theory-sources/scripts/study_muzychka_more_cases.py` without the 3D solid (its estimate for 1 (b) at 2.5 mm is 8.1 GB, above the 3 GB of this review; peak of the run 3.35 GB) | 1 (b): independent 56.56 / 59.97 (paper 56.55 / 59.94); FVM 56.51 / 59.89, FDM 56.47 / 59.86, Analytic 56.51 / 59.89, Lumped 56.37 / 58.75. Case 2: FVM 94.46 / 98.30 / 96.62 / 96.13 (paper 97.40 / 103.82 / 101.28 / 99.94) |
| case 2 decomposition | `research/muzychka-case2-analytic/scripts/study_case2_reproduce.py --quick` (worktree of that branch) | every number of its sections 2 and 3 to the printed digit: through the thickness 2.06 / 4.70 / 3.82 / 2.94 K, film 0.84 / 0.85 / 0.84 / 0.84 K, with `h` 394.74 the FVM, FDM, Analytic within 0.10 K of the column mean |
| the thick-plate warning on the five published plates (13 sources), `development` and `fix/thick-plate-warning-bound` | scratch script (FVM, the cells of the studies) | see section 2.2 |
| the tests of the group | `tests/test_solid3d_verification.py`, `test_layered_vs_3d.py`, `test_calculator_validation.py`, `test_natural_form.py` on `development`: 26 passed (78 s); `tests/test_thick_plate.py` on `fix/thick-plate-warning-bound`: 26 passed |
| finned block in every model | `research/block-and-fins/scripts/study_finned_block_all_models.py` (3 s) | Lumped +1.6 / +2.2 / +2.1 / +2.5 %, Analytic +0.2 / +0.3 / +0.3 / +0.3 %, FDM −0.1 to 0.0 %, 3D solid +0.6 to +0.8 % of the FVM |
| via arrays of Shen et al. | `research/published-cases-followup/scripts/study_shen_vias.py` (42 s, 2.1 GB) | fvm p/3 −0.6 to +5.4 %, fdm −1.5 to +3.4 %, solid3d −1.2 to −7.2 %, lumped +0.2 to +10.9 %, analytic +1.2 to +14.5 % (was −2 to −8 % for the fvm before 2.6.0) |
| Power Calculator against two datasheets | `research/power-calculator/scripts/calculator_validation.py` | CSD17308Q3 0.986 W (−1.4 %), JEDEC 2s2p 1.029 W (+2.9 %), no vias 0.44 W |
| convection closed forms | scratch, `pcbthermal.convection` | Lienhard Example 8.1: laminar 4.233 W/m²K (printed 4.22), general 4.861 (+15 %); up face against Raithby-Hollands with the thick-layer correction −7.2 / −0.9 / +8.8 / +15.4 % at Ra 3e2 / 1e3 / 1e4 / 1e5; against the upper bound of Yovanovich-Jafarpur at a 20 K rise +3.8 / +12.7 / +23.5 % on 60 × 40 / 100 × 80 / 300 × 200 mm; face down 0.475 Ra^(1/5) gives 1.891 and 2.997 at Ra 1e3 and 1e4; the ratio down/up 0.88 Ra^(-1/20) |
| the coupon of Culham and Yovanovich | `research/published-cases-followup/scripts/study_coupon_program.py` | see section 2.4 |

Pages read on the image (papers library, read only, rendered to the scratchpad): Muzychka et al. 2003 PDF pages 6 and 7 (case 2 data `k` 150, `t` 10 mm, `h` 400; Table 3; Table 4; the cross `k` 50, `h` 50, `t` 10 mm, 80.61 / 78.87 C); Lienhard 2024 printed p 421 (PDF 435, Example 8.1), p 419 (PDF 433, eq. 8.13a, 'the added constant 0.68 accounts for very low values of Ra_L at which boundary layer behavior begins to break down'), p 174 (PDF 188, fin efficiency eq. 4.53), p 441 (PDF 455, mixed convection: no blending formula); Yovanovich 2003 PDF page 6 (Table 3, column μ 0: .9401 / .8009 / .6649 / .5337, the values of `solid3d_verification.py`; that page is 'machine' in the status file and was checked here on the image); Teertstra review PDF page 5 (eq. 21 as printed: `[(C/Ra_b)² + (1/(0.59 Ra_b^(1/4)))²]^(-1/2)`, C 24 symmetric). The Electronics Cooling article of Seri Lee was read as web text: the worked example and its values, an accuracy of 'approximately 5 %', the corner factor C = 2; its equations are images and were not read.

## 2. Findings, ranked

### 2.1 Defect in the documents (fixed): the program's plate model was said never to have been run on Seri Lee's plate, and the published plates were presented without the program's own numbers

`docs/theory.md` 7.5 and 11, `docs/validation.md` 20, 22.1 and 25, `research/theory/README.md`, `research/theory-sources/README.md` 3.11, `research/component-heatsink/NOTES.md` said either that 'the plate model reproduces Seri Lee' (meaning a thin-plate solver written inside a study) or that `blocks.py` was never run. Now measured: `blocks.py` in the FVM, FDM and 3D solid gives +0.6 / −0.8 / −4.7 % against the printed values and is within 0.2 % of the exact thin-plate series (FVM and 3D solid 0.05 %); the −4.7 % at the corner is the article's own correlation (stated accuracy about 5 %). The plate had also been run as an aluminium board in `research/published-cases-followup` 7 (within 0.5 % of the series), which the theory did not cite. The sentences are corrected; the corrected wording names which solver gave each number. `research/theory-sources` 3.11 attributed the independent solver's 0.668 / 1.284 / 2.275 to 'the plate model': corrected.

### 2.2 The thick-plate bound and the published plates (`fix/thick-plate-warning-bound` and `research/muzychka-case2-analytic` verified)

Shortfall of the FVM against the surface the paper reports (independent solver), and the bound of the warning, K (rise in brackets):

| case, source | shortfall | bound on `development` (`q'' t/(2k)`) | warns | bound of the fix (`+ q_f t/(2k)`) | warns |
| :-- | --: | --: | :-- | --: | :-- |
| 1 (a) S1, S2 | 5.54, 8.25 | 8.0 (15 %), 12.0 (16 %) | yes | 8.3, 12.4 | yes |
| 1 (b) S1, S2 | 0.05, 0.08 | below 5 % | no | below 5 % | no |
| 2 S1 | 2.90 (4.0 % of its rise) | 3.3 (4.8 %) | **no** | 4.3 (6 %) | yes |
| 2 S2, S3, S4 | 5.55, 4.66, 3.79 | 8.3, 6.7, 5.0 | yes | 9.3, 7.6, 5.9 | yes |
| cross, centre | 1.18 (2.1 %) | 1.25 (2.3 %) | no | 1.53 (2.8 %) | no |
| column, 70 W over the whole top of the case 2 plate (from the case 2 review) | 1.77 | 0.93 | no | 1.87 | no (2.6 %) |

* On the five published plates the old bound is already above the shortfall of every source (narrowly on the cross); it fails only on the column, where the film term is as large as the gradient. The fix makes it a bound everywhere measured (13 sources and the column) and adds the warning on case 2 S1. The numbers of both branches were reproduced; the fix's tests pass.
* The **5 % threshold has no basis in a source** (formula F-017: own, L): it is a choice. Measured: of the 13 published sources the shortfall exceeds 5 % of the rise on 5 (case 1 (a) both, case 2 S2, S3, S4; S1 is 4.0 %) and the fixed bound warns on exactly those 5 plus S1; no source with a shortfall above 5 % is silent. Keep 5 % with the fixed bound (decision 1 of the maintainer).
* `validation.md` 22 ('the bound is above the real effect in every case') rests on a difference of two models of the program (3D solid minus FVM); now said, with the published-plate check as the independent evidence.

### 2.3 Program items found (not edited; section 4)

1. **The cover of a metal block is sampled 4 × 4** (`blocks.extra_layers` calls `cover(s.polygon, 4)`, `fvm.py:258` and `analytic.py:477` pass `samples=n` to `coverage_fraction`), while the board cover is exact since 2.6.0 (`geometry.exact_coverage`). A block edge that cuts cells gets a coverage error of up to 1/32 of a cell per cut cell, in the exposed film, the capacity and the contact. Not measured here; numbers move only for blocks whose edges are off the grid lines.
2. **`Board.validate` refuses a board whose only path to the ambient is a heatsink** ('the board has no path to ambient (all coefficients are zero)' with `h_top = h_bottom = 0`, `h_side` None and a block with `h_extra` 100): a valid problem (a plate cooled only by its heat sink) cannot be built; the Lee script works around it with fins. Low.
3. Docstrings that say the constant 0.68 of the laminar Churchill-Chu form is 'the leading-edge correction' (`convection.h_natural_vertical`; `tests/test_natural_form.py` comment): Lienhard says it accounts for low Ra where the boundary layer breaks down, and the 2D plate gives 0.35 to 0.54. Text only.
4. `checks.check_fin_channels` docstring quotes 'misses 1 of the 667 cases' without 'by construction' (the grid is graded with the same composite whose `phi` is 0.9 at `Ra_b` 90). Text only.

### 2.4 The coupon (Culham and Yovanovich 1998)

`study_coupon_program.py` (about 5 minutes, under 3 GB): the solver's k_e 7.81 against the printed 8.28 W/mK (−5.7 %, the solver's known offset) and every fvm, fdm, Lumped and Analytic number of `published-cases-followup` 4 printed again (base stack at ε 0.25: fvm +0.12 %, fdm +0.03 %, Lumped −4.27 %, Analytic −3.66 % of the solver's R). The 3D solid moved with its slabs by thickness (2.6.0): +0.27 % instead of −1.59 % at 25 mm, +0.68 % at 36 mm, +2.35 % at ε 1 (the face term, as the fvm); corrected in that README. The Cu / FR-4 / Cu version of the coupon is in the battery (`tests/test_layered_vs_3d.py`, passed); the paper's base stack is not (T8).

## 3. Claims: verdict and action

| id | claim (short) | verdict | action (done on this branch, or item) |
| :-- | :-- | :-- | :-- |
| T-128 | Seri Lee by a re-implementation, `blocks.py` not run | **holds with a narrower statement**; now superseded | `blocks.py` run (2.1); theory 7.5 rewritten with the program's numbers; the corner gap is Lee's 5 % |
| T-131 | up face 0.54 Ra^(1/4) from memory, outside its range, above the YJ bound | **holds** (all numbers reproduced: −7 / −1 / +9 / +15 %, +4 / +13 / +24 %) | none; the Lloyd-Moran source stays N (not in the library) |
| T-144 | mixed `(h_n³ + h_f³)^(1/3)`, Churchill's rule | **cannot be checked** (Churchill 1977 not in the library; Lienhard p 441 cites it and prints no formula) | theory 8 now says so and that the blend is used for every orientation; no mixed case is checked |
| T-164 | 3D solid vs finite elements within 0.2 % / +1.6 % / +8 %, 4 slabs, not re-run | **holds as stated** (stale, disclosed) | the re-run is A2 (T-090) |
| T-165 | section 11 row 'Plate (block) model' | **misleading** (the row named the program's plate model for a re-implementation) | row rewritten with `blocks.py` and the four Muzychka plates |
| VA-124 | validation 20 plate check +0.6 / −0.8 / −4.6 % | **misleading** (presented as the program) | sentence says which solver, adds `blocks.py` +0.6 / −0.8 / −4.7 % |
| VA-149 | thick-plate bound above the real effect in every case | **holds with a narrower statement** (the 'real effect' is model minus model) | sentence added; independent check on the published plates (2.2) |
| VA-156 | cross and case 1 reproduced by the independent solver | **holds**, but omitted that the program reads them low | the program's numbers added to 22.1 (2.1 % on the cross, 8.4 / 9.0 % on 1 (a), within 0.2 % on 1 (b), 2.9 to 5.5 K on case 2) |
| RA-018 | the thick-plate criterion 'never fires on the cases the program is built for' | **misleading** (true on the 74 block cases only; case 2 S1 silent, the column under the bound) | sentence restricted to the 74 cases, with the published counter-cases |
| RA-055 | via arrays: fvm −2 to −8 %, ... (non-conservative) | **false on the current program** (pre-2.6.0) | re-run: fvm −0.6 to +5.4 %, lumped up to +10.9, analytic up to +14.5 %; summary row and 6.3 note rewritten |
| RA-103 | face down: Fujii-Imura 5 to 49 % below the program's 0.27 Ra^(1/4) | **holds for a superseded law** | note: the 0.475 Ra^(1/5) law is a constant 8.1 % above Fujii-Imura on 2 A/P; 'not shown conservative' still holds; no document calls the face down conservative (`grep`) |
| RA-114 | Lee 'reproduced by the plate model (0.668, 1.284, 2.275)' | **false** (those are the independent solver) | corrected in theory-sources 3.11 |
| RA-140 | 'the metal plate model reproduces Seri Lee' | **misleading** then; **holds now** that `blocks.py` was run | research/theory README says which solver |
| RA-149 | calculator reproduces two datasheets (−1.7 %, +3 %) | **stale** | re-run: −1.4 % and +2.9 %; research/theory README updated. `docs/calculators.md` 2.1 still quotes 0.968 W (−3.2 %) and 1.039 W (+3.9 %): stale, left to A5 |
| RA-151 | JEDEC 2s2p case rests on unread JESD51 | **holds** (N) | bibliography entry now records the dimensions taken from ROHM 64AN113E and the assumed 3 × 3 vias |
| RA-306 | FVM within 2.5 % of the FEM for pads of 20 mm and more | **misleading** (pre-2.4.5, unconverged FEM on the same side) | caveat added; re-run is A2 (T-090) |
| RA-341 | mould ~1 %, heatsink 41 to 51 %, against the node prototype | **holds with a narrower statement** (the prototype is not evidence) | caveat added to the findings |
| RA-342 | top path within 0.4 to 0.9 K of the prototype | **stale** (0.5 to 1.4 K on 2.6.0; prototype not evidence) | findings line requoted with the caveat |
| RA-346 | heatsink base 0 to 13 % below Lee's closed form | **cannot be checked** (the closed form is from memory; the article's equations are images, N) | none; status reconciled in theory 12 (EC1998 is S: numbers R, equations N) |
| RA-347 | 'the block layer reproduces the published spreading resistance' | **false when written** (a re-implementation), **holds now** | NOTES corrected with the `blocks.py` numbers |
| RA-366 | Lumped and Analytic with the block +1.6 to +3.6 % | **stale** | sections 2 and 4.3 say 'before 2.5.0' and give 2.7.1: Lumped +1.6 to +2.5, Analytic +0.2 to +0.3 % |
| RA-522 | the independent solver 'supports the 1/5 laws' | **misleading** | reworded 'consistent with the level' (theory 8 never said 'supports') |
| RA-562 | 0.68 is the leading-edge term | **false** | validation 22 and plate-h-level INTEGRATION corrected with Lienhard's own words; the docstring and the test comment are item 3 |
| RA-596 | `Ra_b < 90` misses 1 of 667 | **holds by construction only** | validation 25 row and fin-channel INTEGRATION say so and quote the measured arrays (one silent array of six); docstring is item 4 |

## 4. Program and test items (for an executor on a `fix/` branch)

| item | change | frozen-number risk |
| :-- | :-- | :-- |
| P1 | merge `fix/thick-plate-warning-bound` (verified here: the bound holds on 13 published sources and the column; 5 % kept) | none (warning text only); text conflicts with this branch in `docs/theory.md` 7.5 and `docs/validation.md` 22.1 (keep both) |
| P2 | block cover exact (`geometry.exact_coverage` for the block polygon, as the board) | moves the block records whose edges cut cells (`finned_block` and any block off the grid lines in the harness): a pending file |
| P3 | `Board.validate` counts the `h_extra` of heatsinks as a path to the ambient | none |
| P4 | docstring of `convection.h_natural_vertical` and the comment of `tests/test_natural_form.py`: '0.68 is a fitted constant that accounts for low Ra' | none |
| P5 | docstring of `checks.check_fin_channels`: 'misses 1 ... by construction of the composite; one measured array of six is silent' | none |
| T1 | **Seri Lee through `blocks.py`** (new test): FVM at 1 mm, the construction of `scripts/study_lee_blocks.py`; Rc within 0.5 % of the exact series 0.6637 / 1.2799 / 2.2700 and within +1 / −1.5 / −5.5 % of the printed values (one-sided: the corner must stay below the printed 2.38) | about 3 s |
| T2 | **Muzychka cross** (case 3): FVM 1 mm; centre centroid within 79.44 ± 0.1 C; assert the shortfall to the paper's 80.61 is 0 to 2.5 % of the rise (one-sided: the program reads low, never above the paper) | about 5 s |
| T3 | **Muzychka case 2**: FVM 1 mm; each centroid 2.5 to 6.0 K below the paper (one-sided), and the column-mean difference with `h` 394.74 within 0.15 K; the warning fires on all four sources (after P1) | about 2 s |
| T4 | **Muzychka case 1 (a)**: FVM 2.5 mm; centroids 8 to 10 % of the paper's rise low (one-sided) and both sources warn | about 5 s |
| T5 | **Muzychka case 1 (b)**: FVM 2.5 mm; centroids within 0.3 % of the paper's rise | about 10 s (the program; the independent solver is not in the test) |
| T6 | Table 2 of Yovanovich-Muzychka-Culham (thin slab `t/c` 0.1, Bi 2): FVM within 3 % of psi, the program's numbers of `published-cases-followup` 3.3 | under a minute |
| T7 | Lemczyk et al. Table 4, the three-layer board: FVM −1.7 to 0.0 %, `published-cases-followup` 5.3 | under a minute |
| T8 | the coupon base stack (`published-cases-followup` 4): FVM within 0.5 % of `R_solid` at ε 0.25 | about a minute |

## 5. L2: the formulas of thick plates, blocks and fins

| fid | formula as coded | source as printed (page verified) | range of the source / where applied / warning | quantity: paper / program | in the battery | verdict |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| F-017 | `Δθ = q'' t/(2k)` against 5 % of the rise (`checks.thick_plate_bound`, `THICK_PLATE_LIMIT`) | own (L): 1D conduction through a plate with a linear profile; no source gives the 5 % | the warning itself; it bounds only the gradient, not the film on the node (2.2) | papers: surface centroid or source mean; program: node (column mean, film on the node) | no published case (T2 to T4 proposed); `test_thick_plate.py` checks the program's own 3D solid | **holds with the fix** (P1); the threshold is a choice |
| F-018 | block layer `S = k t c`, `C = ρc t A c`, contact `c A [f/R'' + (1−f)/(R''+r_half)]`, `h_exp = h_face r_fin + h_extra`, `h_wall = h_face + h_extra` (`blocks.extra_layers`) | own (L) | isothermal through the block thickness; thick blocks only through the warning; cover sampled 4 × 4 (P2) | node mean | Seri Lee now run (T1 proposed) | **holds** (Lee within 0.2 % of the exact plate); P2 |
| F-019 | `r_fin = (1 − t_f/p) + 2 H_c η/p`, `η = tanh(m H_c)/(m H_c)`, `m = √(2h/(k t_f))`, `H_c = H_f + t_f/2` (`blocks.fin_ratio`) | efficiency `tanh(mL)/(mL)` for an insulated tip: Lienhard eq. 4.53, printed p 174 (R, image); `m² = hP/(kA)` = `2h/(k t_f)` for a thin plate fin; the corrected length `H + t/2` is not printed on those pages (M, Incropera) | thin fins, one `h` on every face; close fins warned (F-020) | fin efficiency / exposed coefficient | own 2D fin (24 cases within 0.08 %), not in the battery | **holds**; the bibliography of `IncroperaDeWitt` for the efficiency can move to [Lienhard2024] (R) |
| F-020 | `Ra_b = g β θ b⁴ Pr/(ν² L)`, warn below 90 | Teertstra review eq. 3 and eq. 21 (PDF p 5, verified): `[(C/Ra_b)² + (0.59 Ra_b^(1/4))^(-2)]^(-1/2)`, C 24 symmetric | vertical isothermal channels; applied to every finned block, also horizontal; `β = 1/T_film` against `1/T_0` (5 %) | channel mean Nu / kept fraction | no | **holds** (the threshold is `phi` 0.9 by construction) |
| F-021 | `phi = [1 + (14.16/Ra_b^(3/4))²]^(-1/2)` | own algebra: `(0.59 × 24) Ra_b^(-3/4)` = 14.16, checked | `Ra_b > 14` | — | no | **holds** |
| F-022 | Schur complement `B = D − D (K_b + D_amb + D)^{-1} D` | static condensation (S) | steady only (transients refuse a block) | tile means | 74 cases against the FVM (not in the battery) | **holds** (exact algebra; Lumped +1.6 to +2.5 %, Analytic +0.2 to +0.3 % on the finned block) |
| F-023 | 3D solid against Yovanovich 2003 Table 3 | Table 3 μ 0 (PDF p 6, checked on the image here; 'machine' in the status file) | square block of the same area | mean source temperature | yes (`test_solid3d_verification.py`, passed) | **holds** |
| F-024 | GCI (Celik 2008) | verified pages | monotone convergence | — | yes | **holds** |

## 6. What could not be checked

* Churchill (1977) and Lloyd and Moran (1974) are not in the library: the mixed blend and the up-face law stay on memory and summaries.
* The equations of the Seri Lee article (images on the web page); its worked numbers were read.
* The 3D solid on case 1 (b) (estimate 8.1 GB, above the 3 GB of this review) and the finite-element re-runs of T-164 and RA-306 (assignment A2).
* The film term of a metal block (`blocks.extra_layers` puts the film on the block node without half the block) was not measured; the Lee plate is thin (`h t/(2k)` 3e-4).
* The 74 block cases of `research/block-and-fins` were not re-run (the finned-block table and the Lee plate were).

## 7. Verdict

**GO for the trust level of this group, on two conditions**: `fix/thick-plate-warning-bound` is merged (it turns the warning into a bound on every published plate and the column, verified here), and the published cases T1 to T4 enter the battery. No formula of the group was found coded differently from its source; what was wrong was the documents (the program's plate model credited with a re-implementation's numbers, published plates quoted without the program's own lower readings, stale via-array and model-comparison numbers, two wrong explanations of constants), all corrected here with the numbers printed by the runs above.
