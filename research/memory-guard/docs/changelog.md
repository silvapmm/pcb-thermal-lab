# Text for `CHANGELOG.md` (Unreleased, when the feature is adopted)

* Memory guard: the program reads the physical memory of the machine, estimates the peak memory of every selected model from its unknown count and class, and refuses before allocating a run above the limit (default 70 % of the physical memory, editable in Preferences, solver section). The panel shows the estimate next to the unknown count; a run that is allowed but large is marked slow; the command line exits with code 2 and says which cell would fit.
* The fixed 3D solid limit of 250 000 unknowns is replaced by the same estimate, with an absolute ceiling.
* The block SOR checks the memory of the dense block inverse instead of the fixed 5000 unknowns.
* The check of the block SOR counts 72 bytes per squared block unknown (5 000 unknowns are 1.8 GB, not 200 MB as the old comment said).
