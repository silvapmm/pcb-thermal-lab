# Text for `CHANGELOG.md` (Unreleased, when the feature is adopted)

* Memory guard: the program reads the physical memory of the machine, estimates the peak memory of every selected model from its unknown count and class, and refuses before allocating a run above the limit (default 70 % of the physical memory, editable in Preferences, solver section). The panel shows the estimate next to the unknown count; a run that is allowed but large is marked slow; the command line exits with code 2 and says which cell would fit.
* The fixed 3D solid limit of 250 000 unknowns is replaced by the same estimate, with an absolute ceiling.
* The block SOR checks the memory of the dense block inverse instead of the fixed 5000 unknowns.
* (If adopted after the ladder) The unknowns are numbered cell by cell before the sparse factorisation: less time and memory on boards with laminate nodes; temperatures agree with the earlier numbering to the solver's round-off.
