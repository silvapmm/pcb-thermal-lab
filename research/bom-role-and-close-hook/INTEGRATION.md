# Integration: BOM role and the before-close hook

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

1. **File role and proposal in step 2.** Recommended: yes to both; the file role alone ("stored, not read") gives the package something to store but nothing the user sees. Cost 18 h of the 35.
2. **DNP unticks the part.** Recommended: yes, with the visible text "not populated (BOM)"; it is the one thing a BOM tells that no other file does (5 of 5 test points in the sample were in the placement file and not populated).
3. **Hook without veto.** Recommended: no veto in 2.6.0.
4. **Power list.** Recommended: a separate later item.
5. **Text rule words.** Recommended: accept for 2.6.0, state the limit (KiCad-style English names), measure on Altium and EasyEDA exports when a sample with a BOM is found.

## 4. Order

1. Hook (`before_close`, `before_release`) with the package capture moved onto it (5 h).
2. `gerber/bom.py` and its tests (8 h).
3. File role and BOM line in step 1 (5 h).
4. Step 2 proposal, DNP, re-import, project round trip (13 h).
5. User guide, tooltips, whole battery (4 h).

## 5. Risks and their tests

* A wrong proposal: only a default; the tooltip says "from the BOM names (a guess)". Test: user edit survives a re-import with a different BOM role.
* Hostile table: formula cells, 100 000-character cell, range `R1-R9999999`, 200 001 rows (tests in this folder cover the first three).
* The hook raising or running while busy: tests in README 6.4.
* A 2.5.x program opening a 2.6.0 project with a BOM role: it ignores the unknown role text (code reading); run `tests/test_format_compat_245.py` style compatibility on the merged tree before release.

## 6. Not verified

Accuracy of the roles against a labelled set; BOM exports of tools other than Pulsonix; any GUI behaviour (nothing was built).
