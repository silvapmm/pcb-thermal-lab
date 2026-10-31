# Entering the program: the via correction for 2.4.5 (branch `fix/point-via`)

**Draft written before any run.** The structure below is what the implementation will touch; every "measured impact" and every "to decide" is filled from `README.md` once the studies have run. Nothing here is done in `pcbthermal/`.

It joins three proposals that depend on each other: the mean-potential via of `point-via-convergence/INTEGRATION.md`, the block SOR (c') of `sor-with-via-couplings/INTEGRATION.md` and the single footprint rule of the 3D solid; this folder adds the footprint restricted to the cells on the board, `gz_via` for the Lumped model, and either the image of the edge or a documented limit.

## 1. What changes (functions and files)

| File | Change | Prototype |
| :-- | :-- | :-- |
| `pcbthermal/viawell.py` (new) | lattice kernel table `a`, `disc_target_weights`, effective radius, Kron reduction `kron_barrel`, Peaceman conductance; vectorised area sampling (one table of the area of a disc against the offset of its centre in the cell, per run) before use on boards with thousands of vias | `point-via-convergence/lib/viakernel.py`, `lattice.py` |
| `pcbthermal/fvm.py` `Network.__init__` | stop adding the barrel to `gz`; call `viawell` per via: footprint on the cells with `cover > 0` (weights times the cover, renormalised), `S` of the well from the cell of the largest weight on the board, store `self.via_blocks` and `self.gz_via` (the point conductance at the cell of the centre, as today) | `lib/edge_patch.py` `via_hook_edge` |
| `pcbthermal/fvm.py` `Network._assemble` | append `G_lm (e_l x w - e_m x w)(.)^T` for every pair of planes of every via | `program_patch.assemble_hook` |
| `pcbthermal/fvm.py` `Network.solve_sor` | block SOR (c'): colour the via blocks once, dense `Binv` per colour group, the two colours skip the via cells, relaxed block step after them; empty block list = today's path | `sor-with-via-couplings/lib/sorvia.py` `RB(block_over)` |
| `pcbthermal/fdm.py` `Network.__init__` | same call with the node origin `-dx/2` (no edge image: the edge nodes are half volumes) | `program_patch.py` |
| `pcbthermal/lumped.py` | read `net.gz + net.gz_via` where it sums `net.gz` over the rings (one line); nothing else | `edge_patch.lumped_sees_gz_via` |
| `pcbthermal/solid3d.py` `Solid.__init__` | one footprint rule for every via: the centred disc enlarged to `0.78 r_v`, a point when the cell is coarser; remove the "fits in the cell or spread" branch | `point-via-convergence/lib/solid_patch.py` `disc_eta` |
| `pcbthermal/analytic.py` | none (computes its own via conductances per tile) | - |
| `pcbthermal/checks.py` | new warnings, section 3 | - |
| the image of the edge | only if the S1 rule says yes: `viawell.edge_term(...)` and the walls of `edge_patch.walls_for`; otherwise nothing | `lib/edge_image.py` |

## 2. Tests to add on the adoption branch

* From `point-via-convergence/INTEGRATION.md` 4: the via effect of the unit cell within 1.5 % of the fine-grid reference at 1, 0.5 and 0.25 mm; the gain of the 3 x 3 board within 0.3 K from 1 to 0.125 mm in the FVM and FDM; symmetry, zero row sum, energy balance; boards without vias bit-identical.
* From `sor-with-via-couplings/INTEGRATION.md`: SOR with vias against the direct solver to 1e-6 K on one filled via, a 0.8 mm copper-filled via, two vias in one cell and a dense array; a regression test that fails with today's `solve_sor`; a board with vias in `solver_equivalence.py`.
* From this folder: the hook is identical to the prototype with its options off; `gz + gz_via` equals today's `gz` (the Lumped result of the example board bit-identical); a footprint never touches a cell with `cover == 0`; 3D solid: the gain of the 3 x 3 board within 0.3 K of -4.5 from 1 to 0.1667 mm; a via near the edge (the S1 board at 1 mm) within the tolerance S1 sets; a board with the number of vias of the Stormduino solves with the direct solver and with the block SOR to the same field.

## 3. New warnings (proposed, sizes to be set by the runs)

* A via whose footprint is cut by the board edge or the outline: "via near the edge: result within X % of the via effect" (X from S1) or, if the image is adopted, nothing.
* Memory of the via blocks: before assembling, the estimated dense coupling entries (`matrix_stats.estimate_dense_entries`); above a limit set from the S2 scaling, refuse the treatment with the cell that fits (as `solid3d.check_size` does), or fall back to the point via with a warning. The limit is a number the maintainer chooses from the table of README 4.2.
* Block SOR: when overlapping footprints merge into a block whose dense inverse exceeds a limit, say so and use the direct solver.

## 4. Numbers of `docs/validation.md` that move

From `out/validation_rows.txt` (not run): sections 2 and 2.1 (FVM, FDM and 3D columns of every row with vias; Lumped and Analytic must not move), section 18 (the copper-fill gain of the five models), the via rows of Lumped and Analytic (A6, unchanged by this work), section 5 (the SOR rows of the example board). The known preliminary figures of `point-via-convergence/INTEGRATION.md` 2 (example board 85.81 -> 85.22 degC FVM, 84.38 -> 85.12 FDM, differences up to 0.8 K) are to be replaced by these.

## 5. Documented limits (to be completed from the results)

* Uniform sheets at the via: the sheet conductance of the well is that of one cell; a via on a copper edge or a zone boundary is outside the claim.
* The target radius `0.78 r_v` is a constant within -2 to +4 % of a 3D barrel (A14, open).
* Cells of 2 mm and above: the via is a fraction of a cell; the error is in the sheet.
* An outline edge that is not parallel to an axis, and the FDM edge: no image.
* Thousands of vias on fine cells: fill-in and dense blocks; the limit and the fallback are in section 3.

## 6. Decisions left to the maintainer

Whether the image of the edge enters (rule in README 2, result in README 3.4); the memory limit of the via blocks; the version (2.4.5 as a fix if the correction is accepted as a fix, 2.5.0 if it is a feature); Young's omega stays a separate item.
