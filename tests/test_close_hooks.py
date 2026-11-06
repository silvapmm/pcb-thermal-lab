#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_close_hooks.py
@brief The before-close hook of the import window (`ImportBoardWindow.before_close`) and the before-release hook of the session (`ImportSession.before_release`): they run once, in
       order, an exception in one does not stop the next one or the release, none runs while a call is busy (it runs once after), the "new files" hooks run in the GUI thread before the
       worker starts, two features register without replacing each other, and the package capture reads a ZIP before the archive is released.
"""

import os
import threading
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QDialog

from pcbthermal.gui.import_session import ImportSession
from pcbthermal.gui.import_window import ImportBoardWindow
from tests.helpers.synthetic_board import make_board


@pytest.fixture
def window(qtbot, tmp_path):
    """!
    @brief An import window on the synthetic set.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return ImportBoardWindow
    """
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    w.confirm = lambda title, text: True
    w.notify = lambda title, text: None
    w.open_path(str(make_board(tmp_path / "fab", inner=0)))
    return w


def test_before_close_runs_once_in_order_on_accept(window):
    calls = []
    window.before_close.append(lambda w, r: calls.append(("a", r, w is window, bool(w.session.files))))
    window.before_close.append(lambda w, r: calls.append(("b", r, w is window, bool(w.session.files))))
    window.accept()
    # The session still holds its files when the hooks run (they are released afterwards)
    assert calls == [("a", QDialog.Accepted, True, True), ("b", QDialog.Accepted, True, True)]
    window.done(QDialog.Rejected)
    assert len(calls) == 2                                              # a second done() runs nothing again
    assert window.session.files                                         # nothing here cleared the file list; only the archive and the caches are released


def test_before_close_runs_on_cancel_too(window):
    calls = []
    window.before_close.append(lambda w, r: calls.append(r))
    window.close_btn.click()
    assert calls == [QDialog.Rejected]


def test_an_exception_in_a_hook_stops_neither_the_next_hook_nor_the_release(window, caplog):
    calls = []

    def bad(w, r):
        raise RuntimeError("boom")
    window.before_close.append(bad)
    window.before_close.append(lambda w, r: calls.append("second"))
    window.session.before_release.append(lambda s, reason: 1 / 0)
    window.session.before_release.append(lambda s, reason: calls.append(("release", reason)))
    with caplog.at_level("ERROR"):
        window.accept()
    assert calls == ["second", ("release", "close")]
    assert not window.isVisible()
    assert "boom" in caplog.text and "ZeroDivisionError" in caplog.text


def test_no_hook_runs_while_a_call_is_busy_and_it_runs_once_after(window):
    calls = []
    window.before_close.append(lambda w, r: calls.append(r))
    window._busy = True
    window.accept()
    window.reject()
    assert calls == [] and window._close_asked
    window._busy = False
    window.done(QDialog.Rejected)
    assert calls == [QDialog.Rejected]


def test_session_hooks_get_the_reason_and_run_once(tmp_path):
    folder = make_board(tmp_path / "fab", inner=0)
    s = ImportSession()
    seen = []
    s.before_release.append(lambda sx, reason: seen.append(reason))
    s.set_files(folder)                                                 # a first set: nothing to release yet, but the hook still runs (the set is replaced)
    assert seen == ["new_files"]
    s.before_release.append(lambda sx, reason: seen.append(reason))
    s.set_files(folder)
    s.before_release.append(lambda sx, reason: seen.append(reason))
    s.close()
    s.close()                                                           # idempotent: the hooks of a release run once
    assert seen == ["new_files", "new_files", "close"]


def test_new_files_hooks_run_in_the_gui_thread_before_the_worker(window, tmp_path):
    main = threading.get_ident()
    seen = []
    window.session.before_release.append(lambda s, reason: seen.append((reason, threading.get_ident() == main)))
    window.open_path(str(make_board(tmp_path / "fab2", inner=0)))
    assert seen == [("new_files", True)]


def test_two_features_register_without_replacing_each_other(window, tmp_path):
    from pcbthermal.gui import package_actions as pa
    cap = pa.capture_on_close(window)
    other = []
    window.before_close.append(lambda w, r: other.append(r))
    window.session.before_release.append(lambda s, reason: other.append(reason))
    window.record = object()
    window.accept()
    assert cap.files and other == [QDialog.Accepted, "close"]


def test_the_package_capture_reads_a_zip_before_the_archive_is_released(qtbot, tmp_path):
    from pcbthermal.gui import package_actions as pa
    folder = make_board(tmp_path / "fab", inner=0)
    zp = tmp_path / "set.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        for f in sorted(folder.iterdir()):
            zf.write(f, f.name)
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    w.open_path(str(zp))
    cap = pa.capture_on_close(w)
    w.record = object()
    w.accept()
    assert {n for n, *_ in cap.files} == {f.name for f in folder.iterdir()}
    # Without the hook the archive is gone before anything reads it
    w2 = ImportBoardWindow()
    qtbot.addWidget(w2)
    w2.show()
    w2.open_path(str(zp))
    w2.record = object()
    w2.accept()
    files, notes = pa.session_files(w2.session)
    assert files == [] and notes
