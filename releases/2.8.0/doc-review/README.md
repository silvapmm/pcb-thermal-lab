# Documentation review of 2.8.0 (step 6b of the release gate)

Branch `docs/doc-review-280` from `development` feb64245, with `release/2.8.0-lumped-shifts` (489f9c35) and `docs/theory-280-review` (a0da1588, GO; its edits of `docs/theory.md`, `research/theory` and the module map of `docs/models.md` kept) merged in. Reviewer. Checklist: `releases/2.8.0/DOC_REVIEW_CHECKLIST.md`. Light work only: one CLI run of the example board, a JSON-only script, the document tests; no solver study, no screenshot regeneration (see B).

## Verdict

**GO for the documentation of 2.8.0**, on these conditions, all of which belong to the release commit or to steps that come after this review:

1. At the bump: the `[2.8.0] - <date>` heading of `CHANGELOG.md`, the README version badge and the line '2.8.0 (in preparation, not released)', the summary at the top of `docs/versions.md` and the heading 'Unreleased (2.8.0, in progress)', `CLAUDE.md` section 15.
2. The tests badge of the README and `CLAUDE.md` section 14 quote the last whole battery (4013 passed); the battery of the final tree (`RELEASE_GATE.md` step 5) replaces both numbers.
3. After the refreeze: the frozen record count (347 today; the three `drawn_*` boards and the FEM records change it) in `CLAUDE.md`, `docs/versions.md`; `WHAT_MOVED.md` section 6 says its 2.8.0 numbers are the pending files until then.
4. Part A of the reproduction pass and its totals README were not available: `WHAT_MOVED.md` 4 quotes parts B and C and `LUMPED_SHIFTS_REVIEW.md` only.

## A. Documents

| # | Document | Checked | Changed | Stale on purpose |
| --: | :-- | :-- | :-- | :-- |
| 1 | `README.md` | features, interface, which model, install, usage (CLI run of the example board: FVM 85.47, LPTN 86.91, Analytic 84.80 °C, the same as `results_summary.png`), versions list, licence table (pyamg MIT present), image links | tests badge 3748 -> 4013 (last whole battery); stack-up and metal blocks 'in all five models' -> every model (the FEM reads the per-gap stack-up and blocks: `femmesh.py`); FEM 'steady state only in 2.8.0'; memory guard names the FEM; pip comment names pyamg; the warning rows now have a dot and the element label; new bullet 'Interface of 2.8.0'; line '2.8.0 (in preparation)' with the link to `WHAT_MOVED.md` | version badge 2.7.1 (until the bump) |
| 2 | `pcbthermal/help/index.html` | the FEM chapter against the code (`api.TIME_MODELS`, `gui/animation.py`), no 'Lumped' left in the guide, links (`tests/test_help.py` passes) | **wrong statement corrected**: 'the animation and the profile tabs say *steady state only*' (no such text exists): the Animation offers FVM, FDM, Analytic and the Power profile runs on the first ticked time model, so a ticked FEM is left out; transient planned for 2.9.0 | - |
| 3 | `pcbthermal/help/calculator.html` | JEDEC row: 31.9 K/W and power +1.8 % at 0.5 mm, the indication wording; the no-via row is not quoted | none | - |
| 4 | `docs/theory.md` | not reviewed here (the theory review, GO, on `docs/theory-280-review`); checked only that nothing here edits it | none | - |
| 5 | `docs/models.md` | sections 2, 2.5, 2.8, 4b, the module map | 'The five models' -> six; 'Which model for which job' names the FEM and the surface read-out; 2.8 says what the window does with the FEM in time runs; `fem.py` and `gui/spinfit.py` added to the map (the theory review's lines kept at the merge) | - |
| 6 | `docs/validation.md` | head ('Which table is current'), 3, 4.1, 51, 53, 55.6 | 4.1 note: 'moved from +0.6 %' -> **+0.3 %** (PART-C; the +0.6 % is the largest of the plain boards), with the reason of the +3.2 %; head: a bullet to `WHAT_MOVED.md`, and one that says the program FEM has no section of its own, its checks are in theory 4a, the CHANGELOG and the reviews, and **56 and 57 are reserved for the 2.9.0 campaign, not written** | the superseded tables listed by its head |
| 7 | `docs/calculators.md` | 2.1 after `release/2.8.0-lumped-shifts`: 83.5 K/W (converged), the reason, 74.6 on 2.7.x | none | - |
| 8 | `docs/versions.md` | 2.8.0 chapter (each bullet has its module and test), 'How each version was tested' (top entry 4013 passed), 'Planned' | 2.8.0 chapter links `WHAT_MOVED.md` and the gate; 'Planned' starts with 'Planned: 2.9.0' (pointer to `releases/2.9.0/PLAN.md`); the finished 2.7.0 list replaced by a closing note; 18 rows marked DONE and two paragraphs of done work removed (one quoted the old '-8 % to +2 %'); the FEM order paragraph says what is done and what the maintainer moved to 2.9.0 | the older chapters 'After 2.6.0', 'Ideas', 'Deferred' (not re-read item by item) |
| 9 | `docs/version-comparison.md` | ends at v2.7.0, 17 boards | an italic note: stale until the refreeze, where the 2.8.0 shifts are, how to regenerate (`regen_version_comparison.sh` with the v2.8.0 label and `version_notes.json`); its tests pass | the body (generated) |
| 10 | `docs/research.md`, `docs/decisions-log.md` | `research.md` is the empty template; the log has the 2026-11-15 scope decision and the GUI decisions | one entry for this review | - |
| 11 | `CHANGELOG.md` | Unreleased against the code and the reviews: Added, Changed, Fixed, Tests, Docs; every entry says whether a number moves | a summary at the top ('2.8.0 in short') with the measured shifts (M1: median 2e-5 K, at most 0.040 K, 0.93 K on a 10 mm plate, 0.7 K on a 6 mm stainless block; M2: JEDEC without vias 74.6 -> 83.5 K/W; M3: up to +14.9 K on part rows, board maximum -3.1 to +3.1 %, +7.1 % on an isolated 10 mm part; M4; the additions) and the link to `WHAT_MOVED.md`; FEM 'steady state only'; four in-release stale phrases ('not selectable yet', 'the checkbox is a later branch', 'pyamg not yet in requirements.txt') | the entries of each branch, kept as written by their branches |
| 12 | `CLAUDE.md` | sections 1, 11, 14, 15, size | 11: the FEM ships **steady** in 2.8.0 (it said steady and transient: the maintainer's decision of 2026-11-15 moved the transient to 2.9.0); 14: the battery of the last merge; 15: 'about to release 2.8.0' with the steps left and what moved to 2.9.0; three trims of history (48.4 to 48.0 KB) | **48 KB against the 40 KB of section 16**: what is left is rules (sections 6, 9, 12 are 22 KB); reaching 40 KB means moving rules out (maintainer's decision) |
| 13 | `research/README.md`, `research/REVIEW.md`, `research/ROADMAP.md` | one row per folder | `drawn-ell-fvm-fdm` (merged, answered by the reviewer) was missing from the index and the register: added | the folders whose README numbers shifted in the reproduction pass (part C 1: `lumped-zones-adoption` is stale against M3; the register update is the tester's, with the totals) |
| 14 | `releases/README.md` | the 2.8.0 rows | added: the gate and its checklists, `WHAT_MOVED.md`, `reproduction/`, `fem-model/`, `theory-review/`, `doc-review/`, plan, opinions, simplify, `2.9.0/PLAN.md` | - |
| 15 | Tooltips | `tests/test_tooltips.py` passes | none | - |
| 16 | Keyboard list | `tests/test_shortcuts.py` passes; `Ctrl+F` filter, `Ctrl+.` Stop calculation, `Ctrl+D` present in `main_window.py` | none | - |
| 17 | About box | `tests/test_help.py`, pyamg sentence present in `gui/help.py` | none | version 2.7.1 until the bump |
| 18 | `tools/ocr/README.md`, `research/theory/BIBLIOGRAPHY.md` | `tests/test_third_party_text.py`, `research/theory/tests` pass | none | - |
| 19 | `releases/2.8.0/*` of the gate | `REFREEZE_PLAN.md` 2 and `RELEASE_GATE.md` against the pending files | M3 band: 'board maximum -0.5 to +3.1 %' is the first link alone; with the part read-out the frozen boards move **-3.1 to +3.1 %** (`part_top_path` -2.7 to -3.1 %): both files corrected | - |
| new | `releases/2.8.0/WHAT_MOVED.md`, `reproduction/scripts/what_moved.py` | - | **new**: the comparison with the previous boards asked by the maintainer (section below) | - |
| new | `releases/2.9.0/PLAN.md` | - | e13: the upper-side flag of the surface uses sqrt(A) of the part, so a 2 x 20 mm part on a 2 mm plate (t/a = 0.32 by sqrt(A), 1 by its narrow side) is not flagged (from the theory review); e14: the Power profile message for a run with only the FEM or the 3D solid ticked names only the 3D solid (`api.py` 1173) | - |

## B. Pictures

`docs/images` holds 109 PNG, `pcbthermal/help` 26; the 26 of the guide are byte-identical copies of `docs/images`. The screens were regenerated in full colour by `fix/gui-review-rest` (e52e7703, 62 files) after the last GUI changes; after it only the import pictures changed (redrawn by 6587974a) and the Power profile picture (16cb7066). **No picture was regenerated here**: no screen changed since. Looked at in this pass (opened and read): `simulation_fem` (groups, plain names, FEM boxes), `results_summary` (the numbers equal the CLI run above; headers `Tmax °C (column)`, `ΔT K`, balance in percent), `results_fem_surface`, `results_surface_table`, `editor_warnings` (dots, element labels), `power_profile`, `import_step2` ('zoom 1.0×'): all current, no cut text, no personal path. `results_temperature_imported.png` is referenced by no document (made by the script; left). The theory and study figures were not looked at here (the theory review's part).

## C. What moved between 2.7.x and 2.8.0 (headline of `WHAT_MOVED.md`)

On the 17 frozen boards, 2.7.0 frozen numbers against the pending files of 2.8.0 (JSON only): the FVM and FDM move by a median 1.5e-5 K (at most 0.040 K at 1 and 0.5 mm, the finned block; at 2 mm the drawn copper edges move the FVM up to +0.19 K and the FDM up to +1.9 K, +1.3 % of the rise); the LPTN part rows up to +14.9 K (node to own peak) and its board maximum -3.1 to +3.1 %; the Analytic at most +0.126 K (finned block); the 3D solid not at all; 12 LPTN times to 63 % move (U2 of the example board -20 %). Additions: 29 FEM records (0.0 to 2.7 % of the rise below the FVM at 1 mm) and the surface metrics of 102 records (1.4 mK above the column, median). Outside the frozen boards (reproduction pass): +0.93 K on a 10 mm plate, +0.7 K under a 6 mm stainless block, +7.1 % for the LPTN on an isolated 10 mm part, 74.6 to 83.5 K/W on the calculator's JEDEC board without vias (a correction).

## D. Not verified

* No solver study was re-run; the 2.8.0 numbers of `WHAT_MOVED.md` are the pending files (the refreeze re-runs them), the numbers outside the frozen boards are quoted from PART-B, PART-C and `LUMPED_SHIFTS_REVIEW.md`. Part A of the reproduction pass was not available.
* The real-screen checklist (`releases/2.8.0/fem-model/GUI_TEST_CHECKLIST.md`, about one hour of the maintainer's hands) is **not done**.
* Not every one of the 109 pictures was opened in this pass (seven were, section B); the theory and study figures were not.
* `docs/versions.md` chapters older than 'Planned: 2.8.0' and the long 'After 2.6.0' list were not re-read item by item.
* **Sources not opened** (an honest 'not read' list, from the theory review): Zienkiewicz and Taylor, Hughes, Maxwell, the pyamg paper; Carslaw and Jaeger, Incropera, Krogh, Peaceman, Young, Varga, Churchill and Chu, Lloyd and Moran, Goldstein and Lau, and the JESD51 family. The documents that cite them mark the status (`research/theory/BIBLIOGRAPHY.md`); none of them was opened in this review.
* The program was not changed; one wrong message of the program was found (2.9.0 item e14) and one weak flag (e13), both in the 2.9.0 plan.

## E. Decisions for the maintainer

1. `CLAUDE.md` size: keep 48 KB of rules, or move the orchestration rules (section 12) or the structure (13) to a document to reach 40 KB.
2. `docs/version-comparison.md`: regenerate at the release (needs the label and the note of v2.8.0) or leave it stale with its note (`REFREEZE_PLAN.md` 7, decision 3).
3. Whether the two small items e13 and e14 stay in 2.9.0 or enter 2.8.0 as a `fix/` branch (text and a flag; no number moves).
