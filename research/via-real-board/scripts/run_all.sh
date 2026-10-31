#!/bin/sh
# Runs every study of the folder in turn (from the repository root); the outputs go to research/via-real-board/out/ (git-ignored).
# Run it only on a quiet machine: the timings are not recorded, but the heavy cases use several GB. PY selects the interpreter.
PY=${PY:-.venv/bin/python}
D=research/via-real-board
mkdir -p $D/out
$PY $D/scripts/fetch_boards.py > $D/out/fetch.txt 2>&1
$PY $D/scripts/study_edge_distance.py --h-side 0 10 --check-fine > $D/out/edge_distance.txt 2>&1
$PY $D/scripts/study_edge_distance.py --h-side 0 --corner > $D/out/edge_corner.txt 2>&1
$PY $D/scripts/study_edge_outline.py > $D/out/edge_outline.txt 2>&1
$PY $D/scripts/study_real_vias_stats.py > $D/out/real_stats.txt 2>&1
$PY $D/scripts/study_fillin.py > $D/out/fillin.txt 2>&1
$PY $D/scripts/study_real_board_effect.py --fdm --save-maps 0.5 > $D/out/real_effect.txt 2>&1
$PY $D/scripts/study_sor_real.py > $D/out/sor_real.txt 2>&1
$PY $D/scripts/study_solid3d_real.py > $D/out/solid3d_real.txt 2>&1
$PY $D/scripts/study_lumped_gzvia.py > $D/out/lumped_gzvia.txt 2>&1
$PY $D/scripts/study_validation_rows.py > $D/out/validation_rows.txt 2>&1
$PY $D/scripts/make_diagrams.py
$PY $D/scripts/make_figures.py
echo finished > $D/out/ALL_DONE
