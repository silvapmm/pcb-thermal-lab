# `docs/versions.md` (chapter "Planned") entry, to adopt after the decision

> **Review note.** Adapt this text to `INTEGRATION.md` 7 before adopting it: the user's assignment of a file is final (above X2); the reader tolerances are general, not per profile; no user-file profiles and no outline pruning in 2.5.0; no Zuken profile; evidence shown only as marker ids and a sanitised version.

**CAD profiles for the Gerber import** (after the investigation `gerber-cad-profiles`; a feature, 2.5.0 with the Gerber import): `pcbthermal/data/cad_profiles.json` and `pcbthermal/gerber/profiles.py` (detection with confidence and evidence, layer-name rules per tool, tolerances, outline rule), the line "Detected: ... [change...]" in the import window, the user-file merge, tests per profile from the banners of real files, user guide and models text. Evidence: `research/gerber-cad-profiles/` (82 sample sets, 19 programs). Open: real Zuken, PADS Professional, Allegro X, OrCAD X, EasyEDA Pro and Horizon files; the profile rules of PADS and EAGLE are from memory; the Allegro drill without `M48`.

# `research/ROADMAP.md` entry (investigations)

* Obtain a real Zuken CR-8000 / CR-5000 / CADSTAR output set (Gerber, drill, placement) and test the emulated quirks against it.
* Obtain Altium, Allegro, Xpedition, PADS and EAGLE placement files and test the placement rules and the bottom-side X sign per tool.
* Obtain an IPC-2581 file of each tool (the header names the program) and an ODB++ export of Altium, Allegro and Xpedition.
