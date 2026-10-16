"""!
@file conftest.py
@brief Shared pytest setup: make the repository root importable.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# GUI tests run without a display; matplotlib must use the PySide 6 binding
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")
