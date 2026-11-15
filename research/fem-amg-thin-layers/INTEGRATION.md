# INTEGRATION: how the result would enter the program (skeleton)

**Status: nothing measured yet.** This file is filled after the studies of README section 4 and the reviewer's check. Nothing in `pcbthermal/` is edited from this branch.

## 1. What would change

A small change in `femcore.Model.solve` (one call, `pyamg.smoothed_aggregation_solver(...)` with other arguments, line 387), possibly:

* (a) the strength argument (theta, or evolution with parameters) and/or smoother arguments: a one-line change, and the new constant is documented in the docstring and `docs/theory.md` 4a (what changed, the iteration count measured, the source);
* (b) tolerance `rtol` if E1b shows it is free;
* (c) hierarchy reuse: `Model.solve` keeps the multilevel object on the model (or an optional `preconditioner=` argument) so that the computed-h loop of the API and the FEM transient reuse it; a larger change, with the stale-hierarchy rule (rebuild when CG needs more than N iterations).

## 2. Measured impact

To be filled: table per case (iterations, setup, solve, total, peak GB, difference in K), the 29 records, case 2 at 828 000 unknowns.

## 3. Recommendation per decision

To be filled: adopt / do not adopt for (a), (b), (c); each with the numbers that decide, against the acceptance rule of README section 3.

## 4. What adoption needs (normal rules of CLAUDE.md)

* a `fix/` or `feature/` branch from `development`, executor then reviewer then maintainer;
* the whole battery with the real-board environment loaded (the FEM tests, `tests/test_fem_*.py`, the frozen FEM records);
* a pending file only if a frozen number moves (the field should change by less than 1e-8 K; the FEM records are in `tests/regression/data/pending/fem-records.json`, not yet frozen);
* `docs/theory.md` (solver paragraph), `docs/models.md`, `docs/validation.md` (the speed numbers, each with its tree and reference), the memory law in `memory.py` if the peak changes, CHANGELOG, the FEM tooltip if it quotes a time;
* a test that fixes the iteration count order of magnitude on a small thin-layer system, so a silent return to 300 iterations is caught.
