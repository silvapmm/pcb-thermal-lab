# Integration of S3 and S4 into the program

Nothing here is implemented. Each item would be a `fix/` branch off `develop` with the reviewer and the whole battery, only after the maintainer decides. 2.4.5 takes fixes only: an estimate of
omega that changes only the sweep count and a tile rule that corrects a model error are fixes; a change of the answer of the Lumped or Analytic models with vias moves numbers in the documents.

## S3. Young's omega in `Network.solve_sor`

**What changes (if the decision rule of README section 2 is met).** `pcbthermal/fvm.py`, `Network.solve_sor`: `omega=None` calls a private `_sor_omega(self)` instead of
`2 / (1 + sin(pi / max(nx, ny)))`. `_sor_omega` computes the Rayleigh bound from the totals of the assembly (`g_amb.sum()` and the diagonal sum: no product) or a short Lanczos on `D^-1/2 K D^-1/2`
(k products) started at `D^1/2 1`, and returns `2 / (1 + sqrt(1 - rho^2))` capped at 1.99. A typed `omega` is untouched. The result of the solve does not change (the stopping rule is the residual); only
`info["iterations"]`, `info["omega"]` and the time change. SOR keeps refusing metal blocks. The block SOR (c') of `sor-with-via-couplings` uses the same function on `diag(K) + stencil`.

**Tests.** `tests/test_fvm_solvers.py` (or the file that holds the SOR tests): omega equals the program's value when it is typed; the automatic omega is below the exact Young optimum
(safe side) on a plate and an example board; fewer sweeps than before on both; the temperatures agree with the direct solve to the residual tolerance.

**Documents that move.** `docs/validation.md` section 5 (rows with SOR: sweeps 2247 and time 0.91 s of the example board, the omega column), `docs/theory.md` (the SOR paragraph: the formula and its
justification as in `docs/theory-text.md` A), `docs/models.md` (the solver options), the user guide line on SOR (`pcbthermal/help/index.html`) only if it quotes the factor, `CHANGELOG.md`, `docs/versions.md`.

**Decision rule:** met (README 2.8): the masked Rayleigh bound is a lower bound everywhere tested, costs under 1 % of the seconds it saves and gives no slower SOR on any board. Lanczos, power method and adaptive estimate are not proposed. `_sor_omega` must use the masked product (nodes with at least one off-diagonal entry), not the closed form from the totals: on a board with an outline both collapse unless masked (README 2.5, defect found).

**Measured impact (README 2.5 to 2.7):** sweeps of the program's SOR, before / after: plate 4 layers 8845 / 998; plate 6 layers 13359 / 1236; 4 layers + 5 x 5 vias 18392 / 2054; partial copper 6623 / 877; round board 4459 / 696; example board 2 mm 1149 / 406 and 1 mm 2247 / 812 (SOR seconds at 1 mm 1.06 s with the program's omega, 0.41 s with Young's exact; the Rayleigh product 0.0017 s). The block SOR with the full K: 34530 / 2010 (3 x 3 array), 23810 / 1940 (5 x 5), 2250 / 810 (example); three boards only. The direct solve stays faster (0.18 s on the example board at 1 mm), so the gain is for the comparison solver. The gain falls with the grid (6.3 times at 40 x 40, 1.2 at 160 x 160 on a plate).

**Risks.** An omega above the optimum on a board where the estimate overshoots (not possible with a lower bound, possible with the power method: not proposed); a board whose Jacobi graph is not two-colourable
(not the case of the stencil); the estimate adds code to a comparison solver for a gain on a path that few users take: the stop rule exists for this.

## S4. Tile rule and mode rule of the Analytic via correction; the Lumped well

**What changes (the corrected models themselves are the proposals of `lumped-analytic-vias/INTEGRATION.md`; this folder only adds the rule).**
* `pcbthermal/analytic.py`: `_tile_grid` receives the vias (or a new `_via_tile(problem, W, H, t_program)`) and returns the tile of the rule chosen in README 3.4; the self-term, the bilinear spread and the guard are those of the earlier proposal.
* `pcbthermal/analytic.py`: `Mg, Ng = min(M, 64), min(N, 64)` becomes a function of the board and the tile if README 3.3 shows an error that more modes remove.
* `pcbthermal/lumped.py`: the cluster well of the earlier proposal; the caps or factors of README 3.8 only if they pass the decision rule.
* `pcbthermal/checks.py`: warnings for the limits that stay (README 4): a via outside every footprint in the Lumped model; tiles coarsened above 1200 active tiles; pitch below the floor of the tile.

**Tests.** The unit-cell closed form with Krogh wells for the Analytic and Lumped models (within the tolerance of README 3.1); the lone via and the 3 x 3 array against stored values of the fine-grid
reference; the tile function: fixed points, the floor, the cap at the program's tile, the coarsening; the program unchanged on a board without vias (bit for bit); the tile independent of the order of the vias.

**Documents that move.** `docs/validation.md`: the via rows (sections 1, 2 and 3 for the example board with nine vias; section 18 the fill table; section 21 the example-board line) and the copper-fill gain of the
Lumped and Analytic models (6.3 to 7.0 K down to about 4.3 to 4.5 K, to be confirmed with the rule); `docs/theory.md` (sections of the Lumped and Analytic models: the constriction, the self-term, the tile
rule); `docs/models.md`; `CHANGELOG.md`; `docs/versions.md`; the user guide (a sentence on the via correction and on the warnings); `tests/test_help.py` if words are added.

**Measured impact (README 3):** error of the via effect against the fine-grid reference, program / with the tile rule, Analytic: simple boards 15.9 % / 3.0 % maximum, dense boards (pitch 0.6 to 1.0 mm, drills 0.2 to 0.8 mm) fixed 1 mm 6.3 % / rule 1.8 %, 17 arrays of 4 to 576 vias 35.3 % / 4.2 %; example board copper fill 6.32 K -> 4.27 K (FVM at 0.25 mm 4.20 K), open-via effect 10.02 -> 9.50 K (9.57). Lumped with the cluster proposal: 6.79 -> 4.47 K on the example, arrays within 9 % except 100 to 400 vias at pitch 2.0 (-32 to -54 %) and 4 vias at 3.5 mm (+18.8 %). Cost of the Analytic correction: same as fixed 1 mm above 1.33 mm pitch; at pitch 1.0 mm 1.3 to 1.9 times the seconds and up to 2.1 times the memory (225 vias 0.68 s and 165 MB; 576 vias 1.33 s and 256 MB); 400 vias at 2.0 mm 3.96 s and 1.0 GB. The mode rule is not needed (64 against 2 per tile within 0.5 points up to 100 mm).

**Warnings that stay (limits, README 4).** A via outside every footprint in the Lumped model (the well is ring dependent, -22 to +65 %, for an effect of at most 3.5 % of the source rise beyond 3 mm); rows beyond 3 vias in the Lumped model (the macro cap 0.75 is the optional cheap fix: worst row error 50.7 to 15.4 %, 5-via rows worse); via pitch below 0.6 mm (untested); more than about 6400 dense unknowns (1 GB).

**Risks.** The correction changes the answer of two models with vias, so it is a fix of a model error, not a no-op: the numbers of the documents change and must be updated in the same commit; the
dense system grows as `(N_t L)^2` in memory; arrays below the floor pitch are outside the tested range (warning); the Lumped limits stay.
