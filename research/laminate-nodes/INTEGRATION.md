# Integration: one construction of the laminate nodes (S5), draft for the fix of 2.4.5

**Status: structure and hypotheses only.** Nothing has been run (README, status). Every statement marked *(to measure)* is filled from the printed output of the named script; the sections are in the order the maintainer needs them: what changes, what moves, what is warned, what is left as a limit. `pcbthermal/` is untouched; the construction lives on copies in `lib/`.

## 1. The proposal in one paragraph

One construction (README 1.2) replaces the four treatments: every gap, and the laminate under the copper of a one-layer board, is cut into `n = min(n_max, ceil(d / s_max))` sub-gaps with a node at every boundary **in the cells where copper is partly absent next to the gap plus a margin**, and is the program's single link elsewhere; the vertical path of a cell with absent copper gets the laminate of half the copper layer on each side; the reported peak of a part over absent copper adds the half-layer drop to the face. Defaults to be fixed by the runs: `s_max`, `n_max`, grading, margin, face exponent *(to measure: steps 3, 4, 6)*.

## 2. What changes in the program (functions and files)

| Where | Change | Test it needs |
| :-- | :-- | :-- |
| `pcbthermal/laminate.py` | becomes the module of the construction: `nodes(board)` (one-layer only today) generalises to `ladder(board, fill, rule)` returning, per gap, `n`, the sub-gaps, the flagged cells and the share of laminate that moves from the copper nodes; `extra_layers` builds the arrays of the new node layers for any gap (today only the one-layer chain); `series_bottom_problem` (Analytic) stays | empty mask = the program bit for bit (`tests/test_laminate_nodes.py`); one-layer ladder equals the old two nodes at n = 2 in every cell |
| `pcbthermal/fvm.py` `Network.__init__` | after the board layers: for each gap append the interior node layers (S, C, links, pins for the cells that do not use them); `gz` is zeroed in the flagged cells and carries the vertical correction elsewhere; the copper nodes lose the moved laminate (S, C, `g_side`); the bottom node of a one-layer board is created for every cell (`laminate_layers` keeps its meaning for the computed-h loop) | the lib tests (`test_gapnet.py`) moved to `tests/` as the regression of the fix |
| `fvm.Network._assemble`, `solve_steady`, `transient_from_network` | unchanged (they already accept extra layers and `extra_links`); optional: assemble without the pinned nodes (`solve_ragged`) if step 11 says the dense layers cost more than 15 % *(to measure)* | direct = ragged on the kept nodes |
| `fvm.Network.solve_sor` | the vertical neighbour is no longer layer ± 1: colour by physical depth `(z_index + i + j) % 2` (the lib uses the two-colouring of the graph) and general links; with the barrels in the sub-links the graph stays bipartite. It must be done together with the coloured block SOR of `sor-with-via-couplings` | SOR = direct on a ladder board; sweeps counted *(to measure, step 11)* |
| `pcbthermal/fdm.py` `Network` | the same arrays; the lateral link of two extra nodes is the mean when both are used and zero otherwise (the arithmetic mean would leak half a refined node into a pinned neighbour) | FDM empty mask = program; balance with refinement |
| `pcbthermal/lumped.py` | none if step 12 shows the ring sums of the extra layers are acceptable (it already aggregates `net.extra_links`); otherwise it keeps its network without extra nodes | measured, README 3.12 |
| `pcbthermal/analytic.py` | none: the Analytic has no cells and takes the **passive cell** of the rule everywhere (one link; the series film on a one-layer board, as today). The rule makes that coherent instead of an exception. The partial-copper candidate of `analytic-partial-copper` is not adopted (its own review) | unchanged results on uniform boards *(to measure, step 12)* |
| `pcbthermal/api.py` `SolverOptions`, Preferences (`defaults.json` section) | `laminate_s_max`, `laminate_n_max`, `laminate_margin`; a switch "laminate nodes" (on by default) so that a user can return to one node | tooltips, user guide, `tests/test_tooltips.py`, `tests/test_help.py` |
| `fvm.unknowns`, `fdm.unknowns`, the memory guard | count the nodes: ragged count for the estimate, dense for the allocation if the dense layers are kept; the guard of 2.5.0 (70 % of the memory, adjustable) uses them | counts equal the built network |
| `results.py`, `plots.py`, `analysis.py` | keep only the `n_board` copper layers (they already slice `[:n_board]`); check the stack-up tab and the reports | GUI stress scenario with a window board |
| the reported peak (`results`, `analysis.heater_stats`) | adds the face term of the rule for a part on an outer layer whose cell has absent copper | `tests/test_layered.py`-style check against the resolved solution |
| `pcbthermal/solid3d.py` | reports the top-face temperature (add `q t_cu / (2 k_z)` for a source on bare laminate) so that the comparison model and the layered models report the same quantity *(to measure, step 6, part D)* | solid3d = reference face within 2 % on the windows |
| `pcbthermal/checks.py` | the warnings of section 5 | one test per warning |

## 3. Impact on the numbers

*(to measure: `study_validation_rows.py`, `study_windows_real.py`, steps 2, 8, 14.)* The table will list for each row of `docs/validation.md` the old value, the new value, the change in K and percent, and the model; rows with copper in every cell are expected unchanged to the last bit (the refined set is empty), and the example boards to under 0.1 K.

## 4. What does not change

Boards with copper in every cell of every gap (planes, full pours); the 3D solid's solution (only the reported quantity); the Analytic's solution; the point via and metal blocks (outside the construction; blocks refused).

## 5. New warnings *(to be decided with the numbers)*

* A part whose hottest cell has copper fill below 0.5 on the layer it sits on: "the part sits on bare laminate; the layered models read lower than the 3D solid; the size is X". (P3 of bare-spot-under-source.)
* A window or a gap in the copper narrower than the gap thickness under a part: "narrower than the laminate it opens; the error is up to Y % (documented limit)" *(Y from step 7)*.
* The cost cap: "the laminate nodes were limited to n = K to keep the unknowns within Z times" when the budget lowers n *(only if step 8 shows it is needed on real layouts)*.

## 6. Risks

*(to complete after the runs.)* Known before: real layouts flag most cells; the simple stack-up with 3+ layers allocates the laminate unequally; the point via and the barrel in the sub-links; the reference is itself 0.3 to 2.2 % above its limit on a window board; the Lumped is erratic over windows.

## 7. Order of work

1. Run the tests of `lib/`; fix what they find, with a regression test each.
2. Steps 1 to 14 of the README; fill README section 3 and this file.
3. The reviewer, with the claims, the scripts that support each and the numbers.
4. `fix/laminate-nodes` off `develop` (2.4.5): `laminate.py`, `fvm.py`, `fdm.py`, `api.py`, the counts, the SOR, the checks, the documents, the whole battery.
