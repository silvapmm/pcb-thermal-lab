# Reviewer's answers to the open decisions: the FEM window, the frozen FEM records, the 2.9.0 plan, and speed

**Standing rule** (maintainer): every open decision of his is answered by a reviewer and he goes with the answer. This file gives the answers for the decisions of `BRANCH5_PLAN.md` section 10 (branch `docs/fem-gui-plan`, commit `fbf4a1fb`), of `REVIEW_BRANCH4.md` 6 and `REVIEW_SURFACE_ALWAYS.md` 5 (on `feature/fem-model` and `feature/surface-always-both`), of `releases/2.9.0/PLAN.md` section 6 (branch `docs/plan-2-9-0`), and the maintainer's question about faster solves. Per decision: the options, the evidence checked, the **decision in one line**, the reason, what it changes.

**Tree of the evidence**: the code of `tmp/merge-fem-surface` at `fd007cd1` (`feature/fem-model` and `feature/surface-always-both` merged; not yet `development`), Python 3.13, NumPy 2.5.4 on Apple Accelerate, SciPy 1.18.1, pyamg 5.4.1, on this machine (macOS arm64, 16 GB). Every number below was printed by a scratch script run on that tree (not committed: the scripts read the program and change nothing; their content is described where the number is used). No program file was edited.

## A. The window branch 5 (`feature/fem-gui`)

### A1. The FEM checkbox without pyamg

* **Options**: (a) never greyed; the reason appears in the verdict row and the live check; (b) greyed when `femcore.available()` is false (DESIGN decision 2 and 5.8).
* **Evidence**: `femcore.py` 29 `FEM_DIRECT_MAX = 30000`; `femcore.solve` uses SuperLU up to that size and imports pyamg only above it (`_import_pyamg`, raising `FemUnavailable` before any heavy work); `api.SKIPPABLE_MODELS = ("solid3d", "fem")` leaves a FEM that raises out of a run with a warning beside the other models; `requirements.txt` 7 has `pyamg>=5.4`, so a normal install has it and (b) would only ever affect a platform without a pyamg wheel or a hand-made environment. The plain 60 x 40 mm four-layer board at 2 mm, the one-layer reference boards and the 20 mm drawn-copper boards are below 30 000 unknowns (DESIGN 8.4 counts), so they solve without pyamg.
* **Decision: (a), never greyed.**
* **Reason**: greying forbids cases that work and are the ones a user without pyamg most likely runs (small boards); the API already handles the large case cleanly. DESIGN's 'greyed' was written when the direct path was not planned to stay.
* **Changes**: the verdict row of BRANCH5_PLAN 3.1 ('needs the package pyamg: it will be left out'), DESIGN 5.8 and decision 2 to be marked superseded by this answer; GUI_TEST_CHECKLIST F item 4 already expects (a).

### A2. The wording of the FEM checkbox tooltip

* **Options**: DESIGN 5.8's 'within about 0.2 % of the FVM and the 3D solid ... reads the surface of thick copper and blocks'; or the numbers measured in the review of branch 4.
* **Evidence**: `REVIEW_BRANCH4.md` 3: FEM 34.129 against FVM 34.270 K (60 x 40 mm, 4 layers, 2 mm, -0.41 %) and 54.284 against 54.762 K (40 x 30 mm, -0.87 %); the FEM converges from below and the finite volumes from above to the same value (55.12 K), so most of the gap is the FVM's error at that cell. The 0.2 % of DESIGN 1.2 compares the FEM point maximum with cell values of the other models on one board (29.306 / 29.253 K): a different read-out. A metal block has no FEM surface (REVIEW_BRANCH4 4, item 3). 'Reads the surface ... of blocks' is false.
* **Decision: the measured numbers ('0.4 to 0.9 % below the FVM at a 2 mm cell on plain boards, mostly the FVM's own error'), no block surface; short tooltip, the details in the guide.**
* **Reason**: the tooltip must quote a number that a study prints, with its read-out and cell (CLAUDE.md 11); the plan's draft (BRANCH5_PLAN 3.5) is right in content but three times the length of the 3D solid's tooltip.
* **Changes**: the tooltip has at most four sentences: what it is (3D hexahedra, steady only), the agreement with its cell and the direction, 'surface of thick copper resolved, a metal block reported as its mean', 'slower; left out above the memory limit or when a large mesh needs pyamg'. The Muzychka case and the convergence go to the guide paragraph 'Finite elements (FEM), comparison'. DESIGN 5.8 text superseded.

### A3. The two FEM mesh options in Preferences

* **Options**: in the Solver page of Preferences (DESIGN 5.8) or only in the Settings box of the panel (precedent of the laminate numbers).
* **Evidence**: `gui/preferences.py` has no laminate control (grep: 0 matches); `MODELS` (line 94) is the only model setting there. REVIEW_BRANCH4 3: six or twelve elements across a gap give the same number to 0.1 mK; refinement 1 to 4 moves the case-2 node by less than 0.01 K. The defaults are enough.
* **Decision: not in Preferences.**
* **Reason**: two numbers that almost never need a change do not deserve a machine-wide default, and a default that differs between machines would make the same project give different FEM numbers. Only the model tick goes to `Preferences.MODELS`.
* **Changes**: DESIGN 5.8 'the Solver page gains the two FEM options' superseded.

### A4. The hottest node (`T_point`) in the window

* **Options**: report and a tooltip only; or also Layer-box entries 'Point (top/bottom)'.
* **Evidence**: `api.py` 394 already prints 'hottest node ... degC' in the report text, which the Summary box of the Results shows; `extras["t_max_point"]` and `arrays["T_point"]` are filled by `fem.py` 255. A third family of Layer entries would exist for one model only.
* **Decision: report and tooltip only in 2.8.0.**
* **Reason**: the point is a read-out of one model; as a map it would invite comparing a node maximum with the cell means of the other models (the error DESIGN 1.2 made with its 0.2 %). The 2.9.0 item e3 (hotspot map `T_point`) can revisit it with the comparison views.
* **Changes**: none to the plan; the Components-table tooltip sentence of BRANCH5_PLAN 3.4 (2) stays.

### A5. Progress inside the FEM

* **Options**: only the message 'Solving FEM, this can take minutes'; or real stages (mesh, assembly, solve) as DESIGN 5.5 promised.
* **Evidence** (profile of section D): on the example board at 1 mm (275 724 unknowns, 15.5 s) the mesh is 0.5 s, the assembly 3.5 s and the solve 10.9 s; three stage messages would show one moving step and then stand still for 70 % of the time. Measured defect on the way: `api.py` 1157 writes `progress(f"Solving {name}", ...)` with the model **key**, so the window will show 'Solving fem' (and today 'Solving solid3d').
* **Decision: message only in 2.8.0, with the label fixed ('Solving FEM'); real progress (CG iteration count against an expected count) in 2.9.0 with the transient.**
* **Reason**: the stages give no useful information; useful progress needs the iteration callback of `spla.cg`, which belongs with the transient's own progress (one design for both).
* **Changes**: branch 5 makes `api.simulate` use `results.MODEL_LABELS` (or `tips.model_label`) in the progress text and adds 'the FEM can take minutes on a large board' to the message when `fem` is ticked; a test on the text. DESIGN 5.5 marked 'stages not built; 2.9.0'.

### A6. Surface CSV from the window, and '(column)' on the zone and hotspot tables

* **Options**: a File-menu item 'Export surface read-out (CSV)...' in branch 5 (about 0.5 day) or 2.9.0 (item e3); the '(column)' tag now or later.
* **Evidence**: `main_window.export_results` calls `sim.save(...)` without `surface_files`; `cli.py run --surface-files` writes them (REVIEW_SURFACE_ALWAYS 5.1). `gui/results_view.py` 568 and 569: zone table 'Mean °C', 'Max °C', 'Min °C'; hotspot table 'Tmax °C', without a read-out name, against the standing rule 'every number the user sees carries the name of its read-out' (CLAUDE.md 11). The part table already says '(column)' (line 706).
* **Decision: the CSV menu item in 2.9.0 (e3); the '(column)' tags NOW, in branch 5.**
* **Reason**: the export is a new feature with a GUI path, a file format and tests, and the command line covers the need; the tags are a breach of a standing rule that ships in 2.8.0 otherwise, and they are text only (the header form 'Mean °C\n(column)' of the part table).
* **Changes**: branch 5 edits the two headers and the tests that read them (`test_results_views.py`; check the column widths at 900 x 700); the e3 row of the 2.9.0 plan loses the tags.

### A7. The FEM in the stress `ALL_MODELS`

* **Options**: add `"fem"` to `ALL_MODELS` of `tests/test_gui_stress.py` (every walking test runs it) or dedicated scenarios.
* **Evidence**: `ALL_MODELS` is used at lines 204, 320, 383, 430, 441, 511, 608 and 625; two of those (`test_run_twice_and_edit_while_running_and_close` 441, `test_overlapping_background_jobs_wait_for_each_other` 625) run the example board at **1 mm**, where the FEM has 275 724 unknowns, takes 15.5 s and peaks at 1.98 GB (section D); the random monkey (608) samples from it. Each of those would add 15 s and 2 GB to a battery that already runs 47 minutes on a 16 GB machine with other jobs.
* **Decision: dedicated scenarios, not `ALL_MODELS`.**
* **Reason**: the cost is in the 1 mm tests, where the FEM adds memory, not coverage; the FEM paths of the window (combo, card, tabs, refusal, cancel) are covered by `tests/test_fem_gui.py` and by adding `("fem",)` and `("fvm", "fem")` to the model loop of line 320 (2 mm or coarser), plus a FEM tick in the random monkey with the cell forced to at least 2 mm.
* **Changes**: BRANCH5_PLAN 4 'edits' row: `ALL_MODELS` unchanged; the loop of line 320 gains the two tuples; the monkey gets a separate model list `ALL_MODELS + ("fem",)` used only when the cell is 2 mm or more. CLAUDE.md 6 ('a new model adds its stress scenarios') is met.

### A8. The `except ValueError` of `_update_cells` that blocks Run for every model

* **Options**: confirm the plan's fix (catch per model) or another.
* **Evidence** (measured on `fd007cd1` with the example board given a slanted side): `memory.check(problem, ("fvm", "fem"), 2.0, refuse="return")` does **not** raise: `memory.py` 857 to 861 already turns the `femmesh` `ValueError` into a `Verdict("fem", 0, 0.0, ..., "refuse", ..., message=reason)`; `api.simulate` with `("fvm", "fem")` runs the FVM and leaves the FEM out with the warning 'cannot be built for this board and will be left out'. So the plan's diagnosis is wrong in its cause: what would block Run is **`panels.py` 1748**, `v.verdict == "refuse" and (v.model != "solid3d" or ...)`, which treats a FEM refusal as fatal; and the row text would read **'FEM: 0 unknowns, about 0.0 GB of x GB; above the memory limit, it will not run'**, a false reason (the mesh, not the memory, is refused). The `except ValueError` itself is still needed for the case it was written for (imported copper masks that no longer fit the board), which concerns every model.
* **Decision: fix the skip rule and the text, keep the global catch.**
* **Reason**: the skip rule must be `v.model not in api.SKIPPABLE_MODELS or len(self.doc.options.models) == 1` (one tuple for the window and the API); a refusal with 0 unknowns (a mesh that cannot be built) must print its `v.message` ('FEM: cannot be built: the FEM needs a rectangular ...; it will be left out') instead of the memory sentence. A per-model try is not needed for the FEM (memory already returns a verdict) and would be wrong for the copper case.
* **Changes**: BRANCH5_PLAN 3.1 and risk 2 corrected by this answer; test `test_fem_refusals_do_not_stop_the_other_models` must assert the row text names the mesh reason and does not say '0 unknowns'. Also make `verdicts()` and `_auto_cell` use one constant `GUARDED_MODELS` including `fem` and pass `fem_params=self.doc.options.fem_params()` (the keyword of `memory.check`, line 796).

## B. Should the frozen FEM records hold the surface read-out?

* **Options**: yes or no; now (in the pending file of the FEM records, frozen with 2.8.0) or in 2.9.0 (e4).
* **Evidence**: `tests/regression/data/pending/fem-records.json` holds 29 `new` records whose metrics are the column (`t_max`, `layer_mean`, parts, `t_sum`...), no surface and no point; `regress_harness.run_one` already stores `extras` (which carry `t_max_surface_top/bottom` and `t_max_point`), but `regress_classify.metrics_of` does not flatten them, and `_blocks` records metal blocks for FVM and FDM only. `regress_frozen.compare` compares the union of metric names, so a metric added to a record that is already frozen alarms as 'frozen None, now x' until the next refreeze: adding it to the FEM records **before** they are frozen costs nothing; afterwards it costs a refreeze item.
* **Decision: yes, now, inside the existing `fem-records.json` (regenerated), before the 2.8.0 refreeze; the FVM and FDM surface too at the same refreeze.**
* **Reason**: the surface is the one thing the FEM adds (resolved thick copper); a later change of it (the face flux, the one-layer bottom face, both corrected once in review) would today pass the frozen numbers silently. The FVM and FDM surface is shown to every user since `surface-always-both` and is equally unguarded.
* **Changes**: on `release/regression-harness` (harness side, the program untouched): `metrics_of` gains `surface:top:t_max`, `surface:bottom:t_max`, the part surface maximum, and `point:t_max` for the FEM, metric group 'temperature'; `_blocks` accepts `fem`; `make_pending.py` rewrites `fem-records.json` (still one record in one file); the 2.8.0 `expected_shifts` table lists the new surface metrics of FVM and FDM records as additions (not shifts). One review of the harness change before the refreeze.

## C. The 2.9.0 plan (`releases/2.9.0/PLAN.md` section 6)

| # | Decision | Answer | Reason (evidence) |
| :-- | :-- | :-- | :-- |
| 1 | Campaign before number-moving corrections | **Yes, campaign first** | A correction in the middle voids the tables; the campaign then gives each correction its measured impact. Exception kept: a clear defect found by `drawn-ell-fvm-fdm`. |
| 2 | Convection under the source: stated limit unless a board moves > 0.5 % of its rise | **Yes, stated limit; the study can be replaced by the closed form** | REVIEW_SURFACE_ALWAYS 3: the film error is a fraction `h t/(2k)` of the source flux on a face that carries both a source and a film: 5e-7 on 35 um at 10 W/m2K, 1e-3 on 2 mm of copper at 400 W/m2K. Reaching 0.5 % needs `h t / (2k) > 5e-3`, i.e. more than 4 mm of copper at 400 W/m2K under a source with the film on the same face: no board of the harness (case 2 has its film on the other face). The research branch shrinks to a check of that bound on the harness and a sentence in the thick-plate warning. The plan's '0.17 K in a 1 mm case' is that 1 mm plate of 50 W/mK (not copper). |
| 3a | Documentation simplification before features | **Yes, before** | They share every document with the features; in series it is cheaper than merging both. |
| 3b | Documentation-only branches run only the documentation tests | **Yes, with the exact wording below; not 'one battery per three branches'** | See C.1. |
| 4 | Lumped surface as an upper bound | **As the plan: only if never below the FEM surface on the six plates and the harness** | An 'upper bound' that is not is the error pattern the audit found. |
| 5 | Headline of the transient FEM and the Difference view: the column | **Yes, column** | Like for like with the other models (the steady decision). |
| 6 | Thermal-capacity inventory with the transient | **Yes** | Small, visible only in the transient. |
| 7 | Measured peak memory in the Results summary | **Yes, only with `fix/memory-law-measured` and if users are near the limit** | As the plan. |
| 8 | Outline projection, if both methods are poor | **Keep the refusal, drop branch d** | A worse number than the FVM's cut cells must not ship. |
| 9 | FEM on imported copper: warn or refuse | **Warn, with the measured number** | As the plan; refuse only on a stated failure. |
| 10 | Smaller 2.9.0 if time is short | **Yes: a, b, c, e1 to e4 (now without the '(column)' tags of A6 and with e4 done in 2.8.0, B); d and e5 to e8 may slip** | The claim 'every model against the FEM' needs only those. |
| 11 | `docs/validation-history.md` permanent | **Yes** | Already decided for 2.8.0. |

**Correction of the plan**: e4 (FEM records with the surface) moves to 2.8.0 (B); the '(column)' tags of e3 move to 2.8.0 (A6); the first-step check of `drawn_ell` stays (the plan itself notes that `validation.md` 51 gives -0.0 % there).

### C.1 A safe exception for documentation-only branches

The whole-battery rule (CLAUDE.md 6 'Before every merge') protects against a change that breaks a program test. A change to Markdown cannot break one, **except** where a test reads the documents. On `development` the tests that open documentation files are `test_docs.py`, `test_license_header.py`, `test_version.py` (README, CHANGELOG), `test_third_party_text.py`, `test_no_secrets.py`, `test_no_fabricator_names.py` and `test_help.py` (the guide), plus `research/*/tests` that read their own folder (grep of `read_text|open(` over `tests/`; many other tests only name a document in a docstring). Wording proposed for CLAUDE.md 6 (the maintainer's text to adopt; not edited here):

> **Documentation-only branches** (`docs/<topic>`) may be merged after the documentation tests instead of the whole battery when ALL of these hold: (1) `git diff --name-only development...HEAD` lists only `*.md` files and files under `docs/images/` or `research/*/figures/` that the branch's own figure scripts made, and nothing under `pcbthermal/` (the guide is HTML in the program), `tests/`, `examples/`, `tools/`, `releases/**/scripts`, `research/**/scripts`, `research/**/lib` or any configuration file; (2) the last whole battery on `development` is green and nothing that is not documentation-only was merged after it; (3) `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_docs.py tests/test_license_header.py tests/test_version.py tests/test_third_party_text.py tests/test_no_secrets.py tests/test_no_fabricator_names.py tests/test_help.py`, every `tests/` file that names a changed file (`git grep -l <basename> tests`) and the `research/<topic>/tests` of a changed research folder pass; (4) the report says it used this exception and lists what ran. Any other branch, every release merge and `development` into `main` keep the whole battery.

This keeps the rule's purpose (no untested code reaches `development`) and is checkable by a command; 'one battery per three docs branches' is not, because it lets a docs branch be merged on top of a code merge that was never run.

## D. Can the assembly and the solves be made faster (SIMD, GPU), on every platform?

### D.1 The profile

cProfile of `api.simulate` with one model, one fresh process per run, one run at a time under the heavy-job lock (peak below 2 GB). Boards of the regression harness: `example_board` (4 layers, vias, two parts, a heatsink), `plate_vias` (2 layers, 16 vias), `finned_block` (a 3 mm block with fins), at the finest cell whose FEM estimate is below 3 GB.

| Run | Unknowns | Wall | Peak RSS | Where the time goes |
| :-- | --: | --: | --: | :-- |
| FEM `example_board` 1 mm | 275 724 | 15.5 s | 1.98 GB | CG + AMG 10.9 s (70 %; of it pyamg Gauss-Seidel smoothing 6.7 s, sparse mat-vec 4.0 s; **331 CG iterations** at `rtol` 1e-12), assembly 3.5 s (23 %: batched `einsum` 2.0 s, `linalg.det` 1.1 s, `linalg.inv` 0.5 s, of which `element_volumes` twice 0.9 s and `validate` 0.5 s recompute the same Jacobians), mesh 0.5 s, AMG setup 0.34 s |
| FEM `plate_vias` 0.5 mm | 212 724 | 7.7 s | 1.50 GB | CG 4.3 s, assembly about 2.5 s (same split) |
| FEM `finned_block` 0.5 mm | 215 172 | 9.4 s | 1.53 GB | CG 5.8 s, assembly about 2.5 s |
| FVM `example_board` 0.5 mm | 151 192 | 1.40 s | 0.67 GB | SuperLU factorisation (`gstrf`) 1.23 s (88 %) |
| FVM `example_board` 0.35 mm | 309 004 | 3.97 s | 1.64 GB | SuperLU factorisation 3.40 s (86 %) |
| FVM `plate_vias` 0.25 mm | 140 148 | 0.75 s | 0.51 GB | factorisation 0.60 s |
| FVM `finned_block` 0.25 mm | 115 200 | 0.45 s | 0.35 GB | factorisation 0.37 s |
| Live check, `example_board` 0.5 mm, FVM + FDM + FEM | | 0.10 s | | polygon tests and the FEM plan layout; not a cost |

**Reading**: no Python loop is a cost anywhere; the time is inside compiled serial code (SuperLU, pyamg's C++ smoother, SciPy's sparse mat-vec) and in batched NumPy on 3 x 3 matrices. The BLAS (Accelerate here, OpenBLAS on Windows and Linux) is almost unused: none of these kernels is a dense matrix product, so more BLAS threads give nothing.

### D.2 Solver settings tried on the captured FEM matrix

The FEM matrix of `example_board` at 1 mm (275 724 unknowns, 7.1 million non-zeros) and of `finned_block` at 0.5 mm (215 172) were captured from `femcore.solve` and solved again with other settings (one process per board; times include the load of a second job, so compare within a block; 'max dT' is the largest difference from the program's solution over every node).

| Setting (`pyamg.smoothed_aggregation_solver`, CG) | example 1 mm: setup + CG, iterations | finned 0.5 mm | max dT | true relative residual |
| :-- | :-- | :-- | :-- | :-- |
| program: strength symmetric theta 0, V-cycle, `rtol` 1e-12 | 0.3 + 10.9 s, 331 (second run 12.8 s) | 0.26 + 5.9 s, 231 | reference | **2.2e-10** (1.2e-10) |
| same, `rtol` 1e-10 | 0.3 + 9.3 s, 280 (10.2 s) | 0.23 + 5.0 s, 194 | 1e-10 K | 2.3e-10 |
| same, `rtol` 1e-9 | 0.3 + 8.4 s, 254 | 0.24 + 4.8 s, 179 | 1.4e-9 K | 9.5e-10 |
| theta 0.25 | 2.2 + 77 s, 258 | 0.9 + 22.6 s, 172 | 4e-11 K | 1.8e-10 |
| symmetric Gauss-Seidel smoother | 0.4 + 11.9 s, 331 | 0.28 + 6.5 s, 231 | 1e-10 K | 2.2e-10 |
| prolongation smoothing 'energy', `rtol` 1e-10 | 0.5 + 9.5 s, 275 | not run | 8e-11 K | 2.2e-10 |
| no prolongation smoothing, `rtol` 1e-10 | 0.07 + 15.5 s, 487 | not run | 2e-10 K | 2.8e-10 |
| strength 'evolution' (default) | **37 + 14.5 s, 34** | 8.7 + 5.8 s, 41 | 1e-10 K | 1e-10 |
| strength 'evolution' k 2, epsilon 4 (with or without candidate improvement) | 40 to 45 + 11.5 s, 28 | not run | 1e-10 K | 1.2e-10 |
| strength 'algebraic_distance' / 'affinity' | 5.5 + 45 s / 3.7 + 33 s, 265 / 257 | not run | 1.4e-10 K | 2.2e-10 |
| float32 matrix, `rtol` 1e-6 | 6.3 s | 3.5 s | **0.82 K / 0.21 K** | |

**Readings**: (1) the program asks for `rtol` 1e-12 but the true residual it reaches is 1e-10 to 2e-10 (the recursive residual of CG drifts below the true one, the effect that the restart of REVIEW_BRANCH4 4.2 handles): the last 50 iterations buy nothing; 1e-10 gives the same true residual and a difference of 1e-10 K, 15 to 20 % less solve time. (2) The preconditioner is weak on this matrix (300 iterations where smoothed aggregation usually needs 20 to 50): a strength measure that sees the layered anisotropy (evolution) cuts the iterations tenfold, but its setup costs more than it saves; the cure is an AMG built for thin layers (semi-coarsening or line smoothing through the thickness), which is an investigation, not a setting. (3) float32 loses 0.2 to 0.8 K: refused.

**The FVM matrix** (`example_board`): SuperLU with the program's ordering 1.07 s at 151 192 unknowns and 3.43 s at 309 004; COLAMD and MMD_ATA orderings are 2 to 3 times slower (the program's choice is the right one); CG with the same pyamg preconditioner 0.78 s (55 iterations) and 2.38 s (77 iterations) at `rtol` 1e-10, 2.6e-10 / 3.3e-10 K from the direct solution: 1.4 times faster at these sizes and, because the factor's fill grows faster than the unknowns, more at finer cells.

**The assembly**, measured on one chunk of 20 000 random hexahedra (the program's chunk size): the batched `np.linalg.det` + `np.linalg.inv` of the 3 x 3 Jacobians take 9.1 ms, the closed-form cofactor formulas 0.82 ms (same result to 3e-15 and 5e-13); `einsum("eai,ei,ebi->eab")` for the element matrix 10.1 ms, the same product as `matmul` 2.2 ms (same to 4e-16). With the three Jacobian passes (`validate`, `element_volumes` twice, `_assemble_elements`) computed once, the 3.5 s of assembly of the example board would be about 1 s (an estimate from these parts, not a measured run).

### D.3 The options

| Option | Expected gain (measured where said) | Effort | Platform risk | Install risk | Recommendation |
| :-- | :-- | :-- | :-- | :-- | :-- |
| FEM CG `rtol` 1e-12 to 1e-10 (true residual unchanged) | 15 to 20 % of the FEM solve, measured; 1e-10 K | 1 line + a test of the true residual | none | none | **2.8.0, in a `fix/` branch** with the frozen FEM records re-made (they are still pending, so nothing frozen moves) |
| FEM assembly: closed-form 3 x 3 det/inv, `matmul` for the element matrix, Jacobians computed once | 2.5 s of 15.5 s on the example board (estimate from measured parts); about 15 % | S (half a day + tests) | none (plain NumPy) | none | **2.8.0 or 2.9.0**, same `fix/` branch as the line above if it goes in 2.8.0; numbers move by about 1e-12 K |
| Faster stages of a run in their own process (several models at once) | wall = slowest model instead of the sum; FEM-dominated runs gain 10 % or less, memory adds up | M | low | none | **do not** (memory on a 16 GB machine is the binding limit) |
| FVM direct to CG + pyamg above a size (pyamg is already a dependency) | 1.4 times at 150 000 to 300 000 unknowns (measured), more at finer cells; less memory | M (a threshold, a fall-back, the frozen numbers at 1e-10 K) | none | none (already installed) | **2.9.0 investigation** (`research/fvm-amg-solve`), with the memory law |
| AMG for thin layers (semi-coarsening, line smoother through the thickness) for the FEM | iterations 300 to about 30 (the evolution measure shows the potential); the solve 2 to 5 times faster, if the setup stays cheap | L | none | none | **2.9.0 investigation**, after the transient (it uses the same solver) |
| More BLAS or OpenMP threads (Accelerate, OpenBLAS) | about 0: the hot kernels are sparse and serial | none | none | none | **do not** |
| float32 | 1.7 times, but 0.2 to 0.8 K error (measured) | S | none | none | **do not** |
| numba or Cython for the assembly | the closed-form NumPy gives most of it; the solve (70 %) is already compiled | M | numba lags new Python releases; Cython needs a compiler per platform or wheels to build | numba plus llvmlite add about 100 MB; Cython makes the project a compiled package | **do not** |
| GPU: CuPy (CUDA), Metal/MPS, OpenCL | large for the solve on NVIDIA only | L | CUDA NVIDIA only, Metal macOS only, OpenCL poor for sparse | heavy (drivers, toolkits) | **do not** (not multi-platform) |
| UMFPACK (scikit-umfpack), CHOLMOD (scikit-sparse) | 2 to 5 times the factorisation (typical, not measured here) | S | Windows wheels missing or fragile | needs SuiteSparse installed outside pip on some platforms; UMFPACK and CHOLMOD's supernodal module are GPL (CLAUDE.md 5) | **do not** |
| Apple Accelerate sparse solvers | fast on macOS | M | macOS only, no SciPy binding | a binding to write and build | **do not** |
| PyPardiso (Intel MKL) | 3 to 10 times the factorisation (typical) | S | x86 only: no macOS arm64 | MKL is large | **do not** |
| Factor reuse (`lu_factor`, `factor_reuse`), already in the FVM transient and the power-profile runner | already in place | | | | keep |
| The live check | 0.10 s on the example board at 0.5 mm with three models | | | | nothing to do |

### D.4 Answer

**No to special instructions and the GPU; yes to three cheap changes that need no new dependency.**

* SIMD (AVX, NEON) is already used where it can be: NumPy, SciPy and pyamg are compiled with it for each platform's wheels, and the time is in those compiled routines (the smoother, the sparse product, the SuperLU factorisation). Writing our own SIMD would mean a compiled extension per platform, which breaks the 'pure Python + wheels' installation for a gain that the profile does not show. The GPU has no route that works on macOS arm64 and Intel, Windows and Linux at once.
* The profile shows where the real gains are: the FEM solve is 70 % of a FEM run because its preconditioner needs 300 iterations; the assembly is 23 % and is slow only because of 3 x 3 linear algebra done the general way; the FVM is 86 to 88 % SuperLU factorisation.
* **First cheap wins**: (1) FEM `rtol` 1e-10 instead of 1e-12, measured 15 to 20 % of the solve, no change in the true residual; (2) closed-form Jacobians computed once and `matmul` in the FEM assembly, about 2.5 s of 15.5 s on the example board at 1 mm; together about a third off a FEM run (estimate from the measured parts). Both in a small `fix/fem-solve-speed` branch, with the pending FEM records re-made (they move by about 1e-10 K). (3) For 2.9.0, two investigations with pyamg, already a dependency: CG + AMG for the large FVM (1.4 times at 300 000 unknowns, more at finer cells, less memory) and an AMG suited to thin layers for the FEM (the evolution measure cuts the iterations from 331 to 28, showing that the solve can be several times faster once the setup is cheap).

## E. What was not verified

* The window code of branch 5 does not exist yet; A8 was measured on the core calls the panel makes (`memory.check`, `api.simulate`), not in a running panel.
* The profile is of one machine (Apple M-series, Accelerate). On Windows and Linux the kernels are the same compiled code (SuperLU, pyamg, SciPy sparse), so the split should hold; absolute times not measured there.
* The FVM transient (`factor_reuse`), the FDM and the 3D solid were not profiled; the 3D solid uses `spsolve` with the same ordering and should look like the FVM.
* The '0.17 K' convection figure was not re-run; C2 rests on its closed form in `REVIEW_SURFACE_ALWAYS.md` 3.
