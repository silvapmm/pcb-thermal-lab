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


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_modal_rectangle_message(monkeypatch):
    """!
    @brief Answer OK to the "board with an outline" message before a run, so no test waits for a real dialog (a test of the message patches it again).
    @param monkeypatch pytest fixture.
    """
    try:
        from PySide6.QtWidgets import QMessageBox
    except ImportError:                                   # Physics-only environment
        return
    monkeypatch.setattr(QMessageBox, "exec", lambda self: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Discard))     # Closing a modified document asks
