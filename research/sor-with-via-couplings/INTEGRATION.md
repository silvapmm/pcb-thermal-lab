# Entering the program: SOR with the mean-potential via couplings

Applies only when the treatment of `research/point-via-convergence/INTEGRATION.md` is adopted (on `develop` today the vias are links in the stencil and the program's SOR is correct: `tests/test_fvm.py` and `research/models-comparison/scripts/solver_equivalence.py` pass). Without a change here, adopting that treatment turns the SOR of the FVM into a solver that never converges on a board with vias (19 to 27 K cool, README 2.4 and 5). The decision between the two options below is the maintainer's.

## 1. Option 1 (recommended): block SOR with relaxed, coloured blocks, variant (c')

*Corrected by the review (README 8)*: the first version of this option was (c), whose block step is not relaxed; it needs up to 2.8 times the sweeps of the board without vias on dense via arrays, (c') 0.79 to 1.00 times. Its convergence for 0 < omega < 2 is now proved (README 8.4).

**What changes** (a `fix/` or `feature/` branch, with the treatment):

* `fvm.Network` keeps, when it assembles the via couplings, the flat unknown indices of the cells of every via (footprint cells of all layers; vias that share a cell are merged), `self.via_blocks`.
* `Network.solve_sor`: (1) colour the blocks once (greedy: two blocks are neighbours when `K` couples a cell of one to a cell of the other) and build per colour group `Binv`, the dense inverses of `K[b, b]` (sparse block-diagonal); (2) the two colour updates skip the via cells (the mask is the colour mask minus the via cells; the stencil arrays and the diagonal are unchanged); (3) after the two colours, group by group, `theta[b] += omega Binv (Q[b] - K[b, :] theta)` (`K[b, :]` kept as a sparse row slice; the same omega as the colours); (4) the residual stop rule is untouched, it already uses `K @ theta`; the step rule (`criterion="step"`) must include the change of the block step. The `info` dictionary can carry the number of blocks and groups. `lib/sorvia.py`, `RB` with `block_omega=None, colour_blocks=True` (variant `block_over`), is the working prototype (about 45 lines of numerics).
* `omega` stays the program's formula (a separate fix: Young's optimum `2 / (1 + sqrt(1 - rho_J^2))` of the board without vias, 1.9613 against 1.8609 on the 3 x 3 board, 6.0 times fewer sweeps, 2.9 times on the example board, README 8.3; it needs a cheap estimate of `rho_J`; not part of this change).
* `solve_sor` still refuses metal blocks (the extra layers are not coloured); boards without vias take the same path with an empty block list, bit-identical to today.

**Measured impact** (copy in `lib/`, README 3, 5 and 8): (c') needs the sweeps of the board without vias or fewer (3770 against 4169 on the 3 x 3 array at 0.5 mm, 2250 against 2247 on the example board at 1 mm, 3280 against 4169 on a 9 x 9 array; (c) needed 4260, 2390 and 11560), the field within 1e-8 K of the direct solver on every board of the study (unit cell, lone via, row of three, 3 x 3 array at 0.5 and 0.25 mm, example board at 1 and 0.5 mm), 0.8 mm copper-filled vias and overlapping footprints included, stable up to 10^4 times the real via stiffness; 15 to 35 % more time per sweep. Memory: the inverses are dense per via, `(footprint cells x layers)^2` floats per via (about 44^2 for a 0.3 mm via at 0.0625 mm cells on four layers).

**What does not change**: the direct and CG solvers, the FDM, the 3D solid, the time paths (they do not use `solve_sor`), the results of the other models, the GUI list ("SOR (iterative, for comparison)"), the stop rule (and its warning).

**Tests to add** (on the adoption branch): `tests/test_fvm.py`: SOR with vias agrees with the direct solver to 1e-6 K on a board with one filled via at a footprint of several cells, on a 0.8 mm copper-filled via, on two vias sharing a cell and on a dense array whose footprints touch (at least two colour groups; its sweeps not more than those of the same board without vias); a regression test that fails with the old `solve_sor` (the failure of README 2.4); `solver_equivalence.py` gets a board with vias in the "five boards" (the table of `docs/validation.md` section 5). The research tests of this folder (`tests/test_sorvia.py`) hold the checks to copy.

**Documents** (adoption branch): `docs/theory.md` solvers (text in `docs/for-the-project-documents.md`), `docs/models.md` the solver sentence, `docs/validation.md` section 5 (the new board and its difference), the user guide sentence on the SOR option, `CHANGELOG.md`.

**Risks**: (1) the dense inverse of a block grows with the square of the layers: a 12-layer board with large vias at a fine cell is the case to watch (130 x 130 per via); (2) the speed of (c') is measured, not proved (its convergence is, README 8.4). The earlier risks are closed by the review: touching blocks are coloured (moving them at once over-relaxed diverges, README 8.1), and convergence is proved.

## 2. Option 2: refuse SOR on boards with vias, variant (f)

`solve_sor` raises `ValueError("SOR does not support vias: use the direct solver or the conjugate gradients")` like it does for metal blocks, `api.simulate` turns it into the same warning/fallback as for blocks; the GUI keeps the entry but greys it for boards with vias (as for the models that do not apply). Costs a few lines and tests, no numerics. SOR is then not available on the example boards, and the row of `docs/validation.md` section 5 must say so. Impact on results: none; on the documentation of the solvers: SOR remains "a solver of the board without vias".

## 3. Rejected

* (c) the first block version (blocks at once, block step not relaxed): converges (proved for `omega_b <= 1`) but up to 2.8 times the sweeps of the board without vias on dense arrays; relaxing it at once diverges (README 8).
* (a) via part in the residual: shorter (10 lines) but diverges for a 0.8 mm copper-filled via at 0.5 mm and at s >= 10 times the real via; its margin falls with the cell (README 3.3).
* (b) Woodbury with SOR inner solves: 3 to 36 times the sweeps of (c).
* (d) SSOR-preconditioned CG: no need for SOR, CG already agrees to 1e-11 K and is 12 times faster here than SSOR-CG.
* (e) the point link for SOR only: the answer differs from the direct solver by 0.2 to 1.1 K (13 K on the weakly cooled unit cell), the error of the old treatment.
