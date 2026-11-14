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

## Candidate program items from the results (review, README 9.4; proposals only, nothing edited)

Each row: the evidence (README section and row), the size, the frozen-number risk, and whether `docs/versions.md` 'Planned' already holds it. The text in the last column is
what would go into `docs/versions.md` when the maintainer decides; it is not written there from this branch.

| Item | Evidence | Size | Frozen-number risk | In 'Planned'? | Proposed text |
| :-- | :-- | :-- | :-- | :-- | :-- |
| FDM via effect too small, also with the laminate resolved | README 8.1 table, column 'FDM 8': at 0.25 mm -2.3 / -2.3 / -0.8 % at 200 W/m2K and -8.6 / -4.3 / -4.0 % at 1000 (via 0.16 mm, 3 mm from the wall, 3 x 3 array), against +0.8 / -0.1 / +1.1 and +0.2 / +2.0 / +3.1 % for the FVM; -2.0 to -19.7 % at 1 mm | 1 to 9 % of the via effect at 0.25 mm; up to 20 % at 1 mm next to a strong edge | yes if fixed: FDM records of every via board | partly: 'FEM extensions (A43)' quotes '4 to 16 % low' and the edge image of the FDM via ('Board-edge image of the via in the FDM and the 3D solid'); the deficit FAR from the wall (3 mm, the array) is not stated | "FDM via effect (after `research/independent-fem-extensions` 8.1): with eight laminate sub-gaps the FDM still reads the via effect 1 to 9 % low at 0.25 mm (up to 20 % at 1 mm near a cooled edge), also 3 mm from the wall and for an array; the FVM reads it within 3 %. A stated limit of the comparison model, or a fix of the node-centred well (investigate first)." |
| Laminate at a strong edge in the via effect (FVM, FDM) | README 8.1: FVM at 0.25 mm -12.7 / -8.7 / -6.6 % at 1000 W/m2K with the default two sub-gaps, +0.2 / +2.0 / +3.1 % with eight | 7 to 13 % of the via effect at 1000 W/m2K | yes, wide (A18, the local laminate rule) | yes: the edge warning and A18 / A33 (the four-sub-gap idealisation) | none new: quote these numbers in the edge-laminate item when A18 is taken up |
| Analytic via effect at a strong edge | README 8.1: -20.1 / -20.2 / -17.0 % at 1000 W/m2K (0.5 mm), beyond the 'up to 16 % too small' of the Analytic via warning | 4 points beyond the warning text | none (text) | no | "The Analytic via warning quotes up to 16 % too small; next to an edge of 1000 W/m2K the via effect read 17 to 20 % low (`research/independent-fem-extensions` 8.1); say 'up to 20 %' or add 'more with a strong edge'." |
| Lumped via near a wall and an array off the part | README 8.1: +31.1 % (via 0.16 mm from the wall, and the 3 x 3 array), +45.8 % with a copper core, +11.1 % at 3 mm | inside the live warning ('22 % too small to 65 % too large' for a lone via, '19 to 56 % too large' for scattered vias) | none | covered by the warning | none: the numbers confirm the warning; a copper-filled via is not in the warning's sample (+45.8 %), within its 65 % |
| 3D solid via effect too large next to a wall | README 8.1: +9.7 / +25.8 % at 0.5 mm and +3.2 / +9.6 % at 0.25 mm for the via 0.16 mm from the wall (200 / 1000 W/m2K); +13.8 / +6.7 % at 3 mm, 1000 W/m2K | 1 to 26 % of the via effect | yes if fixed: 3D solid records of via boards | yes: 'Board-edge image of the via in the FDM and the 3D solid' (about 19 points too large) | none new; add these numbers as evidence; the cause (edge image, slab rule or footprint) is not separated |
| Part idealisation (uniform flux plus a series offset) | README 8.2: the resolved copper tab is 0.99 K (0.95 %) cooler at the part mean and 1.37 K (1.32 %) at the hottest point for 6 mm, 0.48 / 0.93 K for 4 mm | about 1 % of the part rise, on the safe side | depends on the design | yes: 'Part over a thermal-via cluster with a copper tab block' | none new: the measured size is this row; a feature only if the maintainer wants it |
| Drawn copper stripes read cool | README 8.4: -4.21 % (FVM) and -4.34 % (FDM) at 0.25 mm on the stripes board, -3.16 / -2.86 % on the plain control, against a resolved reference | about 1 point from the stripes, 3 points from the laminate at the inset edge | yes, wide (5a) | yes: 5a | add 'confirmed against a resolved finite-element reference (`research/independent-fem-extensions` 8.4)' to 5a |
| Transient of the FVM and FDM with a plate and a cluster | README 8.3 (as corrected): time to 63 % within -1.1 to +0.3 %, steady resistance -1.5 to +0.02 % against the hottest-node reference | none | none | - | none: a confirmation for `docs/validation.md` when the folder is folded in |

## Risks

* Memory: study 2 at 0.05 mm is about 2.9 GB and 1b at 0.05 mm about 2.3 GB (estimates): they need the quiet machine; study 2 at 0.025 mm (about
  10 GB) is not planned.
* The program cannot express a tab: variant B can only measure the program's idealisation, not be matched by an input.
* The transient integrator is of the program's family (theta method); its independence rests on the spatial method and on convergence in `dt`
  and the mesh, and it is checked against the modal reference of `fast-wave-oscillation` on the disc before it is used alone.
* pyamg lives only in `independent-fem-edge/.venv-research`; every case above 30 000 unknowns needs that environment.
