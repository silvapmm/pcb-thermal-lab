"""!
@file _bootstrap.py
@brief Puts research/gerbers/lib on the import path; every script imports it first (`import _bootstrap`), so scripts run from any folder.
"""

import sys
from pathlib import Path

LIB = str(Path(__file__).resolve().parents[1] / "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)
