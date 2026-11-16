# Tester's resolution record: A (`feature/gui-panel-polish` 498d4335) then B (`feature/gui-results-warnings` 4b461802), throwaway `tmp/merge-gui-ab` from `development` 6c225276

Merge of A: clean. Merge of B: 11 conflicted files, resolved exactly per `MERGE_NOTES_GUI_AB.md` section 1.

| File | Hunk | Kept |
| :-- | :-- | :-- |
| `pcbthermal/results.py` | 1 | A's `MODEL_LABELS` + `MODEL_FULL`; then `MODEL_SHORT = MODEL_LABELS` (alias) and B's `short_name(key)` |
| `pcbthermal/gui/fieldscale.py` | 1 | B's import `from ..results import MODEL_SHORT` |
| `pcbthermal/plots.py` | 1 | A's line `label=model_label(name)` |
| `pcbthermal/api.py` | 0, 3 | B (summary table in `to_markdown` and `to_text`) |
| `pcbthermal/api.py` | 1, 2, 5, 6 | A (model names, degree sign) |
| `pcbthermal/api.py` | 4 | A's report head ('×', '°C') with B's call `self.to_text(inline_warnings, table)` |
| `pcbthermal/gui/results_view.py` | 0 | B (`summary_table()`) |
| `pcbthermal/gui/results_view.py` | 1 | A's two lines `for cover in self._covers: cover.cover(False)` then B's two lines (`summary_grid`, `set_summary_headers`) |
| `pcbthermal/help/index.html` | 0, 1, 2 | B's text with 'Lumped' -> 'LPTN' |
| `tests/test_help.py` | 1 | B's list, 'Lumped' -> 'LPTN', 'Finite elements (FEM), comparison' -> 'Finite elements (FEM)' |
| `docs/decisions-log.md`, `docs/versions.md` | 1 each | both entries, B's first |
| `docs/images/editor_warnings.png`, `pcbthermal/help/editor_warnings.png` | binary | B's (`--theirs`); to regenerate later |

Outside the conflicts: `pcbthermal/api.py` tooltip of the Summary surface column, 'the Lumped, Analytic' -> 'the LPTN, Analytic' and 'For the Lumped model' -> 'For the LPTN model'.

Stale tests/text glue fixed as small commits: none so far (see the end of this file for any added after the battery).

## Fixes after the whole battery (3 failures, all glue)

The battery (3963 passed, 3 failed) ran BEFORE these commits.

1. `pcbthermal/api.py` `Simulation.summary_grid(model_name=None)`: with no function the first column is the short name of `results.MODEL_LABELS` (it was the key after B rebuilt the table). Fixes `tests/test_model_names.py::test_the_text_and_markdown_reports_print_names_not_keys` and `tests/test_simulation_panel_groups.py::test_the_report_names_the_models_not_their_keys` (as in `MERGE_NOTES_GUI_AB.md`).
2. Tests adapted (as in the notes): `tests/test_summary_table.py` (`test_the_surface_column_...` passes `lambda k: k`; `test_one_definition_...` finds the rows by `model_label(m)`), `tests/test_numfmt.py` (row `| FVM`).
3. `tests/test_block_models.py::test_simulate_runs_every_model_with_a_block_and_says_how`: not a defect. Commit c6b82720 (A) changed the warning to "time simulation not run for LPTN (...)" (`RESULT_MODEL_LABELS` in `api.py` line ~1171); the test still looked for the key "lumped". Test now looks for "LPTN". The warning text itself is A's, unchanged.
