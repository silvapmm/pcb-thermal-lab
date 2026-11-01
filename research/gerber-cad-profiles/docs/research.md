# CAD profiles: summary for `docs/research.md` (open investigation)

**Question.** Can the Gerber import recognise which eCAD program wrote the files of a set, preselect a "CAD profile" the user can always change, and what does knowing it change in how the files are read?

**What was done** (`research/gerber-cad-profiles/`). 966 Gerber and drill files of 82 open sample sets (54 development, 28 held-out) of 19 eCAD programs, among them real Siemens Xpedition (8 sets), PADS, Altium Designer and CircuitMaker, EAGLE and Fusion Electronics, Cadence Allegro and OrCAD, KiCad 4 to 9, EasyEDA, DipTrace, Pulsonix, Proteus, LibrePCB; a marker table, a detector with a confidence rule, the program's reader run on every file, adjustments measured, the parts rules run on every paste layer.

**Findings.**
* The program is named in the files (X2 `TF.GenerationSoftware`, banner comments, drill headers, support files): 54 of 54 development sets and 28 of 28 held-out sets recognised, high confidence; Fritzing, Upverter, Target 3001 and the Zuken emulation only by a quirk (medium).
* The program's layer-function detection is right on 752 of 844 judged files (692 by name alone); it fails by tool names (Xpedition 61 of 98, Allegro 52 of 78, PADS 8 of 14, Target 3001 1 of 10), which a profile's name rules would cover.
* 17 Xpedition NC drill files (`G93X0Y0`) and 6 Upverter files are refused; 11 outline files (7 tools) are not closed contours; the adjustments read 16 of 17 drills (14 802 holes, none outside the board), all Upverter files (areas within 0.24 % of a second reader) and 6 of 11 outlines.
* The bottom-side X sign of a placement file is not a property of the tool, and `TO.C` in the paste file depends on a plot option: they stay detected from the data.

**Open.** No real Zuken (CR-8000, CR-5000, CADSTAR), PADS Professional, Valor, Allegro X, OrCAD X, EasyEDA Pro, Horizon file was obtained; the Zuken evidence is an emulation. The profile rules of PADS and EAGLE are from memory. Decisions for the maintainer: `INTEGRATION.md` 4.
