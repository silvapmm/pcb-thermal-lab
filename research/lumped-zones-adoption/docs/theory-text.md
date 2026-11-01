# Text for `docs/theory.md`, section 5 (Lumped), if the zonal model is adopted

Draft, adjusted to the results of README sections 4, 8 and 9. Figures 1 (footprint, zones and wells), 2 (network of two layers) and 4 (raster against the core) of this folder go with it; the earlier folder `research/lumped-via-groups/docs/theory-text.md` holds the derivations of the closed forms.

**Zones of the footprint.** When a group of two or more vias lies in the footprint, the cells within `0.7071 d_nn` of its vias form the **core** C and the rest of the footprint is A. A and C are two nodes per layer; the rings outside are the program's. The source is divided between them in proportion to the covered area; each zone has its own sheet conductance, films, dielectric and capacity (sums over its cells); the barrels of C reach the planes through the micro wells of section 6.1. If there is no core, or it covers more than 92 % of the footprint counted on the Lumped grid **and** on a 0.1 mm grid (so that the choice does not jump with the raster), the footprint is one node, the program's network unchanged: a core of 94 to 99 % leaves a handful of cells for A, and the zone network then reads the part up to 14 % hot (README 9.7).

**Link between A and C.** For a uniform source over A and a uniform sink over C of equal strength on a lossless sheet,

    T_A - T_C = Q (2 phi_AC - phi_AA - phi_CC) / (2 pi S),        phi_XY = mean of ln|x - y| over x in X, y in Y.

For concentric discs this is the Krogh resistance of the annulus plus `1/(8 pi S)` of the core, so the same convergence of heat on a group of vias is not added again by the cluster well inside the core (confirmed by the first run: leaving the cluster well out of the zone nodes or keeping it differs by 0.2 point of the mean error; on boards with several groups under one footprint keeping it is better by 3 to 6 points of the effect, README 9.5).

**Link between A and ring 1.** The mean-to-outer-wall resistance of the equivalent annulus with a uniform source,

    R = [ (I1 - I2) / ((a^2 - r_c^2)/2) ] / (2 S pi (a^2 - r_c^2)),
    I1 = a^2 (a^2 - r_c^2)/4 - (a^4 - r_c^4)/8,    I2 = r_c^2 (a^2/4 - (r_c^2/2) ln(a/r_c) - r_c^2/4),

with `r_c` and `a` the radii of the discs of the same area as the core and as the footprint (it tends to `1/(8 pi S)` as `r_c -> 0`), plus the half ring of the program.

**Peak.** The hottest point of the source layer is the largest of: the hottest point of A (the field of a uniform generation `Q_in + Q_out` over A, a sink `Q_in` on C and `Q_out` far, with the `K0(d/lambda)` kernel of the layer), the core mean plus the rise of the rim of the Krogh cell of one via, and, when the core is hotter than A, the core mean plus that rise plus the bump of the core above its mean (the program's own footprint formula applied to C).

**Transient and profiles.** `C dtheta/dt + K theta = s P` with the capacity of each node the sum of its cells' capacities and `s` the source vector (the share of A and C by the covered area); the peak is evaluated at each step. The step response of the hottest point is within 4 to 10 % of the FVM at 0.01 to 100 s on two boards and 0.3 to 36 % on an elongated one, where the one-node network is 63 to 74 % off at 0.01 s (the quasi-steady peak term overshoots at the switching edge, on the safe side); a square-wave run with the source split is within 5.4 % of the FVM's average steady rise at periods of 0.1, 1 and 10 s on three boards and 3.8 % on average (14.3 % at most) over 93 boards, against 9.6 % (28.9 %) for the one node. The profile runner of the program must use the same source vector: with the whole power on A the part reads up to 25 % hot (README 9.2). Figure 12 of this folder.

**Limits.** The core radius, the 92 % and the 700-point decimation are assumed constants; the model reads the part up to 16 % of its rise too cool for an array across the edge of the footprint, 1 to 5 % for an off-centre cluster and 2 to 4 % for an elongated footprint (steady state and profile), and up to 6.1 % of the rise too cool when the vias conduct nothing; against a 3D solver with the barrels drawn (a 0.3 mm barrel on a 0.125 mm grid, not resolved) the hottest rise is within 1.6 % on six cases; several groups under one footprint (one core, the union) are within 19 % of the effect and 2.5 % of the rise on eight cases; irregular groups, guard rings, a block under the part and an L-shaped footprint were not tested. Warnings in `checks.py`.
