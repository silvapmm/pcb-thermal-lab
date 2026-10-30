# Entering the program: SOR with the mean-potential via couplings

Applies only when the treatment of `research/point-via-convergence/INTEGRATION.md` is adopted (on `develop` today the vias are links in the stencil and the program's SOR is correct: `tests/test_fvm.py` and `research/models-comparison/scripts/solver_equivalence.py` pass). Without a change here, adopting that treatment turns the SOR of the FVM into a solver that never converges on a board with vias (19 to 27 K cool, README 2.4 and 5). The decision between the two options below is the maintainer's.

## 1. Option 1 (recommended): block SOR, variant (c)

**What changes** (a `fix/` or `feature/` branch, with the treatment):

* `fvm.Network` keeps, when it assembles the via couplings, the flat unknown indices of the cells of every via (footprint cells of all layers; vias that share a cell are merged), `self.via_blocks`.
* `Network.solve_sor`: (1) build `Binv` once, the dense inverse of `K[b, b]` of every block (sparse block-diagonal); (2) the two colour updates skip the via cells (the mask is the colour mask minus the via cells; the stencil arrays and the diagonal are unchanged); (3) after the two colours, one block step `theta[b] += Binv (Q[b] - K[b, :] theta)` for all blocks at once (`K[b, :]` kept as a sparse row slice); (4) the residual stop rule is untouched, it already uses `K @ theta`. The `info` dictionary can carry the number of blocks. `lib/sorvia.py`, `RB.sweep` is the working prototype (about 35 lines of numerics).
* `omega` stays the program's formula (a separate possible gain: 1.97 against 1.861 on the 3 x 3 board, five times fewer sweeps, README 3.2; not part of this change).
* `solve_sor` still refuses metal blocks (the extra layers are not coloured); boards without vias take the same path with an empty block list, bit-identical to today.

**Measured impact** (copy in `lib/`, README 3 and 5): the same sweeps as the board without vias (4260 against 4170 on the 3 x 3 array at 0.5 mm; 2390 on the example board at 1 mm), the field within 1e-8 K of the direct solver on every board of the study (unit cell, lone via, row of three, 3 x 3 array at 0.5 and 0.25 mm, example board at 1 and 0.5 mm), 0.8 mm copper-filled vias and overlapping footprints included, stable up to 10^4 times the real via stiffness; 15 to 35 % more time per sweep. Memory: the inverses are dense per via, `(footprint cells x layers)^2` floats per via (about 44^2 for a 0.3 mm via at 0.0625 mm cells on four layers).

**What does not change**: the direct and CG solvers, the FDM, the 3D solid, the time paths (they do not use `solve_sor`), the results of the other models, the GUI list ("SOR (iterative, for comparison)"), the stop rule (and its warning).

**Tests to add** (on the adoption branch): `tests/test_fvm.py`: SOR with vias agrees with the direct solver to 1e-6 K on a board with one filled via at a footprint of several cells, on a 0.8 mm copper-filled via and on two vias sharing a cell; a regression test that fails with the old `solve_sor` (the failure of README 2.4); `solver_equivalence.py` gets a board with vias in the "five boards" (the table of `docs/validation.md` section 5). The research tests of this folder (`tests/test_sorvia.py`) hold the checks to copy.

**Documents** (adoption branch): `docs/theory.md` solvers (text in `docs/for-the-project-documents.md`), `docs/models.md` the solver sentence, `docs/validation.md` section 5 (the new board and its difference), the user guide sentence on the SOR option, `CHANGELOG.md`.

**Risks**: (1) blocks that touch through the stencil are updated at once (block Jacobi among blocks): no failure in the layouts tried (README 3.3), merge adjacent blocks if one appears; (2) the dense inverse of a block grows with the square of the layers: a 12-layer board with large vias at a fine cell is the case to watch (130 x 130 per via); (3) the block-SOR convergence for any omega in (0, 2) is not proved from a source here (status M), only measured.

## 2. Option 2: refuse SOR on boards with vias, variant (f)

`solve_sor` raises `ValueError("SOR does not support vias: use the direct solver or the conjugate gradients")` like it does for metal blocks, `api.simulate` turns it into the same warning/fallback as for blocks; the GUI keeps the entry but greys it for boards with vias (as for the models that do not apply). Costs a few lines and tests, no numerics. SOR is then not available on the example boards, and the row of `docs/validation.md` section 5 must say so. Impact on results: none; on the documentation of the solvers: SOR remains "a solver of the board without vias".

## 3. Rejected

* (a) via part in the residual: shorter (10 lines) but diverges for a 0.8 mm copper-filled via at 0.5 mm and at s >= 10 times the real via; its margin falls with the cell (README 3.3).
* (b) Woodbury with SOR inner solves: 3 to 36 times the sweeps of (c).
* (d) SSOR-preconditioned CG: no need for SOR, CG already agrees to 1e-11 K and is 12 times faster here than SSOR-CG.
* (e) the point link for SOR only: the answer differs from the direct solver by 0.2 to 1.1 K (13 K on the weakly cooled unit cell), the error of the old treatment.
