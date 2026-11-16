# Review of `feature/gui-results-warnings` (warning rows V1, Summary table a+, results at 1200 x 800, unit rule)

Tree: the six commits of the branch on `development` 6c225276, plus the corrections of this review. Specs: `WARNING_SELECT_REVIEW.md` (V1), `SUMMARY_TABLE_REVIEW.md` (a+), `GUI_GENERAL_REVIEW.md` and `GUI_FIX_PLAN.md` (branch B items), `UNITS_DELTA_T.md` (unit rule). Executor notes: `GUI_RESULTS_NOTES.md`.

**Verdict: GO** after the corrections below (all made on the branch, with regression assertions). No number of any model moves.

## 1. Claims and verdicts

| Claim | Verdict | Evidence |
| :-- | :-- | :-- |
| Warning rows: dot (red warning, amber note) from theme tokens | holds | `gui/dots.py` takes the colour from `theme.colors()[bad/warn]`; measured pixel at the dot centre: light `#c62828` / `#b26a00`, dark `#ef5350` / `#ffb74d`. A change of the `warn` token on the panel branch propagates (no literal colour). |
| Label with the element-type icon and name at the END of the row, selects the element | holds | last item of the head layout; `test_gui_boxes` selects from a closed row by click and by Enter. |
| Keyboard: Tab to the row, Enter opens; Tab to the name, Enter selects | holds (Tab order now tested) | new assertion: Tab from the head gives the focus to the label. |
| Accessible names `Select heater Q1 on the board`, `Warning:` / `Note:` + title | holds | rendered rows print `Select heater Q9 on the board`, `Note: Q9: ...`. |
| Name elided at 110 px, full name in the tooltip | holds | `Q_OFFBOARD_LONG_DESIGNATOR_99` shows `Q_OFFBOARD_L…`, 133 px wide label. |
| Nothing cut at a 322 px dock and a 340 px dock with long designators | **did not hold** (fixed) | with a long designator the title read `63 % of the footprint is outside…`: the title budget of `checks.warning_title` (64 characters) counted the name, which then moved to the label. The title is now taken from the short form of the warning without the name (`set_label_name`). The 322 px dock shows a 15 px horizontal scroll bar, but it comes from the panel content (minimum width 319 px on `development` too, with or without warnings): not this branch (panel branch). |
| Warnings ordered by severity, junction first | holds | real run with `tj_max` 60 on the example board: the junction warnings are `alert`, rank 0, first; the order survives pickling (the run process). The match is on the text `the junction reaches` (fragile if that sentence is reworded: `tests/test_summary_table.py` holds it). |
| Disabled label after an edit | holds | `set_stale` greys every label, `_emit` refuses while stale. |
| Summary: two-line headers naming the read-out, ResizeToContents, horizontal scroll | holds | rendered at 1200 x 800 (scroll, max 241 px) and 1500 x 900 (fits); looked at. |
| Balance as a percentage with a floor, raw value in the tooltip and `summary.json` | holds | `0.00 %` for 5.7e-13; `table()` keeps `energy_balance` raw for `to_dict()`. |
| Rows = number of models; one definition `api.SUMMARY_COLUMNS` for window, `to_text`, `to_markdown`; on-screen report without the table | holds | rendered and printed. |
| `Tmax (surface)` column = the surface read-out (FVM, FDM, FEM; n/a otherwise) | holds | case 2 of Muzychka (50 x 50 x 10 mm, k 150): at 2 mm FVM 99.22 / 105.10, FEM 99.16 / 103.68; at 1 mm FVM 99.25 / 105.13, FDM 99.23 / 105.11, FEM 99.25 / 103.85 (column / surface), each equal to `nanmax(T_surface[0])` and `t_max_surface_top`; the FEM 103.85 is the centred-cell value of `REVIEW_BRANCH4.md` (103.851), 0.03 K above the paper's 103.82 by the 1 um film. Lumped and Analytic `n/a`. |
| Tmean tooltip 'all copper layers, area weighted' | holds | `fvm.py:905`, `fdm.py:486`, `fem.py:250`: every layer counts equally, cells weighted by the area inside the outline. |
| Components not cut at 1200 x 800 | **partly** (fixed) | headers no longer cut, but the scroll bar took the height of the second heater row (U2 behind a vertical scroll bar; viewport 37 px against 55 px on `development`). The heater table now keeps two rows above its bar. |
| Map title on two lines | holds | looked at. |
| Power profile page without a horizontal bar at 1200 x 800 | holds, but **the waveform plot was 10 px tall** (fixed) | stacked panes squeezed the canvas to 10 px (the plot was invisible; this is the new `constrained_layout not applied` warning). The canvas keeps 220 px (`PLOT_MIN_PX`) and the page scrolls vertically; the warning is gone. |
| About last line | holds | label height 292 = height for its width. |
| Profile legend FVM / LPTN / Analytic / FDM / 3D / FEM; map card `LPTN` | **conflict with the panel branch** (fixed) | `feature/gui-panel-polish` makes `results.MODEL_LABELS` the short names with `3D solid`; this branch had `3D`. `MODEL_SHORT` now says `3D solid`; at the merge it should become an alias of `MODEL_LABELS` (both define the same table). |
| Units: K for differences | holds where touched | no `ΔT °C`, `Osc. °C`, `dT C`, `oscillation ... °C` left in `gui/`, `api.py`, `help/`. Stale texts fixed by this review: the guide (`1 °C threshold` in the fast-wave example; the Balance example `+10.00E-15` now names the tooltip), `docs/models.md` and `docs/theory.md` (threshold default 1 K). `threshold_c` keeps its name. Left to the panel branch (it edits these lines): `cli.py` help of `--threshold-c` (`in degC`), `tips.py:19` (`35 um`) and `SURFACE_MAX_TIP` (`degC`), the `degC` of the text report (absolute temperatures, the rule's spelling `°C` is the panel branch's change of `api.py`). |
| Oscillation threshold box and tooltip in K | holds | `Ignore oscillations below 1.00 K`. |
| `docs/decisions-log.md` and `CHANGELOG.md` entries | exist | both present. |
| Screenshots regenerated | hold; one limit | `editor_warnings.png` (and help copy), `results_summary.png`, `results_summary_imported.png` looked at; regenerating the import pictures on the corrected tree gives the same titles (no replacement needed). Limit: the screenshots are quantised to 256 colours (`make_screenshots.py:63`), which merges the red and the amber dots into one brown in the pictures (all 12 dots of `results_summary_imported.png` are the same palette entry, the junction alert included). |

## 2. Corrections made (files)

* `pcbthermal/gui/profile_page.py`: `PLOT_MIN_PX` 220, floor of the waveform canvas.
* `pcbthermal/gui/results_view.py`: the heater table keeps two rows plus its scroll bar.
* `pcbthermal/gui/warning_box.py`: the row title is `warning_title` of the short form without the element name.
* `pcbthermal/results.py`: `MODEL_SHORT["solid3d"] = "3D solid"`.
* Tests: `tests/test_layout_1200.py` (canvas height, short name), `tests/test_summary_table.py` (two heater rows visible), `tests/test_warning_icons.py` (long designator, short form, Tab order).
* Documents: `pcbthermal/help/index.html`, `docs/models.md`, `docs/theory.md`, `docs/versions.md`, `docs/decisions-log.md`, `GUI_RESULTS_NOTES.md`.

## 3. Runs (corrected tree)

* `test_docs, test_license_header, test_version, test_help, test_tooltips, test_summary_table, test_layout_1200, test_warning_icons, test_theme_coherence, test_gui, test_gui_boxes, test_gui_profile, test_ui_cleanup, test_results_views, test_fem_gui, test_api, test_report_disclaimer, test_numfmt, test_stackimpedance`: 1087 passed, no warning (the constrained-layout warning was new on this branch: the same GUI tests on `development` 6c225276 in a clean worktree give none; it came from the squeezed canvas).
* `tests/test_gui_stress.py -k 'not random'`: 61 passed, 3 deselected (7 min).
* `PCBT_FROZEN_CELLS=2 pytest tests/regression`: 170 passed.
* Not run: the whole battery (not asked), the random-action stress tests.

## 4. Readers of the old report format (for the reproduction pass)

The text table (`dT C`, `Rth K/W`, `vs fvm`, one header line) and the Markdown header (`Error vs fvm`, `ΔT [°C]`) changed. Search of `research/`, `releases/` and `tests/`: no script parses the models table of `report.txt`, `to_text()` or `to_markdown()`; `research/stackup/scripts/make_figures.py` parses Markdown tables of its own study output, not the program report; `tests/test_fem_model.py` checks `| fem |` (still true: the row cells keep the model key). Nothing to update; the reproduction pass should still diff any saved `report.txt` it compares by text.

## 5. Open points for the maintainer

1. Merge with `feature/gui-panel-polish`: `results.MODEL_SHORT` duplicates the panel branch's short `MODEL_LABELS` (same names now): keep one (alias). Expect small conflicts in `api.py` (report lines), `results_view.py`, `fieldscale.py` (the `MODEL_SHORT` line), `profile_page.py`, `plots.py`, `help/index.html`, `CHANGELOG.md`. The text and Markdown reports still print the model KEY in the first column (`fvm`, `lumped`) while the header says `Error vs FVM`; the panel branch says keys are never shown: decide whether the report rows take the labels (a text change of `report.txt`, `| fem |` in one test).
2. The 256-colour screenshots lose the red/amber difference of the dots (and of the memory verdicts): more colours or no quantisation for those pictures (bigger files)?
3. Pictures made stale by this branch and not regenerated here (doc review, step 6b): those that show a map title on one line or the Components tables (`results_temperature_imported*.png`, `results_views*.png`, `results_surface_table.png`, `results_fem_surface.png`, `results_gradient.png`), and the Power profile page.
4. The 15 px horizontal bar of the Simulation dock at 322 px is the panel content (319 px minimum on `development`): panel branch.

## What was verified and what was not

Verified by running: every row of section 1, with renders looked at (dock 322 and 340 px with long designators, Summary and Components at 1200 x 800 and 1500 x 900, map, profiles, Power profile page at 1200 x 800 before and after, About) and the surface column against the read-out on a published case. Not verified: a screen reader (only the accessible names were read), a high-DPI screen (offscreen at ratio 1), the light-theme contrast of `warn` (panel branch tokens), the random-action stress tests and the whole battery.
