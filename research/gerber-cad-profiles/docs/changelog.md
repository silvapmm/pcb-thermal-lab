# CHANGELOG text (Unreleased), to adopt with the feature

> **Review note.** Adapt this text to `INTEGRATION.md` 7 before adopting it: the user's assignment of a file is final (above X2); the reader tolerances are general, not per profile; no user-file profiles and no outline pruning in 2.5.0; no Zuken profile; evidence shown only as marker ids and a sanitised version.

* **Gerber import: CAD profile.** The import window shows which eCAD program probably wrote the files (from `TF.GenerationSoftware`, banner comments, drill headers and the files that come with the set), with a confidence, and lets the user change it. The profile supplies the layer names, the outline rule and the tolerances of each tool; the X2 attribute and the Excellon header always win. Profiles for KiCad, Altium Designer and CircuitMaker, EAGLE and Fusion Electronics, Cadence Allegro and OrCAD, Siemens Xpedition, PADS, EasyEDA, DipTrace, Pulsonix, Proteus, DesignSpark, LibrePCB, gEDA PCB, pcb-rnd, P-CAD, Target 3001, Fritzing and Upverter; a user file adds more.
* **Excellon**: a zero origin shift (`G93X0Y0`, written by every Xpedition NC drill file), `M71,TZ` and a `%` line before `M48` are accepted.
