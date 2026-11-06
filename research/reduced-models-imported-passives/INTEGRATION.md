# Integration: what to do with the reduced models on imported copper

Recommendation first, evidence in `README.md`. Nothing here is implemented; the program is untouched.

## 1. Recommendation

1. **Keep the Lumped and Analytic models available on imported boards, and change the warning so that it says the cause and quotes the measured ranges** (text only, no number moves, frozen numbers unchanged). Do not refuse: the best cases (a large part in plain copper) are 17 to 35 % cool, a usable screening number, and a refusal would take the quick board-level view away for no measured gain in safety, since the warning already tells the user that the finite-volume model is the result.
2. **Do not add a warning threshold on the local copper fill, the distance to a copper edge or a "part on bare laminate" test as a predictor of the error.** Measured on 42 parts of three boards (README 3.3), none of them separates the good from the bad cases: the fill variables and the distance to bare laminate have an AUC of 0.65 to 0.78 for "more than 50 % too cold" and a Spearman correlation of 0.07 to 0.31 with the error. The best variable, the size of the part (AUC 0.87), is not a rule either: the size classes overlap (Lumped -81 to -52 % below 1.5 mm, -82 to -25 % from 1.5 to 3 mm, -56 to -25 % above 3 mm), and big parts of CO60 are 50 to 56 % cool. Every one of the 42 parts is at least 17 % cool.
3. **Replace the sentence "these models do not read the imported copper" of `copper.REDUCED_MODEL_WARNING`** (`docs/validation.md` 27.7 and the user guide quote it) by the cause and the ranges, see `docs/warning-text.md` for the proposed wording. The present text quotes the 1 to 16 % of the 24 mm windows, which the whole boards contradict.
4. **Model change: not recommended as it stands.** A pad-scale correction of the Lumped and Analytic rise, computed from the top-layer mask around the part (a pixel resistor network in a 16 mm window with a leaking fin, 0.1 s per part), cut the mean absolute error from 41 to 60 % to 12 to 22 % on RP2040 and oswlight (fin length 0.5 to 0.75 mm, chosen by a sweep on RP2040 and carried to oswlight), and left it at 57 to 62 % on CO60, where the pads are tied through the second layer (README 3.4). It has one empirical parameter, ignores the second layer and the vias, and would move the Lumped and Analytic numbers of imported boards. The open question for `research/ROADMAP.md`: a correction that reads the whole stack (both layers and the vias) around the part, or the Lumped model fed with the pixel network in a window around each part; and the cause of the Lumped's own 2 to 30 % deficit on a uniform sheet (README 3.1 point 3).

## 2. What does not change

* Frozen numbers (`tests/regression`): no change. Drawn boards do not go through any of the new code; imported boards are not in the frozen set.
* The FVM, FDM and 3D solid, the memory guard and the import window: no change.
* Nothing in `pcbthermal/`, `tests/`, `examples/`, `docs/` is touched by this branch.

## 3. Cost

* Warning text (item 3): one constant in `pcbthermal/copper.py`, the strings in `docs/validation.md` 27.7 and the user guide where the warning is quoted, `tests/test_imported_copper.py` for the new words. About an hour, no risk to numbers.
* Item 4 (if ever): a new function in `copper.py` or `lumped.py`, the window solve (sparse, 40 000 unknowns per part, a tenth of a second), tests against the closed forms of `lib/constriction.py` (strip, disc, fin), a re-freeze of nothing (imported boards are outside the frozen set) but a new validation table; several days with the reviewer.

## 4. Risks and what is not known

* The FVM reference itself is not converged for 1 mm parts at 0.25 mm (README 3.2): the errors in this folder are **lower bounds** of the error against a converged reference, and the sign of the missing part is "even cooler".
* Nothing was compared with a measurement of a physical board.
* The three boards are Gerber exports of hobby and small-product designs (two layers, one four-layer); a board with solid planes under every small part was not tried and could be nearer the "large part in plain copper" rows (17 to 35 % cool); that is a guess, not a finding.
