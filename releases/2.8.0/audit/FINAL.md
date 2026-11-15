# The fine-comb re-review of 2.8.0: closing document

This document closes the re-review that the maintainer asked for after a run of errors in the documents of the program ('we cannot have these errors'). It gathers what the audit tracks, the decisions, the fix branches and the final code-against-theory review found and did, what remains open, and how far each part of the program can be trusted. It adds no measurement of its own: every number below is quoted from a file of the repository, named next to it (section numbers of `docs/validation.md` are written 'validation N', of `docs/theory.md` 'theory N'). The program state it describes is `development` at 7a3ca02e (2.7.1 plus every 2.8.0 branch merged so far).

The source files are in this folder (`CLAIMS_REGISTER.md`, `claims.csv`, `formulas.csv`, `ASSIGNMENTS.md`, the `REVIEW_*.md` files, `DECISIONS.md`, `DECISIONS_2.md`, `DECISIONS_3.md`), in `releases/2.8.0/final-review/` (`PART_1A.md` to `PART_2C.md`) and in `releases/2.8.0/reviews/` (the reviews of the fix branches).

## 1. Summary

1. **What it was.** Every quantitative claim of the theory, the validation, the models document, the calculator document, the warnings, the user guide and 66 research folders was registered (1482 claims, 212 of them at the highest risk; `CLAIMS_REGISTER.md` 1), and every formula, constant and correlation of the program (100 rows; `ASSIGNMENTS.md`, `formulas.csv`) was compared with the printed page of its source, read on the page image wherever the source is in the papers library (section 4.1 lists those that are not).
2. Each claim was re-checked against something that does not share the program's assumptions (a closed form, a published case, the independent layered solver, finite elements), with the compared quantity (point maximum, cell mean, node, face, column mean) fixed on both sides.
3. **What it found.** No formula of the program was coded differently from its printed source (one constant from memory, the turbulent branch of the top face, was replaced by the printed one). What was wrong was mostly in the documents: numbers measured on earlier trees or against references later found hot, quantities that were not the same on both sides, agreements that were two errors cancelling, and claims credited to the program that came from another solver.
4. It also found real defects of the program (the Board settings dock writing back clamped values, the Analytic transient read at the wrong point, the metal-block cover, the drawn-copper faces, the Lumped first link near a side, a thick-plate warning that was not a bound, the film through half the copper layer), each fixed on its own branch with a regression test and the whole battery.
5. **What was done.** Eighteen fix branches and one feature branch were merged since 2.7.1 (`git log --first-parent v2.7.1..development`), each reviewed; four pending files hold the frozen records that moved on purpose; the published cases entered the test battery.
6. The final review read the whole theory, the models document, the validation and every user-facing text against the code; it found no disagreement of physics, corrected the stale numbers and made the implicit rules explicit.
7. **What remains.** Sources that are not in the library (mostly paid papers and the JEDEC board standards), studies read but not re-run (the finite-element references), stale pictures, a short list of text and test items, and a few decisions of the maintainer.
8. No claim of the project rests on a physical measurement: the absolute heat transfer coefficients and the Power Calculator against real parts remain unmeasured.
9. The trust table of section 5 says, area by area, what is now well founded and what would raise the rest.
10. Section 7 says in plain words what this means for a user.

## 2. What was wrong

### 2.1 Wrong or misleading statements in the documents

The most important ones, with the old and the corrected statement. Each was corrected in place (or marked superseded with the replacement named) on the branch of the review cited.

| statement | old | corrected | evidence |
| :-- | :-- | :-- | :-- |
| Accuracy of the Analytic on uniform boards | 135 boards, mean 0.117 %, maximum 0.324 % against the FVM | that FVM had no laminate edge band; against the program as shipped -0.09 to -11.40 %, against the independent 3D solver -0.10 to -14.89 % (3.2 mm board, corner part, 200 W/m²K; within 1.4 % at the default 10 W/m²K) | `REVIEW_L4L9.md` 4 and 5; `REVIEW_A4.md` 4.1; validation 4.1 note |
| The thick-plate bound | 'the bound `q'' t/(2k)` is above the real effect in every case', 'never fires on the cases the program is built for' | the 'real effect' was one program model minus another; on case 2 of Muzychka, Culham and Yovanovich (2003) the 10 W source was silent with a shortfall of 2.90 K (4.0 % of its rise), the column of the case-2 plate read 1.77 K under a 0.93 K bound, and on two thick plates the quoted 9.4 and 4.7 K stood against 17.9 and 14.9 K measured | `REVIEW_A1.md` 2.2; `reviews/thick-plate-warning-bound.md` finding 1; validation 22.1 |
| The JEDEC 2s2p calculator row | the calculator 'reproduces the datasheet' (+2.9 %), the exposed pad '31.9 against 32.5 K/W' | the board was drawn without the 70 µm backside plane its cited source prints and with vias joined to every layer; drawn as printed the model read 27.64 K/W (the calculator +18.1 %, the unsafe side); the four readings of the board span the datasheet value, so the row is an indication, not a check (today 27.0 to 36.6 K/W over the four readings, the board as printed 27.9 K/W) | `REVIEW_A5.md` 2.1; `REVIEW_S1.md` rows 14 and 20; `DECISIONS_2.md` 25 and 26; `CHANGELOG.md` [Unreleased], Fixed; `docs/calculators.md` 2.1 |
| Muzychka case 2 'confirms the effect' | the program's one-layer models read 2.9 to 5.6 K low, '67 to 89 % of the bound, which confirms the effect' | the program reads a node (the column mean, with the film acting on it) against the surface the paper reports; two terms: through the thickness 2.06 / 4.70 / 3.82 / 2.94 K and the film on the node 0.84 K; the sentence is withdrawn; validation 22.1 also omitted that the program reads the cross 2.1 % and case 1 (a) 8.4 / 9.0 % of the rise low | `REVIEW_A1.md` 1 and 3; `research/muzychka-case2-analytic` README 8; validation 22.1 |
| The edge-laminate error on one board | four sets for one quantity: -0.8 / -2.5 / -5.1 / -8.9 %, -1.3 / -3.9 / -7.2 / -11.7 %, -0.4 / -1.4 / -3.2 / -6.0 %, -0.4 / -1.4 / -3.4 / -6.2 % at 200 / 500 / 1000 / 2000 W/m²K | the first two used references that read hot, the third an early finite-element run; against the hottest point of converged finite elements -0.6 / -1.7 / -3.5 / -6.5 % at 0.25 mm, about -0.8 / -2.2 / -4.2 / -7 % converged in the cell; on cut gaps the error grows as the cell shrinks, so 'a smaller cell reduces the cool error' was wrong; the warning's claim that the 3.2 mm figures were 'too pessimistic' was false (their graded reference is within 0.06 % of finite elements) | `REVIEW_A2.md` 2.1, 2.2, 2.4; `DECISIONS_2.md` 17, 18, 20; validation 46.1 |
| Validation 32 (cut cells) | the film floor 0.25 'binds from about 1000 W/m²K' and moves the peak 0.06 to 0.15 K; jump -0.09 / -0.02 K; spread 0.09 / 0.07 K | described the program of 2.6.0: since 2.7.0 the floor never acts in the FVM (peak identical for floors 0.05 to 0.5); with the laminate band the jump is +0.54 / +0.92 K and the spread 0.71 / 0.87 K; the section is marked stale and keeps its band-off numbers with the one independent band-on row (-1.3 % of the rise) | `REVIEW_L4L9.md` 3 and 5; `DECISIONS_2.md` 16 |
| The Lumped first link, interior parts | 'about 2 points' hotter for a part away from the sides | +3.8 points of the rise on average at 0.5 mm (+0.5 to +6.4), +2.2 at 1 mm | `research/lumped-edge-link` README 3.3 and 4.7; validation 53.4 |
| The thick-plate warning on case 2 | 'the warning fires on all four sources' (the planned test of the published cases) | true only while the bound carried the ambient film term; since the film is in the model, 3 of the 4 sources warn (the 10 W source, 3.3 K, is at 4.7 % of its rise, under the 5 % limit, and its real gap, 2.0 K, is under its bound) | `DECISIONS.md` 2; validation 55.4; `research/muzychka-case2-analytic` README, notes after 8.8; `tests/test_published_cases.py` |
| Seri Lee's plate | 'the plate model reproduces Seri Lee' | the numbers came from a re-implementation inside a study and from the independent solver; `blocks.py` had never been run on it; now run: +0.6 / -0.8 / -4.7 % against the printed values and within 0.2 % of the exact thin-plate series (the -4.7 % is the article's own corner rule) | `REVIEW_A1.md` 2.1; theory 7.5 |
| The 3D solid against finite elements | '+8 % on a heater pad', 'the FVM +2.9 % on a one-sided pad' | the 1 mm finite-element reference was 1.1 to 2.4 % cold; against converged finite elements the 3D solid at 1 mm reads +4.9 % (10 mm pad) and +2.3 % (20 mm pad), the FVM +0.5 / -1.1 % | `REVIEW_A2.md` 2.3; validation 3.1 |
| Via on partly covered copper | the FVM reads the via effect 31 to 47 % low, 45 to 68 % low, 3 to 4 times high | numbers of 2.5.x against a smeared reference; now 55 to 85 % low in the FVM and 22 to 73 % in the FDM against a committed resolved reference, the part up to 11.5 % of its rise too hot | `REVIEW_A3.md` 2 items 2 and 3; validation 30.1, 34.2 |
| The Shen via array | the FVM +0.7 % of the unit cell | the program's hottest point against the solver's mean, with the old barrel: a cancellation; like for like -1.5 % | `REVIEW_A3.md` 2 item 5; validation 18.2 |
| Via couplings of the FVM matrix | 832 / 864 positive entries, up to 2.2 times the diagonal | numbers of 2.5.x; on 2.7.1 432 / 432 and 1872 / 2448, at most 0.023 of the diagonal (40 to 100 times smaller) | `REVIEW_L12.md` 2 item 1; theory 2.2 |
| Copper conductivity | 'Lienhard Table A.1 (copper)' | the table prints 398 W/mK for pure copper at 20 °C; the program's 385 has no recorded source (it reads the example board 1.5 % hotter, the safe side) | `REVIEW_L12.md` 2 item 2 |
| Forced convection 0.742 against 0.664 | 0.742 'a coefficient fitted to their CFD on another length scale' | 0.742 is the coefficient of a linearised model with an assumed constant, 11.7 % above the exact 0.664 for the same plate; the uniform-flux mean is 0.688, 3.6 % above; the decision to keep 0.664 holds | `REVIEW_L1L5.md` 2 item 1; `DECISIONS_2.md` 30 |
| Uncertainty of the heat transfer laws | '20 to 30 % on a board with hot spots' | no source; the printed spread of the plate laws is about ±20 % vertical and ±50 % horizontal, and the hot spots change the heat a face loses by under 1 % | `REVIEW_L1L5.md` 2 item 3 |
| Analytic per-layer edge | worst 4.07 %, mean 0.90 % | against the FVM of 2.5.x; on 2.7.1 worst 4.91 %, mean 1.19 %, one layer -7.83 % | `REVIEW_A4.md` 3 and 8; `PART_1B.md` 1 |
| The Lumped near a side | -6.6 % mean [-22.0, +1.4] | -7.4 % [-22.2, -0.8] on 2.7.1 (and -2.7 % on the flagged parts after the first-link fix) | `REVIEW_A4.md` 4.2; validation 53 |
| Fast waves, four layers | node error 5 to 7 times from 50 Hz to 1 kHz | 3.6 to 5 times since the physical slabs of 2.7.0; no decision moved to the unsafe side; the Lanczos factor of theory 10.5 was written `sinc(k/N)` where the code uses `sinc(2k/N)` | `REVIEW_A5.md` 2.3, 2.5 |
| Calculator sensitivities | three different sets in three places (-13 / -24 / -34 / -11 % among them) | the printed run: -16 / -24 / -36 / -12 % | `REVIEW_A5.md` 2.2; `PART_2C.md` 1 |
| Sub-gap bounds | '8 sub-gaps of a 1.6 mm gap need 0.19 mm or less, 16 need 0.09 mm or less' | below 0.229 mm (d / 7) and 0.107 mm (d / 15) | `PART_1A.md` 1.4; `PART_2B.md` 1 |
| A plot value of Lee and Yovanovich (1989) | 89.0 K (the glass plate, second peak) | 79.5 to 80 K on the page image; the study's solver moved from -6.7 % to +4.5 % | `REVIEW_S1.md` row 1 |
| The SOR relaxation factor | 'below the optimum the sweeps grow slowly, above it steeply' | the opposite near the optimum (1634 against 1281 sweeps at -0.015 / +0.015 on the example board at 1 mm) | `REVIEW_L12.md` 2 item 4 |

The pattern behind them (`CLAIMS_REGISTER.md` 4): the compared quantity was not fixed; the reference was the program itself or moved with it (511 of 1482 claims rest on the program against itself, 99 of the 212 at the highest risk); a number corrected in one place stayed uncorrected elsewhere; tests asserted a known defect; warning thresholds were never tested at the threshold.

### 2.2 Real defects of the program, found and fixed

| defect | size of the effect | fixed by | evidence |
| :-- | :-- | :-- | :-- |
| The Board settings dock rewrote every field from its boxes on a single edit, and the boxes clamped what they had loaded | a 10 mm copper plate became 210 µm and the run read 991 to 1138 °C with no warning; the review found the same kind of path in the Simulation dock after an undo, the Power profile page (a period of 1/3 s rounded), an integer box beyond a C int, and four dialogs | `fix/board-dock-write-back` (undo now keeps the solver options; Preferences boxes widen) | `reviews/board-dock-write-back.md`; `DECISIONS.md` 10, 11 |
| The Analytic transient of a part over vias or heatsinks was read at the hot point of the board without them | -21.7 % at 0.3 s and a wave swing -11.2 % against finite elements; after the fix the plateau -0.04 % and -7.9 % at 0.3 s; no frozen record moved | `fix/analytic-transient-hot-point` | `REVIEW_A4.md` 5; `reviews/analytic-transient-hot-point.md`; `CHANGELOG.md` Fixed |
| The cover of a metal block was sampled 4 x 4 and, on an outline board, the board share of a cut cell was counted twice | block area off by -0.34 to +0.88 %, contact 1.3 to 1.6 % short; the first version of the fix lost 0.13 to 0.33 W of 3 W outside the balance (caught by its review); the hottest point moves at most 0.15 K (FVM) and 0.21 K (FDM) | `fix/block-exact-cover` | `REVIEW_A1.md` 2.3 item 1; `CHANGELOG.md` Changed; validation 54 |
| Drawn copper with a cut cell read its fill and faces by an approximate rule; a board with imported copper read its drawn layers by it silently | against finite elements, stripes with a pad -8.0 to -0.6 % (FVM, 1 mm), the FDM stripes -12.9 to -1.8 %, the FDM small outer pad -10.6 to -3.7 %; the mixed board was up to 10 % cool at 1 mm; the review also found the memory search for the cell that fits refused its own answer | `fix/drawn-copper-faces` | `reviews/drawn-copper-faces.md`; validation 51, 51.7; `CHANGELOG.md` Changed |
| The Lumped first link from the footprint to the first ring ignored the sides of the board | flagged parts -9.4 to -2.7 % of the rise on average against the FVM, worst -22.2 to -7.5 %; against an independent 3D solver a part touching a side -9.9 to -3.1 %, in a corner -15.9 to -3.3 % | `fix/lumped-edge-first-link` | validation 53; `CHANGELOG.md` Changed |
| The Lumped part rows read the painted node, not the part's own peak | about 10 % of the rise too cool for a lone part (9 to 15 % on the review's boards); single parts now -0.2 to -5.8 % of the FVM | `fix/lumped-part-readout` | `reviews/lumped-part-readout.md`; validation 48 |
| The face film of a copper node did not pass the half copper layer | case 2 read 0.85 to 0.89 K below the 3D column mean, now within 0.10 K; ordinary PCB copper about 5e-7 of the rise | `fix/face-film-half-slab` | `DECISIONS.md` 8; validation 55; `CHANGELOG.md` Changed |
| The turbulent branch of the top face (`0.15 Ra^(1/3)`, from memory) | 7 % above the printed law and a +6.4 % step at Ra 1e7, now -0.6 %; no board reaches it | `fix/horizontal-face-laws` | `REVIEW_L1L5.md` 2 item 4; `DECISIONS_3.md` 35 |
| The thick-plate warning was not a bound on boards of two or more layers, dropped the film term with computed coefficients and used the wrong film for a block | two plates 17.9 / 14.9 K measured against 9.4 / 4.7 K quoted (the 40 mm source silent at 13 % of its rise) | `fix/thick-plate-warning-bound` | `reviews/thick-plate-warning-bound.md` findings 1 to 3 |
| The top-face Rayleigh warning (1e4 to 1e11) was silent where the face-up law reads 9 to 22 % above the printed Raithby-Hollands law | now 1e2 to 1e7, plus a hot-side note for forced air outside Re 100 to 1e5 | `fix/convection-warnings` | `DECISIONS_2.md` 12, 14 |
| The Power Calculator's board resistance included the rise of the other parts; the 'top of package' route was offered for a part with a heatsink on top | resistance now the part's own `(T(P) - T(0))/P`; the route refused with its reason | `fix/calculator-audit-items` | `REVIEW_A5.md` 2.5; `DECISIONS_2.md` 28 |
| The OCR map counted verified pages only from a notes file | verified pages 33 to 521 of 612 essential pages on the real library | `fix/ocr-map-reading-status` (developer tool) | `reviews/ocr-map-reading-status.md` |
| The battery wrote window settings into the maintainer's own preferences, and an order-dependent GUI test failed in 2 of 3 batteries | tests now use a private settings store per test | `fix/profiles-cut-overlay-flake` | `reviews/profiles-cut-overlay-flake.md` |
| Live warning texts quoted numbers measured against references later found hot (via near a strong edge, via contact, fast waves, reduced-model edge laminate) | FDM via effect 2 to 20 % low at 1 mm, 3D solid 10 to 26 % high at 0.5 mm (instead of '4 to 10 %' and '19 points'); the other texts as in 2.1 | `fix/via-and-edge-warning-texts`, `docs/final-review-2c` | `PART_2C.md` 1; validation 49.1 |

### 2.3 Not defects, but limits the audit made visible

| limit | size | evidence |
| :-- | :-- | :-- |
| The FDM on a small outer pad | -3.7 % at 1 mm with an edge of 10 W/m²K (-5.1 % at 200, -8.5 % at 1000) since the drawn-copper faces; it was -10.6 %; cause not separated | validation 51.7; `PART_2B.md` 3; `REVIEW_A2.md` 2.2 item 5 |
| The Lumped first link keeps the plain link above 3600 footprint cells | a jump in the near-side deficit at that size (30 mm at 0.5 mm) | `CHANGELOG.md` Changed; theory 5 |
| The absolute heat transfer coefficient | every law coded as printed, but the printed horizontal-face results scatter by about ±50 % and no coefficient was compared with a measurement | `DECISIONS_3.md` 34; `REVIEW_L1L5.md` 2 item 3; theory 8 |
| FR-4 conductivity in the plane (0.9 W/mK) | no source; a 6 mm part on a bare two-layer board reads +25 % / -15 % of its rise with 0.6 / 1.2 W/mK (±0.3 % on the example board with copper) | `REVIEW_L12.md` 1 and 2 item 3 |
| Emissivity 0.9 | no source; +6.5 % / +15.3 % of the rise at 0.6 / 0.3 on the example board with computed coefficients | `REVIEW_L12.md` 1 |
| The first seconds of a time result | every layered model rises too slowly at first: 58 / 30 / 9 % too low at 0.3 / 1 / 3 s against an independent finite-element transient (one node per layer holds copper and half the gap); plateau and time to 63 % within -0.7 to +3.9 % | `REVIEW_A4.md` 5; `PART_2C.md` 1 |
| The edge laminate in the Analytic and the Lumped | the Analytic -2.6 to -14.9 % of the rise against an independent 3D solver at 200 W/m²K (within 1.4 % at 10 W/m²K); warned | `DECISIONS_2.md` 15; `PART_1B.md` 1 |
| The via at a copper corner | two independent resolved references disagree by 25 to 39 % (quarter 5.70 against 7.91 K, track 10.34 / 10.89 against 13.60 K); the sign of the FDM error there is not settled | `REVIEW_A3.md` 2 item 1 |
| Small imported parts | the reference at 0.25 mm is not converged, so every error quoted on 0402-size parts is a lower bound | `REVIEW_A5.md` 3 |
| The Analytic tile Green function | capped at 64 modes: about 1 % of the via effect | `REVIEW_A3.md` 2 item 9 |
| The copper conductivity 385 W/mK | 1.5 % of the rise hotter than 398 W/mK on the example board (safe side); kept, marked typical | `REVIEW_L12.md` 1 and 5; `CHANGELOG.md` Changed |

## 3. What was corrected

The branches merged into `development` since v2.7.1 that came from the audit, its decisions or the reviews of 2.8.0, in merge order. 'Battery' is the whole test battery recorded in `CLAUDE.md` (project structure, the line of the test count) on the merge named; where a branch has no count of its own, the next recorded battery covers it. Frozen records are held by the pending files of `tests/regression/data/pending/` until the refreeze of 2.8.0.

| branch | what | frozen records moved | battery |
| :-- | :-- | :-- | :-- |
| `fix/lumped-part-readout` | the Lumped part rows read the part's peak | 51 Lumped records (file later replaced by `lumped-first-link-edge.json`) | 3516 passed, 9 skipped, 2 xfailed |
| `fix/via-and-edge-warning-texts`, `feature/element-tree-filter` | via clauses of the strong-edge warning; the filter box | none | 3552 passed, 9 skipped, 2 xfailed |
| `fix/profiles-cut-overlay-flake`, `fix/ocr-map-reading-status`, `fix/analytic-transient-hot-point`, `fix/thick-plate-warning-bound`, `fix/board-dock-write-back`, with the audit documents of the claims register, the first decisions and the reviews of thick plates, vias, convection, cut cells and edge laminate (`docs/audit-claims-register`, `docs/audit-decisions`, `docs/audit-a1`, `-a2`, `-a3`, `-l1-l5`, `-l4-l9`) | as section 2.2; documents corrected or marked superseded | none | 3606 passed, 9 skipped, 2 xfailed |
| `fix/muzychka-case2-tests`, `docs/audit-decisions-2`, `docs/audit-a4`, `docs/audit-a5`, `docs/audit-s1`, `docs/audit-l12` | research tests; the Lumped, Analytic, transient, calculator, published-source and numerics reviews | none | no count of their own (documents and research tests) |
| `fix/published-case-tests`, `fix/convection-warnings`, `fix/calculator-audit-items`, `docs/h-laws-theory`, `fix/horizontal-face-laws` | published cases in the battery; convection warnings; calculator items; theory 8 law by law; the turbulent top branch | none | no count of their own; covered by the next battery (3617) |
| `fix/drawn-copper-faces`, `fix/typical-values-marks` | drawn copper as imported copper, the mixed board; typical values marked | 8 records and 8 times (`drawn-copper-faces.json`) | 3617 passed, 75 skipped, 2 xfailed |
| `fix/lumped-edge-first-link` | the images of the sides in the Lumped first link | 51 records and 12 times (`lumped-first-link-edge.json`, replacing `lumped-part-readout.json`) | 3633 passed, 75 skipped, 2 xfailed |
| `fix/block-exact-cover`, `research/lumped-edge-link` | exact block cover | three Analytic records of the finned block, +0.09 K (`block-exact-cover.json`) | 3724 passed, 11 skipped, 2 xfailed |
| `fix/face-film-half-slab`, `research/drawn-copper-faces` | the film through the half copper layer | 204 records and 29 times, all hotter, median 2e-5 K, at most 0.040 K (`face-film-half-slab.json`) | 3748 passed, 11 skipped, 2 xfailed |
| `docs/final-review-1a`, `-1b`, `-2a`, `-2b`, `-2c` | theory, models, validation and every user-facing text against the code | none (text only) | targeted runs: 827 passed (documentation gate, part 2b); 1416 passed, 4 skipped on 42 test files and 153 frozen records at 2 mm (part 2c) |

The counts are from `CLAUDE.md` and the commits that recorded them (`git log --first-parent v2.7.1..development`); the targeted runs of the final review are `PART_2B.md` 6 and `PART_2C.md` 5. The skipped count moved from 9 to 75 and back to 11 with the presence of the local library of real boards on the machine, not with the program (`CLAUDE.md`).

Tests added by the audit (`CHANGELOG.md` [Unreleased], Tests): `tests/test_published_cases.py` (Seri Lee's plate through `blocks.py`, the cross and cases 1 (a), 1 (b) and 2 of Muzychka, Culham and Yovanovich, each one-sided or in a narrow band around the program's own value), `tests/test_convection_published.py` (Lienhard Examples 8.1 and 6.5 with the book's properties, the face-down constant, Table A.6), the via-coupling counts and the orders of the theta method, the calculator regression and the order of the four JEDEC readings, and the regression tests of every fix branch named in section 2.2.

## 4. What remains

### 4.1 Sources not in the papers library

Every statement that rests on these is checked as a derivation, through a reprint in a source that was read, or by the program, and is marked so in the bibliography. Lists in `REVIEW_A1.md` 6, `REVIEW_A3.md` 6, `REVIEW_A4.md` 9, `REVIEW_A5.md` 7, `REVIEW_S1.md` 3, `REVIEW_L1L5.md` 6, `REVIEW_L4L9.md` 8, `REVIEW_L12.md` 6 and `DECISIONS_3.md` ('What was not verified').

* Convection: Churchill and Chu (1975), Churchill (1977, the blend exponent), Lloyd and Moran (1974), Goldstein and Lau (1983), Raithby and Hollands (the handbook chapter), Incropera and DeWitt. Their formulas are read through Lienhard (2024) and Yovanovich and Jafarpur (1993).
* Vias and wells: Peaceman (1978, 1983), Krogh (1919), Dietz (1965). The constants are computed and verified numerically; only the attribution rests on them.
* Plates, images and closed forms: Carslaw and Jaeger, Maxwell (the self distance 0.447, checked by its closed form), Seri Lee (1998) as a PDF (read as a web page: numbers read, equations not).
* Packages and boards: JEDEC JESD51-7 and JESD51-5 (the 2s2p board and its vias), JESD51-6, JESD51-8 (free registration at jedec.org, in the maintainer's name).
* Fins and channels: Bar-Cohen, Iyengar and Kraus (2003), Yazicioglu and Yuncu (2009), Tari and Mehrtash (2013), Da Silva and others (2012), Dogan and Dogan (2017).
* Others cited by studies: Guenin (2004), Sampson (2017), Nexperia AN11261, de Vahl Davis (1983), Patankar (1980), George (1973), Young (1950, 1971), Varga (1962), Davis (2006), Papac, Gibou and Ratsch (2010); the journal versions of Johansen and Colella (1998) and Barrett and others (2022) (the library holds the report and the preprint); the source of the Lee-Yovanovich conjugate plate was not identified among the library's files.

A local, untracked source map of where each of these is reprinted in the library exists beside the papers (`papers/notes/`); it is not part of the repository.

### 4.2 Read but not re-run

* The finite-element references (validation 3, 3.1, 28, 36, 40, 43, 44, 46, 47 and `research/independent-fem-extensions`, `research/transient-reference-boards`): their tools need the folder's scratch environment (`PART_2B.md` 5; `REVIEW_A4.md` 10).
* The 3D solid columns of validation 1, 2, 2.1 and 3 (8 to 11 GB on the example board at 0.5 mm) (`PART_2B.md` 5).
* The 29 + 17 via boards of validation 18.1 and the 54 unlike-layer boards of validation 4.1: no committed script (`REVIEW_A3.md` 6; `REVIEW_A4.md` 7).
* The 3D references of the fast-wave folder, the JEDEC board at 0.25 mm, a converged reference for small imported parts and the transient of an imported window (`REVIEW_A5.md` 7).
* The Lumped tables measured before the images of the sides: validation 18.1, 31, 48, the zoned-Lumped warning numbers and the imported-copper warning of the reduced models (`PART_2B.md` 3; `PART_2C.md` 3).
* The sections of validation listed 'not re-run' with their tree in `PART_2B.md` 2 and in the head note of `docs/validation.md`.
* The FDM small outer pad at 2000 W/m²K after the drawn-copper faces (`PART_2B.md` 3).

### 4.3 Stale pictures

* The editor screenshots, which lack the Filter elements box: `docs/images/editor.png`, `editor_warnings.png`, `editor_imported_dark.png`, `editor_overlay.png`, `editor_background.png`, `outline.png` and the guide's own copies; `results_summary.png` and `results_summary_imported.png` (warning wording changed) (`PART_2C.md` 3; `reviews/element-tree-filter.md`). They are regenerated and looked at in the documentation review of the release.
* Figure 22 of theory 11 (old numbers of the verification ladder) and figure 41 of theory 7.1 (the block network without the half block and half copper of the film term); both captions say so (`PART_2A.md` item 2; `PART_1B.md` 3).

### 4.4 Items queued

From the final review (`PART_1A.md`, `PART_1B.md` 3, `PART_2A.md`, `PART_2B.md` 3, `PART_2C.md` 3); those already done by a later part are left out:

* Test and code docstrings: `tests/test_analytic_perlayer.py` (it still says -4.07 to +0.06 % where the measurement is -4.91 %), `tests/test_maximum_principle.py` (a cold spot of '8 to 14 K' where the test prints 5.49 and 12.80 K), the `memory.VIA_CELLS_REF` comment against theory 2.7, the `gerber/parts.py` module docstring ('0402 to 1206', the table starts at 0201).
* Documents: a note in validation 4.1 with the -4.91 % of the 48 boards on the shipped FVM; `docs/models.md` 2.3 ('thin heaters +9.5 %', validation 2 now +8.4 %); the copper-fill gain sentence of the user guide (validation 18.1); the prose under validation 12 A and B; validation 29.2 body columns; splitting the 3D columns of `validation_study.py` from the program columns so they can be re-run on a busy machine.
* Studies: the hot cases of aspect ratio 3 and the 1 mm part of validation 31, re-measured after the images of the sides; the zone and imported-copper warning numbers re-measured on the current tree; the finite-element run that settles the via at a copper corner (`REVIEW_A3.md` 4); the scripts of the via boards of validation 18.1 committed and re-run against a resolved reference (`REVIEW_A3.md` 4).
* Warning wording: the bottom-face Rayleigh warning calls the face 'turned down' also for a board colder than the air (`PART_1B.md` 3); the calculator point label still says '1 mm around the part' (`PART_2C.md` 3); the Lumped column of the README model table (`PART_2C.md` 3).
* Study scripts on their own research branches: `research/fdm-inset-edge` (`os.makedirs` before writing, its 4.5 GB peak in the header), `research/analytic-edge-and-transient` (a library still reads a function removed in 2.6.0) (`DECISIONS_2.md` 31, step 5).
* Model investigations, not for this version unless a review gives GO in time: the laminate in the edge film of the Analytic and the Lumped (`research/reduced-models-edge-laminate`, `DECISIONS_2.md` 15), the Analytic mode cap (`REVIEW_A3.md` 4).

### 4.5 Decisions of the maintainer still open

| decision | recommendation of the reviewer | evidence |
| :-- | :-- | :-- |
| The laminate in the edge film of the Analytic and the Lumped | a stated limit in 2.8.0 with the warning (independent number first); a research branch first, a correction in 2.9 if it works | `DECISIONS_2.md` 15 |
| Copper 385 or 398 W/mK | keep 385 (marked typical, 1.5 % on the hot side); 398 would move every frozen record by about 1.5 % of the rise | `REVIEW_L12.md` 5; `CHANGELOG.md` Changed |
| The 10 / 15 / 10 W/m²K films of a new board | keep (the sum is within the scatter of the laws; the defaults of the original program, now documented) | `DECISIONS_3.md` 36 |
| Accuracy quoted against an independent reference first, and tables against hot references marked superseded rather than rewritten | applied in the documents and the texts; marked 'maintainer to confirm' as a policy of the documents | `DECISIONS.md` 3, 4; `DECISIONS_2.md` 19, 22 |
| A live warning for the FDM on a small outer pad | not added: the error fell from 10.6 % to 3.7 % with the drawn-copper faces and is stated in the guide | `DECISIONS_2.md` 21; `PART_2C.md` 3; `CLAUDE.md` Decisions Log |
| Obtaining JESD51-7 and JESD51-5 | a free registration in his name; the board is then redrawn and the JEDEC row becomes a one-sided test | `DECISIONS_2.md` 26 |
| The timing of the release | after the items of 4.3 and 4.4 that the release gate needs (the screenshots at the documentation review, the refreeze that folds the four pending files) | `DECISIONS_2.md` 31, step 3f and 6 |

## 5. Trust

Trust is the reviewer's judgement after the audit: high where the code matches its source and an independent reference confirms the numbers; medium where the code matches but the accuracy rests on few independent cases or on the program's own models; low where no independent reference exists.

### 5.1 Per chapter of the theory

| chapter | trust | why | what would raise it |
| :-- | :-- | :-- | :-- |
| 0, 1.1 to 1.5: symbols, layered idealisation, laminate, via construction | high | every constant and formula is the code's; the film term described as implemented (`PART_1A.md`) | the bare-laminate sensitivity to the unsourced in-plane FR-4 (a measured laminate value) |
| 1.6 to 1.8: Gerber reader, imported and drawn copper, parts | medium-high | constants match; the evidence is the repository's own measurements and real boards (`PART_1A.md`) | a converged reference for small imported parts |
| 2 FVM | high for the equations, solvers and memory law; medium for the via at a copper corner and near a strong edge | re-run numbers equal; two resolved references disagree by 25 to 39 % at a copper corner (`PART_1A.md`; `REVIEW_A3.md`) | the finite-element run on the copper corner and the track |
| 3 FDM | medium | construction matches the code; its via defect near a strong edge and the small outer pad are stated limits with no separated cause (`PART_1A.md`; validation 51.7) | the cause of the outer-pad error (the open FDM investigation) |
| 4 3D solid | medium-high | slab rule, films and cut cells match; +2.3 to +4.9 % on one-sided pads at 1 mm, +10 to +26 % on a via near a strong edge at 0.5 mm (`PART_1A.md`; validation 3.1, 49) | the 1 mm via near a strong edge against finite elements |
| 5 Lumped | medium | closed forms re-derived; constants fitted to the program's FVM; one resolved via cluster and the near-edge 3D table are the independent checks; several numbers predate the images of the sides (`PART_1B.md` 4) | re-measure the Lumped tables after the side images against an independent reference |
| 6 Analytic | high (steady), medium (transient) | the series and the per-layer edge are exact for the idealisation; edge-laminate error stated with both references; transient -9.1 to +3.2 % of a converged FVM and +1 to +4 % of finite elements on five boards (`PART_1B.md` 4) | more transient boards against finite elements; the edge-laminate investigation |
| 7 Metal blocks | high | the block table is the code term by term; Seri Lee's plate within 0.2 % of the exact series (`PART_1B.md` 4) | the fin coefficient with the channel effect against a source |
| 8 Heat transfer | high for the coding, low for the absolute h | every law as printed; horizontal laws scatter by ±50 %; no measurement (`PART_1B.md` 4) | a physical measurement of a board |
| 9 Parts and junction | high | equations and root finding are the code's; the convention is on the safe side (`PART_2A.md`) | the package θ and heatsink libraries sourced entry by entry |
| 10 Profiles and fast waves | high for the decision and the closed form; medium for the fast-wave limits near sides, with vias and on bare laminate | closed form re-computed to the digit; limits rest on the research 3D references (`PART_2A.md`) | a published fast-wave case or a measurement |
| 11, 12 Verification summary, references | medium-high, high | five stale rows corrected; statuses aligned with the audits (`PART_2A.md`) | figure 22 redrawn |

### 5.2 Per validation group

From `PART_2B.md` 4, with the calculator from `REVIEW_A5.md` 6.

| group | trust | why | what would raise it |
| :-- | :-- | :-- | :-- |
| Numerics (solvers, time stepping, stack-up series, energy balance, memory law) | high | exact checks re-run; the memory law on one machine | the memory law on another machine |
| Layered conduction, FVM | high | within about 1 % of converged finite elements on one-sided pads and the example board | - |
| Edge and laminate (strong edge coefficient) | medium-high | one footing against converged finite elements (validation 46.1); boards of one family | other board families against finite elements |
| Vias | medium | full planes against resolved references; the copper corner rests on references that disagree | the finite-element run that settles the corner |
| Imported and drawn copper (FVM, FDM) | medium-high | faces against the pixel network and an independent 3D solver; drawn layers against finite elements | a real board against a resolved reference |
| Lumped and Analytic | medium (Analytic steady high) | most tables against the FVM they were fitted to; few independent checks | the Lumped tables re-run against an independent reference |
| Blocks and fins | high for conduction, low for the fin coefficient | Seri Lee, the 3D solid, validation 55.3; the channel effect has no reproduced source | a fin-array source reproduced |
| Convection | high for the coding, low for the absolute h | printed examples reproduced; no measurement | a physical measurement |
| Transient | medium | models agree with each other and with a finite-element transient on five boards; the first seconds are too cool | more transient boards, a finer through-thickness model if the first seconds matter |
| Profiles and fast waves | medium | the closed form against two independent solvers | a published case or a measurement |
| Power Calculator | medium-low | one datasheet board (CSD17308Q3, -2.4 %); the JEDEC row an indication | JESD51-7 read and the board redrawn; a part measured on a real board |

## 6. How to repeat

From the repository root, with the project environment (`CLAUDE.md`, 'Commands'). Heavy runs one at a time.

```sh
# The whole battery (about 45 to 55 minutes)
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests --timeout=900 --timeout-method=thread

# The frozen numbers at the three cells (with the four pending files of 2.8.0)
PCBT_FROZEN_CELLS=2,1,0.5 .venv/bin/python -m pytest -q tests/regression

# The published cases, including the release-gate ones (about a minute)
PCBT_PUBLISHED_FULL=1 .venv/bin/python -m pytest -q tests/test_published_cases.py tests/test_calculator_validation.py
.venv/bin/python -m pytest -q tests/test_convection_published.py

# The audit scripts (releases/2.8.0/audit/scripts; each header says what it prints and its review)
.venv/bin/python releases/2.8.0/audit/scripts/study_lee_blocks.py fvm,fdm 0.5            # Seri Lee through blocks.py
.venv/bin/python releases/2.8.0/audit/scripts/study_a4_closed_forms.py $PWD              # Lumped closed forms
.venv/bin/python releases/2.8.0/audit/scripts/study_a4_uniform.py $PWD                   # Analytic and Lumped on 45 uniform boards
.venv/bin/python releases/2.8.0/audit/scripts/study_a4_near_edge.py $PWD out.json        # the 180 near-side cases
.venv/bin/python releases/2.8.0/audit/scripts/study_a4_local_transient.py $PWD           # the Analytic local transient
.venv/bin/python releases/2.8.0/audit/scripts/study_a4_warnings.py $PWD                  # the warnings on the uniform boards
.venv/bin/python releases/2.8.0/audit/scripts/study_via_checks.py closed barrel target shen modes fillgain
.venv/bin/python releases/2.8.0/audit/scripts/study_numerics_data.py omega theta steps lu order memory copper sens gmd
.venv-research/bin/python releases/2.8.0/audit/scripts/study_via_contact_resolved.py     # needs pyamg (.venv-research)

# The final-review scripts (releases/2.8.0/final-review/scripts)
.venv/bin/python releases/2.8.0/final-review/scripts/study_final_1b_checks.py
PCBTHERMAL_CONFIG=<a private folder> .venv/bin/python releases/2.8.0/final-review/scripts/study_final_2b_runs.py all   # peak about 5 GB
```

Two research studies the reviews re-ran: `research/analytic-edge-and-transient/scripts/study_perlayer_edge.py --part 2` (the 48 per-layer edge boards) and `research/models-comparison/scripts/validation_study.py` (validation 2 and 2.1; about 8 GB with the 3D solid, alone on the machine).

## 7. What this means for a user

Trust the FVM (the reference model) for the temperature of a board of ordinary copper with its parts, vias, outline and metal blocks: it agrees with converged finite-element solutions within about 1 % on one-sided pads (validation 3.1) and reads cool by about 1 to 7 % of the rise at a strongly cooled edge, which its warning quantifies (validation 46.1). Treat the Lumped and the Analytic as fast screening estimates whose accuracy was mostly measured against the FVM: they are good at the default edge coefficient and away from the sides, and read cool near strongly cooled edges (the Analytic up to about 15 % against an independent solver at 200 W/m²K, `PART_1B.md` 1), which their warnings say. Treat the absolute level of every result with computed heat transfer coefficients as uncertain by the scatter of the published laws (about ±20 % for a vertical board, up to ±50 % for a horizontal face, `REVIEW_L1L5.md` 2), because no coefficient has been compared with a measurement; the typed coefficients of a new board are defaults, not data. The warnings that matter most: a part on bare laminate (it depends on an FR-4 conductivity that has no source: +25 / -15 %, `REVIEW_L12.md` 1), a strong edge coefficient (the laminate at the edge reads cool), vias at a copper corner or next to a strongly cooled edge, and a time result in its first seconds (more than half too low at 0.3 s, `REVIEW_A4.md` 5). The Power Calculator gives a power that assumes the board is drawn right: its one datasheet check holds to 2.4 %, but a wrongly drawn board moves the answer by 12 to 36 % (`docs/calculators.md` 2.1 and 2.2).
