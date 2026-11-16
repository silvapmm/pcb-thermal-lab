# Review of `fix/fem-solve-speed` (FEM speed and the surface in the frozen records)

**Verdict: GO** for the merge into `development`, with the corrections of section 3 (made on the branch by the review). Nothing found moves a number of the program beyond 1e-9 K, and nothing frozen hides a shift.

**Tree of the evidence**: the branch at `f8e85b42` plus the review's corrections; the "before" tree is `development` at `eabe7a8f` (`git archive` of `pcbthermal/`, `examples/`, `tests/regression`). Python 3.13, NumPy on Apple Accelerate, SciPy, pyamg 5.4.1, this machine (macOS arm64, 16 GB), every heavy run alone under the heavy-job lock. The scratch scripts read the program and change nothing; their content is described where their number is used.

## 1. What was checked and the numbers

### 1.1 The closed-form determinant and inverse (`femcore.det_inv3`, `jacobian`)

* **Against `numpy.linalg`**, batches of 5 000 to 20 000 matrices: random normal (condition up to 1.8e4): determinant 1.8e-13 relative, inverse 3.6e-14; thin copper Jacobians (35 um by 1 mm, condition 9.2e4): 4.6e-14 / 5.2e-14; aspect 1e4: 4.4e-15 / 5.4e-16; nearly singular (condition 3e8): 1.7e-15 on the determinant.
* **Element matrix and load against the old routine** on single badly shaped bricks (conductivity 400 / 400 / 0.3): 35 um thin brick 8.5e-16, mirrored brick (negative determinant) 3.0e-15, strong shear (5 mm over 1 mm) 2.6e-15, twisted 1.1e-15, all relative to the largest entry.
* **Refusals**: a flat element is refused by `validate` with the same message as before ('1 element(s) have a degenerate (zero-volume) mapping, the first is element 0'); a mirrored (inverted) element is **accepted**, as before (both versions use `abs(det)`, the refusal line is unchanged). An element whose Jacobian changes sign inside is not detected by either version: a limit of `validate`, not of this branch (the structured meshes of `femmesh` cannot make one).
* **The reference of `tests/test_fem_assembly_speed.py` is the old code**: `_reference_elements` is line for line the `_assemble_elements` of `eabe7a8f` (without the cancel check). On the full matrices: example board at 1 mm 2.75e-15 of the largest entry, rhs 1.8e-15; Muzychka case 2 plates 1.6e-15 and 3.4e-15, rhs identical.

### 1.2 The CG tolerance 1e-12 -> 1e-10 (true residual, balance, read-outs, the worst mesh)

Matrices assembled by both trees and solved by the program's CG + smoothed aggregation, with the program's restart rule (one restart from the solution when the true residual is above `max(1e-8, 100 tol)`, which is 1e-8 at both tolerances):

| Mesh | Unknowns | old assembly, 1e-12 | new assembly, 1e-12 | new assembly, 1e-10 (the branch) | max \|dT\| from the old default |
| :-- | --: | :-- | :-- | :-- | :-- |
| `example_board` 1 mm | 275 724 | 331 it., true 2.17e-10, balance - 1 = +1.6e-13 | 331 it., 2.19e-10 | 280 it., **2.28e-10**, +4.8e-12 | 2.3e-10 K (rise 60 K) |
| Muzychka case 2, FR-4 film, cell 1, refinement 2 | 84 375 | 67 it., 4.8e-12 | 67 it., 4.8e-12 | 56 it., 7.3e-11 | 1.9e-10 K (rise 79 K) |
| Muzychka case 2, conductive film, cell 0.5, refinement 4 (the worst conditioned mesh of REVIEW_BRANCH4) | 828 375 | first pass true 1.10e-8 -> **restart** -> 5.02e-9, 1090 it., 110 s | the same, 5.05e-9 | first pass 1.10e-8 -> **restart** -> **4.41e-9**, 808 it., 82 s | 9.5e-10 K (rise 79 K) |

* **The 1e-10 default is safe**: on the worst mesh the recursive residual of the first pass stops at the same true residual (1.1e-8) at either tolerance, the restart fires in the same case, and the final true residual (4.4e-9) is below the bound (1e-8) with the same margin as before (5.0e-9). The theory's numbers 2.2e-10 and 2.3e-10 are reproduced (2.17e-10 and 2.28e-10).
* **Read-outs** (full `fem.solve_steady`, old tree's assembly and 1e-12 against the branch): example board, column 3.3e-10 K, `T_surface` and `T_surface_mean` 3.3e-10 K, `T_point` 3.3e-10 K, hottest node 2.0e-10 K; case 2 (FR-4 film) 2.2e-11 / 6.9e-11 / 9.2e-11 / 1.0e-12 K. All below 1e-8 K. Heat balance within 5e-12 everywhere.
* **The CHANGELOG sentence 'the true residual stays 1e-10 to 2e-10' was wrong in general** (it holds for the example board; the large plate stops at 4.4e-9 after the restart): corrected in the CHANGELOG, `docs/theory.md` 4a and the docstring of `Model.solve`.

### 1.3 Timing (example board, 1 mm, `api.simulate` with the FEM alone, fresh process, two alternated runs per tree)

Before 16.06 s and 16.10 s, after 11.72 s and 11.83 s; `Model.assemble` cumulative 3.61 / 3.57 s before, 1.19 / 1.18 s after; the hottest temperature identical to the printed digits (84.686131 degC); peak 1.85 GB in both. The claims 16.0 -> 11.7 s and 3.58 -> 1.18 s are reproduced.

### 1.4 The frozen numbers

* **Old records**: the branch changes only `femcore.py` in the program, and no path of the FVM, FDM, Lumped, Analytic or 3D solid calls the changed functions (`femcore` is imported elsewhere only for `FEM_DIRECT_MAX`, `available` and `FemUnavailable`); `metrics_of` only adds names. So the old records are bit-identical by construction; the frozen test holds them under its tolerance. An exact (`--exact`) re-run of the 249 old records was **not** done.
* **FEM records**: the 29 records of `fem-records.json` against the file of `eabe7a8f`: same keys, largest temperature change 8.5e-10 K (`plate_lone_via|fem|2` t_min, a direct solve: the assembly rounding alone), field sums 1.4e-11 relative, balance 1.0e-11 W: the executor's numbers are right.
* **Run-to-run repeatability** (new): re-running the 29 FEM records on the same tree gives up to 5.0e-10 K (`plate_pad|fem|1`, CG) and 4e-12 relative on the field sums: the CG records are not bit-identical from run to run. Inside the 1e-8 K policy; recorded for the refreeze (SPEED_NOTES).
* **Surface metrics, spot-check of six records** (a direct `simulate`, statistics recomputed by a separate script from the arrays): `example_board|fvm|1`, `hatched_copper|fdm|1`, `plate_uniform|fvm|2`, `one_layer_pad|fdm|1`, `finned_block|fvm|1`, `plate_vias|fem|2`: every face statistic equal to the file (difference 0.0); the part surface maximum equals the maximum of `T_surface` over the cells whose centre lies in the part's rectangle (85.4664, 72.7387, 113.4542, 159.0550, 91.2879, 129.9421, 133.6257). Cross-model reading of the files: FVM and FDM surface within 2 mK of their column except `hatched_copper` (+1.215 K, the laminate face term, explained in REVIEW_SURFACE_ALWAYS item 8), the FEM surface within 1 mK of its column on these PCB-copper boards.
* **The two harness copies** are byte-identical (`cmp`; `tests/regression/test_harness_copy.py` passes).
* **Can a `new_readouts` record hide a shift of an old metric?** No: `compare` takes the union of the metric names, and `test_pending_shifts_belong_to_the_frozen_release` refuses an addition that names a metric the frozen record holds. But `with_pending` let the addition **override** a metric of the record as a shift left it (`{**shifted, **added}`): a later shift file made with the new harness (which also stores the surface) would have been overwritten by the older addition, a false alarm or, worse, a stale expected value. Corrected (section 3).
* **Memory**: `PCBT_FROZEN_CELLS=2,1,0.5 pytest tests/regression`, one process, `/usr/bin/time -l`: branch **3.75 GB** maximum resident (3.60 GB footprint) and 3.96 GB in the final run, `development` before the branch **4.21 GB** (4.06 GB footprint), same hour. The new arrays cost nothing measurable; the 4.10 GB of the executor's run is the run-to-run variation of the same process (3.75 to 4.1 GB); the branch does not raise the peak. Nothing cheap to reduce on this branch; the peak sits at the 4 GB aim on both trees. (The review's own matrix script of the 828 375-unknown case peaked at 5.0 GB because it held two assemblies at once: a review script, not the program, run alone.)

### 1.5 Documents

`docs/theory.md` 4a (speed paragraph): the numbers are right for the example board and `plate_vias`; the residual sentence was made general (1.2 above). CHANGELOG, `docs/versions.md`, `docs/decisions-log.md`: right, completed with the review's additions. The note for the refreeze was missing: written in `SPEED_NOTES.md` ('What the 2.8.0 refreeze must do') with a pointer in `releases/2.8.0/plan-resume/PLAN.md` (G-7, item 1).

## 2. Findings, by severity

1. **Harness defect (refreeze), would have blocked `study_diff.py --strict`**: `regress_classify.diff_sets` classified a metric present in one run only with the scope metric `status`, so the ~1 200 surface metrics added to the FVM and FDM records (baseline v2.7.1 has no surface) could only be excused by a rule on `status`, which would also excuse a run that failed. Fixed: an optional `added_metrics` list of the table matches a metric that only the new run has by its name (section 3).
2. **Test defect**: `with_pending` let an addition override a value a shift holds (1.4). Fixed, with a regression test.
3. **Decision B not complete**: `_blocks` of the harness still refused the FEM, so the FEM metal block (`finned_block`) was unguarded. Fixed: `_blocks` accepts `fem` (`analysis.block_stats` works on a FEM result: 64.77 degC mean, 3.956 W at 2 mm, FVM 65.07 degC, 3.943 W), the two `finned_block` FEM records gained the three block metrics; nothing else of the file changed.
4. **Wrong document**: 'the true residual stays 1e-10 to 2e-10' (CHANGELOG, theory, docstring): true only on the example board. Corrected.
5. **Limit to record**: CG records are not bit-identical run to run (5e-10 K). Recorded in SPEED_NOTES.
6. **Limit (not of this branch)**: `validate` accepts an inverted element and cannot see a Jacobian that changes sign inside an element; unreachable from `femmesh`.

## 3. What the review changed on the branch

* `tests/regression/test_frozen_numbers.py`: `with_pending` merges an addition under the record (`{**added, **record}`: a metric the record holds keeps its value); new test `test_a_new_readouts_file_only_adds_metrics_and_cannot_hide_a_shift` (file-name order, shift wins, a shift of an old metric and of the added read-out and a vanished read-out are all reported).
* `releases/regression-harness/lib/regress_classify.py` and its copy `tests/regression/regress_classify.py`: `diff_sets` classifies a metric only in the new run as `expected` where an `added_metrics` scope of the table names it; test `test_an_added_read_out_is_expected_only_where_an_added_metrics_scope_names_it` in `releases/regression-harness/tests/test_classify_logic.py`; `releases/regression-harness/README.md` section 1 says so.
* `releases/regression-harness/lib/regress_harness.py` and its copy: `_blocks` accepts `fem`; `tests/regression/data/pending/fem-records.json`: the block metrics of `finned_block|fem|1` and `|2` added (the other 1 000-odd numbers kept as the executor wrote them), its `why` says so.
* `pcbthermal/femcore.py` (docstring of `Model.solve` only), `docs/theory.md` 4a, `CHANGELOG.md`, `docs/versions.md`, `docs/decisions-log.md`, `releases/2.8.0/fem-model/SPEED_NOTES.md`, `releases/2.8.0/plan-resume/PLAN.md`.

**Re-runs after the corrections**: `tests/test_fem_*.py`, `tests/test_docs.py`, `tests/test_license_header.py`, `tests/test_version.py`, `releases/regression-harness/tests`: 957 passed; `tests/regression/test_harness_copy.py` passes; `PCBT_FROZEN_CELLS=2,1,0.5 pytest tests/regression`: see the line below.

Final run after every correction: **347 passed** in 176 s (346 + the new test), 3.96 GB maximum resident.

## 4. Not verified

* An `--exact` comparison of the 249 old records between the two trees (argued by construction, 1.4).
* `plate_vias` at 1 mm timing (3.06 -> 2.22 s) was not re-timed; the example board was.
* The whole battery (not asked; the maintainer runs it before the merge).

## 5. Open decisions for the maintainer

None that block. At the refreeze, the `added_metrics` scope of SPEED_NOTES must be written into `expected_shifts_2.8.0.json` (with the adaptation of `make_expected_shifts.py` already planned in PLAN G-7).
