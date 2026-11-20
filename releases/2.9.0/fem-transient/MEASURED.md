# FEM transient: the measured memory and time law

Tree `ec15bdc0` (`feature/fem-transient` merged with `development` 648b531f), Apple M4, 16 GB, one fresh process per case, run by the tester with the main `.venv`; machine during the runs: load 1.8 to 2.6, no swap, about 9 GB free plus inactive. Raw files: `measure_fem_transient_direct_limit.py` and `measure_fem_transient_law.py` outputs (kept in the session scratchpad, not in the repository). Growth is the rise of the peak resident size over the process after the imports. Numbers are measured; the constants fitted from them are in `pcbthermal/memory.py` and the fit is arithmetic from the tables below.

## 1. Direct limit table (example board, 8 steps per stage, Crank-Nicolson)

| cell mm | path | unknowns | setup s | step s | CG iterations per step | growth GB | stage s (setup + 8 steps) |
| --: | :-- | --: | --: | --: | --: | --: | --: |
| 4.0 | direct | 20 930 | 0.54 | 0.005 | - | 0.32 | 0.58 |
| 4.0 | cg | 20 930 | 0.06 | 1.148 | 464.6 | 0.19 | 9.24 |
| 3.0 | direct | 32 637 | 1.31 | 0.010 | - | 0.55 | 1.39 |
| 3.0 | cg | 32 637 | 0.07 | 1.837 | 475.2 | 0.26 | 14.77 |
| 2.5 | direct | 46 644 | 3.09 | 0.018 | - | 0.92 | 3.23 |
| 2.5 | cg | 46 644 | 0.09 | 2.408 | 431.1 | 0.38 | 19.35 |
| 2.0 | direct | 67 229 | 7.31 | 0.033 | - | 1.95 | 7.57 |
| 2.0 | cg | 67 229 | 0.12 | 3.155 | 385.9 | 0.55 | 25.36 |
| 1.6 | direct | 106 122 | 10.95 | 0.053 | - | 3.11 | 11.37 |
| 1.6 | cg | 106 122 | 0.16 | 4.236 | 330.0 | 0.90 | 34.05 |

Direct growth per unknown: 15.3, 16.9, 19.7, 29.0, 29.3 kB (superlinear fill). The direct path is cheaper than CG per stage at every size (3 times at 21 000 and at 106 000 unknowns), and a direct step is about 100 times cheaper than a CG step. No size where the direct factor stops fitting was reached (largest 106 122 unknowns, 3.11 GB).

## 2. Law table (15 cases, step response of 40 frames or two cycles of a profile)

| board | cell mm | path | kind | unknowns | steps | seconds | growth GB | ratio to the steady law |
| :-- | --: | :-- | :-- | --: | --: | --: | --: | --: |
| plate_uniform | 2.0 | direct | step | 14 400 | 52 | 2.1 | 0.21 | 0.91 |
| plate_vias | 2.0 | direct | step | 14 400 | 52 | 2.1 | 0.21 | 0.91 |
| finned_block | 2.0 | direct | step | 15 632 | 52 | 3.1 | 0.24 | 0.96 |
| t_outline | 2.0 | direct | profile | 11 007 | 68 | 0.3 | 0.12 | 0.70 |
| example_board | 3.0 | direct | step | 32 637 | 52 | 12.9 | 0.61 | 1.18 |
| example_board | 2.0 | direct | step | 67 229 | 52 | 82.2 | 2.15 | **2.01** |
| finned_block | 1.4 | direct | step | 29 413 | 52 | 8.9 | 0.51 | 1.10 |
| example_board | 2.0 | cg | step | 67 229 | 52 | 142.0 | 0.55 | 1.06 |
| plate_vias | 1.0 | cg | step | 53 181 | 52 | 65.8 | 0.42 | 0.89 |
| finned_block | 1.0 | cg | step | 55 488 | 52 | 66.5 | 0.46 | 0.97 |
| t_outline | 1.0 | cg | profile | 40 140 | 68 | 66.9 | 0.30 | 0.63 |
| example_board | 2.0 | cg | profile | 67 229 | 68 | 241.1 | 0.49 | 0.95 |
| hatched_copper | 1.0 | cg | step | 57 600 | 52 | 54.4 | 0.47 | 0.99 |
| one_layer_pad | 1.0 | cg | step | 40 328 | 52 | 36.1 | 0.31 | 0.65 |
| example_board | 1.0 | cg | step | 275 724 | 52 | 364.2 | 2.06 | 0.97 |

The ratio is the growth over the steady law of the path (15.9 kB per unknown direct, the CG law of `memory.py` otherwise). The largest direct ratio is 2.011 and the largest CG ratio 1.065. The direct-path rows of the two scripts differ at 67 229 unknowns (1.95 and 2.15 GB): the allocator reuse of freed factors moves the direct growth by about 10 %, as the review saw (DESIGN.md 14.3); the fit takes the larger.

## 3. Fitted constants (each with its margin)

| constant | was | now | from |
| :-- | --: | --: | :-- |
| `FEM_TRANSIENT_FACTOR_DIRECT` | 2.0 | **2.31** | 2.011 x 1.15; the old 2.0 under-predicted the 2.15 GB case (it gave 2.14 GB) |
| `FEM_TRANSIENT_FACTOR_CG` | 2.0 | **1.22** | 1.065 x 1.15 |
| `FEM_TRANSIENT_DIRECT_MAX` | 30 000 | **100 000** | measured to 106 122 unknowns (3.11 GB), direct cheaper than CG at every size; memory limited: `memory.fem_time_law` falls back to CG when the direct factor (36.7 kB per unknown, 3.9 GB at 106 000) does not fit the budget |
| direct time | 3e-6 s per unknown and step | setup 7.31 s (n/67 229)^1.7 per stage + 5.7e-7 s per unknown and step | factorisation 0.54 to 10.95 s (model 1.0 / 2.1 / 3.9 / 7.3 / 15.9 s), step 0.25 to 0.5 us per unknown |
| CG time | 5.2e-5 s per unknown and step | setup 0.2 s per stage + 6.0e-5 s per unknown and step | step 5.5e-5 down to 4.0e-5 s per unknown, 330 to 475 iterations |
| `FEM_RUN_SECONDS_MAX` | 600 | 600 (unchanged) | the data does not change the rule; the setup term makes the prediction honest for large direct meshes |

The estimate of a direct time run is 36.7 kB per unknown at every size (the conservative top of the measured 15.3 to 32 kB per unknown; 3.90 GB predicted against 3.11 GB measured at 106 122 unknowns). Not measured: a direct case above 106 122 unknowns (no upper bound for the direct limit was found), the CG path on a mesh below 40 000 unknowns with a profile, and any other machine.
