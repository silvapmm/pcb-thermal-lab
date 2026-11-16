# Merge notes: `feature/gui-panel-polish` (A) then `feature/gui-results-warnings` (B)

A throwaway merge (`tmp/merge-ab-check`, from A at the review commit, then `git merge --no-ff feature/gui-results-warnings` at `4b461802`) was made by the reviewer of A to prepare the merge of B into `development` after A. The worktree and the branch were removed after the check. Merge order: A into `development` first, then B (B's maintainer merges the new `development` into B, or merges B with these resolutions).

## 1. Conflicts and their resolution (keep both)

| File | Conflict | Resolution |
| :-- | :-- | :-- |
| `pcbthermal/results.py` | A: `MODEL_LABELS` with 'LPTN' plus `MODEL_FULL`; B: old `MODEL_LABELS` ('Lumped (LPTN)') plus `MODEL_SHORT` and `short_name` | A's two tables, then `MODEL_SHORT = MODEL_LABELS` (an alias: one short name per model) and B's `short_name(key)` returning `MODEL_SHORT.get(key, key)` |
| `pcbthermal/gui/fieldscale.py` | A: `MODEL_SHORT = dict(MODEL_LABELS)`; B: `from ..results import MODEL_SHORT` | B's import line (A's `from ..results import MODEL_LABELS` at the top stays) |
| `pcbthermal/plots.py` | profile legend: A `model_label(name)`, B `short_name(name)` | A's line (the same text; `plots.py` imports both) |
| `pcbthermal/api.py` (7 hunks) | B rebuilt the Summary table (`SUMMARY_COLUMNS`, `summary_grid`, `to_text(table=)`); A wrote model names and the unit rule in the lines around it | hunks 0 and 3 (the table in `to_markdown` and `to_text`): B's; hunk 4 (report head): A's line ('Board 100.0 × 80.0 mm', '°C') with B's call `self.to_text(inline_warnings, table)`; hunks 1, 2, 5, 6 (profile decision, ripple, time-simulation lines): A's (model names, °C) |
| `pcbthermal/gui/results_view.py` (2) | A: old table with `ΔT °C`, and the covers hidden in `set_simulation`; B: `summary_table()` and `summary_grid` | hunk 0: B's; hunk 1: A's two lines `for cover in self._covers: cover.cover(False)` followed by B's two lines |
| `pcbthermal/help/index.html` (3) | the dock row (B's round dots and element label), the Summary row (B's two-line headers), the time-step paragraph | B's text with 'Lumped' replaced by 'LPTN' (A's only change in those lines) |
| `tests/test_help.py` | the word list | B's list with 'Lumped' as 'LPTN' and 'Finite elements (FEM), comparison' as 'Finite elements (FEM)' |
| `docs/decisions-log.md`, `docs/versions.md` | both prepended an entry | both entries, B's first (newest) |
| `docs/images/editor_warnings.png`, `pcbthermal/help/editor_warnings.png` | binary | B's (it shows B's warning rows); to be regenerated in full colour on the merged tree (A's `FULL_COLOUR` covers `editor*`), see section 3 |

## 2. Not a conflict but needed on the merged tree

* `pcbthermal/api.py`, B's tooltip text of the Summary surface column (about lines 260 and 266): 'the Lumped, Analytic and 3D solid models' and 'For the Lumped model' read 'LPTN' (A's one-name rule). Done in the throwaway merge; B's maintainer applies the same two words at the real merge.
* **The text and Markdown reports printed the model keys again** on the merged tree (`lumped    86.91 ...`): B's `to_text` and `to_markdown` build their rows with `Simulation.summary_grid()` without a name function, so the first column was the key, and A's two tests (`test_model_names.py::test_the_text_and_markdown_reports_print_names_not_keys`, `test_simulation_panel_groups.py::test_the_report_names_the_models_not_their_keys`) failed. Resolution: `summary_grid(model_name=None)` writes the short name of `results.MODEL_LABELS` when no function is given (the window still passes its own); Three tests of B read the first column as the key and are adapted: `tests/test_summary_table.py::test_the_surface_column_is_the_top_face_peak_or_n_a` passes `lambda k: k` to `summary_grid`; `test_one_definition_feeds_the_window_the_text_and_the_markdown` finds the rows of `to_text` by `model_label(m)`; `tests/test_numfmt.py::test_balance_column_of_the_summary_is_a_percentage_with_a_floor` looks for the row `| FVM`.
* After the merge `results.MODEL_LABELS` and `results.MODEL_SHORT` are the same object; `gui/warning_box.py` (B) still turns ' degC' into ' °C' in titles (`display_title`), harmless now that the program writes °C.

## 3. Checks on the merged tree

* Quick GUI tests (the set of the review of A, 20 files, plus B's `test_summary_table.py`, `test_layout_1200.py`, `test_warning_icons.py`, `test_ui_cleanup.py`; `test_gui_stress.py -k 'not random'`): first run 1065 passed and 2 failed (the reports printing keys, above); after the resolution `test_summary_table`, `test_numfmt`, `test_model_names`, `test_simulation_panel_groups`, `test_report_disclaimer`, `test_stackimpedance` and `test_docs` re-run: all passed (977, then 89 after the last two test adaptations). The whole battery was not run on the merged tree: it is the tester's step before the merge of B.
* Pictures: `editor_warnings.png` (both copies) and B's `results_summary*.png` must be regenerated on the merged tree before the final set of branch C; the results pictures that still show 'Lumped (LPTN)' are listed in `REVIEW_GUI_PANEL.md` section 5.
