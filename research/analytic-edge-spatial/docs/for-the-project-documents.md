# Text for the project documents (to adopt with the feature)

## docs/theory.md 6, equations (replaces the edge paragraph)

The edge is cooled by the series itself. With the edge parameter of the layer `beta_l = h_side s_l / S_l` taken common to the layers, `beta = h_side sum(s_l) / sum(S_l)` (this keeps the
total edge conductance), each direction of length `L` is expanded in the eigenfunctions of `phi'' = -lam^2 phi` with `phi' = +beta phi` at 0 and `phi' = -beta phi` at `L`. On `u = x - L/2`,
`Lh = L/2`: even `cos(lam u)` with `lam Lh tan(lam Lh) = beta Lh`, odd `sin(lam u)` with `lam Lh cot(lam Lh) = -beta Lh`, ordered by `lam`; norms `Lh +- sin(2 lam Lh)/(2 lam)`. They are
orthogonal, and `(m pi / L)^2` of (6.1) becomes `lam_m^2`, the factors `eps_m / W` become `1 / norm_m`. With `beta = 0` they are the cosines. The vertical coupling of the layers is unchanged
(the basis is the same for every layer). Source: [Muzychka2003Part2] eq. 12 to 21 (the edge-cooled channel, centred source, `delta tan delta = Bi_e`), checked against an independent 3D solver
(0.06 to 1.06 %) in `research/analytic-edge-spatial` README 2.

## docs/theory.md 6, limits (replaces the sentence on the edge being at the mean temperature)

The edge is exact for layers with the same ratio `s_l / S_l`; with copper that differs by 3 to 4.5 times between layers one parameter is used for all of them and the hottest temperature was
measured up to 3.2 % and 5.4 % off against the FVM (the program warns above a spread of 3 when the edge carries over 20 % of the loss).

## docs/validation.md 4.1

Hottest rise against the FVM at 0.5 mm on 135 uniform boards (30 x 20 to 100 x 80 mm, 2 to 6 layers, 0.8 to 3.2 mm, `h_side` 10 to 200 W/m2K, part at the centre, a corner, an edge): mean
0.12 %, at most 0.32 % (the transfer to the faces: 3.36 %, up to 37 %). Time to 63 %: -3.3 to +6.0 % (faces: -31 to +38 %). What is left against the 3D solid (up to 17 % low on a thick board with
a large edge coefficient) is the layered idealisation.
