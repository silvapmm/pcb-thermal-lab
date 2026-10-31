# Memory limit and guard

**Status: prepared and planned; nothing has been run.** The scripts compile (`py_compile`) and are ready; the machine was busy, so the measurements, the figures that need data and the tests are to be run after the 2.4.5 release (section 12 says how, in order). Every number in this document is either quoted from an earlier measurement of the repository (with its source) or marked as provisional; no number was produced by this folder yet.

## 1. The question

The program solves sparse systems whose size is set by the cell the user chooses. Nothing stops a cell that needs more memory than the machine has: the maintainer's monkey test once hung on a 1 million unknown 3D solid, and the layered models have only a note "slow" above 500 000 unknowns in the panel. The fixed `solid3d.MAX_CELLS = 250 000` is a rule for one model and one machine, and the SOR guard `fvm.MAX_SOR_BLOCK = 5000` is another fixed number. The item 'memory limit and guard' of `docs/versions.md` (Planned, release 2.5.0) asks for one guard by **estimated memory**: the physical memory of the machine, a default limit of 70 % editable in Preferences, an estimate of the peak memory of each model from its unknown count and class, and a verdict (ok, slow, refuse) used by `api.simulate`, the jobs, the interface and the command line.

What would answer it:

1. A **law** for the peak memory of each class of model against its unknowns, fitted on a ladder of boards, with the error of the fit and a margin so that the estimate does not fall below the measurement.
2. A **detector** of the physical memory that works on macOS, Linux and Windows without a new dependency.
3. The **cell-major numbering** of the unknowns, measured once as a gain of memory and time and shown to give the same answer.
4. The **memory of the SOR block** (a dense inverse) replacing the constant 5000.
5. A **design** of `pcbthermal/memory.py` and where it is called (`INTEGRATION.md`), with a stress scenario.

### 1.1 Pictures

Drawn by `scripts/make_diagrams.py` (no data; not yet run, the files appear in `figures/` when it is):

* `figures/fig_01_guard_flow.png`: from the board to the verdict and the four places that use it.
* `figures/fig_02_board_section_and_unknowns.png`: a section of a two-layer board with copper absent in part of each layer, the copper nodes and the laminate nodes that exist only next to absent copper. It shows why the unknown count is not layers times cells and why the count shown in the panel must come from `fvm.unknowns`.
* `figures/fig_03_numbering_and_matrix_pattern.png`: the matrix pattern of a three-layer board in the layer-major and in the cell-major numbering.

Drawn by `scripts/make_figures.py` after the ladder is run: `fig_04_memory_against_unknowns.png` (peak memory against unknowns for every series with the fitted law and the 70 % limit of 8, 16 and 64 GB machines) and `fig_05_time_and_cell_major.png` (time and memory of the layer-major and cell-major series).

## 2. What is already measured (quoted, not reproduced here)

All of these were measured on the maintainer's 16 GB machine by other folders; they are the starting values of the provisional coefficients in `lib/memory_model.py` and the test of whether the new ladder agrees with them.

| Model and board | Unknowns | Time | Peak memory | Source |
| :-- | --: | --: | --: | :-- |
| 3D solid, plain two-layer board (6 slabs) | 158 000 / 248 000 / 393 000 / 500 000 | 2.0 / 3.5 / 7.5 / 9.3 s | 0.75 / 1.2 / 2.65 / 3.3 GB | `research/solid3d-verification/docs/for-the-project-documents.md` |
| 3D solid, example board (16 slabs) | 158 000 / 247 000 / 392 000 / 512 000 | 7.2 / 15.3 / 32.8 / 57.7 s | 2.15 / 3.5 / 7.4 / 9.9 GB | same |
| layered FVM, plain board | 992 000 / 1 975 000 | 5.2 / 12.4 s | 2.7 / 5.5 GB | same |
| layered FVM, laminate rule, 2 layers, 0.25 mm | 637 000 | 21 s (21.4) | 4.5 GB | `docs/versions.md` Planned, after `fix/laminate-nodes` |
| layered FVM, laminate rule, 4 layers, 0.25 mm | 681 000 | 66 s | 7.6 GB | same |
| same 2-layer board, cell-major numbering | 637 000 | 12.7 s | 3.0 GB | reviewer of `fix/laminate-nodes` (4 layers: 50 s; memory not recorded here) |

What the table already suggests, to be tested and not assumed:

* The plain layered board is **linear** in the unknowns between 1 and 2 million (2.7 and 5.5 GB: exponent 1.0, 2.7 KB per unknown), not N^(4/3). The 3D solid on the example board is steeper: 3.5 to 9.9 GB for 247 000 to 512 000 unknowns is an exponent of about 1.4, and on the plain 6-slab board about 1.3 (these two exponents are computed here from the table above, nothing else).
* The memory per unknown is **not constant across classes**: 2.7 KB (plain layered), 6.6 KB (3D plain), 7 KB and 11 KB (laminate rule, 2 and 4 layers, layer-major), 14 to 19 KB (3D example board). A guard with one constant would be wrong by a factor of 7 either way; hence the classes.
* The two laminate-rule boards are the dangerous ones for the layered models, since the count shown by the panel was wrong for them (`docs/versions.md` Planned: the panel shows 2 400 where 9 600 are solved on a case; corrected by `fix/unknown-count`, with `fvm.unknowns` now counting the ragged nodes).

## 3. Sources to read (status in the vocabulary of `research/theory/BIBLIOGRAPHY.md`)

Section 22 of the bibliography lists them with their status; none was opened in this preparation (status **N** or **M**). What each would give:

| Key | What it gives to this study | Plan |
| :-- | :-- | :-- |
| [George1973] A. George, "Nested dissection of a regular finite element mesh", SIAM J. Numer. Anal. 10 (1973) 345-363 | Fill-in of the factor of an n x n grid is O(n^2 log n) and the operation count O(n^3); on a k x k x k grid fill O(k^4) = O(N^(4/3)). It is the reason for the exponent 4/3 of a 3D-like graph and for 1 (up to a logarithm) of a thin one. | Find the paper (SIAM, paywalled; the result is also in textbooks); read the theorem statements and write the page numbers. Marked M until then. |
| [Davis2006] T. A. Davis, *Direct Methods for Sparse Linear Systems*, SIAM, 2006 | Fill-in, orderings (minimum degree, nested dissection), the memory of LU and Cholesky; the effect of a different numbering on the ordering. | Chapter 7 (orderings) and 8 (fill) from a library copy or the author's pages; extract the statements on tie-breaking. M until read. |
| [LiSuperLU2005] X. S. Li, "An overview of SuperLU: algorithms, implementation, and user interface", ACM Trans. Math. Softw. 31 (2005) 302-325, and the SuperLU user guide | What the memory of `splu` holds: the L and U factors, the permuted copy, the work arrays; the meaning of `permc_spec` (MMD_AT_PLUS_A). | The user guide is open (the author's site, `crd-legacy.lbl.gov/~xiaoye/SuperLU`); read the sections on memory and column ordering. N now. |
| [SciPySuperLU] SciPy documentation, `scipy.sparse.linalg.splu` and `spsolve` | The arguments (`permc_spec`, `diag_pivot_thresh`), the copy of the matrix SciPy makes (`spsolve` converts to CSC/CSR), so the peak is more than the factor. | Open the page, read the notes; the version installed here is read from `pip show`. M now (the entry exists in the bibliography as M). |
| [GeorgeLiu1981] A. George, J. W. H. Liu, *Computer Solution of Large Sparse Positive Definite Systems*, Prentice-Hall, 1981 | The minimum-degree algorithm and its tie-breaking (the reason the numbering changes the ordering). | Only if Davis is not enough. N. |
| [Python resource] Python `resource.getrusage` and `os.wait4` documentation; `man getrusage` on macOS and Linux | `ru_maxrss` unit (bytes on macOS, kilobytes on Linux) and that `wait4` returns the usage of one child. | Open the documentation page and the man pages; one test of the wrapper checks it (section 8). M now. |

Nothing of a third party is stored here. The claim "exponent 4/3 in three dimensions" is not used as a fact: the fit decides, and the literature is used to explain the exponents found.

## 4. Study 1: the memory law of each class

**Question.** For each class of model, how do the peak resident memory and the solve time grow with the unknowns, and what are `base`, `k` and `p` of `peak = base + k N (N / 500 000)^(p - 1)`?

**Method.** `scripts/study_memory_ladder.py --run`: a ladder of square boards of 100 mm at cells from 2 to 0.25 mm (each point in its own subprocess, `lib/measure.py`; the kernel's peak from `os.wait4`; a watchdog kills a child above the cutoff). The series:

| Series | Class (provisional) | Why |
| :-- | :-- | :-- |
| FVM plain 2, 4, 6 layers | layered plain | copper everywhere: no laminate nodes, the count is layers times cells |
| FVM with vias, 4 layers | layered | the via couplings add non-zeros to the matrix |
| FVM partial copper 2, 4, 6 layers | layered laminate (few / many) | the laminate rule: nodes through the gaps next to absent copper |
| FVM outline (L shape), FVM metal block | layered | cells off the board pinned; blocks keep the earlier treatment (no laminate rule) |
| FDM plain and partial, 4 layers | layered | node-centred corners, one more row and column |
| 3D solid plain 2 and 6 layers, vias 4, partial 2, block 2 | solid3d few / many | 6 slabs against 16 or more |
| Lumped plain and partial 2 layers | lumped | dense systems per heater; the plan arrays dominate |
| Analytic plain 2, vias and heatsink 2 and 4 layers | analytic | the dense tile matrices of the local correction |

Each point records the unknowns counted by the program, the peak resident memory, the time to assemble and to solve and the largest temperature rise. A baseline run (a 20 mm board) measures the base of the interpreter.

**Criterion.** A class is accepted when (a) the fit over its points has every measured/fitted ratio within 0.85 to 1.15; (b) leaving the largest point out, the law predicts it within 10 %; (c) the exponent is in 1.0 to 1.7 (the fit is clipped and the clipping reported otherwise). The coefficient put in the program is the fit multiplied by the largest measured/fitted ratio (so the estimate is never below a measurement) and by 1.1 for the machine-to-machine spread; the margin is a decision of the maintainer (section 13).

**Not verified (and why it may fail).** Only one machine is available, so the law is not tested on other RAM sizes, operating systems or SciPy builds; the peak of the Analytic model is not a function of the unknowns but of the number of tiles with a via or a heatsink, so it is a separate law (`memory_model.analytic_bytes`, whose factor four is read from `analytic.py`, not measured); the computed-h loop repeats the solve 3 to 6 times without keeping the factors (the peak should not grow, but this is measured only by running with `h_mode = computed` on one point, not planned in the ladder: add it); the transient factor 2 (`profiles.py` calls `splu` twice) is a reading of the code.

## 5. Study 2: the cell-major numbering

**Question.** Does numbering the unknowns cell by cell (the layers of a cell next to each other) before `spsolve` save time and memory on the laminate-rule boards, and is the answer the same?

**Method.** The `fvm.Network` is built as it is, the matrix is permuted symmetrically (`lib/cell_major.py`: `K[keep][:, keep]` with the cell-major order, the dropped nodes left out as the program does) and `spsolve` is called with the same `permc_spec`. The ladder runs the three series `*_cellmajor` next to the layer-major ones; the mode `compare` solves the same small network both ways in one process and prints the largest difference of the temperatures.

**Criterion.** (a) The largest difference is below 1e-9 K on partial copper 2 and 4 layers, the outline and a plain board (the unit test `tests/test_measure_and_ordering.py` asks it on five small boards). (b) The reviewer's gain is reproduced: 637 000 unknowns, 2 layers, 21.4 s and 4.5 GB become about 12.7 s and 3.0 GB. (c) No class loses: plain boards must not be slower by more than 10 %.

**Not verified.** Why the numbering changes the ordering: the minimum-degree ordering breaks ties by the position of the column, and the thin graph has many ties; this is an explanation from [Davis2006]/[GeorgeLiu1981] to be read, not a result. The effect on the FDM and the 3D solid (whose numbering is different) is not planned; the 3D solid orders the slabs, and a cell-major order there is a separate test (add a series if the ladder shows the 3D solid is the limit). The bit-compatibility is "same linear system, same answer to the solver's round-off": with a different ordering the floating-point sums differ, so equality to the last bit is not expected and not claimed.

## 6. Study 3: the dense block of the SOR

**Question.** What does a dense inverse of a via-footprint block cost, and what limit by memory replaces `MAX_SOR_BLOCK = 5000`?

**Method.** `fvm.Network.solve_sor` inverts (`splu` of the block, then dense `solve` of the identity) a block of n unknowns, so the dense inverse takes 8 n^2 bytes plus a working copy: 16 n^2 (`memory_model.sor_block_bytes`). The study measures the peak of a SOR run on a board whose via footprints merge into a block of 2 000, 5 000, 8 000 and 12 000 unknowns (a dense via array with the cells fine enough to put several cells under the array) in its own subprocess; this series is not in the ladder file yet and must be added as `sor_block_*` when the code is used (the case builder `cases.py` has the `vias` family; the block size is set by the array and the cell).

**Criterion.** The measured peak agrees with `16 n^2` within 25 %; the rule `16 n^2 <= 25 % of the limit` then replaces the constant (400 MB at n = 5 000, 1.6 GB at 10 000 on a 16 GB machine at 70 %: 11.2 GB x 0.25 = 2.8 GB allows n up to 13 000).

**Not verified.** That the SOR with such blocks converges and is useful (that is `research/sor-with-via-couplings`); that the blocks are inverted one after another (read from the code; the factors of all blocks stay, the sum of their sizes counts).

## 7. Study 4: the unknown count the guard uses

**Question.** Is the count the guard reads the count the solver builds?

**Method.** For every point of the ladder the parent counts the unknowns before the run (`fvm.unknowns`, `fdm.unknowns`, `solid3d.unknowns`) and the child counts them from the assembled network; the two must be equal. `fvm.unknowns` counts the laminate nodes of the rule from the zone fill and the cover, which is an independent calculation from the network's own ladder, so the check has teeth.

**Criterion.** Equal on every point (zero tolerance). For the Lumped and the Analytic the count is the plan grid, which is not what they factor; the guard for them uses the tile count (Analytic) and the plan arrays (Lumped), see section 9.

**Not verified.** Boards with blocks and the FDM in the ragged form beyond the ladder's families; boards from a Gerber import (many more cells with partial copper than the ladder's).

## 8. Study 5: the physical memory

**Question.** Does `memory_model.ram_bytes()` give the right number on macOS, Linux and Windows without a new dependency?

**Method.** The order is `os.sysconf` (`SC_PHYS_PAGES` times `SC_PAGE_SIZE`; present on Linux and macOS), `sysctl -n hw.memsize` on macOS, `/proc/meminfo` on Linux, `GlobalMemoryStatusEx` through `ctypes` on Windows; a cgroup limit (v2 `memory.max`, v1 `memory.limit_in_bytes`) lowers it inside a container. `psutil` would give the same and also the **available** memory; it is not adopted because it is a new dependency for one number (licence BSD-3-Clause, to be checked in the README table if it is ever added). The unit test asks a plausible positive value; on the maintainer's machine the value is compared with `sysctl hw.memsize` and with the System Information by hand.

**Not verified.** Windows and the container paths were written from the documentation of the interfaces and have not been run (only macOS is available). The amount of memory **free now** (other programs running) is not read: the guard uses the installed memory and the user's fraction, which is what the maintainer asked for; the free memory would need `vm_stat` / `/proc/meminfo MemAvailable` / the Windows call, and is listed as an option in `INTEGRATION.md`.

## 9. Study 6: the Lumped, the Analytic and the transient

The Lumped solves small dense systems per heater and holds arrays of the plan grid: its memory is expected to be linear in the cells and small. The Analytic holds dense matrices of (tiles x layers)^2 (`analytic.py`: `Gm`, `G`, `C` and the system that is inverted): its memory is quadratic in the tiles that carry a via, a heatsink or a block. The ladder has the series, and the fit of `analytic_bytes` takes the tile count from the child (to be added to `_measure_child.py`: the tile count of `analytic` is internal; the first version of the child records the result and the peak, the tile count is derived from the board: via tiles of 0.25 to 1 mm). The transient (`profiles.py`, steady plus step LU) is measured by one extra point per class with a power profile; the factor 2 of `TRANSIENT_FACTOR` is checked against it.

**Not verified.** The quadratic law for the Analytic, the tile count formula and the transient factor: nothing is measured. These are the least certain parts of the estimator and are listed first in the risks of `INTEGRATION.md`.

## 10. Study 7: the ceiling of the 3D solid

`MAX_CELLS = 250 000` becomes the largest N for which the estimate of the 3D classes is within the limit, with an absolute ceiling (`ABSOLUTE_CEILING_3D = 2 000 000`, a proposal) so that a machine with 256 GB is not asked for a 2 million unknown direct solve whose time is long. The ladder gives the 3D time law; the criterion is a time that the interface can announce ("about X s"); whether to refuse on time as well as memory is a decision (section 13). With the provisional coefficients, a 16 GB machine at 70 % (11.2 GB) allows about 1.3 million unknowns for a plain 6-slab board and about 600 000 for the example board (solving the provisional law for N by hand; the fixed limit today is 250 000); the number is a consequence of the provisional coefficients and is to be replaced by the fit.

## 11. Study 8: the guard in the application

A stress scenario for `tests/test_gui_stress.py` (to be written with the feature, specification in `INTEGRATION.md`): simulated RAMs of 8, 16 and 64 GB (the detector is patched), the 502 mm board of the monkey seed 20261016 refused in under 60 s without allocating more than a few hundred MB, the Auto cell suggestion returns a cell the verdict accepts, and a failed RAM read falls back to the fixed ceiling.

## 12. How to run it later (after the 2.4.5 release; a quiet machine)

All commands from the repository root (the study needs the program's environment, `.venv`):

```sh
.venv/bin/python -m pytest -q research/memory-guard/tests               # the estimator, the wrapper (one tiny subprocess), the ordering on small boards: seconds
.venv/bin/python research/memory-guard/scripts/study_memory_ladder.py --plan              # list the points with their provisional sizes; builds the problems, solves nothing
.venv/bin/python research/memory-guard/scripts/study_memory_ladder.py --run --quick       # the coarse half: minutes
.venv/bin/python research/memory-guard/scripts/study_memory_ladder.py --run               # the whole ladder, resumable (out/ladder.jsonl); about an hour
.venv/bin/python research/memory-guard/scripts/study_memory_ladder.py --fit               # coefficients, exponents, ratios, ordering check; writes out/fit.json
.venv/bin/python research/memory-guard/scripts/make_diagrams.py                           # figures 01 to 03
.venv/bin/python research/memory-guard/scripts/make_figures.py                            # figures 04 and 05 (needs the two files above)
```

Safety of the study: a point is skipped when 1.5 times its provisional estimate exceeds the cutoff (60 % of the physical memory, at most 10 GB; `--cutoff-gb` changes it), a child above the cutoff is killed by the watchdog (the machine does not page), a point has a timeout (900 s), a series stops at its first skipped or killed point, and the results are appended so that an interruption loses only the point that was running. Close the other heavy programs first: the peak resident size of a child does not depend on them, the time does.

Things to look at first when it runs: (1) that `peak_bytes` of the baseline is a few hundred MB, (2) that the unknown counts of the parent and the child agree (section 7), (3) that `ru_maxrss` and the sampled peak agree within 20 %, (4) the exponent of each class against section 2.

## 13. Doubts and decisions left to the maintainer

1. **Margin on the estimate**: the largest measured/fitted ratio times 1.1 (proposed). A tighter margin refuses less and risks the machine; a looser one refuses boards that would run.
2. **Slow mark**: 35 % of the RAM is a placeholder; it should be set from the time law (say, above 60 s predicted) as well as the memory.
3. **Installed against available memory**: the guard reads the installed memory (as asked). A busy machine can still page below the limit; reading the free memory would make the verdict depend on what else is running.
4. **Time as a reason to refuse**: not proposed; only a warning with the predicted time.
5. **3D absolute ceiling** of 2 million unknowns: a proposal.
6. **psutil**: not adopted (one number does not justify a dependency).
7. **Cell-major numbering in the program**: adopt only if the ladder reproduces the gain and the check of section 5 passes; it changes no result beyond the solver's round-off.

## 14. What was read and what was not verified

* **Read in full:** the code of `pcbthermal/fvm.py` (Network, `solve_steady`, `solve_sor`, `unknowns`, `MAX_SOR_BLOCK`), `fdm.py` and `solid3d.py` (the count functions, `MAX_CELLS`, `size_limit`, `check_size`), `analytic.py` (the dense local correction), `api.py` (`SolverOptions`, `suggest_cell_mm`, the model dispatch), `gui/panels.py` (the note on slowness), the `solver` section of `data/defaults.json`, `research/solid3d-verification/docs/for-the-project-documents.md` (the table of section 2) and the Planned items of `docs/versions.md` on the memory guard, the laminate nodes and the SOR guard.
* **Seen as a quoted number only:** the fix/laminate-nodes figures (4.5 GB, 7.6 GB, 12.7 s, 3.0 GB, 50 s) come from the task description and `docs/versions.md`, not from a log re-opened here.
* **Literature:** none of [George1973], [Davis2006], [LiSuperLU2005], [GeorgeLiu1981] was opened; the statements about the 4/3 exponent and the tie-breaking of the minimum-degree ordering are from memory and are used only as the hypothesis the fit tests. The statement that `ru_maxrss` is in bytes on macOS and kilobytes on Linux and that `wait4` returns the child's own usage is from memory of the documentation; the wrapper test checks the first plausibly (a peak above 50 MB), not exactly.
* **Not run:** the tests, the ladder, the fit, the figures (the machine was busy). The scripts were compiled only. A defect in them is likely to show up on the first run; the first run is a `--plan` and the tests, in that order.
* **Not verified at all:** Windows and container paths of the RAM detector; the laws of the Analytic, the Lumped and the transient; behaviour on a machine other than the maintainer's 16 GB Mac; the computed-h loop's effect on the peak; the cell-major gain beyond the reviewer's one number.
