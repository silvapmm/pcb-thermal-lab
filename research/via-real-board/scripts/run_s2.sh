#!/bin/sh
# Runs the S2 studies (from the worktree or repository root); outputs in research/via-real-board/out/ (git-ignored). No network: the boards are read in place.
PY=${PY:-/Volumes/SSD/PROJETOS/pcb-thermal-lab/.venv/bin/python}
D=research/via-real-board
mkdir -p $D/out
$PY $D/scripts/study_fillin.py --cells 1 0.5 --max-dense 15000000 --max-nnz 25000000 > $D/out/fillin.txt 2>&1
$PY $D/scripts/study_sor_real.py --cells 1 --cap 20000 > $D/out/sor_real.txt 2>&1
$PY $D/scripts/study_real_board_effect.py --cells 2 1 0.5 --fdm --save-maps 0.5 > $D/out/real_effect.txt 2>&1
$PY $D/scripts/study_lumped_gzvia.py > $D/out/lumped_gzvia.txt 2>&1
echo finished > $D/out/S2_DONE
