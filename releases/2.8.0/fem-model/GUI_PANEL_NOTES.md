# Notes: branch `feature/gui-panel-polish`

Progress notes of the executor (not a report; the report goes to the main session).

- Item 1 (model labels L3), item 2 (panel groups P2c final) and item 3 (one FEM-not-run warning, Auto with the FEM mesh numbers) are in commit "Group the Simulation settings by model and drop 'comparison' from the labels"; the documents are in the next commit.
- Section 9 of `SIMULATION_PANEL_REVIEW.md` has no accent bar before the title (P2c: bold accent_text title, accent hairline); the task text mentioned a short bar. The spec section was followed; a bar is one `QFrame` away if the maintainer wants it.
- Duplicate warning: the live check (`checks.check_fem`) said 'will be left out' and the run said 'the finite elements (FEM) was not run' (grammar: plural label). The run now uses the short result label ('the FEM was not run') and removes the live notice (`checks.is_fem_left_out`).
- The 'Greyed' tooltip text is now a whole sentence per case (`used only by X, not selected or not available here.` / `not used on a board with a metal block (...)`).
- Not touched (other executor): `gui/warning_box.py`, `results_view.py`, the summary table of `api.py`; only one comment line and `suggest_cell_mm`, the model-skipped warnings and the import line of `api.py` changed.

## Message from the reviewer (GUI fix plan, `docs/gui-general-review`, `releases/2.8.0/fem-model/GUI_FIX_PLAN.md`)

* **Unit rule, final** (`UNITS_DELTA_T.md` on `docs/units-delta-t`): absolute temperatures in °C; every difference, rise, margin, oscillation, gradient step and the oscillation threshold in K; resistances K/W; µm. File-format names keep their spelling (`threshold_c`).
* **A0**: if you can still add it before your review, create `pcbthermal/units.py` (no GUI import; `TEMP = "°C"`, `DELTA = "K"`, `MICRO_M = "µm"`, `TIMES = "×"`, `MINUS = "−"`, `ELLIPSIS = "…"`, `layer_label(i, n)` returning `1 (top)` / `4 (bottom)`, and `FORBIDDEN`: the old forms with a reason each: `degC`, `um` after a number, `dT C`, `ΔT °C`, `Osc. °C`) and use it in what you touch. If not, say so in these notes and it goes to `fix/gui-review-rest`.
* **B9 moves to you** (you own `panels.py`): the Properties panel of a Heat source scrolls horizontally because the label 'Direct contact: the source is at the board temperature.' (`gui/panels.py` about line 885, `info = QLabel(...)`) has no word wrap; add `info.setWordWrap(True)` and check the dock at 322 px has no horizontal bar.
* **The dot**: the results branch wrote `gui/dots.py` (`dot_pixmap`, `severity_token`). Do not add a second painter in `theme.py`; keep your memory-line dot as it is, and `fix/gui-review-rest` will route it through `gui/dots.py` after both merges (C20).

## For branch B (`feature/gui-results-warnings`): what to reuse from this branch (merge order: this one first)

- `pcbthermal/units.py`: the unit rule in one place (`TEMP` °C absolute, `DELTA` K for every difference, rise, margin, oscillation and gradient step, `RESISTANCE` K/W, `MICRO_M`, `TIMES`, `MINUS`, `ELLIPSIS`, `layer_label`, `delta_text`, `temp_text`, `FORBIDDEN` with the reason of every old form). The Summary header 'ΔT °C' and the profile 'Osc. °C' are yours: write them from `units`.
- `results.MODEL_LABELS` (short: FVM, LPTN, Analytic, FDM, 3D solid, FEM) and `results.MODEL_FULL` (full), `results.model_label(key)` and `model_full_label(key)`: ONE name per model; 'Lumped' is gone from the visible text (the word was replaced by 'LPTN' in `gui/`, the guide, `checks.py`, `api.py` and the tests; `results_view.py` has a few such word changes in comments and tooltips, so expect small conflicts there).
- The memory dot is drawn once: `theme.VERDICT_DOT` and `theme.verdict_dot(colour)` (an HTML span); use them for the warning rows.
- Theme tokens added: `accent_text`, `primary`, `primary_hover`, `primary_pressed` (the fill of the main buttons under the white `on_accent` label, 4.5:1 or more in both themes) and the light `warn` darkened to #9a5a00 (4.97:1 on the window). `tests/test_simulation_panel_groups.py` checks them against the WCAG formula.
- `ResultsView.clear()` and `Cover` exist in `results_view.py` (a note laid over the run pages, shown by `main_window._after_load`, hidden by `set_simulation`); B owns the rest of that file.
- `api.py`: only `suggest_cell_mm(fem_params=)`, the 'was not run' warnings (short labels, said once), `°C` instead of `degC` in visible strings and the comment of line 43 changed; the table definition is untouched.

- Merge note for B: `results.MODEL_LABELS` (short names, '3D solid' for the 3D solid, as B's labels) is the table; B's `results.MODEL_SHORT` must become an alias of it at the merge (`gui/fieldscale.MODEL_SHORT` already is `dict(MODEL_LABELS)`). The text and Markdown reports (`api.py` `to_text`, `to_markdown`, the profile tables) print these names through `RESULT_MODEL_LABELS.get(key, key)` in the lines of the tables; B changed `api.SUMMARY_COLUMNS` next to them, so the merge is by hand in `api.py`. The report heads follow the unit rule (`ΔT K`, `Rθ K/W`, `Oscillation [K]`, the oscillation threshold in K; the flag `--threshold-c` keeps its name, its help says K).
- Screenshots of the final set: full-colour PNG where the red and amber dots matter (no 256-colour quantisation); see the report of this branch for which pictures were regenerated.
