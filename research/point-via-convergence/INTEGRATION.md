# Entering the program: the via on the grid (branch `fix/point-via`)

Nothing here is done in `pcbthermal/`. The proposal is measured on copies (`lib/program_patch.py`, `lib/solid_patch.py`); the numbers are in `README.md`. A change of the model of the vias moves results, so it goes through the executor, the reviewer and the whole battery.

## 1. What changes

**Recommended treatment** (`mw_disc@eta`): for every via, in `fvm.Network` and `fdm.Network`,

1. *Footprint.* Weights `w` on the cells (nodes) that the disc of the via covers (area of the disc inside each cell, sampled 24 x 24 per cell); if the lattice effective radius `r_eff` of that footprint is smaller than `r_t = e^(-1/4) r_v` the disc is enlarged (centre fixed) until `r_eff = r_t` (bisection, 30 steps). `r_eff` from `E = Σ w_a w_b a(a-b)`, `ln r_eff = (π/2)(E - κ)`, with the potential kernel `a` tabulated for offsets up to 12 (exact recurrence, 169 numbers, asymptote beyond) and `κ = (2γ + 3 ln 2)/π`.
2. *Wells.* `G_c,l = 2π S_l / ln(r_eff / r_t)` for each copper plane `l` (`S_l` the sheet conductance of the cell with the largest weight; `G_c = ∞` if `r_eff ≤ r_t`; `0` for a layer with no conductance there).
3. *Barrel.* Nodes `b_l` joined by the barrel conductance of each gap `G_v,k = k_Cu A_via / d_k` (the program's `thermal_area`, so the fill is unchanged).
4. *Reduction.* The barrel nodes are eliminated (`viakernel.kron_barrel`): couplings `G_lm` between the plane means `T̄_l = Σ_a w_a T_{l,a}`; the matrix gets `G_lm (e_l ⊗ w - e_m ⊗ w)(e_l ⊗ w - e_m ⊗ w)^T` for every pair. No new unknown; `K` stays symmetric, positive semidefinite and with zero row sum from the via (tested: the heat that leaves equals the power to 1e-9, `tests/test_program_patch.py`).

**Where.** A new module (`pcbthermal/viawell.py`: lattice kernel table, weights, effective radius, Kron reduction; about 150 lines); `fvm.Network._assemble` and `fdm.Network.__init__` append the blocks to their COO lists where they now add `gz`; `fvm.Network.__init__` and `fdm.Network.__init__` stop adding the barrel to `gz`. Both use the same function; the FDM passes the node origin (`-Δx/2`).

**What must not change.**

* The Lumped model reads `net.gz` ring by ring: keep a separate array `gz_via` (the point conductance, as today) in the network for them (`lumped.py` adds it; one line) and let only `_assemble` use the new couplings; otherwise the Lumped model loses its vias.
* Boards without vias: bit-identical (tested at 0.5 mm in the FVM). Boards with vias change.
* `Network.solve_sor` (the comparison solver, `solvers` command) builds its red-black update from the seven neighbour arrays (`gz`, `extra_links`) and does not see a coupling between cells of a footprint: with the new couplings it solves a different matrix (review, `scripts/study_solvers.py`, copper-filled 3 x 3 board: after 200 000 sweeps it stops with the warning "SOR did not converge" and a maximum temperature 19.4 K (0.5 mm) and 21.9 K (0.25 mm) below the direct solution; the 26.7 K first written here was printed by no script). Either it applies the via blocks as an explicit residual term in every sweep (a sparse matrix-vector product of the via part, Gauss-Seidel on the rest), or the SOR option is refused for boards with vias, with a message. Not tried here; the direct and CG solvers use the assembled `K` and are unaffected (CG against direct on the same board: 3.6e-12 K at 0.5 mm, 9.8e-12 K at 0.25 mm).
* The 3D solid, Lumped and Analytic are not touched by this item.
* *Review:* the footprint must keep only cells **on the board** (`cover > 0`, weighted by the cover), not only cells inside the grid as the prototype does: a cell off an outline is pinned to the ambient by `g_pin` and would otherwise be coupled to the barrel; and the sheet conductance of the well must be taken on the board (the prototype uses the cell of the largest weight, which can be off the board or outside a zone).

**Cost.** The footprint of a via is a few tens of cells on fine grids; the extra entries are `L(L-1)/2 · m²` per via (6 · 100 for four planes and 10 cells); the weights are computed once per Network. The sampling in the prototype is slow for thousands of vias (a loop in Python per via): vectorise it (an area table of a disc as a function of the offset of its centre inside the cell, one table per run) before using it on Gerber boards.

## 2. Measured impact

* **Convergence** (README 4): worst error of the via effect over 12 unit-cell cases and three positions 0.7 % / 0.5 % / 0.4 % at 1 / 0.5 / 0.25 mm and finer (program 7 / 10 / 20 %); copper-fill gain of the 3 x 3 board -4.42 to -4.51 K from 1 to 0.0625 mm (program -4.78 to -3.34; reference -4.51).
* **Example board, default cell 1 mm**: FVM open T_max 85.81 -> 85.22 °C, FDM 84.38 -> 85.12 °C; the copper-fill gain -4.49 -> -4.14 K (FVM), -4.55 -> -4.15 K (FDM); at 0.5 mm 85.87 -> 85.17 °C (FVM), 85.22 -> 85.12 °C (FDM); at 0.25 mm 85.95 -> 85.15 °C. The FVM-FDM difference at 1 mm falls from 1.4 to 0.1 K. The tables of `docs/validation.md` 2.1 and 18 move by up to 0.8 K; sections that compare the five models on boards with vias (examples, `validation_study.py`) have to be re-run: **not done here**.
* **Results of boards without vias, of the Lumped and Analytic models and of the 3D solid: unchanged.**

## 3. Proposal for the 3D solid (separate, smaller)

* The rule of `solid3d.py` (a point if the copper area fits in the cell, a disc spread otherwise) makes the open and the filled board two different models at some cells: replace it by **one footprint rule for every via**: the centred disc or the tuned weights of `viakernel.tuned_weights(r_t = 0.78 r_v)`, a point when `r_eq` already exceeds `r_t`. Measured on the 3 x 3 board (README 6): gain -4.77 / -4.51 / -4.54 / -4.42 K at 1 / 0.5 / 0.25 / 0.1667 mm (program -4.77 / -4.35 / -5.65 / -5.34), position-independent (0.00 K for shifts inside the cell). The simple footprint without the tuning (`area`, `disc_eta`) is not enough in the 3D solid because it has no well (-5.29 K at 0.5 mm). 
* The missing well at coarse cells (-4.77 K at 1 mm, 0.27 K too large a gain) is not corrected: a series resistance in the pillar was not tried; leave it as a documented limit.
* Test: the gain of the 3 x 3 board within 0.3 K of -4.5 from 1 to 0.1667 mm.

## 4. Tests to add on adoption

* The via effect of the unit cell (12 cases of `scripts/study_unit_cell.py`, shortened to 3) within 1.5 % of the fine-grid reference at 1, 0.5 and 0.25 mm; the reference of the test is `lib/sheets2d.py` copied into `tests/helpers/` (it imports nothing).
* The gain of the 3 x 3 board within 0.3 K from 1 to 0.125 mm in the FVM and FDM (`research/point-via-convergence/tests/test_program_patch.py::test_copper_fill_gain_converges_to_the_resolved_reference` fails on the old code: -3.64 K at 0.125 mm).
* Symmetry, zero row sum, energy balance; a board without vias bit-identical; the Lumped model with vias unchanged.
* The existing tests of the via fill (`tests/test_via_fill.py`) and of the examples have numbers that move: re-baseline after the reviewer has seen the new ones.

## 5. Risks and open points

* The target radius `0.78 r_v` is derived from the uniform density of the layered model and checked against one 3D solver; the maintainer should decide whether to expose it (a constant in the code is proposed; a Preferences entry is not). *Review* (README 3.3): the uniform density is the construction of the fine-grid reference, not a property of a real barrel; against an axisymmetric 3D solve of 2- to 6-plane stack-ups the radius that matches is 0.23 to 0.94 `r_v`, and `0.78 r_v` leaves -2.1 to +3.9 % in the via effect (`r_v`: +0.1 to +4.7 %). A constant is still the right choice; the documents must quote this spread, not the 0.4 % of the treatment against its own reference.
* At 2 mm cells and above the via is a fraction of a cell and the error (gain -3.70 K against -4.20 K at fine cells on the example board) is in the sheet; the warning of the program about the cell size next to vias (`checks.py`) could say so.
* The transient with the new couplings was not compared; time constants should be unchanged for boards without vias and nearly so with vias (the couplings carry no heat capacity), to be tested.
* Vias within a footprint of each other (closer than their diameter plus a cell) share cells; their blocks add and the weights are not renormalised: the approximation is the same as the program's today (several vias in one cell).
* A via near the board edge or an outline: the footprint is cut and renormalised; not tested.
* The Gerber import (`research/gerber-models/`) puts thousands of vias on fine cells: this is the case that needed the fix; the performance point of section 1 applies. *Review* (`scripts/study_edge_via.py`): the weights cost 0.06 to 1.9 ms per via (about 20 s for 10 000 vias); the matrix is the larger risk: at 0.0625 mm a four-plane via couples about 120 unknowns densely (5 400 entries), which the sparse LU turns into fill-in; measure memory and time on a Gerber board before the merge.
* A via 0.16 mm from a board edge or an outline (README 8): the treatment converges (box edge 3.15 K, outline 7.52 K at fine cells) but is +15 % / +12 % at 1 mm, because the lattice kernel has no image of the edge; the program is +19 % there and drifts to -16 to -18 % at 0.0625 mm.
