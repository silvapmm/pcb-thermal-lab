# What we want to investigate

The plan of the research: what is left to finish, in the order recommended (section 1), and the pool of questions by area (section 2). An investigation that finds a defect of the program records it in the README of its folder; the correction is an item of `docs/roadmap.md` (the list of what we want to implement in the program), which is the only place where program work is listed. The register of what the independent reviewer checked in each folder is [`REVIEW.md`](REVIEW.md); the index of the folders is [`INDEX.md`](INDEX.md).

**Rule.** An item leaves this document when its study is finished and its result is in the README of the folder (the question and the answer are then documented there). The table of section 1 is the only place with the order; the pool lists questions without an order. A pool item that is in the table keeps a line 'see Next work #N' and only the details that the table does not hold. An item that changes a model needs the reviewer before it is closed.

Pool items have the fields **Question**, **Why** (the evidence: folder and section), **First study**, **If it ends well** (what would change in the program, with the item of `docs/roadmap.md` when there is one) and **Status** (`open`: nothing done; `partly`: a first look exists; `waits`: needs a decision or a condition).

## 1. Next work, in the order recommended

Rows 3 to 6 close the present round (rows 1 and 2, the long runs and the figures that depend on them, are done: section 3; the rows keep their numbers because other documents cite them) (the reviews and corrections of the folders); rows 7 to 12 are the investigations whose result blocks program work of `docs/roadmap.md` "Next work" (they come first because the program branch waits for the answer); rows 13 to 17 do not block anything. The program work itself is only in `docs/roadmap.md`, section "Next work, in the order recommended" (`develop`): nothing of it is repeated here.

| # | What | Folder or item | Evidence to start from | Done when / what it produces |
| --: | :-- | :-- | :-- | :-- |
| 3 | **The program documents with the measured times** (a program documents branch off `develop`, not this branch) | `docs/roadmap.md` Next work #9 | the measured times of section 3 (`solid3d-verification` README and the table in its `docs/for-the-project-documents.md`: the documents' times are 20 to 40 times too long); the same numbers feed the memory guard (`docs/roadmap.md` Next work #2) | handed to the maintainer with the numbers; nothing is edited here |
| 4 | **The decisions left to the coordinator** | list in [`REVIEW.md`](REVIEW.md), last section | each has a recommendation to start from | taken now that the runs are finished; the ones that need a study become rows below |
| 5 | **Merge `develop` into this branch**, adopting the `CLAUDE.md` of `develop` | the whole branch | the five Decisions Log entries of the research rules are in `develop`; the notes 'lives only on the research branch' of the structure lines of `CLAUDE.md` and of `INDEX.md` become false on the research branch and are adjusted; stale pointers that the merge may leave: `outline/scripts/study_edge_on_grid_lines.py` (patched a function that has changed) and the numbers of `outline/README.md`; `theory/topics/01-layered-idealisation.md` and `theory/README.md` naming `fig_04_the_five_models_schematic.png` (now `fig_08`); `theory/topics/20-board-outline.md` repeating stale ranges of `outline/`; the figure numbers of `models-comparison/` and `solid3d-verification/` | merge done; the research tests and `tests/test_docs.py` pass; `docs/` and `CLAUDE.md` identical to `develop`; the links fixed |
| 6 | **Publication** | `develop` is 14 commits ahead of `origin/develop` and this branch 82 commits ahead of `origin/research/gerbers` | | push only on the maintainer's word |
| 7 | **A5, the point via and the cell** (Peaceman radius against spreading the barrel over its disc) | `via-fill`; blocks `docs/roadmap.md` Next work #3 | the copper-fill gain is -4.46 K in the independent solver against -4.78 / -4.38 / -3.98 / -3.64 / -3.34 K at 1 / 0.5 / 0.25 / 0.125 / 0.0625 mm (`via-fill/README.md` 7.3); the Gerber boards run at fine cells | both treatments compared against `layered3d.py` with resolved barrels from 1 to 0.0625 mm on two boards, the winner chosen, the tables of `docs/validation.md` 2.1 re-run; the reviewer |
| 8 | **A6, Lumped and Analytic overstate the vias** | `via-fill`; feeds Next work #8 | copper-fill gain -6.0 to -6.8 K against -4.45 K (35 to 52 % too large); the models were tuned against the FVM, which is itself off at fine cells | after row 7, which part of the construction carries it; a correction of the via term or a warning in the report |
| 9 | **A1, subdivide the gap of the multilayer boards** | `power-calculator`, `effective-conductivity`; feeds Next work #8 | a 2-layer board reads 2 to 8 % low in the FVM against the independent solver (-2.3, -3.8, -7.7 % on three boards; the same pad on both faces gives -3.9 %) | the sweep of 1 to 4 nodes on 2, 3 and 4-layer boards against `layered3d.py`; the script of the measurement versioned in `power-calculator/scripts/`; a new table for `docs/validation.md`; the reviewer |
| 10 | **A2, the Analytic model on one-layer boards with partial copper** | `power-calculator`, `docs/validation.md` 21; feeds Next work #8 | Analytic 5.5 % mean error before and after the laminate film; -32 % to -13 % on a 2-layer board with a 20 mm pad | the three candidate causes separated (uniform sheet, film in series, local corrections); a better estimate or a stated limit |
| 11 | **A3, the rotated square in the 3D solid at a high side coefficient** | `solid3d-verification`, `outline`; feeds Next work #8 | +1.15 K above the aligned square, only with a high `h_side` | the edge conductance per cell compared with `geometry.edge_length_on_board`; a correction or a documented limit |
| 12 | **A11, the laminate nodes for patterned copper** (review R2 of `gerber-models`) | `gerber-models`; feeds Next work #8 | the two laminate nodes of a one-layer board are 5.5 to 13.6 % cool on patterned copper against an independent 3D solution (seven real windows; 1.9 and 5.3 % with eight nodes) | the number of nodes (and whether it depends on the copper pattern) chosen on the windows and on solid copper and pads together, so that the earlier fit is not lost; the reviewer |
| 13 | **C3, the channel effect between close fins** (blocks Next work #6; added to the list because the program item waits for it) | `block-and-fins` | the warning at 4 mm; a remembered correlation puts a 6.5 mm gap 10 to 30 % below the typed coefficient; Elenbaas (1942) and Bar-Cohen and Rohsenow (1984) never opened | both papers read, the Elenbaas channel correlation and its optimum spacing reproduced and compared with the finned FVM block; a threshold or a correlation proposed |
| 14 | **D1, the JEDEC board of the calculator** | `power-calculator` | JESD51-3, JESD51-5 and JESD51-7 are behind a login; ROHM's table reads a 70 um backside plane and the JEDEC row is +23 % with it | the standards read, the board rebuilt, the rows moved to a 0.25 mm cell; `docs/calculators.md` text |
| 15 | **The Gerber items**, in this order: E2 (default copper mapping against a finer reference), E1 with E9 (diagonal faces and tilted tracks), E6 (fine cells and time), E3 (Lumped and Analytic with a mask), E7 and E10 (reader conformance and the transformed apertures), E4 (missing validation scenarios), E5 and E8 (wait for the maintainer's decision) | `gerber-models`, `gerber-import`, `gerber-nets` | the pool items E1 to E10 | each as its item says; the Gerber import and the `copper_mapping` option of `docs/roadmap.md` are decided by E2 |
| 16 | **The theory sources**, in the order that the other items need them (C3, D1, F1, F3, F4, E7), then the rest | F1 to F9 | statuses M, N and S in `theory/BIBLIOGRAPHY.md` | a status raised only with a record of the reading |
| 17 | **G1, a measurement on a physical board** | `models-comparison/docs/measurement-protocol.md` | no model has been compared with a physical board | the board built and measured, or public measured data found; waits for a board and an instrument |

The rest of the pool (A7 to A10, B1 to B4, C1, C2, C4 to C6, D2 to D4, H6) has no place in the order: each is taken when a program feature or a review needs its answer, and then gets a row here.

## 2. The pool of questions

Questions by area, without an order; the labels A to H are kept when an item leaves (A4, for example, was the clean-machine timing: done, section 3). Section 3 is the detailed plan of the long runs.

| Area | Items |
| :-- | :-- |
| A. Models and numerics | A1 to A3, A5 to A11 (A4 is done, section 3) |
| B. Boards, vias and stack-up | B1 to B4 |
| C. Parts, heatsinks and blocks | C1 to C6 |
| D. Calculators | D1 to D4 |
| E. Gerber import and models | E1 to E10 |
| F. Theory, sources and verification | F1 to F9 |
| G. Physical measurement | G1 |
| H. Tooling and method | H6 (the long runs are done, section 3) |

The labels are kept when an item leaves, so that the citations between documents stay valid.


## A. Models and numerics

### A1. Subdivide the gap of every multilayer board
* **Order**: see Next work #9.
* **Question**: does more than one node through the dielectric gap of a multilayer board remove the error of the layered models against a resolved 3D solution?
* **Details not in the table**: the error belongs to every 2-layer board and not to a bare bottom (`power-calculator/` 4.5 to 4.7; `effective-conductivity/` 4.11 for the one-layer case that the laminate nodes already fixed); treating only a bare bottom as a one-layer board would make identical 2-layer boards inconsistent. The sweep is that of the one-layer laminate (`laminate.py`), on boards with full copper, a pad, a part and vias; the measurement above was run from a scratch directory and has to be versioned before the numbers are quoted.
* **If it ends well**: a change of every 2- and 3-layer result in the FVM, FDM and Lumped (`docs/roadmap.md`, models); until then the error is only documented.
* **Status**: open.

### A2. Why the Analytic model is hot on one-layer boards with partial copper
* **Order**: see Next work #10.
* **Question**: what makes the Analytic estimate too hot on a one-layer board whose copper does not cover the board, and is there a cheaper variant for the Analytic model alone?
* **Details not in the table**: the variant for the Analytic alone on a 2-layer board with a 20 mm pad still reads -32 % to -13 % (`power-calculator/` 4.7); the first study separates the candidate causes on a pad of growing size against the independent solver.
* **Status**: open.

### A3. The 3D solid with a rotated square at a high side coefficient
* **Order**: see Next work #11.
* **Question**: why does a rotated square source read +1.15 K above the aligned square in the 3D solid when the side coefficient is high?
* **Details not in the table**: seen in the reviews of `solid3d-verification/` and `outline/`; the aligned square agrees with the FVM. First study: rotate the square and the board edge separately on a copy, vary `h_side` and the cell.
* **Status**: open.

### A5. The point via and the cell: Peaceman radius against spreading
* **Order**: see Next work #7.
* **Question**: which treatment makes the via of the FVM and FDM converge with the cell: the Peaceman well index (`r_eq = 0.198 dx`, spreading only when `r_eq <= r_v`), or always spreading the barrel over the cells of its disc?
* **Details not in the table**: the example board gives -4.49 / -3.89 / -3.59 K at 1 / 0.5 / 0.25 mm; at 0.5 to 1 mm the error is 0.1 to 0.3 K (`via-fill/INTEGRATION.md` 1); the results with vias below 0.5 mm of the `gerber-models/` boards have to be read in this light. The 3D solid clipping of vias larger than a cell is a separate program item.
* **Status**: partly (the defect is measured, the two corrections are designed in `via-fill/INTEGRATION.md`, none is compared).

### A6. Why the Lumped and Analytic models overstate the effect of vias
* **Order**: see Next work #8.
* **Question**: why do the Lumped and Analytic models give a copper-fill gain 35 to 52 % larger than the reference, and which part of the construction (ring conductance, Green-function correction) carries it?
* **Details not in the table**: example board -6.3 to -7.0 K against -3.9 to -4.5 K (`via-fill/README.md` 7). First study, after A5: the fill sweep with one via, a row and an array, isolating the lateral spreading and the barrel conductance in each model. Decide first whether to investigate or only document.
* **Status**: open.

### A7. The residual between the Analytic and the FVM with insulated edges
* **Question**: what is the remaining -0.1 to -0.3 % between the Analytic and the FVM when both have insulated edges?
* **Why**: `theory/scripts/study_fvm_analytic_edges.py` shows the 0.3 to 1.0 % of `docs/validation.md` 2 and 4 is the edge loss that the cosine series leaves out; with insulated edges in both the gap is -0.04 to -0.29 % and is not explained (`theory/README.md` 7).
* **First study**: series truncation and the cell-centre against the mode projection of the sources, at several modes and cells.
* **If it ends well**: only an explanation in the documents.
* **Status**: open (small).

### A8. A time simulation with a block, and of the 3D solid
* **Question**: is a transient with a metal block in the Lumped and Analytic models, or of the 3D solid, worth building, and how accurate would it be?
* **Why**: today these have steady state only (`block-and-fins/INTEGRATION.md`, `solid3d-verification/README.md` 8).
* **First study**: the FVM transient with a block as the reference; a lumped capacity of the block in the ring network; the 3D solid with implicit Euler on small boards.
* **If it ends well**: the transient features of `docs/roadmap.md`.
* **Status**: open.

### A9. The outline: scaling, holes and parts inside a cut
* **Question**: is there a better rectangle than the one of the same area for the Lumped and Analytic models, and what happens with parts inside a cut region and with holes?
* **Why**: near the edge or in a T arm the same-area rectangle is 10 to 18 % cool (`outline/README.md` 4.2); scaling about the area centroid was tried and "gave no consistent gain" but no script prints it; the stretch of the field back over the real box was checked only for the maximum and the mean; the lost edge of 2 to 6.5 % over many outlines is the program's own sweep, not reproduced here (four shapes, 0.7 to 3.3 %).
* **First study**: a script for the centroid scaling; a sweep of outlines for the lost edge; maps (not only maximum and mean) of the stretched field against the FVM.
* **If it ends well**: a better equivalent geometry (`docs/roadmap.md`).
* **Status**: open.

### A10. Multigrid and the solver timings
* **Question**: do algebraic multigrid (PyAMG) or a multigrid-preconditioned CG pay for themselves against the direct solve on the boards and sizes of the program?
* **Why**: the timings quoted in `docs/roadmap.md` are printed by no script (`theory/README.md` 7); `theory/topics/16` describes it as planned, without a source for its formulas (smoother, restriction; Briggs and others is not opened).
* **First study**: a script that times direct, CG, SOR and AMG-CG on the example and on a 1 million unknown layered board, with memory.
* **If it ends well**: an option for large boards (`docs/roadmap.md`, solvers).
* **Status**: open.

### A11. The laminate nodes for patterned copper
* **Order**: see Next work #12.
* **Question**: how many laminate nodes under the copper of a one-layer board (two today) keep the FVM, FDM and Lumped within a few percent of an independent 3D solution on patterned copper without losing the fit on solid copper and pads?
* **Why**: review R2 of `gerber-models/` (`study_laminate_reference.py`, checked against `layered3d.py`): 5.5 to 13.6 % cool on seven real windows with two nodes, 1.9 and 5.3 % with eight; the two nodes were chosen from a sweep of 1 to 4 on a bare pad (`laminate.py`, `docs/validation.md`).
* **First study**: the sweep of 1 to 8 nodes on the seven windows, on the nine boards of the earlier sweep and on the pads, against the independent solution; the cost in unknowns.
* **If it ends well**: a change of `laminate.py` (`docs/roadmap.md` Next work #8); the 42-window studies of `gerber-models/` then use the program's network as the reference.
* **Status**: open.

## B. Boards, vias and stack-up

### B1. Real inner layers with 30 to 70 % copper
* **Question**: how far do the results move when the inner layers are signal layers with partial copper instead of full planes?
* **Why**: the stack-up study used one board and planes on every inner layer; a real inner layer lies between the 0.5 oz and the 1 oz results (`stackup/README.md` 4.6, limit a).
* **First study**: replace the planes of the 4-layer template by zones at 30, 50 and 70 % fill, with the mappings of `gerber-models/` as the way to express them, against `layered3d.py`.
* **If it ends well**: guidance in the user guide for the inner copper option, or an inner fill parameter.
* **Status**: open.

### B2. Stack-up data that is missing
* **Question**: what are the layer tables of blind and buried vias, sequential lamination, heavy copper and metal core boards, and of the fabricators that gave nothing usable?
* **Why**: not implemented and not surveyed (`stackup/README.md` last section); Sierra Circuits, Wuerth and Multi-CB gave nothing usable, no Ventec data; two tables (PCBWay's old 8-layer, PCBGOGO's 6-layer) do not add up to their stated thickness; the middle prepreg of the 6-layer template (200 um) is thicker than the 109 to 110 um of JLCPCB and PCBWay; only the 4-layer template is a fabricator's table (the 210.4 um prepreg is not confirmed).
* **First study**: open the pages and datasheets again, one table per fabricator with its status (read in full, extraction, not obtained), and the effect of each change on the 4- and 6-layer boards.
* **If it ends well**: better typical values in `pcbthermal/data/stackups.json`.
* **Status**: partly.

### B3. Sources for the via fill conductivities
* **Question**: which published values support the conductivities of the via fills (resin 0.3, conductive paste 8, electroplated copper) and the claims that were found in no source?
* **Why**: three fabricator pages re-opened (JLCPCB 0.3 / 8 / about 400 W/mK, ALLPCB, Atlas); "up to 16" and "silver 3 to 15 W/mK" were found in none of them (`via-fill/README.md` 7).
* **First study**: filler datasheets and the fabricators' pages; record the status of each.
* **If it ends well**: a corrected typical-value table (`defaults.json`, `via_fills`).
* **Status**: open.

### B4. Dielectric and copper sensitivity beyond the 4-layer board
* **Question**: how much do the dielectric conductivity and thickness and the copper weight move the temperature on boards without vias or with a one-layer pad?
* **Why**: "dielectric about 1 %, copper 5 %" holds only on the 4-layer board with vias; 2 to 3 % without vias, +8.7 / -6.1 % on a one-layer pad (`stackup/README.md` 7); the program and `layered3d.py` agree within 0.2 points.
* **First study**: extend `study_dielectric_sensitivity.py` to boards with other part and copper layouts.
* **If it ends well**: the guidance in the user guide and `docs/validation.md` 12.
* **Status**: partly.

## C. Parts, heatsinks and blocks

### C1. The junction node
* **Question**: when is a junction node (JESD15-3 two-resistor) worth having over the worst-case offset?
* **Why**: without a heatsink on top the node is 1.3 to 3.4 K below the worst-case offset; with a 12 K/W heatsink the top takes 41 to 51 % of the heat and the junction rise roughly halves (`component-heatsink/README.md` 4.10).
* **First study**: the prototype of `package_prototype.py` against more datasheet packages with both RθJC values.
* **If it ends well**: the junction node of `docs/roadmap.md` (parts).
* **Status**: partly (prototype only).

### C2. Heatsink scenarios and the catalogue values
* **Question**: how should theta_SA scale with the temperature rise and the flow (natural, forced, fan), and are the catalogue values of the library right?
* **Why**: the forced factors come from a guide (Electronics Cooling, 1995) and were compared with a few catalogue values only; the catalogue values of `defaults.json` come from distributor listings that were not re-opened; Seri Lee's spreading formula is from memory (`component-heatsink/README.md` 7; `heatsink_convection_study.py` is the first look).
* **First study**: open the guide and 10 catalogue curves; fit the exponent and the forced factors; check the base spreading against Lee's closed form (0 to 13 % above the study today).
* **If it ends well**: heatsink scenarios in `docs/roadmap.md` (parts).
* **Status**: partly.

### C3. The channel effect between close fins
* **Order**: see Next work #13.
* **Question**: what is the heat transfer coefficient between fins in still air as a function of gap and height, and where should the warning of the program sit?
* **Why**: see the table; the evidence is `block-and-fins/README.md` 4.1.
* **First study**: open both papers; reproduce the Elenbaas channel correlation and the optimum spacing; compare with the FVM finned block over the gap.
* **If it ends well**: a channel correlation for still air or a lower warning threshold (`docs/roadmap.md`, blocks).
* **Status**: open.

### C4. Heat capacity: the Foster chain and the top path in time
* **Question**: what chain (junction, case, heatsink) reproduces the transient of a part with a top path, and is the quasi-static top path acceptable?
* **Why**: steady state only today; the chain study shows the block takes 27.5 % of the heat with paste and 27.6 % with a gap pad (`component-heatsink/README.md` 4.9).
* **First study**: a Foster chain from datasheet Zth curves against the FVM transient of the same part.
* **If it ends well**: transient features of `docs/roadmap.md` (parts).
* **Status**: open.

### C5. A heatsink larger than its contact, and a plate on top of a package
* **Question**: what is the resistance of a heatsink larger than the package, and of a plate layer on top?
* **Why**: `component-heatsink/NOTES.md` R3 and R8; the base spreading study has the closed form of Lee as a reference.
* **First study**: base spreading with contact smaller than the base, against the FVM and the 3D solid.
* **If it ends well**: the heatsink scenarios of `docs/roadmap.md`.
* **Status**: open.

### C6. Datasheet values that are assumed or disputed
* **Question**: which values of the parts study are datasheet values and which are assumed?
* **Why**: theta_JC(top) of the MOSFET and the Schottky are assumed; the SX Semiconductor SS12 sheet (20 K/W) was not re-opened against Vishay's 28 K/W; onsemi's SS14 page returned HTML, not the PDF (`component-heatsink/README.md` 7).
* **First study**: open the datasheets and record the status per value.
* **If it ends well**: correct typical values (`package_theta`).
* **Status**: partly.

## D. Calculators

### D1. The JEDEC board of the power calculator
* **Order**: see Next work #14.
* **Question**: what is the exact JESD51-7 board (bottom layer, planes), and what do the datasheet rows give on a finer cell?
* **Why**: see the table (`power-calculator/README.md` 4.5); the no-via row moves from 84 to 73 K/W with the cell.
* **First study**: register on jedec.org for JESD51-3 and JESD51-7, read the board; rebuild the board and move the rows to a 0.25 mm cell.
* **If it ends well**: a correct JEDEC board in the calculator and in `docs/calculators.md`.
* **Status**: waits (standards to obtain).

### D2. The known-power reference and the two-point fit
* **Question**: does a measurement at a known dissipation remove the copper error, and does the datasheet shortcut theta_JA minus psi_JT have a place?
* **Why**: it fits only parts with a controllable dissipation; the copper error it removes also goes away with Gerber import; the shortcut was not offered because the copper dominates the error (11 to 45 %) (`power-calculator/README.md`, last section).
* **First study**: a two-point fit on the validation parts with a controlled power.
* **If it ends well**: a calibration mode in the calculator (`docs/roadmap.md`, calculators).
* **Status**: partly (study only).

### D3. Assumed inputs of the validation
* **Question**: how much do the assumed values (3 by 3 vias under the TPS7A47 pad, typical against maximum RθJC of the CSD17308Q3) change the validation rows?
* **Why**: the via array is assumed; theta 4.5 K/W is a maximum and a typical value would lower the model's RθJA (`power-calculator/README.md` last section).
* **First study**: sweep the assumed inputs and record the range of the validation errors.
* **If it ends well**: honest bands in `docs/calculators.md`.
* **Status**: open.

### D4. The band and drawing errors
* **Question**: can the uncertainty band hold the true power when the drawing of the board is wrong?
* **Why**: the band did not hold the true power for a drawing error in 3 of 4 cases (`power-calculator/README.md` 4.7).
* **First study**: add the drawing error (copper area, board size) to the one-at-a-time effects and re-run the four cases.
* **If it ends well**: a wider default band or an explicit note.
* **Status**: open.

## E. Gerber import and models

### E1. Diagonal faces (nine-point links)
* **Order**: see Next work #15.
* **Question**: can the cell tensor give a share of diagonal conduction that depends on the ratio of the cell to the track width and passes a held-out test?
* **Why**: the gate of `gerber-models/README.md` 4.48 gains 0.1 points instead of 0.4 on 60 new windows, nothing on a board never used, and is worse at 0.5 mm cells (4.50); the best share depends on the cell size; the share alpha was chosen on the same 42 windows it is tested on; the nine-point prototype is `lib/diagonal.py`.
* **First study**: a share as a function of cell over track width, fitted on one set of boards and tested on boards with many diagonal tracks that were not used to choose it.
* **If it ends well**: diagonal couplings in the network (`gerber-models/INTEGRATION.md` 9; `docs/roadmap.md`, import).
* **Status**: partly (failed the held-out test).

### E2. Which copper mapping, and against which reference
* **Order**: see Next work #15.
* **Question**: which mapping (fill, lambda, cell problem, flow-based faces) should be the default of an import, and does the ranking survive a finer reference?
* **Why**: mean absolute errors over eleven boards against the program's own pixel run: fill 7.4 %, lambda 2.4 %, cell problem 2.4 %, flow 2.3 %, Wiener upper bound 2.3 % (4.38, 4.43, re-run by the review of `gerber-models` on the program with its laminate nodes; 6.2 / 1.3 / 1.4 / 1.5 % before them), and that reference is itself 5.5 to 13.6 % cool on patterned one-layer copper against an independent 3D solution (Review R2); the reference uses the four-neighbour stencil, whose absolute resistance is high for tracks thinner than about 8 pixels, and the ranking was not repeated with finer pixels or the nine-point stencil (CONCLUSIONS 4).
* **First study**: repeat the ranking with finer pixels and with the nine-point reference.
* **If it ends well**: the copper mapping option and its default (`docs/roadmap.md`, import; designed in `gerber-models/INTEGRATION.md`).
* **Status**: partly.

### E3. The Lumped and Analytic models with a mask
* **Order**: see Next work #15.
* **Question**: how should the Lumped and Analytic models use a copper mask when they average over rings or regions much larger than a cell?
* **Why**: open in `gerber-models/INTEGRATION.md` 6; on the rectangle board the Lumped reads -16 % and the Analytic -26 % (4.35).
* **First study**: effective conductance per ring or per region from the mask, against the FVM on the real boards.
* **If it ends well**: import support for the two models.
* **Status**: open.

### E4. Validation scenarios that are missing
* **Order**: see Next work #15.
* **Question**: do the mappings reproduce Sampson's board and Guenin's local vertical overlap, and Blackmore's measured case?
* **Why**: Sampson's bitmaps are figures (an analogue was built that reproduces the mechanism, a factor 5 to 10 against 26); Blackmore's validation has no measurement; Guenin's overlap is only in the literature notes (`gerber-models/CONCLUSIONS.md` 4 and 5).
* **First study**: rebuild Sampson's board from the paper if the bitmaps can be obtained; a trace-over-plane case against the 3D solid at fine cells.
* **If it ends well**: two scenarios in `docs/validation.md`.
* **Status**: open.

### E5. Hatched zones and the zone pattern
* **Order**: see Next work #15.
* **Question**: which patterns should a zone offer, and what is the default for files that already use `fill` below 1?
* **Why**: the arithmetic value is the optimistic limit; the geometric-mean variant moves hatched zones by 26 to 45 % (`gerber-models/INTEGRATION.md` 5 and 6).
* **First study**: hatched zones against the resolved mask for each rule.
* **If it ends well**: a `pattern` field of the zone.
* **Status**: waits for the maintainer's decision.

### E6. Behaviour at fine cells and in time
* **Order**: see Next work #15.
* **Question**: how do the 3D solid and the transient behave on the fine cells of an imported board?
* **Why**: "the behaviour of the 3D solid at fine cells" is not verified; the time response of the mapped copper follows the steady one (`study_transient.py`), heat capacity and the through-thickness conduction stay arithmetic (`gerber-models/README.md` last section).
* **First study**: link to A5 and to the clean-machine timing (done, section 3); a transient of an imported board against a resolved mask.
* **If it ends well**: limits stated in the import documents.
* **Status**: open.

### E7. The Gerber reader: scope and conformance
* **Order**: see Next work #15.
* **Question**: do the Ucamco example data sets and the latest specification change the conformance, and which CAD formats should the check of the nets support?
* **Why**: 161 of 164 comparable files within 3 % (`gerber-import/README.md` 4.17); the specification (revision 2024.05) was read in the passages the reader implements by the review of `gerber-import/` (macro primitives, arcs, Excellon slots, AS and G91: four defects fixed, `gerber-import/README.md` 7); the Ucamco example data sets were not run; the licences of the gerbonara test boards could not be confirmed (statistics only, no picture kept); open in `gerber-import/CONCLUSIONS.md` 4.
* **First study**: download the Ucamco data sets with a script into `data/` and run `study_reader_conformance.py` on them.
* **If it ends well**: a stronger reader claim for the import.
* **Status**: open.

### E8. Nets with voltage and current
* **Order**: see Next work #15.
* **Question**: how should the Joule heat of a net, links between pieces, vias, regulators and ratings enter the thermal problem?
* **Why**: a 0.1 ohm link between two pieces of a 1.5 A rail makes 225 mW, 18 times the copper (`gerber-nets/README.md` 4.40); vias, regulators and ratings are open; the form of the inputs (an argument of the import, a sidecar file, a netlist plus part fields, a pads table) and whether IPC-2152 checks are wanted are the maintainer's choice; the split nets of the Stormduino were not examined piece by piece (two web searches, snippets only).
* **First study**: vias and regulators in the prototype; the coupling with the temperature of the thermal run.
* **If it ends well**: a `Problem.electrical` (`gerber-nets/INTEGRATION.md`; `docs/roadmap.md`, electrothermal).
* **Status**: waits (whether the electrical side enters the program before the import).

### E9. Thin tracks at an angle
* **Order**: see Next work #15.
* **Question**: what is the area and resistance of a tilted track on the pixel lattice?
* **Why**: area within 0.5 % except 45 degrees (+-6 %); the five-point stencil gives +97 % at 1.5 px, +10 % at 8 px, +6 % at 12 px across (`gerber-nets/README.md` 4.23); closely tied to E1.
* **First study**: a lattice-independent resistance for tilted tracks.
* **If it ends well**: the net Joule heat of a diagonal track.
* **Status**: partly.


### E10. The reader refuses transformed apertures and aperture blocks
* **Order**: see Next work #15.
* **Question**: should the independent reader implement the aperture transformations `LM`, `LR`, `LS` and the aperture blocks `AB` of the specification, which recent Altium (and other) output may use?
* **Why**: `gerber-import/lib/native_gerber.py` refuses these files with a message (`gerber-import/README.md` 4.19 and 7) instead of drawing them; a refused layer cannot be imported at all; no file of the test set needed them, so how often real boards use them is not known.
* **First study**: count `LM`, `LR`, `LS` and `AB` in a set of recent CAD outputs whose licence allows it; implement them against the 2024.05 specification with tests written from its examples, and compare with gerbonara on the same files.
* **If it ends well**: fewer refused files at import (`docs/roadmap.md`, import).
* **Status**: open (an item to implement, not decided).

## F. Theory, sources and verification

### F1. The effective conductivity above Biot 60
* **Order**: see Next work #16.
* **Question**: why does the stated stack of Culham and Yovanovich (1998) give an effective conductivity of 2 to 6 % different above Biot 60 in our solver?
* **Why**: five definitions of the mean wall temperature and a variant were tested; a bound shows that the stated stack cannot give it; the 1.62 mm of the text against the layers' 1.6501 mm explains about half of the base-case shortfall (8.03 instead of 7.81 against 8.28 W/mK); the definition of the mean wall temperature and the truncation of the paper's series are untested as causes (`effective-conductivity/README.md` 4.2, 4.9, 8).
* **First study**: reopen the paper's pages 460 to 467 and its last page (references) and test the series truncation.
* **If it ends well**: only a closed explanation (the thick-plate warning is already adopted).
* **Status**: open.

### F2. Cases of Muzychka and others and of Lemczyk that were not run
* **Order**: see Next work #16.
* **Question**: does the program reproduce the heat-sink base with four sources (case 2) and the compound plate (case 1 b)?
* **Why**: not run (`effective-conductivity/README.md` 7); the results of Lemczyk and others (1992) were not read; Muzychka's series coefficients were not checked.
* **First study**: both cases with `layered3d.py` and the program.
* **If it ends well**: two more published cases in `docs/validation.md`.
* **Status**: open.

### F3. Natural convection correlations: the originals
* **Order**: see Next work #16.
* **Question**: do the program's forms (Churchill and Chu, Churchill's blending rule, Hollands, Elenbaas) equal the originals?
* **Why**: Churchill and Chu (1975) was never opened (the forms come from the `ht` library, Incropera and Yovanovich); the exponent and sign rule of the Churchill blend, which Hollands paper the notes cite, and Churchill (1977) (AIChE J. 23 (1), 10-16) as the source of the blending rule are open; the documentation and the code of `ht` differ in the Hollands formula (`theory/README.md`, `theory/BIBLIOGRAPHY.md`).
* **First study**: open the papers; check the two forms numerically.
* **If it ends well**: confirmed or corrected `convection.py` forms.
* **Status**: open.

### F4. Formulas written from memory
* **Order**: see Next work #16.
* **Question**: are the 2D Bruggeman equation `k^2 - (a - b)(2f - 1)k - ab = 0`, the 2D Hashin-Shtrikman bounds and the duality of Keller and Dykhne exactly what the books say?
* **Why**: their properties were checked numerically (`theory/scripts/check_mapping_formulas.py`) but no textbook was opened: Milton, *The Theory of Composites* (Hashin-Shtrikman, 2D duality) and Torquato, *Random Heterogeneous Materials*; also the Ucamco text on aperture holes.
* **First study**: open the books; record page and equation.
* **If it ends well**: a confirmed basis for the mappings.
* **Status**: open.

### F5. Sources to open
* **Order**: see Next work #16.
* **Question**: which of the sources of `theory/BIBLIOGRAPHY.md` marked M, N or S should be opened, in what order?
* **Why**: textbooks Patankar (1980), Incropera and DeWitt, Carslaw and Jaeger, Milton (2002), Torquato (2002), Briggs and others (2000); papers Hashin and Shtrikman (J. Appl. Phys. 33, 1962: the conductivity paper; the 1963 paper is the elastic one), Keller (1964), Dykhne (1970), Churchill and Chu (1975), Churchill (1977), Culham and Yovanovich (ITherm 1998, pp. 460-467, reopen), Lush (cited as Electronics Cooling, May 2004, not identifiable: that month's article is by Simons), Lee and others (1995, the citation itself could not be confirmed after two rounds of searches), Elenbaas (1942), Bar-Cohen and Rohsenow (1984), the Hollands correlation; standards JEDEC JESD15-3 and the JESD51 family, IPC-4761, IPC-2152, ASTM D5470, ASME V&V 20 and the Ucamco Gerber specification; JESD51-3 and JESD51-7 by number on jedec.org (free after registration); the byline of the multigrid primer; the reference compilation `theory/docs/reference-compilation.md` settles several citations and leaves the open points named in F3 and F4.
* **First study**: take the list in the order that the other items need it (C3, D1, F1, F3, F4, E7).
* **If it ends well**: statuses raised in the bibliography only with a record of the reading.
* **Status**: open.

### F6. Planned models without a source
* **Order**: see Next work #16.
* **Question**: what do the sources say about the Foster chain, the heatsink scenarios, the virtual JEDEC test with a known-power reference, the import and the multigrid (topics 12 to 16)?
* **Why**: those topics describe intended behaviour; the formulas of topics 12 and 16 are general textbook knowledge written without a source; the numbers of the Gerber topics 15, 17, 19 and 20 are checked by their own folders (`theory/README.md` 7).
* **First study**: one source and one reproduced case per topic before the feature is designed.
* **If it ends well**: designs in `docs/roadmap.md`.
* **Status**: open.

### F7. Grid convergence of the references
* **Order**: see Next work #16.
* **Question**: is the finest-grid reference of every study converged by a grid convergence index?
* **Why**: the Roache/ASME V&V 20 formula is from memory (status M); the 2.5 mm cells of Muzychka's case 1 overstate the mean of a 25 mm source by 0.3 to 0.4 K; the independent solver within 1.4 % at 1 mm and 0.2 % at 0.5 mm (`models-comparison/`).
* **First study**: a GCI with three grids on each reference solution of the studies.
* **If it ends well**: stated uncertainty for the reference numbers in `docs/validation.md`.
* **Status**: partly.

### F8. Papers read only in part
* **Order**: see Next work #16.
* **Question**: do the quoted values of Yovanovich's Table 3 and of Seri Lee (1998) hold on a second reading?
* **Why**: Table 3 was confirmed by the exact Bessel series but the paper was not re-read, its title is from memory (`solid3d-verification/README.md` 7); the Lee article's equations 1 and 2 are images that did not come through.
* **First study**: obtain both and compare.
* **If it ends well**: closes the source records.
* **Status**: open (small).

### F9. Old results not re-run
* **Order**: see Next work #16.
* **Question**: can the rows of the removed wxPython program (4.5) and the quoted test tolerances be reproduced?
* **Why**: the old rows need wxPython and the comparison script of that time (tag `legacy-wxpython-1.0.0`); timings are of one run on one machine (`models-comparison/README.md` last section).
* **First study**: check out the tag in a separate environment, or mark the rows as quoted.
* **If it ends well**: closes the record.
* **Status**: open (low priority).

## G. Physical measurement

### G1. A measurement on a physical board
* **Order**: see Next work #17.
* **Question**: how far are the five models from the temperatures of a real board?
* **Why**: no model has been compared with one; every number in the repository is against another model or a published case. The protocol (one board, a heater of known electrical power, thermocouples at 1, 5, 10 and 15 mm, an infrared map, three powers, the five models, the agreement criterion fixed beforehand) is `models-comparison/docs/measurement-protocol.md`; nothing was built or measured.
* **First study**: build the board and measure; or find public measured data of boards with known power and copper.
* **If it ends well**: the accuracy of every model in `docs/validation.md` stops being "against the reference model"; the corrections of the copper mapping (E2) are checked against the world.
* **Status**: waits for a board and an instrument.

## H. Tooling and method

### H6. Studies that need a script before they are quoted
* **Question**: which numbers of the READMEs are printed by no script?
* **Why**: the 2-layer measurement of A1 (scratch directory only); the scaling about the area centroid (A9); the lost edge over many outlines (A9); the multigrid timings (A10); the "old" rows of `models-comparison/` (F9).
* **First study**: write or remove each, marking numbers not reproduced.
* **If it ends well**: nothing in the program.
* **Status**: open.

## 3. The long runs (H9): done

The twelve runs of the plan were made on a machine just restarted with nothing else running (macOS arm64, 10 cores, 16 GB, Python 3.13.5), in the order of the plan, with the logs outside the repository. Every printed table was compared with the README of its folder, and the machine and the result are written in the last section of each README ("What was read and what was not verified"):

* **Reproduced to the digit**: README 4.44, 4.48 and 4.50 (diagonal studies), 4.6 and 4.8 (fine scan and heater size), 4.2 of `solid3d-verification` (small pad and FEM hand checks), 4.2 and section 8 of `effective-conductivity` (mesh check 7.84 to 7.81 W/mK), 4.5 and 4.7 of `power-calculator` (cell size; the bands typed in `DESIGN_COVERAGE` match the new print in all 16 bands), 7.3 of `via-fill` (the 0.05 mm point of the independent reference, -4.44 K, was added to the table).
* **Not reproduced, and corrected in the research documents**: the cost of the 3D solid and of the layered FVM (`solid3d-verification`, figure 9 and `docs/for-the-project-documents.md`): the times of the program documents (276 s at 393 000 unknowns, 97 s and 273 s at 1 and 2 million) are 20 to 40 times longer than what the quiet machine gives (7.5 s, 5.2 s, 12.4 s) and the memory up to 2.4 times larger; the cost of the mappings (`gerber-models` 4.15): times 5 times shorter and memory 1.4 KB per pixel instead of 830 bytes (the script's memory column was also wrong on macOS and is fixed).
* **Plan numbers that were wrong**: `study_diagonal_heldout.py` takes about 5 minutes, not 3 hours; `study_via_model_checks.py --fine` reached a peak footprint of 22.5 GB on the 16 GB machine (it paged), not 10 GB; `study_fem_hand_checks.py` takes about 4 minutes.
* **For the maintainer** (program documents, not edited here): Next work #3 below, with the table of measured times and memory in `solid3d-verification/docs/for-the-project-documents.md`; the limit `MAX_CELLS = 250 000` and the memory guard rest on the old numbers.
* **Figures redrawn** from the new `out/` files: `gerber-models` figures 8, 19 and 24 (current style) and `solid3d-verification` figure 9; `research/check_figures.py` passes on every folder.
