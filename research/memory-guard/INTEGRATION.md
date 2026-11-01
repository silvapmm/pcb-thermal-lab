# Integration: the memory guard in the program

Design for a `feature/memory-guard` branch off `develop` (release 2.5.0, item 'memory limit and guard' of `docs/versions.md` Planned, with the SOR block guard and, if the ladder confirms it, the cell-major numbering). The research branch changes nothing of the program; the prototype is `lib/memory_model.py` with the measured coefficients (`MEASURED`, README 5.2) and the measured SOR block cost. The measured impact of each proposal is in section 7. Decisions left to the maintainer: README 13.

## 1. `pcbthermal/memory.py` (new module, no GUI imports, no new dependency)

Public functions (the prototype's names, adopted as they are):

| Function | Role |
| :-- | :-- |
| `ram_bytes()` | physical memory (os.sysconf; macOS `sysctl hw.memsize`; Linux `/proc/meminfo`; Windows `GlobalMemoryStatusEx` by ctypes; the cgroup limit lowers it); None if unreadable |
| `limit_bytes(fraction, ram)` | `fraction x RAM`, or the fixed fallback when the RAM is unreadable |
| `estimate_bytes(unknowns, klass, transient)` | the law `base + k N (N / 500 000)^(p - 1)` per class |
| `classify_by_t(model, unknowns, cells)` | the class from the **nodes per plan cell** t = unknowns / (nx ny), which the program already has (the layer count alone and the laminate rule alone do not predict the memory: README 5.1); replaces `classify_layered` and `classify_solid3d` of the first prototype |
| `estimate_measured(model, unknowns, cells, transient)` | the estimate the guard uses: the law of the class times its safety factor |
| `analytic_bytes(tiles, layers, modes)` | the dense tile matrices of the Analytic correction |
| `verdict(estimate, limit, ...)` | `"ok"`, `"slow"` or `"refuse"` |
| `largest_unknowns(klass, limit)`, `cell_that_fits(count, klass, limit, cell)` | the inverse: how many unknowns fit, and the cell that brings a model under the limit (for the message and the Auto suggestion) |
| `sor_block_bytes(n)`, `sor_block_fits(n, limit, share)` | replace `fvm.MAX_SOR_BLOCK`: 72 n^2 bytes (README 9), allowed when it is at most `share` (25 % proposed) of the limit |
| `check(problem, models, options)` (new, not in the prototype) | the one entry the callers use: counts the unknowns of every selected model (`fvm.unknowns`, `fdm.unknowns`, `solid3d.unknowns`, the tile count for the Analytic), classifies, returns a list of `(model, unknowns, estimate, verdict, cell_that_fits)`; raises `MemoryGuardError(ValueError)` with the text for the first `"refuse"` |

The coefficient table (`MEASURED`) lives in the module as constants with a comment giving the series they come from; the base is 0.08 GB (the baseline child; the application with Qt starts higher and the module should read the process's own resident size at the start instead), and each class carries its safety factor 1.11 to 1.46 (README 13.b):

| Class | t | k (B per unknown at 500 000) | p | safety |
| :-- | :-- | --: | --: | --: |
| fvm_t_le_3.5 | up to 3.5 | 2 409 | 1.10 | 1.25 |
| fvm_t_3.5_4.5 | 3.5 to 4.5 | 4 174 | 1.08 | 1.16 |
| fvm_t_gt_4.5 | above 4.5 | 6 441 | 1.36 | 1.46 |
| fdm_t_le_4.5 | up to 4.5 | 4 041 | 1.12 | 1.11 |
| fdm_t_gt_4.5 | above 4.5 | 8 793 | 1.41 | 1.16 |
| solid3d_t_le_6 | up to 6 | 5 609 | 1.26 | 1.12 |
| solid3d_t_6_12 | 6 to 12 | 10 510 | 1.28 | 1.18 |
| solid3d_t_gt_12 | above 12 | 18 641 | 1.23 | 1.40 |

The Lumped (455 B per unknown) and the Analytic (0.5 GB at 640 000 unknowns with vias) never refuse in the measured range; the transient factor 2 is not measured. The prototype's unknown-count helpers are not copied; the real ones are the program's.

Physical memory detection without `psutil`: one reason is the licence table in the README (a new dependency would need a row and a check); the other is that one number does not need it. If the maintainer prefers the available memory, `psutil.virtual_memory().available` is BSD-3-Clause and mature, and that is the only case in which a dependency is justified.

## 2. Where the verdict is used

1. **`api.simulate`**: first thing after `SolverOptions.validate()`, `memory.check(problem, options.models, options)`; a `"refuse"` raises `MemoryGuardError` before any array is allocated (the message: the model, the unknowns, the estimate in GB, the limit, and "use a cell of X mm or more"); a `"slow"` adds a warning to the simulation (`problem_warnings`), shown in the Results summary and the report. `solid3d.check_size` and `MAX_CELLS` are removed (the 3D solid is covered by the same call); `solid3d.size_limit` stays for the offline studies, now over the ceiling.
2. **`jobs.py`** (the calculation process): the check is made in the parent before the process is started (the user gets the message at once, nothing is spawned); the child repeats it because `jobs` can be called by other code, and a refusal comes back as the job's error text. The transient and animation jobs use `transient=True`.
3. **Interface**: `panels.py` `_update_cells` shows `"{n} unknowns, about {GB} GB of {limit} GB"` per selected model, coloured green / amber / red from the verdict, replacing the fixed ">500 000" and "> MAX_CELLS" notes; the Run button is disabled with the reason as a tooltip when the verdict is "refuse"; the **Auto** cell suggestion (`api.suggest_cell_mm`) takes the larger of the heater-based cell and `cell_that_fits`, and says so. The Preferences page for the solver gets a number field "Memory limit (% of the physical memory)", default 70, range 10 to 95, tooltip: what it means, the detected memory, that the estimate may be wrong by the margin shown. A new `solver.memory_fraction` key in `data/defaults.json` (new projects and the user file; `api.default_options` reads it); the Power Calculator and the other callers of `simulate` are covered by (1).
4. **CLI**: `run`, `transient`, `convergence` print the refusal message and exit with code 2 (a distinct code so scripts can tell it from a failure); `--memory-fraction` overrides the setting; `solvers` and `convergence` check every cell they will try before starting.
5. **SOR**: `fvm.Network.solve_sor` asks `memory.sor_block_fits(n, limit)` instead of comparing with `MAX_SOR_BLOCK`; the fallback to the direct solver and its warning stay, with the new reason in the text. The comment of `fvm.py` that says 5 000 unknowns are 200 MB must be corrected: they are about 1.8 GB (README 9).

## 3. The ordering of the unknowns (separate, smaller change in `fvm.py` and `fdm.py`)

`Network.solve_steady` (and the `splu` calls of the transient in `fvm.py` and `profiles.py`) permutes the matrix and the right-hand side cell-major before the factorisation and undoes it after (`lib/cell_major.py` is the prototype). The permutation is `np.arange(nl * ny * nx).reshape(nl, ny * nx).T.ravel()`; the ragged `drop` mask is applied in the permuted order. It is **the same linear system**; the answer agrees with today's to the solver's round-off (accepted: below 1e-9 K on the five boards of `tests/test_measure_and_ordering.py` and on the example boards of the program's own regression numbers). Because the minimum-degree ordering depends on the input numbering the factor changes, so the results are not bit-identical; the frozen reference numbers of the program (the regression table the tester agent runs) must agree to the printed digits, which the prototype test supports but the full table has not been run. **Measured (README 6):** the answer is the same to 1.2e-12 K on four boards; no point is slower than 1.3 times or takes more than 1.08 times the memory; the reviewer's gain (21.4 s and 4.5 GB to 12.7 s and 3.0 GB) was **not reproduced** on 2-layer boards, and a gain appears only on one board (4-layer stripes at 1.1 million unknowns: 35 s and 6.86 GB against a layer-major run stopped above 7.5 GB). The class laws are unchanged within the margin, so the guard does not depend on this change. Recommendation: do not adopt it for the guard; adopt it separately only if boards of that kind at 1 million unknowns must run, after the frozen numbers confirm the last digits, and after repeating the stripes point on a quiet machine.

## 4. Tests of the feature

* `tests/test_memory.py` (unit): the prototype's tests moved with the module, plus the fitted coefficients against the ladder's file shipped as test data (a handful of points, not the ladder).
* Simulated machines: patch `memory.ram_bytes` to 8, 16 and 64 GB; the same board is "refuse", "slow" and "ok".
* `api.simulate` refuses the monkey's 502 mm board at 2 mm with computed h in under 60 s and allocates nothing large (assert on `tracemalloc` peak below 200 MB).
* A failed RAM read (patched to None) falls back to the fixed limit and the 3D ceiling.
* `tests/test_gui_stress.py`: a scenario that sets the limit to 10 % in Preferences, checks the Run button is disabled with a message for a fine cell, checks Auto gives a cell the verdict accepts, and restores; the existing monkey test, which once timed out on the 3D solid, must now end in the refusal quickly.
* Documentation gate and tooltips: the new field has a tooltip (`gui/tips.py`), the user guide (`pcbthermal/help/index.html`) and `tests/test_help.py` get the new words.
* CLI: exit code 2 and the message text.

## 5. Documents to update at adoption (not now)

`docs/models.md` and `docs/theory.md` (the memory law and its picture: figures 04 and 05 of this folder, copy to `docs/images/`), `docs/validation.md` (the ladder table), `docs/versions.md` (the item leaves Planned), `CHANGELOG.md`, `README.md` (the setting), `CLAUDE.md` (structure and a Decisions Log entry); the text for them is in `docs/` of this folder.

## 6. Risks

| Risk | Mitigation |
| :-- | :-- |
| The estimate is below the real peak and the machine pages | the fitted maximum ratio and 1.1 as margin; the point of the ladder with the largest ratio is shown in the documents; the guard is a refusal, not a promise |
| The estimate is above the real peak and a fine run that would work is refused | the limit is editable; the message gives the estimate so the user can raise it; the fallback is a documented Preferences value |
| One machine measured | the coefficients are bytes per unknown of the algorithm, mostly independent of the RAM, but SciPy builds and the operating system change them; the ladder is a one-command repeat, and the coefficients are in one table |
| The Analytic and the Lumped have laws that are less certain | their verdict is "slow" at most until measured; only the sparse classes refuse |
| Installed memory differs from usable memory (other programs, container) | cgroup limit read; a note in the Preferences hint; the free memory is a later option |
| The RAM read fails on a platform not tested (Windows) | fallback to the fixed limit and a log line; test with the patched function |
| Cell-major numbering changes the last digits of results and the frozen reference numbers | not part of the guard (README 6); if adopted, conditional on the regression table, separate commit so it can be reverted alone |
| Installed memory is not usable memory (12.0 GB limit against about 12 GB usable at rest on 16 GB) | lower default (60 %) or the minimum with the available memory at the start of the run (README 8); the run of this study swapped once with a limit-sized workload next to other work |
| The estimate for thick graphs is extrapolated (3D above 240 000 to 400 000 unknowns; FVM t above 4.5 has a steep regime) | safety factors 1.40 and 1.46; the first runs near the limit on a real machine should record their peak and the module should log estimate and measurement |
| The count shown differs from the count solved (laminate nodes, blocks) | both come from `fvm.unknowns`; the ladder's equality check (README 7) is kept as a test over the families |
| A user lowers the limit below the base | the minimum of the field is 10 % and the verdict never refuses a board below the base size |

## 7. Measured impact of each proposal

| Proposal | Measured | Where |
| :-- | :-- | :-- |
| Estimator by class of t | exponent 1.08 to 1.41 (thick graphs steeper); ratios measured/fitted 0.75 to 1.33 in the worst class; safety factors 1.11 to 1.46; the provisional table of the preparation was up to 2.96 times below a measurement (6-layer plain board at 960 000 unknowns, 8.4 GB) and up to 2.4 times above (laminate boards) | README 5.2, 5.3 |
| 70 % default | 70 % of 16 GB is 12.0 GB and the usable memory at rest is about 12 GB; the machine swapped once with 5 to 7 GB solves next to other work. The largest boards that run at 11.2 GB (limit with safety): FVM 3.1 million (t up to 3.5), 2.0 million (t 3.5 to 4.5), 0.94 million (t above 4.5); FDM with laminate nodes 0.87 million; 3D 1.36 million, 786 000, 439 000 (the fixed limit is 250 000) | README 5.4, 8, 10 |
| Cell-major | harmless, gain conditional, reviewer's numbers not reproduced | README 6 |
| SOR block | 72 n^2 bytes measured (the first estimate 16 n^2); 5 000 unknowns take about 1.8 GB, not 200 MB | README 9 |
| 3D ceiling | 2 million never binds at 16 GB; binds from about 26 GB (6 slabs) to 100 GB (26 slabs); predicted time at 2 million unknowns about 120 s | README 10 |
| Slow mark | predicted solve time above 30 s instead of 35 % of the RAM; at the limit of 16 GB the predicted times are 17 to 62 s | README 5.4, 13.c |
