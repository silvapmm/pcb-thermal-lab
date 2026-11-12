# Integration: the Robin basis in `pcbthermal/analytic.py`

**Status (audit 2.6.1): implemented in 2.5.0** (`feature/analytic-robin-edge`, with the corrected root finding and warning rule of the review); the per-layer basis of section 4 followed in 2.6.0 as a GMRES loop on an edge-mismatch modal source (`research/analytic-edge-and-transient`). The text below is the design as proposed.

Recommendation: **adopt in 2.5.0** on a `feature/analytic-robin-edge` branch (or a `fix/` one, since it corrects the accuracy of an unreleased transfer), executor then reviewer then
maintainer with the whole battery. Size: about 150 changed lines in `analytic.py`, one small class, tests, documents. The prototype in `lib/robin_basis.py` and `lib/analytic_edge.py` is the
specification (it equals the current solve to 1e-9 K with beta = 0). **Reviewed** (README 8): go, with the corrections marked "(review)" below; the warning rule of the first
version (spread of `slab/S` above 3) was wrong and is replaced.

## 1. Changes in `analytic.py`

1. New class `_EdgeBasis(length, beta, n)` (the code of `lib/robin_basis.py`): `lam`, `eig2`, `norm`, `evaluate(x)`, `project(lo, hi)`. `beta <= 0` returns the cosine basis (norms `L`, `L/2`).
   **(review)** The roots must be found as in the corrected `lib/robin_basis.py._root`: the pole-free forms `d sin d - bl cos d` (even) and `d cos d + bl sin d` (odd) on their
   intervals, with the first-order asymptote when there is no sign change in floating point. The first version (`brentq` on `d tan d`, `d cot d`) raised an error below `beta Lh` of
   about 1e-9 times the highest root (`h_side` near 3e-7 W/m2K on a 60 x 40 mm board) and above about 1e12; a typed tiny `h_side` would have stopped the Analytic.
2. `_effective_sheet`: also return `beta = h_eff sum(slab) / sum(S)` with `h_eff = h_side P_edge / (2 (W + H))` (keeps the edge conductance of an outline board). `h_edge` stays in
   `h_tot` for the fin lengths and the tile size (so that the copper weighting and the tiles do not move), but is **removed from the surface coefficients** of the modal matrices.
3. `_heater_unit_sources(problem, M, N)`: `q = q0 outer(px / Nx, py / Ny)` with the basis projections and norms instead of `ex px / W`.
4. `solve_steady`: `k2 = lam_x^2 + lam_y^2`; the tile Green function uses `Ainv / (Nx Ny)` for `ex ey / (W H)`, the tile averages `P / tile` and the injection `/ (Nx Ny)`; the field is evaluated with
   `basis.evaluate(xs)`. `p_out`: top and bottom from `h * integral`, with `integral = (project(0, W)) a (project(0, H))`; `sides` = `beta S_l` times the boundary integrals of the layer (as in
   `lib/analytic_edge.py`), so the heat balance still closes (verified 1.0000 on 135 boards).
5. `_modal_matrix`, `_modal_dynamics`, `_point_vector`, `_smeared_steady_max`, `_ModalSet.field`: replace the `np.cos(... m pi x / W)` (eleven places in `analytic.py`, among them
   lines 18, 208 to 217, 311 to 318, 419 to 420, 486, 525 to 533, 557 to 558, 617 to 618 at `develop` `ec227ab`) by the basis. The block path (`_block_tiles` and the tile graph) uses the
   same Green function and must take the same basis (**not covered by the prototype**: see 2). Calibration of vias and heatsinks in time is unchanged.
6. **Warning (review, replaces the first rule).** Remove the "misplaced share" warning of `fix/analytic-edge-transfer` (its premise, the edge at the mean temperature, is gone).
   The first proposal (warn when the spread of `slab_l / S_l` is above 3 and the edge share above 0.2) is **not** adopted: the spread is 7.6 to 9.8 on every advanced stack-up with
   full copper, where Robin is within 2.2 %, and 1.9 on a two-layer board where Robin is 6.9 % cool (README 8.3). Proposed instead, to be calibrated by the executor on
   `study_review_checks.py` part 3 and `study_edge_complications.py` part A: warn when the edge share `sum(h_edge) / h_tot` is above 0.3 **and** the board has one layer, or two
   layers whose sheet conductances `S_l` differ by more than 1.5 times, or more layers whose `S_l` differ by more than 2.5 times. Text: "the edge loss is shared between the copper
   layers by one parameter (and on a one-layer board the laminate edge is given to the copper); the hottest temperature can be off by up to about 9 % either way, measured cool
   with the copper on the heated layer". Acceptance: it fires on every board of those sets with an error above 3 %, and on none of the uniform 135.
7. Not changed: no `h_side` (bit-identical, beta = 0), the Lumped, copper weighting, tiles, via constriction.
8. Equivalent rectangle: the edge parameter uses the rectangle sides with `h_eff` scaled by the outline perimeter (README 5: round +0.44 %, T +0.52 % against the faces numbers, no worse against the FVM).

## 2. Acceptance numbers (to be reproduced by the executor on the program)

| check | requirement | prototype |
| :-- | :-- | :-- |
| the 135 uniform boards of `study_edge_variants.py`, hottest rise against FVM 0.5 mm | mean abs. 0.2 %, max 0.5 % | 0.12 %, 0.32 % |
| the 12 via/heatsink boards | rise within 0.5 %, effect within 6 % | 0.25 %, 4.6 % |
| the heat balance faces + edge over P | 1.000 +- 0.002 | 1.0000 |
| boards without `h_side` (and `h_side` 0) | bit-identical | beta = 0 is the cosine (0.0 K) |
| time to 63 % of the 12 uniform boards | within 7 % | -3.3 to +6.0 % |
| example board, `h_side` 10 / 50 / 200 | within 2.5 % | -1.0 / -1.2 / -1.9 % |
| unit step, steady resistance against the FVM | within 2 % | 1.5 % |
| run time of a steady solve | no more than +5 % | same matrices; 1200 roots in 8 ms |
| (review) the 54 boards of `study_review_checks.py` part 3 | Robin better than faces on each; max abs. 9 % | 54 of 54; 8.6 % |
| (review) the roots for `beta` 1e-30 to 1e14 1/m, 600 modes | found, ordered, residual of the eigen-equation below 1e-9 | `test_basis_roots_any_beta` |
| (review) a vanishing `h_side` | tends to the insulated board linearly | `test_small_beta_is_continuous_with_the_cosine` |
| (review) the Robin series against an independent solver of the same sheets | within 0.3 % | -0.003 to -0.21 % (part 2) |
| (review) a metal-block board and the finned block with `h_side`, against the FVM 0.5 mm | no worse than faces; balance 1.000 | not covered by the prototype |
| (review) the transient of a board with vias and a heatsink (the time calibration) | time to 63 % no worse than faces | not covered by the prototype |

Tests to add in `tests/` (review): the basis (orthogonality, the Robin condition, the roots at any `beta`, `beta = 0` is the cosine); a closed form, the 1D fin with Robin ends
(a strip board, `n x 1`, against `theta_inf (1 - C cosh(m u))`); the energy balance faces + edge on a corner part; the mirror symmetry (a part in two opposite corners gives the
mirrored field); a corner part against a stored FVM number; bit identity without `h_side`; the warning firing and silent on one board each; a block board and the top path running.

## 3. Impact on numbers and documents

* **Frozen numbers** (`tests/regression`): the Analytic records of the boards with `h_side` move +0.3 to +0.7 % at 2 mm (11 boards, README 5; also its times to 63 %). **(review)**
  `tests/regression/data/pending/analytic-edge.json` (39 records, 13 boards, written by `fix/analytic-edge-transfer`) holds the **faces** values: it does not "cover" the Robin change;
  it must be **regenerated** with `tests/regression/make_pending.py` on the Robin branch (same keys plus the transients; the two boards the prototype does not cover, `finned_block`
  and `part_top_path`, move too and are measured only then), and its `why` and `evidence` fields rewritten. One pending file stays; the refreeze at the release folds it. Boards
  without `h_side` do not move.
* `docs/theory.md` 6 (the series and the limit paragraph: edge in the basis, the formula for lam, the new warning), `docs/validation.md` 4.1 (replace the faces table by Robin; the
  +12 % / +37 % become 0.3 %), 13 (outline), the user guide text of the warning, `tests/` (above), `CHANGELOG`, `docs/versions.md`. The text for the documents is in
  `docs/for-the-project-documents.md`.
* Risk: the odd functions are needed for off-centre sources (the paper's centred source does not); the basis is verified for orthogonality and the boundary condition to 1e-9; with a
  very large Biot number the first roots tend to Dirichlet values (tested up to `beta` 1e14 1/m by the review).

## 4. What goes to 2.6.0 or to an investigation (not needed for 2.5.0)

* A per-layer edge parameter (a coupling matrix between modes of different layers, or a perturbation correction): the review measured the common parameter alone at -5.2 to +10.0 %
  on two-layer boards with very different copper at `h_side` 200 (README 8.4). Not needed for 2.5.0: Robin is already better than faces on every board measured, and the case needs
  a large edge coefficient.
* **(review)** The edge of the laminate: the FVM (and FDM) put no laminate nodes where both copper layers are full, so with an edge coefficient their hottest rise jumps by +0.3 to
  +12.6 % between a fill of 1 and 0.9999, and they read 1 to 15 % below the 3D solver with the side film (README 8.4). The one-layer Analytic gives the laminate edge to the copper
  node (-7.3 % at `h_side` 200). Investigation `research/ROADMAP.md` A16 (laminate nodes in a band along the edge when `h_side > 0`, measured against the 3D solver); it would
  move the FVM numbers, so it is not a 2.5.0 item unless the maintainer decides so.
* The strips-as-heatsinks route is not proposed.

## 5. What happens to `fix/analytic-edge-transfer` (merged in `develop`, never released)

* Code: the faces term `h_edge` leaves the surface coefficients of the modal matrices (it stays in `h_tot`); the "misplaced share" warning (`analytic.py` around line 434 to 450 at
  `ec227ab`) is removed and replaced by the warning of 1.6; the `sides` key of the heat balance stays (now the Robin edge loss).
* Tests: the tests of the transfer in `tests/test_analytic_edge.py` that check the faces formula or the misplaced-share warning are replaced by the tests of 2; the heat-balance test stays.
* Documents: `docs/theory.md` 6 (equations and limits, the eq. 27 to 31 paragraph becomes the Robin basis, eq. 12 to 21, with [Muzychka2003Part2] kept as the source of both),
  `docs/validation.md` 4.1 (the faces table replaced), the user guide warning text, `CHANGELOG.md` (the Unreleased entry describes the Robin edge only: the faces transfer never
  shipped), `docs/versions.md`, and the pending file (3).
* The branch `fix/analytic-edge-transfer` stays as the record, as every work branch.
