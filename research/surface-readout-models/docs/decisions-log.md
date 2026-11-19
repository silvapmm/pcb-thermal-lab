# Candidate entries for `docs/decisions-log.md` (proposals of the investigation, not decisions)

* **The Lumped gets no absolute surface.** Reason: the bound `q'' t / 2k` holds for the through-thickness term on all plates and 21 of 22 harness parts, but the Lumped column plus the bound is below the FEM surface on 8 of 22 harness parts (up to 50 K; outlines and copper windows), so a surface number worded as an upper bound would be wrong on boards the program accepts. Rejected: offering the Lumped column plus the bound as a temperature.
* **The headline of the transient and of the Difference view stays the column**, the surface beside it. Reason: from a Fourier number of 1 the surface error equals the node error to within 0.01 K, so the surface changes nothing in a comparison between models.
* **The parabola is the rule of the Analytic and of a transient frame**; the 3D solid computes the face from its first copper slab plus the half slab and uses the parabola with one slab.
