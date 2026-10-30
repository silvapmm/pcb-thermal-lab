# Text for `docs/theory.md`: the via barrel on the grid of the FVM and FDM

(Replaces the sentence "A via is assigned to the cell that contains its centre ..." of the vertical conductance in section 2 of `docs/theory.md` when the proposal of `research/point-via-convergence/INTEGRATION.md` is adopted. Figures: `research/point-via-convergence/figures/fig_01` to `fig_05`, to be copied to `docs/images/`.)

## The via as a sink in a sheet

Every copper plane is a sheet of conductance `S` (W/K, the conductance between two neighbouring cells of a square grid). A via of drill radius `r_v` drains the plane through its barrel: the heat flows sideways towards the barrel and the temperature falls as `ln(r / r_v) / (2π S)` per watt, so the resistance of one plane to the barrel is `ln(R / r_v) / (2π S)` for a far radius `R`. This logarithm is the *constriction* of the via; it is what a model of a via has to get right, whatever the cell.

## What the five-point stencil does with a point sink

A source or sink in one cell of the five-point stencil is a point on the lattice. Its potential relative to far away is not the one of the barrel but that of a hole of radius

`r_eq = exp(-(γ + 1.5 ln 2)) Δx = 0.1985 Δx`

(γ = 0.5772 is Euler's constant; the number follows from the potential kernel of the lattice, `a(x) = (2/π) ln|x| + (2γ + 3 ln 2)/π + O(|x|⁻²)`, and was checked by a finite solve to four digits). Peaceman's radial-flow argument gives `exp(-π/2) Δx = 0.2079 Δx` and his rounded value is `0.2 Δx`; the exact constant of the stencil is 0.1985. When `r_eq > r_v` the grid under-constricts the via and the missing resistance is the **well** `ln(r_eq / r_v) / (2π S)`; when `r_eq < r_v` (cells finer than about `5 r_v`) the point over-constricts it by `ln(r_v / r_eq) / (2π S)`, which no series resistance can remove: the barrel has to be spread over several cells.

## The model

The barrel conductance of every gap, `G_v = k_Cu A_via / d`, is not added to the vertical conductance of one cell. Every via has

* a **footprint**: weights `w_a` (sum 1) on the cells that its disc covers (the area of the disc inside every cell); if the lattice effective radius of that footprint is smaller than the radius `r_t` the model has to reproduce, the disc is enlarged (kept centred on the via) until the radius is reached;
* the **mean temperature of each plane over the footprint**, `T̄_l = Σ_a w_a T_{l,a}`;
* a **well** between `T̄_l` and the barrel node of plane `l`, `G_c = 2π S_l / ln(r_eff / r_t)`, with `r_eff` the effective radius of the footprint (infinite when `r_eff ≤ r_t`);
* the barrel nodes joined by `G_v` per gap.

The barrel nodes are eliminated (Kron reduction), which leaves couplings `G_{lm}` between the plane means, added to the matrix as `G_{lm} (e_l ⊗ w − e_m ⊗ w)(e_l ⊗ w − e_m ⊗ w)^T`: symmetric, zero row sum, no extra unknown. The effective radius of a footprint is `ln r_eff = (π/2)(E − κ)` with `E = Σ_ab w_a w_b a(a − b)` and `κ = (2γ + 3 ln 2)/π = 1.0291`; a single cell gives `E = 0` and `r_eff = r_eq`.

`r_t = e^(-1/4) r_v = 0.78 r_v`: the layered idealisation spreads the barrel conductance uniformly over the disc of the via (as the 3D solid does), and the mean potential of a uniform disc is that of a circle of radius `e^(-1/4)` times its own; against the 3D solver with the barrel drawn at its real size the via effect of this model is within 1 % (`research/point-via-convergence/README.md` 3.2).
