# The part and its heatsinks: what is still open

What is already in the program (releases 2.3.0 and 2.4.0: the junction-to-pad resistance with its limit, the package families, the top path, the interface as one sheet, the heater types and typical heatsinks) is described in the program's `docs/versions.md`, `docs/models.md` and `docs/theory.md`; this file keeps only what is still open.

## Open (in `docs/roadmap.md`)

* **Junction node (JESD15-3 two-resistor)**: only worth it with a heatsink on top (this folder: 3 K without, a factor of two with).
* **Heatsink scenarios**: θSA scaled with the temperature rise from a reference rise, an "other speed (estimated)" factor, the flow linked to the board air speed, heatsinks with a fan, a heatsink from its geometry with the channel effect, comparison with catalogue curves. `heatsink_convection_study.py` is the first look at the scaling and the forced factors.
* **Foster chain / heat capacity of the junction and the heatsink** for transient work with a part.
* **Top path in the time simulation** (steady state only today).
* **A heatsink larger than its contact** and a plate layer on top of a package (`NOTES.md` R3 and R8).
