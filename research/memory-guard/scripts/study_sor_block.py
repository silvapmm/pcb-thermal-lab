#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_sor_block.py
@brief Question: how much memory does the dense inverse of a via block of the block SOR take, and what limit by memory replaces fvm.MAX_SOR_BLOCK = 5000?
@details Run from the repository root with the program's environment:

             .venv/bin/python research/memory-guard/scripts/study_sor_block.py [--cutoff-gb 8]

         A 40 mm two-layer board carries a square array of 0.8 mm vias at 0.8 mm pitch over 20 mm, so the footprints touch and merge into one block of n unknowns
         (n = layers x cells under the array). For every cell size the child process builds the network and (a) stops (mode `build`) or (b) calls `Network.solve_sor` with
         max_iter = 1 (mode `sor`), so the cost of the block inverse is the difference of the two peaks (kernel high-water mark from `os.wait4`; bytes on macOS, kilobytes on
         Linux). MAX_SOR_BLOCK is raised in the child so that the block is not refused. The table printed gives n, the peaks, the difference and the ratio difference / (8 n^2).
         A child above the cutoff is killed by the parent (a poll of its resident size), so the machine does not page.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parents[1] / "out"


def child(cell_mm, mode):
    """!
    @brief Child process: build the board and (mode sor) run one SOR iteration; print a JSON line with the block size.
    @param cell_mm Cell in mm.
    @param mode "build" or "sor".
    @return None.
    """
    from pcbthermal import fvm, viawell
    from pcbthermal.model import Problem
    import numpy as np

    fvm.MAX_SOR_BLOCK = 10 ** 9                         # Never refuse in the study: the point is to measure the cost of a large block
    p = Problem.new(40.0, 40.0, layers=2, name="sor_block")
    p.board.h_top = p.board.h_bottom = 10.0
    p.add_full_copper()
    p.add_heater(1, 2.0, rect=(18.0, 18.0, 22.0, 22.0), name="U1")
    p.add_via_array((10.0, 10.0, 30.0, 30.0), 25, 25, diameter=0.8)
    nx = ny = int(round(40.0 / cell_mm))
    net = fvm.Network(p, nx, ny)
    idx3 = np.arange(net.nl * ny * nx).reshape(net.nl, ny, nx)
    blocks = viawell.unknown_blocks(net.via_blocks, idx3, net.n_board)
    nmax = max(len(b) for b in blocks)
    t0 = time.time()
    if mode == "sor":
        theta, res, info = net.solve_sor(max_iter=1)
    print(json.dumps({"n_block": int(nmax), "blocks": len(blocks), "unknowns": int(net.K.shape[0]), "t": time.time() - t0}))


def timed(cell_mm, mode, cutoff):
    """!
    @brief Run a child under `/usr/bin/time -l` (macOS: maximum resident set size in bytes) or `-v` (Linux: kilobytes) to read the kernel high-water mark.
    @param cell_mm Cell in mm.
    @param mode "build" or "sor".
    @param cutoff Kill threshold in bytes.
    @return Dict with n_block, peak_bytes, killed.
    """
    mac = sys.platform == "darwin"
    cmd = ["/usr/bin/time", "-l" if mac else "-v", sys.executable, str(Path(__file__).resolve()), "--child", str(cell_mm), mode]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(ROOT))
    killed = False
    while proc.poll() is None:
        # The resident size of the whole group: the child is a grandchild of this process, so ask ps for the largest rss of the group
        ps = subprocess.run(["ps", "-A", "-o", "ppid=,rss="], capture_output=True, text=True).stdout.split("\n")
        rss = max((int(l.split()[1]) * 1024 for l in ps if l.strip() and int(l.split()[0]) == proc.pid), default=0)
        if rss > cutoff:
            subprocess.run(["pkill", "-P", str(proc.pid)])
            killed = True
            break
        time.sleep(0.2)
    out, err = proc.communicate()
    peak = 0
    for line in err.splitlines():
        if "maximum resident set size" in line:
            v = int(line.split()[0]) if mac else int(line.split(":")[1]) * 1024
            peak = v
    rec = {"killed": killed, "peak_bytes": peak}
    if out.strip().startswith("{"):
        rec.update(json.loads(out.strip().splitlines()[-1]))
    return rec


def main():
    """!
    @brief Entry: the ladder of cell sizes, the table, and the file out/sor_block.json.
    @return None.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child(float(sys.argv[2]), sys.argv[3])
        return
    cutoff = 8e9
    if "--cutoff-gb" in sys.argv:
        cutoff = float(sys.argv[sys.argv.index("--cutoff-gb") + 1]) * 1e9
    OUT.mkdir(exist_ok=True)
    rows = []
    print(f"{'cell':>6} {'n_block':>8} {'peak build':>11} {'peak sor':>10} {'diff GB':>8} {'8 n^2 GB':>9} {'diff/(8n^2)':>11}")
    for cell in (1.0, 0.8, 0.6, 0.4, 0.35, 0.32, 0.3, 0.28, 0.26):
        a = timed(cell, "build", cutoff)
        b = timed(cell, "sor", cutoff)
        if a.get("killed") or b.get("killed") or "n_block" not in b:
            print(f"{cell:6.2f} killed or failed: {a} {b}")
            continue
        n = b["n_block"]
        diff = b["peak_bytes"] - a["peak_bytes"]
        rows.append({"cell_mm": cell, "n_block": n, "blocks": b["blocks"], "peak_build": a["peak_bytes"], "peak_sor": b["peak_bytes"], "diff": diff})
        print(f"{cell:6.2f} {n:8d} {a['peak_bytes'] / 1e9:11.2f} {b['peak_bytes'] / 1e9:10.2f} {diff / 1e9:8.2f} {8 * n * n / 1e9:9.2f} {diff / (8.0 * n * n):11.2f}")
    (OUT / "sor_block.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
