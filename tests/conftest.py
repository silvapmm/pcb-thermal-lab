#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
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
# The memory guard refuses by a share of the physical memory, so the same test would solve a million 3D unknowns on a 64 GB machine and refuse them on
# 16 GB: the battery runs as on a 16 GB machine (set before any calculation process is spawned, which inherits it; memory.MEMORY_ENV)
os.environ.setdefault("PCBTHERMAL_MEMORY_BYTES", str(16 * 10 ** 9))


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


@pytest.fixture(autouse=True)
def _private_window_settings(monkeypatch, tmp_path):
    """!
    @brief Give every MainWindow built without its own settings a private, empty settings file.
    The default `QSettings("PMS Labs", "PCB Thermal Lab")` is the user's real preference store: a window closed by one test saved its geometry and dock state there and the next
    test restored them (docks closed or narrow), so a layout test passed alone and failed after other tests (the Profiles cut-overlay test, 2 of 3 batteries; reproduced
    by the review with a scratch store holding a closed dock: `-1 >= 0` every time), and the battery wrote the theme and the box states into the user's own preferences.
    Only the module `main_window` is patched (the one place of the program that builds the default store); a window given its own settings is untouched, and two
    windows of the same test share the private file, so persistence between windows is still tested.
    @param monkeypatch pytest fixture.
    @param tmp_path pytest fixture (one folder per test).
    """
    try:
        from PySide6.QtCore import QSettings
        from pcbthermal.gui import boxes, main_window
    except ImportError:                                   # Physics-only environment
        return
    # The open or collapsed state of the boxes is a module-level store bound by the last MainWindow: without this a panel built alone in a later test read the
    # box states of the window of an earlier test (before the redirect, the user's real store)
    monkeypatch.setattr(boxes, "_settings", None)
    monkeypatch.setattr(boxes, "_memory", {})
    ini = str(tmp_path / "window_default.ini")

    def private(*args):
        # Only the organisation/application form is redirected; a path or an explicit format keeps its meaning
        if len(args) == 2 and all(isinstance(a, str) for a in args):
            return QSettings(ini, QSettings.IniFormat)
        return QSettings(*args)

    monkeypatch.setattr(main_window, "QSettings", private)
