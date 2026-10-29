#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file compute.py
@brief Background calculations of the application: one separate process, one job at a time, cancellable and never left running.
@details The calculations (simulation, animation, power-profile analysis) run in a worker process (pcbthermal/jobs.py) started with the "spawn"
         method, instead of threads in the window's process:
         * a job can be **cancelled** at any moment (the process is stopped and a new one starts on the next job), which a thread cannot do
           inside a sparse factorisation;
         * the window never freezes, and the SuperLU rule (never two solves in the same process at once) holds because the process runs jobs in order;
         * when the application closes the process is stopped, so nothing keeps running (shutdown()).
         The process is created at the first job and kept for the next ones (importing SciPy takes a second).
"""

import itertools
import multiprocessing
import queue
from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal

from .. import jobs

_CTX = multiprocessing.get_context("spawn")
_IDS = itertools.count(1)


class Engine:
    """!
    @brief The worker process and the queue of jobs waiting for it.
    """

    def __init__(self):
        """!
        @brief Create an idle engine (the process starts with the first job).
        """
        self.process, self.tasks, self.results = None, None, None
        self.pending = deque()                       # Jobs submitted and not yet sent to the process
        self.current = None                          # Job being executed
        self.known = {}                              # Job id -> ProcessWorker for every job not finished
        self.timer = None

    def _spawn(self):
        """!
        @brief Start the worker process.
        """
        self.tasks, self.results = _CTX.Queue(), _CTX.Queue()
        self.process = _CTX.Process(target=jobs.serve, args=(self.tasks, self.results), daemon=True)
        self.process.start()

    def _stop(self):
        """!
        @brief Stop the worker process at once (a running job is lost).
        """
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(5)
            if self.process.is_alive():
                # A process that did not end on SIGTERM in 5 s (paged out by a large solve, or a handler) is killed, so its memory is freed
                self.process.kill()
                self.process.join(5)
            for q in (self.tasks, self.results):
                q.close()
                q.cancel_join_thread()
        self.process, self.tasks, self.results, self.current = None, None, None, None

    def submit(self, worker):
        """!
        @brief Queue a job; it starts when the previous ones are done.
        @param worker A ProcessWorker.
        """
        worker.job_id = next(_IDS)
        self.known[worker.job_id] = worker
        self.pending.append(worker)
        if self.timer is None:
            self.timer = QTimer()
            self.timer.setInterval(20)
            self.timer.timeout.connect(self.poll)
        if not self.timer.isActive():
            self.timer.start()
        self._feed()

    def _feed(self):
        """!
        @brief Send the next waiting job to the process when it is free.
        """
        if self.current is not None or not self.pending:
            return
        if self.process is None:
            self._spawn()
        self.current = self.pending.popleft()
        self.current.state = "running"
        self.tasks.put((self.current.job_id, self.current.name, self.current.args))

    def poll(self):
        """!
        @brief Deliver the messages of the process to their workers and detect a process that died.
        """
        while self.results is not None:
            try:
                job_id, kind, payload = self.results.get_nowait()
            except (queue.Empty, OSError, ValueError):
                break
            worker = self.known.get(job_id)
            if worker is None:
                continue                              # A cancelled job still sending messages
            if kind == "progress":
                worker.progress.emit(*payload)
                continue
            self._finish(worker, kind, payload)
        if self.current is not None and self.process is not None and not self.process.is_alive():
            self._finish(self.current, "failed", "the calculation process stopped unexpectedly")
            self._stop()
            self._feed()
        if self.current is None and not self.pending and self.timer is not None:
            self.timer.stop()

    def _finish(self, worker, kind, payload):
        """!
        @brief A job ended: free the process for the next one and tell the worker.
        @param worker The ProcessWorker.
        @param kind "done" or "failed".
        @param payload Result or error text.
        """
        self.known.pop(worker.job_id, None)
        if self.current is worker:
            self.current = None
        worker.state = "finished"
        (worker.done if kind == "done" else worker.failed).emit(payload)
        worker.finished.emit()
        self._feed()

    def cancel(self, worker):
        """!
        @brief Cancel a queued or running job.
        @param worker A ProcessWorker.
        """
        if worker.state == "finished":
            return
        was_running = self.current is worker
        self.known.pop(worker.job_id, None)
        if worker in self.pending:
            self.pending.remove(worker)
        worker.state = "finished"
        if was_running:
            self._stop()                              # The only way to interrupt a sparse solve
        worker.cancelled.emit()
        worker.finished.emit()
        self._feed()

    def shutdown(self):
        """!
        @brief Cancel everything and stop the process (the application is closing).
        """
        for worker in list(self.known.values()):
            worker.state = "finished"
        self.known.clear()
        self.pending.clear()
        self._stop()
        if self.timer is not None:
            self.timer.stop()


ENGINE = Engine()


class ProcessWorker(QObject):
    """!
    @brief Handle of one job in the worker process; replaces a QThread with a cancel().
    @details Signals: progress(message, fraction), done(result), failed(message), cancelled(), finished() after any of them.
    """

    progress = Signal(str, float)
    done = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, name, *args, parent=None):
        """!
        @param name Job name in pcbthermal.jobs.JOBS.
        @param args Arguments of the job (pickled; pass private copies).
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.name, self.args, self.job_id, self.state = name, args, 0, "new"

    def start(self):
        """!
        @brief Queue the job.
        """
        self.state = "queued"
        ENGINE.submit(self)

    def cancel(self):
        """!
        @brief Cancel the job (stops the process when it is running).
        """
        ENGINE.cancel(self)

    def isRunning(self):
        """!
        @brief True from start() until the job ends or is cancelled.
        @return bool.
        """
        return self.state in ("queued", "running")


def start(worker):
    """!
    @brief Start a job.
    @param worker A ProcessWorker.
    @return The same worker.
    """
    worker.start()
    return worker


def shutdown():
    """!
    @brief Stop the calculation process (used when the application closes).
    """
    ENGINE.shutdown()
