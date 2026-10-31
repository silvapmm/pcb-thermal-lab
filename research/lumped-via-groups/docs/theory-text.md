# Text for `docs/theory.md` (Lumped model: a group of vias under a larger footprint)

Written for adoption only if the maintainer adopts the two-zone footprint of `research/lumped-via-groups` (option C of `INTEGRATION.md`); otherwise the last paragraph goes into the section of the limits. Nothing here is in the program yet. The picture for the section is `figures/fig_01_footprint_core_section.png` and `fig_02_networks_program_series_zones.png` (to be copied to `docs/images/` on adoption).

## Two zones in the footprint

The Lumped network holds one node per layer for the whole footprint (ring 0). When the vias of a part cover only a core of the footprint (a thermal pad under a larger package, a dense array under a larger land) the heat of the rest of the footprint has two ways down: straight through the dielectric and the films under it, and sideways in the source layer to the core, whose barrels take it down. With one node the sideways path has no resistance; with a Krogh well of the cluster in series with the barrel (the earlier group term) the sideways resistance is there but every watt of the footprint has to cross it, as if the rest of the footprint had no way down of its own. The first is too cool, the second too hot.

The footprint is cut into two zones with a node per layer each:

* **A**, the rest of the footprint: the source in proportion to its area, its own dielectric and film conductances, the link to ring 1;
* **C**, the core: the cells of the footprint within `0.7071 d_nn` of a via of a group of two or more vias in the footprint (`d_nn` the nearest-neighbour distance of the group, so that a square lattice is covered completely), the barrels with their micro wells (`(ln(R_cell / r_t) - 3/4) / (2 pi S)` per plane, `lumped-analytic-vias`), the rest of the source.

**Link between the zones** (lossless sheet, any shapes): a uniform source `Q` over A and a uniform sink `Q` over C give, on an infinite sheet, `T(x) = (Q / (2 pi S)) [ mean_{y in C} ln|x - y| - mean_{y in A} ln|x - y| ]` plus a constant, so the difference of the area means is

`R_AC = (2 phi_AC - phi_AA - phi_CC) / (2 pi S)`, `phi_XY` = mean of `ln|x - y|` over `x` in X, `y` in Y,

with the mean log distance inside a cell `ln(0.447 sqrt(dx dy))` as in the program's footprint potentials. For concentric discs it equals the Krogh mean-to-wall resistance of the annulus plus `1 / (8 pi S)` for the core (the mean of a uniformly loaded core against its boundary); the pieces are checked to 0.1 % in `tests/test_lumped_groups.py`. The link from A to ring 1 is the mean-to-outer-wall resistance of the annulus with a uniform source, `R_A1 = [ (a^2 (a^2 - r_c^2) / 4 - (a^4 - r_c^4) / 8) - r_c^2 (a^2 / 4 - (r_c^2 / 2) ln(a / r_c) - r_c^2 / 4) ] / ((a^2 - r_c^2) / 2) / (2 S) / (pi (a^2 - r_c^2))`, plus the half ring of the program (`r_c` and `a` the radii of the discs of the areas of C and of the footprint).

**Peak.** The hottest point of the source layer is the larger of (1) the hottest point of A and (2) the temperature of C plus the rise of the rim of the cell of one via above its mean. (1): with the heat `Q_in` that A sends to C and `Q_out` that it sends to ring 1, A has a net generation `q = Q_in + Q_out`; the field is `T(x) = (1 / (2 pi S)) [ q mean_A K(x - y) - Q_in mean_C K(x - y) ]` with the kernel `K = -ln d` of the lossless sheet or `K = K0(d / lambda)` of the sheet that loses heat vertically (`lambda = sqrt(S / g)`, `g` the films plus the dielectric to the layers next to it, per area), and the excess is the maximum over the cells of A minus their weighted mean. (2): `I_via (rim - mean)` with `rim - mean = [ (b^2 ln b / (b^2 - 1) - 1/2) / (2 pi S) ] - R_Krogh`, `b = R_cell / r_t`, `I_via` the heat of one via from the source layer.

If the core covers more than 92 % of the footprint (or none of it) the footprint stays one node with the micro wells and the micro peak. Groups of vias outside the footprint keep the group term of the earlier investigation (a row beside a source is a sink of its own).

## If the zones are not adopted (limit of the Lumped model)

A group of vias that covers part of a larger footprint is represented by the micro well of every via and nothing for the sideways path of the rest of the footprint (error of the via effect up to +62 % on the 36 simple boards, the model too cool) or by the series group term (-9 to -39 %, too hot). The Lumped model should say so in the Results summary when a part has two or more vias and they cover less than the footprint: *"the via effect of this part may be off by 30 % or more; use the FVM"*.
