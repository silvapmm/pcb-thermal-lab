# Entry for `docs/research.md`: the surface read-out in the Lumped, the Analytic, the 3D solid and the transient

Investigation `research/surface-readout-models` (plan item e1 of 2.9.0). Not implemented; the proposals and their measured impact are in its `INTEGRATION.md`.

**Question.** How far can the surface read-out of 2.8.0 (FVM, FDM: parabola; FEM: computed) be given to the models that show `n/a`?

**Result.** The Analytic: yes, from its field and its uniform conductances, an estimate within 0.03 K of the FVM parabola on eight plates and case 2 of Muzychka and others. The 3D solid: computed within 0.14 K of the independent 3D surface once the copper has 8 slabs, the same parabola as the FVM with one slab. The transient: the same parabola on a frame, exact once the Fourier number of the layer is 0.3 or more, an upper estimate before. The Lumped: **no absolute surface**; the bound `q'' t / 2k` is above the true term on all plates and on 21 of 22 harness parts, but the Lumped column plus the bound is below the FEM surface on 8 of 22 harness parts (up to 50 K), so it cannot be worded as an upper bound of the temperature. The headline of the transient stays the column: from Fo = 1 the surface error equals the node error.

**Not verified.** Local sources in time (no independent 3D transient), the Lumped frames, blocks, the bottom face, partly filled thick copper, real boards.
