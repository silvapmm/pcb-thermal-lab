#!/bin/sh
# Second round of the S2 studies (after the first run showed that the fixed pad saturates, and that 0.5 mm and 0.25 mm were missing).
# The 0.25 mm Allegro board (527 000 unknowns, LU estimated at 1.8 GB) is left out of the temperature and SOR runs to keep every process under about 4 GB.
PY=${PY:-/Volumes/SSD/PROJETOS/pcb-thermal-lab/.venv/bin/python}
D=research/via-real-board
mkdir -p $D/out
$PY $D/scripts/study_fillin.py --cells 1 0.5 --max-dense 15000000 --max-nnz 25000000 > $D/out/fillin.txt 2>&1
$PY $D/scripts/study_sor_real.py --cells 0.5 --cap 30000 > $D/out/sor_real_05.txt 2>&1
$PY $D/scripts/study_real_board_effect.py --cells 1 0.5 0.25 --only storm "own 100" > $D/out/real_effect_fine.txt 2>&1
echo finished > $D/out/S2B_DONE
