# Decisions on the open questions of the 2.8.0 audit

The reviewer's answers to the open decisions of the audit: the six of `ASSIGNMENTS.md` ('Open decisions for the maintainer', branch `docs/audit-claims-register`), the threshold and the published cases of `REVIEW_A1.md` (branch `docs/audit-a1`), the open points of the reviews in `releases/2.8.0/reviews/` (`thick-plate-warning-bound.md` on `fix/thick-plate-warning-bound`, `drawn-copper-faces.md` on `fix/drawn-copper-faces`, `board-dock-write-back.md` on `fix/board-dock-write-back`), `research/muzychka-case2-analytic/INTEGRATION.md` and the wave plan of `docs/versions.md` ('Planned: 2.8.0'). Program: `development` 5fc91430. Under the maintainer's rule that an open decision is answered by a reviewer, each decision below is taken here, with the evidence; the few that change the shape of the release or the policy of the documents are marked **maintainer to confirm**.

Every number quoted below is printed by a script named next to it, or by the scratch check of section 6 (one Python process, `pcbthermal.convection` only). Nothing in `pcbthermal/` or `tests/` is edited on this branch.

Status of the branches this file depends on (`git rev-list development..<branch>`): `fix/thick-plate-warning-bound` (2 commits, reviewed GO, not merged), `fix/board-dock-write-back` (4 commits, reviewed GO at cb1e29f7, not merged), `research/muzychka-case2-analytic` (3 commits, reviewed GO, not merged), `fix/drawn-copper-faces` (3 commits, reviewed GO, not merged), `docs/audit-a1` (1 commit, GO with two conditions), `docs/audit-claims-register` (3 commits, not merged); `research/lumped-edge-link` is merged.

## 1. Thick-plate warning threshold

**Options.** (a) Keep 5 % of the rise with the corrected bound of `fix/thick-plate-warning-bound` (`(q'' + q_f) t/(2k)` plus `q'' t_l / k` for the other copper layers); (b) lower the threshold (3 %); (c) warn on the measured film-and-gradient estimate without a fixed percentage.

**Evidence.** `REVIEW_A1.md` 2.2 (13 published sources of Muzychka et al. 2003, the column of case 2): the shortfall of the FVM exceeds 5 % of the rise on 5 sources (case 1 (a) S1 and S2, case 2 S2, S3, S4); the fixed bound warns on exactly these 5 plus case 2 S1 (shortfall 4.0 %, bound 6 %); no source above 5 % is silent; the cross (shortfall 2.1 %, bound 2.8 %) and case 1 (b) (0.05 K) stay silent. With 3 % the cross would warn for a 1.2 K shortfall (2.1 % of the rise), which is inside the program's other first-order errors at a 1 mm cell. The 5 % has no source (formula F-017, own rule): it is a choice and is now stated as one.

**Decision.** (a): keep 5 %, with the corrected bound, and say in theory 7.5 that the threshold is the program's choice, checked on 13 published sources. When `fix/face-film-half-slab` (decision 8) is in, the film term leaves the bound on a one-layer plate and the threshold stays.

**Who acts.** Maintainer: merge `fix/thick-plate-warning-bound` (reviewed GO; text conflicts with `docs/audit-a1` in `docs/theory.md` 7.5 and `docs/validation.md` 22.1, keep both) with the whole battery. Executor: none.

**Risk.** Low. The bound is an upper estimate from one-dimensional conduction, not a theorem (the review of the branch found no counter-example on nine plates and 13 sources; a poor plate over a much better one was not searched). Which boards warn changes; no number moves.

## 2. Published cases T1 to T8 as regression tests

**Options.** (a) None in the battery (the studies stay in `research/`); (b) all eight in the battery; (c) the cheap ones in the battery, the slower ones in the release gate.

**Evidence.** Costs and tolerances in `REVIEW_A1.md` 4: T1 Seri Lee through `blocks.py` (3 s), T2 the cross (5 s), T3 case 2 (2 s), T4 case 1 (a) (5 s), T5 case 1 (b) (10 s), T6 Yovanovich-Muzychka-Culham Table 2 (under a minute), T7 Lemczyk Table 4 (under a minute), T8 the coupon base stack (about a minute). Today no published case except the Cu / FR-4 / Cu coupon and Yovanovich 2003 Table 3 (`tests/test_solid3d_verification.py`) is held by a test, and A1 found the documents quoting published plates without the program's own (lower) readings for several versions: that is what a test prevents. The audit rule: a test of a known limit is one-sided.

**Decision.** (c). **T1 to T5 enter the battery** (about 25 s on a 43-minute battery), in a new `tests/test_published_cases.py`, with the tolerances of `REVIEW_A1.md` 4, each written as a one-sided limit plus a narrow band on the program's own value so that a drift is seen:

| test | assertion |
| :-- | :-- |
| T1 | Rc centre / edge / corner within 0.5 % of the exact thin-plate series 0.6637 / 1.2799 / 2.2700 K/W; within +1 / -1.5 / -5.5 % of the printed 0.66 / 1.29 / 2.38, the corner below 2.38 |
| T2 | FVM 1 mm centre centroid 79.44 +- 0.1 C; the shortfall to the paper's 80.61 C between 0 and 2.5 % of the rise (never above the paper) |
| T3 | FVM 1 mm, each source 2.5 to 6.0 K below the paper (never above); the thick-plate warning fires on all four sources (needs decision 1 merged). The column-mean assertion (`h` 394.74, within 0.15 K) is written with the tolerance of today and tightened to 0.10 K by `fix/face-film-half-slab` in the same commit that removes the film term |
| T4 | FVM 2.5 mm, centroids 8 to 10 % of the paper's rise low (never above); both sources warn |
| T5 | FVM 2.5 mm, centroids within 0.3 % of the paper's rise |

**T6 to T8 go into the release gate** behind an environment variable (`PCBT_PUBLISHED_FULL=1`, as `PCBT_COMPAT_V245`), skipped in the ordinary battery: together up to three minutes, and their models move little between releases. The independent solver is not run in any test (its numbers are the stored reference values of the studies, with the study named in the docstring).

**Who acts.** Executor on a `fix/published-case-tests` branch (tests only, no physics), after `fix/thick-plate-warning-bound` is merged; reviewer; maintainer (release gate list in `CLAUDE.md`, 'Commands', and the release steps).

**Risk.** Low. The bands on the program's own value (T2, T3 column mean) will fail on purpose when a model fix moves them (decisions 7, 8, the block cover P2): the fix re-baselines them with the reason written in the test, as the frozen numbers do.

## 3. Accuracy shown to the user: against the FVM or against an independent reference

**Options.** (a) Keep quoting the Lumped and Analytic errors against the FVM; (b) quote only the error against an independent reference; (c) the independent number first, the FVM number second and named as a comparison with the model they were fitted to.

**Evidence.** The Lumped (rings, first-ring cap, zones, via groups) and the Analytic (via tiles, local factor, per-layer edge) constants were fitted against the program's FVM (`docs/theory.md` 5 and 6; `ASSIGNMENTS.md` A4: 'the accuracy figures that the warnings and the documents quote, against an independent reference and not only against the FVM they were fitted to'). An error measured against the model a constant was fitted to is a measure of the fit, not of the accuracy: when the FVM moved (the edge band of 2.6.0, the physical slabs of 2.7.0) the Analytic per-layer numbers moved with it without a line of the Analytic changing (claims VA-035, RCC-002, RCC-019: 'assertion widened to -5.5 % because the FVM moved'). Where both exist they differ in sign and size: the per-layer edge read -0.5 to -5.8 % against the 3D solid on the 24 study boards and -5 to -10 % on the small boards, while the FVM figure said -4.07 to +0.06 % (CLAUDE.md, decision of `feature/analytic-edge-and-local-transient`).

**Decision.** (c). Every accuracy figure that a user reads (warnings in `checks.py`, `copper.py`, `analytic.py`, `lumped.py`, `profiles.py`; the user guide limits table; `docs/models.md`; `docs/theory.md` 'Limits') quotes first the error against an independent reference (the finite elements of `research/independent-fem-edge` and `-extensions`, `tests/helpers/layered3d.py`, a closed form, a published case), with its refinement shown; the error against the FVM may follow as 'against the finite-volume model it was fitted to'. Where no independent number exists the text says 'against the finite-volume model (not an independent reference)'. This applies to every model, not only the two reduced ones (the FVM's own errors are already quoted against the finite elements since validation 46).

**Who acts.** Reviewer (assignment A4 produces both numbers per claim), then assignment A6 (reviewer and executor) writes the texts; maintainer for the user guide and tooltips. **Maintainer to confirm**: it is a policy of the documents (it makes several quoted ranges wider).

**Risk.** Medium in effort, low in physics. The quoted ranges grow on some warnings (the Analytic per-layer edge, the Lumped first ring); the warning thresholds stay. The independent references are themselves at a finite cell: a number is called against a converged reference only with its refinement series (audit rule).

## 4. Tables measured against a reference later found hot or not converged

**Options.** (a) Rewrite every such table with a re-run; (b) keep them and mark 'superseded'; (c) rewrite what is still cited as current evidence, mark the historical ones.

**Evidence.** The claims register has 303 rows with `ref_converged` 'NOT stated'; the ones where the reference is known to be hot or moving (register columns `reference` and `ref_converged`): validation 3 and 3.1 (finite elements of 1 mm, four elements per gap: VA-019, VA-020, VA-026, T-090, T-164), 21 'nine boards' (program 3D solid at 1 mm: VA-128), 21.2 (`ref3d` at 0.25 mm, 0.4 to 1.5 % above its Richardson limit: VA-134, RB-049), 23 'vias at the outline' (3D solid at 1 mm: VB-003), 28 strong-edge and `ref3d` tables (VB-057, VB-058, VB-060), 34.2 (program 3D solid at 0.1 mm, not converged on a plated wall: VB-098, VB-099), 36.1 and 36.3 (cell-centred reference, hot against the finite elements: VB-116, M-028, M-029), 43.6 six-layer (reference still moving: VB-158, VB-159), 44 first table (cell-centred 0.25 mm: VB-160), the research tables `laminate-slabs-and-local-rule` 4.1 (RB-081), `laminate-edge-band` 2 (RB-089), `strong-edge-laminate` 8.2 to 8.4, `via-partial-copper` 2 and 3 (RCD-002, RCD-004), `via-contact-geometry` 3.3 (RCD-016), `solid3d-verification` 2 and 4.2.1 (RA-306), and the warning text W-017 (`checks.check_edge_laminate`, the 3.2 mm numbers). A table that documents why a decision was taken at the time is history; its numbers rewritten would no longer explain the decision.

**Decision.** (c):
* **Rewrite** (re-run against the converged or independent reference) every number that a user reads or that a current text cites as evidence: the warnings and the user guide (W-017, M-028, M-029 and every warning number that rests on the rows above), `docs/models.md`, the 'Limits' and 'Where it is checked' parts of `docs/theory.md`, the consolidated tables `docs/validation.md` 24 and 25, and validation 3 and 3.1 (the only check of the 3D solid against finite elements; already a 'Planned' item with the slab rule of 2.6.0).
* **Mark** every other table above, in place, with one line under it: 'Superseded: the reference of this table reads N % hot (or: was not converged); the current numbers are in section X.' The numbers stay as printed. In the research READMEs the line goes into the review chapter of the folder.
* A table neither rewritten nor marked by the release is a finding of the final opinion.

**Who acts.** Reviewer of assignment A2 (the finite-element re-runs, heavy, on a quiet machine) gives the list with the new numbers; A6 rewrites the user-facing texts; the maintainer applies the marks to `docs/validation.md`; each research folder's marks on its own branch by the reviewer. **Maintainer to confirm** the policy (it is a rule for the documents, which he owns).

**Risk.** Medium in effort (A2 is two to three reviewer-days of heavy runs); low in physics. A marked table can still be cited by mistake: the A6 pass searches every cross-reference to the marked sections.

## 5. Constants without a recorded source

**Options.** (a) Find a printed source for every constant before 2.8.0; (b) mark all of them 'typical, no source'; (c) source the physical constants that a read book already prints, mark the material and catalogue values as typical.

**Evidence.** `ASSIGNMENTS.md` (inventory) lists from memory with no recorded source: the FR-4 properties (`materials` of `defaults.json`: 0.3 / 0.9 W/mK, 1850 kg/m3, 900 J/kgK), the emissivity 0.9, the air-property fits of `convection.air_properties`, the 0.447 self-distance of a square; the libraries (`via_fills` 4, `metals` 5, `interfaces` 5, `dielectrics` 7, `package_theta` 8, `heatsinks` 11 entries) all carry a `note` (checked in section 6), but a note is not always a source. The FR-4 and the emissivity depend on the product and the surface (laminate grade, resin content, solder mask colour and finish): no single source would make them right for a user's board, and both are editable. Copper (385 W/mK, 8960, 385) and air are physical properties printed in a source the project has read (Lienhard 2024 appendix tables, R).

**Decision.** (c):
* **Need a source before 2.8.0** (assignment L12): copper `k`, `rho`, `cp` and the air-property fits, checked against the page images of the appendix tables of [Lienhard2024] (page numbers recorded in the bibliography); the 0.447 self-distance against its derivation (it is a closed form: write it in `docs/theory.md` 6.1 or replace it by the exact value).
* **Marked 'typical, no source'**, in the `note` of the entry, in the Preferences tooltip and in the theory sources table: the FR-4 properties, the emissivity 0.9 (with the words 'depends on the solder mask and finish'), and every library entry whose `note` does not name a source (datasheet, catalogue page or bibliography key). The package theta library keeps its existing rule (a typical start, the datasheet value is the user's). No value changes, so no number moves.

**Who acts.** Reviewer of L12 (copper, air, 0.447) and L10 (the libraries: which notes are sources); executor for the `defaults.json` notes and the tooltips on a `fix/typical-values-marks` branch; maintainer for the user guide.

**Risk.** Low. If the air fits disagree with the printed table beyond 1 % in the 0 to 100 C range, that becomes a fix with a pending file (the computed-h boards move); not expected.

## 6. Forced convection: 0.664 or 0.742

**Options.** (a) Keep `Nu = 0.664 Re^(1/2) Pr^(1/3)`; (b) adopt eq. 18 of Yovanovich and Teertstra (2001) with its 0.742; (c) adopt their whole composite.

**Derivation.** The program models each face of the board as a flat plate of length `L` (the board width, `convection.h_forced`) along a uniform stream with no pressure gradient. For that plate the laminar boundary layer has the similarity solution of Blasius; with an isothermal wall and `Pr >= 0.6` the local value is `Nu_x = 0.332 Re_x^(1/2) Pr^(1/3)` and its mean over the length is `0.664 Re_L^(1/2) Pr^(1/3)` (Pohlhausen; [Lienhard2024] p 311, R). With a uniform flux instead (a board heated by its parts is between the two) the local value is `0.453 Re_x^(1/2) Pr^(1/3)` and the mean based on the mean wall excess is about 0.68: within 2.4 % of 0.664, so the wall condition does not decide the question. Both are leading-order boundary-layer results and hold for `Re_L` above a few thousand; below, the leading-edge and edge (diffusive) effects add heat transfer. The 0.742 of Yovanovich and Teertstra is not a different boundary-layer constant for the same plate: it is the coefficient of the boundary-layer term in their composite on the length scale `sqrt(A)` of a finite rectangular plate (their eq. 17, a linearised coefficient fitted to their CFD over a range of aspect ratios and `Re`), and it is meant to be used inside that composite with its diffusive term, not on `L`; their own eq. 12 is the textbook 0.664 (`docs/theory.md` 8, the transcription of eq. 18 confirmed by image). Put on `L` alone it is a mixture of two length scales. A real board is not a smooth plate either: parts and the leading edge trip the boundary layer, which raises `h`, so the smooth-plate laminar value is on the low (hot, safe) side.

**Effect on h** (scratch check, `pcbthermal.convection` at a 30 K rise, both faces, emissivity 0.9, the program's blend `(h_n^3 + h_f^3)^(1/3) + h_r`, the up face on `L_c = A/P`; the factor 0.742 / 0.664 = 1.117 applied to `h_f`):

| board, air speed | Re | h_f 0.664 / 0.742 (W/m2K) | total h 0.664 / 0.742 | total h |
| :-- | --: | :-- | :-- | --: |
| 60 x 48 mm, 0.5 m/s | 1 773 | 11.31 / 12.64 | 19.49 / 20.51 | +5.2 % |
| 100 x 80 mm, 1 m/s | 5 909 | 12.39 / 13.84 | 19.83 / 21.08 | +6.3 % |
| 100 x 80 mm, 3 m/s | 17 727 | 21.46 / 23.98 | 28.16 / 30.60 | +8.7 % |
| 200 x 160 mm, 2 m/s | 23 637 | 12.39 / 13.84 | 19.39 / 20.71 | +6.8 % |

So the choice moves the total coefficient 5 to 9 % (the rise of a board cooled mostly by its faces about the same, cooler with 0.742), less than the 11 to 14 % of `h_f` because radiation and natural convection are in the sum.

**Decision.** (a): keep 0.664. It is the exact result for the geometry the program models, it is the conservative side, and 0.742 belongs to a composite on another length scale. Option (c), the whole Yovanovich-Teertstra composite on `sqrt(A)`, would be the better model for small boards at low `Re` (it adds the diffusive term the program lacks); it is not adopted without a measurement or a 3D CFD reference of a board (none exists: the Results line 'never compared with a measured copper board' stays). The docstring of `h_forced` and theory 8 already state both coefficients; they get one sentence each: '0.742 is the coefficient of their composite on sqrt(A), not a correction of 0.664 on L'.

**Who acts.** Reviewer of L5 (one sentence in theory 8 and in the docstring, on the branch of L5); nothing for the executor. Planned item, not for 2.8.0: the composite on `sqrt(A)` after the measured board (G1).

**Risk.** Low. If a future measurement shows forced-air boards running 5 to 9 % cooler than the program, the composite is the first candidate.

## 7. Imported copper and drawn layers on one board

**Options.** (a) Accept as a stated limit; (b) a warning; (c) implement the drawn source for the layers that are not imported.

**Evidence.** `releases/2.8.0/reviews/drawn-copper-faces.md` (open decision 1): with `fix/drawn-copper-faces` the drawn layers of a board without imported copper read the exact fill and the flow-based faces; a board with imported copper gets no drawn source at all (`copper.drawn_source` returns None), so its drawn layers keep the earlier path, which reads up to 8 % cool at 1 mm (`research/drawn-copper-faces` README: stripes -8.0 % at 200 W/m2K and 1 mm), the unsafe side, with no warning. The design for the mixed board exists (`research/drawn-copper-faces/INTEGRATION.md` 5: the imported layers win, the zone raster only for the drawn layers), and the mixed board was 'not verified' by that review. A mixed board arises when the Gerber set lacks a layer (inner planes not exported) and the user draws it: not common, but silent.

**Decision.** (c), on a follow-up branch of `fix/drawn-copper-faces` after its merge: `drawn_source` builds the raster only for the layers that have no imported mask, so a mixed board reads one rule on every layer. It moves no frozen record (no harness board mixes the two; to be checked on the 17 boards) and adds a test on a mixed board (imported outer layers, a drawn inner plane with an edge through a part) against the same board with the inner plane imported. If it is not merged before the release gate, (b) ships instead: one live warning on a board with imported copper and a drawn zone on another layer ('the drawn layers of this board are read with the earlier rule, which may read up to 8 % cool at 1 mm; use 0.5 mm or import the layer').

**Who acts.** Maintainer: merge `fix/drawn-copper-faces` (reviewed GO, with its pending file, and the three new harness boards in `expected_shifts_2.8.0.json`). Executor: the mixed-board branch; reviewer; maintainer.

**Risk.** Low to medium: the memory law of `memory.drawn_run_bytes` must count only the drawn layers on a mixed board (the review re-measured the law on drawn boards only).

## 8. The film term `t/(2k)` in series with the face film: always, or above a threshold

**Options.** (a) Always (every face film of a node sees half its slab in series, as the 3D solid, the FVM edge film and the part face over laminate already do); (b) only when `h t/(2k) > 1e-3`, so that ordinary boards keep their numbers; (c) never (keep the film term in the warning bound).

**Evidence.** `research/muzychka-case2-analytic` README 3, 8.3, 8.4 and `INTEGRATION.md` item 2 (reviewed GO): on case 2 the film acting on the node costs 0.84 K; with the half slab in series the FVM, FDM and Analytic read the 3D column mean within 0.10 K. For PCB copper the term is 5e-7 of `1/h` (35 um, `h` 10): every frozen record moves by about 3e-5 K, more on boards with metal blocks. The frozen-number tolerance is 1e-8 K, so with (a) every record moves and needs the pending file and the refreeze of 2.8.0 (which happens anyway). A threshold (b) keeps the frozen numbers but makes a step in the result where a parameter crosses it (a sweep of plate thickness shows a jump) and leaves two rules in the code and the theory. The 3D solid already uses the half slab, so (a) also brings the layered models and the 3D solid to one convention.

**Decision.** (a), always, in wave 3, branch `fix/face-film-half-slab`, as written in `INTEGRATION.md` item 2 (`h_top` and `h_bottom` of the outer copper nodes in the FVM and FDM, the Analytic and Lumped through `1/(1/h + t/(2k))` per face, the exposed film and the board link of a metal block in `blocks.extra_layers`). Two additions to the branch: (i) measure the film term of a metal block against the 3D solid (not measured by A1 or the case 2 review: `REVIEW_A1.md` 6); (ii) the computed-h loop keeps reading the node temperature (the face temperature behind the film is the node minus the film drop; the choice changes `h` by less than the term itself). After the merge the thick-plate bound drops its film term on a one-layer plate (decision 1) and T3 tightens (decision 2).

**Frozen-number consequence.** Every record of the 17 harness boards moves (about 3e-5 K; the block boards more), so the branch must be the LAST model fix before the refreeze: the test `test_no_record_or_time_is_in_two_pending_files` forbids a record in two pending files, and this fix touches all of them. Its pending step is the refreeze itself (or one pending file that folds the earlier ones), with a row in `expected_shifts_2.8.0.json` of direction 'any' and a cap of 1e-4 K for boards without a block.

**Who acts.** Executor (`fix/face-film-half-slab`, after every other number-moving fix of wave 3); reviewer; maintainer (whole battery, the refreeze).

**Risk.** Low in physics, medium in bookkeeping (it touches `fvm.py`, `fdm.py`, `blocks.py`, `analytic.py`, `lumped.py`: one branch at a time; every pending file must be folded consistently). The map hashes of `tests/test_results_views.py` move if the example board moves by more than their rounding: rebaseline at the refreeze.

## 9. The order of wave 3 after the audit

**Evidence.** `docs/versions.md` 'Planned: 2.8.0' (wave 2 and 3 tables), the shared-file rule (`fvm.py`, `fdm.py`, `laminate.py`, `viawell.py`, `lumped.py`, `analytic.py`, `checks.py`, `docs/theory.md`: one branch after another), the pending-file rule (no record in two files), and decisions 1 to 8.

**Decision.** In this order:

1. **Now, no number moves** (merge one after another, each with its whole battery): `fix/thick-plate-warning-bound`; `fix/board-dock-write-back` (reviewed GO; with decisions 10 and 11 done on it first); `research/muzychka-case2-analytic`; `docs/audit-a1` and `docs/audit-claims-register`; then `fix/published-case-tests` (decision 2) and the text items P3 to P5 of `REVIEW_A1.md` 4 on one small `fix/` branch.
2. **Number-moving fixes, in series, each with its own pending file**: (a) `fix/drawn-copper-faces` (reviewed GO, FVM and FDM records of the drawn boards), then its mixed-board follow-up (decision 7); (b) `fix/lumped-edge-first-link` (A27, Lumped only: its pending file replaces `lumped-part-readout.json`); (c) A48, the Analytic transient read at the steady hot point (`analytic.py`, transient records of via and heatsink boards); (d) P2, the exact cover of a metal block (`blocks.py`, the block records whose edges cut cells). A18, A30 and A32/A40 enter only with a GO from their investigations; otherwise they are stated limits of 2.8.0.
3. **`fix/face-film-half-slab` last of the model fixes** (decision 8), then the refreeze.
4. **Assignment A6** (the warning and guide texts quote the numbers that A1 to A5 settled, decisions 3 and 4) after step 3, so that the texts are written once against the final models; the marks of decision 4 in the same pass.
5. **Features after the model fixes**, none of which moves a frozen number: B5 (option off), paint and erase of the imported mask, heater modes, the metal-block face options (one pending file for block boards: put it before step 3 if adopted), the component-role read-out, the via-fill solder entry, the capacity inventory. A feature that slips does not hold the release.
6. **Release gate** as written in `docs/versions.md`, plus `PCBT_PUBLISHED_FULL=1` (decision 2).

**Who acts.** Maintainer (merge order, the `docs/versions.md` wave-3 table updated to this order); executor and reviewer per branch; tester for the batteries and the refreeze. **Maintainer to confirm** the order (it is the plan of his release).

**Risk.** The serial order makes wave 3 long (four model branches plus the face film, each a whole battery of about 45 minutes); running the reviews in parallel with the next executor is allowed (writing work), the batteries are not. A model fix that fails review late pushes `fix/face-film-half-slab` and the refreeze with it.

## 10. Undo of a board edit also undoes a later change of the solver options

**Options.** (a) Keep: the undo snapshot holds the whole project, options included, and the docstring is corrected to say so; (b) undo and redo keep the current options: `Document._restore` carries `project.options` over the restored snapshot, as it already carries `project.package`.

**Evidence.** `releases/2.8.0/reviews/board-dock-write-back.md`, finding 1 and the open decision: edit `h_top`, add two vias, set the cell to 0.7 mm, undo: the project goes back to 1.0 mm (on `development` the dock still showed 0.7 and the next edit wrote it back; on the branch the dock now reloads and shows 1.0). `Document.set_options` (`pcbthermal/gui/document.py`, line 537 on `development`) says 'Change solver options (not part of the undo history)': a change of the options is never an undo step of its own, so it cannot be redone or undone by itself; it is only lost, as a side effect, when an earlier board edit is undone. `_restore` (line 156) rebuilds the project from the JSON snapshot and carries over only `project.package`. The options (`SolverOptions`: models, cell, solver, laminate options, memory fraction is a machine preference and not in them) do not depend on the board geometry, so the current options are valid for any restored board; the cell verdict and the memory check are recomputed on `changed` anyway.

**Decision.** (b). The user's model and cell choice is not part of the edit he undoes, and the documented contract is that it is outside the history; the code is brought to the contract, not the contract to the code. `_restore` keeps `self.project.options` (a deep copy is not needed: the object is replaced, not shared with the snapshot). Redo the same. A test: change `h_top`, change the cell and the models, undo and redo, assert the board edit is undone and redone and the options stay; and the dirty flag follows the board edit only.

**Who acts.** Executor on `fix/board-dock-write-back` (the same topic, before its merge; the 'no branch for its own sake' rule); reviewer re-check of the two changes; maintainer with the whole battery.

**Risk.** Low. A project whose options were changed and then every edit undone is no longer 'clean' only by its options: `set_options` already emits `state_changed` without touching the clean flag, so the window title may say saved while the options differ from the file (the same as today after any option change); recorded as known, not changed.

## 11. Preferences boxes and values outside their range

**Options.** (a) Leave: the box shows a clamped value, Save writes the stored value (each box writes only its own key when edited); (b) widen each box to its loaded value with `gui/spinfit.fit_range`, as the docks and the four dialogs of the review now do.

**Evidence.** The review of `fix/board-dock-write-back` ('Checked and found right', last Preferences bullet): a saved value outside a box's range is shown clamped (analytic modes 500 000 shown as 100 000, `h_top` 2.5e9 shown as 1e9) but Save writes the stored value. So nothing is lost, but the dialog shows a number that is not the one in `user_defaults.json` and not the one a new project will get: the same class of mismatch the branch removed from the docks, and a user who edits the shown value and then types it back writes the clamped one. `fit_range` already handles non-finite values and the C int limit (finding 3 of the review).

**Decision.** (b): `fit_range` before `setValue` in every numeric box of the Preferences pages, so the dialog shows what is stored. The ranges of the boxes stay as the hints of what is typical; a value beyond them is shown, not clamped. A test: write a `user_defaults.json` with two out-of-range values (an integer and a float), open Preferences, assert both are shown as stored and Save writes them unchanged.

**Who acts.** Executor on `fix/board-dock-write-back` with decision 10 (same topic); reviewer; maintainer.

**Risk.** Low (display only, no number moves). A very large value can widen a box's text; the docks' check that Qt truncates the size hint to 18 characters (`tests/test_dock_layout.py`) applies to the Preferences pages too: `tests/test_preferences_layout.py` runs on the branch.

## Summary

| # | decision | who acts | maintainer to confirm |
| --: | :-- | :-- | :-- |
| 1 | keep 5 % with the corrected bound | maintainer (merge) | no |
| 2 | T1 to T5 in the battery (~25 s, one-sided); T6 to T8 at the release gate | executor, reviewer, maintainer | no |
| 3 | accuracy quoted against an independent reference first, the FVM second and named | reviewer A4, A6, maintainer | yes |
| 4 | rewrite what the user reads or is cited as current; mark the rest 'superseded' | reviewer A2, A6, maintainer | yes |
| 5 | source copper, air and 0.447 before 2.8.0; mark FR-4, emissivity 0.9 and unsourced library entries 'typical, no source' | reviewer L10, L12; executor | no |
| 6 | keep 0.664 (exact for the modelled plate, safe side; 0.742 belongs to a composite on sqrt(A); +5 to +9 % of total h) | reviewer L5 (text) | no |
| 7 | implement the drawn source for the non-imported layers; a warning if it misses the release | executor, reviewer, maintainer | no |
| 8 | always, last of the model fixes, folded into the refreeze | executor, reviewer, maintainer | no |
| 9 | the order of section 9 | maintainer | yes |
| 10 | undo and redo keep the current solver options (as the docstring says) | executor on `fix/board-dock-write-back`, reviewer | no |
| 11 | Preferences boxes use `fit_range` like the docks | executor on `fix/board-dock-write-back`, reviewer | no |

## What was not verified here

The numbers of A1, the case 2 study and the drawn-copper review were read, not re-run (they were re-run by those reviews). The Yovanovich-Teertstra paper was not re-opened: the description of eq. 17 and 18 rests on `docs/theory.md` 8 and the transcription check recorded there. The film term of a metal block (decision 8) and the mixed imported and drawn board (decision 7) are unmeasured. Decisions 10 and 11 rest on the review of `fix/board-dock-write-back` and on a read of `Document._restore` and `Document.set_options` (`pcbthermal/gui/document.py` on `development`); no new GUI run was made here.
