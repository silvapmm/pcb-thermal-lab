# Project-memory entries, phase 1

Ready to apply to `CLAUDE.md` when the maintainer adopts the work. Nothing here has been applied: a research branch does not edit `CLAUDE.md`.

## Edits to the sections of `CLAUDE.md`

* **Project Structure, `research/` block**: the Gerber research is three folders, `research/gerber-import/`, `research/gerber-models/` and `research/gerber-nets/` (see `research/INDEX.md`); the example paragraph that names `research/gerbers/` is replaced accordingly.
* **Research branches, "Folder content and layout"**: the clause "except the Gerber research" can read "and are checked by `tests/test_docs.py`" (the Python of the three folders passes it).

* **Research branches, "Folder content and layout"**: the folder layout has no `LOG.md` and no `IMPLEMENTED.md` (they were a diary that git already keeps and a map of the program that `docs/versions.md` already holds): what was read in full, from a summary or from memory, and what was not verified, is the last section of the README; and the research documents carry no dates.

* **Research branches, "Folder content and layout"**: add "every folder has schematic diagrams that explain how the thing works (`scripts/make_diagrams.py`, shapes in `research/diagram_kit.py`), linked from the README" (maintainer's rule: every research module has schemes and diagrams).

## New entries for the Decisions Log (newest first)

- **The vector reference ignored arcs; the reader is checked pixel by pixel** (README 4.45): `gerber_geometry.primitive_polygon` dropped stroked arcs, so our board's circular tracks were missing from the vector reference (41 mm2 against 164 mm2) and an arc file looked 8.6 % low in gerbonara; fixed with a regression test. Against the corrected reference the independent reader differs in 122 of 4.76 million copper pixels on 12 layers of 8 boards, all within 0.045 pixel (4.5 micrometres, the reader's own arc tolerance) of an exact edge.
- **Research folders without `LOG.md` and `IMPLEMENTED.md`, and the folder `research/gerbers` removed** (maintainer): the diary is in git and the map of the program is in `docs/versions.md`; what was read and not verified is the last section of every README; the three folders that derive from the first study replace `research/gerbers/`.
- **A research branch does not edit the program** (maintainer): `pcbthermal/`, `tests/`, `examples/` and `ico/` stay as in `develop`; changes to the program are measured on copies and adopted on `fix/` or `feature/` branches.
- **Illustrations of the real situation in every folder** (maintainer): sections, plan views and computed pictures that explain the problem, sharing one numbering with the data figures.
- **Gerber research split in three folders** (maintainer): `gerber-import` (reading; no program needed), `gerber-models` (the copper in the models), `gerber-nets` (nets with voltage and current); dependencies run one way (2 and 3 use the modules of 1); each folder has its own README, CONCLUSIONS, INTEGRATION, LOG, tests, figures and docs; the section numbers 4.1 to 4.40 of the original study were kept.
- **Nets checked against a KiCad project** (README 4.33): on the Stormduino every CAD object lies on the copper read, no connected group holds two nets, 55 of 56 nets without a zone fill split into the same pieces as in the CAD file.
- **Pictures and a board of our own** (maintainer): the gerbonara test boards had licences that could not be confirmed, so no picture of them is kept; the figures use our own synthetic boards (`lib/our_board.py`, `lib/rect_board.py`) and a window of the Stormduino board (MIT).
