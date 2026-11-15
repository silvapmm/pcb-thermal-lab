# Branch 5 (`feature/fem-gui`): progress notes

Done (follows `DECISIONS_REVIEWER.md` A1 to A8, which override `BRANCH5_PLAN.md`):

* Checkbox, tooltip, `GUARDED_MODELS`, verdict row (mesh reason when no mesh; pyamg row via `checks.fem_needs_pyamg`), Run block from `api.SKIPPABLE_MODELS`, two mesh boxes in the Settings box (not in Preferences), `Preferences.MODELS`, `MODEL_SHORT`, progress text with the model name, resolved surface column header and tooltip with the hottest node (`analysis.point_max`), '(column)' on the zone and hotspot tables.
* Guide text and two screenshots, tests `tests/test_fem_gui.py`, `tests/test_model_lists.py`, FEM scenarios in `tests/test_gui_stress.py` (not in `ALL_MODELS`).
* Not done on purpose: surface CSV export from the window and progress inside the FEM (2.9.0), the three random-action tests (about 7 min) were skipped in the runs.
