"""!
@file compute.py
@brief Rules for the background calculations of the application: one at a time, and never destroyed while running.
@details * The sparse direct solver of SciPy (SuperLU) must not run in two threads at the same time: the stress test of the
           application aborted the whole process when a simulation was started while an animation or an analysis was still
           computing. Every worker takes LOCK for the whole of its calculation, so a second job simply waits for the first.
         * Qt aborts the process if a QThread object is destroyed while its thread runs (for example when a window closes
           during an analysis). Workers are therefore started with start() below: they have no Qt parent and stay referenced
           until they finish.
"""

import threading

LOCK = threading.Lock()
ACTIVE = set()                                   # Running workers, kept alive until they finish


def start(worker):
    """!
    @brief Start a worker thread and keep it alive until it has finished.
    @param worker A QThread created without a parent.
    @return The same worker.
    """
    ACTIVE.add(worker)
    worker.finished.connect(lambda w=worker: ACTIVE.discard(w))
    worker.start()
    return worker


def wait_all(milliseconds=30000):
    """!
    @brief Wait for every running worker (used when the application closes).
    @param milliseconds Longest wait for each worker.
    """
    for worker in list(ACTIVE):
        worker.wait(milliseconds)
