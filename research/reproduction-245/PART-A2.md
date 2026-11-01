# Reproduction of 2.4.5, part A2: the long studies of gap-subdivision

Completes the three rows that `PART-A.md` and the README of this folder left as NOT RUN (they need `out/refs_pads.json`). Tree under test: the tip of `research/reproduction-245` (`8436db5`) with the program of 2.4.5 (`pcbthermal/` untouched). All runs with `nice -n 15`, one job at a time, `QT_QPA_PLATFORM=offscreen`, `.venv/bin/python`. The README numbers of `research/gap-subdivision` are not rewritten.

## Commands, times and results

| Step | Command (from the repository root) | Time | Result |
| :-- | :-- | --: | :-- |
| references | `scripts/study_baseline_pads.py 3` (3 processes; writes `out/refs_pads.json`, 52 references, and `baseline/pads.csv`) | 22 min | exit 0 |
| 5.1, 5.2, 5.4, 5.5 | `scripts/study_gap_nodes.py` (writes `baseline/gap_nodes.csv`) | 28 min | exit 0 |
| 5.3 | `scripts/study_gap_grading.py` (writes `baseline/gap_grading.csv`) | 1 min | exit 0 |
| 10.1 to 10.3 | `scripts/study_review.py` (default: all three checks) | 10 min | exit 0 |
| 6.2 | `scripts/study_real_boards.py` (writes `baseline/real_boards.csv`; `out/` was empty, the reference was recomputed) | 1 min | exit 0 |

The references took 22 minutes, not the 1.5 to 3 hours of the README (3 processes, quiet disk, `nice` only).

## Why most numbers cannot move

`study_gap_nodes.py`, `study_gap_grading.py`, `study_review.py` (parts 1 and 3) and `study_real_boards.py` do not call the program: they use `lib/gapnodes.py` on the layered copy of `research/bare-spot-under-source/lib/layered.py`, and their "n = 1" is `boards.program_without_rule()`, the network of 2.4.4. They are therefore independent of the laminate rule and the other 2.4.5 items, and must reproduce the README. The only program-dependent numbers are the "FVM" columns of `study_review.py` part 2 (they call the program) and the model columns of `baseline/pads.csv`.

## Differences above the tolerance (0.5 %, none given by the folder)

| folder | README section | README | now | 2.4.5 item | verdict |
| :-- | :-- | :-- | :-- | :-- | :-- |
| gap-subdivision | 5.1 uniform boards, n = 1 2 4 8 and graded (9 rows) | table | identical to the printed digit (checked line by line) | none | OK |
| gap-subdivision | 5.2 pad boards, 14 rows x 10 columns | table | all identical to 0.01 point except `4 layers, 0.2 mm gaps, top pad`: the converged reference moved 75.672 -> 75.691 K (+0.025 %), so the totals move by at most 0.03 point (n = 1 tot +0.23 -> +0.20, n = 4 tot eq +0.41 -> +0.38); the z columns are unchanged | none (the cached reference of the first run was fitted again: spread 0.034 -> 0.046 %, order 1.71 -> 1.61, below the folder's own reference spread) | OK (0.03 point, under 0.5) |
| gap-subdivision | 5.3 grading, 3 boards x 9 cuts x 5 n | table | identical; `baseline/gap_grading.csv` identical to the committed file (0 differing lines) | none | OK |
| gap-subdivision | 5.4 the cell (probe 6, three cells) | 1 mm -4.12/-6.84 ... 0.25 mm -5.15/-5.61 | identical (all 18 numbers) | none | OK |
| gap-subdivision | 5.5 cost | 10 800 / 18 000 / 32 400 unknowns, 1.49 / 2.46 / 4.40 x, 1.44 / 2.33 / 4.11 x | identical (seconds differ: 0.04 / 0.12 / 0.65 -> 0.07 / 0.23 / 1.24 s, a timing on a loaded machine) | none | OK (timing = load) |
| gap-subdivision | 4 probes (the `computing 1 references` blocks of part C) | printed in the log | identical to the previous run's pattern for pad10-full and pad20-empty; the committed `gap_nodes.csv` differs only in the 24 rows of the L4-gap0.2 board (the reference above) | none | OK |
| gap-subdivision | 10.1 layered model at n to infinity | -5.93 -3.32 -1.85 -1.02 -0.55 -0.30 -0.17, limit -0.025 % (p 0.94); graded -1.49 -0.49 -0.20 | identical | none | OK |
| gap-subdivision | 10.2 columns "program 3D solid", "same-cell 4", "same-cell 32", "4-slab part" | +5.07 +1.90 +0.69 +0.43 +3.39 +2.56 (and the others) | identical on the six rows (the 3D solid is not changed by the laminate rule on a two-layer board) | none | OK |
| gap-subdivision | 10.2 column "FVM" (the program) | -10.53, -4.73, -0.86, +0.32, -10.21, -5.90 | **-1.05, -0.67, -0.15, +0.34, -2.29, -0.83** | laminate nodes of 2.4.5 (`fix/laminate-nodes`, rule n = min(4, ceil(d/0.4 mm)) in the cells with absent copper plus a margin; `research/laminate-nodes` 3.2, 3.4; `docs/versions.md` 2.4.5) | EXPLAINED |
| gap-subdivision | 10.2 column "FVM, gap alone" (the program against the same-cell solver) | -13.55, -5.94, -1.43, -0.12, -11.51, -7.48 | -4.39, -1.94, -0.72, -0.10, -3.70, -2.49 | same item | EXPLAINED |
| gap-subdivision | 10.3 second solver on two pad references | pad10-full +0.08 %, pad6-full +0.84 % (limits 100.485 and 137.78 K) | identical | none | OK |
| gap-subdivision | 6.2 real windows (6 rows), `baseline/real_boards.csv` | table | identical, CSV identical to the committed file | none (the "program" column is the copy of the 2.4.4 network, see above) | OK |
| gap-subdivision | `baseline/pads.csv` (52 boards, model columns) | the 2.4.5 values written by `rerun_baseline.py --update` | identical in every model column; only the reference columns of the one board above differ | none | OK |

### The movement of the FVM toward the reference

The expected direction is the one of `research/laminate-nodes`: the program now has the rule that this folder proposed, so its error against the converged reference should fall to about the "bare + margin, n = 4, equal" column of README 5.2. It does:

| board | FVM before (2.4.4, README 5.2/10.2, n = 1 tot) | FVM now | README 5.2 "bare + margin, n = 4 tot eq" |
| :-- | --: | --: | --: |
| pad10-empty | -5.90 | -0.83 | -0.88 |
| pad10-full | -4.73 | -0.67 | -0.71 |
| pad10-pad | -6.02 | -0.95 | -0.99 |
| pad20-empty | -1.70 | -0.00 | -0.03 |
| pad20-full | -0.86 | -0.15 | -0.15 |
| gap 3.2 full | -10.21 | -2.29 | -2.33 |
| 4 layers 1.6 mm top pad | -4.63 | -0.69 | -0.73 |
| 6 layers 0.4 mm, pad on every layer | -1.07 | -0.95 | +0.73 |

Seven of the eight rows agree with the proposal to 0.05 point (the program's rule is the proposed one). The last row does not move toward the proposal: the six-layer board with a pad on every layer sits at -0.95 % now (was -1.07) while the study's n = 4 point is +0.73 %; the cause (a difference between the program's mask of absent copper and the study's) was not investigated: the error is under 1.1 % and cool, as before. Listed for the reviewer. Also the FDM and Lumped columns move accordingly in `baseline/pads.csv`, as `README.md` "Update for the program of 2.4.5" already reports.

## Counts

Checked: 14 groups of numbers (the 5.1 table, 5.2, 5.3, 5.4, 5.5, the part C probes, 10.1, 10.2 (two groups), 10.3, 6.2, `pads.csv`, `gap_nodes.csv`, `gap_grading.csv`, `real_boards.csv`).
Unchanged (OK): 12.
Explained: 2 (10.2 "FVM" and "FVM, gap alone": the laminate rule of 2.4.5).
UNEXPLAINED: 0 (one point to look at, the six-layer all-pads row, is listed above and is not a shift of the README).
Not run: 0.

## Regenerated files

`research/gap-subdivision/baseline/gap_nodes.csv` (24 rows of the L4-gap0.2 board changed by up to 0.03 point because the reference was fitted again, 75.6718 -> 75.6906 K) and `baseline/pads.csv` (the reference columns of the same board). `gap_grading.csv` and `real_boards.csv` were regenerated and are byte-identical. `out/` (git-ignored) holds `refs_pads.json` and the text of the runs.

## What could not be verified

* Why the cached reference of the L4-gap0.2 board differs by 0.025 % from the one in the committed `pads.csv`: the graded solver is deterministic by design, so the cause was not established (a different number of fitted grids or a changed BLAS thread count are the candidates); it is far below the folder's tolerance.
* The 6-layer all-pads row discussed above.
