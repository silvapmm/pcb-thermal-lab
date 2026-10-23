# Log: outline

- The outline was added to the FVM, FDM and 3D solid; the Lumped and Analytic models were first skipped on a board with an outline.
- The maintainer asked for an approximation instead of skipping them. Three rectangles were compared (bounding box, same area, 1.1 × box) by `outline_rectangle_study.py`; the same-area rectangle was kept. A pre-run dialog was tried and removed at the maintainer's request: the message is a warning in the Results summary.
- Folder created: the script moved from `examples/`; figures added. The table in the README is the one of `docs/validation.md` section 13.

Not verified: no physical board measurement; the study uses one board and two parts.
- Schematic diagram added (`scripts/make_diagrams.py`, figure 4): drawn, not computed; the numbers it quotes are those of this README.
