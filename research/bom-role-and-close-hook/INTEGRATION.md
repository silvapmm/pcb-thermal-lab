# Integration: BOM role and the before-close hook

*(audit 2.7.0, against the program of 2.6.0: the before-close and before-release hooks are in the program since 2.6.0 (`ImportBoardWindow.before_close`, `ImportSession.before_release`; the 'new_files' hooks run in the GUI thread before the reader's worker starts, the alternative of section 6, not the worker-thread rule). The BOM role was implemented on `feature/bom-role-and-close-hook` and then **deferred by the maintainer** and reverted in the 2.6.0 integration: `pcbthermal/gerber/bom.py` does not exist in the program; the item is 5 of 'After 2.6.0' in `docs/versions.md` 'Planned'; the research question is `research/ROADMAP.md` E14.)*

Branch for the program (after the maintainer decides): `feature/bom-role-and-close-hook` off `develop`, after `feature/project-package` is merged (the hook replaces its `capture_on_close` wrapper). Evidence: `README.md` of this folder; prototype `lib/bomroles.py`.

## 1. What changes

| Where | Change |
| :-- | :-- |
| `pcbthermal/gerber/bom.py` (new, no GUI) | `read_bom`, the role rule (`classify`), caps and text-only cells; unit tests on invented tables for KiCad, JLCPCB, Altium, PCBWay and Pulsonix header styles |
| `pcbthermal/gui/import_session.py` | role `BOM` in `ROLES`; content detection (a table with a designator column and no X/Y columns); `ImportSession.bom` (the merged table); `before_release` list run by `close()` |
| `pcbthermal/gui/import_window.py` | BOM line under the CAD tool line; `before_close` list run by `done()` after the busy check; step 2: Role starts at the BOM proposal, DNP unticks, "in BOM only" / "not in BOM" |
| `pcbthermal/model.py` | nothing (`ImportPart.from_file` already keeps any key; `ImportFile.function` is text); `Heater.role` unchanged |
| `pcbthermal/gui/package_actions.py` (package branch) | `capture_on_close` registers on `before_close` instead of replacing `session.close` |
| User guide, tooltips, tests | import chapter, tooltips of the new line and cells, tests for the help words, GUI stress scenarios (BOM present, absent, malformed, huge) |

## 2. What does not change

* No temperature, no frozen number: the role only chooses defaults of step 2 and the fields it offers (the program's `Heater.role` semantics are untouched).
* No power is ever read from a BOM. A project saved without a BOM is byte-identical (the `from_file["bom"]` key is written only when a BOM was read). Project format stays 2.
* The user's `edits` always win; a re-import rewrites `from_file`, never `edits`.
* `MainWindow.closeEvent` and the unsaved-changes question are untouched.

## 3. Recommendation for each decision (README 10)

The researcher's recommendation, then the reviewer's (README 12).

1. **File role and proposal in step 2.** Researcher: yes to both. Reviewer: **yes to both, in two steps of the same branch**: the file role (content detection, stored in the record, exported with the package) is what the maintainer already agreed ("stored, not read"); the role proposal adds a default the user sees and can change, at no risk to a temperature. If time is short, ship the file role and the reader, and the proposal after. Cost 18 h of the 35.
2. **DNP.** Researcher: untick. Reviewer: **yes, but as a mark, not an untick**: every part already starts unticked, so the BOM can only say "not populated (BOM)", keep the part unticked or warn when a power is typed, and never write `edits["use"]`.
3. **Hook without veto.** Both: **no veto in 2.6.0**. The unsaved-changes veto lives in `MainWindow.closeEvent`; the only hook users (source capture, removal of the extracted folder) must never block a close, and `done()` already defers while a call runs. Add the thread rule of README 6.3 (or run the "new_files" hooks in the GUI thread before the worker starts, which the reviewer prefers: simpler and no Qt hazard).
4. **Power list.** Both: **a separate later item**; no BOM of the library has a power column.
5. **Text rule words.** Researcher: accept. Reviewer: **accept for 2.6.0 only as a proposal shown as a guess**, because the 99 % is agreement on KiCad names in-sample (README 12.2), not accuracy; keep `SMA` and other ambiguous words from deciding alone (a value `SMA` was an RF connector on librevna), and measure on an Altium or EasyEDA set with a BOM before calling it reliable.

## 4. Order

1. Hook (`before_close`, `before_release`) with the package capture moved onto it (5 h).
2. `gerber/bom.py` and its tests (8 h).
3. File role and BOM line in step 1 (5 h).
4. Step 2 proposal, DNP, re-import, project round trip (13 h).
5. User guide, tooltips, whole battery (4 h).

## 5. Risks and their tests

* A wrong proposal: only a default; the tooltip says "from the BOM names (a guess)". Test: user edit survives a re-import with a different BOM role.
* Hostile table: formula cells, 100 000-character cell, range `R1-R9999999`, 200 001 rows (tests in this folder cover the first three).
* The hook raising or running while busy: tests in README 6.4. A session hook run from `set_files` runs in the reader's worker thread with the garbage collector off: a test that a hook touching no Qt object runs there, and the rule written in its docstring.
* A 2.5.x program opening a 2.6.0 project with a BOM role: it ignores the unknown role text (code reading); run `tests/test_format_compat_245.py` style compatibility on the merged tree before release.

## 6. Not verified

Accuracy of the roles against a labelled set; BOM exports of tools other than Pulsonix; any GUI behaviour (nothing was built).

## 7. Program findings of the review (for a `fix/` branch, not this folder)

* **Pulsonix position file refused** (`gerber/parts.parse_placement`): four preamble lines, then `Units,mm,`, then `Ref,Part Name,Side,X,Y,Rotation`; the import goes on without designators (notes: "is not used: no placement header found"). Proposal: skip lines before the first header row (bounded, for example 20 lines), read a `Units,<unit>` line, test with an invented Pulsonix-style table. Moves no number.
* **Parts warning with no placement used**: the session says "0 parts were matched to the placement file by position ... Usually right" when the placement file was refused; the line should not appear (or say that no placement file was read).
