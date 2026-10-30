# Text for the project documents (when the via treatment of `point-via-convergence` is adopted and block SOR with it)

## `docs/theory.md`, solvers (replace the SOR bullet)

* *red-black SOR*, `theta_new = (sum_m G_m theta_m + Q) / D`, `theta <- theta + omega (theta_new - theta)`, with `omega = 2 / (1 + sin(pi / n_max))`, stopped on the **residual** of the assembled matrix (1e-9). The five-point and vertical stencil is two-colourable, so each colour is one array operation. The mean-potential via couplings are not: they join all the footprint cells of every plane of a via to each other (positive in-plane entries, negative entries across the planes), so a via is handled as a **block**: after the two colours, the unknowns of every via (footprint cells of all layers) are corrected together by the exact solution of their small dense block, `theta[b] += K[b, b]^-1 (Q[b] - K[b, :] theta)`, a block Gauss-Seidel step. The matrix is symmetric positive definite, so the iteration converges for 0 < omega < 2 and, measured, as fast as the board without vias for any stiffness of the via. A version that leaves the via entries out of the iteration (the stencil off-diagonals with the diagonal of the matrix) converges to the solution of another matrix and never reduces the residual of the true one: 19 to 27 K too cool on the 3 x 3 array and the example board (`research/sor-with-via-couplings/`).

## `docs/models.md`, linear solvers

SOR (red-black, with the via blocks) is a comparison solver: it reaches the direct solution to 1e-8 K and takes about 50 times longer than CG on the same board.

## `docs/validation.md`, section 5 (solvers)

Add a row: the board with vias (3 x 3 array, 0.5 mm and the example board): block SOR within 1e-8 K of the direct solver in as many sweeps as the same board without vias.

## Picture for `theory.md`

`research/sor-with-via-couplings/figures/fig_02_colouring_over_a_footprint.png` and `fig_04_the_matrix_with_via_couplings.png` (copy to `docs/images/` when adopted).
