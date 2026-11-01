# Import window prototype (three layouts)

Runnable prototype of the planned Gerber import window, to test the layouts by hand. Not part of the program; it imports the program (theme, memory guard) and the independent reader of the research.

```sh
.venv/bin/python research/gerber-real-boards/prototypes/import_window/run.py --layout hybrid            # default: stepper header + Back / Next
.venv/bin/python research/gerber-real-boards/prototypes/import_window/run.py --layout tabs|wizard [--board PATH|ZIP] [--theme light|dark] [--previous demo|none|FILE]
```

* `hybrid`: numbered round markers joined by a line (current in the accent, finished with a check, locked muted; click to jump, tooltip says why a step is locked), a one-line subtitle, Back / Next (Import on step 3), and a secondary *Import now* once step 1 is complete.
* `tabs`: three tabs, one Import button (enabled when step 1 is complete). `wizard`: text step indicator, Back / Next / Import.
* Default board: the RP2040 board in `data/rp2040` (git-ignored, licence unchecked, read in place, never copied), else a synthetic board written to a temporary folder. `--board` takes a folder or a ZIP.

**Real:** reading the folder or ZIP, function detection (X2, Excellon comment, name, header), layer assignment and its checks, copper/outline/drill rendering, paste groups (TO.C designators, else proximity at 0.6 mm), matching to the placement file, zoom/pan/click preview, power table, shape (box or hull, suggested), memory verdict (`pcbthermal.memory.check`), the re-import diff and merge.
**Simulated:** the Import button writes `out/import_summary_<layout>.json` and shows a message; no project is created. The *stored import* of the re-import dialog is made from the same board with edits (`--previous demo`: three parts with powers, one moved, one resized, one removed, a layout-revised copper file, no placement file). The warning texts of step 3 and the 55 bytes per pixel mask line are plausible text, not measured for the program.
**Not verified:** that the proximity rule groups a real package the way a person would (on the RP2040 board 18 of 30 parts match a group, 18 groups match no part: shown in red on purpose; Ctrl+click adds an opening to the selected part); behaviour on boards with inner layers (not exercised); the look on a real desktop (screenshots are offscreen grabs; the dark theme draws unticked radio buttons almost invisibly, as the program does).

Tests: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/gerber-real-boards/prototypes/import_window/tests` (backend, the three layouts in both themes with a grab of every page, the re-import flow, the locked steps of the hybrid).
Design of the re-import: `../../INTEGRATION.md` section 10.
