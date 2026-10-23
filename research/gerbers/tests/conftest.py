"""!
@file conftest.py
@brief Puts the research folder on the import path so the tests import the modules of research/gerbers directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
