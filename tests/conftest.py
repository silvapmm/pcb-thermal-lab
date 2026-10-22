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
def _no_modal_messages(monkeypatch):
    """!
    @brief Answer the modal messages (a real dialog would wait for a click and block the battery): OK to any message box, Discard to "save the changes?".
    @param monkeypatch pytest fixture.
    """
    try:
        from PySide6.QtWidgets import QMessageBox
    except ImportError:                                   # Physics-only environment
        return
    monkeypatch.setattr(QMessageBox, "exec", lambda self: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Discard))     # Closing a modified document asks


@pytest.fixture(autouse=True)
def _private_config_folder(monkeypatch, tmp_path_factory):
    """!
    @brief Point the configuration folder to an empty temporary one, so a user's own defaults file never changes a test (and a test never writes into the real one).
    @param monkeypatch pytest fixture.
    @param tmp_path_factory pytest fixture.
    """
    folder = tmp_path_factory.mktemp("config")
    monkeypatch.setenv("PCBTHERMAL_CONFIG", str(folder))
    try:
        from pcbthermal import defaults, model
        defaults._CACHE.pop("stamp", None)
        model.reload_libraries()
    except ImportError:
        return
