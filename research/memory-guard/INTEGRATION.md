# Integration: the memory guard in the program

Design for a `feature/memory-guard` branch off `develop` (release 2.5.0, item 'memory limit and guard' of `docs/versions.md` Planned, with the SOR block guard and, if the ladder confirms it, the cell-major numbering). The research branch changes nothing of the program; the prototype is `lib/memory_model.py`, the coefficients are provisional until `study_memory_ladder.py --run --fit` has been run (README 12). The measured impact of each proposal is **to be filled in** after that run; a table at the end lists what each item must show.

## 1. `pcbthermal/memory.py` (new module, no GUI imports, no new dependency)

Public functions (the prototype's names, adopted as they are):

| Function | Role |
| :-- | :-- |
| `ram_bytes()` | physical memory (os.sysconf; macOS `sysctl hw.memsize`; Linux `/proc/meminfo`; Windows `GlobalMemoryStatusEx` by ctypes; the cgroup limit lowers it); None if unreadable |
| `limit_bytes(fraction, ram)` | `fraction x RAM`, or the fixed fallback when the RAM is unreadable |
| `estimate_bytes(unknowns, klass, transient)` | the law `base + k N (N / 500 000)^(p - 1)` per class |
| `classify_layered(layers, laminate_rule)`, `classify_solid3d(slabs)` | the class of a case from what the program already knows |
| `analytic_bytes(tiles, layers, modes)` | the dense tile matrices of the Analytic correction |
| `verdict(estimate, limit, ...)` | `"ok"`, `"slow"` or `"refuse"` |
| `largest_unknowns(klass, limit)`, `cell_that_fits(count, klass, limit, cell)` | the inverse: how many unknowns fit, and the cell that brings a model under the limit (for the message and the Auto suggestion) |
| `sor_block_fits(n, limit)` | replaces `fvm.MAX_SOR_BLOCK` |
| `check(problem, models, options)` (new, not in the prototype) | the one entry the callers use: counts the unknowns of every selected model (`fvm.unknowns`, `fdm.unknowns`, `solid3d.unknowns`, the tile count for the Analytic), classifies, returns a list of `(model, unknowns, estimate, verdict, cell_that_fits)`; raises `MemoryGuardError(ValueError)` with the text for the first `"refuse"` |

The coefficient table lives in the module as constants with a comment giving the ladder run they come from (no date, the run is named by the series), and the **fitted values multiplied by the margin** (README 13, item 1). The prototype's unknown-count helpers are not copied; the real ones are the program's.

Physical memory detection without `psutil`: one reason is the licence table in the README (a new dependency would need a row and a check); the other is that one number does not need it. If the maintainer prefers the available memory, `psutil.virtual_memory().available` is BSD-3-Clause and mature, and that is the only case in which a dependency is justified.

## 2. Where the verdict is used

1. **`api.simulate`**: first thing after `SolverOptions.validate()`, `memory.check(problem, options.models, options)`; a `"refuse"` raises `MemoryGuardError` before any array is allocated (the message: the model, the unknowns, the estimate in GB, the limit, and "use a cell of X mm or more"); a `"slow"` adds a warning to the simulation (`problem_warnings`), shown in the Results summary and the report. `solid3d.check_size` and `MAX_CELLS` are removed (the 3D solid is covered by the same call); `solid3d.size_limit` stays for the offline studies, now over the ceiling.
2. **`jobs.py`** (the calculation process): the check is made in the parent before the process is started (the user gets the message at once, nothing is spawned); the child repeats it because `jobs` can be called by other code, and a refusal comes back as the job's error text. The transient and animation jobs use `transient=True`.
3. **Interface**: `panels.py` `_update_cells` shows `"{n} unknowns, about {GB} GB of {limit} GB"` per selected model, coloured green / amber / red from the verdict, replacing the fixed ">500 000" and "> MAX_CELLS" notes; the Run button is disabled with the reason as a tooltip when the verdict is "refuse"; the **Auto** cell suggestion (`api.suggest_cell_mm`) takes the larger of the heater-based cell and `cell_that_fits`, and says so. The Preferences page for the solver gets a number field "Memory limit (% of the physical memory)", default 70, range 10 to 95, tooltip: what it means, the detected memory, that the estimate may be wrong by the margin shown. A new `solver.memory_fraction` key in `data/defaults.json` (new projects and the user file; `api.default_options` reads it); the Power Calculator and the other callers of `simulate` are covered by (1).
4. **CLI**: `run`, `transient`, `convergence` print the refusal message and exit with code 2 (a distinct code so scripts can tell it from a failure); `--memory-fraction` overrides the setting; `solvers` and `convergence` check every cell they will try before starting.
5. **SOR**: `fvm.Network.solve_sor` and `_block_sor` ask `memory.sor_block_fits(n, limit)` instead of comparing with `MAX_SOR_BLOCK`; the fallback to the direct solver and its warning stay, with the new reason in the text.

## 3. The ordering of the unknowns (separate, smaller change in `fvm.py` and `fdm.py`)

`Network.solve_steady` (and the `splu` calls of the transient in `fvm.py` and `profiles.py`) permutes the matrix and the right-hand side cell-major before the factorisation and undoes it after (`lib/cell_major.py` is the prototype). The permutation is `np.arange(nl * ny * nx).reshape(nl, ny * nx).T.ravel()`; the ragged `drop` mask is applied in the permuted order. It is **the same linear system**; the answer agrees with today's to the solver's round-off (accepted: below 1e-9 K on the five boards of `tests/test_measure_and_ordering.py` and on the example boards of the program's own regression numbers). Because the minimum-degree ordering depends on the input numbering the factor changes, so the results are not bit-identical; the frozen reference numbers of the program (the regression table the tester agent runs) must agree to the printed digits, which the prototype test supports but the full table has not been run. Adopt only if the ladder (README 5) reproduces the gain on the laminate boards and no class loses more than 10 %. The estimator then gets the cell-major coefficients for the layered classes (the `@cell_major` entries of `fit.json`), because the guard must describe the code that runs.

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
| Cell-major numbering changes the last digits of results and the frozen reference numbers | adoption conditional on the regression table; separate commit so it can be reverted alone |
| The count shown differs from the count solved (laminate nodes, blocks) | both come from `fvm.unknowns`; the ladder's equality check (README 7) is kept as a test over the families |
| A user lowers the limit below the base | the minimum of the field is 10 % and the verdict never refuses a board below the base size |

## 7. What each proposal must show once the ladder is run (to be filled in)

| Proposal | Measured impact to report | Criterion |
| :-- | :-- | :-- |
| Estimator | per class: exponent, k, ratios, the largest-point prediction | README 4 |
| 70 % default | the largest board that runs on 8, 16 and 64 GB in each class, against the fixed 250 000 | the 16 GB machine must not page at the limit |
| Cell-major | time and peak on every layered series; answer difference | README 5 |
| SOR block | measured 16 n^2; the largest block allowed | README 6 |
| 3D ceiling | unknowns allowed at 16 GB per class, time | README 10 |
