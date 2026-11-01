# Entering the program: the mirror image of the board edge in the via well

**Recommendation: adopt the mirror image (insulated or convective edge, FVM) in 2.5.0 on a `feature/via-edge-image` branch; do not adopt the Robin image.** Evidence: `README.md` 3 and 4. The text for the project documents is in `docs/theory-text.md`.

## 1. What changes (`pcbthermal/viawell.py` only, plus `checks.py` text)

The candidate code is `lib/edge_hook.py` (the `mirror` path); the Robin path (`phi_*` with `ell`, `_GL_X`, `_GL_W`) is **not** carried over. The change in the program:

1. `edge_walls(problem, via, reach)` (about 20 lines): the straight walls within `reach = 6 max(dx, dy)` of the via centre: the box edges, or the axis-parallel segments of the outline, at most one per axis (the nearest). Diagonal and curved segments give no wall.
2. `_lattice_log(di, dj, dx)` (5 lines): `ln dx + (pi/2)(a(d) - kappa)` at real offsets in cells (bilinear between the exact values of `lattice_kernel`; the floor of the offsets must be cast to `int`).
3. `edge_term(w, dx, via_xy, r_via, walls)` (15 lines): `c = sum over walls [P_lat(wall) - ln(2 max(delta, r_v))]` where `P_lat` is `w^T ln_lat(x_a - mirror(x_b)) w`; at two walls add the diagonal image with `D_true = 2 max(hypot(delta_x, delta_y), r_v)`.
4. In `build`, per via, only when `origin == 0` (the FVM; the FDM passes `-dx/2`) and a wall is found: compute `c`; if `ln(r_eff/r_t) + c <= 1e-9` enlarge the footprint (smallest disc, centre fixed, restricted to the board, with `r_eff >= r_t exp(-c) (1 + 1e-6)`; up to five passes, as `edge_hook.build_edge`), and use `well_conductance` with the denominator `ln(r_eff/r_t) + c` for every plane (`c` is the same for the planes of one via when the edge is insulated).
5. `well_conductance(s, r_eff, r_t, c=0.0)`: add the optional argument; with `c = 0` it is bit-identical to today.
6. `edge_via_indices` / `checks.check_via_limits`: the FVM no longer needs the "near the edge" warning for an axis-parallel wall; keep it for the FDM, the 3D solid, diagonal or curved edges, a via across the edge (centre within `r_v` of the wall), and a cell of 2 mm or more. The warning text should say what is left (FDM: via effect 4 to 10 % too small at 1 mm; 3D solid: about 19 points too large at 1 mm).

Not changed: the matrix assembly, the Kron reduction, the SOR blocks (the footprint can only grow, by the enlargement, and `unknown_blocks` reads the footprints), the Lumped and Analytic models (`gz_via`), the transient code, the 3D solid, the FDM.

## 2. Acceptance tests (numbers measured on `develop` tip `2f3bd73`; tolerances are the budget, not the measurement)

All on the board of `research/via-real-board/lib/edge_reference.py` (`edge_board`) with the 1/16 mm reference of `sheets2d` imported by the test or tabulated:

| test | measured now | pass if |
| :-- | :-- | :-- |
| via 0.16 mm from the insulated edge, 1 mm cell: via effect against the reference | program +14.5 %, image +0.7 % | within 2 % |
| the same at 0.5 and 0.25 mm | +0.1 and -0.2 % | within 1 % |
| d = 0.3, 0.5 mm at 1 mm | +0.7, +0.6 % | within 2 % |
| d = 1, 2, 4 mm (away from the edge) | image and program equal within 0.2 points | difference below 0.5 points |
| corner (two walls), d = 0.16 mm, 1 mm | program +26.0 %, image -1.0 % | within 2 % |
| outline cut on a grid line (x = 7 mm), d = 0.16 mm, 1 mm | +1.1 % | within 2 % |
| outline cut inside a cell (x = 7.0625 mm), d = 0.16 mm, 1 mm | +2.5 % | within 3 % |
| `h_side` 10 and 1000 W/m2K, d = 0.16 mm, 1 mm | +0.7 %, +1.5 % | within 3 % |
| no wall within 6 cells (the example board, the plate with vias) | bit-identical | exactly equal |
| matrix on the edge board (1 mm) | symmetric, row sums as without the via (4e-18 W/K), balance -8e-14 | `|K - K^T|` = 0, row-sum difference below 1e-12 W/K, balance below 1e-10 |
| cost of the term | 0.045 ms per via | below 1 ms |
| negative `c` (corner, d = 0.3 mm, 0.5 mm cell) | -0.3 % with the enlargement | within 1 %; no infinite well |

## 3. Impact on the frozen numbers

`example_cut_to_T` moves in the FVM by **-0.196 K at 2 mm, -0.0024 K at 1 mm**, 0 at 0.5 mm (`out/impact.txt`); the four other boards with vias (`example_board`, `profile_board`, `plate_vias`, `plate_lone_via`) do not move (bit-identical). The Lumped, Analytic, FDM and 3D records do not move. A pending shift (`tests/regression/make_pending.py`) is needed for the FVM `example_cut_to_T` records at 2 and 1 mm, folded at the refreeze. The validation tables that hold a via near an edge (none of the example boards) are not known to move; `docs/validation.md` 2.1 and 18 use vias away from the edges.

## 4. Risks

* **Walls found from the outline**: an outline made of many short axis-parallel segments (a staircase) would give a wall per axis at the nearest segment: the image of a wall that is only 1 cell long is wrong. The study did not test it. Mitigation: require the segment to extend `reach` beyond the via along the wall (as `edge_hook.walls_for` does within the segment's length plus `reach`) and a minimum length.
* **Two opposite walls near a narrow board**: one wall per axis, the nearest; the opposite wall's image is not added. A board narrower than about 10 cells with a via in the middle would be wrong by the second image (not tested).
* **Strongly cooled edges**: the image assumes `h_side` up to about 1000 W/m2K (copper planes). Above it the result is not improved and, for the via effect in percent, can be worse; the via effect there is below 1 % of the rise. Document.
* **Several vias near the edge**: each has its own `c`; overlapping footprints share cells, and the sum of the wells is no longer the image of the sum. Not tested; the via arrays of the real boards studied were 2.6 mm or more from the box edge (`via-real-board` 4).
* **Interaction with the cold-spot limit** (`docs/theory.md` 2.2): none expected, the weights are not changed except by the enlargement of a negative `c`.

## 5. What would be measured on the real code before the merge

The whole battery; `PCBT_FROZEN_CELLS=2,1,0.5` for the frozen numbers (only `example_cut_to_T`); the acceptance tests of section 2 as `tests/test_via_edge_image.py` (reference tabulated, with the 1/16 mm solver kept in `research/via-real-board`); the staircase outline and the narrow board as extra cases.
