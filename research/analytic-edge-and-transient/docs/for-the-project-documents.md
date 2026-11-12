# Text for the project documents (to be adopted only with the per-layer edge and the local transient)

## docs/theory.md, Analytic steady model: the edge of layers with different sheets

The series is in the eigenfunctions of one edge parameter `beta0 = h_side sum(s_l) / sum(S_l)`. Layer `l` has its own `beta_l = h_side s_l / S_l`. In the weak form of layer `l`,
`S_l lam_mn^2 N_m N_n a_l,mn + S_l (beta_l - beta0) closed-integral(theta_l phi_m phi_n) + (faces, gaps) = projection of q`; the closed integral over the four sides reduces, by the
orthogonality of the eigenfunctions along each side, to the modal source
`qc_l = -S_l (beta_l - beta0) [ (Ex^T / Nx)(Ex a_l) + (a_l Ey^T)(Ey / Ny) ]`, and the coefficients satisfy `a = A^-1 (q + qc(a))`, solved by GMRES (4 to 9 products). With equal
`s_l / S_l` the source is zero. Against the finite-difference solution of the same sheets the result is within 0.1 %; against the FVM the hottest rise of 48 boards goes from a worst
case of 8.64 % to 4.07 % (mean 1.51 % to 0.90 %). Sources: derivation in `research/analytic-edge-and-transient/README.md` 2.1 (own, checked numerically); basis of the series Muzychka, Culham and
Yovanovich 2003, Part II (see the bibliography).

## docs/theory.md, Analytic transient: local vias and heatsinks

The transient keeps the tile conductances of the steady model in the modal equations on the lowest `K x K` modes (`K = 16`): `(A + D P^T s C P D / W H) c = lam Cap c`, with `a = D c`,
`D_mn = sqrt(e_m e_n)` the weights of the series, `P` the tile averages of the eigenfunctions, `C = C_via + C_sink` the tile conductance matrix of the steady model, and the
via part scaled by one factor `s` (`s C_via + C_sink`) chosen so that the steady rise at the part's hottest point equals that of the steady solve: the factor stands for the
constriction of the barrel, which the steady model has and the coupled block cannot hold; the heatsink conductances need none. Modes above `K` stay the uniform diagonal system.
The smeared calibration it replaces read the time to 63 % from -66 % to +84 % of the FVM at 0.5 mm on boards with a heatsink (+175 % with a 300 W/m2K heatsink and vias on
two layers); the local system -9.0 to +0.6 % on twelve boards (eleven within 4 %).

## docs/validation.md, rows to add

Time to 63 % of the unit step against the FVM at 0.5 mm, 12 boards (`research/analytic-edge-and-transient/README.md` 6.3); per-layer edge on 48 boards (2.3) and what it leaves (the laminate
sub-gaps of the FVM, always cold, 6.1); the limits (the 4 L board with vias and a 300 W/m2K heatsink: -8 to -9 %, on the fast side; the Lumped with a heatsink away from the
part: -30 to -42 %).
