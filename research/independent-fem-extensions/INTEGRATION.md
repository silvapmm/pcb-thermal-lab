# Integration of the finite-element extensions

**What enters the program: nothing.** `git diff development --stat -- pcbthermal tests examples ico` stays empty; new code lives in `lib/` of this folder
(additions that import `independent-fem-edge/lib`, never edit it) and its `scripts/`.

## Recommendation (as corrected by the review, README 7)

1. Build in this order: the hollow-barrel builder of study 1 (O-grid levels at `r_in`, rings across the wall, the open barrel as a hole; no tool
   change); the partial-slab builder of study 2 (`lib/stack_ext.py`: extrude, remove the elements outside the tab, solder, interface and plate
   polygons, films on the new free faces, the via barrel kept to the board slabs) with its 1D check against `exact.series_stack`; then
   `lib/transient.py` (capacity, Rannacher-started Crank-Nicolson and implicit Euler, the frequency-domain periodic solve) with its checks, the disc
   against `fast-wave-oscillation/lib/axisym_stack.py` included, before any program comparison; then the stripe and L builders.
2. Every solve passes `direct_max=30000` and prints its unknowns and estimated peak first; a case above 2 GB is refused while the machine is
   shared (the list of what runs now and what waits is README 4 and 7.4).
3. Study 2 is reported in two parts: variant A (the program's problem: uniform source in the top copper, the solder as the same read-out offset on
   both sides) against every model, and variant B minus A (the part resolved: tab and solder) as the error of the program's idealisation of the part.
4. Results that find the program wrong become proposals here, never edits. A program feature for a tab or a spreading term under a part (variant B)
   is a decision of the maintainer once the numbers exist.
5. This work enables the via cluster under a tab, the Lumped dense via group reference, E13, 5a, A30 and B5 (`docs/versions.md`), and the transient
   reference for vias and a plate (the plain and partial-copper boards already have two references in `research/fast-wave-oscillation`).

## Risks

* Memory: study 2 at 0.05 mm is about 2.9 GB and 1b at 0.05 mm about 2.3 GB (estimates): they need the quiet machine; study 2 at 0.025 mm (about
  10 GB) is not planned.
* The program cannot express a tab: variant B can only measure the program's idealisation, not be matched by an input.
* The transient integrator is of the program's family (theta method); its independence rests on the spatial method and on convergence in `dt`
  and the mesh, and it is checked against the modal reference of `fast-wave-oscillation` on the disc before it is used alone.
* pyamg lives only in `independent-fem-edge/.venv-research`; every case above 30 000 unknowns needs that environment.
