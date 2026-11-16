# Final review of 2.8.0, part 1b: `docs/theory.md` 5 to 8 against the code

Scope: `docs/theory.md` chapters 5 (Lumped), 6 (Analytic), 7 (metal blocks) and 8 (heat transfer coefficients), read statement by statement against `pcbthermal/lumped.py`, `viaconstriction.py`, `analytic.py`, `analytic_local.py`, `blocks.py`, `convection.py`, `api.py` (`_solve_computed_h`, `calibrate_convection`), `analysis.heater_stats` and the warnings of `checks.py` that these chapters quote; `docs/models.md` 2.3, 2.4, 2.6, 4, 4b and 5 where they repeat the same numbers. Program: `development` da16d80f (2.7.1 plus the merged 2.8.0 branches, the film term `fix/face-film-half-slab`, the turbulent face-up branch `fix/horizontal-face-laws`, the images of the sides `fix/lumped-edge-first-link`, the exact block cover `fix/block-exact-cover`). Branch `docs/final-review-1b`: documents only; nothing in `pcbthermal/` or `tests/` was edited. Inputs: `releases/2.8.0/audit/` (`REVIEW_A1`, `REVIEW_A4`, `REVIEW_L1L5`, `REVIEW_L4L9`, `REVIEW_L12`, `DECISIONS`, `DECISIONS_2`, `DECISIONS_3`, `CLAIMS_REGISTER`).

**Verdict.** The four chapters describe the code as it is: every formula, constant and threshold checked below is the one in the code (no formula mismatch found). What was wrong were **numbers left from earlier trees** (the Analytic per-layer edge and transient ranges, the Lumped near-edge sentence of the first-ring paragraph, the Seri Lee digits after the film term, one radiation number) and **statements that were not explicit** (the floors and guards of the code, the film term in the Analytic surface coefficient and in the hidden face of a block, what the computed-`h` loop reads, the independent number of the Analytic edge limit). All of them are corrected in `docs/theory.md` and `docs/models.md` on this branch. Ready to merge as a documents branch; the items of section 3 are for later branches (none moves a frozen number).

## 1. Section by section

Re-runs (all on this tree, light, one at a time, the heavy lock taken for the three runs above 30 s):

| run | command | printed |
| :-- | :-- | :-- |
| R1 | `releases/2.8.0/final-review/scripts/study_final_1b_checks.py` (new, a few seconds) | closed forms of the Lumped, ring-1 subsampling, the corner row of validation 2, `h_r`, computed face coefficients |
| R2 | `research/analytic-edge-and-transient/scripts/study_perlayer_edge.py --part 2` (28 s, 0.88 GB) | 48 boards of two or more layers: −4.91 to −0.01 % of the shipped FVM, mean of the magnitudes 1.19 %; one layer, corner, 200 W/m²K −7.83 % |
| R3 | `releases/2.8.0/audit/scripts/study_a4_uniform.py` (28 s with the stored 3D runs, 0.84 GB) | Analytic at `h_side` 10: within 1.04 % (FVM) / 1.40 % (3D); at 200: −0.84 to −11.40 % (FVM), −2.64 to −14.89 % (3D); Lumped 0.5 mm against the FVM: centre −5.40 to +0.92, side −6.43 to +0.11, corner −7.97 to +1.20 % |
| R4 | `releases/2.8.0/audit/scripts/study_a4_local_transient.py` (38 s, 1.57 GB) | Analytic time to 63 % −9.1 to +3.2 % of the FVM at 0.5 mm (FVM 11.21 / 11.22 s at 0.5 / 0.25 mm on the 4 L board); Lumped −42.5 to +8.6 % |
| R5 | `releases/2.8.0/audit/scripts/study_lee_blocks.py fvm,fdm 0.5` (7 s, 1.0 GB) | Seri Lee `Rc` FVM 0.6637 / 1.2796 / 2.2691, FDM 0.6650 / 1.2798 / 2.2680 K/W |

| section | statement | verdict | evidence (code, number) |
| :-- | :-- | :-- | :-- |
| 5, eq. 5.1 | first ring `E₁ = min(max(1.5 Δ, 0.04 E_max), max(1.5 Δ, a_eq), 0.5 E_max)`, merge below one cell | matches | `lumped.ring_edges`, `_equivalent_radius` (term by term, as `REVIEW_A4` F-058) |
| 5, eq. 5.2 to 5.5 | strip links, log potential, 0.447, blocks above 900 cells, nine lowest blocks, Bessel factors, three passes, peak | matches; **corrected** (not explicit): the floor `max(φ_b − φ̄, 10⁻³)` and the replacement of the half ring by the image term are now stated at eq. 5.3 (A4 item D1) | `_footprint_potentials`, `_footprint_potentials_blocks`, `_interior_factors`, `_one_node_network`; R1: `f_R` 0.99627 / 0.96077 / 0.65805, `f_P` 0.99255 / 0.92235 / 0.39754 at x = 0.3 / 1 / 4 (the radial finite-volume values of `REVIEW_A4` 2); Maxwell 0.447049 |
| 5, first-ring limits | 'a source near a board edge or corner reads too cool (−10 / −17 %, up to −22 / −26 %)' | **corrected**: those are the numbers before the images of the sides; now −2.7 % on the flagged parts; the 1 mm part and aspect-3 numbers of the paragraph are said to predate the images (+3.8 points in the interior, validation 53.4) | `validation.md` 53.1, 53.4; `checks.check_lumped_near_edge` text quotes the new level |
| 5, near a side | images in the four sides and four corners, weight 1, 3600-cell limit, ring-1 sources ≤ 900, floor a tenth of the half ring; −2.7 % flagged, 3D −3.1 … / −3.3 …, +3.8 points interior, the 30.0 / 30.1 mm jump | matches; **corrected**: cross-reference 'section 5.1' → eq. 5.3; **added**: the ring-1 subsampling is every k-th cell, within 0.03 % of the full sum (R1: −0.000 / −0.007 / −0.029 % at 900 / 1600 / 3481 cells) | `_footprint_potentials_images`, `_ring1_potential`, `IMAGE_MAX_CELLS` 3600, `RING1_SOURCES` 900 |
| 5, part read-out | part rows read `max(heater_peak, drawn field)` | matches | `analysis.heater_stats` lines 233 to 237, `lumped.solve_steady` `part_peak` |
| 5.1 | wells (5.6), `R_c`, `r_cl`, `R_macro` capped at `0.75 λ_l`, grouping, Kron | matches | `viaconstriction.ring_couplings`, `MACRO_CAP` 0.75 |
| 5.1, limits | 'a board corner' among the cases where the rings fail | **corrected**: much reduced by the images (−3.3 % at a corner gap of zero against the 3D solver, 5 to 7 % cool at 2 to 5 mm) | `validation.md` 53.3 |
| 5.2 | `CORE_R` 0.7071, `MAX_CORE` 0.92 on both grids, `FINE_MM` 0.1, 700-cell blocks, 0.5 mm raster, (5.7) to (5.9), the three peak candidates | matches | `_core_mask`, `_fine_core_share`, `_zone_network`, `_ZonePeak`; R1: annulus 2.890542 K/W at 0.2 / 2 mm, limit `1/(8πS)` exactly |
| 5.2, small part | half the side, floor 0.125 mm, 1.7 KB per cell scaled above four layers, min(1 GB, guard) | matches | `small_part_cell`, `SMALL_PART_*` |
| 6, eq. 6.0 to 6.2 | Robin basis, roots, norms, `β`, `h_eff` on the real perimeter | matches | `_EdgeBasis`, `_effective_sheet` (`beta`, `h_eff`) |
| 6, `h_l` | surface coefficient of the layer | **corrected** (not explicit): it is the film through the half copper layer (`h_top_eff`, `h_bottom_eff`, `Board.face_film_h` on the influence-weighted fill) | `analytic._effective_sheet` lines 398 to 402 |
| 6, influence weighting | `λ_l = √(S_l/(h_surface + n g))`, spread > 0.25 | **corrected** (not explicit): `h_surface` includes the edge term `h_side P s_l/(W H)`, `S_l` is at the plain mean fill, the other layers take the stack length, and the trigger is the larger of the spread at `λ_l` and at the full-copper fin length | `_effective_sheet` lines 366 to 395 |
| 6, eq. 6.3, 6.4 | tiles `min(max(λ/4, 2.5 mm), 5 mm)`, 64 modes, GMRES rtol 1e-6, restart 30, mismatch 1e-9 | matches | `analytic.py` 316, 710, `EDGE_GMRES_*`, `EDGE_MISMATCH_MIN` |
| 6, transient | `K` 16, `K² N_L ≤ 3000`, Brent on `ln s` in [0.05, 20], readout tolerance 0.25 % | matches | `LOCAL_MODES`, `LOCAL_MAX_UNKNOWNS`, `analytic_local.FACTOR_BRACKET`, `READOUT_TOLERANCE`, `_readout_point` |
| 6, transient limit | '−8.1 to +0.5 % on 12 boards', then two italic notes ('−9.1 to +3.2 … supersedes the range of the next sentence', '−9.1 to +0.6 % on 2.7.1') | **corrected**: one statement, −9.1 to +3.2 % at the default 1 mm cell (R4), −8.3 to +2.1 % at 0.5 mm (validation 52.2), the independent finite-element numbers and the first-seconds limit; the wrong pointer 'DECISIONS_2.md 10' replaced (the fact is in its preface and decision 24); the warning key '−9 % to +3 %' agrees | R4; `analytic.HEATSINK_TRANSIENT_KEY` |
| 6, per-layer edge limit | '−4.1 to +0.1 % of the FVM on 48 boards', one layer '−7.3 %' | **corrected**: −4.91 to −0.01 % (mean 1.19 %) of the shipped FVM, one layer −7.83 % (R2); the old numbers were against the FVM of 2.5.x (`tests/test_analytic_perlayer.py` comment: the edge treatment of 2.6.0 reads these boards about 0.8 % hotter) | R2 |
| 6, edge limit | only the converged-3D numbers of validation 36.3 | **added** (decision 15 of `DECISIONS_2`: the independent number first): the 45 uniform boards at both references (R3) and that the 0.117 / 0.324 % of validation 4.1 are against an FVM without the band | R3 |
| 6.1 | tile `min(1 mm, 0.75 median d_nn)`, floor 0.25 mm, 4800 / 1200 guards, isolation 0.7, guard 0.5, self-terms | matches | `viaconstriction` constants, `add_self_terms` (the `n ≤ 1` term is floored at zero, harmless) |
| 6.1, limits | 'the per-heater scale of the transient is fitted against the program's own FVM' | **corrected**: stale (2.5.x); the factor `s` is found on each run against the Analytic's own steady solve | `analytic._local_dynamics` |
| 7.1 | the block table (7.1), exact cover, `c/b`, isolated `10⁻⁹ W/K` | matches; **added**: `R''` floored at 10⁻⁷ m²K/W, `r_half` is half the slab of the board node over the conductivity of its own gap | `blocks.extra_layers`, `ISOLATED` |
| 7.1, figure 41 | the network formula of the figure | **item** (figure stale): it shows `G = c A [f/R'' + (1−f)/(R'' + r_half)]` and `h_exp A c`, without the half block and half copper of the film term; caption now says so; face factor `1 − c/b` added | image looked at |
| 7.2 | fin ratio (7.2), sides without the ratio | matches | `blocks.fin_ratio`, `wall_h` |
| 7.3 | Lumped block layer, Analytic Schur complement (7.3) | matches; **corrected** (not explicit): the hidden face is `−h_face,eff A c` with the film through the half copper layer | `analytic.py` 505 to 512 |
| 7.4 | `Ra_b` (7.4), threshold 90, bound below 14, (7.5) | matches | `checks.FIN_CHANNEL_RA_LIMIT`, `FIN_CHANNEL_RA_BOUND`, the `14.16 = 24 × 0.59` of `checks.py` 1395; φ(90) = 0.900 |
| 7.5 | (7.6), 5 % threshold, the film term now in the model, Muzychka cases measured before it | matches | `checks.THICK_PLATE_LIMIT`, `thick_plate_bound` |
| 7.5, Seri Lee | FVM 2.2690, FDM 1.2797 / 2.2679 | **corrected** to the re-run on this tree (the film term moved the last digit): FVM 0.6637 / 1.2796 / 2.2691, FDM 0.6650 / 1.2798 / 2.2680; the reading status made explicit (R for eqs 1, 2 and the worked example from the web page, not in the papers library; N for the correction-factor figure; `BIBLIOGRAPHY.md` and `SOURCE_MAP_AUDIT.md` give R and S respectively) | R5 |
| 8, air, `Ra`, lengths | Sutherland fits, `β = 1/T_film`, `ΔT ≥ 10⁻³`, `A/P` of the outline | matches | `convection.air_properties`, `rayleigh`, `board_h` |
| 8, new-board coefficients | 10 / 15 / 10, computed 12.1 / 9.3 … 15.5 / 11.3 W/m²K | matches | R1 (all nine pairs of the three board sizes reproduced) |
| 8, table of deviations | face up / Raithby-Hollands −13.6 / +8.8 / +19.6 / +22.1 % at 10² / 10⁴ / 10⁶ / 10⁷; Fujii-Imura +8.1 % | matches (recomputed) | closed forms at `Pr` 0.71 |
| 8, face up turbulent | `0.14 Ra^{1/3}(1+0.0107 Pr)/(1+0.01 Pr)` above 10⁷, step 30.37 → 30.18 | matches; the 'Planned change' is now implemented text (done by `fix/horizontal-face-laws`) | `UP_LIMIT`, `TURBULENT_UP_*`; recomputed 30.366 → 30.177 |
| 8, face down, vertical, forced, mixed | 0.475 / 0.2, 8.13a/b, 0.664 and the 5·10⁵ branch, `p` = 3 | matches | `convection.py` |
| 8, radiation | '`h_r` 5.7 to 7.6 W/m²K at a 10 to 80 K rise' | **corrected**: 5.7 to 8.0 (7.6 is the value at 70 K) | R1: 5.69 / 7.63 / 8.00 at 10 / 70 / 80 K |
| 8, warnings | top `Ra` 10² to 10⁷, bottom 10² to 10⁹, `Re` 10² to 10⁵, laminar above 10⁹, low `Ra` 10³ (vertical), not settled in 30 | matches | `api._solve_computed_h`, `checks.check_low_rayleigh` |
| 8, the loop | 'the face temperature is the node temperature (the half copper layer between node and face is not counted)' | **corrected**: ambiguous since the film term; now: the film passes the half copper layer, but the laws read the node (decision 8 (ii)); the calibration range 0.1 to 10, 40 halvings and the refusal are stated | `api._solve_computed_h`, `_calibrate_convection` |

`docs/models.md`, the same corrections where it repeats them: 2.3 (the first-ring numbers predate the images; the corner row: −5.4 % against the FVM at 1 mm since the images, −8.7 % before, R1), 2.4 (0.12 / 0.32 % against an FVM without the band; the shipped-FVM and 3D numbers; −4.91 to −0.01 %), 2.6 (the contact and exposed film with the half block and half copper), 4 item 5 (−9.1 to +3.2 %), 5 (the forced branch above 5·10⁵ is the transition form, not 'mixed'; 3 to 6 solves, at most 30).

## 2. Cross-references and sources

Every image path of chapters 5 to 8 exists in `docs/images`, every `research/<topic>` folder named exists, every source key resolves in `research/theory/BIBLIOGRAPHY.md`, and every `validation.md` section quoted (3, 4.1, 7, 8, 13, 17, 18.1, 18.2, 21, 22, 22.1, 24, 31, 35 to 35.3, 36.3, 42.3, 42.6, 48, 50, 52, 53, 53.4, 54, 55) exists (scripted check of this review). Reading statuses quoted in the chapters agree with the bibliography, except the Seri Lee article, whose status is now written out (section 1). Not in the papers library and so not checkable from the source (as `REVIEW_A4` 9 says): Carslaw and Jaeger (images, the disc, the odd eigenfunctions; M), Maxwell (0.447; M, checked by its closed form), Krogh (own derivations, checked numerically), Seri Lee as a PDF.

## 3. Items (not edited here)

| item | kind | change | frozen-number risk |
| :-- | :-- | :-- | :-- |
| F1 | stale document | `docs/validation.md` 2 and 2.1: the Lumped column predates `fix/lumped-edge-first-link` (reference board, heater in the corner: −5.4 % now against −8.7 % printed; centred +1.0 % against −0.7 %; R1). Re-run `research/models-comparison/scripts/validation_study.py` (peak 8.3 GB, alone under the lock) | none |
| F2 | stale figure | `docs/images/fig_41_block_section.png` (drawn in `research/theory`): the contact `G` and the exposed film without the half block and half copper of `fix/face-film-half-slab`; redraw | none |
| F3 | warning text | `checks.check_reduced_edge_laminate` quotes only the FVM numbers (−3 to −13 %); decision 15 of `DECISIONS_2` asks the independent number first: '−2.6 to −14.9 % of the rise against an independent 3D solver at 200 W/m²K, within 1.4 % at 10 W/m²K' (R3); with `tests/test_warning_texts_plain.py` and the help | none |
| F4 | test docstring | `tests/test_analytic_perlayer.py` 121: '−4.07 to +0.06 %' and 'within 4.5 %' while the assertion is −5.5 % and the measurement −4.91 % (R2; `REVIEW_A4` T5, still open) | none |
| F5 | stale document | `docs/validation.md` 4.1 states −4.07 to +0.06 % for the 48 boards with no note of the −4.91 % on the shipped FVM (`REVIEW_A4` promised the note for VA-035; absent) | none |
| F6 | study | the hot cases of aspect ratio 3 (+9 to +12 %) and the 1 mm part of `validation.md` 31 were measured before the images of the sides; re-measure them on this tree (light, Lumped and FVM at 0.5 mm) | none (a study; a model change would move Lumped records) |
| F7 | warning wording | `api._solve_computed_h`: the bottom-face warning calls the face 'turned down' and quotes the face-down band also for a board colder than the air, where the face-up law is used (rare; a cold board) | none |
| F8 | model (decided, stated limit) | the laminate edge film on the copper node in the Analytic and the Lumped (−11.4 % / −14.9 %, decision 15 of `DECISIONS_2`): `research/reduced-models-edge-laminate` before any fix | high if ever implemented (every Analytic and Lumped record with `h_side`) |

No mismatch between a formula of these chapters and the code was found, so no item changes the program's physics.

## 4. Trust level of each chapter

| chapter | trust | reasons |
| :-- | :-- | :-- |
| 5 Lumped | **medium** | every closed form re-derived and checked numerically (`REVIEW_A4` 2, R1), and the text now matches the code; but the constants (ring edges, the cap, `CORE_R`, 92 %, the images) are fitted against the program's own FVM, the independent checks are one resolved via cluster and the near-edge 3D table, and several accuracy numbers of the chapter predate the images of the sides (F1, F6); interior parts read +3.8 points hotter since the images (safe side) |
| 6 Analytic | **high (steady), medium (transient)** | the series and the per-layer edge are exact for the layered idealisation (checked against an independent 2D solver and a published case); the remaining errors are stated with both references (cool by up to 11.4 % / 14.9 % at a strong edge, warned). The transient is −9.1 to +3.2 % against a converged FVM and +1 to +4 % against finite elements on five boards only, with the first-seconds limit of every layered model |
| 7 Metal blocks | **high** | the table (7.1) is the code term by term; Seri Lee's plate reproduced within 0.2 % of the exact series in the FVM and FDM on this tree (R5); fin warning and thick-plate bound match; the figure is stale (F2) |
| 8 Heat transfer | **high for the coding, low for the absolute h** | every law is coded as printed (or as its reprint), the examples and the deviation table reproduce, the warning bands match; but no coefficient has been compared with a measured copper board and the horizontal laws scatter by ±50 % (stated in the chapter) |

## 5. What was not verified

* The 3D solid column of the Seri Lee plate (not re-run; the film term does not change the 3D solid, which always had the half slab).
* The finite-element transient numbers (read from `research/transient-reference-boards`, not re-run).
* The default-coefficient comparisons of theory 8 (the swap 15 / 10 on the example board −0.7 %, the hot plates +7.2 / +8.8 %) and the effect table on the 17 harness boards (`DECISIONS_3`): not re-run here; the laws themselves were recomputed.
* `validation.md` 2 and 2.1 as a whole (F1): only the two reference-board rows of the Lumped were re-run.
* The zone constants against an independent reference beyond the one resolved cluster of `REVIEW_A3`; the 29 + 17 via boards of validation 18.1 (no committed script).
