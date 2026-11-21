# Refreeze of 2.9.0: report

Tree: `release/2.9.0-bump` (version 2.9.0, commits 70ed2753 and 75ab397b); baseline: the tag v2.8.0, run by the same harness on the same machine and libraries (`study_baseline_release.py --tag v2.8.0`, then `study_run_suite.py --label final` on the tree). Table of expected shifts: `releases/regression-harness/reference/expected_shifts_2.9.0.json`, written by `scripts/make_expected_shifts_2_9_0.py` from the two result sets. The result sets and the diff report are in the git-ignored `releases/regression-harness/out/` (`v2.8.0.json`, `final.json`, `diff_v2.8.0_vs_final.md`). Every number below was re-measured by the review from those files.

## Result

* Alarms of `study_diff.py --strict` (re-run by the review on the two sets with the 2.9.0 table, exit code 0): **0** (unexplained 0, must-not-move 0, out of range 0, to be explained 0; 50 records with warning texts changed only; the internal checks of both sets pass).
* Shifted numbers: **2289**, all `expected`; records identical in every number: 149 of the diff (both runs include the two new boards); skipped or failed in both: 29.
* Frozen file `tests/regression/data/v2.9.0.json` (identical to `releases/regression-harness/reference/v2.9.0.json`): 22 boards, **367 records** (199 bit-identical to v2.8.0, 168 moved), 94 times to 63 % (70 of v2.8.0, 18 FEM, 6 of the new boards in the other models), 29 skipped (the one new skip: `thick_copper_gap|fem|0.5`, 188 100 unknowns above the harness cap). The four pending files of 2.9.0 are folded in and deleted.
* Tests: `PCBT_FROZEN_CELLS=2,1,0.5 pytest -q tests/regression` **474 passed** (247 s); `PCBT_FROZEN_CELLS=2` 238 passed; `releases/regression-harness/tests` and `releases/2.8.0/refreeze/tests` 30 passed.

## Shifts per item

| Item | Model | Records | Numbers | What moved (2.9.0 minus 2.8.0) |
| :-- | :-- | --: | --: | :-- |
| FEM part on an outer copper layer enters through its face (`fix/fem-thin-copper-source`) | FEM | 42 | 960 | column of the boards whose part sits on copper +0.01 to +0.8 mK (`finned_block` +0.26 mK, `top_block_pad` +0.03 mK); `drawn_ell` column +0.106, +1.034, +1.476 K at 2, 1, 0.5 mm; FEM surface by up to the term `q t / (2 k)` (`drawn_ell` +0.23 to +3.29 K); `thick_copper_gap` (420 um, already a face flux) 3e-10 K |
| 3D solid interface pad conducts across only (`fix/solid3d-pad-inplane`) | 3D solid | 6 | 60 | `finned_block` +0.0020 to +0.0021 K; `top_block_pad` +0.754, +0.777, +0.784 K at 2, 1, 0.5 mm |
| Copper slabs of the 3D solid (`feature/solid3d-copper-slabs`) | 3D solid | 3 | 33 | `thick_copper_gap` +0.521, +0.566, +0.584 K at 2, 1, 0.5 mm; unknowns doubled (copper above 105 um is a slab of its own) |
| Surface read-out of the Analytic and the 3D solid (`feature/surface-readout-models`) | Analytic, 3D solid | 126 | 1236 | additions (no old value) |
| FEM time simulation (`feature/fem-transient`) | FEM | 18 times | | additions: 16 of the pending file and the two new boards |

Of the 2289 numbers, 292 (51 records) are accepted by the round-off rule as well as by their item: they are the field checksums (`t_sum`, `t_sumsq`) and the heat-balance residuals of the moved records, which the round-off rule does not bound in kelvin, plus `thick_copper_gap|fem|1` (3e-10 K) and three FEM minima within 1e-8 K. They are not a separate set of shifts. **The FVM, the FDM, the Lumped and the Analytic did not move on any board** (no shifted number in those models, the new boards included; the Analytic only gains its surface metrics), and no time to 63 % of v2.8.0 moved.

Check against the pending files (independent of the table, whose limits are measured on the same run): every record of `v2.9.0.json` on the 20 old boards equals the record of `v2.8.0.json` with the pending records applied over it, bit for bit outside the FEM; the FEM records differ from `fem-thin-copper-source.json` by at most 4.3e-10 K (round-off of the solve).

## The two new boards

Hottest column (degC), 3D solid, harness run of v2.8.0 against the tree; the other models unchanged (FEM of `top_block_pad` +3e-5 K, the thin-copper item):

| Board | Cell | v2.8.0 | 2.9.0 | Item |
| :-- | --: | --: | --: | :-- |
| `top_block_pad` | 2 mm | 170.4723 | 171.2264 | pad in-plane |
| `top_block_pad` | 1 mm | 170.6620 | 171.4392 | pad in-plane |
| `top_block_pad` | 0.5 mm | 170.6209 | 171.4045 | pad in-plane |
| `thick_copper_gap` | 2 mm | 172.8462 | 173.3670 | copper slabs |
| `thick_copper_gap` | 1 mm | 172.5079 | 173.0735 | copper slabs |
| `thick_copper_gap` | 0.5 mm | 171.2449 | 171.8287 | copper slabs |

These shifts have no pending record (the boards are new): the table attributes them by hand (`NEW_BOARD_ITEMS` of the script) and the values match the stage-A review and `releases/2.9.0/PLAN.md` e33.

## The classifier change (a time that only the new run has)

The v2.8.0 baseline holds the FEM times to 63 % as skipped, so the first diff gave 18 alarms (a time present in one set only was always `unexplained`). `classify_transients` (`releases/regression-harness/lib/regress_classify.py` and its byte-identical copy `tests/regression/regress_classify.py`) now classes such a time as `expected` only when the old value is absent, the new one present, and the table's `transients.added` list names the board and model (2.9.0: the FEM only). Checked by the review: a time of another model that appears from nothing still alarms (FVM time removed from a copy of the baseline: 1 alarm, exit code 1), a time that disappears still alarms (the rule needs the old value absent), and an FVM board maximum moved by 1e-3 K in a copy of `final.json` gives 1 alarm and exit code 1. The new test `test_a_time_only_the_new_run_has_is_an_addition_only_when_the_table_names_it` holds the rule. A future table that leaves `added` empty keeps the old behaviour.

## Limits recorded

* The limits of the item rules are 1.25 times the shifts of this run (the same method as 2.8.0): the table holds the next run to these sizes, it does not predict them. The independent check is the comparison with the pending files above.
* The field checksums and the balance residuals are not bounded by the round-off rule (a property of the harness since 2.4.5): a shift of a checksum alone in an unmoved model would pass; any real change also moves a temperature, which is bounded at 1e-8 K.
* The hottest FEM node (`point:t_max`, a mesh vertex) of `drawn_ell` moved +2.58, +6.19, +3.31 K at 2, 1, 0.5 mm (the same values are in the pending file). It is the vertex at the corner without top copper, where the thin-copper item now puts the whole face flux on the laminate slab; it was already not converged in v2.8.0 (107.1, 141.3, 129.6 degC at 2, 1, 0.5 mm). The item text sizes the column and the surface, not this vertex; the vertex is not a read-out of the program's tables.
* Between commit 70ed2753 (pending files deleted) and 75ab397b (new frozen file) the frozen test fails; the branch is merged with `--no-ff` as a whole, so `development` never holds that state.

## Commands

```sh
.venv/bin/python releases/regression-harness/scripts/study_baseline_release.py --tag v2.8.0
.venv/bin/python releases/regression-harness/scripts/study_run_suite.py --label final
.venv/bin/python releases/2.9.0/refreeze/scripts/make_expected_shifts_2_9_0.py releases/regression-harness/out/v2.8.0.json releases/regression-harness/out/final.json
.venv/bin/python releases/regression-harness/scripts/study_diff.py releases/regression-harness/out/v2.8.0.json releases/regression-harness/out/final.json --table releases/regression-harness/reference/expected_shifts_2.9.0.json --strict
.venv/bin/python releases/regression-harness/scripts/study_freeze_reference.py releases/regression-harness/out/v2.8.0.json releases/regression-harness/out/final.json --version 2.9.0 --table releases/regression-harness/reference/expected_shifts_2.9.0.json
cp releases/regression-harness/reference/v2.9.0.json tests/regression/data/
PCBT_FROZEN_CELLS=2,1,0.5 .venv/bin/python -m pytest -q tests/regression
```
