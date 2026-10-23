# Phase 1: how the Gerber reader would enter the program (design, not implemented)

*Phase 1 of three of the Gerber research (`research/gerber-import`, `research/gerber-models`, `research/gerber-nets`); the section numbers of the README (4.x) are those of the original single study.*

Question: *what would the program take from a Gerber set, and where would it live?* Short answer: **a small import module with no new dependency (the NumPy-only reader), a dialog that confirms what the files do not say, and masks as the data that the next phases use.**

## 1. What the module does

* **Reads** copper layers, the outline and Excellon holes with `native_gerber.py` (NumPy only, about 1000 lines); the layer assignment is pre-filled from the X2 file function or the file name (`classify`); a feature the reader does not support (aperture blocks, transformed apertures, the moire primitive) is reported and the file refused instead of drawing a wrong picture.
* **Draws** every layer as a binary and a coverage mask at a pixel of at most half the thinnest track found in the file, with a warning when a track is thinner than the pixel (`importer.import_board`); a mask at 0.1 mm of a 70 x 50 mm layer is 9 to 12 KB as PNG; in the project file it can be stored as packed bits, zlib and base64 with the origin and the pixel size.
* **Matches** the plated holes to pads and nets by position (`nets.hole_report`): a hole is a via or a component hole by the aperture function when written, by a diameter filter and a preview when not (a Gerber cannot tell them apart); the plated holes become the program's `Via` elements (open barrels of the hole's diameter).
* **Checks** the nets when a netlist exists (`kicad_pcb.py` and `study_kicad_nets.py` are the research version for a `.kicad_pcb`: position, short and break checks).

## 2. What the user must confirm (the interface)

Not for the physics, but for what the files do not say: which file is which layer and in which order, the units of a drill file without one, the board outline, which holes are vias, the stack-up (the Gerber job file may carry thicknesses, to be checked), the nets when the CAD tool did not write them, and where the heat sources are. A preview of the masks, the holes and the warnings, and a layer table, are the interface; the form in which extra inputs (for example currents of phase 3) are passed is left open by the maintainer.

## 3. Costs and risks

* No new dependency; gerbonara and shapely stay as a test reference (the NumPy reader agrees with them to 0.0 to 0.9 % of the area on 8 real boards and to the digit on 14 files of known area).
* The reader was written from the format as commonly documented, the Ucamco specification was not read in full; 161 of 164 comparable gerbonara test files agree within 3 % of the area, 6 are refused as unsupported (README 4.17).
* Non-rectangular outlines are only a box in the importer; the polygon outline is a separate item (`Board.outline` exists in the program).
* Documentation rules when adopted (`CLAUDE.md`): user guide, tooltips, `docs/validation.md`, tests, the whole battery.
