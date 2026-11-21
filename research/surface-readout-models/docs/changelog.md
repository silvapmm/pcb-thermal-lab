# Entries for `CHANGELOG.md` (Unreleased), if the maintainer adopts the proposals

* Added (proposed): the surface temperature of the outer copper face in the Analytic model (an estimate from its field and the uniform conductances of its sheet), flagged where the part is small against the thickness.
* Added (proposed, after the copper slabs of the 3D solid): the surface of the 3D solid, computed from the first copper slab plus the half slab, and by the heat-flux parabola with one slab.
* Added (proposed): the surface of a frame of a transient FVM, FDM or Analytic run, beside the column, flagged as an upper estimate during the first 0.3 diffusion times of the copper after a change of power.
* Changed (proposed): the Lumped model's `n/a` for the surface states the largest through-thickness term it can add (`q'' t / 2k`), as a bound on that term only.
