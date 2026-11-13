# Final opinion of the reviewer on 2.7.1 (patch release)

Tree reviewed: `development` at `37b3f1ea` against the tag `v2.7.0` (`main` `d2f17880`). The maintainer decided that everything merged into `development` since 2.7.0 (the first wave of the 2.8.0 plan) is released as **2.7.1**, a patch release: fixes, documents and tests only.

## 1. Verdict

**GO for 2.7.1**, on condition that the release commit makes the document changes of section 6 (the plan still says that there is no 2.7.1) and that the whole battery on the final tree is read to its last line (release gate step 6; not run here).

No change of `pcbthermal/` adds a capability or moves a number: the frozen reference `tests/regression/data/v2.7.0.json` and the pending folder are untouched, and the frozen numbers pass at 2, 1 and 0.5 mm (section 3). The project file format (`project.py`, `fileschema.py`, `model.py`) is untouched. The one change a strict reader could call new behaviour, the disclaimer line in the reports, is a text line and an added JSON key (section 2.2): acceptable for a patch, and the maintainer should know that the CLI and JSON outputs change.

## 2. What entered `development` since v2.7.0

20 commits without the merges (`git log --no-merges v2.7.0..development`), 162 files; 128 of them are the records under `releases/` (2.7.0 batteries, reproduction pass with its raw outputs, opinions, the rename record, the wave-1 review).

### 2.1 Program (`pcbthermal/`, 9 files, display and text only)

| Change | Commit | Category | Moves a number |
| :-- | :-- | :-- | :-- |
| Results tabs: only the page shown sets the minimum width (`ResultsView._size_to_current_page`); the Cut overlay box of Profiles goes to a second line when the first cannot hold it (`PlotTab._place_cut_overlay`); the figure is drawn again when the canvas crosses the inset/strip width (`plots.profile_has_strip`, a helper extracted from `draw_profile`, identical rule) | `0c182755` | fix (layout) | no |
| `BoardView.rebuild` emits `selection_changed` only when the rebuild changed the selection | `a443c825` | fix (focus) | no |
| `MainWindow._duplicate`: the copies are selected in Properties and the element list too | `052f78be` | fix (a typed value went to the original) | no |
| `results.DISCLAIMER` in the text report (also the on-screen Results summary), the Markdown report (CLI `run` output), the JSON summary (key `disclaimer`) and the Power Calculator result | `5c156bb1` | text | no |
| Calculator help: JEDEC row 31.6 K/W, +2.9 % at 0.5 mm; the Gerber import is in the interface | `d496d385` | document | no |
| User guide chapter 18: the disclaimer sentence; `help/editor_warnings.png` regenerated | `5c156bb1`, `c8363a1b` | document | no |

Read in full (`git diff v2.7.0..development -- pcbthermal`). Notes from the reading:

* `rebuild` compares `(kind, index)` sets taken before and after the rebuild. The restore of the selection by index was already there; only the emission changed. After an undo that removes a selected element the set shrinks, so the signal is still sent and Properties clears (checked, section 4). After a Delete the index-based set can stay equal while the element under that index is now another one: the canvas already re-selected it by index in 2.7.0, and the Properties form follows the document (it rebuilds on every document change), so board and panel stay consistent. Not a regression.
* `_duplicate` returns early when nothing is selected (Ctrl+D with nothing selected changes nothing; checked). When an edit is refused by the snapshot check (`Document.edit` restores the previous state) the indices of `created` may not exist; `Inspector.rebuild` filters invalid indices, so this path cannot raise.
* `_place_cut_overlay` moves the same widget between two layouts; `takeAt` on the second line frees only the layout items, the widget stays parented to the tab. `_on_canvas_resized` may redraw once more than needed when the picture is off (it tests the figure width, not the picture); harmless.

### 2.2 Compatibility of the disclaimer

* The Markdown report (and so the stdout of `python -m pcbthermal run`) now starts with a quoted line `> PCB Thermal Lab is a design aid. ...` and a blank line before the table; the text report has a `Disclaimer:` line after the header. A user script that takes the table from the first lines of the CLI output would see a shift; no script, test or study of the repository parses those lines (searched `research/`, `releases/`, `tests/`, `examples/`, `tools/`: they use the API objects, `sim.report()` only as a whole, and `summary.json` by key).
* `summary.json` gains one key, `disclaimer`; nothing is removed or renamed. An added key is a compatible change for a JSON reader.
* The text is one constant, worded once (`tests/test_report_disclaimer.py` checks that no report words it again) and the earlier note on computed heat transfer coefficients stays. Acceptable for a patch.

### 2.3 Tests (5 new files, 1 changed)

`test_enter_focus.py`, `test_calculator_dialog.py`, `test_map_markers_and_cut_locator.py` (additions), `test_report_disclaimer.py`, `test_third_party_text.py`; `test_calculator_validation.py` (the JEDEC tolerance follows the corrected row). No expectation of an existing test was loosened to hide a number.

### 2.4 Documents, research and process

CHANGELOG `[Unreleased]`; `docs/versions.md` (2.7.0 marked released, the plan of 2.8.0, item 20 done, vector copper and the BOM role dropped); `docs/calculators.md` 2.1 (JEDEC numbers); four screenshots (`editor_warnings`, `results_summary_imported`, `outline`, `outline_temperature`); the README licence paragraph; `tools/ocr/README.md` (run with `.venv-research`); `research/theory/BIBLIOGRAPHY.md` (licence and source URL fields on every entry, 860 lines); `research/ROADMAP.md` (E14, E15); `research/power-calculator/README.md` (one line of 2.7.0 numbers); `releases/regression-harness/reference/version_notes.json` (notes v2.5.0 to v2.7.0); the rename of `develop` to `development` in `CLAUDE.md`, `.claude/agents/*.md` and the harness `INTEGRATION.md`.

### 2.5 Is every commit fit for a patch?

Yes. None adds a capability. Two commits are planning or process, not fixes, and are harmless in a patch: `9dd5c664` (the 2.8.0 plan, document only) and `3cdef250` / `6d9d4844` / `0cf02d4b` (the branch rename, rules and agents). `97fbe1e6` drops two planned items from the documents (no code). The risk of releasing from `development` instead of a branch off `main` is nil here, because `development` holds nothing beyond `v2.7.0` except the wave-1 items listed above: no number-moving fix, no pending frozen file and no investigation that changes the program has entered it. **Rule for the release**: nothing more may be merged into `development` between this opinion and the release commit, or this opinion does not cover it.

## 3. Re-runs

* Quick set on the tree (worktree `release/2.7.1-final-opinion` = `37b3f1ea`), `QT_QPA_PLATFORM=offscreen`: `tests/test_third_party_text.py test_report_disclaimer.py test_enter_focus.py test_calculator_dialog.py test_calculator_validation.py test_map_markers_and_cut_locator.py test_docs.py test_license_header.py test_version.py test_help.py test_tooltips.py test_shortcuts.py test_api.py test_results_views.py test_single_layer.py test_calculator_window.py test_no_secrets.py tests/regression`: **1028 passed, 2 skipped in 192.94 s**. The regression folder ran at the default 2 mm cell inside this set; the three cells were not run separately here (`PCBT_FROZEN_CELLS=2,1,0.5` belongs to the release gate).
* The third-party guard passes (no `papers/` path, no OCR page markers, no fingerprint of the confidential specification, a licence field on every bibliography entry).
* `git diff v2.7.0..development -- tests/regression pcbthermal/data pcbthermal/project.py pcbthermal/fileschema.py pcbthermal/model.py` is empty.
* The JEDEC numbers of the calculator (31.6 K/W, +2.9 % at 0.5 mm) are held by `tests/test_calculator_dialog.py`, which passed.

## 4. The three GUI changes against the 2.7.0 interface

An offscreen drive of the real `MainWindow` (script in the reviewer's scratch space, not committed): the example board, Run, Stop while it runs, Run again to the end; Duplicate of a heater, a zone, a heatsink, a via and a metal block (a heatsink given 3 mm), each followed by a value typed in Properties and Enter, two undos, a redo and an undo; Ctrl+D with nothing selected; the layer keys 2, 3, 1; the Results tabs (Temperature, Profiles, Animation, Power profile) at 900 x 700 and 1280 x 800 with both docks open, in both themes; the Display popover opened and closed. **All 29 checks passed**:

* Stop is in the toolbar while the run goes and Run comes back after it; the run after a Stop finishes.
* After each Duplicate, Properties and the element list show the copy; the typed value changes the copy and leaves the original identical; the focus stays in the field after Enter; undo removes the copy and Properties holds no stale index; redo restores it.
* At 1280 x 800 the Profiles tab holds the slider, the position and Cut overlay on one line with the inset picture; at 900 x 700 the Cut overlay box is on a second line, the picture is the strip above the curves, and the page does not scroll sideways; the Animation tab still scrolls sideways to reach its controls, as designed.

**A limit to record (not a defect of 2.7.1)**: at 900 x 700 with both docks open the centre area is about 240 px wide, and the Cut slider of Profiles shrinks to about its handle; the keyboard arrows still move it, but dragging is impractical. Before the fix the page scrolled sideways instead. Closing or narrowing a dock gives the slider its width. A one-line note in the user guide or a minimum width for the slider can wait for 2.8.0.

Not verified: the macOS window system (offscreen only), the Display popover as drawn on a real screen (it is a separate tool window that a window grab does not show), and the maintainer's own Enter report, which was not reproduced by the executor, the first review or this drive (the CHANGELOG says so).

## 5. Pictures and the user guide

* `editor_warnings.png` is the same file in `docs/images/` and `pcbthermal/help/`; `results_summary_imported.png` shows the disclaimer line.
* **`docs/images/results_summary.png` is stale**: it was not regenerated after the disclaimer, so the summary in the README picture has no disclaimer line. Regenerate it with `examples/make_screenshots.py` at the release commit (every screenshot also shows `v2.7.0` in the status bar; regenerating all after the bump makes them show 2.7.1, optional).
* User guide: chapter 18 states the disclaimer sentence; the Stop button was documented in 2.7.0 and did not change.

## 6. The release commit of 2.7.1 (list)

1. `pcbthermal/__init__.py`: `__version__ = "2.7.1"`.
2. `CHANGELOG.md`: replace `## [Unreleased]` by `## [2.7.1] - <date>` with the text of section 7 (or keep the present bullets and move the two items noted there).
3. `README.md`: version badge `2.7.1`; the tests badge from the whole battery of the final tree; the versions list.
4. `docs/versions.md`: a chapter `## 2.7.1 - <date>: fixes of the Results layout, the Properties focus and Duplicate; a disclaimer in the reports` (text in section 8); the summary at the top names 2.7.1; the heading of 2.7.0 loses '(prepared on `develop`, not yet on `main`)'; the line 'Done for 2.8.0 (branch `fix/report-disclaimer`)' says 'Released in 2.7.1'; **'Planned: 2.8.0' says 'There is no 2.7.1': replace it** (the wave-1 items are released as 2.7.1, the plan starts from 2.7.1), and mark the wave-1 rows that 2.7.1 releases.
5. `CLAUDE.md`: 'Current release' to v2.7.1 with its date; the test-count line of `tests/`; 'Where to continue' (it says 'there is no 2.7.1'); a Decisions Log entry for the decision to release wave 1 as 2.7.1.
6. Frozen numbers: no number moves, so `tests/regression/data/v2.7.0.json` stays the newest file and the test must pass at 2, 1 and 0.5 mm; `study_diff.py --strict` on `v2.7.0` against the tree with an empty `expected_shifts_2.7.1.json` should give 0 alarms (recommended, cheap). `docs/version-comparison.md` is regenerated at the release (its notes for v2.5.0 to v2.7.0 are in `version_notes.json`).
7. `docs/images/results_summary.png` regenerated (section 5).
8. The whole battery on the final tree with `PCBT_COMPAT_V245=1` and `PCBT_SCAN_KEY_VALUES=1`, read to its last line; then merge into `main` with `--no-ff`, annotated tag `v2.7.1`, push, and the GitHub release from the `[2.7.1]` section.
9. `releases/2.8.0/wave-1/` holds the review of a branch that is released in 2.7.1; keep the file (it is a record) and say in `releases/README.md` that wave 1 was released as 2.7.1.

## 7. Proposed CHANGELOG text

```markdown
## [2.7.1] - <date>

A patch release: interface fixes, a disclaimer line in the reports, tests and documents. No result changes (the frozen numbers of 2.7.0 hold) and the project file format is unchanged.

### Fixed

- **The Results page no longer scrolls sideways in a narrow window, so the Profiles tab and its cut picture stay in view**: only the tab shown sets the width of the Results page (the Animation and Power profile tabs still scroll to reach their controls), the Cut overlay box of the Profiles tab goes to a line of its own when the first line cannot hold it, and the cut picture is drawn again when it moves between the inset over the curves and the strip above them. At 900 x 700 with both docks open the Cut slider is very short; the arrow keys still move it.
- **Enter in a Properties field keeps the focus in the field** for an element shown in Properties that is not drawn on the active layer (two heaters on two layers picked in the element tree, or a selection set by code): the canvas told the panel 'nothing selected' after every edit, which destroyed the form and its focus. The maintainer's report (the first Enter after a change of the Layer box) was not reproduced offscreen; the fix covers the neighbouring path that was found.
- **Duplicate (Ctrl+D) selects the copy in Properties and in the element list**: they kept showing the original, so the next value typed changed the original.

### Changed

- **A disclaimer line in every report**: the text report (saved and on screen), the Markdown report and so the output of `python -m pcbthermal run`, the JSON summary (new key `disclaimer`) and the Power Calculator result say that PCB Thermal Lab is a design aid whose models have not yet been compared with measurements of a real board, and that critical designs are to be validated by measurement. A script that reads the first lines of the command-line output sees one more line.

### Docs

- The JEDEC 2s2p row of the Power Calculator help and of `docs/calculators.md` 2.1 quoted the 2.6.0 program (31.4 K/W, +3.4 %); the 2.7.0 program gives 31.6 K/W, +2.9 % at the 0.5 mm cell. The help no longer says that the Gerber import is not in the interface.
- Screenshots: the outline pictures and the warnings picture no longer show a part off the board; the Results summary pictures show the disclaimer.
- Every entry of the research bibliography carries its licence and source address; the OCR tool is run from `.venv-research`; the version-comparison notes cover v2.5.0 to v2.7.0; the integration branch is called `development`.

### Tests

- `tests/test_third_party_text.py` (no third-party text, OCR output or confidential fingerprint in git; a licence field on every bibliography entry), `tests/test_report_disclaimer.py`, `tests/test_enter_focus.py`, `tests/test_calculator_dialog.py` (the Power Calculator dialog driven on the datasheet boards), and the narrow-window cases in `tests/test_map_markers_and_cut_locator.py`.
```

Two moves against the present `[Unreleased]` text: the JEDEC correction is a document, not a test (it is listed under Tests now), and the third-party guard is a test and a document, not an addition to the program (it is under Added now; a patch release should not have an Added section that reads as a feature).

## 8. Proposed `docs/versions.md` chapter

```markdown
## 2.7.1 - <date>: interface fixes and a disclaimer in the reports

A patch release of the first wave of the 2.8.0 plan (fixes, documents and tests; no number moves, the frozen file `v2.7.0.json` holds, the project format is unchanged).

* **Results page in a narrow window** (`fix/results-map-markers-and-cut-locator`): `ResultsView._size_to_current_page`, `PlotTab._place_cut_overlay`, `plots.profile_has_strip`; tests in `tests/test_map_markers_and_cut_locator.py`.
* **Properties focus** (`fix/enter-focus-and-calculator-test`): `BoardView.rebuild` reports the selection only when it changed; `tests/test_enter_focus.py`. The reported sequence was not reproduced offscreen.
* **Duplicate selects the copies in Properties and the list** (same branch): `MainWindow._duplicate`.
* **Disclaimer** (`fix/report-disclaimer`): `results.DISCLAIMER` in the text, Markdown and JSON reports and the Power Calculator result; `tests/test_report_disclaimer.py`; user guide chapter 18.
* **Documents and guards**: the JEDEC numbers of the calculator (`docs/calculators.md` 2.1), the third-party text guard (`tests/test_third_party_text.py`) and licences in the bibliography, the OCR environment, the version notes, the screenshots, the branch rename.

How it was tested: the reviewer's final opinion (`releases/2.7.1/final-opinion/README.md`: quick set 1028 passed, an offscreen drive of the window with 29 checks), the frozen numbers at 2, 1 and 0.5 mm, and the whole battery on the final tree (<result>).
```

## 9. Open decisions for the maintainer

1. Accept the disclaimer's change of the CLI and JSON outputs in a patch release (one line, one added key; no reader in the repository is affected). The reviewer recommends yes.
2. The short Cut slider at 900 x 700 with both docks: record it as a limit for 2.7.1 (the reviewer's recommendation) or give the slider a minimum width in 2.8.0.
3. The maintainer's own Enter report stays unreproduced: if it happens again on the real screen, note the exact steps for 2.8.0.

## What was read and what was not verified

Read in full: the diff of `pcbthermal/` since v2.7.0, the CHANGELOG `[Unreleased]`, the changes of `docs/versions.md`, `releases/README.md`, the four regenerated screenshots' summary picture. Run: the quick set of section 3 and the offscreen drive of section 4. Not run: the whole battery and the frozen numbers at 1 and 0.5 mm (release gate, the tester); the macOS window system. The 860-line bibliography change and the 128 report files under `releases/2.7.0/` were checked by the guard test and by their file names, not read line by line.
