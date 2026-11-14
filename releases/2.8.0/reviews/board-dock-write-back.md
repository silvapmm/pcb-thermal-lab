# Review: `fix/board-dock-write-back`

**Verdict: GO** (with the reviewer's fixes below committed on the branch; the whole battery is the maintainer's before the merge).

The branch fixes a real defect: the Board settings dock rewrote every board field from its boxes on a single edit, and the boxes clamped or rounded what they had loaded (a 10 mm copper plate became 210 um and the run read 991 to 1138 degC with no warning). The fix (`gui/spinfit.py` `fit_range`, the docks writing only the boxes that differ from what they showed after the load, greyed boxes never written, wider ranges) is right and its eight tests hold it. The review drove the dock through the real main window and found three more paths of the same kind, fixed here.

## Findings

| # | Kind | Finding | Evidence | Fixed |
| :-- | :-- | :-- | :-- | :-- |
| 1 | Program defect (made visible by the branch) | **An undo or a redo left the Simulation dock stale.** `_restore` replaces the whole project, the options included, and emits only `changed`; the Simulation dock reloaded only on `state_changed`, which an undo emits only when the clean flag flips. Sequence: edit h_top, add two vias, cell 0.7 mm, undo: the project held 1.0 mm, the box showed 0.7 mm (and `_shown` 0.7). On `development` the next edit of any box wrote 0.7 back; on the branch, which writes only edited boxes, nothing corrected it, and a run used 1.0 mm while 0.7 was shown. | offscreen MainWindow script: `cell doc 1.0 box 0.7 shown 0.7` after the undo | `SolverPanel` reloads on `changed` too (its refresh already ran the two slots that were connected there); the profile run settings likewise. Test `test_an_undo_reloads_the_simulation_dock`. |
| 2 | Program defect (the open item of the branch) | **The Power profile page rewrote the whole wave and all run settings on any edit of the page**, rounded to the box decimals: a period of 1/3 s, a duty of 12.3456 %, a time of 1.23456789 s. | test before the fix: period, duty and time rounded | `_wave_from_editor` keeps every field of the stored wave whose box was left alone (in the average mode the stored average); `_apply_options` writes only edited boxes. Tests `test_the_power_profile_page_does_not_round_the_wave`, `test_the_profile_run_settings_are_not_rewritten`. |
| 3 | Program defect | **`fit_range` raised on an integer box** for a value beyond a C int (`math.ceil(inf)`, or `setMaximum(10**12)`: OverflowError). `SolverOptions` bounds `lumped_rings` only from below, so a hand-edited project with 1e12 rings made the dock refresh raise (`setValue` raised the same on `development`). | probe: `QSpinBox inf EXC OverflowError`, `1e12 EXC OverflowError` | `fit_range` ignores non-finite values and stops an integer box at the C int; `show_value` sets the nearest whole value inside it. Test `test_an_integer_option_beyond_a_c_int_does_not_break_the_dock`, `test_fit_range_ignores_values_no_box_can_hold`. |
| 4 | Program defect, small | The New board dialog (user defaults), the Background image dialog (its placement is written whole when OK is pressed: a stored width above 4000 mm became 4000), the Power Calculator and the Gerber import window clamped a loaded value the same way. | read of `main_window.py`, `calculator.py`, `import_window.py` | `fit_range` before `setValue` in the four places. |
| 5 | Stale document | The CHANGELOG and `docs/versions.md` named the branch `fix/dock-writeback-clamp`. | `grep` | Renamed to `fix/board-dock-write-back`; the entries say what the review added. |
| 7 | Unexplained interface state (user report) | A user 'could not see h top, h bottom and h edges' at first. Measured through the real window on projects opened from `.pcbt.json` (a `.pcbtz` takes the same load path, `package.load_any`): with `h_mode` manual all three are visible and enabled; with `h_mode` **computed** h top and h bottom are **hidden** (`_show_modes`), and with the edges insulated (`h_side` None) h edges is **greyed**; neither said why. The models chosen (3D solid, Lumped, Analytic, FDM) and the board kind change nothing. The Environment box is collapsible and its state is remembered between sessions, a third way not to see them. | offscreen probe, `opened computed json: h_top vis=False ... h_side en=False` | The mode's tooltip and the user guide say that h top and h bottom are shown only with 'Typed by me'; h edges has its own tooltip with the greyed reason (`_side_enabled`). Test `test_the_h_boxes_say_why_they_are_hidden_or_greyed`. |
| 6 | Document, unverified number | The user guide said the new-board defaults lower "a bare plate by about 3 K", with no board named. | Measured (FVM, 1 mm cell) on the 50 x 50 x 10 mm copper plate, k 150 W/mK, h_bottom 400, 70 W in four 10 mm sources: 98.31 degC adiabatic top and sides, 96.60 with h_top 10, 96.95 with h_side 10, **95.30 with both (3.01 K)**; the same 3.01 K as the research folder `muzychka-case2-analytic` (route C). The defaults are `defaults.json` `new_board`: h_top 10, h_bottom 15, h_side 10, edges lose heat on (`model.new_problem`). | The guide now names that plate and its numbers and says the size depends on the board. |

## Checked and found right

* One edit is one undo step (the board edits keep the merge key `board`; the profile edits `profile<i>`).
* The Board dock reloads on every `changed` (undo, redo, open, import, Replace, Update, a refused edit, a new layer count), so its remembered values cannot go stale; a refused edit restores and reloads.
* Greyed boxes never write: the imported board's size, the edge coefficient with the edges unticked (ticking writes it, unticking writes None).
* A box showing a rounded value (copper 0.25 um shown 0.3, a thickness of 1e-4 mm shown 0.000) is never written unless edited.
* Large values do not widen the docks: Qt truncates the text of a spin box to 18 characters for its size hint; `tests/test_dock_layout.py` passes.
* Preferences: a saved value outside a box range is shown clamped (analytic modes 500 000 shown 100 000, h_top 2.5e9 shown 1e9) but **Save writes the stored value** (each box writes only its own key on its own edit). A limit of the display, not fixed here.
* The Stack-up table and the Properties form write per field; `fit_range` in their constructors is enough.

## Tests run (offscreen, on this branch with the fixes)

* `tests/test_dock_writeback.py` 14 passed (5 of the 6 new tests fail on the branch tip before the fixes).
* `test_dock_writeback, test_dock_layout, test_gui_boxes, test_single_layer, test_window_growth, test_enter_focus, test_shortcuts, test_tooltips, test_help, test_docs, test_license_header, test_version`: 876 passed, 2 skipped.
* The GUI tests that touch the changed widgets (background image, calculator, defaults, profile, import cell, inspector, laminate options, re-import, templates, theme, warning icons, profile face): 176 passed, 12 skipped.
* `tests/test_gui_stress.py`: 62 passed (11 min 26 s).
* `PCBT_FROZEN_CELLS=2 tests/regression`: 153 passed (no number moves).
* After the tooltip fix: `test_dock_writeback` (14), `test_tooltips`, `test_docs`, `test_help`, `test_dock_layout`, `test_license_header`: 815 passed.

## Open decisions for the maintainer

* **Undo restores the solver options.** `Document.set_options` says the options are not part of the undo history, but the undo snapshot holds them, so undoing a board edit also undoes a later cell or model change. The docks now show it; whether the undo should keep the current options (carry them over in `_restore`, as the package files are) is a decision.
* The Preferences boxes show a saved out-of-range value clamped (never written): widen them as the docks do, or leave it.
