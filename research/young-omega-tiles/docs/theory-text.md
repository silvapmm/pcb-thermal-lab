# Text for `docs/theory.md` (solvers, SOR; the Analytic and Lumped via corrections)

Draft for the project documents; it enters `docs/theory.md` only if the maintainer adopts the proposals (see `INTEGRATION.md`). Symbols as in the folder README. Pictures:
figures 01 to 07 of `figures/`. Statements marked (hypothesis) are not yet backed by a run of this folder; the README replaces them by the measured numbers.

## A. The relaxation factor of the red-black SOR

### A.1 The iteration and the Jacobi matrix

The steady matrix is symmetric and positive definite, `K = D - N`, `D` its diagonal (the sum of the conductances of a node, including the loss to the ambient and the pin of the cells off a
board), `N` the off-diagonal part (the conductances between neighbours, positive here). Point SOR with the factor `omega` updates

`theta_i <- theta_i + omega (Q_i + sum_m G_im theta_m - D_i theta_i) / D_i`.

The six-neighbour stencil joins a node `(l, i, j)` only to nodes of the other parity of `l + i + j`: the graph is two-colourable, so the red nodes are updated all at once and then the
black ones, and the matrix is consistently ordered (Young). The Jacobi matrix is `J = D^-1 N`; it is similar to the symmetric `J_s = D^-1/2 N D^-1/2 = I - A_s`, with `A_s = D^-1/2 K D^-1/2`
(the matrix scaled to unit diagonal). The spectrum of `J_s` is symmetric (`+mu` and `-mu` come in pairs, because of the two colours) and

`rho_J = max mu = 1 - lambda_min(A_s)`.

### A.2 Young's relation and the optimum

For a consistently ordered matrix every eigenvalue `lambda` of the SOR matrix satisfies `(lambda + omega - 1)^2 = lambda omega^2 mu^2` for an eigenvalue `mu` of `J` (Saad 2003, Theorem 4.16,
eq. 4.47). The dominant `lambda` is

`rho_SOR(omega) = [ (omega rho_J + sqrt(omega^2 rho_J^2 - 4 (omega - 1))) / 2 ]^2` for `omega <= omega_opt`, and `rho_SOR(omega) = omega - 1` for `omega >= omega_opt`,

with `omega_opt = 2 / (1 + sqrt(1 - rho_J^2))`. The error is reduced by `epsilon` in about `ln(epsilon) / ln(rho_SOR)` sweeps. Above the optimum the radius grows as `omega - 1` (steeply); below it
the curve is flat and rises slowly towards `omega = 1`: an `omega` below the optimum costs little, an `omega` above it costs a lot. (Figure 02.)

For the 5-point Laplacian with fixed edges on `n x n` interior points `rho_J = cos(pi / (n + 1))` and `omega_opt = 2 / (1 + sin(pi / (n + 1)))`: this is the textbook case. The program's factor
`2 / (1 + sin(pi / n))`, `n` the longest side, is the optimum of such a plate: a square with fixed edge temperatures.

### A.3 Why the program's factor is low for a board that loses heat through its faces

Take a uniform plate with insulated edges, the conductance `g` between neighbours (`g = S` for a square cell, `S` the sheet conductance) and a loss `a = h dx^2` per cell to the ambient. The uniform
vector is the dominant mode and `1 - rho_J ~ a / (4 g + a) ~ dx^2 / (4 lambda^2)`, with the fin length `lambda = sqrt(S / h)`. The fixed-edge plate has `1 - rho_J ~ (pi dx / L)^2 / 2`,
`L` the side. The two are equal for `lambda = L / (pi sqrt(2)) = 0.225 L`. A multilayer copper board has `lambda` of the order of the board side or more, so its `1 - rho_J` is smaller than the program's
assumption, `rho_J` closer to 1 and `omega_opt` closer to 2 (1.9613 against 1.8609 on the 3 x 3 array board, `sor-with-via-couplings` 8.3). Coupling between the layers and the lateral
non-uniformity change the number, not the argument.

### A.4 Estimates of `rho_J` without the eigenvalues

* **Rayleigh bound** (one product, or none): the trial vector `x = D^1/2 1` gives `x^T A_s x / x^T x = (1^T K 1) / (1^T D 1)`, so by the min-max principle
  `rho_J >= 1 - (1^T K 1) / (1^T D 1)`. `K 1` is the vector of the conductances to the ambient (the links cancel), so `1^T K 1 = G_amb` and `1^T D 1 = 2 G_links + G_amb` (every link appears in
  two diagonal entries): `rho_R = 1 - G_amb / (2 G_links + G_amb)` from sums that the assembly can keep, no product. The via couplings of the mean-potential treatment have zero row sums and add
  their diagonal to `D`. The bound is exact when the uniform vector is the dominant eigenvector (a periodic plate with a uniform loss: `rho_J = 4 g / (4 g + a)`), and below `rho_J` otherwise: the
  `omega` it gives is on the safe side.
* **Lanczos** (`k` products): `k` steps of the Lanczos process on `J_s` started at `D^1/2 1`; the largest eigenvalue of the `k x k` tridiagonal matrix is a lower bound of `rho_J` that rises with `k`
  (Saad, *Large Eigenvalue Problems*, Theorem 6.4, eq. 6.42: `0 <= lambda_1 - lambda_1^(m) <= (lambda_1 - lambda_n) (tan theta(v_1, u_1) / C_{m-1}(1 + 2 gamma_1))^2`, `C` the Chebyshev
  polynomial, `gamma_1 = (lambda_1 - lambda_2) / (lambda_2 - lambda_n)`). The start vector is close to the dominant eigenvector, so `tan theta` is small.
* **Power method** (`m` products): on `(I + J_s)/2`, whose spectrum is in `[0, 1]` with the dominant eigenvalue `(1 + rho_J)/2`. On `J_s` itself the method does not converge, because `+rho_J` and
  `-rho_J` have the same modulus. The rate is `|lambda_2| / |lambda_1|` (Saad, op. cit., Theorem 4.1), close to 1 for a fine grid.
* **Adaptive** (no product): after `s` sweeps at `omega_0 < omega_opt` the ratio of successive corrections tends to the dominant `lambda` of the SOR matrix; Young's relation gives
  `mu = (lambda + omega_0 - 1) / (omega_0 sqrt(lambda))` and `omega = omega_opt(mu)`. Above the optimum the decay is `omega_0 - 1` and says nothing about `mu`: `omega` is only raised.

### A.5 Cost and the decision

A sweep is two products with `K` (two colours). An estimate that costs `k` products is `k / 2` sweeps. The sweeps saved are `sweeps(omega_program) - sweeps(omega_est)`. The direct solver is the
default of the program; the estimate is worth having only if `k / 2` is a small fraction of the sweeps saved and the SOR with the estimate does not lose to CG and the direct solve in
the cases where SOR is used as a comparison solver (the README of the folder has the measured numbers).

### A.6 With the mean-potential via couplings (variant c')

The colours iterate the stencil with the diagonal of the whole `K`; Young's relation is exact only for that part (the full `K` has triangles in its graph and is not two-colourable). The omega is
taken from the Jacobi matrix of `diag(K) + stencil` and the block step is relaxed by the same omega; the optimum measured on the full iteration is compared with it (README).

## B. The tile of the Analytic via correction and the Krogh well of the Lumped model

### B.1 The constriction

A sink disc of radius `a = e^{-1/4} r_v` (the target radius of the layered idealisation) at the centre of a circular cell of radius `R` with a uniform source and an insulated rim: the temperature
above the wall is `T(r) = I (R^2 ln(r/a) - (r^2 - a^2)/2) / (2 pi S (R^2 - a^2))` and the mean over the cell minus the wall is

`R_c = (1 / (2 pi S)) [ b^4 ln b / (b^2 - 1)^2 - b^2 / (2 (b^2 - 1)) - 1/4 ]`, `b = R / a`, tending to `(ln b - 3/4) / (2 pi S)`.

A model that carries only area means and joins the planes by the barrel conductance misses `R_c` in every plane.

### B.2 The tile Green function

The Analytic model expands the uniform-board solution in cosines and corrects it at the vias through tile means. With `M x N` modes `A_mn` (the layers coupled, tridiagonal in the layer index),
the response of the mean temperature of tile `r` of layer `l` to a unit power injected uniformly in tile `s` of layer `k` is

`G[(r,l),(s,k)] = sum_{m,n < M_G, N_G} (A_mn^-1)_{lk} e_m e_n / (W H) U_x[m, r] U_x[m, s] U_y[n, r] U_y[n, s]`,

`U` the cosine mean over the tile (`sinc`-like, `~ 1` for `k t << 1`, decaying for `k t >> 1`). The vias enter through the conductance matrix `C` (a via of tile `s` couples the layers `l`, `l + 1`) and
the system `(I + G C) y = y0` gives the tile means `y`. The program takes `M_G = min(M, 64)` whatever `M` is.

The self-term adds to the diagonal of `G` the resistance of the point sink read at its wall instead of at the tile mean:
`D = (ln(R_tile / (sqrt(n) a)) - 1/4) / (2 pi S n)` for `n <= 1` vias in the tile (`R_tile = t / sqrt(pi)`), and for `n > 1`
`D = ln(R_tile / r_cl) / (2 pi S) + R_c(S, r_c, a) / n`, `r_cl = sqrt(n) r_c`, `r_c = min(R_tile / sqrt(n), d_nn / sqrt(pi))`. The constant `1/4` is the difference of the mean of `ln r` over a disc
(`ln R - 1/2`) and between two points of a disc (`ln R - 1/4`). The barrel conductance of a via is shared among the four tiles around it with bilinear weights (the first moment of the sink).

### B.3 What the tile has to satisfy (hypothesis, to be measured in the README)

1. `t` at most the spacing of the vias (`~ 0.75 d_nn`): the formula for a tile with `n` vias is right only when the tile resolves the cluster.
2. `R_tile = t / sqrt(pi)` clearly larger than `a`: the self-term `ln(R_tile / a) - 1/4` must be positive and the barrel must be a small part of the tile.
3. `G` must resolve the tile: `M_G >= 2 W / t` modes (one wavelength per two tiles); with `M_G = 64` a tile of 1 mm is resolved on a board of 32 mm and not on one of 100 mm. The tail of the neglected
   modes grows with the board for a fixed tile.
4. The tile must not straddle an edge of copper or of a source: the mean over the tile of two temperatures (figure 05, right).
5. The number of unknowns is `N_t L`, `N_t` the active tiles (at most four per via); the solve costs `(2/3) (N_t L)^3`, `G` costs `2 L^2 N_g N_t^2 M_g`.

### B.4 The Lumped well

The ring network carries one mean temperature per ring and plane; a via in a ring is joined to the plane node through the well `R_c(S, R_cell, a)` of its cell (`R_cell` from the ring area per via,
or from the nearest-neighbour distance), and a cluster adds `ln(R_cell,macro / r_cl) / (2 pi S)`. A via outside the footprint sits at one radius and one angle, the ring has the mean: the lateral
gradient and its angular variation are not in the network; the result depends on the ring in which the via falls. This is a limit of the construction, not of the well.
