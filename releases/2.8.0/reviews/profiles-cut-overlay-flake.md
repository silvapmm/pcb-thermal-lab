# Review of `fix/profiles-cut-overlay-flake`

**Verdict: GO** for the merge into `development` (test-only change; the program is not touched), with the corrections below on the branch and the whole battery left to the tester.

## The claim

`tests/test_map_markers_and_cut_locator.py::test_profiles_tab_never_scrolls_sideways_and_keeps_its_cut_picture[size0]` failed in 2 of the last 3 whole batteries (`_controls2.indexOf(cut_overlay) >= 0` gave -1) and passed alone. The author's cause: the tests that build `MainWindow(doc)` without `settings` use the real store `QSettings("PMS Labs", "PCB Thermal Lab")`; every closed window saves its geometry, `window_state` and `dock_sizes` there and the next window restores them. The fix: an autouse fixture in `tests/conftest.py` that redirects that store to a private `.ini` per test. The author could not reproduce the failure.

## The cause, reproduced

* The real store of this machine (`~/Library/Preferences/com.pms-labs.PCB Thermal Lab.plist`, read only, never edited) held the keys the battery writes: `geometry`, `window_state`, `dock_sizes`, `theme = light` and eleven `boxes/*` states, ten of them collapsed. So the battery was also writing into the maintainer's own preferences of the application.
* A pytest plugin kept outside the repository stood for the real store: one persistent scratch `.ini` shared by every window built without settings, seeded from a window whose arrangement was saved and then closed (the real store itself was never used).
* On `development` (ec5f991f), seed with **one side dock closed** (left or right), both closed, or the right docks floating: `[size0]` fails every time with exactly the battery message `assert -1 >= 0`. The docks being closed, the Profiles page at 900 px is 554 px wide, the controls fit on one line and the box rightly stays inline: the test's premise ("both docks open") was broken by the restored state, not the layout.
* Seed with **wide docks** (520 and 560 px saved): `[size0]` failed 2 of 3 runs on the horizontal scroll bar (a different assertion): the stale sizes are replaced by the defaults only after about 0.25 to 0.5 s, and the test looks at 0.2 s.
* Seed with a copy of the present real store (docks open, default widths): passes. That is why the test passed alone: whether it fails depends on what the previous window of the battery left (the random-action stress test and the shortcut tests toggle the docks).

## Is the program at fault?

No. The real MainWindow offscreen, seeded store, Results - Profiles, both themes, 900 x 700 and 1280 x 800, read at 0.2, 0.5 and 1.5 s:

| Saved arrangement | Tab width at 900 / 1280 px | Horizontal scroll | Cut overlay line | Controls clipped |
| :-- | :-- | :-- | :-- | :-- |
| docks closed (one side or both) | 554 / 934 | none | 1 (fits) | none |
| the real store's arrangement | 248 / 628 | none | 2 / 1 | none |
| wide docks (stale sizes) | 192 at 0.2 s, then 228 / 608 | for about 0.25 s, then none | 2, then 2 / 1 | none |

`_place_cut_overlay` follows the width of the tab, which is right; the brief scroll bar after a restore of stale wide docks is a transient of the existing restore (the 250 ms re-check of `_schedule_dock_minimums`), offscreen only, not seen on a real display: a stated limit, not fixed here.

## Is the redirect safe?

* Only `pcbthermal.gui.main_window.QSettings` is patched (the name the module uses at line 193, the only place of `pcbthermal/` that builds the default store); `QSettings` itself, other modules and every caller that passes a path or a format keep their meaning. The program has no other `QSettings(...)` call (`grep -rn "QSettings(" pcbthermal/`); the package size and the Gerber limit are in `user_defaults.json`, already private per test (`_private_config_folder`); `examples/make_screenshots.py` passes its own settings.
* The private file is per test (`tmp_path`) and empty at the start; two windows of the same test share it, so persistence between windows is still exercised. Tests that pass their own `settings` are untouched. The app code path (`QSettings(org, app)`, native format) is unchanged.

## Defects found and fixed on the branch

1. **The box states leaked between tests.** `gui/boxes.py` keeps a module-level store bound by the last MainWindow (`boxes.set_store`); after the redirect it pointed at the private file of an earlier test (before it, the real store), so a panel built alone in a later test read the box states of another test. The fixture now resets `boxes._settings` and `boxes._memory` per test.
2. **The guard test did not test the behaviour.** It checked only the name of the file. It now also checks that the store is empty at the start of the test, that it is not the native store of the machine, and that two windows of one test share it (the arrangement saved by the first reaches the second). Run without the fixture (`--noconftest` with the scratch store seeded with a closed dock), it fails, and so do both cases of the Profiles test; with the fixture all pass.
3. **The Profiles test now states its premise.** It asserts that both side docks are open and docked before the layout checks, so a restored arrangement would fail with a plain message instead of `-1 >= 0`.

## Tests run on the branch

* `test_map_markers_and_cut_locator.py`, `test_dock_layout.py`, `test_enter_focus.py`, `test_gui_boxes.py`, `test_shortcuts.py`, `test_single_layer.py`, `test_window_growth.py`, `test_docs.py`, `test_license_header.py`, `test_version.py`: 867 passed, 2 skipped (82.6 s).
* `test_gui_stress.py` (whole file, once): 61 passed (604.5 s).

## Not verified

* A real macOS display (offscreen only); the whole battery (the tester's).
* The exact earlier test that left the closed dock in the battery runs that failed (the mechanism is reproduced deterministically; the culprit is one of the tests that toggle the docks and close their window).
* The maintainer's real store still holds the theme `light` and the collapsed boxes written by earlier batteries: the maintainer may reset them in the application (or leave them); nothing here touches them.
