# Integration of S3 and S4 into the program (draft; the measured impact is filled after the runs)

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

**Measured impact:** to be filled (sweeps and seconds before and after on every board of README 2.4; cost of the estimate).

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

**Measured impact:** to be filled (every via row, before and after, by model; time and memory of the correction on 4 to 576 vias).

**Risks.** The correction changes the answer of two models with vias, so it is a fix of a model error, not a no-op: the numbers of the documents change and must be updated in the same commit; the
dense system grows as `(N_t L)^2` in memory; arrays below the floor pitch are outside the tested range (warning); the Lumped limits stay.
