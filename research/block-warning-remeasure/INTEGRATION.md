# Integration: wording of the metal-block warning, and the Lumped part rows (proposals; nothing changed in the program)

Measured (README 3, 4 and 7; cells 1, 0.5 and 0.25 mm; FVM as the reference, the 3D solid of the program agreeing with it within 0.5 %; synthetic 100 x 80 mm two-layer board,
1.5 mm aluminium plate, one to four pads, one board size), with every model's part read as its own peak:

* the Analytic reads the hottest point and every part within -1.3 to +0.1 % of the FVM (the old 74 one-pad cases: 1.1 % mean, 4.3 % at most);
* the Lumped reads the hottest point and the parts too cool: -0.8 to -1.2 % with one pad, -2.6 to -4.8 % with two or four pads on a block of 80 x 60 mm or more, -5.8 and -7.0 %
  with a block of 60 x 45 and 40 x 30 mm on the 100 x 80 mm board (the old one-pad cases: 1.9 % mean, 4.7 % at most); the sharing between pads is 0 to 3.6 points too even, less
  than the 5.1 to 5.2 points of the same board without a block, so it is not a block effect and is left out of the block warning.

The first pass's "a part on a block 8 to 17 % too cool, use the FVM for the temperature of a part" is withdrawn: it compared the Lumped footprint node with the FVM peak (README 7.2).

## 1. Proposed wording (recommendation of the review)

Numbers that are defended: ranges with the board class they come from, no single figure that only one board gave. One sentence per model; the model name chooses it.

* **Analytic** (`api.py:1053`, text for `analytic`): "the metal block is represented as a graph of tiles in the Green-function correction: within about 5 % of the FVM in the
  tests (one plate on one to four pads; docs/validation.md section 17); steady state only". The 5 % stays (it holds for 107 cases, the largest 4.3 %); the only change is
  that the tests are no longer one pad.
* **Lumped** (text for `lumped`): "the metal block is represented as one more layer of the ring network: on the cool side of the FVM, within about 5 % with one pad under the
  block and up to about 7 % with several pads or a block much smaller than the board (tests on 100 x 80 mm two-layer boards; docs/validation.md section 17); steady state only".
* Not proposed: a "use the FVM for the part" sentence (its premise was the mismatch) and a sentence on the sharing between pads (not a block effect).

## 2. Exact edits for a `fix/block-warning-wording` branch (text only, no number moves)

| File | Place | Change |
| :-- | :-- | :-- |
| `pcbthermal/api.py` | lines 1051 to 1054, the loop over `(("lumped", how), ("analytic", how))` and the f-string | a third field per model with the accuracy clause: Lumped "on the cool side of the FVM, within about 5 % with one pad under the block and up to about 7 % with several pads or a block much smaller than the board (tests on 100 x 80 mm two-layer boards; docs/validation.md section 17)"; Analytic "within about 5 % of the FVM in the tests (one plate on one to four pads; docs/validation.md section 17)"; "; steady state only" kept for both |
| `pcbthermal/gui/panels.py` | line 917, the QLabel `only` | "The FVM, FDM and 3D solid model the block fully. The Lumped and Analytic models have it in steady state only (Analytic within about 5 % of the FVM; Lumped up to about 7 % too cool with several pads or a small block); their time simulation does not." |
| `pcbthermal/gui/panels.py` | line 920, its tooltip | "Lumped: one more ring-network layer, within about 5 % of the FVM with one pad, up to about 7 % too cool with several pads or a block much smaller than the board. Analytic: a tile graph, within about 5 %. No time simulation." |
| `pcbthermal/lumped.py` | line 941, docstring of `solve_steady` | "within 2 % on average and 5 % at most" -> "within about 5 % with one pad and up to about 7 % (cool side) with several pads or a block much smaller than the board" |
| `pcbthermal/analytic.py` | line 635, docstring | add "(one to four pads)"; numbers unchanged |
| `pcbthermal/help/index.html` | line 216, the item "The metal block in every model" | replace "(both within about 5 % of the FVM in 74 test cases, ..." by "(the Analytic within about 5 % of the FVM; the Lumped within about 5 % with one pad under the block and up to about 7 % too cool with several pads or a block much smaller than the board; steady state only: ..." |
| `docs/models.md` | line 125, the table header "(74 cases)" | "(74 one-pad cases and 29 with several pads, section 17)"; add a Lumped cell "up to 7.0 % (several pads, small block)" |
| `docs/models.md` | line 132 | the two sentences of section 1 instead of "both within about 5 % of the FVM in 74 cases" |
| `docs/validation.md` | section 17 | say that the 74 cases had one pad and one 10 mm heater; add the table of README 3 (own-peak columns, the controls without a block) and the 3D solid row of README 7.3; one line that the part is read with each model's own peak |
| `tests/test_block_models.py` | after line 46 (`test_simulate_runs_every_model_with_a_block_and_says_how`) | assert that the Lumped warning contains "several pads" and "7 %" and the Analytic warning "5 %"; no test holds the old 5 % text, so nothing else breaks |
| `tests/test_help.py` | word list | add "several pads" if the maintainer wants the help sentence held |

## 3. A separate program finding: the part rows of a Lumped-only run (proposal, `fix/` branch, moves numbers of Lumped-only runs)

`SimulationResult.heater_rows` reads the reference result through `analysis.heater_stats`, which takes the hottest FIELD value under the footprint. The Lumped field paints
the footprint with its ring-0 node, so when the Lumped is the only model run the part temperature, the junction temperature (`+ P theta`), the margin and the power limit
are read without the peak term: 101.9 against 114.3 K of rise on the one-pad block board at 0.5 mm, 128.8 against 141.7 K without the block, about 11 % of the rise on the
unsafe side (README 7.2). With the FVM in the run the rows read the FVM and are right.

* Fix: `lumped.solve_steady` stores the own peak of every heater (it computes it already in the loop that gives `t_max`) in `result.arrays["heater_peak"]`, and
  `analysis.heater_stats` takes it for `t_max` (and through it `t_junction`, `margin_k`, `p_limit_w`) when present; the zoned footprint (`_ZonePeak`) gives its own peak the same way.
* Impact: Lumped-only part rows, the Power Calculator when it is asked for the Lumped (`inverse.py` reads `heater_stats` too) and the top-path split of a part in a
  Lumped run (`api._top_path_split` evaluates the part through `heater_stats`, so the heat sent to the top path is computed from the node; not measured here); the frozen numbers record `Tj` of the Lumped
  (`releases/regression-harness`, for example `reference_board|lumped`) and move; studies that read Lumped parts through `heater_stats` (other research folders) should be
  checked for the same mismatch.
* Decision for the maintainer: adopt (recommended by the review: the rows are on the unsafe side) or state it as a limit in the help.

## 4. Risks

One board family (100 x 80 mm, two layers, 1.5 mm aluminium, no vias, no fins); the references are models of the program that share the block's boundary conditions (README 5 and 7.3).
