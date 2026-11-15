# Notes: branch `feature/gui-panel-polish`

Progress notes of the executor (not a report; the report goes to the main session).

- Item 1 (model labels L3), item 2 (panel groups P2c final) and item 3 (one FEM-not-run warning, Auto with the FEM mesh numbers) are in commit "Group the Simulation settings by model and drop 'comparison' from the labels"; the documents are in the next commit.
- Section 9 of `SIMULATION_PANEL_REVIEW.md` has no accent bar before the title (P2c: bold accent_text title, accent hairline); the task text mentioned a short bar. The spec section was followed; a bar is one `QFrame` away if the maintainer wants it.
- Duplicate warning: the live check (`checks.check_fem`) said 'will be left out' and the run said 'the finite elements (FEM) was not run' (grammar: plural label). The run now uses the short result label ('the FEM was not run') and removes the live notice (`checks.is_fem_left_out`).
- The 'Greyed' tooltip text is now a whole sentence per case (`used only by X, not selected or not available here.` / `not used on a board with a metal block (...)`).
- Not touched (other executor): `gui/warning_box.py`, `results_view.py`, the summary table of `api.py`; only one comment line and `suggest_cell_mm`, the model-skipped warnings and the import line of `api.py` changed.
