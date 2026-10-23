"""!
@file conftest.py
@brief Puts research/gerbers/lib and research/gerbers/scripts on the import path so the tests import the modules and the studies directly.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
for sub in ("lib", "scripts"):
    sys.path.insert(0, str(HERE / sub))
