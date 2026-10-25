# What we want to investigate

The plan of the research: questions that are not answered yet, grouped by area. A question stays here until a study answers it; the answer then goes into the README of its folder, and, when it changes the program, into `docs/roadmap.md` (the list of what we want to implement as features and corrections of the program). **Program features and corrections are not listed here**: when an investigation finds a defect, the defect is recorded in the README of the folder and the correction is an item of `docs/roadmap.md`. The register of what the independent reviewer checked in each folder is [`REVIEW.md`](REVIEW.md); the index of the folders is [`INDEX.md`](INDEX.md).

Every item has the same five fields: **Question**, **Why** (the evidence: folder and section), **First study**, **If it ends well** (what would change in the program, with the item of `docs/roadmap.md` when there is one) and **Status**. Status values: `open` (nothing done), `partly` (a first look exists), `waits` (needs a decision or a condition). An item that changes a model needs the reviewer before it is closed.

## To close this round (after the restart, on the maintainer's instructions)

What is still open to finish the review and the corrections of the investigations; everything else of this document is the plan of future questions.

1. **Restart the machine and run nothing else.** Then the long runs of H9, in the order given there (the clean-machine timing first, then the memory-hungry studies one at a time, then the rest).
2. **After each study**: regenerate the figures that depend on it (three diagonal figures of `gerber-models` still in the old font), read each PNG, run `research/check_figures.py`, update the README where a number moves, write the machine and the time of the run in the README, and make one commit per folder.
3. **Correct the program documents with the measured times** (`docs/roadmap.md` item, `CHANGELOG.md`, `docs/versions.md`, `docs/models.md`, the comment of `pcbthermal/solid3d.py`): a documents branch off `develop`, with the whole battery; the same numbers feed the memory guard (`docs/roadmap.md`, memory and size).
4. **Decisions left to the coordinator** (list in `research/REVIEW.md`): taken when the runs are finished.
5. **A last documents branch** that brings `CLAUDE.md` of `develop` to the same text as this branch (the five Decisions Log entries of the research rules and the structure lines without the 'only on the branch' notes), and the merge of `develop` into this branch.
6. **Publication**: `develop` is 14 commits ahead of `origin/develop` and this branch 82 commits ahead of `origin/research/gerbers`; push only on the maintainer's word.
7. **Program corrections still open** (`docs/roadmap.md`, 'Defects of the program to correct'): block beyond the outline, point via of the FVM and FDM, `via_frac` clip of the 3D solid, union of zones per sample point, laminate nodes for patterned copper, `top_resistance` against `junction_theta`, via diameter label, memory guard; each by the flow executor, reviewer, maintainer on its own `fix/` or `feature/` branch.

| Area | Items |
| :-- | :-- |
| A. Models and numerics | A1 to A10 |
| B. Boards, vias and stack-up | B1 to B4 |
| C. Parts, heatsinks and blocks | C1 to C6 |
| D. Calculators | D1 to D4 |
| E. Gerber import and models | E1 to E10 |
| F. Theory, sources and verification | F1 to F9 |
| G. Physical measurement | G1 |
| H. Tooling and method | H1 to H9 |

## A. Models and numerics

### A1. Subdivide the gap of every multilayer board
* **Question**: does more than one node through the dielectric gap of a multilayer board remove the error of the layered models against a resolved 3D solution?
* **Why**: with one pair of nodes through the gap a 2-layer board reads 2 to 8 % low in the FVM against the independent solver: CSD17308Q3 board -2.3 % (one layer: -1.3 %), 20 mm pad -3.8 % (-2.3 %), 10 mm pad -7.7 % (-4.8 %); the same pad on both faces gives the same -3.9 %, so the error belongs to every 2-layer board and not to a bare bottom (`power-calculator/` 4.5 to 4.7; `effective-conductivity/` 4.11 for the one-layer case that the laminate nodes already fixed). Treating only a bare bottom as a one-layer board would make identical 2-layer boards inconsistent.
* **First study**: the sweep of 1 to 4 nodes in the gap used for the one-layer laminate (`laminate.py`), on 2-, 3- and 4-layer boards with full copper, a pad, a part and vias, against `solid3d-verification/lib/layered3d.py`; write into `power-calculator/scripts/` the script of the measurement above (it was run from a scratch directory and has to be versioned before the numbers are quoted).
* **If it ends well**: a change of every 2- and 3-layer result in the FVM, FDM and Lumped (`docs/roadmap.md`, models); needs the reviewer and a new `docs/validation.md` table. Until then the error is only documented.
* **Status**: open. Start only after the other items of this document that the maintainer ordered first.

### A2. Why the Analytic model is hot on one-layer boards with partial copper
* **Question**: what makes the Analytic estimate too hot on a one-layer board whose copper does not cover the board, and is there a cheaper variant for the Analytic model alone?
* **Why**: its uniform sheet already overestimated the rise on partial copper and the series film made it hotter (`docs/validation.md`, nine boards against the 3D solid: Analytic 5.5 % before and after); a variant for the Analytic alone on a 2-layer board with a 20 mm pad still reads -32 % to -13 % (`power-calculator/` 4.7).
* **First study**: separate the three candidate causes (uniform sheet conductance, the film in series, the local corrections) on a pad of growing size against the independent solver.
* **If it ends well**: a better estimate for the Analytic on partial copper (`docs/roadmap.md`, models).
* **Status**: open.

### A3. The 3D solid with a rotated square at a high side coefficient
* **Question**: why does a rotated square source read +1.15 K above the aligned square in the 3D solid when the side coefficient is high?
* **Why**: seen in the reviews of `solid3d-verification/` and `outline/`; the aligned square agrees with the FVM; the effect appears only with a high `h_side`.
* **First study**: rotate the square and the board edge separately on a copy, vary `h_side` and the cell, and compare the edge conductance per cell with `geometry.edge_length_on_board`.
* **If it ends well**: a correction of the edge handling of the 3D solid, or a documented limit.
* **Status**: open.

### A4. Clean-machine timing of the direct solves
* **Question**: what do the direct solves of the 3D solid and of the layered FVM and FDM really cost (time and memory) against the number of unknowns on a machine with nothing else running?
* **Why**: `solid3d-verification/scripts/study_solve_cost.py` (figure 9) measured 1.7 to 15 s at 65 000 to 247 000 unknowns on a quiet machine, far below the 49 s at 160 000 and 130 s at 254 000 quoted in the program documents, taken from a diagnosis under heavy swap; the memory is the same (2.15 against 2.2 GB at 160 000). The 250 000 limit rests on the memory, less on the time.
* **First study**: extend `study_solve_cost.py` to the sizes of the documents (160 000, 254 000, 400 000 and 512 000 unknowns, and 1 and 2 million for the layered models), run it alone, and write the machine and its memory state in the README.
* **If it ends well**: correct the times of `CHANGELOG.md`, `docs/versions.md`, `docs/models.md`, the comment of `pcbthermal/solid3d.py` and the reasoning of the 250 000 limit; the numbers feed the memory-based guard of `docs/roadmap.md`. Until then the documents read "seconds to minutes depending on the memory pressure".
* **Status**: waits for the maintainer's order: the machine is restarted and nothing else runs during the measurement.

### A5. The point via and the cell: Peaceman radius against spreading
* **Question**: which treatment makes the via of the FVM and FDM converge with the cell: the Peaceman well index (`r_eq = 0.198 dx`, spreading only when `r_eq <= r_v`), or always spreading the barrel over the cells of its disc?
* **Why**: the copper-fill gain of the test board is -4.46 K against the independent solver, and the FVM gives -4.78, -4.38, -3.98, -3.64, -3.34 K at 1, 0.5, 0.25, 0.125, 0.0625 mm (the example board: -4.49 / -3.89 / -3.59 K at 1 / 0.5 / 0.25 mm); at 0.5 to 1 mm the error is 0.1 to 0.3 K, below 0.5 mm it grows (`via-fill/README.md` 7.3, `INTEGRATION.md` 1). The Gerber boards of `gerber-models/` run at fine cells: their results with vias below 0.5 mm have to be read in this light.
* **First study**: both treatments on a copy against `layered3d.py` with resolved barrels, over 1 to 0.0625 mm, on the via-array board and on the example board; then re-run the tables of `docs/validation.md` 2.1.
* **If it ends well**: the fix of the via in `fvm.py` and `fdm.py` (`docs/roadmap.md`, corrections), with the reviewer; the 3D solid clipping of vias larger than a cell is a separate program item.
* **Status**: partly (the defect is measured, the two corrections are designed in `via-fill/INTEGRATION.md`, none is compared).

### A6. Why the Lumped and Analytic models overstate the effect of vias
* **Question**: why do the Lumped and Analytic models give a copper-fill gain 35 to 52 % larger than the reference, and which part of the construction (ring conductance, Green-function correction) carries it?
* **Why**: -6.0 to -6.8 K against -4.45 K on the test board; example board -6.3 to -7.0 K against -3.9 to -4.5 K (`via-fill/README.md` 7). The models were tuned against the FVM, which is itself off at fine cells (A5).
* **First study**: after A5, repeat the fill sweep with one via, a row and an array, isolating the lateral spreading and the barrel conductance in each model.
* **If it ends well**: a correction of the via term of the two models, or a warning in the report.
* **Status**: open (decide first whether to investigate or only document).

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
* **Question**: what is the heat transfer coefficient between fins in still air as a function of gap and height, and where should the warning of the program sit?
* **Why**: the warning at 4 mm leaves a 6.5 mm gap near the optimum spacing of a short array, where a remembered correlation puts the channel coefficient 10 to 30 % below the typed one (`block-and-fins/README.md` 4.1); Elenbaas (1942) and Bar-Cohen and Rohsenow (1984) have not been opened (only the quoted optimum).
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
* **Question**: what is the exact JESD51-7 board (bottom layer, planes), and what do the datasheet rows give on a finer cell?
* **Why**: JESD51-5 and JESD51-7 are behind a login; ROHM's table reads a 70 um backside plane, and with it the JEDEC row is +23 % (`power-calculator/README.md` 4.5); the no-via row moves from 84 to 73 K/W with the cell.
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
* **Question**: can the cell tensor give a share of diagonal conduction that depends on the ratio of the cell to the track width and passes a held-out test?
* **Why**: the gate of `gerber-models/README.md` 4.48 gains 0.1 points instead of 0.4 on 60 new windows, nothing on a board never used, and is worse at 0.5 mm cells (4.50); the best share depends on the cell size; the share alpha was chosen on the same 42 windows it is tested on; the nine-point prototype is `lib/diagonal.py`.
* **First study**: a share as a function of cell over track width, fitted on one set of boards and tested on boards with many diagonal tracks that were not used to choose it.
* **If it ends well**: diagonal couplings in the network (`gerber-models/INTEGRATION.md` 9; `docs/roadmap.md`, import).
* **Status**: partly (failed the held-out test).

### E2. Which copper mapping, and against which reference
* **Question**: which mapping (fill, lambda, cell problem, flow-based faces) should be the default of an import, and does the ranking survive a finer reference?
* **Why**: mean absolute errors over eleven boards against the program's own pixel run: fill 7.4 %, lambda 2.4 %, cell problem 2.4 %, flow 2.3 %, Wiener upper bound 2.3 % (4.38, 4.43, re-run by the review of `gerber-models` on the program with its laminate nodes; 6.2 / 1.3 / 1.4 / 1.5 % before them), and that reference is itself 5.5 to 13.6 % cool on patterned one-layer copper against an independent 3D solution (Review R2); the reference uses the four-neighbour stencil, whose absolute resistance is high for tracks thinner than about 8 pixels, and the ranking was not repeated with finer pixels or the nine-point stencil (CONCLUSIONS 4).
* **First study**: repeat the ranking with finer pixels and with the nine-point reference.
* **If it ends well**: the copper mapping option and its default (`docs/roadmap.md`, import; designed in `gerber-models/INTEGRATION.md`).
* **Status**: partly.

### E3. The Lumped and Analytic models with a mask
* **Question**: how should the Lumped and Analytic models use a copper mask when they average over rings or regions much larger than a cell?
* **Why**: open in `gerber-models/INTEGRATION.md` 6; on the rectangle board the Lumped reads -16 % and the Analytic -26 % (4.35).
* **First study**: effective conductance per ring or per region from the mask, against the FVM on the real boards.
* **If it ends well**: import support for the two models.
* **Status**: open.

### E4. Validation scenarios that are missing
* **Question**: do the mappings reproduce Sampson's board and Guenin's local vertical overlap, and Blackmore's measured case?
* **Why**: Sampson's bitmaps are figures (an analogue was built that reproduces the mechanism, a factor 5 to 10 against 26); Blackmore's validation has no measurement; Guenin's overlap is only in the literature notes (`gerber-models/CONCLUSIONS.md` 4 and 5).
* **First study**: rebuild Sampson's board from the paper if the bitmaps can be obtained; a trace-over-plane case against the 3D solid at fine cells.
* **If it ends well**: two scenarios in `docs/validation.md`.
* **Status**: open.

### E5. Hatched zones and the zone pattern
* **Question**: which patterns should a zone offer, and what is the default for files that already use `fill` below 1?
* **Why**: the arithmetic value is the optimistic limit; the geometric-mean variant moves hatched zones by 26 to 45 % (`gerber-models/INTEGRATION.md` 5 and 6).
* **First study**: hatched zones against the resolved mask for each rule.
* **If it ends well**: a `pattern` field of the zone.
* **Status**: waits for the maintainer's decision.

### E6. Behaviour at fine cells and in time
* **Question**: how do the 3D solid and the transient behave on the fine cells of an imported board?
* **Why**: "the behaviour of the 3D solid at fine cells" is not verified; the time response of the mapped copper follows the steady one (`study_transient.py`), heat capacity and the through-thickness conduction stay arithmetic (`gerber-models/README.md` last section).
* **First study**: link to A5 and A4; a transient of an imported board against a resolved mask.
* **If it ends well**: limits stated in the import documents.
* **Status**: open.

### E7. The Gerber reader: scope and conformance
* **Question**: do the Ucamco example data sets and the latest specification change the conformance, and which CAD formats should the check of the nets support?
* **Why**: 161 of 164 comparable files within 3 % (`gerber-import/README.md` 4.17); the specification (revision 2024.05) was read in the passages the reader implements by the review of `gerber-import/` (macro primitives, arcs, Excellon slots, AS and G91: four defects fixed, `gerber-import/README.md` 7); the Ucamco example data sets were not run; the licences of the gerbonara test boards could not be confirmed (statistics only, no picture kept); open in `gerber-import/CONCLUSIONS.md` 4.
* **First study**: download the Ucamco data sets with a script into `data/` and run `study_reader_conformance.py` on them.
* **If it ends well**: a stronger reader claim for the import.
* **Status**: open.

### E8. Nets with voltage and current
* **Question**: how should the Joule heat of a net, links between pieces, vias, regulators and ratings enter the thermal problem?
* **Why**: a 0.1 ohm link between two pieces of a 1.5 A rail makes 225 mW, 18 times the copper (`gerber-nets/README.md` 4.40); vias, regulators and ratings are open; the form of the inputs (an argument of the import, a sidecar file, a netlist plus part fields, a pads table) and whether IPC-2152 checks are wanted are the maintainer's choice; the split nets of the Stormduino were not examined piece by piece (two web searches, snippets only).
* **First study**: vias and regulators in the prototype; the coupling with the temperature of the thermal run.
* **If it ends well**: a `Problem.electrical` (`gerber-nets/INTEGRATION.md`; `docs/roadmap.md`, electrothermal).
* **Status**: waits (whether the electrical side enters the program before the import).

### E9. Thin tracks at an angle
* **Question**: what is the area and resistance of a tilted track on the pixel lattice?
* **Why**: area within 0.5 % except 45 degrees (+-6 %); the five-point stencil gives +97 % at 1.5 px, +10 % at 8 px, +6 % at 12 px across (`gerber-nets/README.md` 4.23); closely tied to E1.
* **First study**: a lattice-independent resistance for tilted tracks.
* **If it ends well**: the net Joule heat of a diagonal track.
* **Status**: partly.


### E10. The reader refuses transformed apertures and aperture blocks
* **Question**: should the independent reader implement the aperture transformations `LM`, `LR`, `LS` and the aperture blocks `AB` of the specification, which recent Altium (and other) output may use?
* **Why**: `gerber-import/lib/native_gerber.py` refuses these files with a message (`gerber-import/README.md` 4.19 and 7) instead of drawing them; a refused layer cannot be imported at all; no file of the test set needed them, so how often real boards use them is not known.
* **First study**: count `LM`, `LR`, `LS` and `AB` in a set of recent CAD outputs whose licence allows it; implement them against the 2024.05 specification with tests written from its examples, and compare with gerbonara on the same files.
* **If it ends well**: fewer refused files at import (`docs/roadmap.md`, import).
* **Status**: open (an item to implement, not decided).
## F. Theory, sources and verification

### F1. The effective conductivity above Biot 60
* **Question**: why does the stated stack of Culham and Yovanovich (1998) give an effective conductivity of 2 to 6 % different above Biot 60 in our solver?
* **Why**: five definitions of the mean wall temperature and a variant were tested; a bound shows that the stated stack cannot give it; the 1.62 mm of the text against the layers' 1.6501 mm explains about half of the base-case shortfall (8.03 instead of 7.81 against 8.28 W/mK); the definition of the mean wall temperature and the truncation of the paper's series are untested as causes (`effective-conductivity/README.md` 4.2, 4.9, 8).
* **First study**: reopen the paper's pages 460 to 467 and its last page (references) and test the series truncation.
* **If it ends well**: only a closed explanation (the thick-plate warning is already adopted).
* **Status**: open.

### F2. Cases of Muzychka and others and of Lemczyk that were not run
* **Question**: does the program reproduce the heat-sink base with four sources (case 2) and the compound plate (case 1 b)?
* **Why**: not run (`effective-conductivity/README.md` 7); the results of Lemczyk and others (1992) were not read; Muzychka's series coefficients were not checked.
* **First study**: both cases with `layered3d.py` and the program.
* **If it ends well**: two more published cases in `docs/validation.md`.
* **Status**: open.

### F3. Natural convection correlations: the originals
* **Question**: do the program's forms (Churchill and Chu, Churchill's blending rule, Hollands, Elenbaas) equal the originals?
* **Why**: Churchill and Chu (1975) was never opened (the forms come from the `ht` library, Incropera and Yovanovich); the exponent and sign rule of the Churchill blend, which Hollands paper the notes cite, and Churchill (1977) (AIChE J. 23 (1), 10-16) as the source of the blending rule are open; the documentation and the code of `ht` differ in the Hollands formula (`theory/README.md`, `theory/BIBLIOGRAPHY.md`).
* **First study**: open the papers; check the two forms numerically.
* **If it ends well**: confirmed or corrected `convection.py` forms.
* **Status**: open.

### F4. Formulas written from memory
* **Question**: are the 2D Bruggeman equation `k^2 - (a - b)(2f - 1)k - ab = 0`, the 2D Hashin-Shtrikman bounds and the duality of Keller and Dykhne exactly what the books say?
* **Why**: their properties were checked numerically (`theory/scripts/check_mapping_formulas.py`) but no textbook was opened: Milton, *The Theory of Composites* (Hashin-Shtrikman, 2D duality) and Torquato, *Random Heterogeneous Materials*; also the Ucamco text on aperture holes.
* **First study**: open the books; record page and equation.
* **If it ends well**: a confirmed basis for the mappings.
* **Status**: open.

### F5. Sources to open
* **Question**: which of the sources of `theory/BIBLIOGRAPHY.md` marked M, N or S should be opened, in what order?
* **Why**: textbooks Patankar (1980), Incropera and DeWitt, Carslaw and Jaeger, Milton (2002), Torquato (2002), Briggs and others (2000); papers Hashin and Shtrikman (J. Appl. Phys. 33, 1962: the conductivity paper; the 1963 paper is the elastic one), Keller (1964), Dykhne (1970), Churchill and Chu (1975), Churchill (1977), Culham and Yovanovich (ITherm 1998, pp. 460-467, reopen), Lush (cited as Electronics Cooling, May 2004, not identifiable: that month's article is by Simons), Lee and others (1995, the citation itself could not be confirmed after two rounds of searches), Elenbaas (1942), Bar-Cohen and Rohsenow (1984), the Hollands correlation; standards JEDEC JESD15-3 and the JESD51 family, IPC-4761, IPC-2152, ASTM D5470, ASME V&V 20 and the Ucamco Gerber specification; JESD51-3 and JESD51-7 by number on jedec.org (free after registration); the byline of the multigrid primer; the reference compilation `theory/docs/reference-compilation.md` settles several citations and leaves the open points named in F3 and F4.
* **First study**: take the list in the order that the other items need it (C3, D1, F1, F3, F4, E7).
* **If it ends well**: statuses raised in the bibliography only with a record of the reading.
* **Status**: open.

### F6. Planned models without a source
* **Question**: what do the sources say about the Foster chain, the heatsink scenarios, the virtual JEDEC test with a known-power reference, the import and the multigrid (topics 12 to 16)?
* **Why**: those topics describe intended behaviour; the formulas of topics 12 and 16 are general textbook knowledge written without a source; the numbers of the Gerber topics 15, 17, 19 and 20 are checked by their own folders (`theory/README.md` 7).
* **First study**: one source and one reproduced case per topic before the feature is designed.
* **If it ends well**: designs in `docs/roadmap.md`.
* **Status**: open.

### F7. Grid convergence of the references
* **Question**: is the finest-grid reference of every study converged by a grid convergence index?
* **Why**: the Roache/ASME V&V 20 formula is from memory (status M); the 2.5 mm cells of Muzychka's case 1 overstate the mean of a 25 mm source by 0.3 to 0.4 K; the independent solver within 1.4 % at 1 mm and 0.2 % at 0.5 mm (`models-comparison/`).
* **First study**: a GCI with three grids on each reference solution of the studies.
* **If it ends well**: stated uncertainty for the reference numbers in `docs/validation.md`.
* **Status**: partly.

### F8. Papers read only in part
* **Question**: do the quoted values of Yovanovich's Table 3 and of Seri Lee (1998) hold on a second reading?
* **Why**: Table 3 was confirmed by the exact Bessel series but the paper was not re-read, its title is from memory (`solid3d-verification/README.md` 7); the Lee article's equations 1 and 2 are images that did not come through.
* **First study**: obtain both and compare.
* **If it ends well**: closes the source records.
* **Status**: open (small).

### F9. Old results not re-run
* **Question**: can the rows of the removed wxPython program (4.5) and the quoted test tolerances be reproduced?
* **Why**: the old rows need wxPython and the comparison script of that time (tag `legacy-wxpython-1.0.0`); timings are of one run on one machine (`models-comparison/README.md` last section).
* **First study**: check out the tag in a separate environment, or mark the rows as quoted.
* **If it ends well**: closes the record.
* **Status**: open (low priority).

## G. Physical measurement

### G1. A measurement on a physical board
* **Question**: how far are the five models from the temperatures of a real board?
* **Why**: no model has been compared with one; every number in the repository is against another model or a published case. The protocol (one board, a heater of known electrical power, thermocouples at 1, 5, 10 and 15 mm, an infrared map, three powers, the five models, the agreement criterion fixed beforehand) is `models-comparison/docs/measurement-protocol.md`; nothing was built or measured.
* **First study**: build the board and measure; or find public measured data of boards with known power and copper.
* **If it ends well**: the accuracy of every model in `docs/validation.md` stops being "against the reference model"; the corrections of the copper mapping (E2) are checked against the world.
* **Status**: waits for a board and an instrument.

## H. Tooling and method

### H1. The final figure pass
* **Question**: is every figure of every folder drawn the same way and current with its text?
* **Why**: the maintainer asked to regenerate all the figures after the reviews of the remaining folders; the font differs between machines; the `gerber-models` figures that said "today" or showed the 3D solid without the laminate of a one-layer board were redrawn by its review, and `gerber-import` figure 08 was corrected by its review; the `gerber-*` folders need their inputs fetched into the git-ignored `data/`.
* **First study**: regenerate with `make_figures.py` and `make_diagrams.py`, re-read each with the image reader; write `research/check_figures.py` (every figure linked from a README, no broken link, no repeated number, every folder has at least one data graph and one diagram).
* **If it ends well**: nothing in the program.
* **Status**: checker written (`research/check_figures.py`, described in `README.md`); it finds `theory/` without a data figure (all its figures are diagrams; decide whether it needs one) and nothing else. Still open: regenerating and re-reading every figure, after the reviews of the `gerber-*` folders.

### H2. Dates in the research documents
* **Question**: which dates remain?
* **Why**: the rule is no dates, except dates of third-party publications: lines 3 and 55 of `component-heatsink/README.md` and line 65 of `NOTES.md`, line 3 of `block-and-fins/README.md` and `via-fill/README.md`, line 95 of `via-fill/README.md` and line 10 of `via-fill/docs/for-the-project-documents.md`, the section title "Review (...)" and the dates of `outline/docs/for-the-project-documents.md`, and the same check in every folder.
* **First study**: a search for dates in `research/`.
* **If it ends well**: nothing in the program.
* **Status**: done for the dated work entries (the dates of the work were removed from every research document and script, headings included; what stays are dates of third-party publications, such as article dates and standard revisions, in `theory/` and `gerber-models/`); repeat the search `grep -rnE "20[0-9]{2}-[0-9]{2}-[0-9]{2}" research` in the final pass.

### H3. Bring the branch up to date with the program
* **Question**: what must be updated here after the corrections of the program are merged into `develop`?
* **Why**: merge `develop` into `research/gerbers`; `outline/scripts/study_edge_on_grid_lines.py` patched a function that has since changed (rewritten for the current program, re-check after the merge) and the numbers of `outline/README.md`; the figure numbers of `models-comparison/` and `solid3d-verification/` collided between the two sides of a merge (diagrams renumbered 8 to 10 and 8); `theory/topics/01-layered-idealisation.md` and `theory/README.md` still name `fig_04_the_five_models_schematic.png` (now `fig_08`); `theory/topics/20-board-outline.md` repeats the stale ranges of `outline/`.
* **First study**: merge, run the research tests, fix the links.
* **If it ends well**: nothing in the program.
* **Status**: open.

### H4. Reviews still to do
* **Question**: what do the independent reviews of `gerber-import/`, `gerber-models/` and `gerber-nets/` find?
* **Why**: they are `not reviewed` in `REVIEW.md`; `gerber-models/` depends on every correction of the program.
* **First study**: reviewer agent, each folder in turn.
* **If it ends well**: the folders enter the register as `reviewed`.
* **Status**: open.

### H5. Texts for the project documents
* **Question**: have the replacement texts of every `docs/for-the-project-documents.md` reached the project documents?
* **Why**: each reviewed folder keeps text for `docs/validation.md`, `docs/theory.md`, `docs/models.md`, `docs/research.md`, `docs/calculators.md` and the roadmap; the stale numbers in the program documents persist until a `docs/` branch adopts them.
* **First study**: a `docs/` branch off `develop` that takes them (a program task, listed in `docs/roadmap.md`).
* **If it ends well**: `docs/` and the research agree.
* **Status**: waits for the merges of the corrections into `develop`.

### H6. Studies that need a script before they are quoted
* **Question**: which numbers of the READMEs are printed by no script?
* **Why**: the 2-layer measurement of A1 (scratch directory only); the scaling about the area centroid (A9); the lost edge over many outlines (A9); the multigrid timings (A10); the "old" rows of `models-comparison/` (F9).
* **First study**: write or remove each, marking numbers not reproduced.
* **If it ends well**: nothing in the program.
* **Status**: open.

### H7. Separate the documents of the three Gerber folders
* **Question**: does each of `gerber-import/`, `gerber-models/` and `gerber-nets/` document only its own function?
* **Why**: the maintainer found that `gerber-import/` carries much information that belongs to the other two (the processing of the copper and the nets); the three folders have three functions (read the files and import the board; map the copper into the simulation models; nets, current and Joule heat) and each reader should find its own results, limits and sources without wading through the others'.
* **First study**: after the reviews of `gerber-models/` and `gerber-nets/` are finished, read the READMEs, REPORT, CONCLUSIONS and INTEGRATION files of the three folders, assign every section to the folder whose function it belongs to (a paragraph that serves two folders is written once, in the folder that owns the subject, and the other folder links to it), move what is misplaced (with its figures: figure numbers stay unique inside each folder; links updated; scripts and tests stay where they run unless a study belongs elsewhere), and give each folder a short section 'what this folder does and what it leaves to the others'. No result is deleted, and no number changes in the move.
* **If it ends well**: three self-contained folders; the Gerber import into the program (`docs/roadmap.md`) can be read from the folder of each step.
* **Status**: done in the documents and reviewed (a comparison of the numbers, figure paths, citations and section references of every changed file before and after found nothing lost and every pointer resolving; the review fixed one unqualified pointer, the stale "panel" of `charliewatch-v2`, the reading status of the Gerber specification and of the Bruggeman and Hashin-Shtrikman forms, and the pre-laminate-node mapping numbers left in this file, E2, and in theory topic 17). Each README now opens with section 1 "What this folder does and what it leaves to the others" and lists only its own sections; the map of all the sections is in `research/README.md` ("The Gerber research: where the sections are"); no section changed its number, so no citation had to change. Moved: where the net of a piece of copper comes from (the X2 attribute, the zone fills without a net, the working rule, 149 of 176 pieces) from `gerber-nets` 4.20 to `gerber-import` 4.29; the design of the import (pixel size, storage of the masks, KiCad as a second source, the confirmation step) from `gerber-models/INTEGRATION.md` 0 and 3 and README section 5 to `gerber-import/INTEGRATION.md`; the Ucamco literature from `gerber-models/docs/literature.md` to `gerber-import/docs/literature.md` and the Electronics Cooling notes out of the latter; the thermal effect of the reader out of `gerber-import/CONCLUSIONS.md` (it stays in `gerber-models` 4.31); the copied reading record of `gerber-nets` replaced by its own. No figure, script or test had to move (the shared modules stay in `gerber-import/lib`, which the other two import).

### H8. More real boards as test benches: decided not to
* The Stormduino (MIT) is enough as the real board whose figures may be drawn; `our_board.py` is the bench of our own (`gerber-import/README.md` 4.30). No search for further boards.

### H9. The long runs, at the very end
* **Question**: do the studies that were not re-run in the last pass (because they take from 6 minutes to hours, or need a machine with nothing else running) reproduce their numbers and figures on the corrected program?
* **Why**: the maintainer asked to run them when everything else is finished, after the restart of the machine (the same restart as A4). The table below is the exact plan: one row per figure, or per README number when the thing to repeat is a number. It was made by reading the `out/` files that every `scripts/make_figures.py` loads, the studies that write them, the run times in the script headers and the READMEs, and the file times of `out/` against the last change of `pcbthermal/` that matters to the studies (the corrected program: laminate nodes, merged as `0ea5f07`; the later finned-block fix `bd5b2f3` touches no study listed here). "Newer than the corrected program" below means the file was written after that program existed.
* **Machine**: 10 cores, 16 GB of memory (the same laptop as the last pass). Rows 5, 7 and 12 need 5 to 10 GB: nothing else may run, and the memory state before each run goes into the README.

**1. What has to be run** (12 rows: gerber-models 5, solid3d-verification 3, power-calculator 2, effective-conductivity 1, via-fill 1)

| # | Folder | Figure or README number | Figure script and function | Input in `out/` and its state now | Study and exact command | Run time and memory | What to check afterwards |
| :-: | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | `gerber-models` | `fig_08_diagonal.png`; README 4.44; the "Diagonal couplings" row of `CONCLUSIONS.md` | `make_figures.py fig_diagonal` | `out/diagonal.json`: **absent** (the PNG on disk is the old drawing) | `PYTHONPATH=. .venv/bin/python research/gerber-models/scripts/study_diagonal.py \| tee $LOG/diagonal.txt` | about 15 min (header); research solver, one core; memory not documented | The tables of 4.44 (share of a 45-degree track's cooling 37 to 84 % and 64 to 94 %, errors on the 42 windows) against the printed ones; then redraw |
| 2 | `gerber-models` | `fig_19_diagonal_gate.png`; README 4.48 | `make_figures.py fig_diagonal_gate` (also reads `out/windows_storm.npz`, present and newer than the corrected program) | `out/diagonal_gate.json`: **absent** | `PYTHONPATH=. .venv/bin/python research/gerber-models/scripts/study_diagonal_gate.py \| tee $LOG/diagonal_gate.txt` | about 15 min (header); memory not documented | The table of 4.48; the statement of 4.48 that 4.50 corrected must still read as corrected |
| 3 | `gerber-models` | `fig_24_diagonal_heldout.png`; README 4.50 | `make_figures.py fig_diagonal_heldout` | `out/diagonal_heldout.json`: **absent** | `PYTHONPATH=. .venv/bin/python research/gerber-models/scripts/study_diagonal_heldout.py \| tee $LOG/diagonal_heldout.txt` | the script header says 30 min, the README says about 3 hours (60 windows at three cell sizes, 32 tilted tracks): **plan 3 hours**; memory not documented | The 4.50 tables; that no share passes the held-out test (the conclusion of 4.50 and the "experimental" mark of figure 10) |
| 4 | `gerber-models` | README 4.15 (time and memory of the mappings) | none (a table) | none (prints) | `.venv/bin/python research/gerber-models/scripts/bench_mapping_cost.py \| tee $LOG/mapping_cost.txt` | about 2 min; a timing, so it belongs to the clean-machine group | The times and memory of 4.15; whether it was re-run in the last pass could not be determined from the files |
| 5 | `solid3d-verification` | `fig_09_solve_cost.png`; the times of `CHANGELOG.md`, `docs/versions.md`, `docs/models.md`, the comment of `pcbthermal/solid3d.py` (A4) | `make_figures.py cost` (`fig_cost`; the `REPORTED_3D` and `REPORTED_LAYERED` markers become measured points) | `out/solve_cost.json`: present, newer than the corrected program, but only 10 cases up to 247 884 unknowns | first extend `CASES` of `study_solve_cost.py` to the sizes of the documents (3D solid 160 000, 254 000, 400 000, 512 000 unknowns, which needs the study to run inside `solid3d.size_limit` as `study_small_pad_convergence.py` does; layered FVM 1 000 000 and 2 000 000), then `.venv/bin/python research/solid3d-verification/scripts/study_solve_cost.py` | now 5 min and up to 5 GB; extended about 25 min (documented: 276 s and 5 GB at 400 000, 320 s and 8 GB at 512 000, layered 97 s and 4.4 GB at 1 million, 273 s and 8.4 GB at 2 million); up to about 8.4 GB | The measured times against the documents (49 s at 160 000 and 130 s at 254 000 were measured under swap; the quiet machine gave 1.9 s at 158 000 and 3.4 s at 248 000); write the machine and its memory state in the README |
| 6 | `solid3d-verification` | README 4.2 (small pad: where the converged temperature is) | none (a table; figure 2 is drawn inline) | none (prints) | `.venv/bin/python research/solid3d-verification/scripts/study_small_pad_convergence.py \| tee $LOG/small_pad.txt` | about 6 min; scikit-fem (installed, 12.0.2); the 320 000-unknown solves are the heavy part, memory not documented | The 4.2 columns (1 and 0.5 mm, 4 and 8 slabs) and the independent-solver columns |
| 7 | `solid3d-verification` | README 4.2 (FEM mesh checks and the example-board value) | none | none (prints) | `.venv/bin/python research/solid3d-verification/scripts/study_fem_hand_checks.py \| tee $LOG/fem_hand_checks.txt` | header says about 11 min, the README says about 6; needs scikit-fem | 90.63 to 90.57 degC (1 to 0.5 mm), 0.0003 degC (4 to 2 elements per gap), 85.57 and 85.59 degC |
| 8 | `effective-conductivity` | README 4.2 and section 8 (the mesh check: 7.84 to 7.81 W/mK from 2.5 to 0.5 mm cells, 7.81 with twice the sub-slabs); feeds no figure of its own, but `fig_03` and `fig_04` read the same JSON | `make_figures.py` (all, a few seconds) | `out/culham_1998.json`: present, newer than the corrected program, but **without the `mesh_check` key** (every run rewrites the file; the last one had no flag) | `.venv/bin/python research/effective-conductivity/scripts/study_culham_1998.py --mesh-check \| tee $LOG/culham.txt` (once, with the flag, so the file keeps both parts) | about 15 min plus 2 for the flag; memory not documented | The four cell sizes (2.5, 1.25, 0.625, 0.5 mm) against the README numbers; then redraw figures 3 and 4 |
| 9 | `power-calculator` | `fig_06_design_term_coverage.png`; README 4.7 table; the example block against `docs/calculators.md` 1.1b and 1.1c | `make_figures.py design` (`fig_design_coverage`) | none: the bands are typed in `DESIGN_COVERAGE` of `make_figures.py` (copied from an earlier printed table) | `.venv/bin/python research/power-calculator/scripts/study_design_term_coverage.py \| tee $LOG/design_term_coverage.txt` | README says about 6 min, the header says about 10 (four levels, several tens of 1 mm solves per band) | **The figure must be re-fed by hand**: copy the printed bands (nominal, best, worst of the levels none, cad, hand, estimated for the four boards) into `DESIGN_COVERAGE` and into the README 4.7 table, then `make_figures.py design`; check the true 2 W stays inside or outside the same bands |
| 10 | `power-calculator` | README 4.5 (RthetaJA at 1 to 0.25 mm cells, JEDEC board with a bottom plane) | none (a table) | none (prints) | `.venv/bin/python research/power-calculator/scripts/study_cell_size.py \| tee $LOG/cell_size.txt` | the header says about 15 min, the README says about 30 | The 4.5 table (CSD17308Q3 46.4 to 47.1; JEDEC with vias 31.6 to 32.2; without vias 83.6, 68.1, 72.9, 74.5). It was run in the review on the corrected program: this repeat is a confirmation |
| 11 | `via-fill` | README 7.3 (the independent reference at 0.0625 and 0.05 mm; the corrected 0.05 mm run "was not repeated") | none (figure 6 uses the 0.1 and 1/12 mm cells and is drawn inline) | none (prints) | `.venv/bin/python research/via-fill/scripts/study_via_model_checks.py --fine \| tee $LOG/via_fine.txt` | about 8 min plus 20 to 30 for `--fine` (450 000 and 700 000 unknowns), **about 10 GB: alone** | The 0.05 mm point stays near the 40.4 to 40.5 K of the other references (no open bore of zero conductivity); update the sentence "was not repeated" in 7.3 |
| 12 | `gerber-models` | the short studies that the review list R7 names as not re-run and the later list does not name as re-run: README 4.6 (`study_fine_scan.py`, 2 min), 4.8 (`study_heater_size.py`, 2 min) and 4.11 (`study_patterns.py`, 1 min) | none | none (print) | the three commands, `.venv/bin/python research/gerber-models/scripts/<script>.py` | 5 min in all | The tables of 4.6, 4.8, 4.11 against the README (they are short; listed so that nothing named in R7 is left) |

**Left out because they were re-run in the last pass on the corrected program** (the file or figure is newer than it, and the review printed the same digits): `effective-conductivity` Muzychka and others `--mesh-check` (30 to 50 min; `out/muzychka_2003.json` holds `mesh_check`) and `study_biot_definitions.py` `mesh_check` (`out/biot_definitions.json`); `models-comparison` `validation_study.py` with `--fem` (README 4.1) and `study_time_and_coefficients.py` (2 min by its header, so not a long run); `stackup` `study_real_1oz_stackups.py` and `study_inner_copper_1oz.py` with the 3D solid (4 and 3 min, run inside `make_figures.py`); `component-heatsink` (longest study 4 min), `block-and-fins` (seconds), `outline`, `theory`; `gerber-import` and `gerber-nets` (every study is 5 min or less and was re-run by the reviews; their libraries gerbonara, shapely, pygerber and pcb-tools are **not installed in this `.venv`** now, so install them with `pip` before any rerun of those two folders; the fetched boards are in `gerber-import/data/`); and the `gerber-models` studies of the "Re-run (all of them now)" list (4.2, 4.5, 4.7, 4.11 two-layer, 4.25 to 4.28, 4.31, 4.38 and others). The old rows of `models-comparison` 4.5 (wxPython) cannot be repeated (F9).

**2. The order of the run** (shortest first would hide the memory problem; the clean-machine timing first, because it must be measured when nothing else has run since the restart):

1. Restart; log in; start nothing else (no browser, no editor); `vm_stat` and `sysctl hw.memsize` into the log.
2. **Clean-machine timing**: rows 5 and 4 (about 30 min). Alone, first.
3. **Memory-hungry, one at a time, nothing else running**: row 11 (about 40 min, 10 GB), rows 6 and 7 (about 12 to 17 min).
4. **Medium**: rows 8, 9 and 10 (about 15 + 10 + 15 to 30 min; they may run two at a time because each is single-process and uses little memory, but not during rows 5, 4 or 11).
5. **Diagonal studies last, in the background of the writing**: rows 1 and 2 together (about 15 min each), then row 3 (3 hours). They need no more than the research solver, so the reading of the earlier results (the after-steps) can start while row 3 runs, but nothing heavy may start.
6. The short extras of row 12 at the very end.

Total: about 5 to 6 hours, of which row 3 is 3 hours (rows 5, 4, 11, 6, 7: about 1.5 hours; rows 8, 9, 10: about 45 minutes in sequence; rows 1, 2, 12: 35 minutes).

```sh
cd /Volumes/SSD/PROJETOS/pcb-thermal-lab                                       # on the branch research/gerbers
export LOG=$HOME/pcbt-long-runs && mkdir -p $LOG                               # logs stay outside the repository
(vm_stat; sysctl hw.memsize hw.ncpu) > $LOG/machine.txt
# 2. clean-machine timing (extend CASES of study_solve_cost.py first, row 5)
.venv/bin/python research/solid3d-verification/scripts/study_solve_cost.py | tee $LOG/solve_cost.txt
.venv/bin/python research/gerber-models/scripts/bench_mapping_cost.py | tee $LOG/mapping_cost.txt
# 3. memory-hungry, alone
.venv/bin/python research/via-fill/scripts/study_via_model_checks.py --fine | tee $LOG/via_fine.txt
.venv/bin/python research/solid3d-verification/scripts/study_small_pad_convergence.py | tee $LOG/small_pad.txt
.venv/bin/python research/solid3d-verification/scripts/study_fem_hand_checks.py | tee $LOG/fem_hand_checks.txt
# 4. medium
.venv/bin/python research/effective-conductivity/scripts/study_culham_1998.py --mesh-check | tee $LOG/culham.txt
.venv/bin/python research/power-calculator/scripts/study_design_term_coverage.py | tee $LOG/design_term_coverage.txt
.venv/bin/python research/power-calculator/scripts/study_cell_size.py | tee $LOG/cell_size.txt
# 5. the diagonal studies (research solver)
PYTHONPATH=. .venv/bin/python research/gerber-models/scripts/study_diagonal.py | tee $LOG/diagonal.txt
PYTHONPATH=. .venv/bin/python research/gerber-models/scripts/study_diagonal_gate.py | tee $LOG/diagonal_gate.txt
PYTHONPATH=. .venv/bin/python research/gerber-models/scripts/study_diagonal_heldout.py | tee $LOG/diagonal_heldout.txt
# 6. short extras
for s in study_fine_scan study_heater_size study_patterns; do .venv/bin/python research/gerber-models/scripts/$s.py | tee $LOG/$s.txt; done
```

**3. After the runs**
* Regenerate the figures that read the new files: `.venv/bin/python research/gerber-models/scripts/make_figures.py fig_diagonal fig_diagonal_gate fig_diagonal_heldout`; `.venv/bin/python research/effective-conductivity/scripts/make_figures.py`; `.venv/bin/python research/solid3d-verification/scripts/make_figures.py cost`; for `power-calculator` first paste the printed bands into `DESIGN_COVERAGE` (row 9) and then `make_figures.py design`.
* Read every regenerated PNG (the whole image, at full size) and run `.venv/bin/python research/check_figures.py`.
* Compare each printed table with the README section of its row; where a number moves, change the README and every document that quotes it (`CONCLUSIONS.md`, `INTEGRATION.md`, the folder's `docs/`, `ROADMAP.md`); where it does not move, write "reproduced to the digit" with the row number. Mark numbers that could not be reproduced.
* Record the machine (model, memory, the `machine.txt` log) and the time of each run in the README of its folder (row 5 also in A4 and in the text for the project documents under `solid3d-verification/docs/`; the program's documents are not edited on this branch).
* Run `.venv/bin/python -m pytest -q tests/test_docs.py` and the tests of each touched folder; commit one folder at a time (English message, imperative); push only when asked.
* The three diagonal figures (`fig_08`, `fig_19`, `fig_24`) are still drawn in the old font and style, because their data files are absent and the figure functions could not be run; rows 1 to 3 redraw them with the current `make_figures.py`, and that is the only way they change font.

* **First study**: do the rows in the order above, one at a time, with nothing else running.
* **If it ends well**: no figure or number of the research folders rests on a run that was not repeated on the corrected program, and A4 is closed.
* **Status**: waits for the maintainer's order (the same restart as A4). Could not be determined: the memory of rows 1 to 4 and 6 to 10 (not documented in the scripts or the READMEs); whether `bench_mapping_cost.py` and the three short studies of row 12 were re-run (no output file); the true run time of row 3 on this machine (header and README disagree).
