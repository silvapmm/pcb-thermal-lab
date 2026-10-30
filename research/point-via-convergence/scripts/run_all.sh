#!/bin/sh
# Runs every study of the folder in turn (from the repository root); the outputs go to research/point-via-convergence/out/ (git-ignored). About 1.5 hours on a 10-core machine.
PY=${PY:-.venv/bin/python}
D=research/point-via-convergence
mkdir -p $D/out
$PY $D/scripts/study_unit_cell.py > $D/out/unit_cell.txt 2>&1
$PY $D/scripts/study_array_board.py --model fvm > $D/out/array_fvm.txt 2>&1
$PY $D/scripts/study_array_board.py --model fdm > $D/out/array_fdm.txt 2>&1
$PY $D/scripts/study_array_board.py --sweep --model fvm > $D/out/sweep_fvm.txt 2>&1
$PY $D/scripts/study_array_board.py --sweep --model fdm > $D/out/sweep_fdm.txt 2>&1
$PY $D/scripts/study_row_lone.py --model fvm > $D/out/row_fvm.txt 2>&1
$PY $D/scripts/study_row_lone.py --model fdm > $D/out/row_fdm.txt 2>&1
$PY $D/scripts/study_example_board.py --model fvm --fine > $D/out/example_fvm.txt 2>&1
$PY $D/scripts/study_example_board.py --model fdm > $D/out/example_fdm.txt 2>&1
$PY $D/scripts/study_solid3d.py > $D/out/solid3d.txt 2>&1
echo finished > $D/out/ALL_DONE
