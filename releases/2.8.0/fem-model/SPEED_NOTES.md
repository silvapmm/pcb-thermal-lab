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
