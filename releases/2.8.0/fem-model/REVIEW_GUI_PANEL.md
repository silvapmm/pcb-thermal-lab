# Review: branch `feature/gui-panel-polish` (branch A of `GUI_FIX_PLAN.md`)

Reviewer's check of the five commits up to `93483c14` (on `development` `6c225276`), against `SIMULATION_PANEL_REVIEW.md` section 9 (P2c final), `MODEL_LABELS_REVIEW.md` (L3), `GUI_FIX_PLAN.md` (items of branch A, plus B9) and `UNITS_DELTA_T.md` (the final unit rule). Every measurement below was taken offscreen on this branch (`QT_QPA_PLATFORM=offscreen`, window 1200 × 800, both themes) by scripts kept outside the repository. No number of any model moves.

## 1. Verdict

**GO**, with the corrections of section 3 (committed on this branch) and the leftovers of section 5 handed to branch C (`fix/gui-review-rest`).

## 2. Verdict per claim

| Claim | Verdict | Evidence |
| :-- | :-- | :-- |
| L3 labels exactly as `MODEL_LABELS_REVIEW.md` 1 | Holds | Models box reads `Finite volume (FVM), reference`, `Thermal network (LPTN)`, `Analytical (Fourier series)`, line, `Finite difference (FDM)`, `3D solid (finite volumes)`, `Finite elements (FEM)`; ', reference' only on the FVM; the labels come from `results.MODEL_FULL` |
| Role sentence in the three tooltips | Holds | each starts 'Off by default; a cross-check of the three models above.'; no 'comparison' left in the six labels or tooltips |
| Separator after the Analytic | Holds | a 1 px `QFrame` in `muted`, between the Analytic and the FDM boxes (layout order checked), recoloured on a theme switch |
| `api.py:43` comment corrected | Holds | 'the reference of the decisions is the first ticked of MODEL_NAMES + COMPARISON_MODELS (a main model when one runs)', which is what `Simulation.reference` does |
| `cli.py` help without 'comparison models' | Holds | |
| P2c: six groups in the order of 9.2 | Holds | All models, Finite volume (FVM), Laminate (FVM, FDM), Thermal network (LPTN), Analytical, Finite elements (FEM) |
| One label x and one field x in every group | Holds | measured with `mapTo(panel)`: labels x = 8, fields x = 134, titles x = 8, in light and dark, with FVM + FEM and with LPTN + Analytic, at dock widths 322, 340 and the default |
| 10 px around the Settings toggle | Holds by construction | 6 px spacing + the 4 px of the boxes above and below (code comments); not measured in pixels |
| A group greyed with 'not ticked' | Holds | title `muted`, line `border`, tag '<tag> · not ticked', controls and their labels disabled with a whole-sentence 'Greyed: ...' tooltip; the laminate group greyed on a board with a metal block (its tag then also says 'not ticked' although the FVM is ticked: the spec's wording; the tooltip says the real reason) |
| Memory lines compact with the dot, the dot drawn once | Holds | `● FVM: 39052 unknowns · 0.3 of 10.3 GB` (example board, 1 mm); `theme.VERDICT_DOT` / `theme.verdict_dot` used by every row; no thousands separator; the label hidden with only LPTN + Analytic ticked |
| Title colour `accent_text` with 4.5:1 or more | Holds | computed with the WCAG formula: light #4a6a96 5.03:1 on the window, 5.54:1 on white; dark #6a90c0 4.89:1 on the window, 5.39:1 on the base |
| No accent bar (P2e) | Holds | P2c as chosen: bold title, tag at the right, hairline; no bar |
| No horizontal bar in the Simulation dock | Holds at the window's widths (340 px default) | at 322 px a 4 px horizontal bar remains: the panel's minimum width is 308 px (as the P2c prototype measured) plus the vertical scroll bar; 322 px is narrower than the dock opens (limit, section 5) |
| Properties: the 'Direct contact' label wraps (B9) | **Was not done**; fixed by the review | see 3.1 |
| One name per model | Holds in the window and the guide; **not** in four lines of the report, the CLI calibrate line and four README lines | fixed, see 3.3 and 3.4; what remains in section 4 |
| Unit rule in one place (`pcbthermal/units.py`) | Holds | `TEMP`, `DELTA`, `RESISTANCE`, `MICRO_M`, `TIMES`, `MINUS`, `ELLIPSIS`, `layer_label`, `FORBIDDEN` with reasons; the tool-bar Layer box uses `units.layer_label`; `tests/test_units_rule.py` |
| `--threshold-c` help in K, the value unchanged | Holds | help 'oscillation in K'; the option, the JSON field `threshold_c` and the number are unchanged (a difference: the same number in K and in °C) |
| 'Cannot run: <reason>' in red under the button | Holds | `bad` colour; at 1200 × 800 the status line sits at y = 164 px of the window, above the scrolled boxes, visible (306 × 75 px visible region for the two-line memory refusal of a 400 × 300 mm board at 0.5 mm) |
| FEM without pyamg names the cell | Holds, number corrected | see 3.2 |
| 'Calculating…' in the status bar | Holds as 'Calculating: Stop with Ctrl+.' | the low-memory warning shown at the start was overwritten at once by it; fixed (3.5) |
| Indeterminate bar for the FEM | Holds | `progress.maximum() == 0` while the text starts with 'Solving FEM' |
| Menu 'Stop calculation' | Holds | menu, `SHORTCUTS_HTML` ('stop the calculation'), guide |
| Results cleared on New / Open / Import (`ResultsView.clear`, `Cover`) | Holds | driven: run, open the saved file: `win.sim is None`, every cover shown, no 'Done:' line, tab title 'Results' |
| The clear does not touch the project | Holds | saved before a run, after the run and after reopening: the same bytes (new test, 3.6) |
| Contrast tokens | Holds | Run label (white) on `primary`: light 5.54 / 6.43 / 7.54:1 (normal, hover, pressed), dark 5.49 / 5.11 / 7.05:1; `warn` light #9a5a00 4.97:1 on the window, 5.47:1 on white; dark `warn` 9.32:1; `bad` 5.11:1 light, 4.63:1 dark |
| The darker `warn` as a fill | No breakage found | `warn` is used as text and dot colour (memory lines, warning dots); the dots stay amber and distinct in the full-colour pictures |
| Auto respects the FEM mesh, also in the CLI | Holds | `suggest_cell_mm(fem_params=)` from the panel and from `cli._cell_arg`; test with 24 gap elements |
| The single 'FEM was not run' warning | Holds | the live 'will be left out' notice is dropped when the run itself says 'the FEM was not run' (`checks.is_fem_left_out`) |
| Screenshots in full colour | Holds | `FULL_COLOUR` prefixes `editor`, `simulation_`; looked at: `simulation_fem.png`, `editor.png`, `editor_imported*.png`, `editor_warnings.png`, `results_fem_surface.png` (both copies identical in `docs/images` and `pcbthermal/help`) |

## 3. Corrections made by the review

1. **B9, the Properties panel scrolled sideways** (`gui/panels.py`, Inspector): the 'Direct contact: the source is at the board temperature.' label had no word wrap; with it wrapped the panel still asked 334 px, because the closed lists were 14 characters wide next to the 'Interface conductivity' label column. The label now wraps and the lists of the Properties panel are 12 characters wide (the open list still shows every entry): a heat source asks 318 px instead of 354 px, and the 340 px dock has no horizontal bar. Test `test_the_properties_of_a_heat_source_fit_a_narrow_dock`.
2. **The FEM cell for the direct solver was not the smallest** (`checks.fem_cell_for_direct`): the first guess, from 1 / cell², overshoots because the through-thickness planes do not scale with the cell: it quoted 3.5 mm on the example board where 3.4 mm fits (26 910 unknowns against the 30 000 of the direct solver; 3.3 mm does not fit) and 11.4 mm on a 400 × 300 mm board where 11.0 mm fits. It now steps down by 0.1 mm while the mesh still fits and tests the rounded cell it quotes. Test `test_the_fem_cell_for_the_direct_solver_is_the_smallest_that_fits`.
3. **Keys in the report**: 'Reference model: lumped', 'the lumped model has no surface read-out here', the time-simulation warnings 'lumped (time simulation): ...' and 'time simulation not run for lumped, analytic' printed keys; they print the short names now. The CLI calibrate line ('the lumped model then gives') and the surface line (`name.upper()`) use `model_label`. Test `test_the_report_names_the_models_not_their_keys`.
4. **Old forms left**: the tooltip `tips.py` 'on 35 um copper' (now µm), the guide 'the layers (1 top ... n bottom)' (now '1 (top) ... n (bottom)', as the Layer box writes them), the report head 'Board 100.0 x 80.0 mm' (now ×). README: 'the Lumped and Analytic' (three feature lines) and the models table row '**Lumped**' now say LPTN; `docs/models.md` still quoted the checkbox `Finite elements (FEM), comparison` and wrote 'the FVM, Lumped and Analytic models' in the new sentence; `docs/versions.md` 'Planned' quoted the old checkbox label (now with a note of the rename).
5. **The low-memory warning at the start of a run** was written in the status bar and replaced at once by 'Calculating: Stop with Ctrl+.' (the busy signal is synchronous); it is now written after the start.
6. New test `test_a_project_opened_after_a_run_saves_the_same_bytes` (the clear touches only the views).

## 4. One name per model: what remains, and whether it is intended

* `docs/models.md` (about 45), `docs/theory.md` (about 55) and `docs/validation.md` (about 270) use 'Lumped' in prose as the technical name of the ring network, as do the records of past versions (README 2.4.5 to 2.7.0 lines, `CHANGELOG.md`, the Decisions Log). Not visible in the program; left for the documentation review of 2.8.0 (renaming the validation record would rewrite history).
* Code comments, docstrings and identifiers keep `lumped` (the key) and in places 'Lumped'; not visible.
* The summary header 'ΔT °C' of the Results table and the 'Osc. °C' column of the Power profile page are branch B's (B13); B writes 'ΔT K' and 'Osc. K'.
* Grammar in comments: 'a LPTN' (read 'an LPTN'); not visible.

## 5. Leftovers for branch C (`fix/gui-review-rest`) and limits

* Simulation dock at 322 px: a 4 px horizontal bar (panel minimum 308 px + vertical scroll bar); the window opens the dock at 340 px. Properties of a **metal block** heatsink: 337 px (a nested box), a small horizontal bar at 340 px; not part of B9.
* A6 (rest): the FEM mesh cap refusal ('more than the 6000000 it accepts: use a coarser cell') still gives no cell; the FEM warning title has no verb.
* A8: after a run the status bar returns to 'Ready.' while a result is shown; after a Stop it says 'Ready.' while the dock says 'Cancelled.'.
* A9: `muted` light is 4.39:1 on the window (below 4.5:1; used for the greyed group titles, where a disabled control is exempt); the `field_border` token was not added.
* A5: the memory dot is an HTML span (`theme.verdict_dot`), not the pixmap painter of B (`gui/dots.py`); C20 routes it through `dots.py` after both merges.
* A10 (focus ring of the primary button), A11 (Stop in the `bad` fill, bar hidden when idle), A12 (the ellipsis 'Preset shape...' and the other panel strings) were not done on this branch.
* Pictures for the final set of branch C: the window pictures that still show the old Simulation panel (', comparison', 'Lumped rings') or 'Lumped (LPTN)' / 'fvm' in a table or a legend, among them `results_summary.png` and `results_summary_imported.png` (regenerated by B before the name change), `results_profile_cut.png` (legend 'fvm', looked at), `results_temperature*.png`, `results_views*.png`, `results_components.png`, `results_gradient.png`, `results_power_profile.png`, `results_terrain.png`, `results_surface*.png`, `animation*.png`, `outline_temperature.png`, `editor_overlay.png`, `power_profile.png` (not each looked at; listed by what they show); and `editor_warnings.png` after the merge with B (section 3 of `MERGE_NOTES_GUI_AB.md`).
* Not verified: macOS native fonts (wider than offscreen), VoiceOver; the 10 px around the Settings toggle was read from the code, not measured.

## 6. Tests run

* This branch with the corrections (one `pytest` at a time, offscreen): `test_docs`, `test_license_header`, `test_version`, `test_help`, `test_tooltips`, `test_simulation_panel_groups`, `test_model_names`, `test_units_rule`, `test_model_lists`, `test_fem_gui`, `test_gui`, `test_gui_boxes`, `test_gui_profile`, `test_preferences_layout`, `test_theme_coherence`, `test_warning_context`, `test_laminate_edge_band`, `test_profiles`, `test_report_disclaimer`, `test_gui_stress -k 'not random'`: **1061 passed, 3 deselected** in 11 min 10 s. Frozen numbers `PCBT_FROZEN_CELLS=2 pytest tests/regression`: **170 passed**. The whole battery was not run (the maintainer runs it before the merge).
* The throwaway merge with branch B (`MERGE_NOTES_GUI_AB.md`): the same set plus `test_summary_table`, `test_layout_1200`, `test_warning_icons`, `test_ui_cleanup`: 1065 passed and 2 failed, both the reports printing keys after B's table rework (B's `to_text` and `to_markdown` call `summary_grid()` without names); resolved in the merge notes (`summary_grid` writes the short names by default; three tests of B adapted), then the report and summary tests re-run on the merged tree: all passed.
