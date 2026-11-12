# Review of the map markers, the cut overlay and the via span warning (2.6.1)

Merged into `develop` before review: `fix/results-map-markers-and-cut-locator` (1a77212d), `fix/hot-mark-position-and-span-warning` (c4e550ea), `fix/cut-overlay-from-display` (044a1d0e). Corrections on `fix/cut-overlay-review` (from `develop` abf85f58), three commits, each with a regression test that fails on `develop`.

## Verdict

**GO with the corrections of the review branch.** The rings, the cut line and its title are where the code says; the cut picture follows the Layer, the Display panel and the Map button, survives undo and redo, costs nothing measurable on a large imported board, and the command line and the saved PNG carry it. Three defects were found and fixed: a false blind-via warning on real boards, a map title that contradicted its own rings, and a corner rule that hid the curves of the example board.

## Findings, by severity

1. **Defect in the program, via span warning** (fixed, `copper.copper_numbering`, `copper.span_is_whole_board`): the span of a drill file was compared with `1..n`, the count of imported copper layers. CAD programs that number the copper otherwise make every through via a "blind, buried or micro" via: on two real Proteus sets of the local library, a two-layer board written as `Copper,L1` and `Copper,L16` with the drill span `1,16` reported 48 of 48 vias, a one-layer board with the span `0,1` 25 of 25. The span now counts as whole when it covers the first and last copper numbers the files give (`1..n` when the copper files carry no X2 number); one copper layer never warns. After the fix both sets give no line; the synthetic blind (1,2 of 4) and buried (2,3 of 4) cases still warn, and a span 1,8 on the L1/L16 board warns. Tests in `tests/test_via_span_warning.py`.
2. **Defect in the program, map title against the rings** (fixed, `results_view.PlotTab.redraw`, `plots.draw_field` returns the marks as `ax.extreme_marks`): the single-layer Temperature map quoted the board Tmax, Tmin and Tmean while the rings mark the extremes of the layer shown. Measured at 2 mm on the example, block, outline and reference boards, every model: on every layer that does not hold the coolest point of the board the blue ring and the title Tmin differ (example FVM layers 2 to 4: 43.56, 43.62, 43.42 against 43.16 degC; the Analytic layer 1 44.24 against 44.01), and on a layer without the model's Tmax the red ring is the layer's hottest sample under a title that quotes the board's. The title now reads `max`, `min` and `mean` of the layer (the red ring is the model's Tmax on the layer that holds it); the board numbers stay in the Summary. Test in `tests/test_results_views.py`.
3. **Defect in the program, corner of the cut picture** (fixed, `plots.choose_inset_corner`, constant `INSET_LOAD_TIE` replaces `INSET_LOAD_MAX`): the upper left was kept up to 3 % of the curve samples under it, and once rejected it was never scored again. At the size of the Results tab (5.25 x 4.4 in) the x cut of the example board hid the rising flank of all four curves (1.3 % of the samples, the outline board 2.2 %) while the upper right was empty. The picture now goes to the corner with the fewest samples, never over the hottest point, the upper left on a tie (0.2 % of the samples); of ten cuts of five boards, three moved (to the empty upper right) and seven stay upper left. Tests in `tests/test_map_markers_and_cut_locator.py` (the old test of the upper left now uses the y cut, where the upper left is empty).
4. **Stale document** (fixed): the user guide repeated one sentence of the Profiles row; the docstring of `draw_profile` claimed a strip for a figure "narrower than 1.3 times its height", which the code does not test (only the 5 in width).
5. **Limit to record**: the Lumped red ring sits at the part's reported peak (for example 86.79 degC at (35, 40) mm on the example board) while its map tops at 82.03 degC elsewhere: by design (the peak of a part is not a cell of the map) and said in the guide.
6. **Limit to record**: the inset title with the note `(no map: equivalent rectangle)` is wider than the picture at the Results size and runs over the plot frame (readable, cosmetic).
7. **Limit to record**: a flat field marks nothing on the Results maps but the card of the map on the board still draws both rings on the first sample (cosmetic; a flat field needs a board without power).
8. **Not from these branches**: at 900 x 700 the Results area scrolls sideways because the Animation tab asks 533 px; the Profiles tab asks 325 px with the new box, so the overlay adds nothing to it. At 1280 x 800 nothing scrolls sideways. The docks scroll at 900 x 700 too (older).

## Checked and found right

* Rings against the printed numbers, at 2 mm, FVM, FDM, 3D solid, Lumped and Analytic on the example board, the block board, a one-layer board, an L-shaped outline board (stretched and as-solved frames) and the reference board: on the layer of the model's Tmax the red ring is at `t_max_location` (scaled by `s` in the as-solved frame, 0.929 for the L) and the blue ring at the coolest drawn sample; FDM rings on nodes, cell models on centres; cells off an outline never marked; every panel of All layers marks its own pair.
* Cut line and title: on the example board for 16 positions along x and y (0 to 100 mm) the line in the picture and the title quote the same plotted row or column of the reference model.
* GUI, offscreen, light and dark, 900 x 700 and 1280 x 800, four boards: the inset or the strip is always drawn, the legend never overlaps the picture; the Display popover has the Profiles context (View greyed); an edit unchecks and greys the Map button and the picture drops the map, undo and redo keep it that way until a run; the copper underlay is drawn.
* CO60 (imported, 285 x 95 mm, 359 vias, local library): redraw and draw 0.05 to 0.08 s with or without copper and map, no measurable memory, ten slider moves 0.84 s.
* Command line `run --model compare` on the reference board: `profiles.png` has the picture with the map.
* Tests: 833 passed, 11 skipped (the real-board tests without the library) on the touched and neighbouring files; with the library variables, `test_imported_copper.py`, `test_import_cell_and_add.py`, `test_reimport_matrix.py`, `test_cut_overlay.py` and `test_via_span_warning.py` 91 passed. The whole battery was not run.

## Not verified

The real display (macOS rendering, retina); a real board with genuine blind or buried vias (none in the library); the Results maps of the 3D solid on an outline board in the as-solved frame (it has none); the frozen numbers (no solver code was touched).

## Open decisions for the maintainer

* The command line default of the cut picture is the board with the map (`plot_profiles(picture="map")`, an executor's choice).
* Whether the cut picture should use the colour limits of the Temperature tab (it uses the field's own minimum and maximum).
