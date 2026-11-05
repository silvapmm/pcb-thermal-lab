# Theory: the problem, the models and how we know they are right

This folder explains the physics behind PCB Thermal Lab: this page is the overview, one topic file per model, equation or planned method holds the detail (picture, formulation, limits, tests, sources), and the equations themselves are in [`docs/theory.md`](../../docs/theory.md). It changes nothing in the program.

## 1. The problem

A printed circuit board is a stack of thin copper planes separated by a laminate (FR-4) that conducts hundreds of times less than copper. Parts on its faces dissipate power, vias join the planes, and the air takes the heat away from both faces (and a little from the edges) by convection and radiation. The designer wants to know where the temperature ends up: the map over the board, the hottest points and the junction temperature of each part, in steady state and when the power changes in time.

Three things make it hard. **The heat spreads in thin copper**: a part of a few millimetres sits on a sheet of tens of millimetres, so the temperature is steep under the part and flat far away, and how much copper there is decides how high the peak is (middle panel of figure 45). **The planes are coupled through a poor conductor**: over a large area the laminate couples them well, but under a small part the heat reaches the other planes mostly through the vias, and a via is a small copper tube that the heat must converge on. **Every board is different**: outline, copper pattern, stack-up, heatsinks; there is no single formula, so the board has to be computed.

![The problem and the way to a model](figures/fig_45_problem_to_model.png)

*Figure 45 (`figures/fig_45_problem_to_model.png`): left, a board in section with a part, three copper planes and a via, and the paths of the heat (sideways in the copper, down the via, to the air from both faces); middle, the rise along the board under a part (closed form of a 1D fin, illustrative): with little copper the peak is high and narrow, with planes of copper low and wide, for the same heat; right, the chain from the board to the result.*

![The continuum problem](figures/fig_20_continuum.png)

*Figure 20 (`figures/fig_20_continuum.png`): the equation behind every model: conduction in the board and in any metal block, exchange with the air on every face, a part as a power over its footprint. Theory section 1.1.*

## 2. What the program computes

Five models take the same board. Four of them share one idealisation (figure 1): one temperature per copper layer and position, the laminate between two layers a resistance through its thickness. The fifth, the 3D solid, has real slabs and measures what that idealisation costs.

![Map of the theory](figures/fig_38_document_map.png)

*Figure 38 (`figures/fig_38_document_map.png`): the board, the layered idealisation, the five models, and the pieces they share; the numbers are the sections of `docs/theory.md`. Schematic.*

![Layered idealisation](figures/fig_01_layered_idealisation.png)

*Figure 1 (`figures/fig_01_layered_idealisation.png`): the layered idealisation: one node per copper layer, the gap a one-dimensional resistance (cut into laminate nodes where copper is absent), the air on the outer layers, and the energy balance every result reports. Theory section 1.2.*

| Model | The idea | What it is for |
| :-- | :-- | :-- |
| **FVM** (finite volumes) | a heat balance on every cell, a sparse matrix | the reference: any geometry, steady state and time |
| **FDM** (finite differences) | the same physics on nodes, the board edge a node | a second discretisation, to see the grid error |
| **3D solid** | real slabs for every copper layer and gap | the check of the layered idealisation; steady state, at most 250 000 unknowns |
| **Lumped** (ring network) | rings around each part, joined by resistors | very fast estimate; rectangles only |
| **Analytic** (cosine series) | exact on a uniform board, local corrections for vias and heatsinks | fast, smooth estimate; rectangles only |

![FVM cell](figures/fig_02_fvm_cell.png)

*Figure 2 (`figures/fig_02_fvm_cell.png`): the FVM balances the heat of each cell through its faces; a face between two cells is two half cells in series; the matrix is symmetric and has one solution. Theory section 2.*

![FDM nodes](figures/fig_03_fdm_nodes.png)

*Figure 3 (`figures/fig_03_fdm_nodes.png`): the FVM puts the unknown at the cell centre, the FDM on the node, so the FDM has half cells on the edges and quarter cells at the corners. Theory section 3.*

![3D solid](figures/fig_04_solid3d_slabs.png)

*Figure 4 (`figures/fig_04_solid3d_slabs.png`): the 3D solid: one slab per copper layer, four per gap, vias as copper rods, blocks as metal slabs. Theory section 4.*

![Lumped rings](figures/fig_05_lumped_rings.png)

*Figure 5 (`figures/fig_05_lumped_rings.png`): the Lumped model cuts the board into rings by distance from each part, joins them by resistors and adds the parts by superposition. Theory section 5.*

![Analytic modes](figures/fig_06_analytic_modes.png)

*Figure 6 (`figures/fig_06_analytic_modes.png`): the Analytic model writes each layer as a sum of cosines and corrects locally for vias and heatsinks on tiles. Theory section 6.*

Around the models are the pieces they share. **Vias** carry a constriction resistance, the heat converging on the barrel (theory section 1.5; on the grid 2.6, in the rings 5.1, in the tiles 6.1). **Metal blocks and fins** are extra node layers (section 7, figure 11). **Heat transfer coefficients** are computed per face, convection plus radiation, in a loop around any model (section 8, figure 8). **Parts** have a junction-to-pad resistance and, on a component, a top path to the air; the split of the power between the two is the root of an equation, not a loop (section 9, figure 42). **Power profiles** (square waves, CSV tables) are averaged or resolved in time heater by heater (section 10, figure 10). **Input checks and warnings** say where a model is outside its range, before and after the run (`docs/models.md` 3, topic 34).

![Metal block](figures/fig_11_metal_block.png)

*Figure 11 (`figures/fig_11_metal_block.png`): a block with fins on the board, a plate fin, and how the Lumped and Analytic models keep the lateral conduction of the block.*

![Heat transfer](figures/fig_08_heat_transfer.png)

*Figure 8 (`figures/fig_08_heat_transfer.png`): convection and radiation both grow with the temperature, so a constant h overstates the rise at high power and understates it at low power; the loop re-solves until h settles (illustrative values).*

![Memory guard](figures/fig_46_memory_guard.png)

*Figure 46 (`figures/fig_46_memory_guard.png`): left, the chain from the cell to the verdict (lower bound, exact count, estimate, limit); right, the law of the estimate against the unknowns for the FVM (`t_eff` 2 and 6), the FDM (4) and the 3D solid (6) with the coefficients of `memory.CONTINUOUS`, safety factor included and base left out, against 60 % of 16 GiB. Illustrative of the shape: the bytes were measured on one machine (`docs/theory.md` 2.7).*

![Top path split](figures/fig_42_top_path_split.png)

*Figure 42 (`figures/fig_42_top_path_split.png`): a part with a top path, the root of its split, and why the plain loop oscillates (illustrative values).*

![Profile decision](figures/fig_10_profile_decision.png)

*Figure 10 (`figures/fig_10_profile_decision.png`): the temperature oscillates around the response to the average power; heaters with a small oscillation are averaged, the others resolved (illustrative).*

## 3. How we know it is right

Each check is more independent than the one before (figure 22; numbers from `docs/theory.md` 11 and `docs/validation.md`):

* **Exact answers**: the energy balance closes to 1e-12 to 1e-9 on every model; the time stepping has the order it should against the exact solution of a uniform board; the stack-up matches the exact series circuit to 1e-6 K.
* **Solvers against each other**: direct, conjugate gradients and SOR agree to 2e-8 K on five boards.
* **Published solutions**: the 3D solid reproduces Yovanovich's spreading-resistance table to 0.7 to 0.8 %; the metal plate model Seri Lee's article (+0.6 % centre, -0.8 % edge, -4.6 % corner); the convection correlations the textbook values to 1 to 3 %.
* **Independent 3D solutions**: the FVM is within 0.4 to 2.2 % of an independent finite-element solid on four boards (`docs/validation.md` 3), and the FVM, the 3D solid and the Analytic within 0.2 % of the independent solver of the tests on a copper-laminate-copper coupon.
* **Models against each other**: 19 scenarios in all five models (`docs/validation.md` 2). The FVM, FDM and 3D solid agree within a few per cent; the Lumped and Analytic models fail in known cases (a part across a copper edge: 26 to 29 % too cool) and the input checks warn there.

**No model has been compared with measurements of a physical board.** That is the missing rung of the ladder; `calibrate_convection` fits the air coefficient to one measurement when one exists.

![Verification ladder](figures/fig_22_verification_ladder.png)

*Figure 22 (`figures/fig_22_verification_ladder.png`): the checks in order of independence, from exact answers to a physical board (not done). Theory section 11.*

The limits are known and warned: the Lumped and Analytic models work on rectangles (a board with an outline runs on the rectangle of the same area) and are coarse with vias and partly absent copper; the 3D solid is steady state only and limited in size; one node through a thick metal plate hides a gradient (the thick-plate warning); the layered models read low over a part on bare laminate (warned).

## 4. The studies that shaped the program

One row per question that changed the program or confirmed it; a row marked **no change** is a study that led to no change of the program (the question was answered, or the candidate was rejected). The full list is [`../README.md`](../README.md), the review register [`../REVIEW.md`](../REVIEW.md). Versions are those of `CHANGELOG.md`; 2.4.5 is in `develop`, not released.

| Question | What it found | What it changed in the program | Folder |
| :-- | :-- | :-- | :-- |
| Do the layered models match an independent 3D solution? | FVM within 0.4 to 2.2 % of an independent finite-element solid; the 3D solid reproduces Yovanovich's table to 0.7 to 0.8 % | the 3D solid as a comparison model (2.3.0); its laminate of a one-layer board (2.4.2) | [solid3d-verification](../solid3d-verification/README.md) |
| Where does one node through the thickness stop being valid? | published laminate and plate cases reproduced; the hidden gradient is at most `q'' t / (2 k)`, negligible for copper layers | thick-plate warning, laminar natural-convection option, the independent 3D solver in the tests (2.4.2) | [effective-conductivity](../effective-conductivity/README.md) |
| Do the five models agree, and where not? | 19 scenarios; the Lumped and Analytic models fail in known cases | the table of `docs/validation.md` 2, input warnings | [models-comparison](../models-comparison/README.md) |
| How is a part with a heatsink on the package modelled? | a bare mould takes about 1 % of the heat, a clip-on heatsink 41 to 51 %; the fixed-point loop stopped 17 to 58 K low on small pads | `theta` and the top path on a component (2.4.0); the split as a root (2.4.2, `fix/top-path-convergence`) | [component-heatsink](../component-heatsink/README.md) |
| What do a metal block and fins do? | fins within 0.08 % of a 2D fin; the block as one more layer works in the Lumped and Analytic models (an equivalent coefficient did not) | the block in all five models (2.4.0); side walls without the fin ratio (2.4.2) | [block-and-fins](../block-and-fins/README.md) |
| How much does the air between close fins matter? | the channel effect is real; quantified for fins on a vertical board, not all originals obtained | a warning after the run (2.4.4); the correction is not implemented | [fin-channel](../fin-channel/README.md), [fin-channel-sources](../fin-channel-sources/README.md) |
| Which natural-convection level for a vertical face? | the laminar Churchill and Chu form is the exact boundary layer plus a leading-edge term; the choice moves a board by at most 2 % | decided: laminar as the default of new projects, for 2.5.0 (not yet in the program) | [plate-h-level](../plate-h-level/README.md) |
| Which level for a horizontal face? | the upper face lies between the published levels; the lower face has the wrong exponent, but the published forms move a board by -2.7 to +1.3 % | **no change**: a documented limit | [horizontal-plate-h](../horizontal-plate-h/README.md) |
| Which rectangle stands for a board with an outline? | the rectangle of equal area is within 0.2 to 3 % away from the edge (the bounding box 6 to 10 % cool) | equal-area rectangle for the Lumped and Analytic models (2.4.0); the outline edge counted in full (2.4.2) | [outline](../outline/README.md) |
| How does a part across the outline heat the cut cells? | the full-cell power was up to 4 K too hot on a T; the 3D solid is still +1 to +3 K on a turned square at a high edge coefficient | part weights by the board cover (2.4.5); the cut cells of the 3D solid stay in "Planned" | [rotated-square-3d](../rotated-square-3d/README.md) |
| Which stack-ups are typical? | fabricators' builds; 0.5 oz inner copper is the common default | stack-up templates (2.4.0), 1 oz inner option (2.4.2) | [stackup](../stackup/README.md) |
| What fills a via, and does the via converge with the cell? | only copper fill matters (a resin plug does not); the point via drifted below 0.5 mm | via fills (2.4.0); the via as mean-potential couplings with a well, via warnings (2.4.5) | [via-fill](../via-fill/README.md), [point-via-convergence](../point-via-convergence/README.md) |
| Why do the Lumped and Analytic models overstate vias? | the constriction at the barrel was missing (35 to 60 % too much via effect); a double counting in the group term was tested and rejected | the Krogh well and the self-terms (2.4.5); a zonal Lumped model stays in "Planned" | [lumped-analytic-vias](../lumped-analytic-vias/README.md), [lumped-via-groups](../lumped-via-groups/README.md) |
| Why was the SOR slow, and wrong with vias? | the relaxation factor was the optimum of fixed edges; the via blocks were not seen by the update | Young's omega estimate and a block SOR (2.4.5) | [young-omega-tiles](../young-omega-tiles/README.md), [sor-with-via-couplings](../sor-with-via-couplings/README.md) |
| What happens where copper is absent next to the laminate? | one node per layer reads cool over bare laminate (FVM -18 % over a 6 mm window on a 1.6 mm board); extra gap nodes change nothing on full copper | laminate nodes where copper is absent, FVM and FDM (2.4.5); the Lumped and Analytic only warn (2.4.5) | [laminate-nodes](../laminate-nodes/README.md), [bare-spot-under-source](../bare-spot-under-source/README.md), [gap-subdivision](../gap-subdivision/README.md) |
| Can the Analytic model see a copper pad on bare laminate? | its uniform sheet cannot; a candidate correction was measured and not recommended | **no change** to the model; a sharper warning (2.4.5) | [analytic-partial-copper](../analytic-partial-copper/README.md) |
| How are the zones of a layer combined in a cell? | the larger share lost the copper of the other zone (5 to 15 % too cool on real copper) | the union of the points of the zones (2.4.3) | [zone-union](../zone-union/README.md) |
| What power does a measured temperature mean? | the board model run backwards reproduces two datasheet cases (-1.7 % and +3 %); the band of numbers alone missed drawing errors | the Power Calculator (2.4.0) and its design-uncertainty band (2.4.2) | [power-calculator](../power-calculator/README.md) |
| Do the sources of the theory say what we quote? | correlations and published cases reopened and reproduced; some ranges and readings corrected in the folder | **no change** to the program | [theory-sources](../theory-sources/README.md) |
| Can the copper come from Gerber files? | an independent reader, the mapping to cells and the nets work on real boards | prepared for 2.5.0 (import, with the memory guard); nothing in the program yet | [gerber-import](../gerber-import/README.md), [gerber-models](../gerber-models/README.md), [gerber-nets](../gerber-nets/README.md) |
| Vias near an edge, boards with 100 or more vias? | the via kernel has no image of the edge (+12 to +15 % at 1 mm); the fill-in and memory of the matrix grow | warnings (2.4.5); the rest prepared for the memory guard (2.5.0) | [via-real-board](../via-real-board/README.md) |

## 5. The topics of this folder

Each topic file has the same order: picture, what it is, formulation, assumptions and limits, how the program does it, where it is tested, related topics, sources, and what was read. Planned topics say **Status: planned** and claim no results. Sources are cited by key; [`BIBLIOGRAPHY.md`](BIBLIOGRAPHY.md) gives the address and the reading status of each (R read, S summary, M memory, N not obtained). The figure inventory, with where each picture goes in the project documents, is [`docs/theory-figures.md`](docs/theory-figures.md).

| # | Topic | Status | Code | Research folder |
| --: | :-- | :-- | :-- | :-- |
| 01 | [Layered idealisation](topics/01-layered-idealisation.md) | in program | `model.py`, `laminate.py` | [stackup](../stackup/README.md), [solid3d-verification](../solid3d-verification/README.md), [effective-conductivity](../effective-conductivity/README.md) |
| 02 | [Finite volumes (FVM)](topics/02-finite-volume.md) | in program | `fvm.py` | [models-comparison](../models-comparison/README.md) |
| 03 | [Finite differences (FDM)](topics/03-finite-difference.md) | in program | `fdm.py` | [models-comparison](../models-comparison/README.md) |
| 04 | [3D solid](topics/04-solid-3d.md) | in program | `solid3d.py` | [solid3d-verification](../solid3d-verification/README.md) |
| 05 | [Lumped rings (LPTN)](topics/05-lumped-rings.md) | in program | `lumped.py` | [models-comparison](../models-comparison/README.md), [outline](../outline/README.md) |
| 06 | [Analytic series](topics/06-analytic-series.md) | in program | `analytic.py` | [models-comparison](../models-comparison/README.md), [block-and-fins](../block-and-fins/README.md) |
| 07 | [Time stepping](topics/07-time-stepping.md) | in program | `fvm.py` | - |
| 08 | [Heat transfer coefficients](topics/08-heat-transfer-coefficients.md) | in program | `convection.py`, `api.py` | [effective-conductivity](../effective-conductivity/README.md) |
| 09 | [Parts and the junction](topics/09-parts-junction.md) | in program | `analysis.py`, `api.py` | [component-heatsink](../component-heatsink/README.md) |
| 10 | [Power profiles](topics/10-power-profiles.md) | in program | `profiles.py` | - |
| 11 | [Metal blocks and fins](topics/11-metal-blocks-fins.md) | in program | `blocks.py` | [block-and-fins](../block-and-fins/README.md), [fin-channel](../fin-channel/README.md) |
| 12 | [Foster chain](topics/12-foster-chain-planned.md) | **planned** | - | - |
| 13 | [Heatsink scenarios](topics/13-heatsink-scenarios-planned.md) | **planned** | - | [component-heatsink](../component-heatsink/README.md) |
| 14 | [Virtual JEDEC test, known-power reference](topics/14-virtual-jedec-and-known-power-planned.md) | partly planned | `inverse.py` | [power-calculator](../power-calculator/README.md) |
| 15 | [Import and power list](topics/15-import-and-power-list-planned.md) | **planned** | - | [gerber-import](../gerber-import/README.md) |
| 16 | [Multigrid](topics/16-multigrid-planned.md) | **planned** (optional) | - | [models-comparison](../models-comparison/README.md) |
| 17 | [Copper to cells, the tensor](topics/17-copper-mapping-and-tensor.md) | researched | - | [gerber-models](../gerber-models/README.md) |
| 18 | [Spreading resistance](topics/18-spreading-resistance.md) | verification | `solid3d.py` | [solid3d-verification](../solid3d-verification/README.md) |
| 19 | [Nets, current, Joule heat](topics/19-nets-current-and-joule-heat.md) | researched | - | [gerber-nets](../gerber-nets/README.md) |
| 20 | [Board outline](topics/20-board-outline.md) | in program; Gerber reader researched | `model.py`, `geometry.py` | [outline](../outline/README.md), [gerber-import](../gerber-import/README.md) |
| 21 | [Vias and fills](topics/21-vias-and-fills.md) | in program | `model.py`, `viawell.py`, `viaconstriction.py` | [via-fill](../via-fill/README.md), [point-via-convergence](../point-via-convergence/README.md), [lumped-analytic-vias](../lumped-analytic-vias/README.md) |
| 22 | [Stack-up](topics/22-stack-up.md) | in program | `model.py`, `data/stackups.json` | [stackup](../stackup/README.md) |
| 23 | [Power calculator](topics/23-power-calculator.md) | in program | `inverse.py` | [power-calculator](../power-calculator/README.md) |
| 24 | [Thermal interfaces and metals](topics/24-thermal-interfaces-and-metals.md) | in program | `model.py` | [component-heatsink](../component-heatsink/README.md) |
| 25 | [Contact area, air gap, chain of levels](topics/25-contact-area-gap-and-chain.md) | contact area in program; gap and chain researched | `blocks.py` | [component-heatsink](../component-heatsink/README.md) |
| 26 | [Plate spreading on a component](topics/26-plate-spreading-on-a-component.md) | decided (K/W only) | - | [component-heatsink](../component-heatsink/README.md) |
| 27 | [Datasheet numbers and compact models](topics/27-datasheet-numbers-and-compact-models.md) | `theta` and top path in program; junction node not | `analysis.py` | [component-heatsink](../component-heatsink/README.md) |
| 28 | [Continuum problem and sources](topics/28-continuum-and-sources.md) | in program | `model.py`, `geometry.py` | [rotated-square-3d](../rotated-square-3d/README.md) |
| 29 | [Verification ladder](topics/29-verification-ladder.md) | in program | `tests/` | [models-comparison](../models-comparison/README.md), [solid3d-verification](../solid3d-verification/README.md) |
| 30 | [Board orientation](topics/30-board-orientation.md) | in program | `convection.py` | [horizontal-plate-h](../horizontal-plate-h/README.md) |
| 31 | [Program architecture and API](topics/31-program-architecture-and-api.md) | in program | `api.py`, `cli.py`, `jobs.py` | - |
| 32 | [The removed program against the current one](topics/32-legacy-program-against-current.md) | history | tag `legacy-wxpython-1.0.0` | [models-comparison](../models-comparison/README.md) |
| 33 | [Time-dependent results](topics/33-time-dependent-results.md) | in program | `fvm.py`, `profiles.py` | - |
| 34 | [Input checks](topics/34-input-checks.md) | in program | `checks.py` | [effective-conductivity](../effective-conductivity/README.md) |
| 35 | [Curved boards](topics/35-curved-boards.md) | in program | `geometry.py` | - |
| 36 | [Prepreg and sheets in a gap](topics/36-prepreg-and-sheets-in-a-gap.md) | in program | `model.py` | [stackup](../stackup/README.md) |
| 37 | [Why the FVM and the Analytic model agree](topics/37-why-fvm-and-analytic-agree.md) | explanation | - | [models-comparison](../models-comparison/README.md) |

## Adoption

A topic is adopted when the maintainer decides: its text goes into `docs/theory.md` (or `docs/versions.md` "Planned" for planned work), its picture into `docs/images/`, its sources into the bibliography of that document. Corrections for the project documents found here are in [`docs/for-the-project-documents.md`](docs/for-the-project-documents.md).

## What was read and what was not verified

* **Read in full**: `docs/theory.md`, the sections of `docs/models.md`, `docs/versions.md` "Planned", `docs/calculators.md` and `docs/validation.md` named in the topics, and the READMEs of the investigations they cite. The topics restate them; the numbers in a topic come from those documents and are marked with their source.
* **Sources**: the reading status of each is in `BIBLIOGRAPHY.md`; statements from sources marked M or N are marked "(memory)" there. The Python `ht` package (1.2.0) was read: its documentation and its code differ in the Hollands formula. The maintainer's compilation (`docs/reference-compilation.md`) is second-hand; only its numbers were checked.
* **Checked numerically here**: the Bruggeman and Hashin-Shtrikman properties (`scripts/check_mapping_formulas.py`), the correlations (`scripts/check_correlations.py`), the area loss of a polygon corner (topic 35), the coverage sum against the polygon area (topic 28) and the explanation of topic 37 (`scripts/study_fvm_analytic_edges.py`: the first explanation was wrong).
* **The overview (sections 1 to 4)**: its numbers are copied from `docs/theory.md` 11, `docs/validation.md` and the folder READMEs and `CHANGELOG.md`, not re-run here; the middle panel of figure 45 is a closed form chosen to show a shape, not a board.
* **Not verified**: the residual -0.1 to -0.3 % of the Analytic with insulated edges; the multigrid timings (quoted from `docs/versions.md`, printed by no script); the formulas of the planned topics 12 and 16 (textbook knowledge, no source opened).

## Review

* **Status**: topics reviewed against `develop` `3e90a7f` and the READMEs of the investigations they cite; the figures were read one by one. The overview (sections 1 to 4, figure 45) was reviewed separately: every figure it uses was looked at, the verification numbers were checked against `docs/theory.md` 11 and `docs/validation.md` 3 and 16, and every row of the study table against the folder README and `CHANGELOG.md`. Status in [`../REVIEW.md`](../REVIEW.md).
* **Corrected in the overview by the review**: the FVM against the independent finite-element solid is 0.4 to 2.2 % (`validation.md` 3), not 0.4 to 2.4 % "of the 3D solid" (the program's 3D solid is not the independent reference there); the planes are not coupled "mostly through the vias" in general, only under a small part (over a large area the laminate couples them well); the input checks are in `docs/models.md` 3, not theory section 11; the natural-convection row mixed a decided change (laminar default for new projects, 2.5.0) with a documented limit (horizontal faces, no change); the top-path root had no version (2.4.2); rows that led to no change are now marked, and the theory-sources and analytic-partial-copper studies added. Figure 45 had the sideways spreading drawn in the air above the copper; it is now in the plane, and a middle panel shows the shape of the temperature along the board. Figure 38 pointed the vias at 2.6, 5.1, 6.1 only and called section 11 "checks"; it now says 1.5 and "verification" (copied to `docs/images/`, caption of `docs/theory.md` adjusted).
* **Independent checks**: the Lumped factors `f_R` and `f_P` re-derived from the disc solution (topic 05); the top-path closure and its root (topic 09); the fixed point of the power coefficient (figure 9); the theta-method factor and the explicit-Euler limit (figure 7); the laminate construction (topic 01); the explanation of topic 37 (the 0.3 to 1.0 % between the Analytic and the FVM is the edge loss the cosine series leaves out, not mesh error); the 1D fin profile of figure 45 (peak `1 - e^(-a/λ)` and the same area under both curves, so the same heat).
* **Limits**: the numbers of the Gerber topics (15, 17, 19, 20) are those of their folders, reviewed there; the pictures explain, they are not tests; the overview quotes, it does not re-run.
* **Program defects**: none open. The one found here (`Heater.top_resistance()` with `theta` against `junction_theta()` in `analysis.part_split`) is closed: since 2.4.3 the top path exists only on a component (`Heater.has_top_path()`), where the two are the same value (`tests/test_top_path_role.py`).
* **Go / no-go**: go for the overview, after the corrections above.
