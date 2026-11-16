# Refreeze of 2.8.0: report

Tree: `development` 232ba648 plus the refreeze commit; baseline: tag v2.7.1 (v2.7.1 moved no frozen number, so also v2.7.0). Reference of every shift: the baseline run of the same harness on the tag. Detail: `DIFF_v2.7.1_vs_final.md`; table: `releases/regression-harness/reference/expected_shifts_2.8.0.json`.

## Result

* Alarms: **0** (unexplained 0, must-not-move 0, out of range 0, to be explained 0).
* Shifted numbers: **3882**, all `expected` by the table (13 rules, none without an item). Records identical in every number: **54**. The 3D solid did not move.
* Shifted records per rule: R1 Analytic with M1 57; R2 FDM with M1 39; R3 FVM with M1 39; FDM with M1 and M2 21; FVM with M1 and M2 21; R6 Lumped with M1 and M3 59; R7 Analytic with M1 and M4 3 (records of the maximum temperature).
* Shift of the board maximum per model (K, 2.8.0 minus 2.7.1): Analytic median 0, maximum +0.13; FDM median 0, maximum +18.98; FVM median 0, maximum +17.91 (the three new `drawn_*` boards at 2 mm, item M2); Lumped median +0.59, maximum +5.55, minimum -1.51.
* Additions (not shifts): 60 FEM entries (20 boards x 3 cells, all `direct`; the pending file had 29): 38 hold numbers and 22 are skipped in the frozen file (above the harness cap); the surface read-outs of the FVM, FDM and SOR runs; the three `drawn_*` boards in all models.
* Frozen file `tests/regression/data/v2.8.0.json` (identical to `releases/regression-harness/reference/v2.8.0.json`): 332 records (54 bit-identical to 2.7.1, 278 moved), 70 transients, 28 skipped; the six pending files are deleted.
* Tests: `PCBT_FROZEN_CELLS=2,1,0.5 pytest tests/regression` 413 passed in 182 s (200 with cell 2 only).
* Times and resources: baseline run on v2.7.1 about 2 min, final run 192 s; peak resident memory 4.17 GB (above the 4 GB ceiling, finished without trouble); swap 1.77 GB.

## The version line

`pcbthermal.__version__` is still 2.7.1 on `development`, and the freeze refuses a version other than 2.8.0. The tester put a temporary `2.8.0` line for the final run and the freeze and reverted it. The real bump belongs to the release commit.

## Tests of this folder

`tests/test_expected_shifts_2_8_0.py` held three tests that certified the preview table against the pending files (every shift expected, additions not shifts and the 3D solid held, a file of additions never the item of a shift). After the refreeze the pending files are deleted, so they failed by design. They were rewritten to read what remains: the diff report (0 alarms, 3882 expected, 54 identical), the frozen file against its reference copy (332 records, 28 skipped, 70 transients, 60 FEM entries of 20 boards, no pending file) and the table (13 rules, none open, the 3D solid held, no 3D solid shift in the report). The functions of `scripts/make_expected_shifts_2_8_0.py` that read the pending files are no longer exercised by a test (the script stays as the record of how the table was made).

## `docs/version-comparison.md`: not regenerated (decision 3 of `REFREEZE_PLAN.md`)

`regen_version_comparison.sh` needs result sets of every version v2.0.0 to v2.7.0 in `out/` (they are not on disk) and a pair entry in `version_notes.json`. Done: the entry `v2.7.0->v2.8.0` was added to `releases/regression-harness/reference/version_notes.json` from `releases/2.8.0/WHAT_MOVED.md`. Left: the document keeps its 'stale until the next regeneration' note; the regeneration with all versions is item e15 of `releases/2.9.0/PLAN.md`.

## Commands

```sh
.venv/bin/python releases/regression-harness/scripts/study_baseline_release.py --tag v2.7.1
.venv/bin/python releases/regression-harness/scripts/study_run_suite.py --label final
.venv/bin/python releases/regression-harness/scripts/study_diff.py <baseline> <final> --strict
.venv/bin/python releases/regression-harness/scripts/study_freeze_reference.py out/v2.7.1.json out/final.json --version 2.8.0
cp releases/regression-harness/reference/v2.8.0.json tests/regression/data/
PCBT_FROZEN_CELLS=2,1,0.5 .venv/bin/python -m pytest -q tests/regression
```
(the exact arguments are those of the tester's run; the `study_diff.py` output is `DIFF_v2.7.1_vs_final.md`.)
