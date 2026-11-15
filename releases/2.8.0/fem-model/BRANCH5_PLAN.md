# FEM branch 5 (`feature/fem-gui`): the window. Plan

**Status**: plan only, written while the whole battery was running (nothing was run, no GUI was launched). It is written from `DESIGN.md` 5.8, 6, 10 and 11, from `REVIEW_BRANCH4.md` section 6, `SURFACE_DECISIONS.md` and `MERGE_NOTES_FEM_SURFACE.md`, and from the code of the throwaway tree `tmp/merge-fem-surface` (commit `fd007cd1`: `feature/fem-model` and `feature/surface-always-both` merged). `development` does not hold that code yet: **every line number and name below was read on that tree, not on `development`; re-grep after the merge** (section 9).

## 1. Scope

In: the FEM as a checkbox of the Models box, exactly like the 3D solid; its memory verdict in the panel; its results in every steady view; the read-outs (column, surface, point) named in the window; tooltips, Preferences, user-guide words, stress scenarios, screenshots.

Out (other branches): the difference table/map and trust hints (branch 7, `feature/compare-differences`), the validation chapter and the 'Which model to use' chapter (branch 6), the transient (branch 8). No number of any model moves; the frozen numbers are untouched (no pending file, section 8).

Already done by branch 4 and not to be redone (read on the merged tree): `api.COMPARISON_MODELS` and `SKIPPABLE_MODELS` hold `fem`; `SolverOptions.fem_gap_elements` (6, 2 to 24) and `fem_refine` (2.0, 1 to 4) with their saving rule; `to_dict`/`from_dict` write `comparison_models` / `comparison_only` (so v2.7.1 opens the file); `results.MODEL_LABELS["fem"] = "FEM"` (so `tips.model_label`, the Results model combos, `plots.draw_comparison` and the profile combo already say FEM); `memory.check` and `memory.MODEL_LABELS` know `fem`; `checks.check_fem` is inside `check_input`, so the live checks of the window (`main_window.py` 1277 `check_input(..., live=True, ui="gui")` -> `solver_panel.set_checks`) already carry its warnings; `api._simulate` leaves a failing FEM out with a warning beside the other models; the surface arrays `T_surface`, `T_surface_mean`, `T_surface_flag` and `extras["t_max_surface_top/bottom"]` are filled by `fem.py`, so `results_view.surface_faces()` and the Layer box (`layerchoice.py`, `main_window.py` 1110) show the entries for the FEM without a change; `plots.plot_surface`, `cli.py` and the report already say 'resolved'.

## 2. How the 3D solid is exposed today (the pattern to copy; grep on the merged tree)

| Place | What it does for `solid3d` | FEM line |
| :-- | :-- | :-- |
| `gui/panels.py` `SimulationPanel.__init__` (about 1559 to 1570) | `self.cb` dict of QCheckBox, `tips` dict, one loop sets the tooltip and connects `toggled -> _apply`; `refresh` (1680 to 1695) ticks `k in o.models`; `_apply` writes `models` with `set_options` (at least one stays ticked) | add `"fem"` to `cb` and `tips` (the loop does the rest) |
| `panels.py` `verdicts` (1713), `_auto_cell` (1758) | `tuple(k for k in ("fvm", "fdm", "solid3d") if ...)` | add `"fem"` in both (one shared constant `GUARDED_MODELS` is better than two literals) |
| `panels.py` `_update_cells` (1725 to 1750) | `names` dict; one row per verdict ('N unknowns, about x of y GB; slow / above the memory limit, it will not run: use a cell of c mm'); blocks Run on a refusal **unless the model is `solid3d` and others are ticked** (line 1748) | `names["fem"] = "FEM"`; the skip rule becomes `v.model not in api.SKIPPABLE_MODELS` (the API's own tuple, so the window and the API cannot disagree) |
| `panels.py` `_update_availability` (1660 to 1680) | greys the controls of models not ticked (`base_tip` + 'Greyed: used only by ...') | the two FEM spin boxes (section 3.2), greyed unless `on("fem")` |
| `gui/preferences.py` 94 `MODELS = (...)`, 375 to 384 (checkboxes of the default models with `tips.model_label(m)`), 456 `_read_models` | the default-models list of the Solver page | add `"fem"` to `MODELS` (`defaults.default_options` filters unknown keys, so an older program is safe) |
| `gui/fieldscale.py` 167 `MODEL_SHORT` | title of the card of the map on the board; `main_window.py` 842 does `MODEL_SHORT.get(res.model, str(res.model))`: **a missing key prints the key `fem` in lower case** | add `"fem": "FEM"` |
| `gui/results_view.py` 338 | model combo from `sim.results` with `tips.model_label` | nothing |
| `gui/results_view.py` 730 | the part table's surface note 'The X model has no surface read-out (steady FVM and FDM only)' | the FEM fills the arrays, so a FEM row never reaches that branch except on an inner layer; the text is still wrong for `ref.model == "fem"` on an inner-layer part: test it, adjust the sentence (section 3.4) |
| `gui/animation.py` 54, `gui/profile_results.py` 81, `jobs.job_transient` | animation model combo lists FDM only; profile combo lists the models that ran | nothing (the FEM has no time model: `api` already writes 'steady state only' into `profile_error`) |
| `gui/help.py` 147 About text | lists the models | add 'finite elements' and pyamg (MIT) if branch 3 did not (check) |

There is no FEM key in `pcbthermal/data/defaults.json` and it must not be added (off by default, as `solid3d`).

## 3. Changes, file by file

### 3.1 The checkbox and its availability (`gui/panels.py`)

* Label `"Finite elements (FEM), comparison"` (the exact words of DESIGN decision 4 and of `tests/test_help.py`).
* **pyamg**: the design says 'greyed without pyamg'; the merged model says otherwise: a mesh up to `femcore.FEM_DIRECT_MAX` (30 000 unknowns) solves without pyamg, a bigger one raises `FemUnavailable` (skipped). **Decision for the maintainer (section 10, item 1)**: (a) never grey the box, and show the reason in the verdict row and the live check (what the code does today, recommended: a small board works without pyamg); (b) grey it when `femcore.available()` is false (the design text, simpler to explain, but it forbids a working case). Plan assumes (a); (b) costs 6 lines in `refresh` (`setEnabled`, tooltip suffix 'needs the package pyamg (pip install pyamg)').
* **Verdict rows**: the extra reason for the FEM is 'above 30 000 unknowns and pyamg is missing': `memory.check` does not know it (it is in `fem.solve_steady` and `checks.check_fem`). Add to `_update_cells` one line after the verdict row when `fem` is ticked and `femmesh.unknowns(problem, cell)[0] > femcore.FEM_DIRECT_MAX and not femcore.available()`: 'FEM: N unknowns, above what the direct solver takes; needs the package pyamg: it will be left out' in the `refuse` colour, **without** blocking Run (the API skips it). The count is the exact one of `check_fem`; reuse it through a small public function `checks.fem_needs_pyamg(problem, cell)` returning `(n, bool)` (a refactor of three lines of `check_fem`; `checks.py` is core, allowed on the feature branch). A mesh that cannot be built (`ValueError` from `femmesh.unknowns`: slanted outline, too many break lines) appears already as a live-check ALERT; the verdict rows must not raise (the existing `except ValueError` of `_update_cells` shows the message and **blocks Run**: for the FEM this is wrong when other models are ticked: the FEM is skipped, not the run; catch it per model).
* Skip rule of Run: refusal of the FEM blocks Run only when it is the only model ticked (same as 3D solid, from `api.SKIPPABLE_MODELS`).

### 3.2 The two mesh options (`gui/panels.py`, Settings box, after the laminate rows 1601 to 1621)

* `self.fem_gap = QSpinBox` (2 to 24, 6) 'FEM elements across a gap' and `self.fem_ref = _spin(1, 4, 2.0, 1, 0.5, "")` 'FEM refinement'; tooltips with meaning, unit, range, default, what they cost (each element across a gap adds unknowns; refinement is the ratio of the run cell to the fine element near parts and via patches; 'six or twelve elements across the gap give the same number to 0.1 mK' from the review; the default is enough).
* Written like the laminate boxes: add to the `for box, key in (...)` list of `_apply` (only an edited box is written: keep that rule, the guard against writing a shown-rounded value back); `_put` in `refresh`; greyed by `_update_availability` unless `fem` is ticked. They change the unknown count, so the verdict row follows (`memory.check(..., fem_params=o.fem_params())` is what `api` passes; `verdicts()` must pass `fem_params=self.doc.options.fem_params()` exactly as it passes `laminate_params`: check the name of the keyword in `memory.check`, `test_the_fem_options_change_the_count_that_the_guard_sees` is the existing proof).
* Preferences: the laminate numbers are **not** in Preferences (grep: no `laminate` in `preferences.py`), so by precedent the two FEM numbers are not either; only the model tick is (DESIGN 5.8 said 'the Solver page gains the two FEM options': **decision, item 3**). Plan: precedent (no).

### 3.3 Results, card, combos (`gui/fieldscale.py`, `gui/results_view.py`, `gui/canvas.py`)

* `MODEL_SHORT["fem"] = "FEM"` (the title of the board card; the model menu of the card, key M, lists the models of the result through the same dict: verify on the code that it iterates `sim.results`, not `MODEL_SHORT`).
* Temperature, Gradients, Models tab, profile combo: nothing (generic) but the **tests walk them** (section 6).
* Models tab bar chart (`plots.draw_comparison`) and summary table: generic; check the colour/position of six bars and the table height (the note at `results_view.py` 94 about the fixed 170 px ceiling: six rows at most; verify no scroll bar).
* Reference: `sim.reference` when the FEM is the **only** model ticked (the file saved with `comparison_only`): the Results must open on it, the `fvm`-preferring `findData("fvm")` falls back to index 0 (read: `results_view.py` 342); test that a FEM-only run walks every tab (Gradients and the summary read `sim.reference`).

### 3.4 Read-outs (column, surface, point) in words

* Column: the default of every map ('column mean' in the title, `plots.COLUMN_LABEL`): nothing to change.
* Surface: the Layer-box entries come from `surface_faces()`; their tooltip `tips.SURFACE_ENTRY_TIP` says 'an estimate ... Always available for the FVM and the FDM': **edit**: 'an estimate for the FVM and FDM, resolved by the elements for the FEM'. The Components table header `Max °C (surface, estimate)` and `tips.SURFACE_MAX_TIP`: say 'estimate (FVM, FDM) or resolved (FEM)'; the header is a fixed two-line column of a narrow table (the decision of `SURFACE_DECISIONS` 5 and the cut-off screenshot): do **not** lengthen the header; put the FEM wording in the tooltip and make the header text depend on `ref.model` only if it fits (`Max °C\n(surface,\nresolved)`; the same three lines), else leave 'estimate' and say it in the tooltip.
* `results_view.py` 730 note: for `ref.model == "fem"` on a part on an inner layer say the inner-layer sentence, never 'no surface read-out'.
* Metal blocks: the FEM gives **no surface for a block** (REVIEW_BRANCH4 section 6: the block result is the mean through the block). The part table and the block table already show that mean; the tooltip of the FEM checkbox says it (3.5). `block_faces()` reads `block_*_max` extras, which the FEM fills (`fem.py` 360): the Layer box entry 'Metal block (top)' shows the block mean for the FEM; test.
* Point read-out (hottest node): `arrays["T_point"]` (2, ny, nx) and `extras["t_max_point"]` are **not shown anywhere in the window**. Minimal, no new control (the decision of `SURFACE_DECISIONS` 3 and 6 is that a read-out is a view, not a mode): (1) the Summary text (`results_view` line ~533 `report` box) already carries `report_text`, which prints the point line (check on the merged tree; add it to `api.report_text` if the surface merge dropped it); (2) the Components table tooltip of the FEM column gets 'hottest node under the part: x degC' (one more sentence in the existing per-row `notes`, from `arrays["T_point"]` under the part's cells through `analysis.surface_stats` or a new `analysis.point_stats`, core); (3) **no** map of `T_point` in 5 (**decision, item 4**: offer it as the Layer-box entries 'Point (top/bottom)'? It would be a third family of entries, a view that changes nothing; recommended: not in 2.8.0).

### 3.5 Tooltips (`gui/panels.py` `tips` dict; `gui/tips.py`; `tests/test_tooltips.py`)

Checkbox tooltip (replaces DESIGN's 'within about 0.2 %', which the review found false as a statement about the FVM): *'The board as a 3D solid of finite elements (hexahedra through every copper layer and gap, several through thick copper, hollow vias, the film on the real faces). Steady state only. On ordinary boards it reads 0.4 to 0.9 % below the FVM at the same cell, and most of that gap is the finite volumes' own error (the elements converge from below, the volumes from above, to the same value at 0.06 %). Its surface read-out of thick copper is resolved, not estimated (case 2 of Muzychka, Culham and Yovanovich: 0.02 to 0.05 K below the paper). A metal block is meshed through its thickness but reported as its mean: no surface of a block. Imported copper is read as an element mean (no better than the 3D solid). Slower than the 3D solid; skipped above the memory limit or when a large mesh needs the package pyamg.'* Numbers: `REVIEW_BRANCH4.md` section 3 (printed by `study_review_branch4.py`); the 0.2 % of the design is not used. Check the length against the other tips (the 3D solid's is two lines; if too long, move the second half to the user guide and keep 'see the guide: Finite elements').

The two spin boxes, the entry tip (3.4), the FEM column wording, the verdict row: each gets a tooltip or uses one above. `test_tooltips.py` needs no exemption (a checkbox is not a command button).

### 3.6 Progress and cancel (`jobs.py`, `main_window.py`)

`jobs.job_simulate` calls `api.simulate(progress=...)`, which calls progress(`Solving FEM`, k/n) before every model; the FEM has no inner progress callback to the window (`fem.py` signature: `cancel` only; `REVIEW_BRANCH4` 'Cancel: the application cancels by stopping the job process'). **Nothing to change in `jobs.py`**; the window plan: (a) the progress line says 'Solving FEM' (check it is not cut by `model_label`: `api` writes `name`; verify what `name` is for fem: key or label); (b) a test that Cancel during a FEM run stops the process and leaves no worker (as the existing cancel stress test does for the 3D solid); (c) a FEM-only run on a large board is a long call with no moving bar: say 'assembly and solve, this can take minutes' in the status text through the existing `progress(message, fraction)` (one extra message from `api` before `fem.solve_steady`, core change of one line, allowed). Whether to add inner progress ('mesh', 'assembly', 'solve', DESIGN 5.5) is **decision, item 5**: DESIGN promised it; branch 4 did not do it (read: not in the notes); cost S (a callback argument through `fem.solve_steady`, `femcore` between chunks).

### 3.7 Live check warnings

Nothing new in the code (`check_fem` is in `check_input`). To do: verify in the window that the three texts (cannot be built, needs pyamg, imported copper, part below the mesh) reach `set_checks` with the control name through `uicontext` (`ui="gui"`): the texts quote 'the cell ({cell_where()})': check `cell_where()` returns the window's name when `ui="gui"`.

### 3.8 Project load/save, files, export

* `comparison_models` round trip is done in `SolverOptions`; GUI test: tick FEM only, save, reopen (the Simulation panel shows only FEM ticked; `doc.options.models == ("fem",)`), and tick FVM+FEM.
* The window's **File > Export results to a folder** (`main_window.export_results`, 1412) calls `sim.save(d, plots=True, view=..., cmap=...)` with no `surface_files`: the surface CSV of the FEM and of the FVM has **no GUI path** (`SURFACE_DECISIONS` 6: open item). Not in this branch unless the maintainer wants it (**item 6**: recommended, a third checkbox is a new control; the lighter way is the menu item 'Export surface (CSV)...' calling `sim.save(surface_files=True)` into a folder; M effort 0.5 day with test).
* A project opened with an older version: covered by `PCBT_COMPAT_V271` (done in branch 4); GUI test not needed.

### 3.9 Help, guide, shortcuts, About

* `pcbthermal/help/index.html`: the paragraph `id="fem"` and the surface chapter already mention the FEM (read: line 250, 293 to 310). Add: the window controls (the checkbox, the two spin boxes by their exact labels, the verdict row words, the pyamg sentence), the 'Models' table column for the FEM (the table at line 241 has five columns: add a sixth, or one sentence under it, whichever the page layout allows), the Layer-entry note; **screenshots**: `results_surface.png` (the map title, caption 'FVM' unchanged), a new `simulation_fem.png` of the Simulation panel with the FEM ticked and its verdict row, optional `results_surface_fem.png` for the thick-plate case. Regenerate through `examples/make_screenshots.py` (it asserts neutral paths); the script is edited to tick the FEM on one scene (**needs a quiet machine**: it launches the GUI and a FEM solve).
* `tests/test_help.py` words: 'Finite elements (FEM), comparison', 'elements across a gap' (or the final label), 'FEM refinement', 'needs the package pyamg', 'column mean'.
* `SHORTCUTS_HTML`: no new shortcut: unchanged. About box (`gui/help.py` 147): the sentence lists the models; add 'finite elements'.
* `docs/models.md` (the model table), `docs/versions.md` (branch 5 entry), `CHANGELOG.md` (Unreleased, one bullet), `docs/decisions-log.md` (the decisions of section 10), `CLAUDE.md` section 15 state: all by the maintainer in the branch's last commit (CLAUDE.md 10).

## 4. Tests to write

Where: `tests/test_fem_gui.py` (new; the offscreen GUI, helpers `load`, `run`, `walk_results` imported from `tests/test_gui_stress.py` as that file does), plus edits of existing tests.

| Test | What it proves |
| :-- | :-- |
| `test_the_fem_checkbox_is_off_by_default_and_exposed_like_the_3d_solid` | unticked on a new project; tooltip words; the shared tuple of guarded models includes `fem` |
| `test_every_tuple_that_lists_solid3d_lists_fem` (the grep test of DESIGN 10.2, `tests/test_model_lists.py`) | parses `pcbthermal/gui/*.py`, `api.py`, `cli.py`, `memory.py`, `checks.py`, `results.py` for tuples/dicts containing `"solid3d"` and requires `"fem"` in the same one (an allowlist for the deliberate exceptions: `TIME_MODELS`, the animation combo, laminate groups) |
| `test_the_panel_shows_the_fem_verdict_and_the_skip_rule` | a big board: the row says 'FEM: N unknowns ... above the memory limit, it will not run: use a cell of c mm'; Run enabled when FVM is also ticked, disabled when FEM alone |
| `test_the_fem_without_pyamg_is_said_not_blocked` (monkeypatch `femcore.available` to False, big mesh) | the extra row, Run enabled with other models, FEM-alone run fails with the text |
| `test_the_two_fem_options_change_the_count_and_are_greyed_without_the_fem` | spin box -> `doc.options.fem_*`; the verdict count changes; greyed when unticked; **only an edited box is written** (open a file with `fem_refine` 1.25: the box shows 1.3 or 1.2, unticking another model does not rewrite 1.25) |
| `test_fem_only_and_fem_with_fvm_save_and_reopen` | save/load through `Document`; `comparison_models` in the JSON; the v2.7.1 shape is covered by branch 4's test |
| `test_a_fem_run_walks_every_results_tab` | FVM+FEM and FEM alone on `example_board`: Temperature (model combo lists FEM), the Layer box entries (surface entries present, 'column mean' in the title), Gradients, Models tab (six rows, no scroll bar), Components table (surface column filled, tooltip says resolved), the card (title 'FEM'), animation and profile tabs say 'steady state only' |
| `test_the_fem_surface_entries_and_the_thick_plate` | case-2 plate (50 x 50 mm, 10 mm copper) with FEM: the Layer box 'Surface (top)' map max equals `res.extras["t_max_surface_top"]`; the title says 'resolved'; column and surface differ by 2 to 5 K |
| `test_fem_cancel_leaves_no_worker` | start a FEM run, press cancel; `worker` stopped, no result, next run works |
| `test_fem_refusals_do_not_stop_the_other_models` | a slanted-outline board with FVM+FEM: live warning ALERT, the run answers with FVM, the warning list says the FEM was left out |
| edits | `tests/test_gui_stress.py`: `ALL_MODELS` gets `"fem"` (line 33; this makes every walking test run it: check the time budget, keep the boards small); add `("fem",)` and `("fvm", "fem")` to the model loops at 320 and 1365; a scenario for the new spin boxes inside the random-actions stress (every new control is part of it); `tests/test_help.py` words; `tests/test_tooltips.py` (nothing if the controls have tips); `tests/test_preferences_layout.py` (the new tick in the Solver page) |

New stress scenarios required by CLAUDE.md 6 ('every new model, element type, dialog or background job'): the FEM as a model (FEM alone and with the others, through `walk_results`), its background job (cancel), its two controls (random edits while ticked and unticked).

Time budget: the gui stress file already runs minutes; `ALL_MODELS` with the FEM adds one FEM solve per run at 2 mm cells (about 1 to 4 s each on the small boards, direct solve) times about 20 runs: **plan 2 to 5 minutes more** (to be measured; keep the FEM out of `ALL_MODELS` and add it to a smaller set if above 5).

## 5. Order of commits (each green on `tests/test_fem_gui.py`, `test_tooltips.py`, `test_help.py`, `test_docs.py`, `test_model_lists.py` before the next; the whole battery once, at the end)

1. `MODEL_SHORT`, `Preferences.MODELS`, `GUARDED_MODELS` constant, the checkbox and tooltip, `names`, the skip rule from `api.SKIPPABLE_MODELS`; `test_model_lists.py`; the first three tests of section 4.
2. The verdict rows (pyamg row, per-model catch of `ValueError`), `checks.fem_needs_pyamg`; tests.
3. The two spin boxes, `_apply` / `_put` / greying; tests (including the only-edited-box rule).
4. Read-outs in words: `tips.SURFACE_ENTRY_TIP`, `SURFACE_MAX_TIP`, header, the inner-layer note, point sentence in the report/tooltip; the thick-plate GUI test.
5. Results walk with the FEM, FEM-only reference, six-row Models tab; cancel and refusal tests; `test_gui_stress.py` edits.
6. Guide, About, screenshots (a quiet machine), `docs/` of the maintainer, CHANGELOG, decisions log; `tests/test_help.py`.
7. Reviewer: the checklist `GUI_TEST_CHECKLIST.md` run by hand by the maintainer is the acceptance test; the reviewer repeats it offscreen where possible.

## 6. Frozen-number impact

None expected: no model, no solver, no option default changes; `fem_gap_elements` and `fem_refine` keep their defaults and are not written unless changed. A check: `PCBT_FROZEN_CELLS=2,1,0.5 pytest tests/regression` (1 to 2 minutes, after the battery is quiet) and a byte comparison of a saved example project before and after (the `SURFACE_ALWAYS` method).

## 7. Effort and risks

Effort: **M, 4 to 6 agent days** (code 2, tests and stress 2, guide and screenshots 1, review rounds 1 to 2), as DESIGN's size M for branch 5; the unknown part is the stress file's run time and the screenshot script. Risks:

1. **A hard-coded list missed** (a `"fdm", "solid3d"` tuple somewhere): the grep test is the guard; known extra places: `results_view.py` 730, `fieldscale.MODEL_SHORT`, `panels.py` 1713, 1725, 1748, 1758.
2. **The verdict code raising or blocking for the FEM** when a mesh cannot be built (a slanted outline): the existing `except ValueError` blocks Run for all models; fixed per model in step 2.
3. **Stress run time** with `fem` in `ALL_MODELS`.
4. **Surface column wording** on a table already cut once (keep the header as is).
5. **Screenshots** need a GUI and a FEM solve: wait for a quiet machine (rule of the standing orders).
6. **The merge is not in `development`**: this plan is written against `tmp/merge-fem-surface`; the line numbers move.

## 8. Not verified here

Nothing was run (no pytest, no GUI). Not read: `gui/main_window.py` outside the lines quoted, `results_view.py` outside 330 to 375 and 700 to 745, `plots.draw_comparison`, the card model menu code, `tests/test_gui_stress.py` outside the lines quoted; whether `api` names the progress message with the key or the label; whether `Simulation.reference` handles a FEM-only result (read of `results.py` was partial); the exact keyword of `memory.check` for the FEM options in the window call; the run time of the stress file with the FEM.

## 9. After the merge, before the first line of code

`git grep -n "solid3d" -- pcbthermal tests | wc -l` and the list again; confirm `fd007cd1` content is what `development` holds; re-read `MERGE_NOTES_FEM_SURFACE.md` for conflicts that moved a line quoted here; diff the quoted functions against this plan.

## 10. Decisions left to the maintainer

1. **pyamg and the checkbox**: never grey it (small meshes work without pyamg; the reason appears in the verdict row; recommended), or grey it without pyamg as the design says.
2. **Headline wording of the FEM tooltip**: the measured '0.4 to 0.9 % below the FVM (mostly the volumes' error)' instead of the design's '0.2 %' (recommended; it is what the review measured).
3. **FEM mesh options in Preferences**: no, by the precedent of the laminate numbers (recommended); the design said yes.
4. **Hottest node (`T_point`)**: in the report and a tooltip only (recommended), or also as Layer-box entries 'Point (top/bottom)'.
5. **Progress inside the FEM** (mesh, assembly, solve), promised by DESIGN 5.5 and not built: add now (S) or leave 'Solving FEM' with a 'can take minutes' note (recommended for 2.8.0).
6. **Surface CSV in the window**: the export menu has no way to write it (only `run --surface-files`): add the menu item now (0.5 day) or leave it open.
7. Whether the FEM joins `ALL_MODELS` of the stress file (cost: minutes per battery) or a smaller set.
