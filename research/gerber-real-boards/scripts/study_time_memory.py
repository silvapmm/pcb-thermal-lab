#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_time_memory.py
@brief Time and memory of a full real board imported at 1.0, 0.5 and 0.25 mm cells, phase by phase, and the memory per unknown with the laminate nodes of 2.4.5, to feed the memory guard.
@details Each case (board, cell) is run in a FRESH child process of this script so that the peak resident size is the peak of that case. A case: import (masks at pixel = cell / 10, coverage), the program's Problem,
         the flow-based faces of every copper layer, the face network (research/gerber-models faces.FaceNetwork, ladder off), the steady direct solve. Recorded after each phase: seconds, the peak resident size so
         far, the number of unknowns of the network, the matrix size (non-zeros) and, for the program's own count with the laminate rule, `fvm.unknowns(problem, cell)` on the same Problem (the program's path would
         add laminate nodes only in cells with absent copper: the count is what the memory guard sees). Older coefficients to compare with (research/solid3d-verification/docs/for-the-project-documents.md):
         2.8 KB per unknown for the layered FVM on a plain board (2.7 GB at 992 000 unknowns), the 7 GB per million measured on refined boards by the maintainer, 6.6 KB (plain) to 14.3 to 19.3 KB (example board) for the 3D solid.
         Output: out/time_memory.json with every case and the fit (bytes per unknown through the origin, scatter) printed.
         Success criterion (before the run): a single coefficient with at most 25 % scatter over the cases, so that the guard can use `baseline + unknowns * coefficient`; otherwise the guard needs the structure (layers, nnz).
         NOT verified: the effect of memory pressure (a case that pages is flagged by the resident size close to the physical memory), other machines, the 3D solid on an imported board, the program's GUI process on top.
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/study_time_memory.py [--cells 1.0 0.5 0.25] [--boards isastm cmm2] [--max-gb 12]
         A case whose peak resident size exceeds --max-gb is flagged (it may have paged; its time is then not trusted). Child mode (used by the parent): --case <board> <cell>. Do not run it while another heavy job is running: the times would be wrong.
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import subprocess
import sys
import time

import memory_model as mm
import rb_paths
import registry


def run_case(key, cell):
    """!
    @brief Run one case in this process and return its record.
    @param key Board key.
    @param cell Cell (mm).
    @return dict with the phases, unknown counts and peak sizes.
    """
    import boardrun
    import faces as im
    from pcbthermal import fvm
    rec = {"board": key, "cell": cell, "pix": cell / 10.0, "phases": []}
    rec["baseline_bytes"] = mm.peak_rss_bytes()

    def mark(name, t0):
        """!@brief Record a phase. @param name Phase name. @param t0 Start time. @return None."""
        rec["phases"].append({"name": name, "seconds": time.time() - t0, "peak_bytes": mm.peak_rss_bytes()})

    t = time.time()
    ib = boardrun.import_window(key, None, cell / 10.0, cell, supersample=2)
    mark("import", t)
    rec.update(width=ib.width, height=ib.height, layers=len(ib.layers), holes=len(ib.holes), warnings=ib.warnings)
    p = boardrun.make_problem(ib, (ib.width / 2.0, ib.height / 2.0), 6.0)
    nx, ny = int(round(ib.width / cell)), int(round(ib.height / cell))
    rec["unknowns_faces"] = len(ib.layers) * nx * ny
    try:
        rec["unknowns_program"] = int(fvm.unknowns(p, cell)[0])           # the program's own count with the laminate rule (ragged), for the guard
    except Exception as exc:
        rec["unknowns_program"] = None
        rec["unknowns_program_error"] = str(exc)
    t = time.time()
    sheets = im.layer_sheets(ib, p, "coverage")
    faces = im.layer_faces(sheets, ib, p, "flow")
    del sheets
    mark("faces", t)
    t = time.time()
    net = im.FaceNetwork(p, nx, ny, assemble=False, ladder=False)
    net.set_faces(faces)
    mark("assemble", t)
    rec["nnz"] = int(net.K.nnz)
    t = time.time()
    theta = net.solve_steady()[0]
    mark("solve", t)
    rec["max_rise_K"] = float(theta.max())
    return rec


def parent(cells, boards, max_gb):
    """!
    @brief Run every case in a child process and fit the memory per unknown.
    @param cells Cell sizes (mm).
    @param boards Board keys.
    @param max_gb Skip a case whose estimate (7 KB per unknown) is above this many GB.
    @return None (prints and writes out/time_memory.json).
    """
    import numpy as np
    results = []
    for key in boards:
        if key not in registry.available():
            print(f"{key}: not in data/, skipped")
            continue
        for c in cells:
            cmd = [sys.executable, str(__file__), "--case", key, str(c)]
            print("running", " ".join(cmd[1:]), flush=True)
            out = subprocess.run(cmd, capture_output=True, text=True)
            lines = [ln for ln in out.stdout.splitlines() if ln.startswith("{")]
            if out.returncode != 0 or not lines:
                print(f"  failed ({out.returncode}): {out.stderr.strip()[-300:]}")
                continue
            rec = json.loads(lines[-1])
            gb = rec["phases"][-1]["peak_bytes"] / 1e9
            print(f"  {rec['width']:.0f} x {rec['height']:.0f} mm, {rec['layers']} layers, {rec['unknowns_faces']} unknowns (program count {rec['unknowns_program']}), "
                  + ", ".join(f"{p['name']} {p['seconds']:.0f} s" for p in rec["phases"]) + f", peak {gb:.1f} GB", flush=True)
            if gb > max_gb:
                print(f"  note: peak above --max-gb {max_gb}: the machine may have paged, treat the time with care")
            results.append(rec)
    fit = None
    if results:
        u = np.array([r["unknowns_faces"] for r in results], float)
        pk = np.array([r["phases"][-1]["peak_bytes"] for r in results], float)
        base = float(np.median([r["baseline_bytes"] for r in results]))
        fit = mm.fit_bytes_per_unknown(u, pk, base)
        print(f"\nmemory per unknown (through the origin, baseline {base / 1e6:.0f} MB removed): {fit['bytes_per_unknown'] / 1e3:.2f} KB, largest deviation {100 * fit['max_relative_deviation']:.0f} % over {fit['n']} cases")
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    with open(rb_paths.OUT / "time_memory.json", "w") as fh:
        json.dump({"cases": results, "fit": fit}, fh, indent=1)


def main(argv):
    """!
    @brief Parent or child entry.
    @param argv Command-line words.
    @return None.
    """
    if argv and argv[0] == "--case":
        print(json.dumps(run_case(argv[1], float(argv[2]))))
        return
    def values(flag, default):
        """!@brief The words after a flag up to the next flag. @param flag Flag. @param default Value when absent. @return list of str."""
        if flag not in argv:
            return default
        out = []
        for w in argv[argv.index(flag) + 1:]:
            if w.startswith("--"):
                break
            out.append(w)
        return out

    cells = [float(x) for x in values("--cells", ["1.0", "0.5", "0.25"])]
    boards = values("--boards", ["isastm", "cmm2", "oswlight"])
    max_gb = float(values("--max-gb", ["12"])[0])
    parent(cells, boards, max_gb)


if __name__ == "__main__":
    main(sys.argv[1:])
