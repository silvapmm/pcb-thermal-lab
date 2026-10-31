#!/bin/sh
# The rows of docs/validation.md (rerun after the 3D size guard was added to the scenario table).
PY=${PY:-/Volumes/SSD/PROJETOS/pcb-thermal-lab/.venv/bin/python}
D=research/via-real-board
$PY $D/scripts/study_validation_rows.py > $D/out/validation_rows.txt 2>&1
echo finished > $D/out/S2D_DONE
