#!/bin/sh
#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
# Run the real-board comparison on the boards of the local library, one at a time (from the repository root).
PY=${PY:-.venv/bin/python}
for b in "cmm2 1.0,0.5 3" "isastm 1.0,0.5 3" "oswlight 1.0,0.5 3" "rp2040 1.0,0.5 3" "co60 1.0 3"; do
  PCBT_REAL_BOARDS=${PCBT_REAL_BOARDS:-pcb-library/real} $PY -u research/imported-via-rim/scripts/study_real_boards.py $b
done
