# What we want to investigate

What is left to investigate, triaged against the tree of 2.7.0: the questions worth starting now (section 1), the order table (section 2), the open pool by area (section 3), the questions closed since (section 4), and the physical measurement (section 5). A defect of the program found by a study is recorded in the README of its folder; its correction is an item of `docs/versions.md` (chapter "Planned"), the only place where program work is listed. The register of the reviews is [`REVIEW.md`](REVIEW.md); the index of the folders is [`README.md`](README.md).

**Rule.** An item leaves the open lists when its study is finished and the result is in the README of its folder; its label is kept in section 4 because other documents cite it. An item that changes a model needs the reviewer before it is closed. Status keys: `ready` open and can start now, `partly` the main question is answered and leftovers stay, `blocked` waits on a named decision, source or measurement, `feature` needs a program feature first, `done` closed. Value: H, M or L for the program. Effort: h hours, d days, w weeks.

## 1. Worth investigating now

Two groups. **For 2.7.0** (the version being closed): rows 1 (branch `research/strong-edge-laminate`), 2 (a decision is pending) and 8 (branch `research/small-model-defects`). **Candidates for 2.8.0, because they may become features** (not part of 2.7.0): rows 3, 4, 5, 6 and 7.

| # | Question | Why now | Unlocks | Effort |
| --: | :-- | :-- | :-- | :-- |
| 1 | A34 with A16 above 200 W/m2K: the via effect and the laminate at a strong edge | **partly** (`research/strong-edge-laminate`, reviewed: go): no converged residual; the error is the default two sub-gaps plus the equal slabs T / L of the simple stack-up of three or more layers (plate -8.9 % at 1000 W/m2K, 0.25 mm; +0.4 % with physical slabs and eight sub-gaps); warning text corrected on `fix/edge-laminate-warning-text` | the maintainer's decision on the simple-stack-up slabs (`strong-edge-laminate/INTEGRATION.md` 1) | done |
| 2 | A33 with A26: the centroid edge film on the drawn layers | **done**: implemented for the drawn layers too (`fix/drawn-layers-edge-film-centroid`, reviewed: GO, merged); what is left is the new first-order hot error at copper that touches the outline (at most +1.5 %, the safe side) and the idealisation of four sub-gaps (-2 %), both limits | closed; the refreeze folds the pending file | - |
| 3 | E13 (b) and (c): the converged reference of small imported parts | the FVM moves 15 to 30 % from 0.5 to 0.25 mm on an 0402, so every number of the reduced-model warning (25 to 82 % cool) rests on an unconverged reference; a refinement around the powered part, checked against an independent solver | E3 (the largest user-visible error of the reduced models); re-measure the warning | d, memory-heavy |
| 4 | B5: plated component holes as vias and vias with a layer span | blind and buried vias are modelled as through vias (unsafe side, only warned); a study against the 3D solid of component holes (lead and solder) as vias | the 2.8.0 import option of item 17 of 'Planned: 2.7.0'; a real model instead of a warning | 2 to 3 d |
| 5 | A18: the local laminate rule, second study round | small parts on thick boards read 16 to 20 % too cool and only a warning covers it; the gate on the cell (4 cells), the conservative transition, the cost with many small parts | a `fix/` branch for 2.7 (moves frozen numbers) | d |
| 6 | A27: the Lumped first link alone (with the 'first link and ring 1 on a finer raster' and the near-edge correction of `docs/versions.md`) | the near-edge deficit (4 to 15 % cool, -7.4 % on the sweep) is the main remaining Lumped error | one place for one question | d |
| 7 | G1: the first measurement dataset. The maintainer has no measured board yet, but a colleague built one and his data may be the first dataset (section 5); if it is not enough, order the boards of the plan | the physical measurement is the only way to choose the face-up law and to remove the line 'never compared with a measured copper board'; the fabrication lead time is the long pole; add a square-wave run on board B to give A31 a measured fast-wave case | C8 face up; a measured via effect | 1 to 2 d of bench plus the lead time |
| 8 | A35, A36, A37: the cheap possible defects (study done on `research/small-model-defects`; the fixes wait on their own branches, not merged: A35 on `fix/lumped-via-groups-lone-via`, A36 on `fix/fdm-harmonic-face-mean`; A37 is a limit; the via well sheet order is closed and reviewed on `research/via-well-sheet-order`: keep, pin test and theory 2.6 sentence to adopt) | the Lumped that heats when a far via is added, the FDM 10 % low on separate zones, the 3D solid asymmetric with vias on a grid line; each is a defect or a sentence in the limits | hours each | h |

## 2. The order table

Rows keep their numbers because other documents cite them. Rows 1 to 3, 5 to 9b, 11, 11b, 11c, 12, 13b to 13d, 16b and the long runs are done and removed; row 4 is the decision list of `REVIEW.md`.

| # | What | Folder | Done when |
| --: | :-- | :-- | :-- |
| 4 | The decisions left to the maintainer | `REVIEW.md`, last sections | each taken; only E10, E5, E8 and A2 P2 are still open |
| 10 | A2, the Analytic model on boards with partial copper | `analytic-partial-copper` | P1 (the warning trigger) is in the program since 2.4.5; the maintainer adopts P2 (about a week) or keeps the stated limit P3 |
| 13 | C3, the channel effect between close fins | `fin-channel` | A is in 2.4.4; B waits for C3a and C3b |
| 14 | D1, the JEDEC board of the calculator | `power-calculator` | JESD51-3/-7 read (a free download after registration: the block is the registration), the board rebuilt, rows moved to a 0.25 mm cell |
| 15 | The Gerber items that remain: E3 (after E13 b), E4, E6, E7, then E5 and E8 | `gerber-*` | each as its item says; E2 is decided (the default mapping is confirmed) and E11 is done |
| 16 | The theory sources still partly open | F1, F3, F5, F6 | a status raised in `theory/BIBLIOGRAPHY.md` only with a record of the reading; F2, F4, F7 and F8 are done; F9 dropped |
| 17 | G1, a measurement on a physical board | `convection-laws/docs/measurement-plan.md` | section 5 |

## 3. The pool, by area

### A. Models and numerics

| id | question | status | where | value | effort | blocker |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| A2 | Analytic too cool on partial copper | partly | P1 in 2.4.5; candidate P2 in `analytic-partial-copper` | M | d (P2 w) | maintainer: adopt P2 or keep the limit |
| A7 | Analytic against the FVM, insulated edges (-0.04 to -0.29 %) | ready | `theory` topic 37 | L | h | - |
| A8 | transient with a block and of the 3D solid | feature | `block-and-fins/INTEGRATION.md` | M | d | a block transient in the Lumped and Analytic |
| A9 | outline scaling, holes, parts in a cut (with H6) | ready | `outline` 4.2, validation 13 | M | d | - |
| A10 | multigrid and solver timings (with H6) | ready | `theory` 7 | L | h to d | - |
| A12 leftovers | bare spot under a source: the FDM, windows narrower than the gap (-9 %) | partly | `bare-spot-under-source` | L | d | - |
| A14 | via target radius by stack-up | ready | `point-via-convergence` 9, `via-contact-geometry` 7.1 | M | d | safe side, 2 to 14 % |
| A15 | via near an edge: the FDM, the 3D solid, curved and short sides; **and the unexplained 3D solid on the L shape**: it reads -3.3 % of the FVM at 1 mm (it was -1.9 % at 2.4.5) while its own rise is unchanged (100.043 K); the FVM moved with the via mirror image (+1.18 K) and the via barrel (+0.25 K) and the 3D solid has no image of the edge in its via rule, so whether the FVM is high or the 3D solid low there is not established (`docs/validation.md` 12, the 3D solid paragraph) | partly | `via-edge-image`; the FVM done in 2.5.0 | L to M | d | an independent reference on an L outline with vias beside the inner walls |
| A16 | the laminate at the board edge above 200 W/m2K | partly | 2.6.0 `fix/laminate-edge-band`, validation 36 | H | d | overlaps A34; on boards of three or more layers in the simple stack-up the equal slabs add to it (`strong-edge-laminate` README 8.2) |
| A18 | source-aware local laminate rule | partly | `laminate-slabs-and-local-rule` INTEGRATION 1.0 | M to H | d | the gate and the conservative transition study before code |
| A19 leftovers | Analytic: the partial-copper transient (+23 %), several parts, outlines | partly | `analytic-edge-and-transient` | L to M | d | - |
| A27 | Lumped first link alone, with the near-edge correction and ring 1 on a finer raster | ready | `lumped-near-edge` 10, `lumped-ring-uniform-deficit/INTEGRATION.md` 4 | M | d | - |
| A29 | the edge laminate limit of the Lumped and Analytic | ready | `laminate-edge-band` README | M | d | warned today |
| A30 | the corner of a copper region and the end of a track at a via (what is left of A20) | ready | `via-contact-geometry/INTEGRATION.md` 4 | M | d | safe side (15 to 85 % low); sector-well prototype |
| A31 leftovers | fast waves: the neighbour cross term, vias, the Lumped and Analytic, a measured case | partly | validation 37 | L to M | d | the measured case needs G1 |
| A32 | node-centred FDM cut cells (with the former A24) | ready | `docs/evidence/fdm_cutcells_prototype.diff` | L to M | d | the FVM scheme did not transfer: the FDM needs a scheme of its own |
| A33 | the centroid edge film for the drawn layers (done, 2.7.0); the four-sub-gap idealisation at the edge (-2 %, a known limit) | partly | `imported-copper-edge-film/` README 8; validation 40 | L | d | the limit is accepted or not by the maintainer |
| A34 | the via effect near a cooled edge at `h_side` 1000 against an independent 3D solver | partly (answered: `research/strong-edge-laminate` README 8): not a via defect away from the wall (within 0.6 % at 0.5 to 3 mm with physical slabs and 8 sub-gaps); left: a via within one cell of a wall above 500 W/m2K (-7 to -13 % at 0.25 mm, the reference 5 % uncertain there) and a structurally different solver | item 21 of 'Planned: 2.7.0'; validation 28 | M | 1 d | decision: simple-stack-up slabs |
| A35 | the Lumped heats by 0.80 to 0.89 K when a far via is added (the FVM cools) | ready, possible defect | 'Fixes waiting' of `docs/versions.md` | M | h | - |
| A36 | the FDM 10 % below the FVM at 1 mm on a four-layer board with separate zones; the Lumped mirror asymmetry of 0.4 K | ready, possible defect | 'Fixes waiting' of `docs/versions.md` | M | h to d | - |
| A37 | the 3D solid not mirror-symmetric with vias on a grid line (0.36 K) | ready | 'Fixes waiting' of `docs/versions.md` | L | h | - |
| A38 | the via rim test on imported copper (every via joined to every layer, also through an antipad) | answered (`research/imported-via-rim`, reviewed: go): today 0 to 4.4 % cool on five real boards (upper bound, against the ray rule), +46 / +12 % on the via effect of a synthetic antipad at 1 / 0.5 mm; the ray test from the masks is the proposal | `imported-via-rim/INTEGRATION.md` | L | h | implementation on `fix/imported-via-rim-mask` (reviewed separately); the reach (0.5 mm) is the maintainer's |

### B. Boards, vias and stack-up

| id | question | status | where | value | effort | blocker |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| B1 | inner layers at 30 to 70 % copper | ready | `stackup` 4.6 | M | h to d | - |
| B2 | missing stack-up data | partly | `stackup` | L | ongoing | fabricator data |
| B3 | sources for the via-fill conductivities | ready | `via-fill` | L | h | - |
| B4 | dielectric and copper sensitivity beyond four layers | partly | `stackup` 7 | L to M | h | - |
| B5 | plated component holes as vias, and vias with a layer span (blind, buried, micro) | ready | item 17 of 'Planned: 2.7.0'; the span warning of 2.7.0 | M to H | 2 to 3 d | - |

### C. Parts, heatsinks and blocks

| id | question | status | where | value | effort | blocker |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| C1 | the junction node | partly | `component-heatsink` 4.10 | M | d | feature (a junction node in the models) |
| C2 | heatsink scenarios and a catalogue | partly | `component-heatsink` 7 | L to M | d | the guide and curves to open |
| C3 | the channel effect between fins (B open) | partly | A in 2.4.4 | M | d | C3a, C3b |
| C3a | open-front arrays and horizontal orientations | blocked | `fin-channel-sources` 7 | M | d | no fins-down data; originals paywalled |
| C3b | the originals of the channel effect | blocked | `fin-channel-sources` 9 | L | h after the fetch | the maintainer fetches the paywalled papers |
| C4 | the Foster chain, the top path in time | feature | `component-heatsink` 4.9 | M | d to w | a transient top path |
| C5 | a heatsink larger than its contact | ready | `component-heatsink/NOTES.md` R3, R8 | L to M | d | - |
| C6 | assumed datasheet values | partly | `component-heatsink` 7 | L | h | - |
| C8 | the plate level: the face up (the face down is done in 2.6.0) | blocked | `plate-h-level`, `face-down-convection` | M | - | the measurement G1, board D |
| C9 | radiation between fins, fins down | blocked | `fin-channel` | L | d | no measurement |
| C10 | local h on a poor conductor | ready | `paper-case-studies` 13.3 | L | d | safe side |

### D. Calculators

| id | question | status | where | value | effort | blocker |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| D1 | the JEDEC board of the calculator | blocked | `power-calculator` 4.5 | M | d | JESD51-3/-5/-7 registration (free) |
| D2 | the known-power reference, the two-point fit | partly | `power-calculator` | L | d | - |
| D3 | assumed inputs of the validation | ready | `power-calculator` | L | h | - |
| D4 | the band and the drawing errors | partly | the design-uncertainty term of 2.4.2 | L | h | the board-size term is not added |

### E. Gerber

| id | question | status | where | value | effort | blocker |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| E1 | diagonal faces (parked: failed the held-out set) | partly | `gerber-models` 4.48, 4.50 | L | d | park |
| E3 | the Lumped and Analytic with a mask | ready | `gerber-models` 4.35; the warning (25 to 82 % cool on 42 parts) | H | w | needs the reference of E13 (b) first |
| E4 | missing validation scenarios | ready | `gerber-models/CONCLUSIONS.md` | L to M | d | - |
| E5 | hatched zones, the pattern | blocked | `gerber-models/INTEGRATION.md` 5, 6 | M | d | maintainer |
| E6 | fine cells and time, imported | ready | `gerber-models`, last section | M | d | - |
| E7 | reader conformance (the Ucamco sets) | ready | `gerber-import` 4.17 | L | h | the study was killed at load in the audit |
| E8 | nets with voltage and current | feature | `gerber-nets` | M | w | the electro-thermal feature, maintainer |
| E9 | thin tracks at an angle (tied to E1, parked) | partly | `gerber-nets` 4.23 | L | d | - |
| E10 | LM, LR, LS and AB | blocked | `gerber-import` 4.19 | L | d | maintainer decision; count the usage first |
| E12 | CAD profiles of untested tools | blocked | `gerber-cad-profiles` 10.5 | L to M | d | real sample files |
| E13 | the reduced models on small imported parts; (b) and (c) open: the converged reference | partly | (a) done in 2.6.0 (first ring) | H | d to w | - |
| E15 | the BOM role on other CAD names (deferred with the BOM role) | blocked | the maintainer deferred the BOM role | L | - | returns with a BOM feature |

### F. Theory and sources

| id | question | status | where | value | effort | blocker |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| F1 | the effective conductivity above Biot 60 | ready | `theory-sources` 3.6 | L | h | - |
| F3 | the convection originals | partly | `theory-sources` 3.1 to 3.4 | L | - | paywalled |
| F5 | sources to open | partly | `theory/BIBLIOGRAPHY.md` section 18 | L | ongoing | paywalls |
| F6 | planned models without a source | partly | `theory-sources` 3.8 to 3.12 | L | d | topic 14 needs the JEDEC registration |

### G and H

| id | question | status | where | value | effort | blocker |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| G1 | a measurement on a physical board; the first dataset may come from a colleague's board (section 5) | blocked | `convection-laws/docs/measurement-plan.md`, `models-comparison/docs/measurement-protocol.md` | H | 1 to 2 d of bench plus the board lead time | boards, logger, supply |
| H6 | numbers that need a script before they are quoted (A9, A10) | ready | - | L | h | - |
| H7 | the memory law at 8 to 16 slabs; the 3D solid of the eight-layer board is refused (15.2 GB estimate, never compared with a measured peak) | ready | 'Left over by the memory guard' of `docs/versions.md`; `releases/2.7.0/research-audit` 6 | M | h to d, heavy | - |
| H8 | `laminate-slabs-and-local-rule/scripts/study_solid_slices.py` counts the 3D face term twice | ready (a study defect) | `releases/2.7.0/research-audit` 6 | L | h | - |

## 4. Closed since (the labels stay because other documents cite them)

| id | outcome |
| :-- | :-- |
| A1, A11, A12 | the laminate nodes and warnings for patterned copper, 2.4.5 (A12 leftovers above) |
| A3 | the rotated square: exact board cover, cut-cell links and the 3D sliver fix, 2.6.0 (leftovers A25, A26) |
| A5, A6, A13 | the mean-potential via, the via constriction and zones in the reduced models, the block SOR, 2.4.5 and 2.5.0 |
| A17 | 3D solid slabs by thickness, 2.6.0 |
| A19 | the Analytic per-layer edge and local transient, 2.6.0 (leftovers above) |
| A20, A22 | the via barrel length and the rim uncoupling, 2.6.0 (leftover A30) |
| A21, A23 | the Lumped near an edge: warning and small-part raster, 2.6.0 (A21 was a duplicate of A23; leftover A27) |
| A24 | merged into A32 |
| A25 | the pixel mask of the outline for imported copper, 2.7.0 (validation 38; the edge-film bias is A33) |
| A26 | the copper edge held inside the outline: the imported layers by the outline mask and the drawn zones by the centroid edge film, 2.7.0 (validation 38 to 40) |
| A28, A31 | fast power waves, 2.6.0 (validation 37; A28 was closed by A31; leftovers above) |
| C7 | the plate level on the vertical face: proposal A in 2.5.0, `plate-h-level` closed |
| E2 | the default mapping of the imported copper: flow-based faces on the reduced sheet, confirmed by the maintainer (a nine-point reference is left for later) |
| E11 | the heater from the paste layer and the designator, 2.5.0 |
| F2 | the Muzychka and Lemczyk cases reproduced (`theory-sources` 3.7) |
| F4 | the formulas written from memory checked (`theory-sources` 3.5) |
| F7 | grid convergence of the references (`theory-sources` 3.10) |
| F8 | papers read only in part (`theory-sources` 3.11) |
| F9 | dropped: the legacy rows are marked as quoted, not re-run |
| the long runs | the twelve long runs reproduced the READMEs to the digit except the cost numbers of the 3D solid and the layered FVM and of the mappings, corrected in the research documents and in the program documents; the guard by estimated memory replaced the old limit |

## 5. G1: what exactly is needed

From `convection-laws/docs/measurement-plan.md` (the newer plan; `models-comparison/docs/measurement-protocol.md` is the older one).

| item | content |
| :-- | :-- |
| Boards | five boards each of four designs, 100 x 80 mm, 1.6 mm FR-4, 35 um, two layers: A full copper both sides with mask (the multiplier on h); B a 20 x 20 mm pad both sides (local heating); C as B with a 3 x 3 array of 0.3 mm vias at 1.3 mm pitch (6 x 6 if the effect is too small: +6 % of the power is predicted); D full copper, no mask on top, ENIG (bright face, the up and down law test); E is board A with a film heater and no foam (face coupling); about 100 to 150 EUR of boards |
| Heaters | two 2512 4.7 ohm 2 W resistors in series on A, B and C (four-wire V sensing); a 90 x 70 mm 12 V film heater for D and E |
| Instruments | a supply with current limit, a 0.1 % voltmeter and a 0.2 % ammeter (or two bench multimeters), a six-channel type K logger with 0.1 K resolution, 3 m of 36 AWG type K wire, Kapton tape, epoxy, 30 mm of mineral-wool board (XPS softens near 75 degC), needle supports, a cardboard draught shield, smoke or an anemometer to prove still air |
| Procedure | isothermal offset of the thermocouples (30 min); T1 under the heater on the bottom, four on the top at 14, 26, 24 and 42 mm, T6 in shielded air; horizontal up, turned over and vertical; three powers per board (A 0.75, 1.5, 2.25 W; B 0.3, 0.6, 0.9 W; C 0.33, 0.66, 1.0 W), 30 min per point, accepted at dT/dt below 0.02 K/min; D at 2 and 4 W up and down; E at 3, 6, 12 W; an afternoon per set once built |
| What it decides | fit the multiplier m on A, predict B, C, turned and vertical within 5 % of the rise (budget 2 to 3 %); the ratio rise(up) / rise(down) of D picks the face-up law (program 0.63, Raithby-Hollands with Goldstein-Lau 0.69, with Fujii-Imura 0.66, Jaffer 0.52; resolution about +-0.03, so neighbouring laws may stay undecided); E shows a face coupling of 10 % or more. A local-heater board is almost blind to the convection law (0.5 %): A to C validate the board model (spreading, vias, radiation), only D chooses the law |
| Closes | G1, the face-up half of C8, the line 'never compared with a measured copper board' of the Results summary; a measured via effect (C); with a square-wave run on B, a measured fast-wave case for A31 |
| Not covered | fins (C3a, C9), strong edges (A34, A16); the program cannot mix a computed h on one face and a manual h on the other (D and E are one-dimensional balances, recorded as a limit) |
| The colleague's board | the maintainer has no measured board of his own, but a colleague built one and he will try to use that data as the first measurement dataset. It can serve as board B or C of the plan above only if the data below exist; otherwise it is a case study with larger uncertainty (stated, not hidden). **What we need from the colleague** (the request list is in the next row) |
| Request list for the colleague | (1) the stack-up: number of layers, copper weight per layer, dielectric thicknesses, board outline and size, the finish; (2) the copper layout: the Gerber files or a drawing of every layer, with the drills; (3) the power per part: which parts dissipate, how many watts, constant or switched, how the power was measured; (4) the ambient temperature and how it was measured; (5) the setting: orientation (flat face up, face down, vertical), whether it was in free air or in an enclosure, any fan, any heatsink, the mounting (standoffs, a table, foam); (6) the temperature measurements: for each thermocouple or IR reading its position on the board (a photo with marks or coordinates), the layer or face it was on, the emissivity used for IR, and the time the board had been powered (steady state or not); (7) the measured temperatures themselves, a table or the logger file; (8) the uncertainties: the instrument accuracy, the calibration, the repeatability if the run was repeated; (9) a photograph of the board and the setup. The minimum that already helps: stack-up, layout, power of one part, ambient, orientation and one temperature next to that part |
| Decision for the maintainer | build and measure (about 200 to 300 EUR with parts, if a logger and a supply are at hand), or keep looking for public data with known power and copper |
