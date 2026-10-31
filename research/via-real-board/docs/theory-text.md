# Text for `docs/theory.md`: the via near an edge and the footprint on the board

(Complements `research/point-via-convergence/docs/theory-text.md`. To be adopted only with the parts the studies confirm; figures `research/via-real-board/figures/fig_01` to `fig_05`, to be copied to `docs/images/`. The formulas are derived here; no source gives them (status in `research/theory/BIBLIOGRAPHY.md` section 18).)

## Notation

`S_l` sheet conductance of plane `l` (W/K, the conductance between neighbouring cells of a square grid of side `Δ`); `r_v` drill radius; `r_t = e^(-1/4) r_v` the radius the model must reproduce; `w_a` footprint weights (sum 1) on cells `a` with centres `x_a`; `a(d)` the potential kernel of the five-point lattice, `a(d) = (2/π) ln|d| + κ + O(|d|^-2)`, `κ = (2γ + 3 ln 2)/π = 1.0291`, `a(0) = 0`, `a(1,0) = 1`, `a(1,1) = 4/π`.

## The via as a well (recall)

Mean temperature of a plane over the footprint `T̄_l = Σ_a w_a T_{l,a}`; effective radius `ln r_eff = (π/2)(E − κ) Δ`-units with `E = Σ_ab w_a w_b a(x_a − x_b)/Δ`; well `G_c = 2π S_l / ln(r_eff / r_t)`; barrel `G_v = k_Cu A_via / d` per gap; barrel nodes eliminated by Kron reduction into `G_lm` between the plane means; matrix term `G_lm (e_l ⊗ w − e_m ⊗ w)(e_l ⊗ w − e_m ⊗ w)^T`.

## A via next to an insulated edge

An insulated straight edge is a mirror: the temperature of a sheet with a source at `x` is the sum of the source and an equal source at the mirror image `x'`. On a cell-centred grid whose edge lies on a cell face the discrete problem is exactly the lattice sum of the footprint and its mirror image, with the images of the cell centres. The footprint's mean potential for a unit current `I` is therefore, up to a constant common to all positions,

`T̄_lat = −(I / 2π S) [ ln r_eff + ln D_lat ]`, `ln D_lat = ln Δ + (π/2)(P_img − κ)`, `P_img = Σ_ab w_a w_b a((x_a − x'_b)/Δ)`,

while the continuum disc of radius `r_t` at distance `δ` from the edge (image at `D_true = 2δ`) has `T̄ = −(I / 2π S)[ln r_t + ln D_true]`. When `δ` is smaller than a cell the cell centre of the footprint is not at the via (`δ = 0.16 mm` against a cell centre `0.5 mm` from the edge on a 1 mm grid): `D_lat = 1.0 mm`, `D_true = 0.32 mm`. The well has to supply the difference:

`G_c = 2π S_l / [ ln(r_eff / r_t) + c ]`, `c = ln(D_lat / D_true)`.

For a via near a corner (walls `x = p`, `y = q`) three images enter, two single and one diagonal (`D_true = 2 √(δ_x² + δ_y²)`), and `c` is the sum of the three terms. `δ` is clipped at `r_v`. If the denominator is not positive the well is infinite. The correction is zero when the via sits at the centre of the cell next to the wall (`P_img = a(1,0) = 1`, `D_lat = 0.955 Δ`, `c ≈ −0.05`); it grows as `ln(Δ/2δ)` for `δ → 0`.

*Status: derived, implemented in `lib/edge_image.py`, not yet compared with the resolved reference (README 3).* Valid for walls parallel to an axis on a cell-centred grid (FVM); the FDM edge nodes are half volumes whose mirror is themselves, and a diagonal or curved edge has no lattice image.

## The footprint on the cells of the board

Cells off the board (an outline) are pinned to the ambient by `g_pin`; weight on them would couple the barrel to the pin. The footprint therefore keeps the cells with `cover > 0` with weight `w_a · cover_a`, renormalised, and the sheet conductance of the well is that of the cell of the largest weight on the board. At the border of the grid the weight outside it may instead be moved to the mirror cell (`fold`), which keeps `r_eff` of an uncut footprint; which of the two is better is measured in README 3.3.

## The single footprint rule of the 3D solid

The copper area of every via is spread over the cells of its disc enlarged to `r_t`, centred on the via, or put in one cell when the cell is so coarse that the point already has `r_eq = 0.1985 Δ > r_t`; no rule that depends on whether the copper area fits in a cell (it made the open and the filled via two different models at some cells). The missing well of the 3D solid at coarse cells is a documented limit.

## Size of the coupling

A via with a footprint of `n` cells on `L` planes adds up to `(nL)²` entries to the matrix (the Kron-reduced couplings are dense across the footprint). The fill-in of the sparse factorisation grows with the overlap of footprints; the numbers against the number of vias and the cell are in README 4.2.

## Block SOR (recall)

Colour the stencil red-black, skip the via cells in the colours, solve each via block exactly (`B^{-1} (q_b − K_{b,:} θ)`), relaxed by the same `ω`, blocks coloured in groups of mutually uncoupled blocks; convergence for `0 < ω < 2` is proved in `sor-with-via-couplings` 8.4. The dense inverse of a block has `(unknowns of the block)²` entries; overlapping footprints merge into one block.
