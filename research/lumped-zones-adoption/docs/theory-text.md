# Text for `docs/theory.md`, section 5 (Lumped), if the zonal model is adopted

Draft written before any run; to be adjusted to the results. Figures 1 (footprint, zones and wells), 2 (network of two layers) and 4 (raster against the core) of this folder go with it; the earlier folder `research/lumped-via-groups/docs/theory-text.md` holds the derivations of the closed forms.

**Zones of the footprint.** When a group of two or more vias lies in the footprint, the cells within `0.7071 d_nn` of its vias form the **core** C and the rest of the footprint is A. A and C are two nodes per layer; the rings outside are the program's. The source is divided between them in proportion to the covered area; each zone has its own sheet conductance, films, dielectric and capacity (sums over its cells); the barrels of C reach the planes through the micro wells of section 6.1. If there is no core, or it covers more than 92 % of the footprint, the footprint is one node.

**Link between A and C.** For a uniform source over A and a uniform sink over C of equal strength on a lossless sheet,

    T_A - T_C = Q (2 phi_AC - phi_AA - phi_CC) / (2 pi S),        phi_XY = mean of ln|x - y| over x in X, y in Y.

For concentric discs this is the Krogh resistance of the annulus plus `1/(8 pi S)` of the core, so the same convergence of heat on a group of vias is not added again by the cluster well inside the core [if the first run confirms it].

**Link between A and ring 1.** The mean-to-outer-wall resistance of the equivalent annulus with a uniform source,

    R = [ (I1 - I2) / ((a^2 - r_c^2)/2) ] / (2 S pi (a^2 - r_c^2)),
    I1 = a^2 (a^2 - r_c^2)/4 - (a^4 - r_c^4)/8,    I2 = r_c^2 (a^2/4 - (r_c^2/2) ln(a/r_c) - r_c^2/4),

with `r_c` and `a` the radii of the discs of the same area as the core and as the footprint (it tends to `1/(8 pi S)` as `r_c -> 0`), plus the half ring of the program.

**Peak.** The hottest point of the source layer is the largest of: the hottest point of A (the field of a uniform generation `Q_in + Q_out` over A, a sink `Q_in` on C and `Q_out` far, with the `K0(d/lambda)` kernel of the layer), the core mean plus the rise of the rim of the Krogh cell of one via, and, when the core is hotter than A, the core mean plus that rise plus the bump of the core above its mean (the program's own footprint formula applied to C).

**Transient.** `C dtheta/dt + K theta = s P` with the capacity of each node the sum of its cells' capacities and `s` the source vector; the peak is evaluated at each step.

**Limits.** The core radius, the 92 % and the 700-point decimation are assumed constants; the model is up to 20 % too cool for an elongated footprint, a cluster off its centre and a sparse array; irregular groups, several groups of different pitch in one footprint, guard rings, a block under the part and an L-shaped footprint were not tested. Warnings in `checks.py`.
