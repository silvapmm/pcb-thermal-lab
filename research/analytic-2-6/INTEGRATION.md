# Integration: per-layer edge and local transient of the Analytic model

Everything here is a proposal measured on copies (`lib/`); `pcbthermal/` is untouched. Evidence in `README.md` (sections in brackets).

## 0. Recommendation

| item | proposal | for 2.5.0? | reason and risk |
| :-- | :-- | :-- | :-- |
| A | per-layer edge in the steady model | **No, 2.6.0** | gain on unequal layers with a strong edge (8.64 -> 4.07 % worst, mean 1.51 -> 0.90 %; 2.3), no gain on uniform layers; needs the Woodbury step restructured (LU kept, `solve_steady` split in two). Frozen cost is small (3 of 10 records move by under 0.01 K, 2.5), so the frozen file is NOT a reason to hurry: the pending file is regenerated in 2.6.0 as cheaply. |
| B | local modal transient (with the calibration of the steady point) | **No, 2.6.0** | removes -67 .. +113 % errors of the time to 63 % with a heatsink (3.2), but it is a new ~250-line module with a dense eigenproblem per part, no profile adapter yet, 10 boards of evidence; four frozen t63 records would move (3.3). A hurried version in a release battery is the larger risk. |
| B0 | **text-only warning in 2.5.0** | **Yes** | when the Analytic transient or profile is asked on a board with a heatsink: "the Analytic transient smears heatsinks over the board; the time to 63 % was measured from -67 % to +113 % of the FVM; use the FVM or Lumped for the time response (Lumped: -12 to +8 % with the heatsink under the part)". No number moves, no frozen record. |
| C | Lumped transient | no change | its error comes from the steady ring averaging (4), not from a calibration |

Why 2.5.0 does not need A or B for the frozen records: whatever is frozen at 2.5.0 is replaced at the 2.6.0 refreeze through the pending-file mechanism; a second shift costs one
`make_pending.py` run (A: 3 Analytic steady records of the harness; B: 4 Analytic times to 63 %: example_board, profile_board, plate_vias, plate_lone_via).

## 1. A: per-layer edge, exact changes in `analytic.py`

### 1.1 `_effective_sheet`

Keep `beta` (the basis parameter), add `beta_l = h_eff * slab / S` (array, 1/m) and `edge_mismatch = max|beta_l - beta| / beta` to the returned dict (`beta` zero or one layer: mismatch 0).
The "edge convection" warning rule (`edge_share > 0.3 and spread > ...`) stays for one-layer boards and is dropped for L >= 2 once the loop is on (the remaining error is the
idealisation, not the common beta; 2.3), with the text of the 2.5.0 warning kept for the thick-board and one-layer cases.

### 1.2 New helper

```
def _edge_mismatch_source(bx, by, a, S, dbeta):   # a (M, N, L) -> (M, N, L)
    Ex, Ey = bx.evaluate([0, bx.L]), by.evaluate([0, by.L]);  Nx, Ny = bx.norm, by.norm
    for l: out[:, :, l] = -S[l]*dbeta[l] * ((Ex.T/Nx[:, None]) @ (Ex @ a[:, :, l]) + (a[:, :, l] @ Ey.T) @ (Ey/Ny[None, :]))
```

(`lib/robin_perlayer.py`, `qcorr`.) Derivation in `README.md` 2.1.

### 1.3 `solve_steady`

1. Factor the Woodbury step once: keep `lhs = I + G C` as an LU (`scipy.linalg.lu_factor`, `overwrite_a=True`) instead of `np.linalg.solve(...); del lhs`; peak memory equal
   (the dense matrix is overwritten by its factors, at most 4800^2 doubles = 184 MB).
2. Split the rest into a function `respond(q_mn_extra)` returning the final `a_mn` for an extra modal source: `a = Ainv q_extra`; tile averages `y0`; `y = lu_solve(y0)`;
   injected heat `f = -C y`; `a += Ainv (q_corr from f)`. With no vias and heatsinks `respond` is the first line only.
3. If `edge_mismatch > 1e-9` (so equal layers are bit-identical) solve `(I - respond(qc(.))) a = a_0` with `scipy.sparse.linalg.gmres` on the flattened `a` (rtol 1e-6, restart 30,
   maxiter 30), `a_0` the present `a_mn`. Measured 4 to 9 products on 54 boards, 6 to 8 with vias and a heatsink (2.3, 2.4). A non-converged GMRES keeps the best iterate and adds a warning.
4. `p_out["sides"]` uses `beta_l` per layer: `sum_l _edge_loss(bx, by, a_l, S_l, beta_l)` (balance 1.00000 to 1.00002 in the prototype).
5. Cost estimate (not measured): each product is two small matrix products plus one triangular solve of `(Nt L)^2`: milliseconds; the prototype, which repeats the whole solve, took 0.7 to 35 s.

### 1.4 Transient consistency

The transient keeps the common `beta` (the modal matrix `_modal_matrix`). After 1.3 its plateau would differ from the steady solve by the 2.3 error (up to 8.6 %) on boards with
unequal layers. Options: (i) leave and document; (ii) after the local system of 2 is in, calibrate the plateau by a plain scale of the steady resistance (one factor on `G` so that
`rth` equals the steady point value; applied only when `edge_mismatch > 1e-9`), which keeps the shape and fixes the end. The coupled-block mismatch matrix was tried and fails
(README 3.4); (ii) is untested.

### 1.5 Acceptance tests (new `tests/test_analytic_perlayer.py`)

* equal layers: `solve_steady` bit-identical to the present code (uniform 2-layer board and the example board);
* 2 L top 0.2 / bottom full, h_side 200, corner part: hottest rise within 0.3 % of the finite-difference solution of the same sheets (`research/analytic-edge-spatial` `sheet_fd`
  or a copy in the test helper), and the program's present common beta off by more than 5 % (the regression the test must keep failing for the old code);
* heat balance `top + bottom + sides` within 1e-3 of the power with unequal layers, vias and a heatsink;
* the 54-board study (`scripts/study_perlayer_edge.py --part 2`): max error <= 4.5 % and mean <= 1.0 %, per-layer not worse than the program by more than 0.1 point on any board;
* GMRES product count <= 12 on every board of the study.

## 2. B: local modal transient

### 2.1 Where

New module `pcbthermal/analytic_local.py` (or a section of `analytic.py`; the module is the cleaner choice, `analytic.py` is already 1000 lines) holding `LocalSystem` from
`lib/local_modal.py` (`Reduced`, `local_matrix`), reusing `_tile_grid`, the via plan and `coverage_fraction` exactly as `solve_steady` does (the tile matrix `C` must be the one of the
steady solve: factor it out of `solve_steady` as `_local_conductances(problem, sh, bx, by)` returning `C`, `PX`, `PY`, `tiles`, used by both).

### 2.2 `_ModalSet`

* `_calibrated_dynamics` is replaced by: uniform dynamics with `via_scale = heatsink_scale = 0` (the board without them), plus, when the problem has vias or heatsinks, a
  `LocalSystem` with `K = 16` (module constant `LOCAL_MODES`, 24 optional), calibrated with one factor `s` on `C` so that the steady rise at the heater's own point equals that of
  `solve_steady` for the same part alone (the present `local_max` target, taken at the point, not at the maximum).
* The response is the coupled block (eigenvalues `lam_k`, source `g_k`, output row `u_k`) plus the uniform modes outside `K x K`. Represent both as flat mode lists
  (`lam`, `G (nh, n)`, `U (nh, n)`), so that `step_responses`, `drive`, `steady` and `points_temperature` keep their form; the coupled block adds `back` for the field
  (`field` needs the block's `Cap^-1/2 V` and `D`; the 2D evaluation is a sum over block modes of `phi_m(x) phi_n(y) a_mn`).
* The profile adapter (`_AnalyticAdapter.advance`: exact propagator per mode) works unchanged on a flat list of decoupled modes. This was NOT prototyped.
* Memory/time: eigenproblem of `K^2 L` unknowns per part: K 16, L 4: 3.8 s and 42 MB measured; L 8 (2048 unknowns) ~ 10 s estimated. A guard: `K^2 L <= 3000` (else K is lowered).
* `via_scale` and `heatsink_scale` keys stay in the dict (reported as 1.0) so that `docs`, `scaled` reporting and tests keep working.

### 2.3 Bidirectional calibration alone (a small fallback, 2.5.0 or later)

If the local system is postponed and a minimal change is wanted: remove `if steady(1.0) <= local: return d`, bisect both ways (lower bound 1e-3), and calibrate the heatsink-only
case on the maximum as now (`two_max`). Result (README 3.2): `sink beside` -54 % -> +14 %, `vias + sink beside` -67 % -> -15 %, `vias + sink under` +46 % -> +20 %, `sink under`
unchanged (-37 %), 4 L +113 % -> +72 %. Not good enough to be called a fix; it is only the correction of the defect that the plateau differs from the program's own steady solve.

### 2.4 Acceptance tests (new `tests/test_analytic_local.py`)

* no vias, no heatsinks: `step_responses` bit-identical to the present code;
* steady plateau: `rth` equals the point value of `solve_steady` within 1 % for the 10 boards of `scripts/study_transient_both.py`;
* time to 63 % against the FVM at 1 mm: within 10 % on the nine boards other than the 4 L one (measured 0.1 to 8.7 %), and in the 4 L case no worse than the present +113 %;
* `sink under`: |t63 error| < 3 % (measured -0.4 %), and the present code fails the test (-36.7 %);
* `sink beside`: steady plateau within 1 % of the steady solve (present code: 19.53 against 23.92 K/W);
* profile: square wave of period t63/2 and 2 t63, peak and swing of the local system within 4 % of the FVM on the 9 boards;
* K 16 versus K 24: t63 within 2 points on every board.

### 2.5 Frozen records that would move

Analytic times to 63 % of `example_board` and `profile_board` (identical, 9 vias and a heatsink; program +18.0 % of the FVM at 2 mm -> local +3.8 %, change -12.0 % against the
program), `plate_vias` (+1.3 %), `plate_lone_via` (+1.1 %) (README 3.3); the Analytic steady records, the other three models and the boards without vias or heatsinks do not move. The
`profile_board` run of the Analytic would move in its power-profile output if the harness records it (not checked). Pending file `analytic-transient.json` at the 2.6.0 refreeze.

## 3. C: Lumped

No change. Record in `docs/validation.md`: Lumped transient with a heatsink not under the part reads t63 -37 to -42 % (steady -7 to -10 % low) on the 60 x 40 mm board of
`README.md` 4; the existing via warning for the Lumped is not about this; a warning for "heatsink outside the footprint rings" could be added with a proper test (not studied).

## 4. Text for the project documents

`docs/for-the-project-documents.md`: the paragraphs for `docs/theory.md` section 6 (per-layer edge), 6.x (transient) and `docs/validation.md`, to be adopted only with A and B.
