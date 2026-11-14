# Integration: wording of the metal-block warning (proposal; nothing changed in the program)

Measured (README sections 3 and 4, cells 1, 0.5 and 0.25 mm, FVM as the reference, synthetic 100 x 80 mm two-layer board, 1.5 mm Al plate, 1 to 4 pads, one board size):
the Analytic reads the hottest point and every part within 2.4 % of the FVM; the Lumped reads the hottest point 1.0 to 7.0 % too cool (above 5 % with a small block or two pads) and the temperature of a part
8 to 17 % too cool (7 to 11 of those points are its small-part limit that exists without a block), and shares the heat between pads too evenly (8 to 12 points of the rise).

## Proposed wording (per model, one sentence each; the model name decides which one a run shows)

* Analytic (`api.py:1053` text for `analytic`): "the metal block is represented as a graph of tiles in the Green-function correction: within about 3 % of the FVM for the hottest point and for the parts in the tests of research/block-warning-remeasure (one to four pads, one board size); steady state only".
* Lumped (text for `lumped`): "the metal block is represented as one more layer of the ring network: the hottest point of the board is 1 to 7 % too cool against the FVM in the tests (more when the block is small against the board or when two pads share it), the temperature of a part on the block 8 to 17 % too cool and the heat is shared between pads too evenly; use the FVM, FDM or 3D solid for the temperature of a part on a block; steady state only".
* Keep the pointer "(docs/validation.md section 17)" and add "section 17.x" for the new table when adopted.

## Places to change (a `fix/` branch, text only, no number moves)

| File | Place | Change |
| :-- | :-- | :-- |
| `pcbthermal/api.py` | line 1053, the f-string with `how` | one text per model as above (the loop over `("lumped", ...), ("analytic", ...)` needs a second field) |
| `pcbthermal/gui/panels.py` | line 917, the QLabel `only` | "...in steady state only (Analytic within about 3 % of the FVM, Lumped less accurate for the temperature of a part: see the warning)" |
| `pcbthermal/help/index.html` | line 216, the "metal block in every model" item | replace "both within about 5 % of the FVM in 74 test cases" by the two sentences |
| `docs/models.md` | line 132 | same |
| `docs/validation.md` | section 17 | add the table of this folder (several pads, control without block) and say that the 74 cases had one pad |
| tests | `tests/test_block_models.py` lines 46, 58 assert only the words "ring network", "tiles", "local corrections"; no test holds the 5 % text; add one that the Lumped text contains "part" and the Analytic text "3 %"; `tests/test_help.py` word list unaffected unless a word is added |

Not for the wording: the Lumped part error without a block is a separate known limit (small parts at a 1 mm cell, `docs/validation.md` 31), not a block defect.
Risks: the numbers are one board family and the FVM as the only reference (README 5); the reviewer should re-run, add the independent 3D reference and confirm before the `fix/` branch.
