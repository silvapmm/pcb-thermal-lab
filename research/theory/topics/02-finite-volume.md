# 02. Finite volumes: the reference model (FVM)

![FVM cell](../figures/fig_02_fvm_cell.png)

*Figure 2 (`figures/fig_02_fvm_cell.png`): left, the heat balance of one cell through its four faces; middle, one face as two half cells in series, which gives the harmonic mean of the two sheet conductances; right, the row of the matrix that the cell produces (a symmetric M-matrix).*

## 1. What it is

The reference model of the program. The plan of the board is cut into rectangular cells; the unknown is the mean temperature rise `theta_{l,i,j}` of the copper layer `l` in the cell `(i, j)` of size `dx * dy`, stored at the cell centre. The heat equation (topic 01, equation (1)) is integrated over each cell and the heat through its faces is balanced, so the discrete energy balance is **exact in every cell**, not only in total.

## 2. Face conductances (all in W/K)

* **Lateral**, between two neighbouring cells: the heat crosses the two half cells in series,
  `R = dx / (2 S1 dy) + dx / (2 S2 dy)`, hence

      G_x = (2 S1 S2 / (S1 + S2)) dy / dx            G_y = (2 S1 S2 / (S1 + S2)) dx / dy

  the **harmonic mean** of the two sheet conductances (a copper / FR-4 edge is a series, not an average). It is zero when both are zero.
* **Vertical**, between layers `l` and `l + 1` in a cell: `G_z = k_th dx dy / d` (the dielectric alone). The barrel of a via is **not** added to the cell of its centre: it is a mean-potential coupling of a footprint of cells (section 6 below).
* **Ambient**: `G_amb = h dx dy` on the outer layers (`h_top` or `h_bottom`), plus `h_extra dx dy c_hs` under a plain heatsink, plus `h_side` times the edge length times the slab on edge cells. On a board with an outline the edge length of a cell is the length of the outline inside it (`geometry.edge_length_on_board`): the outline is sampled at a tenth of a cell, every sample is moved a thousandth of a cell towards the board (a side on a grid line belongs to the cell on the board) and a sliver that falls in a cell off the board goes to the nearest board cell, so the lengths add up to the perimeter (`research/outline/README.md` 4.6; before this, sides on grid lines lost their edge loss). When a metal block covers a face the board coefficient is multiplied by `1 - c` (topic 11).

## 3. The system

`K theta = Q`, with `K = D - A`. `A` is the symmetric matrix of non-negative face conductances and `D` is its row sums plus the ambient conductances. `K` is symmetric, weakly diagonally dominant (strictly where there is an ambient path) and irreducible: a symmetric positive definite **M-matrix**. Consequences: the solution exists and is unique, and the **maximum principle** holds (`theta >= 0`: no temperature below the ambient). The sum of the rows of `K` is the ambient conductance, hence `sum G_amb theta = sum Q`, the energy balance.

The source of a heater is `Q_i = P c_i / sum c` with `c_i` the sub-sampled coverage of the footprint in cell `i` (8 x 8 samples per cell for heaters, 4 x 4 for zones, heatsinks and blocks; the board cover of an outline is also sampled 8 x 8, topic 28), so the **power is exact** whatever the grid; a footprint smaller than a sample sends all the power to the centroid's cell.

## 4. Solvers

| Solver | What it does | Note |
| :-- | :-- | :-- |
| direct | sparse LU (SuperLU) with the symmetric minimum-degree ordering | half the fill and about 40 % less time than the default ordering; relative residual about 1e-13 |
| conjugate gradients | Jacobi (diagonal) preconditioner, tolerance 1e-12 | |
| red-black SOR | `theta_new = (sum G_m theta_m + Q) / D`, `theta <- theta + omega (theta_new - theta)`, `omega` the estimate of Young's optimum `2 / (1 + sqrt(1 - rho^2))`, `rho` from a Rayleigh quotient of `K` (a lower bound, so `omega` is on the safe side; `fvm.Network.sor_omega`), plus an exact solve of each dense via block after the two colours (block SOR) | stopped on the **residual** (1e-9). The old `2 / (1 + sin(pi / n_max))` is the optimum of a plate with fixed edges and needed 2.8 to 19 times more sweeps (`research/young-omega-tiles`); the step-change stopping rule of the removed program can stop 2.7 to 16 K from the solution (`docs/validation.md` section 5) |

## 5. Accuracy

Second order in the cell size for smooth fields, first order at features (a via, a copper edge, a thin heater). The example board converges monotonically (within 0.25 % of the 0.25 mm value from 1 mm, `docs/validation.md` 2.1). The layered idealisation of topic 01 is the model error (0.4 to 2.2 % against the 3D solid). Direct, CG and SOR agree to 2e-8 K on five boards (1.7e-8 K on the 8-layer board, `docs/validation.md` 5; `docs/theory.md` 11 says 1e-8).

## 6. The via on the grid

A source in one cell of the five-point stencil has the potential of a hole of radius `r_eq = exp(-(gamma + 1.5 ln 2)) dx = 0.1985 dx` (gamma Euler's constant), so a barrel put on the cell of its centre under-constricts on coarse cells and over-constricts once `dx < 5 r_via`. The program spreads each barrel over a **footprint** of cells (weights `w_a`, lattice effective radius `r_t = e^(-1/4) r_via`), couples the plane means `T_l = sum w_a T_{l,a}` to the barrel nodes through a well `G_c = 2 pi S_l / ln(r_eff / r_t)` and eliminates the barrel nodes (Kron reduction): the matrix gets rank-one couplings between the plane means, `K` stays symmetric positive semidefinite and no unknown is added (`viawell.py`; figures V1 to V4 of `docs/images`). The via effect then converges with the cell (worst error 0.7 % at 1 mm, 0.5 % at 0.5 mm, 0.4 % from 0.25 mm against a fine-grid reference, `research/point-via-convergence/`). The Peaceman well radius is [Peaceman1978] (status S: the 0.1985 here is computed, not taken from the paper).

## 7. How the program does it

`pcbthermal/fvm.py` (`Network`, `solve_steady`, `solve_sor`, `transient_from_network`, `step_responses_from_network`), `docs/theory.md` section 2. The transient part is topic 07.

## 8. Where it is tested

`docs/validation.md` sections 2 (scenarios), 5 (solvers), `research/models-comparison/` (figure 2 grid convergence, figure 3 solver equivalence), `research/solid3d-verification/`.

## 9. Related topics

01 (the model), 03 (the node-centred comparison), 07 (time), 16 (a faster solver for very large boards), 17 (what goes into `S` per cell).

## 10. Sources

* Finite-volume discretisation, harmonic means at interfaces: [Patankar1980]. A balance on every cell conserves energy locally and globally: [EymardGallouetHerbin], [SpringerFVHeat], [Khouider].
* Direct sparse solver: [SciPySuperLU]. SOR, Young's optimum `omega = 2 / (1 + sqrt(1 - rho^2))` for consistently ordered matrices (Theorem 4.16, equation 4.47, pages 126 and 127), convergence for `0 < omega < 2` (Theorem 4.10), multicolouring: [Saad2003] (read); [Young1950] (the original, not obtained). The lattice sink and the well radius: [Peaceman1978] (S).
* The rest is own computation: [L-validation].

*What was read and what was not verified:* the formulas come from `docs/theory.md` section 2 (read in full); [Patankar1980] was not opened here; the SOR statements rest on [Saad2003] pages 90 to 127 (read), the well radius on a computation of this repository.
