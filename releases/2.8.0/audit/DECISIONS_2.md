# Decisions on the open questions of the 2.8.0 audit, second set

The reviewer's answers to the open decisions raised after `DECISIONS.md` (decisions 1 to 11): `REVIEW_L1L5.md` (D1 to D3), `REVIEW_L4L9.md` (P3, T4), `REVIEW_A2.md` (section 6 and items W1 to W4), and the three review branches not yet merged: `docs/audit-a4` (`REVIEW_A4.md`), `docs/audit-a5` (`REVIEW_A5.md`, M1 to M3 and P1 to P10) and `docs/audit-s1` (`REVIEW_S1.md`, the JEDEC board). The numbering continues that of `DECISIONS.md`. Program: `development` 35eeb773 (the five fix branches and the audit documents of A1, A3, L1+L5, L4+L9, A2+L7 and `DECISIONS.md` merged). The same rule: each decision is taken here with its evidence; only a question of policy, scope, licence, sourcing or release is marked **maintainer**. Nothing in `pcbthermal/` or `tests/` is edited on this branch.

Every number below is printed by a script named next to it, by the review that is cited, or by the checks of section 33 of this file (run on 35eeb773 for this file).

**Two facts found while answering, which change earlier texts:**

* `fix/analytic-transient-hot-point` was merged in its reviewed form (commit cae83792, 'Keep the Analytic readout point on a flat steady top'): the readout keeps the point of the board without vias while it is within 0.25 % of the steady maximum, **no frozen number moved and its pending file was removed**. So the item P1 of `REVIEW_A4.md` ('example board U1 +0.69 % plateau, -1.0 % t63', 'Analytic transient records of the boards with vias' moving) describes the first version of that branch and is stale; `DECISIONS.md` 9, step 2 (c), is done and moves nothing. The only pending file on `development` is `lumped-part-readout.json`.
* The re-run asked by `REVIEW_A4.md` P1 (section 33, check 1) gives the Analytic time to 63 % at -9.1 % to **+3.2 %** of the FVM on the ten boards of validation 4.1 at the Analytic's default 1 mm cell (the 'vias and heatsink beside' board moved from +0.6 % to +3.2 % with the merged fix). The review of the fix measured -8.3 % to +2.1 % with the Analytic at 0.5 mm. The warning key on `development` says '-8 % to +2 %', which the default cell does not meet (decision 24).

## 12. The Rayleigh warning of the face up (L1L5 D1)

**Options.** (a) Keep the band 1e4 to 1e11; (b) the range of the law used, Lloyd and Moran 2.2e4 to 8e6; (c) adopt the Raithby-Hollands law of Lienhard eq. 8.37 for the face up (option B of `research/convection-laws`); (d) a band chosen by where the law used still agrees with the printed one.

**Evidence.** The program's up-face law `0.54 Ra^(1/4)` against the Raithby-Hollands form printed by [Lienhard2024] (eq. 8.37a/b with the thick-layer correction, `Pr` 0.71; check 2): -28.6 / -13.6 / -7.2 / -0.9 / +4.1 / +8.8 / +11.3 / +15.4 / +19.6 / +21.9 / +22.1 % at Ra 10 / 1e2 / 3e2 / 1e3 / 3e3 / 1e4 / 2.2e4 / 1e5 / 1e6 / 8e6 / 1e7 (the -7 / -1 / +9 / +15 % already in theory 8 are reproduced). Below about 2e3 the program's coefficient is the lower one (the board reads hotter: safe side); above it the program's is the higher one (cooler: unsafe side). **The band of today (a) warns exactly where the program is on the safe side and is silent from 1e4 to 1e7, where it is 9 to 22 % above the printed law.** Option (b) does not fix that either: inside Lloyd and Moran's own range the two published forms differ by +11 to +22 %, so a range warning is not an accuracy signal. Top-face Ra of typical boards (`A/P`, rise 5 / 10 / 20 / 40 K, check 3): 30 x 20 mm 1.0e2 to 6.2e2; 60 x 40 mm 8.0e2 to 4.9e3; 100 x 80 mm 5.1e3 to 3.1e4; 160 x 100 mm 1.4e4 to 8.3e4; so today's band warns on nearly every board up to 100 x 80 mm, and (b) would warn on almost every board. The effect of the choice of up-face law on the rise is small: option B moved the hottest rise by -1.7 to +2.9 % on the 17 boards (CLAUDE.md, 'Convection decision'). Option (c) moves the computed-h results and is the maintainer's earlier decision to defer until the measured board (same entry): not reopened here.

**Decision.** (d): the face-up warning fires outside **1e2 to 1e7**, with the text 'outside the range where the up-face law and the law printed by Lienhard (Raithby-Hollands) agree within about 15 to 22 %; the face-up coefficient is uncertain by more than that'. 1e2 matches the face-down band (1e2 to 1e9), 1e7 is the end of the law used and of the printed one (the program's turbulent branch starts there with a +6 % step, `REVIEW_L1L5` finding 4). Theory 8 gets one sentence with the table of check 2 (the two published forms differ by -14 to +22 % over the board range, inside the ±50 % spread of the horizontal-plate results printed by [YovanovichJafarpur1993] p 8), and the Results line 'never compared with a measured copper board' stays.

**Who acts.** Executor on `fix/convection-warnings` (decision 31, step 2); reviewer; maintainer (help, tooltips none). **Frozen numbers**: none (no frozen record uses computed `h`). Tests: the warning fires at Ra 50 and 2e7 and not at 1e3 and 1e5 (`tests/test_convection.py`); `tests/test_help.py` if the guide quotes the band.

**Risk.** Low. Fewer runs warn than today; the ones that stop warning are those where the law reads hot.

## 13. `L = A/P` on a concave outline (L1L5 D2)

**Options.** (a) Keep the perimeter of the outline itself; (b) the perimeter of its convex hull.

**Evidence.** Lloyd and Moran tested discs, squares, rectangles and right triangles (YJ p 7): a concave planform has no source either way. With the hull perimeter the two concave harness boards read +0.63 % and +1.16 % of the rise (`REVIEW_L1L5` section 1). The role of `A/P` is the mean distance the air travels from an edge where it can enter; a re-entrant notch of a board is an open edge, and the arms of a T are narrow strips that the hull would treat as part of one wide plate. The difference is about 1 % against a ±50 % spread of the published horizontal-face results.

**Decision.** (a): keep the outline perimeter, as now documented in models 18; no code change. **Frozen numbers**: none.

**Who acts.** Nobody beyond the sentence already in models 18. **Risk.** Low: the program's choice is the cooler one by about 1 % on concave boards.

## 14. A Reynolds-range warning (L1L5 D3)

**Options.** (a) No warning; (b) a warning when a face with forced air has `Re` below 100 or above 1e5.

**Evidence.** The laminar plate holds for about 100 < Re < 1e5 ([Lienhard2024] p 309, transition 'typically over 1e5', 4e4 to 1e5 with disturbances, p 332); the program stays laminar up to 5e5 and has no lower bound; both errors under-state `h` (the board reads hot). A board with parts at Re 1.4e5 (150 mm at 15 m/s) is likely turbulent.

**Decision.** (b), as the item P3 of `REVIEW_L1L5` writes it, worded as a hot-side note ('outside the laminar flat-plate range of the forced-air law; the result is on the hot side'), in the run warnings beside the Rayleigh warnings of `api._solve_computed_h`. It costs nothing, fires rarely, and tells the user why a forced-air result may be pessimistic.

**Who acts.** Executor on `fix/convection-warnings` with decision 12. **Frozen numbers**: none. Test: `h_forced` cases at 0.05 m/s on 20 mm (Re about 60) and 15 m/s on 150 mm warn, 1 m/s on 100 mm does not.

## 15. The laminate in the edge film of the Analytic and the Lumped (L4L9 P3, A4 P3)

**Options.** (a) Implement in 2.8.0: the laminate half-thickness in series with the edge film inside `β_l` (Analytic) and in the edge loss of the rings (Lumped); (b) a stated limit with the existing warning, the fix investigated first and adopted after; (c) nothing.

**Evidence.** The Analytic reads cool by 2.4 to 11.4 % against the shipped FVM and 3.7 to 14.9 % against the independent 3D solver at `h_side` 200 W/m²K (3.2 mm board, part in a corner the worst), and within 1.4 % of both at the default 10 W/m²K (`REVIEW_A4` 4.1, `REVIEW_L4L9` section 4). `checks.check_reduced_edge_laminate` fires on every such board of the sample (from 150 W/m²K·mm). The proposed fix is a sketch, not measured: CLAUDE.md (decision of `feature/analytic-edge-and-local-transient`) attributes the cool side of the per-layer edge to the one laminate link per gap of the idealisation, so a series film alone may close only part of the gap, and the Lumped's near-edge deficit has its own fix in progress (`fix/lumped-edge-first-link`). The change would move the Analytic records of every harness board with an edge coefficient (`regress_boards.py` builds at least eight of the 17 with `h_side` 10), by a small amount at 10 W/m²K. The 2.8.0 aim, answered by the reviewer and kept by the maintainer, is measured, bounded and warned errors, not new corrections (CLAUDE.md, 'Open questions of 2.8.0 answered by the reviewer').

**Decision.** (b). In 2.8.0 the error is a stated limit with the independent number first (decision 3): the warning text of `check_reduced_edge_laminate` and theory 6 quote '-4 to -15 % of the rise against an independent 3D solver at 200 W/m²K, within 1.4 % at the default 10 W/m²K'. A research branch `research/reduced-models-edge-laminate` prototypes the series film in its `lib/` on a copy, measures it on the 45 boards of `REVIEW_L4L9` against `layered3d_side` and the FVM, separates the series film from the one-link-per-gap term, and writes `INTEGRATION.md`. If its review gives GO before step 3 of decision 31 starts, it enters as a model fix before `fix/face-film-half-slab`; otherwise it is a 2.9 item. **Maintainer**: only whether he wants this correction in 2.8.0 despite the 'no new corrections' aim (recommended: no).

**Risk.** The limit stays for users with strong edge cooling (warned). Frozen numbers: none in 2.8.0 with (b).

## 16. Validation 32: re-measure against a 3D reference with the band, or keep the band-off numbers (L4L9 T4)

**Options.** (a) Re-measure 32.1 and 32.2 with the laminate band on against a 3D reference; (b) keep the cut-cell statement with the band off (what it isolates), and quote the one band-on independent row that exists.

**Evidence.** Section 32 is about the cut-cell links and the edge film; the band is section 36, checked against the finite elements in 46. With the band off the program reproduces the 32.1 'after' column to the third decimal and the turn spread is 0.13 to 0.44 K (`REVIEW_L4L9` section 3); the cut-cell tests already switch the band off. One independent band-on number exists: the sliver board, 138.79 °C against 140.23 °C of the 3D box of 33.4 (-1.3 % of the rise). `two_sheet.py` is not a reference with a cooled edge (it lacks the edge laminate: +5.5 K).

**Decision.** (b): section 32 states its numbers with the band off and says so in its head note (already added by L4L9), plus the band-on sliver row against the 3D box (-1.3 %); no heavy re-run. A2's item R1 to R3 re-runs stay as written. **Frozen numbers**: none.

**Who acts.** A6 (one row and one sentence in validation 32). Tests: item T1 of `REVIEW_L4L9` (the FVM peak does not depend on `EDGE_FILM_FLOOR`) in `fix/audit-regression-tests`.

## 17. Which quantity the user-facing numbers quote: the hottest point or the hottest 0.25 mm cell (A2, open decision 1)

**Evidence.** The finite-element point maximum is 0.1 to 0.25 % above the hottest 0.25 mm cell mean on the 24 pairs of validation 46.1 (`REVIEW_A2` 2.2). The user reads the program's hottest value as the hottest point of the board.

**Decision.** The point: warnings and the guide quote the error of the program's hottest value against the true hottest point (-0.6 / -1.7 / -3.5 / -6.5 % on the 4-layer 1.6 mm board at 0.25 mm), and name the quantity once ('against the hottest point of an independent finite-element solution'). Validation tables keep both columns. **Frozen numbers**: none.

## 18. Which cell's error the edge warning quotes (A2, open decision 2)

**Options.** (a) 0.25 mm (the cell of the studies); (b) the error converged in the cell; (c) both with the default 1 mm cell.

**Evidence.** On cut gaps the error depends on the cell and grows as the cell shrinks: 1 mm +1.0 / +1.7 / +0.4 / -3.1 %, 0.5 mm -0.0 / -0.5 / -2.0 / -5.0 %, 0.25 mm -0.6 / -1.7 / -3.5 / -6.4 %, 0.125 mm -0.8 / -2.1 / -4.1 / -7.0 % at 200 / 500 / 1000 / 2000 W/m²K; the 0.25 mm set is a mix of the idealisation error and a compensating half-cell film error (`REVIEW_A2` 2.2 item 3). On uncut thin gaps the error does not depend on the cell.

**Decision.** (b) first, then the default cell: 'the laminate at the edge reads cool by about 1 / 2 / 4 / 7 % of the rise at 200 / 500 / 1000 / 2000 W/m²K against an independent finite-element solution, the limit as the cell is refined; at a 1 mm cell part of it is hidden by a compensating error (+1 to -3 %)'. The headline is the bound a user approaches by refining, which is the honest one for a warning; the 0.25 mm numbers stay in validation 46. **Frozen numbers**: none.

## 19. Tables measured against references later found hot (A2, open decision 3)

**Decision.** The handling of `REVIEW_A2` (validation 36 and 43.2 first columns, 44 first table, `strong-edge-laminate` 4 to 8 kept and marked superseded) is decision 4 (c) of `DECISIONS.md` applied as written; nothing new to decide. It stands or falls with decision 4, which the maintainer has to confirm (policy of the documents).

## 20. The edge-laminate warning texts (A2 W1, W2, W3): NO-GO until corrected

**Evidence.** `checks.check_edge_laminate` (long text, `checks.py` 1174 to 1183) calls the 3.2 mm figures 'too pessimistic' because measured 'against a cell-centred reference that reads hot': false, that reference is the graded `graded3d.py`, within +0.06 % / +0.02 % of the finite elements (`REVIEW_A2` 2.4). Its advice 'a smaller cell reduces the cool error' is wrong for the default rule on cut gaps (decision 18). The uncut-gap clauses hold (W3).

**Decision.** The texts are a release blocker (the user reads them): rewrite them as `REVIEW_A2` W1 and W2 propose, with the numbers of decisions 17 and 18, in A6 (`fix/audit-texts`, decision 31, step 4). **Frozen numbers**: none. Tests: `tests/test_help.py`, `tests/test_warning_texts_plain.py`, and one assertion that the long text no longer contains 'too pessimistic'.

## 21. The FDM on small outer pads (A2 W4)

**Options.** (a) A limit written in validation 47 and the guide; (b) (a) plus a live warning for the FDM; (c) a fix (A40, open investigation).

**Evidence.** The FDM reads a 5 x 4 mm outer pad of a four-layer board 10.6 % low at the default 1 mm cell with `h_side` only 10 W/m²K (finite elements 74.35 K, FDM 66.45 K, FVM 72.77 K), 4.3 % at 0.5 mm, 2.3 % at 0.25 mm, and 15 to 28 % low at 1 mm with 200 to 2000 W/m²K: larger than any number the documents quote for the FDM, on the unsafe side, at the default cell. One board only; size unexplained (A40 of `research/ROADMAP.md`).

**Decision.** (b). The FDM is a comparison model, but a user who ticks it sees its number beside the FVM's with no hint that it is 10 % low. A live warning when the FDM is selected and the copper under a heater on an outer layer has its narrow side under 8 cells ('the FDM may read 5 to 11 % low here, 15 to 28 % with a strong edge; use the FVM or a cell of at most an eighth of the pad'), with the rule checked on two more pads (3 x 3 and 8 x 6 mm) by the executor before the text quotes numbers. It must be measured **after** `fix/drawn-copper-faces`, which changes the FDM faces of drawn layers. A40 stays open. **Frozen numbers**: none.

**Who acts.** Executor in A6 (`fix/audit-texts`) after the model fixes; reviewer.

## 22. Independent-reference first, and the -13.7 / +0.3 % sentence (A4)

**Evidence.** `REVIEW_A4` applies decision 3 of `DECISIONS.md` throughout. Its item M1 says `CLAUDE.md` quotes '-13.7 % to +0.3 %' without the reference; the entry of `fix/lumped-first-ring` in `CLAUDE.md` already reads '100 x 80 mm -13.1 % to +1.0 % against the FVM at 0.5 mm, the -13.7 / +0.3 % of the investigation is against the FVM at 0.25 mm', and gives the independent figure in the same entry (-29.5..+1.2 % to -7.8..+1.2 % against the 3D layered solver). So M1 is already met, except the words 'partly two errors cancelling' (RCB-018).

**Decision.** Decision 3 stays as written (awaiting the maintainer's confirmation as a policy of the documents); A4 is consistent with it. **Maintainer** (his file, a history entry): leave the `CLAUDE.md` entry as it is; recommended at most a parenthesis '(partly a cancellation, audit A4)'. No document of `docs/` needs a change for M1.

## 23. The zone and near-edge warnings of the Lumped (A4 W2, W3)

**Decision.** Accept both: the zoned-Lumped warning (`checks.py` 866 to 872) leads with the hottest temperature (1.6 to 2.6 % of the rise on average, up to 7.6 %, against a fine-grid layered solver of the same idealisation, not independent), then the one resolved 3D cluster (-2.4 / +1.0 %, `REVIEW_A3`) and the placement noise of 1 to 3 points (validation 50); the via-effect figure moves to the docstring. The near-edge warning quotes 'up to 22 % against the FVM, 26 % against an independent 3D solver'. **Both after `fix/lumped-edge-first-link`**, which moves the near-edge level (mean -9.4 % to -2.5 %, worst -22.4 % to -8.6 % against the FVM, `docs/versions.md` A27): the texts are re-measured on that tree, so they go in A6. **Frozen numbers**: none.

## 24. The Analytic heatsink transient warning (A4 W1 and P1)

**Evidence.** Check 1 (section 33): on 35eeb773 the ten boards of validation 4.1, Analytic at its default 1 mm cell against the FVM at 0.5 mm (converged: 11.21 / 11.22 s at 0.5 / 0.25 mm on the 4 L board): -9.1 % (4 L, vias and a 300 W/m²K heatsink) to +3.2 % (2 L, vias and a heatsink beside); with the Analytic at 0.5 mm the fix's review printed -8.3 to +2.1 %. The key `analytic.HEATSINK_TRANSIENT_KEY` is '-8 % to +2 %'. The independent finite-element transient gives +1 to +4 % at 0.5 mm (five boards, `REVIEW_A4` 5).

**Decision.** The key becomes **'-9 % to +3 %'** (the default cell; 'against the converged FVM'), followed by the independent figure, as A4 W1 asks; test T4 of `REVIEW_A4` holds the 4 L board between -10 % and 0 % at the default cell. Whether the '5 to 7 % low' square-wave peaks of the same warning come from the readout point is no longer a question: the merged fix keeps the old point on those boards (flat top), so the peaks are the coupled-block limit; the text keeps them, re-run in A6. **Frozen numbers**: none.

## 25. The JEDEC calculator test (A5 M1)

**Options.** (a) Keep `tests/test_calculator_validation.py` asserting the datasheet's 32.5 K/W within 5 %, with a docstring saying it is not a validation; (b) replace it by a regression of the program's own reading of the 'as drawn' board and an order test of the four readings.

**Evidence.** The 'as drawn' board is not the board of its cited source; the four readings span 27.6 to 36.1 K/W (0.5 mm) and the datasheet's 32.5 lies between them, so a test against 32.5 asserts an agreement that is one reading among several (`REVIEW_A5` 2.1). A test against a published number must check that number on the published case (audit rule).

**Decision.** (b): (i) the 'as drawn' board held to the program's own value with a narrow band and a docstring 'regression of the program, not a validation: the board differs from ROHM 64AN113E', its value taken after `fix/drawn-copper-faces` (the board is drawn copper, whose faces that branch changes); (ii) `test_jedec_board_readings_keep_their_order` (B < C < A < D at 1 mm) in the release-gate set behind `PCBT_PUBLISHED_FULL=1` (decision 2) if it takes more than about 20 s, in the battery otherwise. When JESD51-7 is read, the board is redrawn and a one-sided test against the datasheet replaces (i) (A5 P2). **Frozen numbers**: none (the harness has no calculator board).

## 26. The JEDEC rows in the documents before JESD51-7 is read (A5 M2)

**Decision.** Keep them as `docs/audit-a5` writes them: the four-reading table labelled an indication, the claim of agreement withdrawn. Removing them would remove the evidence that the board drawing decides ±20 % of the power. **Maintainer**: obtaining JESD51-7 and JESD51-5 needs a free registration at jedec.org in his name (with JESD51-6 and JESD51-8, `REVIEW_A5` 7); only the registration is his, the redraw is the executor's (A5 P2).

## 27. The BGA 40 x 40 x 18 natural-convection heatsink (A5 M3, P7)

**Options.** (a) Keep 7.68 K/W (the catalogue value at a 75 K rise); (b) take 10.8 K/W (the same note, at 1 W); (c) rename the entry to name the rise.

**Evidence.** `defaults.json` already writes both values and the 75 K rise in the note; every other natural-convection entry of the library is the catalogue headline value, which manufacturers quote at a large rise. A part is linked to the library by the entry's name (`Heater.heatsink`), so a rename (c) breaks the link of a saved project. The program has no scaling of θSA with the rise (stated). Taking 10.8 (b) for one entry only would make the library inconsistent and move every project that uses it, while a value at 1 W (a rise of about 10 K) is as far from a typical 30 to 50 K rise as 7.68 is.

**Decision.** (a), keep the value and the name; the note starts with 'catalogue value at a 75 K rise (10.8 K/W at 1 W): at a small rise the heatsink is worse than this', the tooltip of the heatsink list and the guide carry one sentence that natural-convection θSA values of catalogues are quoted at a large rise. **Frozen numbers**: none; no user project moves.

**Who acts.** Executor in `fix/typical-values-marks` (decision 5, the same file and topic).

## 28. The other items of A5 (P1 to P10)

| item | decision | branch |
| :-- | :-- | :-- |
| P1 | decision 25 | `fix/calculator-audit-items` |
| P2 | after JESD51-7 (decision 26) | later |
| P3, P4, P9 | accept the texts of `REVIEW_A5` (help sensitivities -16 / -24 / -36 / -12 %, the JEDEC row as an indication, the ψJB band 'an approximation of the centre-pin point of TI SPRA953', '201 K at 0.25 mm is a lower estimate') | `fix/audit-texts` (A6) |
| P5 | refuse the 'top' point of the calculator for a part with a top path (θSA set), with the reason in the greyed control: ψJT of a datasheet is defined without a heatsink, so no power split makes the route valid (calculators.md 3 already says not to use it) | `fix/calculator-audit-items` |
| P6 | bring the code to the documented definition: `resistance_k_per_w = (T(P_run) − T(0))/P_run` (the part's own resistance); the window also shows the rise from the other parts when it is not zero; test with two heaters | `fix/calculator-audit-items` |
| P7 | decision 27 | `fix/typical-values-marks` |
| P8 | docstring '0.04 W' | `fix/calculator-audit-items` |
| P10 | decision 5 of `DECISIONS.md` | `fix/typical-values-marks` |

None moves a frozen number.

## 29. `docs/audit-s1` against `docs/audit-a5`: which text stays

**Evidence.** The merge of `docs/audit-a5` into `development` is clean, the merge of `docs/audit-s1` into `development` conflicts in `docs/theory.md` (two hunks), and after A5 it conflicts in `docs/calculators.md` 2.1 and `docs/validation.md` 29.2 as well (checked with `git merge-tree`). In both theory hunks (theory 6 'Where it is checked', the face-down paragraph of theory 8) `development` already holds S1's narrowed statements (Table 2 of YMC 1999, the length `A/P` of the face down) together with the later corrections of L1L5 and L4L9. In calculators 2.1 and validation 29.2, S1 wrote a provisional sentence (26.4 K/W with the plane, 'a decision for A5'); A5 replaces it with the four measured readings from a committed script (`study_jedec_board_readings.py`). S1's own numbers for the board with the plane (26.59 K/W in `REVIEW_S1` row 14, 26.4 in its calculators sentence) are not printed by a committed script; A5 prints 26.74 K/W for the same reading (0.5 mm), a difference of 0.6 % that was not traced.

**Decision.** `docs/theory.md`: the `development` side in both hunks. `docs/calculators.md` 2.1 and `docs/validation.md` 29.2: the `docs/audit-a5` side. Everything else of `docs/audit-s1` merges as it is (the corrected Lee and Yovanovich plot value, script, README and figure 08 of `paper-case-studies`, the face-down README, the power-calculator README sentence, which auto-merges beside A5's rewrite: read once after the merge for a repeated sentence). `REVIEW_S1.md` stays as the record; its row 14 numbers are superseded by `REVIEW_A5` 1 and its 'decision for the maintainer' is answered by decisions 25 and 26.

## 30. Correction of decision 6 of `DECISIONS.md`

`REVIEW_L1L5` finding 1 showed that the derivation written in decision 6 was wrong in two points: 0.742 is the coefficient of the linearised analytical model of Yovanovich and Teertstra with an assumed `C_T` = 2.31 (only the blending exponent is fitted to their CFD), an approximation of the same flat-plate boundary layer 11.7 % above the exact 0.664, not a coefficient of another length scale; and the uniform-flux mean is 0.688 (Lienhard eq. 6.72), 3.6 % above 0.664, not 'about 0.68, within 2.4 %'. The decision (keep 0.664) holds for the reasons L1L5 gives. A correction note is added under decision 6 in `DECISIONS.md` on this branch; theory 8 was corrected by L1L5. The docstring of `h_forced` is item P1 of `REVIEW_L1L5` (`fix/convection-warnings`).

## 31. The ordered fix plan (replaces the list of decision 9)

This replaces the list of decision 9 of `DECISIONS.md` for what is left, one branch at a time, each from `development` after the previous merge, each through executor, reviewer and maintainer with the whole battery. The shared-file rule holds (`fvm.py`, `fdm.py`, `blocks.py`, `lumped.py`, `analytic.py`, `checks.py`, `docs/theory.md`: one after another). Done since decision 9: `fix/thick-plate-warning-bound`, `fix/board-dock-write-back` (with decisions 10 and 11), `research/muzychka-case2-analytic`, `fix/analytic-transient-hot-point` (no number moved), the audit documents of A1, A2, A3, L1+L5, L4+L9 and `DECISIONS.md`.

**Step 1, the document merges** (no program change; decision 32).

**Step 2, tests and warnings that move no number and do not quote a model number:**

| # | branch | what | files | tests | pending | frozen |
| --: | :-- | :-- | :-- | :-- | :-- | :-- |
| 2a | `fix/published-case-tests` | decision 2 (A1 T1 to T5 in the battery, T6 to T8 behind `PCBT_PUBLISHED_FULL=1`); the printed-page tests of L1L5 T1 (Lienhard Ex. 8.1), T2 (Ex. 6.5), T3 (0.475 and Fujii-Imura), T4 (transition continuity), T5 (Table A.6 replaces the remembered values), T6 (radiation limit); A2 T2 (Muzychka 2004 eq. 50, one row); L4L9 T3 (a row at k 20, τ 0.1 of the eq. 21 test) | `tests/test_published_cases.py` (new), `tests/test_convection.py`, `tests/test_analytic_edge.py`, `CLAUDE.md` 'Commands' (the gate variable) | themselves | none | none (the program-value bands of T2 and T3 are re-baselined by the later model fixes, with the reason in the test) |
| 2b | `fix/audit-regression-tests` | A4 T1 (disc factors and 0.447 against the closed forms), A4 T2 (null-via zones within 6.1 %), A4 T5 (docstring -4.91 to -0.01 %), L4L9 T1 (peak independent of `EDGE_FILM_FLOOR`), L4L9 T2 (the disc against a radial solver committed under `tests/helpers/`), L4L9 P1 and P2 (comments of `fvm._cut_edge_film`, `cut_cell_study.count_at_floor`), A2 T1 (4-layer 1.6 mm board at 1000 W/m²K, 0.25 mm, between -5 % and -2 % of the stored FE limit 24.33 K) | `tests/`, `tests/helpers/`, comments of `fvm.py` | themselves | none | none |
| 2c | `fix/convection-warnings` | decisions 12 and 14; docstrings of `h_forced` (L1L5 P1, decision 30), `air_properties` (P2), `h_natural_vertical` (P6); guide sentence of P4 | `pcbthermal/api.py`, `pcbthermal/convection.py`, `pcbthermal/help/index.html`, theory 8 | `tests/test_convection.py`, `tests/test_help.py` | none | none (computed `h` only) |
| 2d | `fix/calculator-audit-items` | A5 P5, P6, P8 (decision 28); P1 part (ii) only, the order test (part (i) waits for step 3) | `pcbthermal/inverse.py`, `pcbthermal/gui/` (calculator window), `tests/test_calculator_validation.py`, `docs/calculators.md` | a calculator test with θSA set; a two-heater resistance test; the order test | none | none |
| 2e | `fix/typical-values-marks` | decision 5 (FR-4, emissivity, unsourced library notes), decision 27 (the BGA note), A5 P10 | `pcbthermal/data/defaults.json`, `gui/tips.py`, the guide, theory sources table | `tests/test_tooltips.py`, a library-note test | none | none (no value changes) |

2a to 2e touch different files (2c and 2d both touch the guide: in series); they may be reviewed in parallel but merged one at a time.

**Step 3, the model fixes, in series, each with its pending file (no record in two files):**

| # | branch | what | files | tests | pending | frozen |
| --: | :-- | :-- | :-- | :-- | :-- | :-- |
| 3a | `fix/drawn-copper-faces` (reviewed GO, 3 commits) | the exact fill and flow-based faces for drawn layers; on the same branch before its merge, or reopened on it after, the mixed imported and drawn board (decision 7; the memory law of `memory.drawn_run_bytes` counting only the drawn layers) | `copper.py`, `fvm.py`, `fdm.py`, `memory.py` | the branch's tests; the mixed-board test of decision 7 | `drawn-copper-faces.json` (its own) | FVM and FDM records of the drawn boards; three new harness boards in `expected_shifts_2.8.0.json` |
| 3b | `fix/lumped-edge-first-link` (planned, A27) | the side image in the first footprint-to-ring link; A4 T3 (re-baseline `tests/data/lumped_near_edge_cases.json` to the new sweep, on this branch because the fix moves it) | `lumped.py`, `checks.py` (the near-edge text's numbers re-measured) | the branch's tests; A4 T3 | one file that **replaces** `lumped-part-readout.json` | 51 Lumped records and 14 times to 63 % (A27 estimate) |
| 3c | `fix/block-exact-cover` (A1 P2) | `geometry.exact_coverage` for the metal-block polygon | `blocks.py` | a block whose edges cut cells against the area | `block-exact-cover.json` | block records whose edges cut cells (`finned_block` and any block off the grid lines) |
| 3d | only with a GO in time: `research/reduced-models-edge-laminate` (decision 15) and A18, A30, A32/A40 | otherwise stated limits of 2.8.0 | - | - | own file each | Analytic (and Lumped) records with `h_side` |
| 3e | `fix/face-film-half-slab` **last** | decision 8: `t/(2k)` in series with every face film (FVM, FDM, Analytic, Lumped, the metal block), measured on a block against the 3D solid | `fvm.py`, `fdm.py`, `blocks.py`, `analytic.py`, `lumped.py`, theory 1, 7.5 | case 2 column mean within 0.10 K (tightens 2a T3); the thick-plate bound drops its film term on a one-layer plate | none of its own: the refreeze folds it with the earlier files | every record (about 3e-5 K, more on block boards); row 'any', cap 1e-4 K for boards without a block |
| 3f | `release/2.8.0-refreeze` | `study_baseline_release.py --tag v2.7.1`, `study_run_suite.py`, `study_diff.py --strict` with `expected_shifts_2.8.0.json`, `v2.8.0.json`, the pending files deleted, the map hashes of `tests/test_results_views.py` | `tests/regression/data/`, `releases/regression-harness/reference/` | `tests/regression` at 2, 1, 0.5 mm | all folded | all |

**Step 4, the texts written once against the final models** (A6), after 3e and before or after 3f (they move no number):

| # | branch | what |
| --: | :-- | :-- |
| 4a | `fix/audit-texts` | decisions 15 (the edge-laminate warning of the reduced models), 16 (validation 32 row), 17 and 18 (the quantity and the cell), 20 (A2 W1 to W3, release blocker), 21 (the FDM pad warning, measured on 3a's tree), 23 (zones and near edge, measured on 3b's tree), 24 (the heatsink key '-9 % to +3 %' and A4 T4), A4 D1, D2 and P2 (the first-seconds limit of the step response and the animation: text only), A4 W4 (`copper.REDUCED_MODEL_WARNING` re-measured after 3b), A5 P3, P4, P9, A2 D1 to D3, the marks of decision 4; `pcbthermal/checks.py`, `analytic.py`, `copper.py`, the guide, tooltips, theory, models, validation |
| 4b | `fix/calculator-audit-items` reopened | decision 25 (i): the 'as drawn' JEDEC board held to the program's value after 3a and 3e |

**Step 5, the study scripts** (on their own research branches, by the 'no branch for its own sake' rule): `research/fdm-inset-edge` (L4L9 S1: `os.makedirs` before writing `out/independent.json`, the 4.5 GB peak in its header), `research/analytic-edge-and-transient` (A4 S1: `lib/calib_variants.py` reads `analytic._calibrated_dynamics`, removed in 2.6.0), A4 S2 (commit the scripts of the 29 + 17 via boards and the 54 unlike-layer boards) on the folders that own them. Any time; they move nothing in the program.

**Step 6, the features** of decision 9 step 5, then the release gate with `PCBT_PUBLISHED_FULL=1`.

**Maintainer**: the order is the plan of his release (as decision 9). The bookkeeping risk is the same: 3a to 3e each need a whole battery of about 50 minutes; a model fix that fails its review pushes 3e and the refreeze.

## 32. The document merge plan for `docs/audit-a4`, `docs/audit-a5`, `docs/audit-s1`

In this order, each with `--no-ff`, the quick document tests (`tests/test_docs.py`, `test_license_header.py`, `test_help.py`) after each:

1. **`docs/audit-a5`** (clean against 35eeb773). Keep as it is.
2. **`docs/audit-s1`**: `docs/theory.md` both hunks the `development` side; `docs/calculators.md` 2.1 and `docs/validation.md` 29.2 the `docs/audit-a5` side (decision 29); the rest as merged; read `research/power-calculator/README.md` once for a sentence said twice.
3. **`docs/audit-a4`** (clean against 35eeb773, and against the result of 1 and 2: no file in common with A5 or S1 except `docs/theory.md` and `docs/validation.md`, in other sections). **Before the merge, on the branch**: (i) replace '-9.1 to +0.6 %' (validation 4.1 audit note, the research README of `analytic-edge-and-transient`) by the numbers of check 1 (-9.1 to +3.2 % on 35eeb773, the Analytic at 1 mm) and say that the merged hot-point fix moved no frozen record; (ii) in `REVIEW_A4.md` mark P1 'done by `fix/analytic-transient-hot-point` (cae83792), no record moved; re-run in DECISIONS_2.md section 33, check 1' and M1 'already met by the CLAUDE.md entry (decision 22)'. Then read validation 4.1 and 32 once after the merge: A4 and L4L9 both added audit notes there (no textual conflict, but a reader must not find two notes saying the same thing with different numbers).
4. **`docs/audit-decisions-2`** (this branch).

## 33. Checks run for this file (on `development` 35eeb773)

1. `releases/2.8.0/audit/scripts/study_a4_local_transient.py` of `docs/audit-a4`, copied to the scratchpad and run against the program of 35eeb773 (`PCBTHERMAL_CONFIG` private; 42 s, 1.59 GB peak). Time to 63 % of the Analytic (1 mm) against the FVM (0.5 mm): plain 2L +0.6 %, 1 via +0.1, vias 4x4 +0.6, sink under +0.0, sink beside -0.7, vias+sink under -0.1, vias+sink beside +3.2, plain 4L +0.6, 4L vias+sink under -9.1 (FVM 11.21 s at 0.5 mm, 11.22 s at 0.25 mm), 2L h_side 50 vias+sink -0.3 %. Lumped -41.4 to +13.3 % (as A4).
2. The up-face law against Raithby-Hollands (`Nu_t = 0.560 Ra^(1/4)/[1 + (0.492/Pr)^(9/16)]^(4/9)`, `Nu = 1.4/ln(1 + 1.4/Nu_t)`, `Pr` 0.71; one line of Python): the ratios of decision 12.
3. Top-face Rayleigh numbers with `pcbthermal.convection.air_properties` and `rayleigh` at the film temperature, `L = A/P`, ambient 25 °C, rises 5 / 10 / 20 / 40 K: 30 x 20 mm 100 / 193 / 358 / 618; 60 x 40 mm 804 / 1.55e3 / 2.87e3 / 4.94e3; 100 x 80 mm 5.11e3 / 9.82e3 / 1.82e4 / 3.14e4; 160 x 100 mm 1.36e4 / 2.61e4 / 4.83e4 / 8.34e4; 233 x 160 mm 4.96e4 / 9.55e4 / 1.77e5 / 3.05e5.
4. `git merge-tree --write-tree` of `development` with each branch and in sequence (decision 29, decision 32); the pending folder of `development` holds only `lumped-part-readout.json`; `git show cae83792` (the hot-point fix removed its pending file).

## Summary

| # | decision | moves frozen numbers | maintainer |
| --: | :-- | :-- | :-- |
| 12 | face-up Ra warning 1e2 to 1e7, worded by the agreement with the printed law | no | no |
| 13 | keep the outline perimeter for `A/P` | no | no |
| 14 | add the Reynolds warning (100 to 1e5), as a hot-side note | no | no |
| 15 | edge laminate of the reduced models: a stated limit in 2.8.0, a research branch first | no (in 2.8.0) | only if he wants it in 2.8.0 |
| 16 | validation 32 keeps the band-off numbers plus the band-on independent row | no | no |
| 17 | quote the hottest point | no | no |
| 18 | quote the converged error first, the 1 mm one second | no | no |
| 19 | = decision 4 | no | yes (decision 4) |
| 20 | edge-laminate warning texts: release blocker, rewrite in A6 | no | no |
| 21 | FDM small outer pads: limit plus a live warning, after 3a | no | no |
| 22 | decision 3 stands; the CLAUDE.md sentence already names its reference | no | yes (his file; decision 3) |
| 23 | zone and near-edge texts: accept, after 3b | no | no |
| 24 | heatsink transient key '-9 % to +3 %' | no | no |
| 25 | JEDEC test: program regression plus order test | no | no |
| 26 | keep the JEDEC rows as an indication | no | registration at jedec.org |
| 27 | keep the BGA value and name, say the rise | no | no |
| 28 | A5 P1 to P10 as the table | no | no |
| 29 | theory: development; calculators 2.1 and validation 29.2: A5 | no | no |
| 30 | correction of the derivation of decision 6 | no | no |
| 31 | the ordered plan (steps 1 to 6) | 3a to 3f | yes (the plan of his release) |
| 32 | merge A5, then S1 (theory: development; 2.1 and 29.2: A5), then A4 after its numbers are updated | no | no |

## What was not verified here

The numbers of A2, A4 (except check 1), A5, L1L5 and L4L9 were read, not re-run. The series edge film of decision 15 is not prototyped. The rule of decision 21 rests on one board. The order test of decision 25 was not timed. The 0.6 % between S1's and A5's reading of the board with the plane was not traced (both scripts were not run here). The merges of decision 32 were checked with `git merge-tree` only; the semantic duplicates in validation 4.1 and 32 after the A4 merge were not resolved here.
