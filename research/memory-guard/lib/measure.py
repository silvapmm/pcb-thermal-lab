#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file measure.py
@brief Run one case in its own child process and record its peak resident memory, with a watchdog that kills the child above a cutoff so the study cannot freeze the machine.
@details tracemalloc and the Python allocator do not see the memory SciPy's SuperLU and NumPy allocate in C, so the peak is the kernel's: os.wait4 returns the resource usage of exactly
         that child (ru_maxrss: bytes on macOS, kilobytes on Linux). While the child runs the parent samples its resident size every 0.25 s with `ps -o rss=` (macOS and Linux)
         and kills it above `kill_bytes`. Windows has no ps or wait4: the wrapper is for macOS and Linux, the platform of the study (stated in README).
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHILD = HERE.parent / "scripts" / "_measure_child.py"
MAXRSS_UNIT = 1 if sys.platform == "darwin" else 1024          # ru_maxrss is in bytes on macOS, in kilobytes on Linux


def _rss_now(pid):
    """!
    @brief Resident size of a process now, in bytes (0 when it cannot be read).
    @param pid Process id.
    @return int bytes.
    """
    try:
        out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, timeout=2).stdout.strip()
        return int(out) * 1024 if out else 0
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def run_case(spec, kill_bytes, timeout_s=900.0, python=None, child=None):
    """!
    @brief Run a case in a subprocess and return what it printed together with the peak memory seen by the kernel.
    @param spec Case spec (dict, see cases.py) plus the optional keys "mode" ("solve" or "compare") and "order" ("layer" or "cell").
    @param kill_bytes Resident size above which the child is killed (the safety cutoff).
    @param timeout_s Wall-clock limit in seconds; the child is killed after it.
    @param python Interpreter of the child (default: the interpreter running this).
    @param child Path of the child script (default: scripts/_measure_child.py).
    @return Dict with the child's keys plus peak_bytes, wall_s and status ("ok", "killed_memory", "killed_time", "error").
    """
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as out, tempfile.NamedTemporaryFile("w+", suffix=".err", delete=False) as err:
        out_path, err_path = out.name, err.name
    t0 = time.perf_counter()
    proc = subprocess.Popen([python or sys.executable, str(child or CHILD), json.dumps(spec), out_path], stdout=subprocess.DEVNULL, stderr=open(err_path, "w"))
    status, rusage, peak_seen = "ok", None, 0
    while True:
        pid, st, ru = os.wait4(proc.pid, os.WNOHANG)           # Reaps the child and returns its own resource usage (not poll(): that would discard it)
        if pid:
            rusage = ru
            if st != 0 and status == "ok":
                status = "error"
            break
        peak_seen = max(peak_seen, _rss_now(proc.pid))
        if peak_seen > kill_bytes:
            proc.kill()
            status = "killed_memory"
        elif time.perf_counter() - t0 > timeout_s:
            proc.kill()
            status = "killed_time"
        time.sleep(0.25)
    res = {}
    try:
        with open(out_path) as fh:
            res = json.load(fh)
    except (OSError, ValueError):
        if status == "ok":
            status = "error"
    try:
        res["stderr"] = Path(err_path).read_text()[-500:]
    finally:
        for pth in (out_path, err_path):
            try:
                os.unlink(pth)
            except OSError:
                pass
    res.update(spec=spec, status=status, wall_s=time.perf_counter() - t0, peak_bytes=int(rusage.ru_maxrss * MAXRSS_UNIT) if rusage else peak_seen,
               peak_sampled_bytes=peak_seen)
    return res
