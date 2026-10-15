"""!
@file conftest.py
@brief Shared pytest setup: make the repository root importable.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
