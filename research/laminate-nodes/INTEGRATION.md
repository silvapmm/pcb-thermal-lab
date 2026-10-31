# Integration: one construction of the laminate nodes (S5), draft for the fix of 2.4.5

**Status: measured (README section 3), waits for the reviewer.** The sections are in the order the maintainer needs them: what changes, what moves, what is warned, what is left as a limit, what is decided. `pcbthermal/` is untouched; the construction lives on copies in `lib/`.

## 1. The proposal in one paragraph

One construction (README 1.2) replaces the four treatments: every gap, and the laminate under the copper of a one-layer board, is cut into `n = min(n_max, ceil(d / s_max))` sub-gaps with a node at every boundary **in the cells where copper is partly absent next to the gap plus a margin**, and is the program's single link elsewhere; the vertical path of a cell with absent copper gets the laminate of half the copper layer on each side; the reported peak of a part over absent copper adds the half-layer drop to the face. Measured defaults: `s_max` 0.4 mm, `n_max` 4 (so 1, 2, 4, 4 sub-gaps for gaps of 0.4, 0.8, 1.6, 3.2 mm), equal sub-gaps, margin `ceil(d/dx) + 1` cells, mask "bare", vertical correction on, barrels in the sub-links; the face exponent is the open point (README 3.3, 3.4, 3.6).

## 2. What changes in the program (functions and files)

| Where | Change | Test it needs |
| :-- | :-- | :-- |
| `pcbthermal/laminate.py` | becomes the module of the construction: `nodes(board)` (one-layer only today) generalises to `ladder(board, fill, rule)` returning, per gap, `n`, the sub-gaps, the flagged cells and the share of laminate that moves from the copper nodes; `extra_layers` builds the arrays of the new node layers for any gap (today only the one-layer chain); `series_bottom_problem` (Analytic) stays | empty mask = the program bit for bit (`tests/test_laminate_nodes.py`); one-layer ladder equals the old two nodes at n = 2 in every cell |
| `pcbthermal/fvm.py` `Network.__init__` | after the board layers: for each gap append the interior node layers (S, C, links, pins for the cells that do not use them); `gz` is zeroed in the flagged cells and carries the vertical correction elsewhere; the copper nodes lose the moved laminate (S, C, `g_side`); the bottom node of a one-layer board is created for every cell (`laminate_layers` keeps its meaning for the computed-h loop) | the lib tests (`test_gapnet.py`) moved to `tests/` as the regression of the fix |
| `fvm.Network._assemble`, `solve_steady`, `transient_from_network` | unchanged (they already accept extra layers and `extra_links`); assemble without the pinned nodes (`solve_ragged`): the dense layers cost +25 % over the ragged matrix on the 2-layer board (README 3.11) | direct = ragged on the kept nodes |
| `fvm.Network.solve_sor` | the vertical neighbour is no longer layer ± 1: colour by physical depth `(z_index + i + j) % 2` (the lib uses the two-colouring of the graph) and general links; with the barrels in the sub-links the graph stays bipartite. It must be done together with the coloured block SOR of `sor-with-via-couplings` | SOR = direct on a ladder board. **Not ready for one-layer boards:** the general red-black colouring failed on the one-layer ladder (README 3.11); 2-layer ladders colour and need 990 against 720 sweeps |
| `pcbthermal/fdm.py` `Network` | the same arrays; the lateral link of two extra nodes is the mean when both are used and zero otherwise (the arithmetic mean would leak half a refined node into a pinned neighbour) | FDM empty mask = program; balance with refinement |
| `pcbthermal/lumped.py` | **keeps its network without the extra nodes** (README 3.12: on the refined network it moves the 2- and 3.2 mm windows from -15.9 and -34.6 % to +5.4 and -3.3 %, but the 4- and 6-layer windows from +6.9 and +1.9 % to +8.9 and +4.1 %) | measured, README 3.12 |
| `pcbthermal/analytic.py` | none: the Analytic has no cells and takes the **passive cell** of the rule everywhere (one link; the series film on a one-layer board, as today). The rule makes that coherent instead of an exception. The partial-copper candidate of `analytic-partial-copper` is not adopted (its own review) | unchanged results on uniform boards (README 3.12: within 0.3 to 0.8 % of the reference, 0.3 to 0.6 point below the FVM) |
| `pcbthermal/api.py` `SolverOptions`, Preferences (`defaults.json` section) | `laminate_s_max`, `laminate_n_max`, `laminate_margin`; a switch "laminate nodes" (on by default) so that a user can return to one node | tooltips, user guide, `tests/test_tooltips.py`, `tests/test_help.py` |
| `fvm.unknowns`, `fdm.unknowns`, the memory guard | count the nodes: ragged count for the estimate, dense for the allocation if the dense layers are kept; the guard of 2.5.0 (70 % of the memory, adjustable) uses them | counts equal the built network |
| `results.py`, `plots.py`, `analysis.py` | keep only the `n_board` copper layers (they already slice `[:n_board]`); check the stack-up tab and the reports | GUI stress scenario with a window board |
| the reported peak (`results`, `analysis.heater_stats`) | adds the face term of the rule for a part on an outer layer whose cell has absent copper | `tests/test_layered.py`-style check against the resolved solution |
| `pcbthermal/solid3d.py` | reports the top-face temperature (add `q t_cu / (2 k_z)` for a source on bare laminate) so that the comparison model and the layered models report the same quantity (README 3.6 part D: the solid is within 2 % of the face value on 12 windows and within 0.3 % of the slab centre on 4 and 6 layers: optional, a refinement of at most 2 %) | solid3d = reference face within 2 % on the windows |
| `pcbthermal/checks.py` | the warnings of section 5 | one test per warning |

## 3. Impact on the numbers

`study_validation_rows.py`, 1 mm cell (README 3.14), FVM peak in degrees C, program against rule:

| row | program | rule | change K | 3D solid |
| :-- | --: | --: | --: | --: |
| the reference board and every variant of it (corner, 5 mm heater, 8 layers, two heaters, thin heater) | | identical | 0.00 | |
| example board / without heatsink / without vias / only U1 | 85.81 / 88.91 / 94.67 / 79.97 | 85.82 / 88.92 / 94.68 / 79.97 | +0.01 | 85.98 for the first |
| example with top copper over the full board, uniform | 85.29, 96.68 | identical | 0.00 | 85.42, 96.88 |
| heater 5 mm inside the copper edge | 94.45 | 94.48 | +0.03 | 94.78 |
| heater straddling the copper edge | 143.89 | 148.98 | +5.08 | 149.27 |
| no copper on the heater layer | 150.16 | 154.70 | +4.54 | 153.19 |
| copper island 30 x 30 mm | 92.38 | 92.44 | +0.05 | 92.78 |
| hatched copper, fill 0.5 | 105.78 | 107.34 | +1.56 | 106.23 |

Boards with copper in every cell are bit for bit the program (14 of 22 rows). On the simple boards (README 3.2) the error against the resolved reference falls on every board with a bare spot: 2L 1.6 mm window 6 from -18.4 to -3.1 %, 2L 3.2 mm window 6 from -34.2 to -9.1 %, 1L pad 10 from -4.1 to -1.8 %, 4L window 6 from -3.8 to -0.6 %. Two rows overshoot the 3D solid by about 1 % (no copper under the heater, hatching); the example board moves by 0.01 K. The unknowns: 1.0 x on uniform and multilayer-with-thin-gaps boards, 1.2 to 2.5 x on thick two-layer boards with a pad, 1.3 to 1.7 x on a one-layer pad, 0.7 to 1.0 x on a one-layer window, 1.16 x on the example board (ragged); dense 1.25 to 2.5 x. The FDM is not in the table (n/a).

## 4. What does not change

Boards with copper in every cell of every gap (planes, full pours); the 3D solid's solution (only the reported quantity); the Analytic's solution; the point via and metal blocks (outside the construction; blocks refused).

## 5. New warnings 

* A part whose hottest cell has copper fill below 0.5 on the layer it sits on: "the part sits on bare laminate; the layered models read lower than the 3D solid; the size is X". (P3 of bare-spot-under-source.)
* A window or a gap in the copper narrower than the gap thickness under a part: "narrower than the laminate it opens; the error is up to 9 to 10 % at a 1.6 mm laminate and no number of nodes repairs it" (README 3.7; trigger: window width under 1.5 gap thicknesses or under 2 cells).
* The cost cap: not needed on the real windows (the cap at 2 x never acted, README 3.8: 1.5 to 1.7 x with 87 to 100 % of the cells flagged); no warning proposed.
* Copper finer than the cell on a one-layer board: "the copper has features finer than the cell; the nodes cannot represent them; the result is up to X % cool" (README 3.8: -12 to -43 % at 0.4 to 0.8 mm cells on real windows). The size of X and the trigger (a measure of the spread of the fill inside a cell) are **not measured**; to be designed before the warning is written.

## 6. Risks

* Real layouts flag 87 to 100 % of the cells (1.5 to 1.7 x the unknowns): on a real board the mask is nearly "all"; the memory guard must count them.
* The one-layer ladder is not bipartite (README 3.11): the coloured SOR is unavailable on one-layer boards until this is understood; the program's point SOR is unaffected.
* The transient: the time constant improves (2 to 4 % against 8 to 15 %) but the earliest points of a one-layer board are +58 % against +36 % in the program (README 3.10).
* On real one-layer layouts at the cells a user would choose (0.8 mm) the rule leaves -17 to -43 % (the program -27 to -62 %): the gain is real and the remainder is the scalar fill; and the program's own numbers here do not match the earlier folder's (README 3.8, unreconciled).
* The Analytic is 10 to 68 % cool on any partial copper and is not helped (README 3.12); the Lumped is erratic on the refined network.
* Metal blocks are refused; a board with a block keeps today's treatment.
* The reference is 0.4 to 1.5 % above its Richardson limit.

## 7. Decisions left to the maintainer

1. The law: (0.4 mm, 4) the proposed default (mean error 1.87 %, 1.31 x unknowns) against (0.2 mm, 8) (0.85 %, 1.83 x) or (0.2 mm, 6) (1.08 %, 1.63 x) (README 3.3); a one-layer 1.6 mm laminate reaches -1.8 % at n = 4 and -0.5 % at n = 8 (pad 10).
2. The face exponent: p = 0 (full term on every cell with fill under 1) is closest on every board printed, the code defaults to p = 1; overshoot near fill 1 not measured (README 3.6).
3. `rebuild_slabs` for the simple stack-up of 3+ layers (worth 1.9 and 0.7 points on 4 and 6 layers, README 3.13 B).
4. Ragged assembly (recommended, README 3.11) or dense layers.
5. The Analytic and the Lumped keep their own construction and are warned (recommended, README 3.12).
6. Whether the `solid3d` reports the face (at most 2 %, optional, README 3.6 D).
7. Whether one-layer boards enter 2.4.5 before the SOR colouring defect is understood: the direct solver does not need it.

## 8. Order of work

1. Tests of `lib/` (18 passed) and steps 0 to 14 (done).
2. The reviewer, with the claims, the scripts that support each and the numbers.
3. `fix/laminate-nodes` off `develop` (2.4.5): `laminate.py`, `fvm.py`, `fdm.py`, `api.py`, the counts, the SOR, the checks, the documents, the whole battery.
