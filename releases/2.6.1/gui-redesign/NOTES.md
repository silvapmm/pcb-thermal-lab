# GUI redesign 2.6.1: implementation notes

Branch `feature/gui-boxes-warnings-layer-keys` (from `develop`). Items 5 to 8 of 'Planned: 2.6.1'. Mock-ups: `docs/mockups-261/`.

## What is where

* `pcbthermal/gui/boxes.py`: `CollapsibleBox` (title row = button, body widget, state by key `<dock>/<section>` in the QSettings bound by `MainWindow`; in memory when no store is bound).
* `pcbthermal/gui/warning_box.py`: `WarningAccordion` ('Warnings (N)' box, closed rows, 'Select heater U1' button, opened rows survive a refresh by title). `WarningList` stays for the Gerber import window.
* `pcbthermal/checks.py`: `warning_title` and `warning_severity` (a classifier on the text, not a stored field: the checks return plain strings).
* `pcbthermal/api.py`: `Simulation.to_text(inline_warnings=)`, `report(inline_warnings=)`; `save(view=, cmap=)`. `plots.plot_fields(view=, cmap=)`.
* `panels.py`: BoardPanel (Size, Board outline, Environment), SolverPanel (Models, Settings; the accordion is the third box), Inspector `box()` (+ a first box with the element name, layer and type; 'Part' is now 'Power'). Panel side margins 4 px (the Board dock scrolled by 1 px at 900 x 700 otherwise).
* `main_window.py`: footer (Run, progress, status) above the scroll area; `_FooterLimiter` removed; layer keys (`_step_layer`, `_show_layer_key`, `_pick_combo_entry`); `export_results` passes the Display view and colour map.
* Docks keep their object names and `STATE_VERSION` 2 (no dock was added or removed).

## Decisions of the implementation (to confirm)

* Severity: two levels, a symbol only (alert-coloured warning sign for a wrong, refused or unsafe result by key words, a muted bullet otherwise). The classifier is brittle by design (2 h route of the mock-up findings).
* Title: first clause (to `;`, `. `, ` (` after 20 characters, or a colon that closes a first clause of at least 7 words, 4 after a prefix), at most 64 characters, capital first letter. Review: the first rule (a colon after 13 characters) gave titles that were only a prefix ('Analytic model', 'Lumped and Analytic', 'analytic (time simulation)', 'Via 3 and 1 more vias'); every warning text produced by the checks and runs of 12 warning test files (1959 texts) was classified again with the new rule.
* Digit keys 1 to 9 only (a board with more layers uses L); 0 = All layers, offered by Temperature only (status bar says so elsewhere).
* Settings was not split into Cell, Solvers and Laminate (kept as one box).
* Screenshots (offscreen) for 900 x 700 and 1280 x 800, both themes: `scratchpad/shots261/redesign_*.png`; the docks have no horizontal scroll bar. Not verified on macOS cocoa.
* `docs/images` screenshots not regenerated (`examples/make_screenshots.py` was not run: it is not cheap, 74 pictures); `editor_warnings.png` of the guide shows the earlier list and the guide says so.
