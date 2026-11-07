#!/bin/sh
#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
# Third round: the 3D solid on windows and the rows of docs/validation.md (run after run_s2b.sh, one process at a time).
PY=${PY:-/Volumes/SSD/PROJETOS/pcb-thermal-lab/.venv/bin/python}
D=research/via-real-board
$PY $D/scripts/study_solid3d_real.py --window 30 --cells 1 0.5 > $D/out/solid3d_real.txt 2>&1
$PY $D/scripts/study_validation_rows.py > $D/out/validation_rows.txt 2>&1
echo finished > $D/out/S2C_DONE
