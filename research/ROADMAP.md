# What we want to investigate

What is left to finish, in the order recommended (section 1), and the pool of open questions by area (section 2). A defect of the program found by a study is recorded in the README of its folder; its correction is an item of `docs/versions.md` (chapter "Planned"), the only place where program work is listed. The register of the reviews is [`REVIEW.md`](REVIEW.md); the index of the folders is [`README.md`](README.md).

**Rule.** An item leaves this document when its study is finished and the result is in the README of its folder. The table of section 1 is the only place with the order; the pool has no order. The labels A1 to H6 are kept when an item leaves, because other documents cite them. An item that changes a model needs the reviewer before it is closed. Status: `open` nothing done, `partly` a first look exists, `waits` needs a decision or a condition.

## 1. Next work, in the order recommended

Rows keep their numbers because other documents cite them (rows 1 to 3, 5 and 6, the long runs, the timings documents, the merge of `develop` and its publication, are done and removed; row 4 is the decision list in `REVIEW.md`). Rows 7 to 12 block program work of `docs/versions.md` "Planned"; rows 13 to 17 block nothing.

| # | What | Folder | Done when |
| --: | :-- | :-- | :-- |
| 4 | The decisions left to the maintainer | `REVIEW.md`, last section | each taken; the ones that need a study become rows |
| 7 | A5, the point via and the cell | `via-fill` | Peaceman and spreading compared against `layered3d.py` from 1 to 0.0625 mm on two boards; one chosen; reviewer |
| 8 | A6, Lumped and Analytic overstate vias | `via-fill` | the part of the construction that carries it found; a correction or a warning |
| 9 | A1, subdivide the gap of multilayer boards | `power-calculator`, `effective-conductivity` | 1 to 4 nodes on 2, 3, 4-layer boards against `layered3d.py`; script versioned; reviewer |
| 10 | A2, the Analytic model on one-layer boards with partial copper | `power-calculator` | the three candidate causes separated; a better estimate or a stated limit |
| 11 | A3, the rotated square in the 3D solid at a high side coefficient | `solid3d-verification`, `outline` | edge conductance per cell checked; a correction or a documented limit |
| 12 | A11, laminate nodes for patterned copper | `gerber-models` | the number of nodes chosen on windows, solid copper and pads together; reviewer |
| 13 | C3, the channel effect between close fins | `block-and-fins` | Elenbaas and Bar-Cohen papers read, the correlation reproduced; a threshold or a correlation proposed |
| 14 | D1, the JEDEC board of the calculator | `power-calculator` | JESD51-3/-7 read, the board rebuilt, rows moved to a 0.25 mm cell |
| 15 | The Gerber items in order: E2, E1 with E9, E6, E3, E7 and E10, E4, then E5 and E8 | `gerber-*` | each as its item says; E2 decides the import default |
| 16 | The theory sources, in the order the other items need them (C3, D1, F1, F3, F4, E7) | F1 to F9 | a status raised in `theory/BIBLIOGRAPHY.md` only with a record of the reading |
| 17 | G1, a measurement on a physical board | `models-comparison/docs/measurement-protocol.md` | board built and measured, or public data found |

The rest of the pool (A7 to A10, B1 to B4, C1, C2, C4 to C6, D2 to D4, H6) has no place in the order: each is taken when a program feature or a review needs its answer.

## 2. The pool of questions

Format: question; Why (evidence, with its pointer); status; Next step (the first study, then what would change in the program).

### A. Models and numerics
* **A1. Subdivide the gap of every multilayer board** (#9). Does more than one node through the gap remove the error against a resolved 3D solution? Why: a 2-layer board reads 2 to 8 % low in the FVM (-2.3, -3.8, -7.7 % on three boards; `power-calculator` 4.5 to 4.7; the one-layer case is fixed, `effective-conductivity` 4.11); the measurement ran from a scratch directory and is not versioned. Open. Next step: the sweep of the one-layer laminate on boards with full copper, a pad, a part and vias; then a change of the 2- and 3-layer results.
* **A2. Why the Analytic model is hot on one-layer boards with partial copper** (#10). Why: -32 % to -13 % on a 2-layer board with a 20 mm pad (`power-calculator` 4.7). Open. Next step: a pad of growing size against the independent solver to separate the causes.
* **A3. The 3D solid with a rotated square at a high side coefficient** (#11). Why: +1.15 K above the aligned square (reviews of `solid3d-verification` and `outline`). Open. Next step: rotate square and board edge separately on a copy, vary `h_side` and the cell.
* **A5. The point via and the cell** (#7). Which treatment makes the FVM/FDM via converge: the Peaceman well index or always spreading the barrel over its disc? Why: example board -4.49 / -3.89 / -3.59 K at 1 / 0.5 / 0.25 mm; error 0.1 to 0.3 K at 0.5 to 1 mm (`via-fill/INTEGRATION.md` 1). Partly (defect measured, two corrections designed, none compared). Next step: compare both against `layered3d.py`.
* **A6. Why Lumped and Analytic overstate vias** (#8). Why: copper-fill gain 35 to 52 % too large, -6.3 to -7.0 K against -3.9 to -4.5 K (`via-fill` 4.5 and 4.6). Open. Next step after A5: fill sweep with one via, a row and an array, per model; decide first whether to investigate or only document.
* **A7. The residual between Analytic and FVM with insulated edges**. Why: the 0.3 to 1.0 % is the edge loss the series leaves out; with insulated edges -0.04 to -0.29 % is unexplained (`theory` 7). Open (small). Next step: series truncation and cell-centre against the mode projection.
* **A8. A time simulation with a block, and of the 3D solid**. Why: steady state only today (`block-and-fins/INTEGRATION.md`, `solid3d-verification` 8). Open. Next step: FVM transient with a block as the reference; a lumped capacity in the ring network.
* **A9. The outline: scaling, holes and parts inside a cut**. Why: the same-area rectangle is 10 to 18 % cool near the edge or in a T arm (`outline` 4.2); the centroid scaling and the lost edge over many outlines are printed by no script. Open. Next step: scripts for both; maps of the stretched field against the FVM.
* **A10. Multigrid and the solver timings**. Why: timings quoted by the program documents are printed by no script (`theory` 7); topic 16 has no source for its formulas. Open. Next step: time direct, CG, SOR and AMG-CG on the example and a 1 million unknown board.
* **A11. Laminate nodes for patterned copper** (#12). Why: two nodes are 5.5 to 13.6 % cool on seven real windows, 1.9 and 5.3 % with eight (`gerber-models` R2). Open. Next step: sweep 1 to 8 nodes on the windows, the nine boards and the pads; a change of `laminate.py`.

### B. Boards, vias and stack-up
* **B1. Real inner layers with 30 to 70 % copper**. Why: the stack-up study used planes on every inner layer (`stackup` 4.6, limit a). Open. Next step: zones at 30, 50, 70 % fill on the 4-layer template against `layered3d.py`.
* **B2. Stack-up data that is missing** (blind and buried vias, heavy copper, metal core, more fabricators). Why: Sierra, Wuerth and Multi-CB gave nothing usable; two tables do not add up; the 6-layer middle prepreg is thicker than JLCPCB and PCBWay (`stackup`, last section). Partly. Next step: one table per fabricator with its reading status.
* **B3. Sources for the via fill conductivities**. Why: "up to 16" and "silver 3 to 15 W/mK" were found in no source (`via-fill`, "What was read and what was not verified"). Open. Next step: filler datasheets and the fabricators' pages.
* **B4. Dielectric and copper sensitivity beyond the 4-layer board**. Why: "dielectric 1 %, copper 5 %" holds only on the 4-layer board with vias (`stackup` 7). Partly. Next step: extend `study_dielectric_sensitivity.py` to other layouts.

### C. Parts, heatsinks and blocks
* **C1. The junction node**. Why: without a heatsink the node is 1.3 to 3.4 K below the worst-case offset; with 12 K/W the junction rise roughly halves (`component-heatsink` 4.10). Partly (prototype). Next step: more datasheet packages with both RθJC values.
* **C2. Heatsink scenarios and the catalogue values**. Why: forced factors from one guide compared with a few curves; catalogue values from listings not re-opened; Lee's formula from memory (`component-heatsink` 7). Partly. Next step: open the guide and 10 catalogue curves; fit exponent and factors.
* **C3. The channel effect between close fins** (#13). Why: the warning is at 4 mm; a remembered correlation puts a 6.5 mm gap 10 to 30 % below the typed coefficient; Elenbaas and Bar-Cohen never opened (`block-and-fins` 4.1). Open. Next step: reproduce the Elenbaas correlation and compare with the finned FVM block.
* **C4. Heat capacity: the Foster chain and the top path in time**. Why: steady state only; the block takes 27.5 % of the heat with paste (`component-heatsink` 4.9). Open. Next step: a Foster chain from datasheet Zth against the FVM transient.
* **C5. A heatsink larger than its contact, and a plate on top**. Why: `component-heatsink/NOTES.md` R3 and R8. Open. Next step: base spreading with a smaller contact against the FVM and the 3D solid.
* **C6. Datasheet values that are assumed or disputed**. Why: θJC(top) of the MOSFET and the Schottky assumed; the SS12 sheet (20 K/W) not re-opened against Vishay's 28 K/W (`component-heatsink` 7). Partly. Next step: open the datasheets, record the status per value.

### D. Calculators
* **D1. The JEDEC board of the power calculator** (#14). Why: JESD51-3/-5/-7 are behind a login; the no-via row moves from 84 to 73 K/W with the cell (`power-calculator` 4.5). Waits (standards to obtain). Next step: read the board, rebuild it, move the rows to a 0.25 mm cell.
* **D2. The known-power reference and the two-point fit**. Why: fits only parts with a controllable dissipation; the copper error it removes also goes away with Gerber import (`power-calculator`, last section). Partly. Next step: a two-point fit on the validation parts.
* **D3. Assumed inputs of the validation**. Why: the via array under the TPS7A47 and the maximum RθJC of the CSD17308Q3 are assumed. Open. Next step: sweep the assumed inputs, record the range of the errors.
* **D4. The band and drawing errors**. Why: the band did not hold the true power for a drawing error in 3 of 4 cases (`power-calculator` 4.7). Open. Next step: add copper area and board size to the one-at-a-time effects.

### E. Gerber import and models
* **E1. Diagonal faces (nine-point links)** (#15). Can the cell tensor give a share that depends on cell over track width and passes a held-out test? Why: the gate gains 0.1 points instead of 0.4 on 60 new windows, nothing on a new board, and is worse at 0.5 mm cells (`gerber-models` 4.48, 4.50). Partly (failed the held-out test). Next step: fit the share on one set of boards, test on boards with many diagonal tracks.
* **E2. Which copper mapping, against which reference** (#15). Why: mean errors over eleven boards against the program's pixel run: fill 7.4 %, lambda 2.4 %, cell problem 2.4 %, flow 2.3 %, Wiener upper 2.3 % (4.38, 4.43); that reference is itself 5.5 to 13.6 % cool on patterned copper (R2) and uses the four-neighbour stencil. Partly. Next step: repeat the ranking with finer pixels and the nine-point reference; the default of an import.
* **E3. The Lumped and Analytic models with a mask** (#15). Why: Lumped -16 % and Analytic -26 % on the rectangle board (`gerber-models` 4.35, `INTEGRATION.md` 6). Open. Next step: effective conductance per ring or region from the mask.
* **E4. Validation scenarios that are missing** (#15). Why: Sampson's bitmaps are figures, Blackmore has no measurement, Guenin's overlap is only in notes (`gerber-models/CONCLUSIONS.md` 4, 5). Open. Next step: rebuild Sampson's board; a trace-over-plane case against the 3D solid.
* **E5. Hatched zones and the zone pattern** (#15). Why: the arithmetic fill is the optimistic limit; the geometric-mean variant moves hatched zones 26 to 45 % (`gerber-models/INTEGRATION.md` 5, 6). Waits for the maintainer. Next step: hatched zones against the resolved mask; a `pattern` field.
* **E6. Behaviour at fine cells and in time** (#15). Why: the 3D solid at fine cells is not verified; heat capacity and through-thickness conduction stay arithmetic (`gerber-models` last section). Open. Next step: link to A5; a transient of an imported board against a resolved mask.
* **E7. The Gerber reader: scope and conformance** (#15). Why: 161 of 164 files within 3 % (`gerber-import` 4.17); the Ucamco example sets were not run (`gerber-import/CONCLUSIONS.md` 4). Open. Next step: fetch them into `data/` and run `study_reader_conformance.py`.
* **E8. Nets with voltage and current** (#15). Why: a 0.1 ohm link in a 1.5 A rail makes 225 mW, 18 times the copper (`gerber-nets` 4.40); vias, regulators, ratings and the form of the inputs are open. Waits (whether the electrical side enters before the import). Next step: vias and regulators in the prototype; coupling with the thermal run.
* **E9. Thin tracks at an angle** (#15). Why: area within 0.5 % except 45 degrees (+-6 %); the five-point stencil +97 % at 1.5 px, +10 % at 8 px, +6 % at 12 px (`gerber-nets` 4.23); tied to E1. Partly. Next step: a lattice-independent resistance.
* **E10. Transformed apertures and aperture blocks** (#15). Should the reader implement `LM`, `LR`, `LS` and `AB`? Why: it refuses such files (`gerber-import` 4.19, 7); how often real boards use them is not known. Open (to implement, not decided). Next step: count them in recent CAD outputs; implement against the 2024.05 specification.
* **E11. The other Gerber layers and the part identity** (#15). Can a heater be drawn from the solder-paste (or courtyard, or component) layer of a project and identified by its reference designator? Why: today the import reads copper, holes and the outline; the maintainer wants to click the paste polygon of a part and give it a power, and the file does not say which part it is. Open. Next step: find a real project (KiCad, Altium or other, open licence) that has the paste layers and a pick-and-place file, or ODB++ or IPC-2581; read the Gerber X2 attributes (`.AperFunction`, `.P`, `.C`) that may carry the designator; compare what each source gives; decide what stays manual.

### F. Theory, sources and verification
* **F1. The effective conductivity above Biot 60** (#16). Why: 2 to 6 % different from Culham and Yovanovich (1998); the 1.62 mm of the text explains about half of the base-case shortfall (`effective-conductivity` 4.2, 4.9, 8). Open. Next step: reopen the paper's pages 460 to 467 and test the series truncation.
* **F2. Cases of Muzychka and others and of Lemczyk not run** (#16). Why: the heat-sink base with four sources and the compound plate (`effective-conductivity` 7). Open. Next step: both cases with `layered3d.py` and the program.
* **F3. Natural convection correlations: the originals** (#16). Why: Churchill and Chu (1975) and Churchill (1977) never opened; `ht` documentation and code differ in the Hollands formula (`theory/BIBLIOGRAPHY.md`). Open. Next step: open the papers, check the forms numerically.
* **F4. Formulas written from memory** (#16). Why: 2D Bruggeman, Hashin-Shtrikman and the Keller-Dykhne duality were checked numerically (`theory/scripts/check_mapping_formulas.py`), no textbook opened. Open. Next step: Milton and Torquato, with page and equation.
* **F5. Sources to open** (#16). Why: the statuses M, N and S of `theory/BIBLIOGRAPHY.md` (textbooks, papers, JEDEC, IPC, ASTM, ASME and Ucamco documents). Open. Next step: in the order the other items need them (C3, D1, F1, F3, F4, E7).
* **F6. Planned models without a source** (#16). Why: topics 12 to 16 (Foster chain, heatsink scenarios, virtual JEDEC test, import, multigrid) are textbook knowledge without a source (`theory` 7). Open. Next step: one source and one reproduced case per topic.
* **F7. Grid convergence of the references** (#16). Why: the Roache/ASME formula is from memory; 2.5 mm cells overstate a 25 mm source by 0.3 to 0.4 K (`models-comparison`). Partly. Next step: a GCI with three grids on each reference.
* **F8. Papers read only in part** (#16). Why: Yovanovich's Table 3 confirmed by the exact series but the paper not re-read; Lee's equations 1 and 2 are images that did not come through (`solid3d-verification` 7). Open (small).
* **F9. Old results not re-run** (#16). Why: the rows of the removed wxPython program need that program (tag `legacy-wxpython-1.0.0`). Open (low priority). Next step: check out the tag in a separate environment, or mark the rows as quoted.

### G. Physical measurement
* **G1. A measurement on a physical board** (#17). Why: no model has been compared with one; the protocol is `models-comparison/docs/measurement-protocol.md`, nothing built. Waits for a board and an instrument. Next step: build and measure, or find public data with known power and copper.

### H. Tooling and method
* **H6. Studies that need a script before they are quoted**. Why: the 2-layer measurement of A1, the centroid scaling and lost edge of A9, the multigrid timings of A10, the old rows of F9. Open. Next step: write each script or remove the number.

## 3. The long runs: done

The twelve long runs were made on a quiet machine and compared with the READMEs; the results and the machine are in the last section of each README and in `gerber-models/README.md` R7. Every table reproduced to the digit except the cost numbers of the 3D solid and the layered FVM (`solid3d-verification` figure 9, `docs/for-the-project-documents.md`) and of the mappings (`gerber-models` 4.15), corrected in the research documents; the program documents were corrected on `docs/timings`. The limit `MAX_CELLS = 250 000` and the memory guard rest on the old numbers; a guard by estimated memory is the better form.
