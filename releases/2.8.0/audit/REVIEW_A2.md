# Review A2: edge, laminate, outline and the finite-element references (with L7)

Assignment A2 of the claims register (`releases/2.8.0/audit/ASSIGNMENTS.md` and `claims.csv` on `docs/audit-claims-register`: 339 rows, 41 of risk 3) and the literature-to-code group L7 (formulas F-041 to F-049 of `formulas.csv`). Program: `development` 5fc91430 (2.7.1 plus documents). Branch `docs/audit-a2`; nothing in `pcbthermal/` or `tests/` was edited: the program, warning and test changes are items of section 5. Method as REVIEW_A1, A3, S1 and L1L5: the code read against `docs/theory.md`, every number re-printed by a run, the compared quantity fixed on both sides, every reference shown converged by its own refinement series, one heavy job at a time under the lock of the session (peak of every run of this review 2.37 GB). The 41 risk-3 claims are all given a verdict (section 4); of the other 298 rows of A2 only those that share a number with them were looked at.

**The finite-element runs** use the solver of `research/independent-fem-edge/lib` (numpy and scipy, pyamg above 40 000 unknowns) from a scratch environment outside the repository, with scratch scripts outside the repository (`fem_thin.py`, `prog_thin.py`, `report2.py`, `fem_pad.py`, `prog_pad.py`, `padlow.py`, `nsweep.py`, `fem_band.py`; their numbers are quoted here and in the documents). Nothing was read from stored `out/` caches: every finite-element number below was solved by this review.

## 1. What was re-run and what it printed

| run | what | printed (quoted in this review) |
| :-- | :-- | :-- |
| finite elements, thin-laminate boards of validation 44 (`cases.thin_board`) | 6 boards (full copper 4 layers 1.6 mm, 2 layers 1.0 mm, 4 layers 1.0 mm, 6 layers 1.0 and 1.6 mm; pad 4 layers 1.6 mm) x `h_side` 200 / 500 / 1000 / 2000 = 24 pairs; plan 0.4 / 0.2 / 0.1 / 0.05 mm (6 elements per gap); 12 elements per gap on the 0.2 mm plan at every coefficient, 24 on the 4-layer 1.6 mm board; 124 solves, balance 1 to 1e-12, largest 237 000 unknowns, 2.37 GB | point maximum and hottest 0.25 mm and 0.5 mm cell means, each extrapolated in its own sequence (section 2) |
| program on the same 24 pairs | FVM default at 1 / 0.5 / 0.25 mm (and 0.125 mm on the two 4-layer boards), FVM eight sub-gaps at 1 / 0.25 / 0.125 mm, FDM default at 1 / 0.5 / 0.25 mm | section 2; peak 0.54 GB |
| sub-gap sweep | FVM, n = 1 / 2 / 4 / 8, cells 0.25 and 0.125 mm, 4 layers 1.0 and 1.6 mm at 1000 W/m2K | section 3 (F-042) |
| pad board at `h_side` 10 | finite elements 0.2 / 0.1 / 0.05 mm, 6 / 12 / 24 per gap; FVM and FDM 1 / 0.5 / 0.25 mm | finite elements 74.35 K; FVM 72.77 / 75.15 / 73.96 K; FDM 66.45 / 71.16 / 72.60 K |
| validation 3.1, 10 and 20 mm pad rows (`copper_dissipation.board`) | finite elements quarter board 0.4 / 0.2 / 0.1 mm plan, 6 / 12 / 24 per gap; FVM, FDM 1 / 0.5 mm; 3D solid 1 mm | section 2.3 |
| `research/power-calculator/scripts/study_independent_datasheet_board.py` | the CSD17308Q3 board against `layered3d.py` | independent 48.00 K/W; FVM two layers 47.65 (-0.7 %), one layer 47.65 (-0.7 %), 3D solid 48.00 (+0.0 %); films 16.04 / 12.03 W/m2K; affine check +1.35 / -5.67 / -13.73 K with computed films |
| the 3.2 mm board of validation 36.1 (graded reference) | finite elements, 30 x 20 mm, corner part, 200 and 2000 W/m2K | section 2.4 |

**Pages read on the PDF image** (papers library, read only, rendered with pypdfium2 to the scratchpad; the text layer used only as a cross-check): [Muzychka2004Orthotropic] printed pages 49 and 50 (PDF 5 and 6): eq. 39 `k_r, k_xy = Σ k_i t_i / t` (bottom of the left column, p 49), eq. 40 `k_z = t / Σ t_i/k_i` (right column, p 49) with the condition 'if the source size is considerably larger than the thickness of individual layers', eq. 41 to 44 (flux tube), eq. 48 to 51 (flux channel, `k_eff = sqrt(k_xy k_z)`, `t_eff = t/γ`, `γ = sqrt(k_z/k_xy)`), eq. 52 to 56. The bibliography said 'equations 39 and 40 on page 6, machine only': they are on printed page 49 (PDF 5); eq. 50 and 51 are on printed page 50 (PDF 6). [CulhamYovanovich1998] (a scan, no text layer) printed pages 460 to 466, read on the image: Fig. 1 (base coupon 50 x 50 x 1.62 mm, FR4 0.5263 / Cu 0.0356 / FR4 0.5263 / Cu 0.0356 / FR4 0.5263 mm, k 0.4 / 400 W/mK, 25 x 25 mm 2.5 W source insulated around it, h 5 W/m2K on the exposed faces, adiabatic sides), Table 1 (in-plane 17.62, cross-plane 0.42, arithmetic 9.02, geometric 2.71, harmonic 0.82 W/mK), Table 2 (the five layer orders), text p 464 ('the effective conductivity can vary between 15.02 and 5.00 W/mK'; the base case 8.28 W/mK), Fig. 2 (layer order: 15.0 / about 11.5 / 8.3 / about 7.4 / 5.0 read from the plot). So the published coupon values used by `research/independent-fem-edge` 2 (RB-003) are confirmed on the page (two from the plot, as the folder said), and its base case is order 3 of Table 2, not order 1.

**Sources not among the PDFs (cannot be checked from the source, to download):** [Patankar1980] (the harmonic face mean of the FDM, F-048; a textbook, from memory); the Lee-Yovanovich conjugate glass and ceramic plate of T-023 (the folder does not name the paper; `LeeYovanovich1989Discrete`, `LeeYovanovich1991Step` and `LeeCulhamYovanovich1991` are in the library but were not identified as the source within this review).

## 2. The edge-laminate numbers on one footing (the main finding)

### 2.1 Four sets for one board, and which one is right

The same 1.6 mm four-layer board (10 x 10 mm, gaps 0.487 mm cut into two, 0.5 W on 3 x 2 mm, h_top 10, h_bottom 200) was quoted as:

| set | where | reference | quantity | verdict |
| :-- | :-- | :-- | :-- | :-- |
| -0.8 / -2.5 / -5.1 / -8.9 % | validation 36, 43.2 (first columns), strong-edge-laminate 8 | cell-centred `ref3d` at 0.125 mm | hottest cell | **superseded**: the reference is +0.3 / +1.0 / +1.7 / +2.8 % hot |
| -1.3 / -3.9 / -7.2 / -11.7 % | validation 44 (first table) | the same scheme at 0.25 mm | hottest cell | **superseded**: reference +0.9 / +2.5 / +4.1 / +6.2 % hot |
| -0.4 / -1.4 / -3.2 / -6.0 % | theory 1.4, validation 36.1, 44 'Reconciled' (until this review) | first finite-element run | hottest 0.25 mm cell | **superseded**: its through-thickness term was too small at 1000 and 2000 |
| -0.4 / -1.4 / -3.4 / -6.2 % | `checks.py`, user guide, validation 43.2, 44, 46 | closing review of `independent-fem-edge` | hottest 0.25 mm cell | **holds to 0.2 point**; this review: -0.4 / -1.6 / -3.4 / -6.3 % |
| -0.57 / - / -3.52 / - % | validation 46 table | the same finite elements | point maximum | **holds** (this review -0.58 / -1.67 / -3.50 / -6.45 %) |

Why the fourth set moves by up to 0.2 point: the closing review measured the through-thickness correction of the finite elements (6 against 12 elements per gap) at 1000 W/m2K only, set it to zero at 200 and 500 and used the 1000 value at 2000. Measured here at every coefficient (6 / 12 / 24 on the 4-layer board, observed order 2.4 to 2.7): +0.012 / +0.026 / +0.039 / +0.055 K, and +0.019 / +0.055 / +0.103 / +0.179 K on the 2-layer 1.0 mm board. The limits of the 24 pairs agree with the closing review within -0.29 to +0.06 % (largest on the 2-layer board at 2000 W/m2K).

The plan sequences: the point maximum converges with observed order 1.5 to 2.3 on 0.2 / 0.1 / 0.05 mm where the 0.4 mm level is left out (with it, order 0.5 to 1 on the thin-gap boards: the 0.4 mm plan is not in the asymptotic range for the point, and an extrapolation from 0.4 / 0.2 / 0.1 alone overshoots by up to 1 %); the cell means converge with order 1.1 to 1.7, the 0.4 / 0.2 / 0.1 and 0.2 / 0.1 / 0.05 limits within 0.01 to 0.2 % except the 6-layer 1.0 mm board at 1000 and 2000 W/m2K (0.45 and 0.96 %, gaps of 0.16 mm). The 8-layer and 6-layer 2.4 mm boards were not re-run.

### 2.2 The table on one footing

The full table (24 pairs, both quantities, every cell) is `docs/validation.md` 46.1 (added by this review). The readings that change what the documents say:

1. **The quantity.** The finite-element point maximum lies 0.1 to 0.25 % above the hottest 0.25 mm cell mean on these boards, so the two quantities give the same message at the rounding of the warnings. The user reads the program's hottest value as the board's hottest point, so the warning should quote the point: -0.6 / -1.7 / -3.5 / -6.5 % on the 4-layer 1.6 mm board (item W1). The hottest 0.5 mm cell mean of the truth is 0.5 to 0.75 % below the 0.25 mm one, which is why the tables of validation 44 that compare each program cell with the truth's cell of the same size show 0.4 to 0.7 point between 0.5 and 0.25 mm while the program's own rise does not move.
2. **Thin gaps that are not cut** (every gap under 0.4 mm: 4 layers 1.0 mm, 6 layers 1.0 and 1.6 mm): the error does not depend on the cell (within 0.2 point from 1 to 0.125 mm) and is -0.4 to -1.3 / -1.6 to -3.5 / -3.4 to -6.2 / -5.8 to -10.0 % against the hottest point. The warning's 'about -0.1 to -1 / -1 to -3 / -2 to -6 / -4 to -10 %' holds (the -0.1 and -2.2 ends are the 8-layer boards, not re-run).
3. **Gaps that are cut (the 4-layer 1.6 mm and 2-layer 1.0 mm boards): the error depends on the cell, and the cooler the finer.** Against the hottest point, 4-layer 1.6 mm, default rule: 1 mm +1.0 / +1.7 / +0.4 / -3.1 %; 0.5 mm -0.0 / -0.5 / -2.0 / -5.0 %; 0.25 mm -0.6 / -1.7 / -3.5 / -6.4 %; 0.125 mm -0.8 / -2.1 / -4.1 / -7.0 %. The half-cell film of a coarse cell on the laminate nodes of the band over-corrects and hides part of the missing sub-gaps; converged in the cell the error is about -0.8 / -2.2 / -4.2 / -7 %. **The quoted 0.25 mm numbers are therefore not the idealisation error but a mix**, and the warning's advice 'a smaller cell reduces the cool error' is wrong for the default rule: refining the cell alone makes the reading cooler (item W2).
4. **Eight sub-gaps** reach the truth only when the cell is near the sub-gap: +0.0 to +0.3 % at 0.125 mm on the cut board (+0.2 to +1.4 % on the thin ones), +0.4 to +2.3 % at 0.25 mm, +3.6 to +14.5 % at 1 mm (thin boards up to +20 %). The rule of thumb that the sweep of section 3 supports: a sub-gap of about half the cell (within about 1 % at 1000 W/m2K on the two boards swept).
5. **The FDM on outer pads at a coarse cell** reads 15 to 28 % low at 1 mm on the pad board at 200 to 2000 W/m2K, and **10.6 % low with an edge of only 10 W/m2K** (finite elements 74.35 K, FDM 66.45 K, FVM 72.77 K at 1 mm; FDM 4.3 % low at 0.5 mm, 2.3 % at 0.25 mm). That is the FDM's copper edge inside the outline (validation 47, A40 of `research/ROADMAP.md`), not the laminate at the edge, and it is larger at the default 1 mm cell than any number the documents quote for it (-5.8 / -12.0 % on the 20 mm square at 200 / 1000 W/m2K). Unexplained in size; a limit to record (item W4).

### 2.3 Validation 3 and 3.1: the old finite-element reference is cold

`research/solid3d-verification/scripts/fem3d_validation.py` (scikit-fem, 1 mm elements, 4 across a gap) is the reference of validation 3 and 3.1 and of theory 4 ('within 0.2 %, +1.6 %, +8 %'). The two pad rows of 3.1 were solved again with the conforming finite elements (quarter board, plan 0.4 / 0.2 / 0.1 mm near the edges, Richardson order 1.5 and 1.9; 6 / 12 / 24 elements in the 1.53 mm gap, order 2.9): hottest rise **481.7 K** (10 mm pad; the table's 470.3 K is 2.4 % low; the through-thickness term alone is +1.57 K) and **250.7 K** (20 mm; the table's 248.0 K is 1.1 % low). Against them, on the tree: FVM +0.5 / -1.1 % (1 / 0.5 mm) and +0.1 / -0.6 %; FDM -4.3 / -2.7 % and -2.0 / -1.3 %; the 3D solid at 1 mm +4.9 % and +2.3 % (the table's +8.0 and +3.6 % were the 4-slab solid of 2.4.5 against the cold reference). So 'the FVM is +2.9 % on a one-sided heater pad' and 'the 3D solid +8 %' are false on the current program; the 3D solid's excess is its 1 mm plan cell on a 10 mm part (validation 21.3). Note added to validation 3.1. The main table of validation 3 (four boards, 90.6 / 112.2 / 136.2 / 85.6 °C) was not re-run; its reference has the same element size, so its 'within 0.2 %' carries an uncertainty of the order of 1 % (not measured).

### 2.4 The graded reference of validation 36.1

(filled in when the run finishes)

## 3. L7: the laminate formulas against their sources

| formula | code | source and check | verdict |
| :-- | :-- | :-- | :-- |
| F-041 layer sheet `S = f k_cu t_cu + k_ip (slab - f t_cu)`, gap `g = k_th/d`, slab = copper + half of each gap | `fvm.py` 223 to 225, `model.Board.slab_thicknesses` | own (parallel sheet, 1D gap); the parallel and series sums are eqs. 39 and 40 of [Muzychka2004Orthotropic] p 49 (read on the image here) with their condition (source much larger than a layer) | **holds** as coded; theory 1.2 equals the code. The statement that no averaged stack conductivity is used rests on [CulhamYovanovich1998] Table 1 (read on the image): the five means 0.42 to 17.62 W/mK against effective 5.0 to 15.0 |
| F-047 gap of several sheets | `model.combine_sheets` | eqs. 39 and 40 p 49 of [Muzychka2004Orthotropic], read on the image | **holds**; the status of eqs. 39 and 40 is now R on the image; the bibliography's page (6) is wrong: printed page 49, PDF 5 |
| F-042 sub-gap rule `n = min(n_max, ceil(d/s_max))`, margin `ceil(d/dx) + 1` | `laminate.n_for_gap`, `margin_cells`, `flag_cells` | own; checked against the finite elements (section 2) and by a sweep: 4 layers 1.6 mm, 1000 W/m2K, error against the hottest point n = 1 / 2 / 4 / 8: -10.3 / -3.5 / +0.2 / +2.0 % at 0.25 mm, -10.3 / -4.1 / -1.0 / +0.3 % at 0.125 mm; 4 layers 1.0 mm -6.1 / -0.9 / +1.9 / +3.3 % and -6.1 / -1.9 / +0.1 / +1.0 % | **holds with a narrower statement**: theory's 'the error falls as 1/n' holds for the idealisation part (a fit `e_inf + a/n`, a about -11 %, leaves 0.4 point), but a cell term of about +16 % per mm of cell at 1000 W/m2K is added on the laminate nodes (`e_inf` +3.9 % at 0.25 mm, +1.7 % at 0.125 mm). With n = 1 the error does not depend on the cell at all. The defaults (0.4 mm, 4) and the margin are own choices with no source |
| F-043 edge band | `laminate.edge_band`, `plan_gaps(edge=)` | own; band applied only when the gap is cut (n > 1): a board whose gaps are all under 0.4 mm gets no band, which is why validation 44 exists | **holds** as coded and documented; the width claim (one gap thickness is enough) was not re-measured |
| F-044 face term `Q t_cu / (2 k_z A)`, sliver guard `min(1, w/(4 t_cu))` | `laminate.face_terms` | own 1D derivation (half the copper thickness filled with laminate); the guard of four copper thicknesses is a choice with no source | **holds** as a first-order model (the 2.33 K of validation 3 is this term); the guard is unmeasured |
| F-045 face time constant | theory 10 | Carslaw-Jaeger from memory | not checked (L8) |
| F-046 legacy two laminate nodes, Analytic series film | `laminate.LAMINATE_NODES`, `series_bottom_problem` | own sweep | **holds** as stated (validation 21; not re-run) |
| F-048 FDM harmonic face mean | `fdm._mean` | [Patankar1980], not among the PDFs (to download): **cannot be checked from the source**; the harmonic mean of two half-cells in series is exact for a 1D series and needs no source | **holds** numerically; the cover handling (the mean cover times the harmonic mean of the physical sheets) is own |
| F-049 3D solid slabs `clip(ceil(d/0.2 mm), 4, 16)` | `solid3d.slab_rule` | own; validation 21.3 | **holds** as coded; its accuracy statements are A2 claim VA-143 (section 4) |

L7 item 4 (eq. 50 of [Muzychka2004Orthotropic] in a battery test): the equation was read on the image (p 50, with eq. 51 for `φ(ζ)`); `research/paper-case-studies` reproduces it; proposed as test T2 (section 5). L7 item 5 (quantity): eq. 50 gives the spreading resistance from the SOURCE MEAN temperature; the program reports the hottest cell plus the face term (peak). Theory 1.4's small-part table (T-020) and theory 4 (T-084) compare those two without saying so: section 4.

## 4. The 41 risk-3 claims

| id | claim (short) | verdict | action |
| :-- | :-- | :-- | :-- |
| T-014 | theory 1.4: -0.4 / -1.4 / -3.2 / -6.0 % against the FE | **false at 1000 and 2000** (first FE run) | theory 1.4 rewritten: -0.4 / -1.6 / -3.4 / -6.3 % (cell), -0.6 / -1.7 / -3.5 / -6.5 % (point), the cell dependence on cut gaps |
| T-015 | eight sub-gaps +0.6 / +1.6 / +2.2 / +2.6 % | **holds** (+0.6 / +1.4 / +2.2 / +2.5) | theory 1.4, validation 36.1 and 43.2 aligned |
| T-020 | small-part table against eq. 50 and an extrapolated 3D | **narrower**: eq. 50 is read on the page (p 50) but gives the source MEAN; the program column is a peak with the face term; the quantity is not stated | item D1 (state the quantity in theory 1.4); not re-run |
| T-021 | pad numbers carry about 1.5 points (reference order near 1) | **holds as a stated uncertainty** (self-referenced) | not re-run; the pad cases against the FE are item R1 |
| T-023 | single h on the Lee-Yovanovich glass plate +10.3 % | **cannot be checked from the source** (paper not identified among the PDFs) | listed for download |
| T-054 | via effect 31 to 47 % low etc. (theory 2.2) | settled by A3 (RCD-003: false on the current program, pre-rim) | none here |
| T-084 | 2 mm part +5.5 -> +4.1 % etc. | **narrower** (quantity not stated: eq. 50 is a source mean, the program a peak) | item D1 |
| T-090 | 3D solid vs FE within 0.2 % / +1.6 % / +8 % | **false for the +8 %**: the reference was 2.4 % cold; against a converged FE the 3D solid at 1 mm is +4.9 % (10 mm pad), +2.3 % (20 mm pad) | validation 3.1 note; theory 4 text item D2 |
| VA-020 | validation 3.1 3D FV +8.0 / +3.6 %, FVM +2.9 % | **false on the current program** | note in 3.1 with the re-run numbers |
| VA-025 | uniform board within 0.7 %, example within 1.7 % | **holds with a wider band**: the reference (1 mm elements) carries up to about 1 % on a one-sided pad (2.3); not re-run on these four boards | stated in 3.1 note |
| VA-027 | the remaining 0.1 to 0.7 % attributed to one node per layer, not measured | **holds as a disclosed attribution** | none (the sub-gap sweep of section 3 measures the analogous term for the edge) |
| VA-076 | 3D solid -3.3 % of the FVM on the L; which is right not established | **holds** (still not established) | item R2 (L shape against the FE) |
| VA-077 | 'FVM and the independent 3D solid agree within 1.5 %' | **misleading** (the program's own solid, called independent) | validation 12 sentence corrected |
| VA-078 | advanced stack-up adds no model error (table A) | **holds against the FVM only** (self-referenced) | none; not re-run |
| VA-128 | nine boards vs 3D solid at 1 mm | **narrower**: the 3D solid at 1 mm is +2 to +5 % on parts of 10 to 20 mm (2.3), the size of the claimed means | item R3 (re-run against `layered3d` or the FE) |
| VA-132 | 2-layer boards vs the independent solver, script not in the repository | **stale and partly unreproducible**: the empty-bottom row has a script and prints -0.7 % now (not -2.3 %); the other rows have none | validation 21.1 marked superseded; power-calculator 4.6 marked stale |
| VA-134 | laminate rule vs resolved 3D, 3.2 mm reference 1.6 % high | **holds with its own footnote** (the reference is unconverged, derived numbers) | not re-run (item R1) |
| VA-143 | slabs alone follow d/n/S; the 0.15 warning; plan cell dominates | **holds in direction** (2.3 confirms the plan-cell term: +4.9 % at 1 mm on a 10 mm part); the 1/n² slab extrapolation was not checked | none |
| VB-003 | T preset 106.809 / 105.938 / 107.788 °C | **stale** (pre-2.6.0: exact cover, cut-cell links, band, sliver fix) | validation 23 marked; not re-run |
| VB-007 | cut-cell residual 0.5 to 0.7 K, turned 40 mm board +1.25 / +3.52 K | **stale** (2.4.5) | validation 23 marked |
| VB-116 | four-layer at 1000: -8.9 % (equal slabs) vs -5.1 % | **superseded** (against the hot reference); -3.4 % (cell) / -3.5 % (point) against the FE | strong-edge README note; 43.2 already carries the FE columns |
| VB-128 | 38.1 'mean error halves' | **already corrected in the text** (38.4 review) | none |
| VB-134 | 'about -2 % below the resolved laminate' | **misleading** (not a constant: -0.8 % on the T and L at 200, -3.1 % on the square at 1000, -0.8 to -7 % converged on the 4-layer board) | three sentences of validation 39 and 40 corrected |
| VB-138 | 40.2 square at 1000: -3.65 -> -0.93 % | **misleading in the table** (a cancellation, said in 40.5 only) | mark added in the 40.2 row |
| VB-143 | 41 strips row | **cannot be reproduced** (no script; 47.2 says so) | row marked withdrawn |
| VB-160 | 44 first table against the cell-centred reference | **superseded** (reference hot), kept with its caveat | decision 4 of the maintainer: kept marked |
| RB-003 | coupon FE vs paper -2.5 to -5.5 % | **holds**: the published values are confirmed on the PDF image (Fig. 2 and p 464); the shortfall is not explained (case definition or paper); the base case is order 3 | none in the folder; the boundary condition (h 5 W/m2K on the exposed faces, source insulated around) is as Fig. 1 says |
| RB-007 | via 3 mm from the wall -0.9 % agreement | **misleading** (the folder's own review: a crossing) | none (already said in 3(b) reading 4) |
| RB-012 | the reconciliation and -0.4 / -1.4 / -3.4 / -6.2 % | **holds to 0.2 point** | independent-fem-edge 6.4 added; validation 44 'Reconciled' corrected |
| RB-038 | FVM within 0.6 % of the axisymmetric layered model; 'FVM adequate at the edge' | **misleading** (self-consistent: same idealisation); against the FE the FVM default reads -0.6 to -6.5 % at a strong edge | item D3 (README of rotated-square-3d) |
| RB-056 | 3D solid slab centre within 2 % of the face value | **not re-run**; same family as 2.3 (the 3D solid at 1 mm carries its plan-cell error) | item R1 |
| RB-060 | transient of the laminate rule against ref3d | **cannot be checked here** (transient FE is A4's `transient-reference-boards`) | to A4 |
| RB-074 | screening rule 8 / 12 gap thicknesses | **holds as a pre-2.4.5 study**; no program text quotes it (`grep`) | none |
| RB-081 | '13 to 17 % low at 200' | **superseded** (before the band, against a reference hot at 1 mm); no program document quotes it any more (`grep`) | laminate-slabs README line marked |
| RB-088 | `study_solid_slices.py` counts the face term twice, not corrected | **false**: corrected in the script since c98d21d3 (`face_mean` guard) | README status sentence corrected |
| RB-099 | ref3d sound, 1/8 mm 0.8 % hot | **narrower**: against the FE the plate is +1.65 % and the via effect +8.5 % at 1/8 mm, 1000 W/m2K | strong-edge README note |
| RB-100 | eight sub-gaps plate +0.4 / -0.4 % | **false against the FE** (+2.2 / +2.5 %) | strong-edge README note |
| RB-101 | via within 0.6 % with eight; 0.16 mm -7.3 % | **false against the FE** (+0.5 % at 0.16 mm, 1000 W/m2K) | strong-edge README note |
| RB-115 | 3D solid sliver defect +15.9 K | **holds as history**; fixed in 2.6.0 (validation 33) | validation 23 marked |
| RB-142 | straddling heater rows against the 3D solid at 1 mm | **not re-run** (3D solid at 1 mm carries +2 to +5 % on such parts) | item R1 |
| RCB-071 | Analytic variant -32 to -13 % (no script) | **cannot be reproduced** (no script) | validation 21.1 says so |

## 5. Items for a `fix/` branch or the executor (not edited here)

* **W1 (texts, `checks.py` 1174 to 1183 and the user guide limits table, `help/index.html` 451)**: quote the point set, -0.6 / -1.7 / -3.5 / -6.5 % at 200 / 500 / 1000 / 2000 W/m2K at a 0.25 mm cell, or keep -0.4 / -1.6 / -3.4 / -6.3 % and name the quantity (hottest 0.25 mm cell); either way 500 W/m2K reads -1.6, not -1.4, and 2000 -6.3, not -6.2. The phrase 'cell-centred finite-volume 3D reference, which the finite-element comparison showed to read hot' for the 3.2 mm two-layer boards is about the graded reference of validation 36.1, which was converged to 0.03 K on a graded mesh; see 2.4 for whether the clause stands. Frozen-number risk: none (text). Tests: `test_help.py`, `test_warning_texts_plain.py`.
* **W2 (texts, the same warning)**: 'A larger sub-gaps (now n) and a smaller cell reduce the cool error' and the short 'refine the cell' are wrong for the default rule on cut gaps (a finer cell alone makes the reading cooler: -3.1 % at 1 mm to -7.0 % at 0.125 mm at 2000 W/m2K). Proposed: 'At the default sub-gaps a coarse cell hides part of the error (on this board +0.4 % at 1 mm, -4.1 % at 0.125 mm at 1000 W/m2K); more sub-gaps help only with a cell no wider than about two sub-gaps (eight sub-gaps at 0.125 mm: within 0.3 %).' In the uncut text, 'refine the cell first' changes nothing on its own (the error of uncut gaps does not depend on the cell): say 'cut the gaps (a sub-gap of about half the cell) and refine the cell together'.
* **W3 (texts)**: the uncut warning's '-4 to -10 %' at 2000 holds; its 'eight sub-gaps read +1 % at 200 to +7 % at 2000 at a 0.25 mm cell' holds (+0.7 to +6.9 %).
* **W4 (limit to record, `docs/validation.md` 47 and the FDM limits row of the guide)**: the FDM reads a 5 x 4 mm outer pad of a four-layer board 10.6 % low at 1 mm with `h_side` 10 W/m2K and 15 to 28 % low at 200 to 2000 W/m2K (section 2.2 item 5). A40 of `research/ROADMAP.md`.
* **D1 (theory 1.4 small-part table, theory 4 limits)**: say which quantity each side is (eq. 50 of [Muzychka2004Orthotropic] p 50: the spreading resistance from the source mean; the program: the hottest cell with the face term).
* **D2 (theory 4 'where it is checked')**: replace 'within 0.2 % on three boards, +1.6 % on a 20 mm pad, +8 % on a heater-sized pad' by the converged numbers of 2.3 (+2.3 % and +4.9 % at 1 mm on the 20 and 10 mm pads of validation 3.1) and say that the four-board table of validation 3 rests on a 1 mm finite-element mesh.
* **D3**: `research/rotated-square-3d` README 7 and 9.5 ('the FVM is adequate at the edge') rests on a reference with the same idealisation; point to validation 46.1.
* **R1 (re-runs left)**: the pad and small-part rows (T-020, T-021, T-084, VA-134, RB-056, RB-142) against the FE at a converged cell; **R2** the L shape of validation 12 against the FE; **R3** the nine boards of validation 21 against `layered3d` or the FE.
* **T1 (test)**: a battery test that the 4-layer 1.6 mm board at 1000 W/m2K and 0.25 mm reads between -5 % and -2 % of 24.33 K (the FE limit stored as a number, with this review as its source; one-sided bounds on both sides, about 1 s). **T2 (test)**: eq. 50 of [Muzychka2004Orthotropic] in the battery for one row of the small-part table (the closed form is 10 lines).

## 6. Open decisions for the maintainer

1. Which quantity the user-facing numbers quote: the true hottest point (proposed: it is what a user reads) or the hottest 0.25 mm cell (what the scheme is measured against). The difference is 0.1 to 0.25 point.
2. Whether the edge warning quotes the 0.25 mm numbers (the cell of the studies) or the error converged in the cell (-0.8 / -2.2 / -4.2 / -7 % on the cut board), or both with the default 1 mm cell's (+1.0 to -3.1 %).
3. The tables measured against the hot references (validation 36 first columns, 43.2 first columns, 44 first table, strong-edge-laminate 4 to 8) were kept and marked superseded, not rewritten (decision 4 of `ASSIGNMENTS.md`).

## 7. Verdict

(written at the end)
