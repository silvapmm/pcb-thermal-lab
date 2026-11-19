# Entry for `research/ROADMAP.md` and `docs/versions.md` 'Planned'

* `research/surface-readout-models` is the investigation behind item e1: after it, `feature/surface-readout-models` (Analytic rule F, the 3D solid on top of `feature/solid3d-copper-slabs`, the transient frames, the Lumped wording).
* Open for a later investigation: a time-stepping independent 3D solver (a local source in time), the Lumped frames, a block under the part, and, for the FEM work of 2.9.0 (an implementation item, not an investigation), the face flux for a part on a thin outer copper layer: the review measured that the FEM's volumetric source in a one-slab copper reads half of the exact term on a one-dimensional board, 2 to 37 times below the FVM's on the harness (milli-kelvin).
