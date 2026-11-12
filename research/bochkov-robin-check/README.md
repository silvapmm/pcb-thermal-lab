# Bochkov and Gibou (2019): the Robin scheme of the cut-cell edge film, read and reproduced

*Status (audit 2.6.1): reviewed and closed; the film of the program (`fvm.Network._cut_edge_film`, 2.6.0) is the scheme confirmed here. Review in section 5.*

Question: is the boundary film of the proposal in `research/cut-cell-links` (aperture links, film in series with the conduction from the cell centre to the closest outline point, denominator floored at 0.25; taken from Barrett, Fogelson and Griffith 2022 eq. 12 to 14, "based on Bochkov et al.") the same as the Robin scheme of Bochkov and Gibou (2019), what does the original add (kinks, small cells, order of accuracy), and does anything have to change in the executor's implementation (`fix/cut-cell-aperture-film`)?

The source is chapter 1 of the dissertation of D. Bochkov (*Computational Methods for Solidification of Multicomponent Materials and Moving Boundary Problems in Physics of Inhomogeneous Polymers*, UC Santa Barbara, 2020; eScholarship item 3qj3t08h), which is the paper of J. Comput. Phys. 376 (2019) 1156-1198. Page numbers below are printed page (PDF page); the offset is 15.

## 1. What the thesis says (read by image: pp. 19, 22, 23, 26, 39, 51; text layer for the rest of pp. 18-61)

### 1.1 The scheme (section 1.4)

Problem (1.1)-(1.2): `-div(mu grad u) + k u = f` in Omega, `mu du/dn + alpha_p u = g_p` on every smooth piece Gamma_p of the boundary (n outward). Cell-centred finite volumes, the cell C_ij centred on the node; integrate over C_ij and Omega (eq. 1.3, p. 17 (32)):

`sum_p int_{C_ij ∩ Gamma_p} alpha_p u dGamma  -  int_{∂C_ij ∩ Omega} mu du/dn dGamma  +  int k u dOmega  =  int f dOmega + sum_p int g_p dGamma`.

* **Fluxes between cells, symmetric form (eq. 1.7, p. 19 (34))**: `mu_{i+1/2,j} (u_{i+1,j} - u_ij)/dx * L_{i+1/2,j}` with `L` the length of the cut face inside Omega, `mu` at the face centre; "straightforward to show symmetric". This is the aperture link of the proposal (`a S dy/dx` with `a = L/dy`). Truncation `O(h^D)` per cell integral.
* **Fluxes, higher-order form (eq. 1.8, pp. 20-21 (35-36))**: the same with the flux at the centroid of the cut face and the normal derivative interpolated between neighbouring faces; needs the diagonal neighbours, non-symmetric.
* **Robin term, symmetric form (eqs. 1.9-1.14, pp. 21-23 (36-38))**. One smooth piece in the cell: `int alpha u dGamma ≈ alpha(r_G) u(r_G) L` (eq. 1.10), `L` the length of C_ij ∩ Gamma, `r_G` the foot of the normal through the cell centre, `d = phi/|grad phi|` the signed distance (phi negative inside, so `d < 0` for a centre inside). Taylor: `u_ij = u(r_G) + d du/dn(r_G) + O(h^2)` (1.11); with the boundary condition `mu du/dn + alpha u = g` at r_G (1.12):

  `u(r_G) = u_ij mu/(mu - alpha d) - g d/(mu - alpha d)`   (1.13)

  `int alpha u dGamma = u_ij mu alpha L/(mu - alpha d) + g d alpha L/(mu - alpha d)`   (1.14, as printed)

  **Sign in the print**: (1.14) shows `+` before the `g` term while (1.13) has `-`; with the `-` of (1.13) the term moves to the right-hand side with `+`, which is what the section 1.4.6 list gives ("add to RHS" = `int g dGamma + g d alpha L/(mu - alpha d)`, p. 39 (54)). I take (1.14) as a misprint of the sign; the solver here uses the (1.13) and 1.4.6 form, and its tests (constant solution exact) fail with the other sign. The thesis says: "does not involve any value at neighbouring points, it preserves the symmetry". The diagonal gets `mu alpha L/(mu - alpha d)`.
* **Which is Barrett's film?** With `g0 = alpha L` (film per piece), `S = mu`, `d_in = -d` (positive inside): `g0 / (1 + g0 d_in/(S L)) = alpha L/(1 + alpha d_in/mu) = mu alpha L/(mu - alpha d)`. **The same number, term for term**; the proposal's `g_side/max(1 + H d/S, 0.25)` is eq. 1.14's diagonal with a floor.
* **Kinks (a cell with two pieces; eqs. 1.15-1.19, pp. 23-27 (38-42))**: the projection of a piece's centroid may fall outside the domain, so the accuracy drops. Instead expand `u(r) = u_ij + grad u . (r - r_ij)` (1.16) and fix the gradient from the two boundary conditions at the projections rho_1, rho_2 of the two piece centroids: `N grad u = (g_1, g_2)^T - u_ij (alpha_1, alpha_2)^T` (1.17), `grad u = b - a u_ij` (1.18), `a = N^-1 alpha`, `b = N^-1 g`; diagonal `sum_p int alpha_p (1 - a.(r - r_ij)) dGamma`, right-hand side `- sum_p int alpha_p b.(r - r_ij) dGamma + int g` (1.19). Remarks (pp. 27-28 (42-43)): the per-cell flux is `O(h^{D+1})` at kinks; more than two pieces is under-resolved (least squares); `N` becomes singular when the two sides are almost parallel and the ordinary form must then be used per piece. Section 1.4.6 prints the right-hand side of the kink case as that of the smooth case (a copy of the first line, the `b` term is missing there).
* **Non-symmetric (superconvergent) form (eqs. 1.20 and the least-squares of pp. 29-33 (44-48))**: the Robin integral by the value at the centroid of the piece, `u` there from a weighted least squares on the 3x3 neighbours plus the boundary conditions (`3 x 3` matrix `X^T W X`). Truncation third order per cell, first order after scaling by the cell area; second-order solution and gradient (section 1.4.4, p. 35 (50)); needs diagonal neighbours (8 in 2D, 26 in 3D), not symmetric (solved with BiCGSTAB and multigrid, p. 40 (55)).
* **Truncation (section 1.4.4, p. 35 (50))**: per cell integral, symmetric scheme second order, non-symmetric third; scaled by the cell area `O(h^D)`, so `eps_tr = O(1)` (formally inconsistent at the boundary nodes, as every cut-cell scheme of this kind) for the symmetric scheme and `O(h)` for the other. Expected and shown numerically: **symmetric scheme: second-order solution, first-order gradient**; non-symmetric: second order in both.
* **Fall-back for small cells (section 1.4.5, pp. 36-38 (51-53))**: it belongs to the NON-symmetric scheme only: a cell without enough valid neighbours (a "hanging" cell) falls back to the symmetric formula, or is merged with a valid neighbour (strategy 2 of 1.5.2, works in 2D; in 3D the values at fall-back cells are discarded, strategy 3). **The symmetric scheme needs no fall-back ("always produces a valid discretization")** and is used with no merging of small cells.
* **Non-singularity (section 1.4.6, pp. 38-40 (53-55))**: for non-negative `k` and `alpha_p`, if `mu - alpha d > 0` (and `1 - a.(r - r_ij) > 0` for kink cells) the diagonal is non-negative, the matrix is diagonally dominant and irreducible (strongly connected graph), hence non-singular (eq. 1.21, p. 39 (54)). With `d < 0` (centre inside) the condition always holds; it can fail only for a centre OUTSIDE Omega (`d > 0`) when `alpha d >= mu`, i.e. "sufficiently refined grids, `h < C min(mu/alpha)`" (p. 23 (38)). The thesis puts **no floor**: "even when the resolution does not satisfy (1.21) the system is still invertible" (p. 39 (54)); the sign of the diagonal and the M-matrix property are not claimed then.
* **Integrals** (1.4.7, appendix 1.A): geometric reconstruction by simplices with level sets (linear or quadratic), needed for kinks; not used here (the geometry of the test is exact).

### 1.2 The numerical results (section 1.5, pp. 44-61 (59-76))

Plots only, no error tables (log-log, L-infinity, maximum over `nx x ny` = 10 x 10 relative placements of the grid, 16^2 ... 1024^2 cells in 2D, 16^3 ... 128^3 in 3D). Statements: symmetric scheme **second-order solution, first-order gradient**; non-symmetric second order in both (pp. 51-52 (66-67)); condition number grows like `h^-2`, equal for both schemes. The triangle test (section 1.5.2, p. 50 (65)): corners (0.74, -0.86), (-0.83, -0.11), (0.37, 0.87), `u = sin x cos y`, `mu = 1`, `k = 0`, `alpha = 1, 0, x - y + (x + y)^2` on the right, bottom and left sides (negative on part of the left side), grid `[-1, 1]^2`; a plot value (fig. 1.21, p. 51 (66)) of about 1e-5 at the finest grid is read from the plot and is only an order of magnitude. Union of two disks: the gradient converges with order 1.75 at the acute inner kinks (p. 54 (69)).

## 2. Reproduction (`lib/robin2d.py`, `scripts/study_triangle_disc.py`, `scripts/study_stiff_and_corner.py`)

Independent solver written for this folder (NumPy, SciPy; imports nothing of the program): exact face lengths by clipping and circle intersection, exact boundary pieces by breakpoints on the grid lines and 4-point Gauss quadrature, cell area by 64 midpoint strips, the cell is a node when any part of the domain touches it. Schemes: `bg` (eq. 1.7 + the (1.13)/1.4.6 form of 1.14 per smooth piece, eq. 1.19 for a cell with two pieces), `bg_nokink` (1.14 per piece with the distance to its own line), `film` (the proposal: one distance per cell to the closest point of the WHOLE outline, denominator `max(1 - alpha d, 0.25)`, data scaled with the same factor), `nofilm` (alpha L u_ij at the cell centre).

Defect found and fixed on the way (regression test `test_triangle_geometry_closed_forms` and the disc order test): a cell was dropped when its volume fell below the strip resolution although a cut face of positive length joined it to a neighbour; one spike of 3.5e-3 at a placement of the disc (all orders stalled near 1). A cell now counts when it has a volume, a cut face or a boundary piece. A first film variant also took the `alpha` of one piece for the whole cell at a corner (the corner cell mixes the sides with `alpha` 0 and `alpha_3`): wrong; each piece keeps its own `alpha` and `g`, only the distance `d` is common.

### 2.1 Convergence (fig. 1; `study_triangle_disc.py --nsh 4`; max over 4 x 4 placements; L-infinity at the cell centres inside; gradient by central differences where the 3 x 3 stencil is inside)

Triangle of the thesis (grid n x n nodes on [-1, 1], h = 2/(n-1)):

| n | nofilm u | bg_nokink u | bg u | film u | bg grad |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 33 | 2.33e-03 | 3.49e-03 | 6.49e-03 | 3.99e-03 | 4.44e-03 |
| 65 | 7.04e-04 | 1.13e-03 | 1.63e-03 | 1.25e-03 | 1.89e-03 |
| 129 | 2.67e-04 | 3.51e-04 | 4.19e-04 | 3.14e-04 | 7.97e-04 |
| 257 | 5.43e-05 | 1.23e-04 | 1.19e-04 | 1.22e-04 | 4.11e-04 |
| fitted order u / grad | 1.77 / 1.05 | 1.86 / 1.13 | 1.94 / 1.30 | 1.91 / 1.14 | |
| last-pair order u / grad | 2.30 / 0.99 | 1.52 / 0.88 | 1.81 / 0.96 | 1.37 / 0.88 | |

Disc (centre (0.1, -0.05), radius 0.7, `alpha = 2 + sin(x + y)`, `u = sin x cos y`):

| n | nofilm u | bg u | film u | bg grad |
| ---: | ---: | ---: | ---: | ---: |
| 33 | 6.13e-03 | 5.74e-04 | 5.31e-04 | 2.90e-03 |
| 65 | 2.88e-03 | 1.60e-04 | 1.54e-04 | 1.38e-03 |
| 129 | 6.82e-04 | 4.20e-05 | 4.14e-05 | 7.32e-04 |
| 257 | 3.21e-04 | 1.09e-05 | 1.06e-05 | 3.84e-04 |
| fitted order u / grad | 1.36 / 0.61 | 1.87 / 0.99 | 1.82 / 0.94 | |

* **The published orders are reproduced** for the symmetric scheme: second order in the solution (1.9, last pair 1.8 on the triangle; 1.9 / 1.95 on the disc), first order in the gradient (1.3 / 0.96; 0.99 / 0.93). The absolute level at n = 257 extrapolates (second order) to about 7e-6 at 1024^2, the order of the 1e-5 read from the plot of fig. 1.21 (plot reading, not a table).
* **The film without the Taylor distance (`nofilm`) is not consistent** on the smooth disc (order 1.4, errors 30 to 40 times the film's at n = 257): the film term is what gives the order. On the triangle `nofilm` happens to be the smallest (alpha is 0 on one side and changes sign on another, so the film correction is small there): the film changes the constant, not the order, on this problem; stated as measured.
* **The proposal's film (one distance per cell to the closest point of the whole outline, floor 0.25) equals eq. 1.14 on a smooth boundary** (disc: 1.06e-5 against 1.09e-5; the floor never binds) and is as good as the thesis' kink treatment on the triangle: 1.2e-4 against 1.2e-4 (bg) and 1.2e-4 (`bg_nokink`) at n = 257; the scatter between schemes is smaller than the scatter over the placements. At the vertices (error inside 3.5 h of a vertex against the rest, 3 x 3 placements, n = 257): bg 1.10e-4 / 1.05e-4, film 9.6e-5 / 6.6e-5, bg_nokink 8.7e-5 / 7.0e-5, nofilm 5.3e-5 / 3.4e-5: **the corner cells are not worse than the rest for any scheme**, and the kink treatment of the thesis (1.19) brings no measurable gain in the solution; it gives a gradient about 1.5 times smaller (4.1e-4 against 6.0e-4 at n = 257), which the program does not use.

### 2.2 The stiff edge, where the thesis stops (fig. 2; `study_stiff_and_corner.py`)

The condition (1.21) holds for centres inside; for a centre outside (sliver cell, `d > 0`) `1 - alpha d` goes to zero and negative when the cell Biot number `alpha h/mu` is of the order of one. Disc, `alpha = s (2 + sin(x + y))`, L-infinity error (3 x 3 placements):

| s | n | alpha_max h | nofilm | eq. 1.14, no floor | film, floor 0.25 | film, floor 0.5 | 1/(1 + alpha d) for d > 0 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 65 | 0.09 | 1.21e-03 | 1.62e-04 | 1.60e-04 | 1.60e-04 | 1.29e-04 |
| 10 | 17 | 3.75 | 3.45e-02 | 1.08e-02 | 5.71e-03 | 8.80e-03 | 8.64e-03 |
| 100 | 33 | 18.75 | 1.97e-02 | 2.64e-02 | 1.01e-02 | 1.09e-02 | 1.00e-02 |
| 1000 | 33 | 187.5 | 2.26e-02 | **2.92e-01** | 1.25e-02 | 1.25e-02 | 1.24e-02 |
| 10000 | 33 | 1875 | 2.46e-02 | **2.95e+00** | 1.27e-02 | 1.27e-02 | 1.27e-02 |

(the unfloored equation has 12 to 101 cells with a negative denominator in the stiff rows). **The unfloored equation 1.14 breaks at stiff edges (errors of 0.3 to 12), the floored series film does not** (errors 1e-2, below `nofilm`, falling with h), floors 0.25 and 0.5 and a smooth `1/(1 + alpha d)` replacement differ by 0 to 60 %: the floor is a safe rule and its value is not critical. The pairing matters: the data must be scaled with the same factor as the conductance (`g/den`, the program's `g_amb T_amb` form); with the thesis' right-hand side `int g + g d alpha L/den` and a floored `den` the pair is inconsistent and the stiff errors rise to 4 to 450 (a first version of this study did that). The constant solution is reproduced to round-off by `film` at every stiffness (test).

## 3. Differences between the thesis and the adopted scheme

| item | thesis (symmetric scheme) | `research/cut-cell-links` `aperture+film` | consequence |
| --- | --- | --- | --- |
| flux between cells | `mu_face L/dx (u_nb - u)`, `L` cut face | `a S dy/dx`, `a = L/dy` (min of the two sides' inside lengths) | same (S the harmonic mean of the physical sheets instead of mu at the face centre: a layered-model choice) |
| edge film | eq. 1.14: `mu alpha L/(mu - alpha d)`, `d` to the foot of the piece's own line | `g0/max(1 + g0 d/(S L), 0.25)`, `d` to the closest outline point | identical on a smooth edge; differs at corners and by the floor |
| data/ambient term | `int g + g d alpha L/(mu - alpha d)` (as the 1.4.6 list) | ambient conductance changed by the same delta as the film (`g_amb T_amb`) | equal without the floor; only the second is consistent when the floor binds |
| corner cell | gradient from two boundary conditions (1.17-1.19) | one `d` (closest point), the whole edge length | measured equal in the solution on convex corners (2.1); re-entrant corners not tested here |
| small or hanging cells | none for the symmetric form (fall-back and merging belong to the non-symmetric form) | none | same |
| centre outside, `alpha d >= mu` | assumed not to occur on a fine grid (1.21), no remedy | floor 0.25 | the floor is needed and measured safe (2.2) |
| symmetry | symmetric (and the non-symmetric variant for second-order gradients) | symmetric (SPD, symmetric LU stays valid) | keep symmetric |
| order | second order in the solution, first in the gradient | second-order class (measured in `research/cut-cell-links`) | confirmed here on an independent problem |

## 4. Limits

* Convex corners and a smooth disc only; the re-entrant corner (the small T of the proposal, an inverted T) is not in this folder: the kink treatment (1.19) of the thesis assumes the two pieces of the cell, and the proposal's closest-point distance there was reviewed in `research/cut-cell-links` 10.4.
* One piece family, `mu` constant (the layered sheet in the program has a different conductance per cell and layer; the face value `S` and the film `H d/S` carry it), no time dependence, no vias.
* The non-symmetric scheme (eq. 1.8, 1.20), the three fall-back strategies, the 3D examples, the singular-solution and level-set-accuracy tests (1.5.4, 1.5.5) and the integration appendix were not implemented or run. The thesis' table of integration errors (1.5.1) was not reproduced.
* The grid error is a maximum over 4 x 4 placements (the thesis: 10 x 10), so the maxima are less stable than theirs.

## 5. Review

Independent review in the research audit of 2.6.1 (`releases/2.6.1/research-audit/`), on the program of the audit branch (`develop` 6bdef422 merged: 2.6.0 plus the 2.6.1 interface fixes). Status: **reviewed, closed; go** (nothing to adopt: the thesis confirms the film already in the program).

* **Re-run.** `scripts/study_triangle_disc.py --nsh 4` reprints every number of the tables of 2.1 to the digit (the tables are the 4 x 4 placements; the script's default is `--nsh 3`, which prints the same orders with other maxima, for example triangle `bg` 1.10e-4 at n = 257 instead of 1.19e-4: the command is now stated under 2.1's heading). `scripts/study_stiff_and_corner.py` reprints the table of 2.2 (the rows quoted are a subset of the 15 it prints) and the vertex errors of 2.1 (`bg` 1.10e-4 / 1.05e-4, `film` 9.6e-5 / 6.6e-5, `bg_nokink` 8.7e-5 / 7.0e-5, `nofilm` 5.3e-5 / 3.4e-5) exactly. 15 s and 13 s. The folder tests pass (5).
* **The program against the folder's claims.** `fvm.Network._cut_edge_film` (`pcbthermal/fvm.py` about line 425 to 466) puts `H L / max(1 + H d / S, EDGE_FILM_FLOOR)` per piece, `EDGE_FILM_FLOOR = 0.25`, `d` the signed distance from the node to the closest outline point positive inside (`geometry.signed_distance_to_outline`), so it is the `film` scheme of `lib/robin2d.py` with the program's sign convention; the change goes into `g_amb`, so the data carry the same factor as the conductance (INTEGRATION 2 point 2); a rectangle uses the half-cell distance per side. INTEGRATION 2 points 1 to 3 and 5 hold in the code and in `docs/theory.md` 2.1.1 (which cites the thesis, Papac and others and Barrett and others, and gives the sign of `d` of the thesis as the opposite one). Point 4 (a sliver with a cut face stays a node): with the exact cover a face of positive aperture has board on both sides, so both cells have a positive area; checked by argument and by `geometry.face_apertures` (apertures and covers snapped together only within 1e-9), not by a dedicated test.
* **Independent reference.** The solver of this folder imports nothing of the program and checks itself against a constant solution (exact for every scheme and stiffness) and the closed-form geometry of the triangle; the reproduced published statement is the order of accuracy (second in the solution, first in the gradient) and one order of magnitude read from a plot. The program's own film was checked against an independent two-sheet solver and a radial solver in `research/cut-cell-links` (README 10, `docs/validation.md` 32.1, 32.4); not repeated here.
* **Limits that stay** (section 4): convex corners only, constant `mu`, no time, the non-symmetric scheme not run; the re-entrant corner belongs to `cut-cell-links` 10.4.
* **Corrections made by the review**: the placement count of the tables of 2.1 is stated with its command; nothing else in the folder was wrong.

## What was read and what was not verified

* Read by comparing the page image with the text layer: PDF 34 (eq. 1.7), 37-38 (1.10-1.14), 41 (1.17-1.19), 54 (1.21 and the "add to diag / RHS" lists), 66 (fig. 1.20-1.21 and the order statement). Status R for those pages; the rest of chapter 1 pp. 33-76 (1.8, 1.9, 1.15, 1.16, 1.20, least squares, 1.4.4, 1.4.5, results 1.5.2 and 1.5.3) was read from the text layer of the born-digital PDF without an image comparison (status S under the rule of CLAUDE.md "Papers library and OCR"); the integration appendix, the introduction and chapter 2 were not read. The literature review of chapter 1 (pp. 21-25) was read in text; Papac et al. 2010 (symmetric Robin scheme, J. Comput. Phys. 229:875-889) and Arias, Bochkov and Gibou 2018 (J. Comput. Phys. 365:1-6) are cited there as the origin of the symmetric scheme and of the second-order-gradient variant: not obtained.
* The convergence plots carry no numbers; the only comparison with the publication is the order of accuracy, and one order of magnitude read from a plot.
* The finite-volume schemes of this folder are mine, written from the equations (the thesis' code is not available); they reproduce the stated orders, which is the check.
* Nothing of the program was changed.
