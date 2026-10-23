# Changelog entry for the research branch

Ready to paste under `## [Unreleased]` of `CHANGELOG.md` when the maintainer adopts the work (updated 2026-10-23):

### Added
- **Investigation `research/gerbers`** (Gerber import, nets and the mapping of copper to the grid; nothing in the program changed): an independent Gerber and Excellon reader that needs only NumPy (copper layers, drills, X2 attributes), the mapping of copper to the face conductances of a square grid compared on 42 real windows, patterns, two and four layers and in all five models (the fill fraction is 10 to 23 % too cool on real copper; flow-based faces 0.3 to 3.6 %), coverage masks, tracks at any angle, vias and nets matched from the files, the current and Joule heat of a net, a board of our own as a test bench (`lib/our_board.py`), 77 tests, eleven figures, the import path end to end (`lib/importer.py`). It found that the program combines zones per cell with a maximum, which loses copper where several zones share a cell (+7 % FVM to +17 % FDM for the same copper). See `research/gerbers/CONCLUSIONS.md`, `research/gerbers/README.md` and `research/gerbers/INTEGRATION.md`.
