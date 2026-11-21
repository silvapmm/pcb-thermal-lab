# `feature/compare-differences`: the Difference view (design note, stage 1)

Item `compare-differences` of `releases/2.9.0/PLAN.md` (2.2, 2.3, 3) and decision 5 of the PLAN: a difference between models must not be a difference of definition. Display only; no solver is run, no number of any model moves.

## 1. Where the control goes
In the **Temperature** page, in the row of the Model box: `Model [LPTN]  [x] Difference to [FVM]`. A checkbox and a combo, both reachable by Tab and the arrow keys, with an accessible name and a tooltip. Not in the Display popover: the popover holds the map style shared by Temperature, Gradients, Animation and the board (`DisplayState`); a difference is a choice of data of one page, like the Model box, so it sits beside it. While the view is on, Hotspot contour, Auto range and the two limits (temperatures in degC) are hidden, because the scale of a difference is symmetric and set by the data.
Below the row: ~~a note of two lines~~ replaced by section 8 (no permanent note; one conditional caveat line).

## 2. Data flow (`pcbthermal/compare.py`, no GUI imports)
`PlotTab.redraw` -> `_difference()` -> `compare.difference_field(model_result, reference_result, problem, readout, layer, face)` -> `plots.draw_difference(fig, diff, problem)`.
* **Read-out**: the toolbar Layer box decides: a copper layer gives the **column mean** of that layer for both models; `Surface (top/bottom)` gives the **surface** of both (FVM, FDM, FEM hold it). All layers and All (2 x 2) show layer 1 (the note says so); a metal block has no difference (the note says so, the temperature map is drawn).
* **Refusals** (`unavailable_reason`, the reason is the tooltip of the greyed-out item and the note): the same model; a model without a field; a model without the surface read-out (the LPTN, Analytic, 3D solid); the LPTN or Analytic on an outline board (they solve a rectangle of the same area, the field is stretched: its points are not points of the board). `subtract` raises `DifferenceError` for two different read-outs, so a definition can never be mixed whatever the caller does.
* **Single model run**: the checkbox is disabled, its tooltip says to run two or more models.
* **Default reference** (`default_reference`): the FVM, else the first other model with a field. If the model shown becomes the reference, the reference moves to that default.

## 3. Interpolation rule
The result has the grid of the **reference**. If the two fields have the same shape and positions to a millionth of a cell, they are subtracted directly (exact). Otherwise the model field is resampled by **bilinear interpolation between its sample positions** (cell centres for a cell field, grid points for the FDM node field), linearly extended into the half cell between the outer samples and the board edge, so a linear field is reproduced exactly everywhere (a test). The note says: `<model> was interpolated onto the <reference> grid`. NaN off an outline spreads to the neighbouring samples.

## 4. Colour scale and figure
`RdBu_r`, limits plus and minus the largest absolute difference (white is zero, red the model above the reference, blue below); the red ring marks the largest difference, the blue ring the smallest. Title in three lines: `<model> - <reference>, <read-out>` (K), `max ... K at (x, y) mm`, `min ... K at (x, y) mm   RMS ... K`. Colour-bar label `<model> - <reference> (K)`. The toolbar's copy and save act on this figure. Theme-safe: figure colours come from the theme as for every map; the diverging map is white-centred on both. The histogram was not made: the maximum, minimum, where, mean, RMS and the peak difference carry the numbers (the brief allowed either).

## 5. The confidence tips and their evidence
Section 8 moves these tips out of the view into the user guide and the manual; the table and its evidence below stay valid as the content of that chapter.

Only statements with a documented measurement; a pair without one says nothing. Every number is the hottest point of the 20 scenarios of `docs/validation.md` section 2 (share of the rise above ambient, the FVM as reference), and `tests/test_compare.py` recomputes each range from that table, so a number the table does not hold fails.

| Model against the FVM | Statement | Evidence |
| :-- | :-- | :-- |
| FDM | 0.5 % of the rise below or closer in 19 of 20 scenarios; outside: a copper edge across the heater -1.3 % | validation 2 |
| Analytic | -1.8 to +0.3 % in 18 of 20 (-1.1 % on the example board); outside: a copper island around the heater -5.1 %, a copper edge across the heater -27.9 % | validation 1 and 2 |
| LPTN | -5.4 to +8.4 % in 19 of 20 (+2.4 % on the example board); outside: a copper edge across the heater -27.9 % | validation 1 and 2 |
| 3D solid | -0.3 to +0.9 % in 20 of 20; a comparison model of the program, not an independent reference | validation 2 |
| FEM, and every pair whose reference is not the FVM | nothing | the 2.9.0 comparison campaign has not been run |

Every tip ends with: the ranges are for the **hottest point**, not for every point of the map. This matters: on the example board the LPTN's hottest point is +1.4 K from the FVM but its map reaches +8.7 K and -4.1 K around the heaters, and no document measures that, so the view says no more than the table does. **Not stated, because not documented**: that the LPTN reads a "node/ring value 1 to 2 K above under a part" or that the Analytic reads "-1 K on a rise of 85 K": the measured examples are in percent of the rise of the example board (rise 60.4 K: +2.4 % is +1.4 K, -1.1 % is -0.7 K), and a definition-difference claim needs the part-read-out study of validation 48, which the pair table above does not cite. The reviewer decides whether a sentence from 48 may be added.

## 6. Tests
Pure (`tests/test_compare.py`, 9 tests, passing): zero for an equal copy and refusal of the same result, antisymmetry, mean difference = difference of means, interpolation exactness on a linear field between a node grid and a cell grid, the interpolation note, read-out mixing refused (and a missing surface, a missing field), the surface difference, the default reference, the documented ranges against the validation table, silence without evidence.
Stage 2 (after approval): GUI tests (control present; disabled for one model; greyed items with reasons; the title names both models and the read-out; no sideways scroll at 1200 x 800; theme toggles; clear), a layout test that can fail (the note must not widen the page, the Hotspot and range controls are hidden), a stress scenario in `tests/test_gui_stress.py` (several models, pair changes, layer changes, an outline board, a clear). Documents per CLAUDE.md section 10.

## 7. Risks and what is not in stage 1
* The tips table is built from a table of the hottest point; it does not describe the map. Said in every tip.
* The map of the LPTN on a board with an outline is refused (stretched field); the FEM is not in the tips until the campaign.
* **Steady only**: the Animation and the transient frames have no Difference view in this version (the PLAN row of `fem-transient` expects it on frames; it is left for that branch). Said in the guide and the manual.
* At 900 x 700 with both docks open the centre area is about 230 px wide: the baseline Temperature page is just as cramped (it was before this branch); the Difference view hides three controls and needs two lines more for the note, so the map is a little smaller still. The Cut-slider-narrow item of the PLAN owns that width.
* The CSV export of the difference statistics and the CLI table are not in stage 1.

## 8. Decision on the note (reviewer, after the stage 1 screenshots)
**Decision: no permanent note.** Asked: is the two-line note under the row worth its place? Answer: no, for three reasons.
* **It repeats or misleads.** The peak difference is the difference of the hottest points, already in the Summary and Models tables. The expected-agreement tips are measured at the hottest point only, and the view shows a map: next to a map that reaches +8.7 K and -4.1 K (LPTN minus FVM on the example board) a sentence saying "-5.4 to +8.4 % in 19 of 20 scenarios" reads as a statement about the map, which no document measured. The disclaimer at the end of the tip is cut off by the two-line elision in every screenshot, so the user sees the claim and not its limit.
* **It costs space where there is none.** At 900 x 700 with the docks open the centre is about 230 px wide; the note shows about 60 characters of text that are not readable and need `More`; the figure title already wraps to five lines there.
* **It costs upkeep.** The tips table in the program must follow every change of `docs/validation.md`; that is document content and belongs in documents.

**What stays on screen** (only what is needed to read the map correctly):
1. The figure title, as it is (model minus reference, read-out, max/min with where, RMS).
2. **Interpolation**: when `DifferenceField.notes` holds the interpolation sentence, a short fourth title line `(<model> interpolated onto the <reference> grid)`. In the title, not a label, so a copied or saved figure keeps the caveat.
3. **One conditional caveat line** under the row, an `ElidedLabel` of ONE line (no `More` button; its tooltip holds the full text), **hidden when nothing applies**. It shows only: the refusal (`Difference not shown: <reason>. The temperature map is drawn.`) and the layer fallback of All layers / All (2 x 2) (`The Difference shows one layer at a time: layer N`). In the normal case (a copper layer, two models with fields) nothing is shown under the row.
4. The tooltip of the checkbox: the present text, ending with `How closely each pair of models agrees at the hottest point, with its evidence, is in the user guide (Help, Difference view).` instead of `read the note below the controls`. No numbers in the tooltip.

**Changes for stage 2** (small: about -60 lines in the program, +25 in the documents, one test moved):
* `pcbthermal/compare.py`: delete `Tip`, `EXPECTED` and `expected_agreement` (lines 248-291 at 9598777f) and the `Tuple` import if unused. `DifferenceField.notes`, `peak_k` and `peak_pct` stay (the notes feed the title; the peak fields are cheap and tested).
* `pcbthermal/plots.py`, `draw_difference`: append `"\n(" + note + ")"` to the title for each entry of `diff.notes` (shortened to `<model> interpolated onto the <reference> grid`).
* `pcbthermal/gui/results_view.py`: delete `diff_more` and `_toggle_more` (the `More`/`Less` handler); `diff_note` becomes `ElidedLabel("", max_lines=1)` with the full text as its tooltip; in `_difference` the `Hottest points differ by` line, `lines += d.notes` and `lines += compare.expected_agreement(...)` go; the row is shown only for the refusal and the layer fallback, hidden otherwise; the checkbox tooltip as in point 4.
* `tests/test_compare.py`: delete `test_a_pair_without_documented_evidence_says_nothing`; `test_every_documented_range_is_what_the_validation_table_prints` is kept but reads the ranges from the tips table of `docs/USER_MANUAL.md` (the chapter of the Difference view) instead of `compare.EXPECTED`, so the document cannot drift from `docs/validation.md` section 2. `test_another_cell_size_is_resampled_and_the_note_says_so` stays. Stage 2 GUI tests add: no note row in the normal case; the row visible with the reason when refused; the interpolation line in the figure title for FDM minus FVM; no `More` button.
* **Where the tips table lives**: in the documents, not the program. `docs/USER_MANUAL.md` (chapter of the Difference view) holds the table of section 5 with its evidence column and the sentence "the ranges are for the hottest point, not for every point of the map", with the LPTN example (+1.4 K at the hottest point, +8.7 / -4.1 K on the map); `pcbthermal/help/index.html` holds the same table (the guide is what `Help` opens). The test above guards the manual's numbers.
* This DESIGN: section 1 (the note) and section 5 are superseded by this section; section 6 follows the test list above; the last risk of section 7 (two lines of the note) no longer applies.
