# Roadmap entry, phase 2

Ready to apply to `docs/roadmap.md` when the maintainer adopts the work.

* **Imported copper in the simulation models**, researched on `research/gerber-models`: face conductances from the mask (flow-based faces, lambda 0.5, cell problem) for the FVM, FDM and 3D solid, a reduction for the Lumped and Analytic, the option `SolverOptions.copper_mapping` (default `fill`); the fill fraction is 10 to 23 % cool on real copper.
* **Orthotropic copper** is part of the import (directional face conductances).
* **Two corrections to the program** (`fix/<topic>`): zones combined by the maximum per sample point (`geometry.zone_fill`); a laminate slab under a single copper layer in `solid3d.py`.
