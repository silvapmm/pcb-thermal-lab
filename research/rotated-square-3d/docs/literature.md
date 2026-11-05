# The cut-cell literature: what the sources say, what was reproduced, what nobody documents

Text for the README of this folder (section 10 and the last section) and for `INTEGRATION.md`. Every statement says its source by key from `research/theory/BIBLIOGRAPHY.md`
and the page or equation (printed page numbers of the copy that was read). Numbers marked "plot" were read from a figure; none is used below except where said.

## 1. What was obtained and read

| Key | Copy read | Status here |
| :-- | :-- | :-- |
| [JohansenColella1998] | LBNL report LBNL-39908 (escholarship `08z7t0bm`, 28 pages) | **R** for printed pages 1 to 18 (scheme, error analysis, equations 13 to 18, numerical results up to Problem 3, Tables I and II checked on the page image); Tables IV and V, the conclusions and the references not read; the journal version not opened |
| [SchwartzEtAl2006] | LBNL report version (escholarship `0fp606kk`, 33 pages; dated 2004 on the cover) | **R** for printed pages 1 to 16 (the whole text; the figures are plots of errors and were not used as numbers) |
| [CrockettEtAl2011] | LBNL report version (escholarship `00q9z6st`, 39 pages) | **R** for the abstract, the introduction and sections 5.3 and 5.4 (the 3D sphere tests, printed pp. 26 to 27); the matching-condition flux formulas, the multigrid and sections 5.1 and 5.2 were **not read** |
| [CalhounLeVeque2000] | the author's copy (donnacalhoun.github.io, 38 pages) | **R** for printed pages 143 to 151 (sections 1 to 3: capacity function, fluxes on cut cells, the diffusion scheme) and the description of the tests of section 6; the advection part (sections 4, 5, 7, appendices) **not read** |
| [BarrettEtAl2022] | arXiv 2102.07966 (25 pages) | **R** for sections 1 to 3.1 and 3.3 (the cut-cell diffusion step with the Robin condition, eq. 5 to 15) and the description of the test of section 4.1; the semi-Lagrangian advection and the later tests **not read** |
| [BergerHelzel2012] | preprint (cs.nyu.edu, 28 pages) | **S** (abstract, introduction, and a text search for the small-cell passages; hyperbolic, explicit: not read as a method) |
| [ZhouMoriYao2026] | arXiv 2607.26341 | **S** (abstract and introduction only; it avoids cut cells, so it is not a source for this scheme) |
| chombo-discharge documentation, "Linear solvers" page | the page as returned by the fetch tool (an extract) | **S** (Robin condition on the embedded boundary, see 3) |
| Bochkov and Gibou (JCP 376, 2019, 1156) [BochkovGibou2019]; Papac, Gibou and Ratsch (JCP 229, 2010) [PapacEtAl2010]; Ingram, Causon and Mingham (Math. Comput. Simul. 61, 2003, 561) [IngramEtAl2003] | no open copy found (the Manchester Metropolitan record of Ingram et al. says "file not available") | **N** |
| EBChombo design document (davis.lbl.gov), Helzel, Berger and LeVeque 2005, the thesis of Johansen (1997), McCorquodale, Colella and Johansen 2001 | found by search, **not opened** (host not tried or blocked) | **N** |

The hosts osti.gov, core.ac.uk and par.nsf.gov refused every request from this machine (connection refused or 403); escholarship PDFs open through the fetch tool but not through `curl`.
Nothing of a third party is stored in the repository: the PDFs were converted in the scratchpad.

## 2. What the sources document (formulas with their places)

Notation: `kappa` volume fraction, `a` aperture (open fraction of a face), `A_f` front (boundary) length in the cell, `F` flux, `phi` the unknown.

1. **Divergence over the cut volume** (cell-centred unknowns): the integral of the divergence is the sum over the open parts of the faces and the front,
   `kappa (L phi) = (1/h) [ sum a_f F_f  +  alpha_B n_B . F_B ]` ([SchwartzEtAl2006] eq. 1, 4, p. 3 to 4; [JohansenColella1998] eq. 14, p. 8). The equation is multiplied by `kappa` to avoid the small
   volume in the denominator ([SchwartzEtAl2006] eq. 5, p. 4).
2. **Flux on a whole face**: central difference of the two cell values ([JohansenColella1998] eq. 15, p. 8). **On a partial face**: the aperture times the gradient linearly interpolated to the
   midpoint of the open part from the face and its neighbour, `F = a [ (1+a)/2 g_own + (1-a)/2 g_neighbour ]` (eq. 16, p. 9); in 3D the bilinear version ([SchwartzEtAl2006] eq. 6 and 7, p. 4 to 5, which also
   says that a three-face linear interpolation without the diagonal face was **unstable** for some configurations of adjacent small cells, p. 5). The values `phi_i` are those of the cell centres "even if those centres are beyond the domain boundary" ([JohansenColella1998] p. 8).
3. **Dirichlet flux on the front**: a quadratic through the boundary value and two values interpolated on the first two grid lines crossed by the normal through the midpoint of the front
   ([JohansenColella1998] eq. 17 and 18, p. 9 to 10; [SchwartzEtAl2006] eq. 8, p. 5, 18-cell stencil in 3D). Neumann: the flux is given ([SchwartzEtAl2006] p. 5). **Robin** is not in either paper.
4. **Accuracy**: the truncation error is second order in whole cells and first order in cut cells (`tau = O(h / kappa)` as written, [SchwartzEtAl2006] eq. 11 to 13, p. 7); the error of the solution is second order, because a cut-cell charge acts as a dipole of
   strength `tau h^2`, the Dirichlet condition giving an image charge ([JohansenColella1998] p. 6 and 10, and Table II, p. 15: the part of the error from the cut cells falls at rate 3, the interior part at rate 2). **Condition number** independent of the smallest `kappa` for the well-separated Dirichlet stencil
   (Figure 2, p. 7; the price is a non-symmetric matrix and no discrete maximum principle when the centre of the cut cell is outside, p. 7).
5. **Centroid unknowns** ([CalhounLeVeque2000] p. 148 to 151): the capacity function `kappa` of the cell is the open fraction (eq. 8 and 13); the flux through the open part of an edge is `h_edge/dx` times the flux at its midpoint (eq. 13); the gradient at the midpoint of a partial edge
   is found by **bilinear interpolation of the four neighbouring values taken at the centres of mass** (eq. 18 and 19, p. 150), which is formally first order at the edge but second order globally (p. 151); the boundary flux `H_ij` enters as `dt l_ij H_ij / (kappa dx dy)` (eq. 14 and 26) and is zero for an insulated wall; Crank-Nicolson, with the matrix non-symmetric (BiCGSTAB), "the presence of small cells ... does not place any unreasonable restrictions on the size time step" (p. 151). Its tests are advection and diffusion in a channel and advection in an annulus with **no-flow** walls (Figure 15, `R1 = 0.25`, `R2 = 1.25`; pp. 165 to 167); no Robin condition and no conduction table.
6. **Robin (film) condition on a cut cell** ([BarrettEtAl2022] eq. 1b, 12 to 14, p. 3 and 5 to 6, following Bochkov and Gibou, not obtained): the sheet condition `D dq/dn + a q = g`; the flux through the boundary of the cell is `L_Gamma (g - a q(r))`, `r` the closest boundary point to the cell centre `x`, and `q(r)` comes from the Taylor step `q(x) = q(r) + d dq/dn(r)` with `d = phi/|grad phi|` the signed distance, solved together with the Robin condition; "this system is well posed for a sufficiently refined grid" (p. 6).
   In terms of resistances: the cell value reaches the boundary through the conduction `d / D` in series with the film `1 / a`, so the film conductance is `a L / (1 + a d / D)`; `d` is negative when the cell centre is outside the domain. The face fluxes use `D L_g (q_{i+1} - q_i)/dx`, `L_g` the length fraction of the face (eq. 10 and 11, p. 4 to 5), on **cell-centre** values, reconstructed from the centroid unknowns by moving least squares or radial basis functions (section 3.3, p. 7 to 8; a linear reconstruction in the diffusion step is "more robust"). Implicit trapezoidal rule, GMRES (p. 6). The static cut-cell part is the part used here.
   The chombo-discharge documentation (summary only, status S) writes the Robin condition as `d_n Phi = (C - A Phi_EB)/B` with `Phi_EB` interpolated by an unweighted least-squares fit "using cells which can be reached with a monotone path of radius one around the EB face", with the cut cell itself in the stencil; it states no accuracy and says nothing on small cells.
7. **Small cells**: for implicit time stepping or the steady state there is no stability limit from the cut-cell size ([CalhounLeVeque2000] p. 151; [JohansenColella1998] p. 7 for the conditioning; [CrockettEtAl2011] abstract: stable and efficient for coefficient ratios up to 10^6 with multigrid). The small-cell problem is that of **explicit** schemes (the time step proportional to the volume): remedies are cell merging, flux redistribution, the h-box methods ([BergerHelzel2012] introduction, status S) and a "capacity form" with an enlarged capacity in small triangular cells ([CalhounLeVeque2000] sections 4 and Appendix, not read). The program's steady state and implicit transient are not affected.
8. **Published numerical cases with numbers**: only [JohansenColella1998] (Tables I to III, p. 15 to 17, and the definition of the problems, p. 13 to 14 and 17 to 18). [SchwartzEtAl2006] and [CrockettEtAl2011] show their errors as plots (sphere of radius 0.392, `sin(x) sin(2y) sin(3z)`; the heat equation on a sphere; a neutrophil geometry), [CalhounLeVeque2000] as plots and a few rates, [BarrettEtAl2022] as plots (Robin disc of radius 1, `D = 0.01`, `a = 1`, a manufactured Gaussian; "errors of the order of one percent" at 26 cells across the diameter, section 4.1).

## 3. What was reproduced

**Case: Problem 1 of Johansen and Colella** ([JohansenColella1998] p. 13 to 15): `Delta phi = 7 r^2 cos 3 theta` (the report prints a symbol that reads like pi; the exact Laplacian of the solution is 7 `r^2 cos 3 theta`), Dirichlet data from `phi = r^4 cos 3 theta`, the domain `r <= 0.30 + 0.15 cos 6 theta`, cells per unit length `N = 40 ... 640`.
The independent implementation `lib/jc_poisson.py` (nothing of the program imported; written from eq. 13 to 18: marching-squares front through the intersections with the grid lines, apertures, volume fractions, centroid for the right-hand side, partial-face interpolation, the quadratic front flux, the boundary shift of 0.1 % of the grid spacing for cells below 1e-6 as the report describes on p. 13) gives, with `scripts/study_cutcell_sources.py jc` (a few seconds):

| N | cut cells (pub / ours) | whole cells (pub / ours) | max kappa tau, cut cells (pub / ours) | max tau, whole cells (pub / ours) | max solution error (pub / ours) | 1-norm solution error (pub / ours) |
| --: | --: | --: | --: | --: | --: | --: |
| 40 | 208 / 208 | 400 / 400 | 1.20e-01 / 1.21e-01 | 1.66e-03 / 1.66e-03 | 5.85e-05 / 5.84e-05 | 8.34e-06 / 8.04e-06 |
| 80 | 420 / 424 | 1824 / 1824 | 7.71e-02 / 7.72e-02 | 4.15e-04 / 4.15e-04 | 7.36e-06 / 7.36e-06 | 1.02e-06 / 9.96e-07 |
| 160 | 856 / 856 | 7712 / 7712 | 4.20e-02 / 4.21e-02 | 1.04e-04 / 1.04e-04 | 1.17e-06 / 1.18e-06 | 1.07e-07 / 1.05e-07 |
| 320 | 1716 / 1716 | 31716 / 31716 | 2.18e-02 / 2.21e-02 | 2.59e-05 / 2.59e-05 | 1.68e-07 / 1.68e-07 | 1.80e-08 / 1.81e-08 |
| 640 | 3416 / 3428 | 128604 / 128596 | 1.11e-02 / 1.11e-02 | 6.49e-06 / 6.48e-06 | 2.27e-08 / 2.27e-08 | 5.02e-09 / 5.05e-09 |

*Figure 13 (`figures/fig_13_jc_published_vs_reproduced.png`): published (squares) and reproduced errors against N.* Agreement to three digits in the maximum error and the whole-cell truncation error, 3 % at worst in the cut-cell truncation error, 4 % at worst in the 1-norm (published values read from the page image; which of the report's norm normalisations the 1-norm column uses is not stated, the area-normalised one is shown; the cut-cell counts differ by up to 12 where the report's boundary representation differs from the exact intersections).
Defects found and fixed in this implementation on the way: a node within 0.1 % of the boundary left sliver cells of volume 4e-8 whose front stencil does not exist (two cells at N >= 320 gave errors of 1e-3 to 3e-3 until the report's boundary shift was applied); the first fix flagged whole cells with a flipped corner as empty and gave truncation errors of 0.3 to 165 (the tests now check the published tables).
The tests are `tests/test_cutcell_sources.py` (`test_jc_reproduces_the_published_tables`, the rate and the geometry).

**Not reproduced**: the numbers of [SchwartzEtAl2006], [CrockettEtAl2011], [CalhounLeVeque2000] and [BarrettEtAl2022] (plots only, or advective/moving problems); the adaptive refinement and multigrid of [JohansenColella1998].

## 4. The film boundary on a disc and an annulus (the closest representable version of the program's edge)

No source tests the case the program has: a thin sheet with face losses whose rim loses heat through a film. The closed form exists (`lib/sheet_robin.py`: `T = q/G + A I0(k r) + B K0(k r)`, `k = sqrt(G/S)`; its tests check the energy balance by quadrature and the limits), so the schemes were compared with it
(`scripts/study_cutcell_sources.py sheet`; a 20 mm disc or annulus, `S = 0.05 W/K`, `G = 20 W/m2K`, `q = 1000 W/m2`; five schemes on the same exact geometry (apertures from exact chords, `tests/test_cutcell_sources.py::test_shape_geometry_is_exact`), the sheet moved by 0, (0.37, 0.21) and (0.5, 0.5) cells against the grid). The schemes:
`program` (nodes at the cell centres, link = harmonic mean of the cover-scaled conductances over the centre distance, film `H L` on the node: the rule of `fvm.py`, re-implemented here and compared at the centroid, which is where a cell mean lives), `aperture` (centre nodes, link `a S`, film on the node: the partial-face flux of [JohansenColella1998]),
`aperture+bochkov` (as `aperture`, film conductance `H L / (1 + H d / S)` with `d` the signed distance from the cell centre to the circle: the Robin treatment of [BarrettEtAl2022] eq. 12 to 14), `links` (nodes at the centroids, two-point flux `a S/(d1 + d2)`, film on the node) and `links+strip` (`links` plus the conduction over half the depth of the open strip in series with the film).
Worst error in the cells that are whole (the temperature under a part and in the interior), as per cent of the highest rise, worst of the three shifts:

| case | cells per radius | program | aperture | aperture+bochkov | links | links+strip |
| :-- | --: | --: | --: | --: | --: | --: |
| disc, `H` 5 W/m K (h_side 3000), highest rise 1.462 K | 5 / 10 / 20 / 40 | 13.3 / 7.5 / 4.1 / 2.1 | 2.2 / 0.94 / 0.39 / 0.16 | 0.15 / 0.03 / 0.01 / 0.01 | 3.4 / 1.7 / 0.83 / 0.41 | 1.1 / 0.60 / 0.33 / 0.17 |
| disc, `H` 100 W/m K (rim nearly fixed), 0.545 K | 5 / 10 / 20 / 40 | 15.4 / 15.2 / 11.8 / 7.9 | 9.5 / 5.3 / 2.8 / 1.4 | 0.38 (two of three shifts ill posed) / ill posed / 0.03 / 0.01 | 12.0 / 6.5 / 3.4 / 1.7 | 3.1 / 1.7 / 1.0 / 0.53 |
| annulus (inner radius R/3), `H` 5 on both rims, 0.782 K | 5 / 10 / 20 / 40 | 16.9 / 8.6 / 6.1 / 2.6 | 2.2 / 1.2 / 0.42 / 0.20 | 0.60 / 0.14 / 0.04 / 0.02 | 3.6 / 2.1 / 1.0 / 0.56 | 2.5 / 1.1 / 0.51 / 0.27 |
| disc, `H` 0.016 W/m K (h_side 10), 43.1 K | 5 to 40 | below 0.02 | below 0.01 | below 0.01 | below 0.01 | below 0.01 |

*Figure 14 (`figures/fig_14_cut_cell_schemes_film_boundary.png`): a cut cell with the nodes of the schemes drawn, and the error of the five schemes against the cells per radius at `H` = 5.* All the schemes conserve the heat (rim + faces = source to 1e-10 of the power). The heat through the rim is within 0.3 % in every scheme (it is nearly fixed by the balance), so the totals hide the differences; the interior temperature shows them.
What the table says, and no more:
- the program's treatment of the cut cell (cover-scaled conductance) is 3 to 10 times worse in the interior than the cut-cell forms when the rim film is strong (`H` 5 or 100 W/m K), and it converges at about first order; with a weak film (the default `h_side` 10) all schemes are within 0.02 %: the effect is at high `h_side`, as the rest of this folder found;
- the film written as the literature writes it (`aperture+bochkov`) is the most accurate where it is defined (0.01 to 0.15 % at 5 to 40 cells per radius, `H` 5) but **is not defined when a cell centre lies outside the sheet by more than `S/H`** (it is `ill posed` above: `S/H` = 0.5 mm at `H` = 100 W/m K, cells of 2 and 1 mm); `S/H` for a two-layer board of 35 um copper (S about 0.03 W/K, my estimate from `k_Cu t_Cu`, H = `h_side` times 1.6 mm) is about 2 m at the default `h_side` 10 and 4 to 6 mm at `h_side` 3000 to 5000, so the condition would bind only for cells above a few mm and a stiff rim (thicker copper loosens it);
- `links+strip` is never ill posed and is the best of the others for a stiff film (0.5 to 3 %), `aperture` is better for a moderate film;
- the first-order behaviour of the schemes without the Bochkov film shows that the error is dominated by the film-to-node path, not by the face fluxes.
Limits of this case: one thin sheet (no vertical conduction, no laminate), a uniform source, circles only (a smooth outline: no re-entrant corner, no sliver of a polygon), the 2D solver is an independent re-implementation of the program's rule, not the program (the program on the layered round board is in section 5).

## 5. The program's prototype on the closest version

`lib/fvm_cutcell.py` (on the branch of this folder) run with `scripts/study_cutcell_sources.py proto` (the folder of the prototype is found in `lib/` or in `CUTCELL_LIB`), a 40 mm round two-layer board with a 3 mm part, peak at the centre of the hot cell and rim loss against the axisymmetric reduction (per cent; 1 and 0.5 mm cells):

| h_side | rise (K) | cell (mm) | links | links+strip | aperture | program |
| --: | --: | --: | --: | --: | --: | --: |
| 10 | 94.144 | 1 | +0.19 / -0.01 | +0.19 / -0.02 | +0.19 / -0.02 | +0.19 / -0.06 |
| 10 | 94.565 | 0.5 | +0.04 / +0.01 | +0.04 / +0.01 | +0.04 / +0.01 | +0.05 / -0.01 |
| 1000 | 48.309 | 1 | +0.22 / +0.17 | +0.44 / -0.04 | +0.33 / +0.06 | +0.69 / -0.27 |
| 1000 | 48.734 | 0.5 | +0.00 / +0.08 | +0.11 / -0.02 | +0.07 / +0.02 | +0.28 / -0.19 |

The peak at the centre is insensitive to the treatment of the rim (0.2 to 0.7 % at 1 mm), which agrees with section 4: the cut-cell error lives next to the outline. The prototype was **not** run on a case with a re-entrant corner against a published number (there is none).

## 6. What nobody documents, and has to be established here

1. **The film on the rim of a thin plate in a layered model.** The sources treat `D dq/dn + a q = g` for a bulk field (a chemical species, a temperature). The program's edge is a film per length of rim on every slab of a stack (copper, dielectric, copper) with a sheet conductance `S = k t` and the face loss: the reduction to the sheet is ours and the closed form of section 4 is the test. For the 3D solid (real slabs) no source applies beyond the 2D idea.
2. **Centroid unknowns with a two-point flux** (`links`, the form of the prototype: `a S dy/(d1 + d2)` between two centroids): [CalhounLeVeque2000] put the unknown at the centre of mass but interpolate the gradient bilinearly from four values (eq. 18 and 19); [BarrettEtAl2022] keep centroid unknowns but build the fluxes on cell-centre values reconstructed by MLS or RBF; [JohansenColella1998] and [SchwartzEtAl2006] use cell centres. A two-point flux between centroids along the line of the two centroids is **not in any source read**. It is symmetric and positive (an M-matrix, so no stability problem), but it is not consistent in the sense of the sources when the line of the centroids is not normal to the face; the numbers of section 4 show it first order and 2 to 4 times worse than the aperture form for the same cells.
3. **The strip depth of `links+strip`** (half of the open area over the rim length, capped at one cell): our choice. The literature quantity is the distance from the cell centre to the **closest boundary point** (Bochkov and Gibou via [BarrettEtAl2022]); the strip depth is a centroid-based analogue of it.
4. **The size of the cut cell in the film**: with the film on the node (the program, `aperture`, `links`) the node is treated as being at the boundary; nothing in the literature does that, it is the program's present rule, and the error of section 4 is its price.
5. **What a first implementation can take from the literature as it stands**: the flux on a partial face through the aperture and the volume-fraction divergence (sources 1 to 4), and the Robin film with the signed distance (source 6) together with the guard that the denominator `1 + H d / S` stays positive. Whether that combination (`aperture+bochkov`) also holds for the layered stack, for a polygon with re-entrant corners and for a part that crosses the outline, was not tested: the test on a circle is necessary, not sufficient.

## 7. Corrections to earlier statements of this folder

- README section 10 said "No published case reproduced" and that Johansen and Colella's tests are "Dirichlet problems on a circle and an annulus (report pages 12 and later)": the report's Problem 1 is a Dirichlet problem on a **flower-shaped** domain and Problem 3 is Laplace's equation between a circle with an oscillating radius and a square (printed pp. 14 and 18); there is no annulus. Problem 1 is now reproduced (section 3). The statement "pages 12 to 28 not read" is replaced by section 1 above.
- The statement that nobody documents the film variant is refined: the **Bochkov-Gibou film** is documented ([BarrettEtAl2022] eq. 12 to 14); what is not documented is the program's (the film on the node) and the centroid two-point flux of the prototype (section 6).
- The INTEGRATION statement "the scheme is a standard cut-cell finite-volume idea written from scratch; no source was opened for it": the aperture flux and the volume-fraction divergence are standard (section 2, items 1 and 2), the centroid two-point link is not (section 6, item 2).
