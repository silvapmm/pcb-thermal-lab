# INTEGRATION: a cheaper preconditioner for the FEM above the direct limit

**Status: measured by the executor, not reviewed; recommendation below is a proposal, not a decision.** Nothing in `pcbthermal/` is edited from this branch. Tree: `development` 6c225276; reference: the current default of `femcore.Model.solve`. Numbers: README section 7.

## 1. What would change (if the maintainer wanted it)

Only `femcore.Model.solve`, in the CG branch (line 387 of this tree). The pyamg-only variants (theta, smoothers, aggregation, evolution, Ruge-Stueben, root-node, W cycle, coarse size, scaling, candidates) and the reuse of a hierarchy do **not** pass: no change is proposed for them (a), (c). The only candidates are:

* (b) CG tolerance `rtol` 1e-10 to 1e-9: saves 4 % (2 mm) and 10 % (1 mm) on one run each, field moves by 1.4e-9 to 1.6e-9 K. Not proposed on this evidence alone: the docstring of `solve` argues that 1e-10 is what the recursive residual delivers on the contrast-heavy matrices (case 2 needs a restart), and the case-2 and 828 000-unknown cases were not run at 1e-9.
* (d) a **vertical-column preconditioner**, new code of about 25 lines: column index of every unknown from the node coordinates (`np.unique` of the rounded x, y of the used nodes); `P` = the entries of `A` whose two unknowns share a column (block-diagonal, SPD); `splu(P)`; preconditioner `z = P^-1 r` (`colblock`) or `z = P^-1 r + V(r)` with the current V cycle (`colblock_amg`). Reference implementation: `research/fem-amg-thin-layers/lib/variants.py` (`column_ids`, `column_matrix`, `make_preconditioner`).

## 2. Measured impact (README section 7)

| Case | default total s | colblock (ratio) | colblock_amg (ratio) |
| :-- | --: | --: | --: |
| example 2 mm, 67 229 unknowns | 4.06 | 0.16 | 0.31 |
| thin4 1 mm, 246 468 | 8.51 | 0.37 | 0.51 |
| example 1 mm, 275 724 | 10.15 | 0.55 | 0.64 |
| case 2 plate 1 mm, 84 375 | 0.67 | 1.09 | 1.01 |
| case 2 plate 0.5 mm, 315 375 | 2.09 | 2.53 | 1.40 |
| example 0.732 mm, 487 048 | 12.31 | 1.07 | 0.84 |
| the 29 frozen records (6 480 to 93 060 unknowns): median / worst | | 0.14 / 0.85 | 0.61 / 1.42 |

Fields agree with the default to at most 1.1e-9 K (unknown vector), `colblock` repeats bitwise, the default and `colblock_amg` to 4e-10 K. Peak memory equals the default's at 487 000 unknowns (3.04 GB: the extra LU of the column blocks was not visible in the peak at that precision). Setup of both is below 1 s.

## 3. Recommendation per decision (executor's proposal; the reviewer judges)

* (a), (c) pyamg variants and hierarchy reuse: **do not adopt.** No variant gets 10 % on the example board at 1 mm; evolution cuts iterations 10-fold but costs 5 times more in total; reuse cannot make an expensive setup pay because its solve alone is slower than the default's total (5.5 s against 4.2 s at 2 mm). A **clear negative result** for the question as posed.
* (b) rtol 1e-9: not proposed without the case-2 and large-case runs.
* (d) column preconditioner: **the acceptance rule of README section 3 is not met** (fails on case 2 and at 487 000 unknowns), so by the rule it is not adopted. It is a strong, cheap result for thin boards below about 300 000 unknowns (every one of the 29 records converges, 2 to 25 times faster with `colblock`), so the maintainer may want a selection rule, for example the column solve below a unknown-count threshold or by a probe, which needs more cases than the three sizes and two thick plates measured here (the vertical share of the coupling does not separate the cases, README 7.4). Decision left to the maintainer, after the reviewer.

## 4. What adoption of (d) would need (normal rules of CLAUDE.md)

* a `fix/` or `feature/` branch from `development`, executor then reviewer then maintainer; before that, the missing measurements: case 2 at 828 000 unknowns (needs more than 4 GB), the boards between 300 000 and the cap with real stacks, the surface and column read-outs per variant, a second platform;
* the whole battery with the real-board environment loaded (the FEM tests, `tests/test_fem_*.py`, the frozen FEM records);
* frozen impact: the field changes by at most about 1e-9 K, so no pending file is expected, but the 29 records are not frozen yet (`pending/fem-records.json`) and would have to be recomputed and compared to their tolerance;
* `docs/theory.md` 4a (solver paragraph), `docs/models.md`, `docs/validation.md` (the speed numbers with tree and reference), the memory law in `memory.py` if the peak changes (the LU of the blocks was not priced), CHANGELOG, the FEM tooltip if it quotes a time;
* a test that fixes the iteration-count order of magnitude on a small thin-layer system, as `research/fem-amg-thin-layers/tests/test_amg_variants.py` does for the tool.

