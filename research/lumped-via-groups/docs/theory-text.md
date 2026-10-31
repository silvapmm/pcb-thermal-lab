# Text for `docs/theory.md` (Lumped model: a group of vias under a larger footprint)

Written for adoption only if the maintainer adopts the two-zone footprint of `research/lumped-via-groups`; otherwise the paragraph under "If the zones are not adopted" goes into the section of the limits. Nothing here is in the program yet.

## Two zones in the footprint

The Lumped network holds one node per layer for the whole footprint (ring 0). When the vias of a part cover only a core of the footprint (a thermal pad under a larger package, a dense array under a larger land) the heat of the rest of the footprint has two ways down: straight through the dielectric under it, and sideways in the source layer to the core, whose barrels take it down. With one node the sideways path has no resistance; with the series group term of the earlier investigation (a Krogh well of the cluster in every plane, in series with the barrel) the sideways resistance is there but every watt of the footprint has to cross it, as if the rest of the footprint had no way down of its own. Both are wrong in opposite directions (the program too cool, the group term too hot).

The footprint is cut into two zones with a node per layer each:

* **A**, the rest of the footprint: the source in proportion to its area, its own dielectric and film conductances, the link to ring 1;
* **C**, the core: the cells of the footprint within `0.7071 d_nn` of a via of a group of two or more vias that lies in the footprint (`d_nn` the nearest-neighbour distance of the group, so that a square lattice is covered completely), the barrels with their micro wells (`ln(R_cell / r_t) - 3/4` form, `lumped-analytic-vias`), the rest of the source.

The two nodes of every layer are joined by the resistance of the annulus between the core and the footprint, with the equivalent discs `r_c = sqrt(A_C / pi)` and `a = sqrt(A_foot / pi)`:

`R_AC = [ (a^4 ln(a/r_c)) / (a^2 - r_c^2)^2 - a^2 / (2 (a^2 - r_c^2)) - 1/4 ] / (2 pi S)` (Krogh, lossless)

or, with the vertical loss `g` of the rest of the footprint in that layer (films plus dielectric), the closed form of the lossy cell (`I0, I1, K0, K1` of `x = r / lambda`, `lambda = sqrt(S / g)`), which is exact for the cell problem and tends to the Krogh form for `a / lambda -> 0`. The link from A to ring 1 is the mean-to-outer-wall resistance of the annulus with a uniform source,

`R_A1 = [ (a^2 (a^2 - r_c^2)/4 - (a^4 - r_c^4)/8) - r_c^2 (a^2/4 - (r_c^2/2) ln(a/r_c) - r_c^2/4) ] / ((a^2 - r_c^2)/2) / (2 S) / (pi (a^2 - r_c^2))`,

plus the half of ring 1 of the program. The peak of the source layer is the hottest point of the annulus: with the heat `Q_in` that A sends to C and `Q_out` that it sends to ring 1, the net generation `q = Q_in + Q_out` is uniform, the flow through radius `r` is `I(r) = Q_out - q (a^2 - r^2) / (a^2 - r_c^2)`, `dT/dr = -I / (2 pi S r)`, the maximum is at the radius where `I` changes sign, and the excess over the area mean of A is multiplied by `4 (phi_mean - phi_min)` of the real footprint (1 for a disc).

If the core covers more than 92 % of the footprint (or none of it) the footprint stays one node, with the micro wells and no group term inside the footprint. The group term of the earlier investigation stays for groups of vias outside the footprint.

## If the zones are not adopted (limit of the Lumped model)

A group of vias that covers part of a larger footprint is represented by the micro well of every via and nothing for the sideways path of the rest of the footprint (error of the via effect 0 to +34 %, model cooler) or by the series group term (-14 to -31 %, model hotter). The Lumped model should say so in the Results summary when a part has two or more vias and the vias cover less than the footprint: "the via effect of this part may be off by 30 %; use the FVM".
