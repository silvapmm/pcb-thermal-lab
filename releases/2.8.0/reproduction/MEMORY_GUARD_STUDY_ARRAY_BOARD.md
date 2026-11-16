# Memory guard and `point-via-convergence/study_array_board` (reproduction pass of 2.8.0)

Question from part A of the reproduction pass (`PART-A.md` on `release/2.8.0-reproduction`, item 3 and the table row of `study_array_board`): the study ran on v2.7.1 but is refused on the tree of 2.8.0 at its finest cell (FVM, 0.0625 mm, 451 584 unknowns: "need about 10.4 GB ... more than the 10.3 GB allowed (60 % of the 17.2 GB of memory); use a cell of 0.1 mm or more"). Is it an intended consequence of 2.8.0 or a regression of the guard?

Tree: `development` at 232ba648. Reference: `git archive v2.7.1` (program and the research folder). Machine: 16 GB (17.2 GB decimal), limit 10.31 GB.

## 1. Verdict

**(c) Neither.** The memory law of the FVM and the FDM is the same in v2.7.1 and in 2.8.0 for this board, to the byte, and the measured peaks of the two trees agree within 1 %. The refusal comes from the **base** of the estimate: the resident size of the process, read once at the first estimate of the process (`memory.baseline_bytes`). The study runs its independent references (the fine 2D solver and the 3D solver with drawn barrels, which import nothing from the program) **before** its first program run, so the base is the resident size those references left: about 7.55 GB in the 2.8.0 run against about 6.0 GB in the v2.7.1 run. The same growth of 2.82 GB lands at 10.37 GB (refused) in one run and 8.8 GB (accepted) in the other. The difference is the history of the process and the state of the machine (part D ran beside it), not a change of the program.

The statement of `PART-A.md` that "the estimates of the coarse cells fell (8.8 to 7.6 GB): the memory law was re-measured in 2.8.0" is **wrong**: 8.8 GB was the estimate of the 0.0625 mm cell in the v2.7.1 run (the only one above the memory available then), 7.6 GB the estimate of the coarse cells in the 2.8.0 run (a base of 7.55 GB plus at most 0.09 GB of growth).

## 2. Evidence

### 2.1 The law did not change for this board

`git diff v2.7.1 development -- pcbthermal/memory.py` adds the FEM law (`FEM_K1`, `FEM_DIRECT_BYTES`, used only when the FEM is ticked), the drawn-copper raster term `drawn_run_bytes` (FVM and FDM, only for a drawn layer with a cell cut by a zone edge) and an `extra` argument of `cell_that_fits`; `CONTINUOUS` of the FVM, FDM and 3D solid, `VIA_GAIN`, `VIA_CELLS_REF`, the factors and the fraction are unchanged. The surface read-out arrays (`T_surface`, the means, the flags) and the face fluxes add no term to the estimate.

The array board has full-board zones on a 21 mm board, whose edges fall on grid lines at every cell of the study, so `drawn_run_bytes` is 0. Estimate of the growth (base 0), both trees, identical:

| model | cell mm | unknowns | via cells | growth estimate GB | bytes per unknown |
| :-- | --: | --: | --: | --: | --: |
| FVM | 1 | 1 764 | 18 | 0.003 | 1 590 |
| FVM | 0.125 | 112 896 | 96 | 0.494 | 4 380 |
| FVM | 0.0625 | 451 584 | 250 | 2.816 | 6 237 |
| FDM | 0.125 | 114 244 | 96 | 0.447 | 3 910 |
| FDM | 0.0625 | 454 276 | 250 | 2.902 | 6 388 |

### 2.2 The measured peak did not change either

Fresh process, `api.simulate` of the copper-filled array board, peak resident size (`/usr/bin/time -l`, `nice -n 10`), growth = peak minus the resident size before the run:

| case | 2.8.0 growth B/unknown | v2.7.1 growth B/unknown | change | estimate / measured growth |
| :-- | --: | --: | --: | --: |
| array board FVM 0.0625 mm (peak 1.99 / 1.97 GB) | 4 223 | 4 194 | +0.7 % | 1.48 / 1.49 |
| array board FDM 0.0625 mm (peak 1.93 / 1.90 GB) | 4 078 | 4 001 | +1.9 % | 1.57 / 1.60 |
| array board FVM 0.125 mm | 3 389 | 3 424 | -1.0 % | 1.29 / 1.28 |
| example board FVM 1 mm (39 052 unknowns) | 3 215 | 3 248 | -1.0 % | 1.22 / 1.21 |
| example board FDM 1 mm (40 092 unknowns) | 3 284 | 3 208 | +2.4 % | 1.01 / 1.04 |

The arrays that 2.8.0 adds to every steady FVM and FDM result (surface read-out, face fluxes) are within the noise of the peak (a few per cent at most); the estimate stays above the measurement in both trees (the safety factor 1.40 of the FVM, 1.24 of the FDM). The guard does not over-count the solve of this board: at a fresh base it accepts the 0.0625 mm cell with 2.90 GB against 10.31 GB.

### 2.3 The base is what moved

The study (`research/point-via-convergence/scripts/study_array_board.py`, `main`) computes `rb.array_quadrant` at 1/16 and 1/32 mm and `rb.array_3d` at 0.1 and 1/12 mm before its first `pc.max_rise`; `pc.layer_parameters` builds an `fvm.Network` directly and makes no estimate. So the first estimate, which fixes the base for the rest of the process, comes after the references. The process keeps its peak resident after a solve: a light check (the 2D reference at 1/16 mm in a fresh process) gives 0.080 GB before, peak 0.414 GB, 0.413 GB after.

The raw outputs of part A (`repro280/raw/{old,tree}__point-via-convergence__study_array_board.txt` in the session scratchpad) give the base exactly, since the warning "the estimate is above the memory available now" prints the estimate:

* 2.8.0: six warnings at 7.6 GB (the cells 1, 0.5 and 0.25 mm, growth 0.003 to 0.09 GB), two at 8.0 GB (0.125 mm, growth 0.49 GB), refusal at 10.4 GB (0.0625 mm, growth 2.82 GB): base about 7.55 GB.
* v2.7.1: two warnings at 8.8 GB only (the 0.0625 mm pair; the coarse cells were below the 7.2 to 7.6 GB available, so silent): base about 6.0 GB.

The research library of the folder is identical in both trees (`git diff v2.7.1 development -- research/point-via-convergence/lib` is empty).

## 3. What the user sees

Nothing changes for the application or the command line: the calculation process of the window reads its base at start-up, before its first job, and a command-line run is a fresh process, so the array board at 0.0625 mm is estimated at about 2.9 GB and accepted in both versions. The refusal is seen only by a script that does heavy work outside the program before its first program run. The message it gives is right for the base it holds (a cell of 0.1 mm or more fits 10.31 GB with a base of 7.55 GB).

The guard thresholds hold: limit 0.60 x 17.2 GB = 10.31 GB; refuse above it, slow above 30 s, warning (not refusal) above the memory available now.

## 4. Limit to record

`docs/theory.md` (memory law, *Verdicts*) says that the pages a process kept after a solve "are reused by the next solve, so they are not counted again". That holds for the calculation process (base read at start-up) and for a process whose first heavy work is a program run. For a script whose first estimate comes after large solves of its own, the kept pages are counted in the base and the guard can refuse a run that fits; how much depends on what the operating system let the process keep (here 6.0 or 7.55 GB for the same code).

## 5. What to do

1. **The study (research branch of `point-via-convergence`, in the reproduction pass, not a program change)**: read the base before the references, with one line at the start of `main`: `from pcbthermal import memory; memory.baseline_bytes()`. With a fresh base the finest cell is estimated at 2.90 GB and runs, as on v2.7.1. Alternatively run the program cells before the references, or wrap the table in `memory.accept_unknowns("fvm", 500_000)`.
2. **PART-A.md**: correct item 3 and the table row of `study_array_board`: the class is "not run (guard base raised by the study's own references)", not "memory law"; the 8.8 to 7.6 GB comparison mixes two different cells.
3. **The program**: no change needed for 2.8.0. Open question for the maintainer (later, a `fix/` branch with the whole battery if wanted): let a script fix the base explicitly (for example a documented `memory.reset_baseline()` followed by an early `baseline_bytes()` in the studies' helpers), and add the limit of section 4 to the *Verdicts* paragraph of `docs/theory.md`.

## 6. Not verified

The full study was not re-run on either tree: its 3D references at 1/12 mm need about 7 GB, above the 3 GB allowed beside part D. The bases of 6.0 and 7.55 GB are deduced from the printed estimates of the part A outputs and the unchanged law (the arithmetic is exact to the 0.1 GB rounding of the messages); why the operating system left 1.5 GB more resident in the 2.8.0 run was not measured.
