# Entering the program: the via correction for 2.4.5 (branch `fix/point-via`)

Nothing here is done in `pcbthermal/`. The numbers are those of `README.md` (sections in brackets); every claim of impact is measured on in-memory copies. The change moves results (the FVM, FDM and, at coarse cells, the 3D solid), so it goes through the executor, the reviewer and the whole battery.

It joins three proposals: the mean-potential via of `point-via-convergence/INTEGRATION.md`, the block SOR (c') of `sor-with-via-couplings/INTEGRATION.md` and the single footprint rule of the 3D solid. This folder adds the footprint restricted to the cells on the board, `gz_via` for the Lumped model, **the image of the edge (adopted, README 3.4)** and the guard on the block memory.

## 1. What changes (functions and files)

| File | Change | Prototype |
| :-- | :-- | :-- |
| `pcbthermal/viawell.py` (new) | lattice kernel table `a`, `disc_target_weights`, effective radius, Kron reduction `kron_barrel`, Peaceman conductance; **the edge term** `a_cont`, `image_energy`, `well_correction`, `well_conductance_image` (56 lines of code), and, when the edge term is negative on a footprint already enlarged to `r_eff = r_t`, a further enlargement until `ln(r_eff/r_t) + c > 0` instead of an infinite well (review, README 3.2: the corner at d = 0.3 mm, 0.5 mm cells, from -3.3 % to -0.3 %); vectorised area sampling (a table of the area of a disc against the offset of its centre in the cell, one per run) before use on boards with thousands of vias | `point-via-convergence/lib/viakernel.py`, `lattice.py`; `lib/edge_image.py` |
| `pcbthermal/fvm.py` `Network.__init__` | stop adding the barrel to `gz`; per via: footprint on the cells with `cover > 0` (weight x cover, renormalised, **required with the image**, README 3.3), sheet conductance of the well from the cell of the largest weight on the board, the edge term `c` from the axis-parallel walls within 6 cells (`walls_for`: box edges, or the axis-parallel segments of the outline, the nearest per axis); store `self.via_blocks` and `self.gz_via` (the barrel conductance at the cell `cell_index_of_point`, exactly what the loop adds today) | `lib/edge_patch.py` `via_hook_edge`, `walls_for` |
| `pcbthermal/fvm.py` `Network._assemble` | append `G_lm (e_l x w - e_m x w)(.)^T` for every pair of planes of every via | `program_patch.assemble_hook` |
| `pcbthermal/fvm.py` `Network.solve_sor` | block SOR (c'): colour the via blocks once, dense `Binv` per colour group, the two colours skip the via cells, relaxed block step after them; empty block list = today's path; **guard**: if the largest merged block exceeds a limit (proposal: 5 000 unknowns, about 200 MB of inverse), refuse SOR for that board with the message of the metal-block refusal ("use the direct solver") | `sor-with-via-couplings/lib/sorvia.py` `RB(block_over)`; `matrix_stats.block_structure` |
| `pcbthermal/fdm.py` `Network.__init__` | the same call with the node origin `-dx/2`, **no edge image** (the edge nodes are half volumes) | `program_patch.py` |
| `pcbthermal/lumped.py` | where it sums `net.gz` over the rings, sum `net.gz + net.gz_via` (one line); **without it the Lumped model loses its vias** (+10 to +20 K, README 4.7) | `edge_patch.lumped_sees_gz_via` |
| `pcbthermal/solid3d.py` `Solid.__init__` | one footprint rule for every via: the centred disc enlarged to `0.78 r_v`, a point when the cell is coarser; remove the "fits in the cell or spread" branch | `point-via-convergence/lib/solid_patch.py` `disc_eta` |
| `pcbthermal/analytic.py` | none | - |
| `pcbthermal/checks.py` | warnings, section 3 | - |

**Not proposed:** the fold of a cut footprint (identical to the restriction in every case, README 3.3); a target-radius rule by stack-up (A14, open); an image for a diagonal or curved outline edge.

## 2. Tests to add on the adoption branch

* From `point-via-convergence/INTEGRATION.md` 4: the via effect of the unit cell within 1.5 % of the fine-grid reference at 1, 0.5 and 0.25 mm; the gain of the 3 x 3 board within 0.3 K from 1 to 0.125 mm in the FVM and FDM; symmetry, zero row sum, energy balance; boards without vias bit-identical.
* From `sor-with-via-couplings/INTEGRATION.md`: SOR with vias against the direct solver to 1e-6 K on one filled via, a 0.8 mm copper-filled via, two vias in one cell and a dense array; a regression test that fails with today's `solve_sor`; a board with vias in `solver_equivalence.py`. **New:** a board with about 100 vias at 0.5 mm (the own field of `lib/real_board.py`, or 109 holes of the size of the Stormduino's) in which the block SOR matches the direct solution to 1e-6 K in at most as many sweeps as the board without vias (README 4.4: 0.9 to 1.0 times).
* From this folder (copy of `tests/`): the hook is identical to the prototype with the options off; `gz + gz_via` equals today's `gz` on the example board and on an array whose vias fall on cell lines (the Lumped result bit-identical); a footprint never touches a cell with `cover == 0`; the edge term: algebra (`test_edge_image.py`: one-cell footprint `D_lat = dx exp((pi/2)(1 - kappa))`, the corner's diagonal term, zero without walls).
* **The S1 board** (10 x 10 mm, four planes, 0.3 mm copper-filled via, 0.5 W in 3 x 2 mm): the via effect of the via 0.16 mm from the edge within 3 % of the resolved reference at 1 mm (README 3.1: +0.7 %), for the box edge, an outline at a grid line and an outline inside a cell (+1.1 %, +2.5 %), and the corner (-1.0 %), including the corner at d = 0.3 mm on 0.5 mm cells (-0.3 % with the enlargement, -3.3 % without: the regression of the review). The reference of the test must be a copy of `lib/sheets2d.py` (it imports nothing); the reference value E is 3.16 K (the reference is uncertain by about 0.7 %, so the tolerance is 3 %).
* 3D solid: the gain of the 3 x 3 board within 0.3 K of -4.5 from 1 to 0.1667 mm.
* The existing tests of the via fill (`tests/test_via_fill.py`) and of the examples have numbers that move: re-baseline after the reviewer has seen the new ones.

## 3. New warnings

* A via whose axis-parallel wall is within 6 cells is corrected silently; a via within **one drill radius** of an edge is clipped: warn "via touching the board edge".
* A via near a **diagonal or curved** outline edge (nearest outline segment not axis-parallel within 2 cells): warn "via near a slanted edge: its effect may be up to about 15 % too large at a 1 mm cell" (the +12 to +15 % of the uncorrected case, README 3.1; not measured for this geometry).
* **Block memory**: before the SOR, the largest merged block; above the limit use the direct solver (README 4.3). The matrix of the direct solvers has no such limit: 4900 vias at 0.5 mm give 244 000 unknowns and an estimated 0.72 GB of factors (README 4.2), the cell guard of the application stays the one that limits.
* The existing warning about the cell next to vias (`checks.py`) can say that at 2 mm and above the via is a fraction of a cell.

## 4. Numbers of `docs/validation.md` that move (README 4.8)

* **Section 2 (1 mm)**, the eight rows with vias: FVM -0.57 to -0.62 K, FDM +0.71 to +0.74 K (example board 85.81 -> 85.22 and 84.38 -> 85.12 degC; no heatsink 88.91 -> 88.29 / 87.47 -> 88.18; top copper over the full board 85.29 -> 84.72 / 83.94 -> 84.67; only U1 79.97 -> 79.38 / 78.54 -> 79.27); their percentage errors and the text "FDM 2 to 3 % low at 1 mm" (the FVM-FDM gap falls from 1.43 to 0.10 K). The 3D, Lumped and Analytic columns do not move.
* **Section 2.1**: FVM 83.00 / 85.34 / 85.81 / 85.87 / 85.95 -> 83.52 / 85.07 / 85.22 / 85.17 / 85.15; FDM (area) 82.29 / 84.66 / 84.38 / 85.22 / 85.67 -> 83.79 / 84.26 / 85.12 / 85.12 / 85.13; FDM (point) 85.36 / 86.18 / 85.15 / 85.58 / 85.80 -> 86.68 / 85.77 / 85.90 / 85.47 / 85.27; the paragraph that says the FVM "has no limit to converge to" must be rewritten.
* **Section 18**: copper-fill gain of the FVM -3.89 -> -4.19 K, FDM -4.09 -> -4.21 K (the text "-3.9 to -4.6 K" becomes about -4.2 K); Lumped and Analytic -6.3 to -7.0 K unchanged.
* **Section 5**: the SOR rows of the example board (block SOR, to be recomputed).
* The via rows of Lumped and Analytic (A6): unchanged.
* `research/via-fill`, `point-via-convergence` and `lumped-analytic-vias` quote program numbers (example board 85.81, copper-fill gain) that are "program as of 2.4.4"; they stay as the record.

## 5. Documented limits

* Uniform sheets at the via: the sheet conductance of the well is that of one cell; a via on a copper edge or a zone boundary is outside the claim.
* The target radius `0.78 r_v` is one constant, within -2 to +4 % of a 3D barrel (A14, open).
* On real layouts with 1 mm and 3.2 mm holes the cell dependence of the via effect is about 0.5 K (5 to 10 % of E) for both the program and the new treatment (README 4.5): the improvement shown on the simple boards is not visible there, and no board here has a reference.
* Cells of 2 mm and above: the via is a fraction of a cell; the error is in the sheet.
* Edge: axis-parallel walls only; `h_side` tested up to 10 W/m2K; none in the FDM, whose via within 0.3 mm of an edge is -4.5 to -10.1 % at 1 mm and -6.9 % at 0.5 mm (d = 0.16 mm) with the treatment (README 3.4, measured by the review).
* At 1 mm cells a via next to a source is -5.5 to +3 % in its effect depending on its position in the cell, with or without the image (README 3.1, review); the 3 % of the edge tests above holds for the positions along the edge that were swept.
* Block SOR memory for a via field with pitch near the cell: guard and fallback.
* The reference of S1 is uncertain by about 0.7 %; no measured board.

## 6. Decisions left to the maintainer

* The image of the edge enters (the rule of README 2 was met); its 56 lines are the size limit of the rule, so a simpler alternative is a documented limit: +12 to +15 % at 1 mm for a via within a cell of the edge, up to +26 % at a corner. With the review's enlargement the code is about 65 lines without the `def` lines (74 with them), above the 60 lines of the rule; the maintainer decides whether the size criterion still stands.
* The memory limit of the block (proposal: 5 000 unknowns) and whether SOR is refused or falls back to the direct solver.
* The version: 2.4.5 as a fix (the program's point via is a defect: non-convergence of -10 to -17 % at fine cells on the S1 board and of 0.5 K on real layouts), 2.5.0 if it is judged a feature; Young's omega stays a separate item.
