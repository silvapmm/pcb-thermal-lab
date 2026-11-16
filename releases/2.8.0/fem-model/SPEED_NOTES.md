# FEM speed and frozen surface: working notes (`fix/fem-solve-speed`)

Measured with cProfile (`api.simulate`, one model, one process at a time, one run under the heavy-job lock), worktree tree, interpreter of the main checkout.

| Run | Before | After | Assembly (`Model.assemble`, cumulative) before / after |
| :-- | --: | --: | :-- |
| FEM `example_board` 1 mm (275 724 unknowns) | 16.00 s | 11.67 s | 3.58 s / 1.18 s |
| FEM `plate_vias` 1 mm | 3.06 s | 2.22 s | 0.65 s / 0.22 s |

Field change against the old default (CG 1e-12, old assembly): largest node difference 1.4e-10 K (example board), 3.0e-10 K (`plate_vias`); heat balance 1.0000000000028 and 0.99999999999379.
Frozen FEM records regenerated (29): largest temperature change 8.5e-10 K, field sums 1.4e-11 relative, balance 1e-11 W. `PCBT_FROZEN_CELLS=2,1,0.5 pytest tests/regression`: 346 passed in 176 s, peak 4.10 GB resident (3.95 GB footprint), a little over the 4 GB aim.
Surface file: 51 FVM + 51 FDM records, metrics `surface:*`, `part:*:t_max_surface`, `part:*:t_mean_surface`.
Not done: Jacobians computed once and shared by `validate` / `element_volumes` / assembly (only the cost of each pass was cut); the AMG for thin layers (2.9.0).

## What the 2.8.0 refreeze must do with these records (additions, not shifts)

The baseline of the refreeze is run on the tag v2.7.1, which has no surface read-out, no FEM and no FEM block: in `study_diff.py` every `surface:*`, `part:*:t_max_surface`, `part:*:t_mean_surface` metric of the FVM and FDM records is "present in one set only", and the FEM records are only in the new set.

1. **The table `expected_shifts_2.8.0.json`** (written by `make_expected_shifts.py`) carries an `added_metrics` list (read by `regress_classify.diff_sets` since the review of this branch, `REVIEW_SPEED.md`): one scope `{"id": "surface-readout-added", "boards": "*", "models": ["fvm", "fdm"], "cells": "*", "metrics": ["surface:*", "part:*:t_max_surface", "part:*:t_mean_surface"], "note": "surface read-out of 2.8.0 added to the records (fix/fem-solve-speed)"}`. A metric only in the new run is then `expected` where a scope names it by its metric name, and stays an alarm elsewhere. **Do not** cover the additions with a rule on `status`: that rule would also excuse a run that failed.
2. **The FEM records** are a new model (`new_models` of `fem-records.json`): they are only in the new set (`missing.only_in_new`), not shifts; `study_freeze_reference.py` freezes them from `out/final.json` with the surface, `point:t_max` and the block of `finned_block`.
3. **Both pending files** `fem-records.json` and `surface-records.json` are folded by the refreeze (the new frozen file holds every metric) and deleted in the same commit as the others. A record of `surface-records.json` never moves an old metric (`test_pending_shifts_belong_to_the_frozen_release` refuses a clash, and `with_pending` lets a shift win over an addition).
4. **Repeatability**: the FEM records above `FEM_DIRECT_MAX` (CG) are not bit-identical from run to run (largest 5.0e-10 K on `plate_pad|fem|1`, field sums 4e-12 relative, measured by the review); the FEM records are therefore frozen with the class `new` and compared under the tolerance, never `--exact`.

## Memory of the frozen run

`PCBT_FROZEN_CELLS=2,1,0.5 pytest tests/regression` (one process, measured by the review with `/usr/bin/time -l`, same machine and hour): branch 3.75 GB and 3.96 GB maximum resident in two runs (3.60 GB footprint in the first), `development` before the branch 4.21 GB (4.06 GB footprint). The surface arrays and statistics add nothing measurable; the 4.10 GB of the executor's run is the run-to-run variation of the same process; the branch does not raise the peak. Nothing cheap to reduce on this branch.
