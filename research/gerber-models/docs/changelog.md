# Changelog entry, phase 2

Ready to paste under `## [Unreleased]` of `CHANGELOG.md` when the maintainer adopts the work (updated 2026-10-23):

### Added
- **Investigation `research/gerber-models`** (nothing in the program changed): the mapping of copper to the face conductances of a square grid compared on 42 real windows, patterns, two and four layers, in all five models and on two boards of our own (the fill fraction is 10 to 23 % too cool on real copper; flow-based faces 0.3 to 3.6 %), the import to the program's FVM, the mappings as an option, 29 tests, six figures. It found that the program combines zones per cell with a maximum, which loses copper where several zones share a cell, and that the 3D solid has no laminate under a single copper layer. See `research/gerber-models/CONCLUSIONS.md`.
