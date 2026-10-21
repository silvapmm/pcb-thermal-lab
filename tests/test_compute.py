"""!
@file test_compute.py
@brief The calculation process: results, errors, cancellation at once, jobs in order, and nothing left running after shutdown.
"""

import time

import pytest

from pcbthermal.gui import compute
from pcbthermal.gui.compute import ProcessWorker


@pytest.fixture(autouse=True)
def clean_engine():
    """!
    @brief Make sure every test starts and ends without a calculation process.
    """
    compute.shutdown()
    yield
    compute.shutdown()


def test_job_result_progress_and_error(qtbot):
    got, seen = [], []
    w = ProcessWorker("sleep", 0.3)
    w.done.connect(got.append)
    w.progress.connect(lambda m, f: seen.append(f))
    compute.start(w)
    assert w.isRunning()
    qtbot.waitUntil(lambda: bool(got), timeout=60000)
    assert got == [0.3] and seen and not w.isRunning()
    bad = ProcessWorker("simulate", None, None)                       # A job that raises: the message comes back, the process survives
    errors = []
    bad.failed.connect(errors.append)
    compute.start(bad)
    qtbot.waitUntil(lambda: bool(errors), timeout=60000)
    again = ProcessWorker("sleep", 0.1)
    out = []
    again.done.connect(out.append)
    compute.start(again)
    qtbot.waitUntil(lambda: bool(out), timeout=60000)


def test_cancel_running_job_is_immediate_and_the_next_job_still_runs(qtbot):
    long, short = ProcessWorker("sleep", 60.0), ProcessWorker("sleep", 0.1)
    flags, out = [], []
    long.cancelled.connect(lambda: flags.append("cancelled"))
    long.done.connect(lambda r: flags.append("done"))
    short.done.connect(out.append)
    compute.start(long)
    compute.start(short)                                             # Waits behind the long one
    qtbot.waitUntil(lambda: long.state == "running", timeout=60000)
    t0 = time.time()
    long.cancel()
    assert time.time() - t0 < 10 and flags == ["cancelled"] and not long.isRunning()
    qtbot.waitUntil(lambda: bool(out), timeout=60000)                # A fresh process serves the queued job
    assert flags == ["cancelled"]


def test_shutdown_leaves_no_process(qtbot):
    w = ProcessWorker("sleep", 60.0)
    compute.start(w)
    qtbot.waitUntil(lambda: w.state == "running", timeout=60000)
    proc = compute.ENGINE.process
    assert proc is not None and proc.is_alive()
    compute.shutdown()
    assert not proc.is_alive() and compute.ENGINE.process is None and not w.isRunning()
