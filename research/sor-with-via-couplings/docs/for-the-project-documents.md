# Text for the project documents (when the via treatment of `point-via-convergence` is adopted and block SOR with it)

## `docs/theory.md`, solvers (replace the SOR bullet)

* *red-black SOR*, `theta_new = (sum_m G_m theta_m + Q) / D`, `theta <- theta + omega (theta_new - theta)`, with `omega = 2 / (1 + sin(pi / n_max))`, stopped on the **residual** of the assembled matrix (1e-9). The five-point and vertical stencil is two-colourable, so each colour is one array operation. The mean-potential via couplings are not: they join all the footprint cells of every plane of a via to each other (positive in-plane entries, negative entries across the planes), so a via is handled as a **block**: after the two colours, the unknowns of every via (footprint cells of all layers) are corrected together by the exact solution of their small dense block, relaxed by the same omega, `theta[b] += omega K[b, b]^-1 (Q[b] - K[b, :] theta)`; the blocks are coloured so that two blocks coupled through the stencil are never moved at once. The matrix is symmetric positive definite, and every step of a sweep lowers the energy error by `omega (2 - omega) r_g^T K_gg^-1 r_g`, so the iteration converges for 0 < omega < 2 whatever the layout of the vias; measured, it needs at most the sweeps of the board without vias for any stiffness of the via. A version that leaves the via entries out of the iteration (the stencil off-diagonals with the diagonal of the matrix) converges to the solution of another matrix and never reduces the residual of the true one: 19 to 27 K too cool on the 3 x 3 array and the example board (`research/sor-with-via-couplings/`).

## `docs/models.md`, linear solvers

SOR (red-black, with the via blocks) is a comparison solver: it reaches the direct solution to 1e-8 K and takes about 50 times longer than CG on the same board.

## `docs/validation.md`, section 5 (solvers)

Add a row: the board with vias (3 x 3 array, 0.5 mm, a dense 9 x 9 array and the example board): block SOR within 1e-8 K of the direct solver in at most as many sweeps as the same board without vias.

## Picture for `theory.md`

`research/sor-with-via-couplings/figures/fig_02_colouring_over_a_footprint.png`, `fig_04_the_matrix_with_via_couplings.png` and `fig_08_block_step_relaxed_and_omega.png` (copy to `docs/images/` when adopted).

## Separate fix: the relaxation factor (`docs/theory.md`, solvers)

The default omega `2 / (1 + sin(pi / n_max))` is the optimum of a square with fixed edge temperatures; a board loses heat through its faces, so the Jacobi spectral radius `rho_J` is closer to 1 and Young's optimum `2 / (1 + sqrt(1 - rho_J^2))` (exact for the red-black stencil, a consistently ordered matrix) is larger: 1.9613 against 1.8609 on the 3 x 3 board at 0.5 mm, 6.0 times fewer sweeps; 2.9 times on the example board at 1 mm.
