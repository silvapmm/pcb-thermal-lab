# `feature/compare-differences`: the Difference view (design note, stage 1)

Item `compare-differences` of `releases/2.9.0/PLAN.md` (2.2, 2.3, 3) and decision 5 of the PLAN: a difference between models must not be a difference of definition. Display only; no solver is run, no number of any model moves.

## 1. Where the control goes
In the **Temperature** page, in the row of the Model box: `Model [LPTN]  [x] Difference to [FVM]`. A checkbox and a combo, both reachable by Tab and the arrow keys, with an accessible name and a tooltip. Not in the Display popover: the popover holds the map style shared by Temperature, Gradients, Animation and the board (`DisplayState`); a difference is a choice of data of one page, like the Model box, so it sits beside it. While the view is on, Hotspot contour, Auto range and the two limits (temperatures in degC) are hidden, because the scale of a difference is symmetric and set by the data.
Below the row: a note of two lines (the first two lines of the text; the tooltip has all of it; a `More` button shows all). It holds the peak difference, the interpolation note when one applies, and the documented expected agreement (section 5).

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
