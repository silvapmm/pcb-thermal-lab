#!/bin/sh
# Runs the S1 studies and the board statistics (from the repository root or the worktree root); outputs in research/via-real-board/out/ (git-ignored).
PY=${PY:-/Volumes/SSD/PROJETOS/pcb-thermal-lab/.venv/bin/python}
D=research/via-real-board
mkdir -p $D/out
$PY $D/scripts/study_edge_distance.py --h-side 0 10 > $D/out/edge_distance.txt 2>&1
$PY $D/scripts/study_edge_distance.py --h-side 0 --corner > $D/out/edge_corner.txt 2>&1
$PY $D/scripts/study_edge_outline.py > $D/out/edge_outline.txt 2>&1
$PY $D/scripts/study_real_vias_stats.py > $D/out/real_stats.txt 2>&1
echo finished > $D/out/S1_DONE
