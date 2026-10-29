#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_orphan.py
@brief The calculation process stops by itself when the application dies without a clean shutdown.
"""

import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APP = """
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, {root!r})
from PySide6.QtWidgets import QApplication
app = QApplication([])
from pcbthermal.gui.compute import ProcessWorker, ENGINE
w = ProcessWorker("sleep", 100.0)
w.start()
while ENGINE.process is None or not ENGINE.process.is_alive() or w.state != "running":
    app.processEvents()
print(ENGINE.process.pid, flush=True)
os.kill(os.getpid(), 9)                         # The application dies at once: no shutdown, no atexit
"""


def alive(pid):
    """!
    @brief True if the process exists and is not a zombie.
    @param pid Process id.
    @return bool.
    """
    try:
        return open(f"/proc/{pid}/stat").read().split()[2] != "Z"
    except OSError:
        return False


def test_calculation_process_exits_when_the_application_is_killed():
    out = subprocess.run([sys.executable, "-c", APP.format(root=ROOT)], capture_output=True, text=True, timeout=120)
    pid = int(out.stdout.split()[-1])
    deadline = time.time() + 20
    while alive(pid) and time.time() < deadline:
        time.sleep(0.5)
    assert not alive(pid), "the calculation process outlived the application"
