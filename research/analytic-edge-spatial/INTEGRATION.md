# Integration: the Robin basis in `pcbthermal/analytic.py`

Recommendation: **adopt in 2.5.0** on a `feature/analytic-robin-edge` branch (or a `fix/` one, since it corrects the accuracy of an unreleased transfer), executor then reviewer then
maintainer with the whole battery. Size: about 150 changed lines in `analytic.py`, one small class, tests, documents. The prototype in `lib/robin_basis.py` and `lib/analytic_edge.py` is the
specification (it equals the current solve to 1e-9 K with beta = 0).

## 1. Changes in `analytic.py`

1. New class `_EdgeBasis(length, beta, n)` (the code of `lib/robin_basis.py`): `lam`, `eig2`, `norm`, `evaluate(x)`, `project(lo, hi)`. `beta <= 0` returns the cosine basis (norms `L`, `L/2`).
2. `_effective_sheet`: also return `beta = h_eff sum(slab) / sum(S)` with `h_eff = h_side P_edge / (2 (W + H))` (keeps the edge conductance of an outline board), and `edge_ratio_spread`
   (max/min of `slab_l / S_l`). `h_edge` stays in `h_tot` for the fin lengths and the tile size, but is **removed from the surface coefficients** of the modal matrices.
3. `_heater_unit_sources(problem, M, N)`: `q = q0 outer(px / Nx, py / Ny)` with the basis projections and norms instead of `ex px / W`.
4. `solve_steady`: `k2 = lam_x^2 + lam_y^2`; the tile Green function uses `Ainv / (Nx Ny)` for `ex ey / (W H)`, the tile averages `P / tile` and the injection `/ (Nx Ny)`; the field is evaluated with
   `basis.evaluate(xs)`. `p_out`: top and bottom from `h * integral`, with `integral = (project(0, W)) a (project(0, H))`; `sides` = `beta S_l` times the boundary integrals of the layer (as in
   `lib/analytic_edge.py`), so the heat balance still closes (verified 1.0000 on 135 boards).
5. `_modal_matrix`, `_modal_dynamics`, `_point_vector`, `_smeared_steady_max`, `_ModalSet.field`: replace the four `np.cos(... m pi x / W)` by the basis (`cos_x`, `cos_y` become `basis.evaluate`).
   Calibration of vias and heatsinks in time is unchanged.
6. Warning: remove the "misplaced share" warning. Replace by: warn when `edge_ratio_spread > 3` and `sum(h_edge) / h_tot > 0.2`: "the layers have very different copper, one edge parameter is used for
   all of them; the hottest temperature can be off by up to 5 % (measured up to 5.4 % at a spread of 4.5)". Measured (README 4A): spread 1.95 gives at most 1.2 %, 3.14 at most 3.2 %.
7. Not changed: no `h_side` (bit-identical, beta = 0), the Lumped, copper weighting, tiles, via constriction, blocks (a block board still uses the local corrections: same basis, same code path).
8. Equivalent rectangle: the edge parameter uses the rectangle sides with `h_eff` scaled by the outline perimeter (README 5: round +0.44 %, T +0.52 % against the faces numbers, no worse against the FVM).

## 2. Acceptance numbers (to be reproduced by the executor on the program)

| check | requirement | prototype |
| :-- | :-- | :-- |
| the 135 uniform boards of `study_edge_variants.py`, hottest rise against FVM 0.5 mm | mean abs. 0.2 %, max 0.5 % | 0.12 %, 0.32 % |
| the 12 via/heatsink boards | rise within 0.5 %, effect within 6 % | 0.25 %, 4.6 % |
| the heat balance faces + edge over P | 1.000 +- 0.002 | 1.0000 |
| boards without `h_side` | bit-identical | beta = 0 is the cosine |
| time to 63 % of the 12 uniform boards | within 7 % | -3.3 to +6.0 % |
| example board, `h_side` 10 / 50 / 200 | within 2.5 % | -1.0 / -1.2 / -1.9 % |
| unit step, steady resistance against the FVM | within 2 % | 1.5 % |
| run time of a steady solve | no more than +5 % | same matrices; roots 2 ms |

## 3. Impact on numbers and documents

* **Frozen numbers** (`tests/regression`): the Analytic records of the boards with `h_side` move +0.3 to +0.7 % at 2 mm (11 boards, README 5; also its times to 63 %); the records are already
  held by the pending shift of `fix/analytic-edge-transfer`, so one pending file covers both and the refreeze at the release folds them. Boards without `h_side` do not move.
* `docs/theory.md` 6 (the series and the limit paragraph: edge in the basis, the formula for lam, the new warning), `docs/validation.md` 4.1 (replace the faces table by Robin; the
  +12 % / +37 % become 0.3 %), 13 (outline), the user guide text of the warning, `tests/` (a test for the basis, one for the corner part against a stored FVM number, the warning), `CHANGELOG`,
  `docs/versions.md`. The text for the documents is in `docs/for-the-project-documents.md`.
* Risk: the odd functions are needed for off-centre sources (the paper's centred source does not); the basis is verified for orthogonality and the boundary condition to 1e-7; with a very
  large Biot number the first roots tend to Dirichlet values (tested up to beta L = 30, roots bracketed on each interval so none is lost).

## 4. What goes to 2.6.0 (not needed)

A per-layer edge parameter (a coupling matrix between modes of different layers, or a perturbation correction) for layers whose copper differs by more than about 3 times; the cut of the
top-path split and blocks are unaffected. The strips-as-heatsinks route is not proposed.
