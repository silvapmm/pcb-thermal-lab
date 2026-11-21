# `feature/compare-differences`: the Difference view (design note, stage 1)

Item `compare-differences` of `releases/2.9.0/PLAN.md` (2.2, 2.3, 3) and decision 5 of the PLAN: a difference between models must not be a difference of definition. Display only; no solver is run, no number of any model moves.

## 1. Where the control goes
In the **Temperature** page, in the row of the Model box: `Model [LPTN]  [x] Difference to [FVM]`. A checkbox and a combo, both reachable by Tab and the arrow keys, with an accessible name and a tooltip. Not in the Display popover: the popover holds the map style shared by Temperature, Gradients, Animation and the board (`DisplayState`); a difference is a choice of data of one page, like the Model box, so it sits beside it. While the view is on, Hotspot contour, Auto range and the two limits (temperatures in degC) are hidden, because the scale of a difference is symmetric and set by the data.
Below the row: ~~a note of two lines~~ replaced by section 8 (one verdict-first line; caveats in the figure title).

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
Section 8 shortens how these tips are shown (one verdict line, the rest in its tooltip) and copies them into the user guide and the manual; the table and its evidence below stay valid.

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
**Decision: replace the two-line note by ONE line, verdict first; caveats go into the figure title.** (A first version of this section removed the note entirely; the prototype below showed that one line carries the one fact the tables do not: whether the gap is usual for that pair. Revised.)

**Why the stage 1 note goes.** Its first fact (the difference of the hottest points) is already in the Summary and Models tables; the tips are long, and the two-line elision cuts off their limit ("for the hottest point, not for every point of the map"), so beside a map reaching +8.7 / -4.1 K (LPTN minus FVM, example board) the user reads a range as if it were about the map. At 900 x 700 the note shows about 60 characters and needs `More`.

**What the one line gives that the tables do not**: a verdict against documented evidence, worded so that it names the hottest point. Texts (the numbers in braces are computed; the ranges are those of section 5, nothing else is claimed):
* LPTN - FVM, example board: `Usual for the LPTN: hottest point +1.4 K, +2.4 % of the rise (usual -5.4 to +8.4 %)`
* FDM - FVM: `Usual for the FDM: hottest point -0.1 K, -0.1 % of the rise (usual within 0.5 %)`
* Analytic - FVM: `Usual for the Analytic: hottest point -0.7 K, -1.1 % of the rise (usual -1.8 to +0.3 %)`
* FEM - FVM: since the campaign is merged, validation 56.1 holds the pair (FVM against the FEM, peak, 1 mm cell, 16 boards without the three drawn ones: the FVM is -0.3 to +2.7 % of the FEM rise from it). Row to add to section 5 when this branch merges development: `Usual for the FEM: hottest point {k} K, {pct} % of the rise (usual -2.7 to +0.3 %, validation 56.1)`, with the sign converted and its test reading the 56.1 table, or no row until then.
* Outside the range: the same line in the warning colour of the theme (`alert_note`), `Larger than usual for the LPTN: hottest point ... (usual ...)`. A pair without evidence: no line.
* The tooltip of the line holds: the range, the scenarios (19 of 20 ...), the outliers, the evidence (`docs/validation.md` section), and the sentence `Measured at the hottest point; the map can differ more around the parts.`

**Caveats move into the figure title** (so a copied or saved figure keeps them): the interpolation as a short last title line `(FDM was interpolated onto the FVM grid)`; the layer fallback of All layers / All (2 x 2) is already visible in the title (`layer 1, column mean`). A refusal (`Difference not shown: <reason>. The temperature map is drawn.`) uses the same one-line label, in the warning colour.

**The figure does not fit a narrow canvas (measured, must be fixed in stage 2).** A sweep of `draw_difference` (example board, LPTN - FVM, constrained layout, Agg, drawn at the size and also drawn at 1600 x 1000 then shrunk) keeps every text inside the canvas from 1400 down to 180 px wide (no layout warning above 180 px; below, the collapse warning as on every map). But from a canvas of 300 px and narrower (axes 160 px; the 900 x 700 window with both docks gives about 230 px) the title runs over the colour bar and its label: `ax.title.set_wrap(True)` wraps at the figure edge while the title is centred on the axes. Measured: canvas 400 px no overlap, 300, 230 and 180 px overlap. Re-layout on resize itself works (constrained layout runs at every draw), but the wrapping is fixed at the first draw. Fix for stage 2: put the title in `fig.suptitle` (centred on the figure, so it cannot run over the colour bar) at size 9, wrapped to the figure width; refit on resize the way the Profiles figure does (`plots.refit_texts`, called from `_on_canvas_resized`; that code is on `development`, not on this branch: merge `development` first and extend `_on_canvas_resized` to the Temperature page). The prototype screenshots used this and fit at 1200 x 800 and 900 x 700. Test for stage 2: the sweep above (widths 1400 to 230 px, drawn large then shrunk) asserting title, colour-bar label and tick labels inside the canvas and the title box not overlapping the colour-bar box.

**What the note costs**: the two-line note took about 40 px of the height. At 1200 x 800 (canvas height-limited) that cost the map 9 % of its width (axes 568 -> 518 px); at 900 x 700 (width-limited) it cost nothing (96 -> 97 px). One line halves that.

**Defect found while prototyping (stage 2 must fix it)**: the default reference is not the FVM when the shown model is changed before ticking the box. After a run of FVM, LPTN, Analytic and FDM, with the FVM shown: choose FDM (or Analytic) in the Model box, tick `Difference to`: the reference is the LPTN (the map is FDM - LPTN, -1.51 K at the hottest point), not the FVM. With the FVM first shown, the reference was moved off it to the first other model and is not moved back. Rule to implement: whenever the model shown changes, a reference that is not the user's own choice returns to `default_reference`; test: the sequence above gives the FVM.

**Changes for stage 2**:
* `pcbthermal/compare.py`: `Tip`/`EXPECTED` stay (the line uses them); `expected_agreement` returns `(verdict_line, tooltip_text, outside)` instead of two sentences; the FEM row per the bullet above.
* `pcbthermal/plots.py`, `draw_difference`: the title as a wrapped `suptitle` with the interpolation line; refit on resize.
* `pcbthermal/gui/results_view.py`: `diff_more` and its handler go; `diff_note` is an `ElidedLabel(max_lines=1)` with the tooltip, the warning colour when outside or refused, hidden for a pair without evidence; the `Hottest points differ by` sentence goes (it is in the verdict line); the reference default as above; the checkbox tooltip ends `The line below says whether the gap at the hottest point is usual for that pair (the user guide has the evidence).`
* `tests/test_compare.py`: the range test stays (against the validation tables, 56.1 too when the FEM row is added); add: the verdict for inside and outside a range; no line for a pair without evidence. GUI tests of stage 2: the line is one line, no `More`, the interpolation line in the title for FDM - FVM, the default reference after a model change, and the resize sweep.
* Documents: the tips table with its evidence also goes into `docs/USER_MANUAL.md` and `pcbthermal/help/index.html` (chapter of the Difference view); the program's table in `compare.py` is the one the test guards. Sections 1, 5 (layout of the text), 6 and the last risk of 7 are superseded by this section.

Prototype screenshots (throwaway copy, not committed): the stage 1 form, the form with no note, and this one-line form at 1200 x 800 and 900 x 700, light theme.

## 9. Stage 2 as implemented

Done on `feature/compare-differences` after merging `development` (fd4ece39): `compare.expected_agreement(model, reference, peak_k, peak_pct, cell_mm)` returns `Agreement(line, tooltip, outside)` or None; `Tip`/`EXPECTED` gained the FEM row (-2.7 to +0.3 %, 16 boards, validation 56.1, recomputed by the test from the peak table: `(FEM / FVM - 1)` over the boards without `drawn_*` and with a FEM value); `plots.draw_difference` puts the title in a figure title (size 9, 8 or 7 by canvas width, wrapped to the figure, the interpolation sentence as its last line) and `plots.refit_texts` fits it again, called from `PlotTab._on_canvas_resized`, now connected on the Temperature page too; the `More` button and its handler are gone; `diff_note` is a one-line `ElidedLabel` in the `alert_note` colour outside the range or on a refusal, with the tooltip set after the text; the reference follows the model shown unless the user chose it (`_ref_chosen`, set by a change of the box made outside `_updating`). Differences from the text of section 8: the outside verdict reads `Outside the usual range for the ...` (a gap of the opposite sign is not 'larger'), the FDM range is printed `-0.5 to +0.0 %` (the table has no positive FDM case, so 'within 0.5 %' would claim more), and the tooltip adds that the ranges were measured with 1 mm cells when the run's cell differs (the FDM against the FVM is -1.1 % of the rise at 2 mm on the example board, outside the 1 mm range). The CSV of the difference statistics was left to the CSV item that follows.
