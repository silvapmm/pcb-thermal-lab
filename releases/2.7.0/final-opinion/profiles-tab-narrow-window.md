# Review: the Profiles tab in a narrow window (commit 0c182755)

Branch `fix/results-map-markers-and-cut-locator`. The commit `0c182755` ('Keep the Profiles tab and its thumbnail in view in a narrow window') was left out of 2.7.0 by accident. Display only: no solver, no result and no frozen number is touched.

## Verdict

**GO**, after the corrections below (made on the branch in the merge of `development`). Safe for a 2.7.1 patch: about 150 lines, two GUI files and one helper of `plots.py`, display only, a regression test, and the GUI tests pass.

## 1. The problem, reproduced on `development` (2.7.0)

Offscreen, the example board, FVM + Lumped + Analytic at 2 mm, window 900 x 700 with both docks open, Results - Profiles:

| tree | minimum width of the Results tabs | width given to the page | horizontal scroll | cut picture |
| :-- | --: | --: | :-- | :-- |
| `development` | 531 px | 248 px | yes (283 px) | out of view (the canvas is 519 px wide in a 248 px page) |
| the commit as written, merged | 295 px | 248 px | yes (47 px) | in view (strip), the Cut overlay box cut to 'Cut o' |
| this branch after the review | 192 px | 248 px | none | in view (strip), the Cut overlay box on a line of its own |

At 1280 x 800 none of the three trees scrolls and the layout of the Profiles tab is unchanged (one control line, inset picture).

## 2. Findings

1. **The commit no longer fixed the problem on the 2.7.0 tree** (defect of the change, interaction with 2.7.0): 2.7.0 added the Cut overlay box (97 px) to the Profiles control line, which set the minimum width of that tab to 291 px, so the Results page still scrolled 47 px at 900 x 700. The commit's own test (no horizontal scroll at 900 x 700) fails on the merged tree. Fixed: the box takes a line of its own when the first line cannot hold it at its natural width (`PlotTab._place_cut_overlay`, from `resizeEvent`), and its own width no longer counts in the minimum.
2. **The Animation and Power profile pages clipped their controls** (regression of the commit): the commit gave those two pages the Ignored size policy for good, so on the Animation tab at 900 x 700 the Mode, Duration and Frames boxes and the Compute button were squeezed to unreadable stubs with no way to scroll to them (on `development` they scroll). Fixed: only the page shown sets the minimum size of the Results tabs (`ResultsView._size_to_current_page`, on `currentChanged`; the hidden pages are Ignored), so the Profiles tab is narrow and the Animation tab scrolls as before. Checked by rendering both tabs on both trees.
3. **The thumbnail redraw followed a layout that 2.7.0 replaced**: the commit redrew the figure when its shape crossed width = 1.3 x height (thumbnail beside or above the curves); in 2.7.0 the picture is an inset over the curves, or a strip above them in a figure narrower than 5 in (`INSET_MIN_WIDTH_IN`). The merge keeps 2.7.0's `draw_profile` and changes the helper to `plots.profile_has_strip` (figure narrower than `INSET_MIN_WIDTH_IN`), which the resize handler uses.
4. Conflicts of the merge (`CHANGELOG.md`, `plots.py`, `results_view.py`, the test file) were resolved keeping every 2.7.0 change (the cut overlay from Display, the hot and cold marks, the corner choice); the old `[2.7.0]` text of the branch was dropped in favour of the released one, and the entry is in a new `[Unreleased]` section, Fixed.

No conflict with the other 2.7.0 GUI work: the warnings accordion, the Run/Stop button and the Display popover are in other widgets (their tests pass); the Temperature and Gradients rows keep their `FlowLayout`.

## 3. Tests

* `tests/test_map_markers_and_cut_locator.py::test_profiles_tab_never_scrolls_sideways_and_keeps_its_cut_picture` (900 x 700 and 1280 x 800): no visible horizontal scroll bar on the Results page, the minimum width of the tabs below 240 px on Profiles and at least that of the Animation page when it is shown, the Cut overlay box on the second line at 900, exactly one cut picture inside the canvas, and a canvas resize across 5 in redraws (inset to strip or back). The scroll and width assertions fail on `development` (531 px, scroll 283 px).
* Quick set on the merged tree: docs, licence header, version, help, tooltips, shortcuts, results views, window growth, dock layout, single layer, map markers: 834 passed, 2 skipped; cut overlay, display control, toolbar icons: 46 passed; `tests/test_gui_stress.py`: 61 passed (9 min 37 s).

## 4. Not verified

* A real display (macOS, retina): offscreen only.
* The narrowest case below about 190 px of centre area: the slider shrinks to its handle and the position text is clipped (accepted, as in the commit).
* No new control, so no tooltip or user-guide change (the guide does not describe where the Cut overlay box sits).
