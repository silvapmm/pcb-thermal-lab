# Surface always: progress notes (branch feature/surface-always-both)

Done (code): thickness.py gates removed (THICK_MIN_M, SHOW_*, significant); api report lines always, each face against the column of its layer;
api.save(surface_files=) + plots.plot_surface + CLI --surface-files + CLI surface line; plots column labels (COLUMN_LABEL, 'column mean' titles);
results_view: Layer entries always, one surface column with cell tooltips (difference in K and %), 'n/a' with reason.
To do: tests (invert/add), docs (guide, tips, models, theory, validation, README, CHANGELOG, versions, decisions-log, SURFACE_DECISIONS.md), screenshots, runs.

Update: tests written (test_thickness, test_gui_stress, test_help words), docs written (guide, tips, models 4b, theory 1.2c, validation 55.6 update, README, CHANGELOG, versions, decisions-log, SURFACE_DECISIONS.md).
Measured: thin copper surface minus column max under the part +0.4 to +3.2 mK on 20 boards; hatched_copper +1.2153 K and drawn_ell +3.6458 K board-level (part rows +0.000 K); face-flux balance 3e-10 W; arrays 272 kB, run 0.27 s.
Running: GUI tests in the background (not the random user actions test, ~7 min each, skipped). To do: frozen numbers, screenshots, commits.

Results: GUI tests (help, boxes, profile, gui, results_views, stress without random_user_actions) 125 passed after three test fixes (help words, top-path column index, 'fields' picture hash c86e8a40 -> c29d267c); frozen numbers 317 passed at 2, 1, 0.5 mm; screenshots regenerated and looked at.
Not run: test_random_user_actions (3 cases, ~7 min each), the whole battery.
