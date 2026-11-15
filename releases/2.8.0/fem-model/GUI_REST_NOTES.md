# Notes: branch `fix/gui-review-rest` (branch C of `GUI_FIX_PLAN.md`)

Progress notes of the reviewer implementing branch C (not a report). Base: `development` at `b4097cc0` (branches A and B merged).

* Run feedback (A8 rest, A10, A11, A9 muted): status bar mirrors the line under Run (stage and seconds while busy, final line after), Stop in a red `stop` token, focus ring on the primary button, slim progress hidden when idle, status line two lines high; muted light 4.87:1. Commit ce5775be.
* FEM cap refusal (A6 rest): 'use a cell of about X mm or more' (checked accepted), FEM warning title 'The FEM (finite elements) will be left out'. Also fixed two stale CLI tests on development ('| fem |' became '| FEM |'). Commit fbaa735a.
* One dot painter (C20): `dots.dot_html` embeds the pixmap in rich text; the memory lines use it. Commit 24104688.
* Docks (C1, the leftovers): a scroll area never narrower than its content plus the vertical bar (`_FitWidth`); Elements header whole. The start-up sideways bar of the review was a first-paint state (gone after the first event cycles), not a user-visible defect.
* Ruler corner (C3), typography sweep (C17, `tests/test_typography.py` over the visible strings of gui/, help/ and the core modules that write messages, with `units.FORBIDDEN` and `units.ALLOWED`), × in sizes, ellipsis, 'Off', colour-map names, outline table notation, emissivity line, guide 'lumped network', Holes tooltip. 'Power Calculator' is kept as the proper name of the tool (in about 30 places and the docs): decision for the maintainer.
* Empty-board hint (C4); Open recent and the tab entries of the View menu (C5, C7); shortcut list test (C8). The tool-bar Open/Save/Undo/Redo (C6) were NOT added: no room at 1200 px (Run would go into the overflow).
* Import window (C9): parts counter in words, Tj max 0 reads 'none' ('no limit' cost 5 px of the Package column at 1100 px, a test).
* Compact plot tool bars (C11), empty states of every plot page (C12), failure box with what to do (C13), accessible names and the Properties tab order (C14, C15, `gui/a11y.py`), tooltip test extended to the Display popover and Preferences (C16).
* Stack-up page at 1200 x 800 (C2): `gui/adaptive.py` (the splitter of the Power profile page, shared), inner copper on its own line, 'Readable' Scale entry, elided note. Docstrings K/W (C21). Field borders at 3:1 NOT done: Fusion draws the edge of a field at 2.0:1 (light) and 1.1:1 (dark) and only a restyle of every input changes it (measured offscreen): a larger design.
* Documents: user guide (Quick start: hint and Open recent; section 8 status row: red Stop, seconds, final line, failure), CHANGELOG, `docs/versions.md`, `docs/decisions-log.md`, `docs/models.md` module map. Screenshots: `FULL_COLOUR` also keeps `results_summary*` unquantised (the warning dots).
* After the final look at the window: map titles by short name (the key upper-cased gave LUMPED, SOLID3D), the profile title saying when it plots the nearest cell centre, the all-layers title with the balance as a percentage (the pixel baseline of `tests/test_results_views.py` moved with it, field untouched), and the Power profile page that still scrolled sideways at 1200 x 800 (the 'Repeats every' row).

## Self-review against the plan (branch C and the leftovers of A and B)

| Item | State | Evidence |
| :-- | :-- | :-- |
| C1 dock widths, start-up | done | `_FitWidth`; `test_the_right_docks_never_scroll_sideways_at_their_narrowest` (fails without the fix); the start-up bar of the review was a first-paint state |
| C2 Stack-up texts and width | done | `gui/adaptive.py`; `test_the_stack_up_page_has_no_sideways_bar_at_1200_by_800` |
| C3 ruler corner | done | `test_the_ruler_corner_holds_only_the_unit` (fails without the fix) |
| C4 empty-board hint | done | `test_an_empty_board_shows_the_first_steps...` |
| C5 Open recent | done | `test_open_recent_lists_the_projects...` |
| C6 tool-bar Open/Save/Undo/Redo | NOT done | the 1200 px tool bar is full: Run would go to the overflow menu |
| C7 tab entries of View | done | `tests/test_shortcuts.py` |
| C8 keyboard list against the menus | done | `test_every_key_of_every_menu_is_in_the_keyboard_list` |
| C9 import window words, Tj max | done ('none', not 'no limit': width) | `test_the_import_parts_step_reads_in_words...` |
| C10 Holes tooltip | done | text only, no test |
| C11 compact plot tool bars | done | `test_the_plot_tool_bars_are_compact` |
| C12 empty states | done | `test_every_plot_page_says_what_to_do_before_the_first_run` |
| C13 failure box | done (cause and what to do in one text; no 'Show details' box: a modal instance would hang the tests that patch QMessageBox) | `test_a_failed_run_says_the_cause_and_what_to_do` |
| C14 tab order | done | `test_tab_goes_through_the_properties_fields_before_the_tool_bar` |
| C15 accessible names | done for the window, the calculator, the import window and Preferences; not checked with VoiceOver | `tests/test_accessibility_names.py` |
| C16 tooltip coverage | done (Display popover, Preferences added) | `tests/test_tooltips.py` |
| C17 typography sweep | done | `tests/test_typography.py` (its own self-test) |
| C18 CLI units | done (the sweep covers `cli.py`; the board line uses ×) | `tests/test_typography.py` |
| C19 pictures | done: 39 pictures of `docs/images` and 23 copies in `pcbthermal/help` regenerated; about 20 of them looked at one by one, the others are the same screens in the other theme or step | `examples/make_screenshots.py` (all five modes) |
| C20 one dot painter | done | `test_the_memory_lines_and_the_warning_rows_use_one_dot_painter` |
| C21 docstrings K/W | done | grep `degC/W` empty |
| A6 rest: FEM cap refusal with a cell, warning title | done | `test_a_fem_mesh_above_the_cap_says_which_cell_to_use...` |
| A8 rest: status bar | done: busy 'Calculating (N s): stage. Stop with Ctrl+.'; after a run the final line of the dock; 'Ready.' only when there is none | `test_the_status_bar_counts...`, `test_simulation_panel_groups.py` |
| A9 rest: muted 4.39 -> 4.87; `field_border` | muted done; field border NOT done (Fusion draws it, a restyle of every input) | `test_secondary_text_and_the_stop_button_read_in_both_themes` |
| A10 focus ring, A11 Stop red and slim bar | done | `test_the_run_button_shows_where_the_keyboard_is`, `test_the_run_button_turns_red_as_stop...` |
| A12 ellipsis, Off, colour maps | done; 'Power Calculator' kept as a proper name (decision) | `tests/test_typography.py` |
| B leftovers: 'Lumped' in the guide | done ('thermal network (LPTN)') | text |

Tests run on this branch (one pytest at a time, offscreen): the GUI set (`test_gui`, `test_gui_boxes`, `test_gui_profile`, the new tests, `test_docs`, `test_license_header`, `test_version`, `test_help`, `test_tooltips`, `test_shortcuts`, `test_typography`, `test_units_rule`) 950 passed; `test_gui_stress -k 'not random'` 62 passed; frozen numbers at 2 mm 170 passed; the import, profile, stack-up, results-views, FEM and robustness tests touched by the changes passed. The whole battery was not run (the tester runs it on the merge). Not verified: native macOS fonts, VoiceOver, HiDPI.
