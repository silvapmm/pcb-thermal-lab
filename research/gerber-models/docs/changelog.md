# Changelog entry, phase 2

Ready to paste under `## [Unreleased]` of `CHANGELOG.md` when the maintainer adopts the work:

### Added
- **Investigation `research/gerber-models`** (nothing in the program changed): the mapping of copper to the face conductances of a square grid compared on 42 real windows, patterns, two and four layers, in all five models and on two boards of our own (the fill fraction is 10 to 23 % too cool on real copper in the one-sheet studies, 24 to 26 % against an independent 3D solution; flow-based faces 0.3 to 3.6 %), the import to the program's FVM, the mappings as an option, 34 tests, 24 figures. It found that the program combines zones per cell with a maximum, which loses copper where several zones share a cell, and that the 3D solid had no laminate under a single copper layer (corrected in the program since); its review found that the program's two laminate nodes are 5.5 to 13.6 % cool on patterned one-layer copper. See `research/gerber-models/CONCLUSIONS.md`.
