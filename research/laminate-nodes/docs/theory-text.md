# Text for `docs/theory.md`: the laminate nodes (draft; numbers from README section 3; the face exponent and the law are decisions of the maintainer)

To be placed after section 1.2 (the layered idealisation) and replacing section 1.4 (a one-layer board: the laminate nodes), with the pictures of `figures/` (figures 1 to 4).

## 1.2a The gap as a ladder of nodes

**Symbols.** `d` thickness of a gap (m); `n` number of sub-gaps; `s_1 ... s_n` their thicknesses, `Σ s_k = d`; `k_z, k_p, ρc` the through conductivity, the in-plane conductivity and the volumetric heat capacity of the laminate of the gap; `A` the area of a cell; `t_a, t_b` the copper thicknesses of the layers above and below; `f_a, f_b` their copper fill in the cell (fractions); `F` the set of flagged cells.

A gap is the laminate between two copper nodes `a` and `b`. For a board of one layer it is the laminate between the copper node and the bottom face; the end node is then a laminate node that holds the bottom film (the board is a two-layer board whose second layer has no copper).

**Cutting.** The sub-gaps are symmetric about the middle: `s_k = d w_k / Σ w`, `w_k = r^{min(k-1, n-k)}`, with `r ≥ 1` the grading (1: equal; 2: the sub-gaps at the copper are half the middle ones). The number of sub-gaps follows the thickness: `n = min(n_max, max(n_min, ⌈d / s_max⌉))` (measured: `s_max` = 0.4 mm, `n_max` = 4, `r` = 1; README 3.3).

**Nodes.** A node sits at every boundary between sub-gaps (`n − 1` interior nodes) in every cell of `F`. The interior node `j` (between `s_j` and `s_{j+1}`) holds the laminate of thickness `h_j = (s_j + s_{j+1})/2`:

    lateral conductance   S_j = k_p h_j                   [W/K]
    heat capacity         C_j = ρc h_j A                  [J/K]
    edge exchange         G_edge,j = h_side h_j ℓ         (ℓ the board edge in the cell)

The copper node `a` keeps the copper and half of the first sub-gap: its laminate share changes from `d/2` to `s_1/2`, so `S_a ← S_a − k_p (d − s_1)/2` and `C_a ← C_a − ρc A (d − s_1)/2`; the node `b` likewise with `s_n`. (One layer: the copper node, whose slab holds the whole laminate in the old model, keeps `s_1/2`; the end node holds `s_n/2` and the bottom film.) Nothing is added or lost: the laminate is only redistributed, so the total heat capacity of the network is the program's *(identity, checked by `study_transient.py`)*.

**Links.** Consecutive nodes `k` and `k+1` are joined by

    G_k = (G_lam + G_via) d / s_k   ...   with the vertical correction below added to the first and last sub-gap,

where `G_lam = k_z A / d` is the laminate part of the program's vertical conductance and `G_via = k_cu A_via / d` the barrels of the vias in the cell (the barrel is part of every sub-link: a chain of homogeneous pieces is the single link, so the series of the sub-links is `G_lam + G_via` when nothing else changes). In the cells outside `F` the program's single link is kept and no interior node is used (its row is pinned: `G = 1 W/K` to the ambient, no coupling).

**Vertical correction.** A copper node sits at the middle of its layer; where the copper is absent in a cell (fill `f < 1`) the layer is laminate, and half of it lies between the node and the gap:

    d_eff = d + (1 − f_a) t_a/2 + (1 − f_b) t_b/2       (added to the first and the last sub-gap; barrels not corrected)

Exact in one dimension for `f = 0`, a free correction (no unknown).

**Reported peak (face term).** A part on the face of the top layer injects its heat at the node; where the copper is absent the half layer of laminate between the node and the face adds

    θ_face = θ_node + Q (1 − f)^p t_a / (2 k_z A),       f < 1,        p = 1 in the code, p = 0 closest on every board measured (README 3.6; decision open)

for the hottest cell of the footprint (not to the field). The exponent decides the partly covered cell (the 3D solid and the resolved reference mix the conductivities of a partial cell arithmetically and have no face drop where the heat enters the copper directly).

**The mask.** `F` = the cells where `min(f_a, f_b) < 1` (the laminate shows next to the gap), dilated by `m` cells with `m = ⌈d/Δx⌉ + 1` (a disc of that radius): a thickness of the gap plus a cell, so that the extra nodes of the bare cells are not walled in by single links (with no margin the overshoot was +3.8 % at n = 8, earlier folder). *(Variants and their errors: `study_mask.py`.)*

**Why it works, and the 1/n tail.** The temperature field in the laminate under a copper edge is singular on the edge line; the error of a piecewise-constant representation through the thickness falls like `1/n` (`e(n) = e_∞ + a/n`, README 3.3, (fit printed in README 3.3: e_inf within 1 % on 13 of 15 boards)). The error of the cell in the plane has the opposite sign for a cell that is too coarse, so the total error crosses zero at some `n` and the number of nodes is a cost-accuracy choice, not a convergence: the gap column of the tables is the accuracy of `n`.

**Cost.** Unknowns: `N (L + b) + Σ_gaps (n_g − 1)|F_g|` with `N` the cells, `L` the copper layers, `b = 1` for a one-layer board (the end node), against `N L (+ 2N)` in the program *(measured: README 3.11)*.

**Limits.** A window narrower than the gap it opens (`w < d`): the idealisation of one temperature per cell across the window; *(error from step 7)*. Copper finer than the cell: the scalar fill is the larger error. Blocks: not part of the construction.

## 1.4 (replacement) A one-layer board

The laminate under the copper is the gap of a board whose second layer is bare; the rule above decides n and the cells. Under solid copper (empty `F`) the laminate is the single link from the copper node to the end node: the program's old two nodes in every cell are the special case `n = 2`, `F = every cell`.

## Analytic and Lumped

The Analytic model has no cells: a layer is one sheet and its gap is the single link (the series film on a one-layer board), i.e. the **passive cell** of the rule everywhere; the construction is a statement about the cells that the Analytic does not have. The Lumped model aggregates the arrays of the FVM network into rings and therefore inherits the nodes and the links (measured, README 3.12: erratic on windows, so the Lumped is not given the nodes).
