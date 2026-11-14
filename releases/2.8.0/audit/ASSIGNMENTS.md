# The re-review split into reviewer assignments (2.8.0 audit, step 2 plan)

Two tracks: the **document track** (A1 to A6: the claims of the documents against the numbers) and the **literature-to-code track** (L1 to L12: each formula, constant and correlation of the program against the printed page of its source). The order of the two together is in the last section.

Input: [`CLAIMS_REGISTER.md`](CLAIMS_REGISTER.md) and [`claims.csv`](claims.csv), whose last column `assignment` gives each of the 1482 rows to one assignment below (filter on it for the full list). The risk 3 ids of each assignment are listed here; the numbers in brackets are the items of the top 40 (register section 2).

**Rules for every assignment.** Read the code against `docs/theory.md` before the numbers. Re-run, do not trust: every number kept in a document must be printed by a script of the repository. For every comparison fix on both sides the quantity (point maximum, footprint mean, centroid, node, face, thickness mean) and check that both sides model the same board (copper conductivity, films and where they act, edge losses, laminate anisotropy and in-plane conductivity). A reference is called converged only with its own refinement series shown. A test of a known limit is one-sided. Corrections of the program are measured on a copy and written up for a `fix/` branch; documents and research folders are corrected on the branch of the assignment. One heavy job at a time, at most two reviewers at once, the load rules of `CLAUDE.md`.

**Order.** A1 and A3 first (light, can run together), then A2 (the heaviest, finite elements) with A4, then A5, then A6 last, because A6 makes the program texts quote the numbers that A1 to A5 settle.

## A1. Thick plates, published cases, convection, metal blocks

- **Scope**: theory 7 (blocks, thick plates, 7.5), 8 (convection), 11 (the table of checks) and the sources table; validation 5, 8, 10, 11, 15 to 17, 20, 22, 22.1; research `effective-conductivity`, `theory-sources`, `published-cases-followup`, `paper-case-studies`, `solid3d-verification`, `block-and-fins`, `block-warning-remeasure`, `component-heatsink`, `convection-laws`, `face-down-convection`, `horizontal-plate-h`, `plate-h-level`, `fin-channel`, `fin-channel-sources`, `bochkov-robin-check`, `market-fem-comparison`, `theory` (bibliography statuses). 304 rows.
- **Risk 3** (24): T-128, T-131, T-144, T-164, T-165, VA-124, VA-149, VA-156, RA-018, RA-055, RA-103, RA-114, RA-140, RA-149, RA-151, RA-306, RA-341, RA-342, RA-346, RA-347, RA-366, RA-522, RA-562, RA-596 (top 40: 1, 2, 3, 16, 30, 31).
- **Code**: `blocks.py`, `checks.check_thick_plates` (and how `q''` is taken: copper layer, block, the auxiliary run), `convection.py`, `solid3d.py`, `research/effective-conductivity/lib/layered3d.py`.
- **Re-run**: `research/theory-sources/scripts/study_muzychka_more_cases.py` (cases 1 (b) and 2) and the cross and case 1 (a) of `effective-conductivity`; separate on case 2 the through-thickness gradient from the film acting on the node (program node against the 3D thickness mean, then the surface, with and without the film in series with half the plate); the thick-plate warning on the five Muzychka cases and on a sweep of plate thickness and conductivity (decide the 5 % threshold on the measured shortfall); the program's `blocks.py` on Seri Lee's plate (never done); the coupon of `published-cases-followup`; `tests/test_solid3d_verification.py`.
- **Deliverables**: corrected texts of validation 20, 22, 22.1 and theory 7.5 and 11; a proposal (`INTEGRATION.md` of the folder) for regression tests of the published cases (the five Muzychka cases, Seri Lee with the block, Table 2 of Yovanovich-Muzychka-Culham, Lemczyk), each with the program's error as a one-sided bound; a proposal for the warning threshold.
- **Cost**: light to moderate: the plates are single-layer boards (case 1 (a) is 300 mm at 2.5 mm cells, case 2 is 50 mm at 0.5 to 1 mm); the independent solver with 32 sub-slabs on case 2 is the largest run (under 2 GB expected); about one reviewer-day.

## A2. Edge, laminate, outline and the finite-element references

- **Scope**: theory 1.1 to 1.4, 2 (except 2.6), 3, 4; validation 3, 3.1, 12, 14, 21 to 21.3, 23, 23.1, 32, 33, 36, 38 to 41, 43, 44, 46, 47; research `independent-fem-edge`, `independent-fem-extensions`, `strong-edge-laminate`, `laminate-nodes`, `laminate-slabs-and-local-rule`, `laminate-edge-band`, `gap-subdivision`, `cut-cell-links`, `outline`, `rotated-square-3d`, `imported-copper-edge-film`, `fdm-inset-edge`, `bare-spot-under-source`, `stackup`. 339 rows.
- **Risk 3** (41): T-014, T-015, T-020, T-021, T-023, T-054, T-084, T-090, VA-020, VA-025, VA-027, VA-076, VA-077, VA-078, VA-128, VA-132, VA-134, VA-143, VB-003, VB-007, VB-116, VB-128, VB-134, VB-138, VB-143, VB-160, RB-003, RB-007, RB-012, RB-038, RB-056, RB-060, RB-074, RB-081, RB-088, RB-099, RB-100, RB-101, RB-115, RB-142, RCB-071 (top 40: 4, 12, 13, 16, 17, 18, 25, 26, 27, 28, 29, 39).
- **Code**: `fvm.py` (cut cells, `_cut_edge_film`), `fdm.py` (faces, `face_fill`), `laminate.py` (`plan_gaps`, `edge_band`, `face_terms`), `solid3d.py` (slab rule, apertures), `geometry.py` (`exact_coverage`, `face_apertures`), the finite-element tool of `research/independent-fem-edge/lib`.
- **Re-run**: one set of edge-band numbers against the finite elements with the quantity fixed (point maximum or cell mean); the tables of validation 28, 36.3, 44 and `strong-edge-laminate` 8.2 to 8.4 against the finite elements instead of the cell-centred reference; validation 3 and 3.1 with the slab rule of 2.6.0 (already a 'Planned' item); validation 13, 21, 23 rows that used the program's 3D solid (before the sliver fix) against `layered3d` or the finite elements; validation 21.2 3.2 mm row against the converged reference; the small-part tables of theory 1.4 and validation 21.3 with the observed order of convergence and the quantity defined (these set the 0.10 and 0.15 thresholds of the laminate warning); the strips row of 41 (write the script or withdraw it).
- **Deliverables**: corrected validation sections, theory 1.4 and 2.2 (the partial-copper numbers go to A3), research READMEs and their review chapters; the list of tables to mark superseded.
- **Cost**: the heaviest: finite-element runs need the folder's scratch environment and several GB each (the declared peaks of `independent-fem-edge`); run in series on a quiet machine; two to three reviewer-days.

## A3. Vias

- **Scope**: theory 1.5, 2.6, 5.1 and 6.1 (via parts); validation 18, 18.1, 28, 30, 34, 45, 49 and the via rows of 24 and 25; research `via-partial-copper`, `via-contact-geometry`, `via-edge-image`, `via-well-sheet-order`, `imported-via-rim`, `via-fill`, `via-real-board`, `point-via-convergence`, `sor-with-via-couplings`, `young-omega-tiles`, `lumped-analytic-vias`. 170 rows.
- **Risk 3** (19): T-066, VA-105, VA-111, VA-113, VB-055, VB-057, VB-058, VB-073, RCA-032, RCA-037, RCA-041, RCC-082, RCD-002, RCD-003, RCD-004, RCD-008, RCD-016, RCD-020, RCD-042 (top 40: 5, 19, 20, 21, 38).
- **Code**: `viawell.py` (barrel length, rim shares, Peaceman well, Kron reduction, edge image), `viaconstriction.py`, `lumped.py` (via groups, zones), `analytic.py` (`_local_conductances`), the SOR block relaxation in `fvm.py`.
- **Re-run**: the partial-copper numbers of theory 2.2 and validation 30.1 against the resolved reference of `via-contact-geometry` (the pre-rim numbers are still quoted); the 29 + 17 via boards of validation 18.1 on the tree against a reference that resolves the barrel; the three 16 mm boards of 18.2 with the barrel resolved; the via near a strongly cooled edge (28, 49) against the finite elements; the Shen 2020 case (find the 21 % gap or say it is not reproduced); the Shen cell definitions (one value, like for like); the via-fill numbers of validation 18.
- **Deliverables**: corrected theory 2.2 and 2.6 numbers, validation 18, 28, 30, 34; the corrected rows of the via warnings handed to A6.
- **Cost**: moderate: the resolved via references are small 3D boxes (under 3 GB); one to two reviewer-days.

## A4. The Lumped and Analytic models and the transient

- **Scope**: theory 5, 6, 9; validation 1, 2, 2.1, 4, 4.1, 6, 7, 13, 31, 35, 42, 48, 50; research `lumped-zones-adoption`, `lumped-near-edge`, `lumped-dense-via-group`, `lumped-via-groups`, `lumped-ring-uniform-deficit`, `lumped-edge-link`, `lumped-zone-placement`, `analytic-partial-copper`, `analytic-edge-and-transient`, `analytic-edge-spatial`, `transient-reference-boards`, `models-comparison`. 260 rows.
- **Risk 3** (45): T-097, T-100, T-113, T-120, VA-006, VA-007, VA-035, VA-043, VA-048, VA-053, RB-152, RCA-001, RCA-004, RCA-005, RCA-006, RCA-009, RCA-011, RCA-019, RCA-024, RCA-025, RCA-029, RCA-046, RCA-048, RCA-050, RCA-051, RCB-005, RCB-011, RCB-014, RCB-018, RCB-025, RCB-028, RCB-044, RCB-053, RCB-059, RCB-064, RCC-002, RCC-008, RCC-021, RCC-023, RCC-025, RCC-028, RCC-030, RD-069, RD-070, RD-072 (top 40: 6, 8, 10, 14, 15, 22, 23, 24, 39).
- **Code**: `lumped.py` (first ring, zones, near-edge raster, part read-out), `analytic.py` (Robin basis, per-layer edge, `_local_dynamics` and the point it reads), `analytic_local.py`, `profiles.py`.
- **Re-run**: the accuracy figures that the warnings and the documents quote, against an independent reference and not only against the FVM they were fitted to (per-layer edge: 48 boards, quote 4.91 / 1.19 % or the new numbers; Robin edge 135 boards; first ring at one reference cell; near-edge table after the band; zones with the barrels resolved; the transient against the finite-element transient of `transient-reference-boards`, with the open defect of the point the Analytic transient reads stated); validation 2 and 2.1 regenerated with `validation_study.py`.
- **Deliverables**: corrected sections and folders; for each accuracy statement both numbers (against the FVM and against an independent reference) and which one the warning quotes.
- **Cost**: moderate: the program runs at 0.5 and 0.25 mm on boards up to 200 x 150 mm (watch the FVM reference memory at 0.25 mm), the transient references from the existing outputs where they are kept; two reviewer-days.

## A5. Imported copper, Gerber, the calculator and fast waves

- **Scope**: theory 1.6 to 1.8 and 10; validation 9, 19, 26, 27, 29, 37; `docs/calculators.md` and `help/calculator.html`; research `gerber-models`, `gerber-real-boards`, `gerber-import`, `gerber-cad-profiles`, `gerber-nets`, `reduced-models-imported-passives`, `power-calculator`, `zone-union`, `fast-wave-oscillation`, `small-model-defects`, `memory-guard`, `bom-role-and-close-hook`. 190 rows.
- **Risk 3** (23): VA-116, VB-053, H-044, C-003, C-010, C-011, C-012, C-014, RA-320, RA-323, RD-001, RD-012, RD-025, RD-026, RD-028, RD-032, RD-033, RD-039, RD-041, RD-063, RD-064, RD-086, RD-101 (top 40: 11, 36, 37).
- **Code**: `copper.py` (mappings, pixel rule, warnings), `gerber/parts.py` (heat-source shape), `inverse.py` (power band, sensitivities), `stackimpedance.py` and `profiles.decide`.
- **Re-run**: the Lumped and Analytic on imported copper against a converged reference (the FVM at 0.25 and 0.125 mm on windows, or the independent solver), and the reference uncertainty quoted once; the calculator datasheet rows and the sensitivities from `research/power-calculator/scripts/calculator_validation.py` and `tests/test_calculator_validation.py` (one table); the JEDEC case with the bottom copper read both ways; the fast-wave numbers against the closed form and the reference of the folder. Real boards are third-party: numbers only, on this machine (`pcb-library/`).
- **Deliverables**: corrected validation 19, 27, 29, 37, calculators.md, the research folders and their registers.
- **Cost**: moderate: the whole-board runs at 0.25 mm are the largest (declare the peak; the memory guard estimate first); one to two reviewer-days.

## A6. The program's texts and the tests that hold a defect (last)

- **Scope**: the warning texts (`checks.py`, `api.py`, `copper.py`, `analytic.py`, `lumped.py`, `profiles.py`), the user guide (limits tables), `docs/models.md`, validation 24 and 25 (the consolidated tables), the registers `research/README.md`, `REVIEW.md`, `ROADMAP.md`, and the tests `tests/test_layered_vs_3d.py` (one-layer pad windows and the model order), `tests/test_rect_board.py` (bands), `tests/test_analytic_perlayer.py` (floor and docstring). 219 rows.
- **Risk 3** (60): VA-148, VB-014, VB-017, VB-020, VB-022, VB-026, VB-033, VB-035, VB-038, VB-039, M-008, M-015, M-019, M-020, M-027, M-028, M-034, M-041, M-044, M-051, M-053, M-059, M-068, M-071, M-072, W-001, W-003, W-005, W-007, W-022, W-025, W-029, W-034, W-035, W-036, H-005, H-007, H-008, H-012, H-015, H-016, H-019, H-020, H-021, H-025, H-033, H-036, H-037, H-042, RA-014, RA-567, RCA-026, RCA-038, RCB-057, RCB-070, RCC-017, RCC-019, RCC-026, RD-019, RD-105 (top 40: 7, 9, 32, 33, 34, 35, 40).
- **Work**: give every number one home in `docs/validation.md` and make every warning, the guide and models.md cite it with the numbers that A1 to A5 settled; remove the numbers that no document holds (or find their study); refresh validation 24 and 25 (or reduce 25 to pointers); rewrite the three tests as one-sided bounds with the reason in the docstring. Text changes in `pcbthermal/` and `tests/` go on a `fix/` branch with the whole battery (tooltips, `tests/test_help.py`, `tests/test_warning_texts_plain.py`).
- **Cost**: light in computation (the warning rates are re-derived from the outputs of A1 to A5), heavy in reading; one to two reviewer-days, then the maintainer's whole battery.

## The literature-to-code track (L1 to L12)

**Why a second track.** The image verification of the transcriptions found no error in a formula that the program uses. That checks the page, not the program: it does not show that the code implements the printed formula (symbols, exponents, constants, units: the 0.742 of eq. 18 against the 0.664 of eq. 12 of Yovanovich and Teertstra 2001 is the example), that the program applies it inside the range the paper states, or that the quantity the paper reports (surface, centroid, mean over the source, average Nusselt number over the plate) is the one the program compares (the thick-plate case 2 of Muzychka et al. 2003 is the example: the paper reports the surface, the program a node that is the mean through the thickness with the film acting on it).

**Inventory**: [`formulas.csv`](formulas.csv), 100 rows, one per formula, constant or correlation of `convection.py`, `laminate.py`, `viawell.py`, `viaconstriction.py`, `lumped.py`, `analytic.py`, `analytic_local.py`, `blocks.py`, `stackimpedance.py`, `profiles.py`, `memory.py`, `checks.py`, `inverse.py`, `fvm.py`, `fdm.py`, `solid3d.py`, `geometry.py`, `api.py` and the libraries of `data/defaults.json`. Columns: `fid`, `group`, `formula`, `code` (file:function, line), `models_using`, `source_key`, `status_theory` (status in the sources table of `theory.md`), `status_bib` (`research/theory/BIBLIOGRAPHY.md`), `eq_page`, `page_verified` (Y all cited pages verified against the image in `papers/ocr/reading_status.json`, read with `python -m tools.ocr status show <stem>`; P partly; N machine only or not in the file; NA no source), `validity_paper`, `range_program`, `warning_outside`, `published_case`, `case_in_battery`, `quantity_paper`, `quantity_program`, `known_issue`, `risk`, `risk_reason`. The scores are those of the inventory pass; the reviewer of each group confirms them.

**Counts.** 100 formulas in 12 groups; risk 3: 20, risk 2: 16, risk 1: 47, risk 0: 17. About 45 are the program's own derivations, fits or rules (the laminate sub-gap rule and edge band, the face term, the barrel extra length, the target radius `e^(-1/4)`, the rim ray, the Krogh closed form, the Lumped well, groups, zones, rings and first-ring cap, the Analytic tile self-term, per-layer edge, influence fill and local factor, the 0.25 floor of the cut-cell film, the 3D slab rule, the memory via gain, the fast-wave thresholds, the profile decision, the power band, the equal-area rectangle, the warning thresholds); for those the check is the derivation and an independent case, not a page. From memory with no recorded source: the 0.447 self-distance of a square, the emissivity 0.9, the FR-4 properties (0.3 / 0.9 W/mK, 1850 kg/m3, 900 J/kgK), the air-property fits.

**Sources whose cited pages are not verified** (or not in the status file): `Muzychka2004Orthotropic` (p 6 machine only, with an uncorrected error), `YovanovichJafarpur1993Bounds` (PDF pages 13, 14, 18 verified; their match with the printed pages 7, 8, 11 cited is not confirmed), `Yovanovich2003` (the Table 3 page not listed), `Ostrach1953` (Table I pages corrected; report page 77 not identified), `Lie2019Reservoir`, `Koch2019Well`; not in the file at all: `EC1998Spreading` (Seri Lee), `JohansenColella1998`, `BochkovGibou2019`, `BarrettEtAl2022`, `JESD15-3`, `George1973`, `Peaceman1978`, `GoldsteinLau1983`, `LloydMoran1974`, `IncroperaDeWitt`, `CarslawJaeger`, `ChurchillChu1975`, `ChurchillBlend`; the page of Lienhard Table A.1 (copper) is not identified.

**Published cases of a formula held by the battery**: Yovanovich 2003 Table 3 (`tests/test_solid3d_verification.py`), the Celik GCI procedure, the CSD17308Q3 and JEDEC 2s2p calculator cases (`tests/test_calculator_validation.py`), the Culham-Yovanovich coupon geometry against the independent solver (`tests/test_layered_vs_3d.py`), equation 21 of Muzychka Part II on the series basis (`tests/test_analytic_edge.py`), and the laminar natural-convection form against the similarity solution of Ostrach with LeFevre's Prandtl fit (`tests/test_natural_form.py`, a closed form, not the published table). Not held: Lienhard Examples 6.5 (forced, 21.39 against 21.4) and 8.1 (vertical plate, 4.233 against 4.22), the TI barrel example (261 C/W), Table 2 of Yovanovich-Muzychka-Culham 1999, Seri Lee, the Muzychka 2003 cases, Fish 2017, Shen 2020.

**The procedure, the same for every assignment** (one reviewer per group, 7 to 13 formulas): for each formula (1) open the verified page image (`papers/`, local, never committed) and write the formula as printed, with the equation number, the symbols and the units; a source not obtained or read from a summary is said so and the formula is checked as an assumption; (2) read the code at the line of the inventory and write the formula as coded; (a) compare them term by term (constants, exponents, the length or temperature they are taken at, units, which variant when the paper prints several); (b) compare the validity range the paper states with the range the program applies it in, and check that a warning exists outside it; (c) find the published numerical case, reproduce it with an independent script if it is not reproduced, run the program on it, and say whether a test of the battery holds it (propose the test when not); (d) compare the definition of the quantity the paper reports with the one the program reports or compares. Findings in the program are measured on a copy and written up for a `fix/` branch; findings in the documents are corrected on the branch of the assignment and fed to A6.

**Ranking** (the order below): first the formulas used by several models with a source of status S, M or N or pages not verified, no reproduced published case, or a quantity mismatch; then the own derivations used by every model; then data and numerics.

| # | Group (formulas) | Risk 3 | Main sources | Cost |
| :-- | :-- | :-- | :-- | :-- |
| L1 | natural convection (F-001 to F-008) | F-001, F-003, F-004, F-007 | Lienhard 2024, Yovanovich-Jafarpur 1993, Lloyd-Moran (not obtained), Goldstein-Lau (second hand), Churchill-Chu (not obtained), Ostrach 1953 | light (closed forms; Lienhard Example 8.1 as a test) |
| L2 | thick plate, blocks, fins (F-017 to F-024) | F-017, F-019 | Seri Lee (EC1998), Yovanovich-Culham-Teertstra 1998, Bar-Cohen-Rohsenow through Teertstra, Yovanovich 2003, Celik | light to moderate (the Muzychka cases with A1) |
| L3 | via barrel and well (F-025 to F-033) | F-027, F-029 | TI AN-2020, Shen-Wang 2019, Peaceman 1978 (abstract), Durlofsky 2005, Ibraguimov 2022, Yovanovich 1995 image method, Dorfler-Bullo | moderate (a resolved via box) |
| L4 | cut cells and geometry (F-066 to F-071) | F-066, F-067 | Johansen-Colella 1998, Bochkov-Gibou 2019, Barrett et al. 2022, Greiner-Hormann | light (the 2D Robin solver of `bochkov-robin-check`) |
| L5 | forced convection, radiation, air (F-009 to F-016) | F-009, F-011 | Lienhard 2024 (Example 6.5), Yovanovich-Teertstra 2001 (eq. 12 against 17 and 18), Churchill 1977 (not obtained), air tables | light |
| L6 | via constriction (F-034 to F-040) | F-034 | Krogh 1919 (memory), Dietz (summary), Fish 2017, Carslaw-Jaeger (memory) | light to moderate |
| L7 | laminate and layered stack (F-041 to F-049) | F-041 | Muzychka 2004 orthotropic (p 6 machine only), Patankar, own rules | moderate (the gap sweeps of `gap-subdivision`) |
| L8 | transient, profiles, stack impedance (F-079 to F-085) | F-081, F-082 | Carslaw-Jaeger (memory), Lienhard eq. 5.62, own | light (closed forms against the folder's reference) |
| L9 | Analytic series and edge (F-050 to F-057) | none (four at 2) | Yovanovich-Muzychka-Culham 1999 (Table 2), Culham Fourier 2000, Muzychka 2003 Part II, Muzychka 2006, Carslaw-Jaeger | light (series sums) |
| L10 | package and calculator (F-086 to F-094) | F-087, F-093, F-094 | JESD15-3, JESD51 (not obtained), ROHM 65AN114E, TI SPRA953B, vendor notes from summaries, catalogues | light (calculator cases) |
| L11 | Lumped network (F-058 to F-065) | none (one at 2) | Carslaw-Jaeger (memory), own | light |
| L12 | numerics, memory, materials data (F-072 to F-078, F-095 to F-100) | F-096 | Patankar, Saad 2003, SuperLU guide, Lipton-Rose-Tarjan, George 1973, Lienhard Table A.1, catalogues | light |

### Briefs (5 lines each)

**L1, natural convection** (first; 8 formulas, about one reviewer-day).
1. Write the face-up `0.54 Ra^(1/4)` / `0.15 Ra^(1/3)`, the face-down `0.475 Ra^(1/5)`, the Churchill-Chu general and laminar forms and `L = A/P` as printed in the pages the bibliography marks R, and as coded in `convection.py`.
2. The face-up law and Lloyd-Moran are not obtained: find an open copy or restate the law as an assumption; confirm the printed-page mapping of Yovanovich-Jafarpur 1993 for 0.475.
3. Compare each published range (face up 2.2e4 to 8e6, face down, Churchill-Chu) with the ranges of the warnings (1e4 to 1e11 top, 1e2 to 1e9 bottom), and `L = A/P` on concave outlines.
4. Turn Lienhard Example 8.1 into a battery test; check that the paper reports the average Nusselt number over an isothermal plate while the program applies it to the mean face temperature of a board with hot spots.
5. Output: a row per formula in the folder of the assignment, corrected theory 8, the warning ranges for A6, the proposed tests.

**L2, thick plate, blocks and fins** (second; 8 formulas, one day, with A1).
1. Write the bound `q'' t/(2k)` and its derivation, the fin efficiency `tanh(mH)/(mH)` and fin ratio, the close-fin channel `Ra_b` and the kept fraction, the block Schur complement, as coded in `checks.py`, `blocks.py`, `analytic.py`, `lumped.py`.
2. Compare with the spreading closed forms of Yovanovich-Culham-Teertstra 1998 and Seri Lee (EC1998, not in the status file: verify the page) and with Bar-Cohen-Rohsenow as printed in the Teertstra review.
3. Separate on the Muzychka 2003 cases the through-thickness gradient from the film acting on the node; check whether the 5 % threshold of the warning has any basis in the sources.
4. Run the program's `blocks.py` on Seri Lee's plate; propose Seri Lee and the Muzychka cases as battery tests.
5. Quantity: the papers report a centroid or a source-mean surface temperature; the program a node mean through the thickness; write which one each comparison uses.

**L3, via barrel and well** (third; 9 formulas, one to two days).
1. Write the barrel conductance with its length `d + 0.5 t_bar`, the Peaceman well `2 pi S / (ln(r_eff/r_t) + c)`, the lattice radius 0.1985 cells, the target `e^(-1/4) r_v`, the mirror image `c`, the Kron reduction, as coded in `viawell.py`.
2. TI AN-2020 (the 261 C/W example) covers only the pure-length barrel; Peaceman 1978 was seen as an abstract: open it or rest the well on Durlofsky 2005 eq. 34 (verified) and say so.
3. Check the ranges: the image only for straight sides at least six cells long, the well for a via within the footprint rule; warnings outside.
4. Reproduce the published cases (TI example, Shen-Wang 2019, the image method of Yovanovich 1995) and propose the TI example as a battery test; the target radius is an own derivation: check it against a resolved barrel.
5. Quantity: the barrel resistance of the sources is wall to wall; the program's well is reached through the mean temperature of a footprint: say what each comparison reads.

**L4, cut cells and geometry** (fourth; 6 formulas, half a day).
1. Write the aperture link `a S dy/dx` and the film in series `g0 / max(1 + g0 d/(S L), 0.25)` from Johansen-Colella 1998, Bochkov-Gibou 2019 eqs. 1.13 and 1.14 and Barrett et al. eqs. 12 to 14, and as coded in `fvm.py` and `solid3d.py`.
2. None of these three sources is in the OCR status file: verify the pages against the images first.
3. The floor 0.25 is the program's own: state where it binds (from about 1000 W/m2K with copper inset) and whether the papers have any bound.
4. Reproduce Johansen-Colella problem 1 (done in `rotated-square-3d` tests) and the Bochkov-Gibou order of accuracy with the 2D solver of `bochkov-robin-check`; propose one as a battery test.
5. Quantity: the papers measure the error of the field in a norm; the program reports the hottest cell: say which the validation sections compare.

**L5, forced convection, radiation and air** (fifth; 8 formulas, half a day).
1. Write `0.664 Re^(1/2) Pr^(1/3)`, the mixed laminar-turbulent form, the Churchill blend `(h_n^3 + h_f^3)^(1/3)`, the linearised radiation, the air-property fits, as printed and as coded in `convection.py`.
2. Settle the 0.742 (Yovanovich-Teertstra eq. 17 and 18) against 0.664 (their eq. 12): which one the program uses, which one applies to a heated board, and the 11 to 14 % between them.
3. Churchill 1977 is not obtained: restate the blend exponent 3 as an assumption, or find the paper; check the transition at Re 5e5 against the board sizes.
4. Turn Lienhard Example 6.5 (21.39 against 21.4) into a battery test; check the air properties against Lienhard's tables (verified pages) at three temperatures.
5. Quantity: the correlations give an average over an isothermal plate at the film temperature; the program applies them at the mean face temperature: write the consequence.

**L6, via constriction** (sixth; 7 formulas, one day).
1. Write the Krogh cell `R_K`, the ring well, the via groups, the Analytic tile self-term, the annulus link and the micro peak, as coded in `viaconstriction.py` and `lumped.py`.
2. Krogh 1919 is from memory and Dietz from a summary: derive `R_K` again from the log potential and compare term by term (the `- 1/4`).
3. The macro factor, the 0.75 fin-length cap, the core radius `0.7071 d_nn` and the group rule are own fits: state the range of the boards they were fitted on.
4. Reproduce Fish 2017 (1215.2 against 1240 K/W) in the program, not only in the study, and propose a closed-form test of `R_K`.
5. Quantity: the Krogh resistance is from the wall to the cell's outer mean; the Lumped ring is a ring mean: say what is compared.

**L7, laminate and the layered stack** (seventh; 9 formulas, one day).
1. Write the layer sheet `S = f k_cu t_cu + k_ip (slab - f t_cu)`, the gap conductance, the sub-gap rule, the edge band, the face term `Q t_cu/(2 k_z A)`, the harmonic face of the FDM and the 3D slab rule, as coded.
2. Muzychka 2004 orthotropic p 6 is machine-only with an uncorrected error: verify the page and the equations 39 and 40 before relying on them.
3. The sub-gap rule (0.4 mm, at most 4), the band margin and the slab rule are own: their error against the finite elements is A2's; here check the derivation and the ranges.
4. Reproduce eq. 50 of Muzychka-Yovanovich-Culham 2004 in the program (done in a research folder) and propose it as a battery test.
5. Quantity: the closed forms give a source-mean or centroid temperature on the surface; the program a node with the face term added: write which one each table uses.

**L8, transient, profiles and the stack impedance** (eighth; 7 formulas, half a day).
1. Write the slab quadrupole admittance, the disc-on-sheet `K1` term, the Lanczos harmonic sum, the superposition of delayed steps and the decision thresholds, as coded in `stackimpedance.py` and `profiles.py`.
2. Carslaw-Jaeger is from memory: derive the quadrupole and the disc term again (or open a verified transmission-line or Carslaw-Jaeger page) and compare term by term.
3. The 4 s / 2 s thresholds and the fill 0.9 are measured rules: state their range.
4. No published fast-wave case exists: check against the semi-infinite limit of Lienhard eq. 5.62 and the reference of `fast-wave-oscillation`.
5. Quantity: the swing of the closed form is at the heater face; the program's profile curves are node values plus the face term: say which.

**L9, the Analytic series and edge** (ninth; 8 formulas, half a day).
1. Write the compound-channel modal system, the Robin eigenfunctions `lambda tan = beta`, the per-layer edge mismatch, the influence fill with `K0`, the Woodbury correction, the propagator, as coded in `analytic.py` and `analytic_local.py`.
2. Compare with Yovanovich-Muzychka-Culham 1999 (Table 2, 33 of 36 cells reproduced; theory says 'to four digits'), Culham Fourier 2000 and Muzychka 2003 Part II eq. 12 to 21 (verified pages).
3. Range: the thin-sheet statement holds for `t/L <= 0.1`; check that a warning covers thicker cases.
4. Turn Table 2 of 1999 into a battery test; keep the equation 21 test.
5. Quantity: the papers give the resistance from the source mean; the program its hottest point: write the conversion.

**L10, package and calculator** (tenth; 9 formulas, half a day).
1. Write the two-resistor junction, the psi_JB ring (0.5 to 1.5 mm), the top of package with psi_JT, the power from temperature, the power band, the top-path split, as coded in `analysis.py`, `inverse.py`, `api.py`.
2. JESD15-3 and JESD51 were not obtained: say which definitions rest on vendor notes (ROHM 65AN114E, TI SPRA953B, verified) and which on memory.
3. The package theta and heatsink libraries rest on web summaries and catalogues: record the source of each entry or mark it 'typical, unsourced'.
4. Keep the CSD17308Q3 and JEDEC tests; add the psi_JB ring definition check against the vendor notes.
5. Quantity: psi_JB is defined at the board 1 mm from the package; the program's ring is a mean over 0.5 to 1.5 mm: state it.

**L11, the Lumped network** (eleventh; 8 formulas, half a day).
1. Write the ring edges and the first-ring cap, the lateral ring resistance, the footprint log potentials with the 0.447 self-distance, the Bessel factors, the peak, as coded in `lumped.py`.
2. The disc solutions are Carslaw-Jaeger from memory and the 0.447 has no recorded source: derive them again and check the Bessel factors against the closed form of a disc on a leaking sheet (Shen eq. 19, verified).
3. The rules (raster, near-edge gap, via-cool warning) are own: state their fitted range.
4. Propose a closed-form test of the disc factors.
5. Quantity: the ring is a mean, the part reading is the peak (validation 48): say which every Lumped comparison uses.

**L12, numerics, memory and the materials data** (last; 13 formulas, half a day).
1. Write the theta method, the Young optimum with the Rayleigh quotient, the SuperLU symmetric mode, the memory law and its via gain, as coded in `fvm.py` and `memory.py`.
2. Check Saad 2003 p 147 (not listed) and George 1973 (not in the status file) for the statements that rest on them.
3. Check every material constant of `data/defaults.json` against a verified page (Lienhard Table A.1 for copper: identify the page) or mark it 'typical, unsourced' (FR-4, emissivity 0.9).
4. No published case is needed for the numerics; the tests of the battery already hold the solver equivalence.
5. Quantity: none to compare; the output is the source of every constant.

## The order of the two tracks

At most two reviewers at once, one heavy job at a time. The literature groups that feed a document assignment go with it, so that the same reviewer reads the page and the claims that rest on it.

| Step | Reviewer 1 | Reviewer 2 |
| --: | :-- | :-- |
| 1 | A1 with L2 (thick plates, published cases) | L1 then L5 (convection) |
| 2 | A3 with L3 and L6 (vias) | L4 (cut cells), L9 (Analytic series) |
| 3 | A2 with L7 (edge, laminate; finite elements, heavy) | A4 with L11 (Lumped, Analytic, transient) |
| 4 | A5 with L10 and L8 (imported copper, calculator, fast waves) | L12 (numerics, data) |
| 5 | A6 (the program's texts and the tests), last | - |

## Open decisions for the maintainer

1. The thick-plate threshold: keep the bound `q'' t/(2k)` against 5 % of the rise, lower it, or warn on the film-and-gradient estimate measured in A1 (the 10 W source of Muzychka case 2 is silent today while the program reads it about 4 % low).
2. Published cases as regression tests in the battery (A1 proposes the list; each costs seconds to a minute at the cells of the documents).
3. Whether the Lumped and Analytic accuracy quoted to the user should be the number against the FVM (what the models were fitted to) or against an independent reference (A4 gives both).
4. Whether tables measured against a reference later found hot are rewritten or kept marked 'superseded' (A2).
5. Which constants without a recorded source stay as 'typical, unsourced' (the FR-4 properties, the emissivity 0.9, the package and heatsink libraries) and which need a source before 2.8.0 (L10, L12).
6. Whether the forced-convection constant stays 0.664 or follows eq. 18 of Yovanovich-Teertstra (0.742, 11 to 14 % more h, L5).
