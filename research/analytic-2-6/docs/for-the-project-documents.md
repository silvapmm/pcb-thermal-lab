# Text for the project documents (to be adopted only with the per-layer edge and the local transient)

## docs/theory.md, Analytic steady model: the edge of layers with different sheets

The series is in the eigenfunctions of one edge parameter `beta0 = h_side sum(s_l) / sum(S_l)`. Layer `l` has its own `beta_l = h_side s_l / S_l`. In the weak form of layer `l`,
`S_l lam_mn^2 N_m N_n a_l,mn + S_l (beta_l - beta0) closed-integral(theta_l phi_m phi_n) + (faces, gaps) = projection of q`; the closed integral over the four sides reduces, by the
orthogonality of the eigenfunctions along each side, to the modal source
`qc_l = -S_l (beta_l - beta0) [ (Ex^T / Nx)(Ex a_l) + (a_l Ey^T)(Ey / Ny) ]`, and the coefficients satisfy `a = A^-1 (q + qc(a))`, solved by GMRES (4 to 9 products). With equal
`s_l / S_l` the source is zero. Against the finite-difference solution of the same sheets the result is within 0.1 %; against the FVM the hottest rise of 48 boards goes from a worst
case of 8.64 % to 4.07 % (mean 1.51 % to 0.90 %). Sources: derivation in `research/analytic-2-6/README.md` 2.1 (own, checked numerically); basis of the series Muzychka, Culham and
Yovanovich 2003, Part II (see the bibliography).

## docs/theory.md, Analytic transient: local vias and heatsinks

The transient keeps the tile conductances of the steady model in the modal equations on the lowest `K x K` modes (`K = 16`): `(A + D P^T s C P D / W H) c = lam Cap c`, with `a = D c`,
`D_mn = sqrt(e_m e_n)` the weights of the series, `P` the tile averages of the eigenfunctions, `C` the tile conductance matrix of the steady model and `s` one factor chosen so that the
steady rise at the part's hottest point equals that of the steady solve. Modes above `K` stay the uniform diagonal system. The smeared calibration it replaces read the time to 63 %
from -67 % to +113 % of the FVM on boards with a heatsink; the local system 0.1 to 9 % (nine of ten boards of the study).

## docs/validation.md, rows to add

Time to 63 % of the unit step against the FVM at 1 mm, 10 boards (`research/analytic-2-6/README.md` 3.2); per-layer edge on 48 boards (2.3); the limits (the 4 L board with a heatsink:
the layer-node capacity, +45 % against 1 mm and +23 % against 0.5 mm; the Lumped with a heatsink away from the part: -37 to -42 %).
