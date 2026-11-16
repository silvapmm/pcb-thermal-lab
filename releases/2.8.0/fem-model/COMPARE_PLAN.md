# The comparison campaign: 'test everything and compare'

**Status**: plan only; nothing is run. The maintainer's order: after the FEM steady model (branch 4) and the FEM transient (branch 8) are merged, every model is compared with the FEM and the 3D solid on every board that applies. Executed by `tester` agents, judged by the `reviewer`. The results are written in `docs/validation.md`: **section 56 'FEM comparison campaign'** (steady) and **section 57 'FEM transient'**; those numbers are reserved. No number is quoted here that a script has not printed; the tolerances below are acceptance criteria to be confirmed by the reviewer when the first results exist, not results.

## 1. Models and read-outs

Models: FVM, FDM, Lumped, Analytic, 3D solid, FEM. The headline is the column read-out of every model; the surface and point read-outs (vocabulary of `fix/thick-plate-surface-estimate`) are compared where a model gives them (FEM, 3D solid with copper slabs, FVM/FDM estimate). Differences are always quoted as a share of the rise above the ambient, and as K.

## 2. The campaign

| # | Comparison | Boards and cases | Models | Quantity | Tolerance to meet (to be confirmed) | Written in |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| C1 | Steady, every harness board | the 20 boards of `tests/regression/regress_boards.py` at 2, 1 and 0.5 mm; boards over the FEM cap are skipped and listed | FVM, FDM, Lumped, Analytic, 3D solid, FEM | hottest rise (column), part means, heat balance | FVM, FDM, FEM within about 1 % on boards without vias, edge or outline effects (`docs/validation.md` 3); every other difference is classified (known limit, warned, or unexplained = defect) | 56.1 |
| C2 | Same, surface and point read-outs | boards with a thick layer or a block | FEM, 3D solid (copper slabs), FVM and FDM estimate | surface minus column | the estimate within the tolerance of its own study (`research/through-thickness-readout`) | 56.2 |
| C3 | Muzychka case 2 | the published plate and cross | FEM, 3D solid, FVM, FDM, Lumped, Analytic | surface and column read-outs against the paper's Table 4 | the paper's printed values (reading status R); the column and surface both shown | 56.3 |
| C4 | Published cases | every case already reproduced in `docs/validation.md` and `research/paper-case-studies` that the FEM can represent | all | published number | as in the case's own section; the FEM must not be worse than the 3D solid | 56.4 |
| C5 | Thick plate and block | thick plates (heat spreading through the thickness), metal blocks with and without fins | FEM, 3D solid, FVM, FDM | hottest rise, surface | against the thick-plate bound of `checks.check_thick_plates` and the independent reference of `research/independent-fem-edge` | 56.5 |
| C6 | Thin copper boards | the standard 1.6 mm boards | all | hottest rise | no difference expected beyond the usual (below 1 %); a larger one is a defect | 56.6 |
| C7 | Vias | hollow barrel, arrays, near an edge, partial copper | FEM (patch and rod fallback), FVM, FDM, 3D solid | via effect (rise with minus rise without) | against the independent reference in `research/independent-fem-extensions`; the known FDM and Lumped limits quoted, not re-measured | 56.7 |
| C8 | Edge film | strong edge cooling (200 to 2000 W/m2K), rectangle | FEM, FVM, FDM, 3D solid | hottest rise | as `docs/validation.md` 43, 44, 46 and 47 | 56.8 |
| T1 | Transient step response | boards where all apply: the plain boards, the example board, one board with a block, one with vias | FVM, FDM, Analytic, Lumped, FEM (the 3D solid has no transient) | time to 63 % and the plateau | within 0.5 % of the independent references for the FEM (research result, 8.3 of the extensions); the other models against the FEM with the differences classified | 57.1 |
| T2 | Transient profiles | one square wave per board class, slow and fast | FVM, FDM, Analytic, Lumped, FEM | peak, swing, last-window curve | slow waves as T1; fast waves: the quoted limit (the swing of a small source 0.5 to 3.5 % low) | 57.2 |
| T3 | First seconds | a small source on a bare plate | FEM, FVM, FDM | the first seconds of the step | the stated limit of 2.7.0, not a pass criterion | 57.3 |

## 3. Cost and the load rule

Heavy jobs run **in series**, one `pytest` or study at a time (the rule of 'Agents and workflow'; at most the ceiling of 3 parallel jobs only while the load average is below 5, swap below 2.5 GB and the free memory above 6 GB plus the declared peak). Each job declares its peak memory (the FEM law of `DESIGN.md` 5.3; the 3D solid and the FEM at 0.5 mm on four layers are the heavy ones). A board whose estimate exceeds the memory limit is skipped and listed with the cell that fits; no run is forced past the guard. The campaign is a script per row in `releases/2.8.0/fem-model/scripts/` (`study_compare_<row>.py`, run from the repository root, each with a `@brief` header), all with fixed inputs so the tables can be reproduced.

## 4. Outputs

* One table per row with every model's number, the difference to the FEM and to the 3D solid in K and in percent of the rise, and the verdict (within tolerance, known limit with the section that states it, or defect).
* Figures (`fig_NN` in the folder's `figures/`, linked from the section): bar charts of the difference to the FEM per model and board class; difference maps (the compare views of branch 7, `DESIGN.md` 6) for three boards; the step responses of T1 with the 63 % marks; the surface against column plot of C3. Every figure is looked at before it is committed, and quotes only numbers the tables hold.
* The validation sections 56 and 57, the tooltip numbers of the FEM hints (`DESIGN.md` 6) and the 'which model to trust' table take their numbers from these tables only.
* Any unexplained difference becomes a `fix/` proposal with its measured impact; the campaign never edits the program.

## 5. Order

C1 and C6 first (they decide whether the FEM port is sound), then C3 to C5, C7 and C8, then T1 to T3 after branch 8. The reviewer reads the tables before the sections are written.
