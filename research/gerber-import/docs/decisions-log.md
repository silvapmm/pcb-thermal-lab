# Project-memory entries, phase 1

Ready to apply to `CLAUDE.md` when the maintainer adopts the work. Nothing here has been applied: a research branch does not edit `CLAUDE.md`.

## Edits to the sections of `CLAUDE.md`

* **Project Structure, `research/` block**: the Gerber research is three folders, `research/gerber-import/`, `research/gerber-models/` and `research/gerber-nets/` (see `research/INDEX.md`); the example paragraph that names `research/gerbers/` is replaced accordingly.
* **Research branches, "Folder content and layout"**: the clause "except the Gerber research" can read "and are checked by `tests/test_docs.py`" (the Python of the three folders passes it).

* **Research branches, "Folder content and layout"**: the clause "`LOG.md` (dated entries: ...)" can read "`LOG.md` (entries: ...)": the maintainer does not want dates in the research documents (the documents of the three Gerber folders carry none).

* **Research branches, "Folder content and layout"**: add "every folder has schematic diagrams that explain how the thing works (`scripts/make_diagrams.py`, shapes in `research/diagram_kit.py`), linked from the README" (maintainer's rule: every research module has schemes and diagrams).

## New entries for the Decisions Log (newest first)

- **Gerber research split in three folders** (maintainer): `gerber-import` (reading; no program needed), `gerber-models` (the copper in the models), `gerber-nets` (nets with voltage and current); dependencies run one way (2 and 3 use the modules of 1); each folder has its own README, CONCLUSIONS, INTEGRATION, LOG, tests, figures and docs; the section numbers 4.1 to 4.40 of the original study were kept.
- **Nets checked against a KiCad project** (README 4.33): on the Stormduino every CAD object lies on the copper read, no connected group holds two nets, 55 of 56 nets without a zone fill split into the same pieces as in the CAD file.
- **Pictures and a board of our own** (maintainer): the gerbonara test boards had licences that could not be confirmed, so no picture of them is kept; the figures use our own synthetic boards (`lib/our_board.py`, `lib/rect_board.py`) and a window of the Stormduino board (MIT).
