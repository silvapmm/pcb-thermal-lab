# Review of `fix/enter-focus-and-calculator-test` (2.8.0, wave 1)

Branch `fix/enter-focus-and-calculator-test` (from `development` 9874eae3, executor commits a443c825 and c84ed690), with `development` merged in by the review. **Verdict: GO**, with the corrections listed below, on the condition that the maintainer knows that his original report was not reproduced.

## 1. The Enter-focus fix

**Change.** `Canvas.rebuild` (`pcbthermal/gui/canvas.py`) emits `selection_changed` only when the rebuild changed the set of selected elements.

**The original report was not reproduced.** Through the real `MainWindow` offscreen, on `development` without the fix, the review tried: the Layer box, the keys L, Shift+L and the digits, the element tree (which switches the layer), a clicked warning, the Results tab shown before and after, the Temperature context, and a spin box, a line edit and a second edit after the first. Enter kept the focus in the field in every case. The only state that lost the form was one in which Properties shows an element that is not drawn on the active layer. The executor reached it only by code. In the program it is reached by picking two heaters on two layers in the element tree: the form is then "2 elements selected", and before the fix any edit made elsewhere cut the form and the list down to the heater drawn on the canvas. **So the fix covers a neighbouring path, not necessarily the reported one.** If the maintainer still sees it on macOS, the exact steps are needed (an offscreen platform does not activate windows the way macOS does).

**Consumers checked.** Only `MainWindow._on_canvas_selection` listens to `Canvas.selection_changed`, and it updates the element list and the Properties panel. The Properties panel (`Inspector`) and the element list (`ElementList`) each connect to `Document.changed` themselves, so their refresh after undo, redo, a value written elsewhere (Power Calculator Use, the Power profile page), a re-import or a layer-count change never depended on the canvas signal. A changed selection is still reported (a layer change that leaves the selected element on another layer, a delete). Index-based staleness after a delete or an undo is unchanged; it already existed for elements on the active layer.

**Found by the review, fixed.** Duplicate (Ctrl+D) selected the copies on the board through `set_selection`, which emits nothing, so Properties and the list kept the originals: the next value typed changed the original, not the highlighted copy. This happened before and after the fix. Now `MainWindow._duplicate` updates both panels.

**Tests** (`tests/test_enter_focus.py`, 11 tests; against the `development` code, 5 of them fail):

| Test | On `development` |
| :-- | :-- |
| Enter after a layer change by the combo, the digit key or the step key (executor, 3) | passes: these tests do not guard the fix |
| element on another layer keeps its form and focus (executor) | fails |
| undo and redo refresh the form, on the active layer and on another layer (review) | the other-layer case fails |
| a value set elsewhere refreshes the form, on both layers (review) | the other-layer case fails |
| a selection that is no longer drawn is still cleared, by a layer change or a delete (review) | passes (guards the remaining emission) |
| a selection on two layers survives an edit made elsewhere (review) | fails |
| Duplicate selects the copy in Properties and in the list (review) | fails |

## 2. The JEDEC numbers

Measured on this branch: the program of 2.7.0 with the 2.8.0 wave-1 commits, none of which changes a model. Computed h, run one job at a time with a 25 min and 4 GB guard.

| Run | JEDEC 2s2p with 9 vias | Without vias | CSD17308Q3 |
| :-- | :-- | :-- | :-- |
| `calculator_validation.py` (0.5 mm, 157 s, 1.24 GB) | 31.6 K/W, 1.029 W, +2.9 % (top point the same) | 74.6 K/W, 0.44 W | 46.7 K/W, 0.986 W, -1.4 %; maximum 45.6 K/W |
| `study_cell_size.py --case jedec --cell 1.0` (8 s, 0.29 GB) | 32.23 K/W, +0.8 % | - | - |
| the same at 0.5 mm (56 s, 1.23 GB) | 31.59 K/W, +2.9 % | - | - |
| the same at 0.25 mm | **not run**: 5.13 GB resident after 12 s, stopped by the 4 GB guard | - | - |

**Where 31.4 K/W and +3.4 % come from.** They are the 2.6.0 program, measured by the 2.7.0 research audit (`research/power-calculator/README.md`). `docs/calculators.md` 2.1 took them, and the 2.7.0 documentation review (`releases/2.7.0/doc-review/README.md`, rows 3 and 9) copied them into the help and called 2.1 current without re-running it on the final 2.7.0 tree.

**Why the numbers moved.** On 2.7.0 the JEDEC row moves to 31.6 K/W and the board without vias to 74.6 K/W, while the two-layer CSD17308Q3 board does not move. The 2.7.0 items that touch a four-layer simple stack-up are the physical slabs of the simple stack-up (`docs/validation.md` 43). The FDM changes do not apply (the calculator runs the FVM), and neither do the edge-film changes (no outline). The move is attributed to the slabs, but the items were not separated one by one.

**Corrected by the review:**
* the JEDEC rows and the no-via row of `docs/calculators.md` 2.1, with the cell and the cell sweep;
* `pcbthermal/help/calculator.html`, which now gives the cell. The help also said that the Gerber import "is not in the interface yet", which has been stale since 2.5.0, and now names File - Import Gerber board;
* the docstring of `tests/test_calculator_dialog.py`;
* a stale comment in `tests/test_calculator_validation.py`;
* a dated line in `research/power-calculator/README.md` (the table of that README was left as the record).

**Not checked.** `docs/validation.md` 29 quotes 31.9 K/W at 1 mm for the heater on the exposed pad of the same JEDEC case (before 2.7.0). The calculator board gives 32.2 K/W at 1 mm now, but that section comes from another script (the heater-shape study), so the review did not change it. It is probably stale by the same slab change, and it should be re-run at the next reproduction pass.

## 3. `tests/test_calculator_dialog.py`

As written by the executor the file had 6 tests and took 158 s. Three of them repeated `tests/test_calculator_window.py` (the greyed fields, the case selector with its undo step, the Help page), and the top-point JEDEC run (56 s) repeated the same number already held through the API by `tests/test_calculator_validation.py`. Those four were removed. The file now has 3 tests, about 60 s:
* the CSD17308Q3 numbers through the dialog;
* the JEDEC numbers through the dialog;
* the dialog closed while its job runs (new, no other test covers it).

The tolerances (±0.15 and ±0.2 K/W, ±0.3 and ±0.4 points) are wide enough for platform noise. They tie the test to `docs/calculators.md` 2.1 on purpose: a model change that moves these rows must update the document too.

## 4. Documents

CHANGELOG `[Unreleased]` was merged with the sections already on `development` (Fixed, Added, Changed, then Tests). The Fixed entry now says that the report was not reproduced, and the Duplicate fix and the JEDEC correction are added. `docs/versions.md` item 20 says the same.

## 5. Quick tests run

See the report of the review: docs, licence header, version, help, tooltips, shortcuts, the two new files, `test_calculator_window.py`, `test_gui_stress.py` once, `tests/regression` at 2 mm.
