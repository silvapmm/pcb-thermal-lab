# Final review of 2.8.0, part 2b: `docs/validation.md` against the corrected theory and the code

Scope: `docs/validation.md` sections 1 to 55 (2919 lines), read against the program on `development` da16d80f (2.7.1 plus the 2.8.0 model items: the Lumped part read-out, the drawn copper read as imported copper, the Analytic transient hot point, the images of the sides in the Lumped first link, the exact block cover, the film through the half copper layer), against `docs/theory.md` as corrected by parts 1a and 1b (`docs/final-review-1a`, `docs/final-review-1b`) and against the audit of `releases/2.8.0/audit/`. Branch `docs/final-review-2b`: documents only (`docs/validation.md`, `docs/calculators.md`, this folder); `docs/theory.md`, `docs/models.md`, the user guide and the code were not edited.

**Verdict.** The document is now consistent with itself on the sections that the theory cites and on the ones that the 2.8.0 items moved: a 'Which table is current' note at its head lists the tree of each table, the superseded tables with their replacements and the sections not re-run; the light tables were re-run on da16d80f and their numbers replaced (1, 2, 2.1, 3, 7, 12, 13, 17), two that did not move were re-run and marked (5, 8), and every claim that a re-run contradicted is corrected in place with the earlier value kept in a note. Ready to merge as a documents branch. What it leaves open: the items of section 3 below (the theory verification summary, the user guide's validation table and `docs/models.md` quote numbers that these runs contradict), and the sections measured on earlier trees that were not re-run (list in section 2).

## 1. Runs (all on da16d80f, one at a time, the heavy lock taken for the first; `PCBTHERMAL_CONFIG` private)

| run | command | time, peak | result |
| :-- | :-- | :-- | :-- |
| R1 | `releases/2.8.0/final-review/scripts/study_final_2b_runs.py` (new; scenarios of 2 without the 3D solid, grid of 2.1, program columns of 3) | 59 s, **5.2 GB** (the FDM at 0.25 mm and the 36-slab stress case; above the 3 GB asked for this review: the next run of it should be alone on the machine) | FVM, FDM, Analytic of 1 and 2 unchanged at the printed digit; Lumped column moved (section 53); 2.1: 2 mm FDM 84.52 → 84.62, 4 mm 83.75 / 84.01 → 83.93 / 84.12 (section 51); 3: every program column moved (below) |
| R2 | `research/models-comparison/scripts/solver_equivalence.py` | 3 s, 0.24 GB | section 5 identical (one digit, 87.3953 → 87.3954) |
| R3 | `research/models-comparison/scripts/study_time_and_coefficients.py` | 68 s, 0.68 GB | 7: FDM step 76.1 → 76.2, within 0.78 → 0.70 K, steady 84.52 → 84.62; **Lumped profile peak 133.0 → 140.8 °C**; CSV Lumped 124.0 → 124.2; 8: identical |
| R4 | `research/stackup/scripts/stackup_outline_study.py` | 18 s, 1.5 GB | 12 A and B: 0.1 point in the FDM and 3D columns, Lumped +1.2..+1.7 → +0.5..+2.4 %; C identical |
| R5 | `research/block-and-fins/scripts/study_finned_block_all_models.py` (and the same script on `git archive v2.7.1`) | 3 s each | 12 D: the printed Analytic column (91.5 / 66.1 / 71.4 / 57.2) was already stale on 2.7.1 (88.5 / 65.2 / 70.2 / 56.7); now 88.6 / 65.2 / 70.2 / 56.8; Lumped 89.8.. → 90.2 / 66.9 / 71.9 / 58.4 |
| R6 | `research/block-and-fins/scripts/block_equivalent_study.py` | 29 s, 0.17 GB | 17: implemented Lumped 1.9 / 4.7 → **1.4 / 2.5**, Analytic 1.1 / 4.3 → **1.4 / 4.7**; the Lumped error changed sign (now −1.7 to +2.5 %, mostly hot) |
| R7 | `research/outline/scripts/outline_rectangle_study.py` | 42 s, 0.51 GB | 13: reference column +0.2 to +0.8 K, every mean and range of the bullets moved (same-area 4.1 / 2.5 → 3.9 / 3.5 %; enlarging the box worst in 30 of 30) |
| R8 | the full-copper board of 3 on `git archive v2.6.0` and `v2.7.1` | seconds | FVM 0.5 mm 90.35 → 90.49 °C: the physical slabs of 2.7.0 moved it; the 2.7.0 note of section 3 that called the row unchanged was wrong |
| R9 | `laminate.n_for_gap(1.6 mm, s, n)` | – | 0.2 mm gives 8, 0.1 mm gives 16: the '0.19 / 0.09 mm or less' of 21.2 was wrong (the condition is `s < d/(n−1)`: 0.229 and 0.107 mm) |

## 2. Section by section

Legend: **current** = re-measurable on da16d80f and consistent; **re-run** = re-run here, table replaced; **stale-corrected** = a number corrected from a run or from a section that holds it; **superseded by X** = kept as the record with a mark; **not re-run (tree)** = measured on the named tree, still the evidence, the tree now named in the section or in the head note.

| § | scenario, quantity, reference | status | evidence / change |
| :-- | :-- | :-- | :-- |
| head | – | added | 'Which table is current' note: the 2.8.0 items that move numbers, the re-run list, the superseded list, the not-re-run list |
| 1 | example board, board maximum, FVM 0.5 mm (and a 1 mm FE row) | re-run, stale-corrected | Lumped 86.87 → 86.91 °C (+2.5 %); FE row not re-run |
| 2 | 20 scenarios, board maximum, against the FVM (fitted target) and the program's 3D solid | re-run, Lumped column replaced | R1; corners −8.7 / −8.5 → −5.4 / −3.5 %, thin heater +9.6 → +8.4 %; reading bullet of the Lumped rewritten; 3D column not re-run (no 2.8.0 item reaches it) |
| 2.1 | example board against the cell, maximum | re-run, two rows corrected | R1; 3D column not re-run; prose below kept as the 2.7.x record |
| 3 | four boards against a 1 mm finite-element solid (four elements per gap), maximum | program columns re-run and replaced; FE and 3D (FV) columns not re-run | R1, R8; FDM 20 mm pad −1.1 → −0.3 % (section 51); the 'Reading' paragraph and the FV paragraph now say that the FE reference is cold on pads (3.1) |
| 3.1 | one-sided pads against finite elements | superseded in part by its own audit paragraph | the first bullet and the FV paragraph now carry the converged numbers (FVM +0.5 / −1.1 %, 3D solid +4.9 / +2.3 %) |
| 4, 4.1 | Analytic Robin edge, per-layer edge, local transient; against the FVM, `layered3d_side`, the finite elements | not re-run (2.7.1 audit and 1b's re-run: −4.91 % worst, −9.1 to +3.2 %) | the notes agree with theory 6 as 1b corrected it; the edge-laminate figure of the last paragraph now names its quantity (cell mean) and points to 46.1 |
| 5 | five boards, direct / CG / SOR | re-run, current | R2 |
| 6 | the removed wxPython program | history, labelled | – |
| 7 | step, animations, profiles, CSV; model against model | re-run, 'now' values extended | R3; independent transient reference is `research/transient-reference-boards` (not re-run) |
| 8 | computed h, FVM 1 mm | re-run, current | R3 |
| 9 | parts, junction (2.4.5) | not re-run (2.4.5); one number corrected | RθJA 46.7 → 47.1 K/W (`docs/calculators.md` 2.1 after section 51) |
| 10, 11 | literature, commands | current | – |
| 12 | stack-up, outline, sensitivity, finned block | re-run (A to D), replaced | R4, R5; the prose under A and B is still flagged as of the earlier tables |
| 13 | Lumped and Analytic on the equivalent rectangle, against the FVM on the real outline | re-run, table and bullets replaced | R7 |
| 14, 14.1 | typical stack-ups, FVM 2 mm, example board | not re-run (2.4.x); the advanced stack-up has the physical slabs since always, and section 51 moves the 2 mm example by 0.001 K in the FVM | – |
| 15 | fin formula against a 2D fin | current (closed form) | – |
| 16 | 3D solid against Yovanovich Table 3 and a GCI | current (the 3D solid did not change in 2.7 to 2.8 on these cases) | – |
| 17 | block in the Lumped and Analytic, 74 cases, against the FVM | re-run, table replaced | R6; the 'typical case' and 'finned' figures given with the new values |
| 18 | via fill | not re-run (point-via era for the absolute numbers, said in the text) | – |
| 18.1 | fill gain of the example board | not re-run (2.7.1 audit); note added: the Lumped row predates section 53 | – |
| 18.2 | zones | not re-run (research numbers, said) | – |
| 19 | power from the top | not re-run (5fc91430, A5); the calculator bullet now gives the post-51 values | – |
| 20, 21 | first and second round of corrections | history, labelled | – |
| 21.1 | – | superseded (already marked) | – |
| 21.2 | laminate rule | not re-run (2.4.5 to 2.7.0, by paragraph); **stale-corrected**: the `S_MAX` sentence | R9 |
| 21.3 | 3D solid slabs | not re-run (2.6.0) | – |
| 22, 22.1 | effective conductivity, published plates | not re-run (before section 55; the note in 22.1 says so) | – |
| 23 | part across the outline | history up to 23.1 (marked), 23.1 not re-run (2.7.0) | – |
| 24 | warnings | not re-run (studies of 2.4.x) | – |
| 25 | numbers the old theory carried | history, 'carried over' | – |
| 26 | memory law | not re-run (2.4.5 ladder, 2.7.1 audit points) | – |
| 27 | imported copper mappings | not re-run (2.5.x; 27.3 re-run by the audit on 5fc91430) | – |
| 28, 28.1 | via near an edge | not re-run (2.7.0; the strong-edge tables marked superseded) | – |
| 29, 29.2 | heat-source shape; JEDEC readings | not re-run (2.7.0; 29.2 5fc91430); note added: the pad column on da16d80f from `docs/calculators.md` 2.1 (32.15 / 27.41 / 28.26 / 36.35 K/W at 1 mm) | – |
| 30 | via on partly covered copper | not re-run (2.5.x, cold spot 2.7.0) | – |
| 31 | Lumped first ring | not re-run (2.6.0); note in 31.6: measured before section 53 (1b F6) | – |
| 32 | cut-cell links | superseded (its own audit note: 32.1 to 32.3, 32.6 stale) | – |
| 33 | 3D solid cut cells | not re-run (2.6.0) | – |
| 34 | barrel length and rim | not re-run (2.6.0, audit 2.7.1); **cross-reference corrected**: the imported rim is section 45, not 43 | – |
| 35 | Lumped near a side | superseded in its levels by 53 (mark added); the rule and the raster current | – |
| 36 | laminate band | not re-run (2.6.0); its cell-centred reference superseded by 46.1 (head note) | – |
| 37 | fast waves | not re-run (2.6.0, audit 5fc91430) | – |
| 38 to 40 | imported and drawn outline films | not re-run (2.7.0; 40 audited on 2.7.1); 40.4 first bullet already pointed to 51 | – |
| 41 | FDM harmonic face | not re-run (2.7.0); the update note now names section 51 too | – |
| 42 | Lumped via groups | not re-run (2.7.0) | – |
| 43, 44 | simple stack-up slabs; thin laminate | not re-run (2.7.0); first tables marked superseded (46) | – |
| 45 | imported via rim | not re-run (2.7.0) | – |
| 46, 46.1 | finite elements | not re-run (scratch environment); **the FDM pad row at 1 mm and reading (5) superseded by 51.7** (−10.6 → −3.7 % at 10 W/m²K, −14.7 → −5.1 % at 200, −23.3 → −8.5 % at 1000); the FDM bullet of 46 marked | – |
| 47 | FDM cell-fill faces | not re-run (2.7.0); head mark: FDM columns of boards whose copper edge cuts a cell superseded by 51 | – |
| 48 | Lumped part read-out | 2.8.0 branch; note: measured before section 53 | – |
| 49 | via near a strong edge, warning texts | current (text only); **moved to its place between 48 and 50** (it stood after 51) | – |
| 50 to 55 | 2.8.0 items | measured on their branches, current | – |

Numbering: section numbers 1 to 55 are unique and now in order; every `### X.Y` sits under its section `X`; section 33 uses bold run-in subsections (33.1 to 33.5) instead of headings, left as it is. Every 'section N' cross-reference of the document resolves; the one wrong target found (34.2 → 43) is corrected.

## 3. Items (not edited here: other branches or an executor)

| item | file | what is stale | the number that holds (evidence) |
| :-- | :-- | :-- | :-- |
| T1 | `docs/theory.md` 11, row 'Linear solvers' | 'agree to 7·10⁻⁹ K (5)' | 4·10⁻⁹ K (3.9e-9, R2, validation 5) |
| T2 | theory 11, 'Layered idealisation' | 'FVM 0.1 to 0.7 % on the four boards of 3 … +2.9 % on a one-sided pad' | 0.1 to 0.4 % on da16d80f against the 1 mm FE (R1); against the converged FE of 3.1 the one-sided 10 mm pad is +0.5 / −1.1 % at 1 / 0.5 mm |
| T3 | theory 11, '3D solid / finite-element solid' | '+8 % on a heater-sized pad', '+1.6 % on a 20 mm pad' | +4.9 % (10 mm) and +2.3 % (20 mm) at 1 mm against the converged FE (validation 3.1 audit paragraph) |
| M1 | `docs/models.md` 2.3 (line 81 on 1b) | 'thin heaters (+9.5 %)' | +8.4 % (R1, validation 2) |
| M2 | `docs/models.md` 106, `docs/versions.md` 182, user guide line 228, `docs/theory.md` 1.4 on `development` (1a corrected theory only) | '8 sub-gaps … 0.19 mm or less, 16 … 0.09 mm or less' | below 0.229 and 0.107 mm (R9; validation 21.2 corrected) |
| H1 | user guide, table 'What is validated', row 'FDM, a small outer pad' | 10.6 % low at 1 mm (10 W/m²K), 15 to 28 % low with 200 to 2000; FVM 2.1 % | −3.7 % at 1 mm (10 W/m²K), −5.1 % (200), −8.5 % (1000); FVM −2.0 % (validation 51.7); 0.5 and 0.25 mm unchanged; 2000 W/m²K not re-measured after 51 |
| H2 | user guide, row 'Power Calculator' | '−1.7 % and +3 %' (the values of 2.4.5) | CSD17308Q3 −2.4 % (the check); JEDEC +1.8 % as drawn, an indication only (27.0 to 36.6 K/W over the four board readings at 0.5 mm), `docs/calculators.md` 2.1 |
| H3 | user guide, row 'Heat transfer coefficients' | 'two datasheet resistances −3.2 % and +3.9 %' (2.4.5) | the two calculator rows of H2 |
| H4 | user guide, row 'Exposed pad as the heat source' | 'one JEDEC datasheet 31.9 against 32.5 K/W' as a check | validation 29.2: the order of the shapes holds, the agreement is not a check; the pad reads 27.4 to 36.4 K/W over the four board readings (32.15 as drawn, 1 mm) |
| H5 | user guide, row '3D solid' | '0.7 to 0.8 %' (Table 3 only) | add the FE check: +2.3 to +4.9 % on one-sided pads at 1 mm, the plan cell of a small part (validation 3.1, 21.3) |
| H6 | user guide line 407 | copper-fill gain 'down to 4.5 K (FVM 4.2 K)' | validation 18.1 (2.7.1): Lumped 4.54 / 4.71, Analytic 4.32 / 4.23, FVM 4.25 / 4.20 K at 0.5 / 1 mm; the Lumped row predates section 53 (re-run `study_via_checks.py fillgain`) |
| V1 | `docs/validation.md` 18.1, 31.6, 48 | measured before section 53 | re-run the Lumped rows (light) |
| V2 | `docs/validation.md` 29.2 body columns | 5fc91430, before section 51 | `study_jedec_board_readings.py` at 1 mm (4.6 min, 2.1 GB at 0.5 mm) |
| V3 | `docs/validation.md` 12 A / B prose | written for the tables of 2.4.x | re-read against R4 |
| V4 | `validation_study.py` | peaks at 8.3 GB with the 3D solid (5.2 GB without it) | split the 3D columns into their own option so that the program columns can be re-run on a busy machine |

The checked rows of the guide's table that agree with validation: laminate edge (46.1), imported copper (27.3), Gerber reader, the Lumped near-edge text (53.1 to 53.4), the 3D solid small-part numbers (21.3), the zoned Lumped (18.2).

## 4. Trust level per scenario group

| group | trust | why |
| :-- | :-- | :-- |
| Numerics (solvers, time stepping, stack-up series, energy balance, memory law) | **high** | exact checks re-run (5, 7, 12 'exact checks'), closed forms; the memory law on one machine |
| Layered conduction, FVM | **high** | within about 1 % of converged finite elements on one-sided pads and the example board (3, 3.1); the residual is the laminate idealisation, measured (46.1) |
| Edge and laminate (strong `h_side`) | **medium-high** | one footing in 46.1 against converged finite elements; four earlier sets marked superseded; boards of one family |
| Vias | **medium** | FVM and FDM against resolved references at full planes; the copper corner and the strong edge rest on references that disagree by 25 to 39 % (34.2) and the FDM and 3D solid defects near a strong edge are stated (49) |
| Imported and drawn copper (FVM, FDM) | **medium-high** | the faces against the pixel network and an independent 3D solver (27), the drawn layers against finite elements and `layered3d` (51); no real board against a reference |
| Lumped and Analytic | **medium** (Analytic steady high) | most tables against the FVM they were fitted to; the independent checks are fewer (4.1, 53.3, 51.7, the block cases); the 2.8.0 Lumped items moved most of its numbers, re-run here where it was light |
| Blocks and fins | **high** for the conduction (Seri Lee, the 3D solid, 55.3), **low** for the fin coefficient (channel effect, 15) | |
| Convection | **high** for the coding, **low** for the absolute `h` | 8 identical; no measured board |
| Transient | **medium** | the program's models agree with each other (7) and with a finite-element transient on five boards (`research/transient-reference-boards`, not re-run); the first seconds are too cool in every model |
| Profiles and fast waves | **medium** | the closed form against two independent solvers (37.2); no published case or measurement |
| Calculator | **medium-low** | one datasheet check (CSD17308Q3, −2.4 %); the JEDEC row is an indication; the accuracy against a real board is that of the drawn board |

## 5. What was not verified

* The finite-element columns (3, 3.1, 28, 36, 40, 43, 44, 46, 47): scikit-fem and pyamg live only in the scratch environment of `research/independent-fem-edge`, which is not installed here; read, not re-run.
* The 3D solid columns of 1, 2, 2.1 and 3 (the 3D solid at 0.5 mm of the example board needs about 8 to 11 GB); the 3D solid did not change on these boards in 2.8.0, and its errors in 2 are against the FVM, which did not move.
* The sections listed 'not re-run' in section 2; in particular the Lumped tables of 18.1, 31 and 48 after section 53 (V1), the JEDEC body columns (V2), the 74 block cases' bullets beyond the table and the typical case (R6 gives them), and the research numbers quoted in 18.2, 27, 30, 35, 37, 50.
* The cause of the stale Analytic column of 12 D on 2.7.1 (R5) was not traced to an item.
* `tests/test_docs.py`, `tests/test_license_header.py` and `tests/test_version.py` were run at the end (section 6).

## 6. Tests

`QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_docs.py tests/test_license_header.py tests/test_version.py` on the branch after the commit of these files: 827 passed (also before the commit, the new script included by the documentation gate).
