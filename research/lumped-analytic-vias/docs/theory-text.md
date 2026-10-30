# Text for `docs/theory.md` and `docs/models.md` (Lumped and Analytic models, vias)

To be adopted with the code; figures 01 to 05 and 07 of `../figures/` go to `docs/images/`.

## The constriction of a via in a plane

A via of target radius `a = e^(-1/4) r_v` (the radius of a uniform sink density over the disc of the drill, `docs/theory.md` section on the point via) draws heat from a plane of sheet conductance `S` (W/K). The temperature that the Lumped and Analytic models carry is the **mean** over a region (a ring, a tile); the temperature at the barrel wall is lower by the constriction resistance of the plane. For the cell of one via of a lattice (a disc of radius `R`, uniform source, insulated rim):

`R_c = (1 / (2 pi S)) [ b^4 ln b / (b^2 - 1)^2 - b^2 / (2 (b^2 - 1)) - 1/4 ]`, `b = R / a`, tending to `(ln b - 3/4) / (2 pi S)`.

A through via of L planes is the star of L such resistances, the barrel conductance `G_v = k_Cu A / d` of every gap and the barrel nodes; eliminated (Kron) it gives the couplings between the plane means.

## Lumped model

For every ring and group of vias (vias at most twice their nearest-neighbour distance apart): micro cell `r_c = min(sqrt(A_ring / n_ring), d_nn) / sqrt(pi)`, cluster radius `r_cl = sqrt(N_g) r_c`, macro radius `R = sqrt(sum of the touched ring areas / pi)`; the well of plane `l` is `R_c(r_c, a) + N_g R_c(R, r_cl)` (second term if `N_g > 1`). The sheets of the ring are coupled by the reduced star, in place of the adjacent conductance `gz` alone. Known limits: a via or row outside the footprint (isotherms around the footprint); dense arrays of open barrels (the effect is underestimated by 8 to 24 %).

## Analytic model

The tile means `y` solve `(I + G C) y = y0` (`G` the modal response of the tile mean to a unit power in a tile). The vias read the tile mean, not their wall: a diagonal term is added to `G`, for a tile with `n <= 1` vias `[ln(R_blk / a) - 1/4] / (2 pi S n)` and for `n > 1` `ln(R_tile / r_cl) / (2 pi S) + R_c(r_c, a) / n`. The barrel conductance of an isolated via is shared by the four nearest tiles with bilinear weights (the position of the sink is kept), and the tiles near vias are at most 1 mm so that they resolve the spacing of the vias.

## `docs/models.md` (a note in the via section)

The copper-fill gain of a via in the Lumped and Analytic models agrees with the FVM and the 3D solid within 0.3 K on the example board (4.5 and 4.3 K against 4.2 K); validation: `docs/validation.md` via scenarios and `research/lumped-analytic-vias/`. The `legacy` option restores the numbers of version 2.4.
