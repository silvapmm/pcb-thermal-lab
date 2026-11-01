# Text for `CHANGELOG.md` (Unreleased), to be written when the work is adopted

*Not applicable yet: this folder changes nothing in the program. The entries below are the ones the adoption would add; each is re-written with the numbers of the implementation.*

* Added: import of a Gerber set (copper, Excellon drills, outline) with our own reader; imported copper with face conductances (or the fill per cell, after the study of the faces with the laminate rule) and its heat capacity; plated holes as vias.
* Added: parts from the solder-paste layer, with reference designators from the Gerber X2 attribute `TO.C` and from placement files matched by name.
* Added: warnings on imported boards (Lumped and Analytic read cool; the cell model of imported copper is approximate; a feature thinner than the sampling) and a memory guard that knows the cost of an import.
* Changed: a project with imported boards is saved in format 2, which older programs refuse to open (instead of dropping the imports); projects without imports stay format 1.
