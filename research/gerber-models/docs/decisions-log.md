# Project-memory entries, phase 2

Ready to apply to `CLAUDE.md` when the maintainer adopts the work (updated 2026-10-23). Nothing here has been applied: a research branch does not edit `CLAUDE.md`.

## Edits to the sections of `CLAUDE.md`

* **Decisions Log**: in the entry "`research/gerbers/` is done in the cloud ... figures 02 and 03 render boards of the gerbonara test set whose licence could not be confirmed" the question is settled (the figures were replaced by our own boards and an MIT board).

## New entries for the Decisions Log (newest first)

- 2026-10-23: **Diagonal couplings simulated** (`research/gerber-models`, README 4.44): a hybrid of the flow-based axial faces and the diagonal conduction they miss reproduces a lone 45-degree track at 64 to 94 % (damped by 0.5) against 37 to 84 % and keeps the 42 real windows at 1.77 %; undamped it over-adds on real boards (3.1 %, -2.8 % bias); not for the program until a detector of single dominant diagonal conductors replaces the global share.
- 2026-10-23: **Corrections to the program, measured** (README 4.39): zones combined by the maximum per sample point (`geometry.zone_fill`) instead of per cell (the additive rule double counts overlap and was dropped); laminate slab under a single copper layer in `solid3d.py`; no change on the example boards; to be adopted on a `fix/<topic>` branch off `develop` with the whole battery.
- 2026-10-23: **Mappings as an option** `SolverOptions.copper_mapping` (default `fill`; `lambda`, `cell_problem`, `flow`), README 4.38: mean error 6.5 % for the fill fraction against 1.9, 2.5 and 1.7 %.
- 2026-10-23: **Rectangle board; cause of the 3D solid's single-layer error** (README 4.35, 4.37): on squares and rectangles the Lumped is 16 % and the Analytic 26 % below the FVM, the 3D solid +8 % with two layers; `solid3d.py` has no laminate under a single copper layer (924 against 166 K with no copper).
- 2026-10-23: **Gerber import path end to end as research code** (`research/gerber-models/lib/faces.py`, README 4.31): files to a `Problem` with vias and a `FaceNetwork` for the program's FVM; the heater temperature error falls from -15.1 to -2 / -5 % (Stormduino) and from -5.0 to +4 / +2 % (own board); the reader choice moves it by 0.01 to 0.04 %.
- 2026-10-23: **Gerber research: conclusions on the mapping**: the fill fraction of a cell is 10 to 23 % too cool on real copper because it hides connectivity; the flow-based face conductances (Sampson 2005/2017, prior art) are within 0.3 to 3.6 % and lambda 0.5 within 1.0 to 3.2 %; Blackmore's tile method (2010) is the lower bound plus the arithmetic fraction; `Zone.fill` keeps its formula and imported copper gets its own element; in the five models FVM 11.9 to 2.6 %, FDM 15.9 to 7.1 %, Lumped 13.0 to 4.8 %, Analytic 18.6 to 12.2 %. Not validated: any measurement.
