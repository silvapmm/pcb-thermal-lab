#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file compat_run.py
@brief Question: what did an OLD release of the program (v2.0.0 to v2.3.0, which lack the outline, the parts and other later APIs) give on the regression boards? Runs a tag with the same result-set format as `study_run_suite.py`, and records what the tag cannot do instead of stopping.
@details Usage, from the repository root:

         .venv/bin/python releases/regression-harness/scripts/compat_run.py --tag v2.0.0 --label v2.0.0 [--quick] [--dest DIR] [--reuse-dest]
         .venv/bin/python releases/regression-harness/scripts/compat_run.py --program-root /path/to/tree --label develop     # a tree instead of a tag

         `lib/` (byte-compared with `tests/regression/`) is not changed: this script imports the harness and replaces three of its functions in memory (`features`, `steady_problem`,
         `build`) by versions that do not assume the newest API. A board that the tag cannot build (an API it does not have: `set_outline`, a part with theta, a metal block ...)
         is stored with status `not_available` and the exception text as the reason, for every model and cell; a model the tag does not have (`fdm`, `solid3d`) is stored as `error` with
         the exception text by `run_one`; nothing is skipped silently. The example boards are read from the CURRENT tree (the same input for every tag): a tag that does not know a field of
         the file ignores it, which `features` shows (counts of vias, parts, blocks, outline) so that the reader can see what the tag really solved.
         The output is `out/<label>.json`, git-ignored.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(HERE))


def compat_features(problem):
    """!
    @brief Facts about a built problem, without assuming the newest API.
    @param problem A Problem of any release.
    @return dict with layers, vias, outline, heaters, blocks, profiles, ambient and size_mm (a missing attribute gives False or None).
    """
    b = problem.board
    has_outline = getattr(b, "has_outline", None)
    return {"layers": int(b.layers), "vias": len(problem.vias), "outline": bool(has_outline()) if has_outline else False, "heaters": len(problem.heaters),
            "blocks": sum(1 for h in getattr(problem, "heatsinks", []) if getattr(h, "thickness", 0) > 0),
            "heatsinks": len(getattr(problem, "heatsinks", getattr(problem, "sinks", []))),
            "profiles": bool(problem.has_profiles()) if hasattr(problem, "has_profiles") else False, "ambient": float(b.ambient),
            "size_mm": [round(b.width * 1000.0, 3), round(b.height * 1000.0, 3)]}


def compat_load_example(name, examples_dir):
    """!
    @brief Load an example file with a release that stores heatsinks under the old key `sinks` (before 2.3.0 renamed it `heatsinks`).
    @param name File stem, for example "example_board".
    @param examples_dir Folder with the `.pcbt.json` files.
    @return Problem. Without this, a release before 2.3.0 silently drops the heatsink of the example boards (found by comparing v2.2.0 with v2.3.0: -3.1 K that was the missing heatsink, not the model).
    """
    import tempfile
    from pcbthermal import model
    path = Path(examples_dir) / f"{name}.pcbt.json"
    problem = model.load_problem(str(path))
    if hasattr(problem, "heatsinks"):                                          # 2.3.0 and later read the file as it is
        return problem
    data = json.loads(path.read_text(encoding="utf-8"))
    if "heatsinks" in data and "sinks" not in data:
        data["sinks"] = data.pop("heatsinks")
        tmp = Path(tempfile.mkdtemp(prefix="pcbt_compat_ex_")) / f"{name}.pcbt.json"
        tmp.write_text(json.dumps(data), encoding="utf-8")
        problem = model.load_problem(str(tmp))
    return problem


def compat_steady_problem(problem):
    """!
    @brief Copy of a problem with every part at its average power and no profile, for releases without profiles.
    @param problem A Problem of any release.
    @return A new Problem.
    """
    import copy
    p = copy.deepcopy(problem)
    for h in p.heaters:
        if hasattr(h, "average_power"):
            h.power = h.average_power()
        if hasattr(h, "profile"):
            h.profile = None
    return p


def compat_blocks(sim, model, problem):
    """!
    @brief Temperature of the metal blocks, or None for releases without blocks.
    @param sim Simulation.
    @param model Model key.
    @param problem The Problem that was solved.
    @return list of dicts or None.
    """
    try:
        from pcbthermal.analysis import block_stats
    except ImportError:                                                       # the release has no metal blocks
        return None
    if model not in ("fvm", "fdm"):
        return None
    try:
        return [{"name": r.get("name"), "face": r.get("face"), "t_mean": r.get("t_mean"), "t_max": r.get("t_max"), "w_to_block": r.get("w_to_block")} for r in block_stats(sim.results[model], problem)]
    except Exception:
        return None


def mark_missing_model(rec):
    """!
    @brief Turn the refusal of an unknown model into status `not_available` with a plain reason.
    @param rec A record of the run.
    @return The same record.
    """
    if rec.get("status") == "error" and "models must be a non-empty subset" in rec.get("reason", ""):
        rec["status"], rec["reason"] = "not_available", f"model '{rec['model']}' does not exist in this release"
    return rec


def run_compat_suite(program_root, out_path, label, boards, models, cells, log=print):
    """!
    @brief Run the suite on one tree, tolerating the missing APIs of old releases.
    @param program_root Folder with the `pcbthermal` package.
    @param out_path Output JSON.
    @param label Name of the result set.
    @param boards Board names.
    @param models Model keys.
    @param cells Cell sizes in mm.
    @param log Function that takes one line of text.
    @return The result set (dict).
    """
    import platform
    import regress_boards as B
    import regress_harness as H
    mod = H.use_program(program_root)
    import numpy
    import scipy
    H.steady_problem = compat_steady_problem
    H._blocks = compat_blocks
    B.features = compat_features
    B.load_example = compat_load_example
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = {"format": H.FORMAT, "label": label, "program": {"root": str(Path(program_root).resolve()), "version": mod.__version__},
            "environment": {"python": sys.version.split()[0], "numpy": numpy.__version__, "scipy": scipy.__version__, "platform": platform.platform(), "machine": platform.machine()},
            "settings": {"models": list(models), "cells": list(cells), "max_unknowns": H.MAX_UNKNOWNS, "solid_cap": H.SOLID_CAP, "transient_cell": H.TRANSIENT_CELL,
                         "sor_boards": list(H.SOR_BOARDS), "sor_cell": H.SOR_CELL, "examples_dir": str(B.REPO / "examples"), "compat": True},
            "boards": {}, "records": [], "transients": [], "sor": [], "done": []}
    for name in boards:
        try:
            problem = B.build(name)
            feat = B.features(problem)
        except Exception as exc:                                              # the tag lacks an API this board needs: said, not skipped
            reason = f"{type(exc).__name__}: {exc}"
            data["boards"][name] = {"description": B.DESCRIPTIONS.get(name, ""), "not_available": reason}
            for model in models:
                for cell in cells:
                    data["records"].append({"board": name, "model": model, "cell_mm": cell, "solver": "direct", "status": "not_available", "reason": reason, "unknowns": None})
            log(f"{name:22s} NOT AVAILABLE in this release: {reason[:100]}")
            data["done"].append(name)
            out_path.write_text(json.dumps(data, indent=1), encoding="utf-8")
            continue
        feat["description"] = B.DESCRIPTIONS.get(name, "")
        feat["reference"] = name in B.REFERENCE_SPECS
        data["boards"][name] = feat
        for model in models:
            for cell in cells:
                try:
                    rec = H.run_one(problem, name, model, cell)
                except Exception as exc:                                      # anything the harness did not anticipate in an old release
                    rec = {"board": name, "model": model, "cell_mm": cell, "solver": "direct", "status": "error", "reason": f"{type(exc).__name__}: {exc}", "unknowns": None}
                data["records"].append(mark_missing_model(rec))
                log(f"{name:22s} {model:8s} {cell:4.2f} mm  {rec['status']:7s} " + (f"Tmax {rec['t_max']:8.3f}  {rec['seconds']:6.1f} s" if rec["status"] == "ok" else rec["reason"][:90]))
        if problem.heaters:
            for model in ("fvm", "fdm", "lumped", "analytic"):
                if model in models:
                    # a release without the model must not get a step response: v2.1.0's step_response falls back to the analytic branch for an unknown key
                    if any(r["board"] == name and r["model"] == model and r["status"] == "not_available" for r in data["records"]):
                        data["transients"].append({"board": name, "model": model, "cell_mm": H.TRANSIENT_CELL, "status": "not_available", "reason": "model does not exist in this release", "parts": []})
                        continue
                    try:
                        tr = H.t63(problem, model)
                    except Exception as exc:
                        tr = {"model": model, "cell_mm": H.TRANSIENT_CELL, "status": "error", "reason": f"{type(exc).__name__}: {exc}", "parts": []}
                    tr["board"] = name
                    data["transients"].append(tr)
        # v2.2.0 answers a step response of the steady-only FDM with the analytic one (identical numbers to the last digit): that is not an FDM result
        fd = next((t for t in data["transients"] if t["board"] == name and t["model"] == "fdm" and t["status"] == "ok"), None)
        an = next((t for t in data["transients"] if t["board"] == name and t["model"] == "analytic" and t["status"] == "ok"), None)
        if fd and an and [q["t63_s"] for q in fd["parts"]] == [q["t63_s"] for q in an["parts"]]:
            fd.update(status="not_available", reason="this release answers the FDM step response with the analytic one (identical numbers)", parts=[])
        if name in H.SOR_BOARDS and "fvm" in models:
            try:
                data["sor"].append(H.run_one(problem, name, "fvm", H.SOR_CELL, linear_solver="sor"))
            except Exception as exc:
                data["sor"].append({"board": name, "model": "fvm", "cell_mm": H.SOR_CELL, "solver": "sor", "status": "error", "reason": f"{type(exc).__name__}: {exc}", "unknowns": None})
        data["done"].append(name)
        out_path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data


def main(argv=None):
    """!
    @brief Extract a tag (parent) and run the suite in a child process, or run it on a given tree (child).
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--tag", default=None, help="git tag to extract with git archive and run")
    ap.add_argument("--program-root", default=None, help="a tree that holds the pcbthermal package (instead of --tag)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--dest", default=None, help="scratch folder outside the repository for the extracted tag")
    ap.add_argument("--reuse-dest", action="store_true")
    ap.add_argument("--quick", action="store_true", help="2 mm cell only")
    ap.add_argument("--cells", nargs="+", type=float, default=None)
    ap.add_argument("--models", nargs="+", default=None)
    ap.add_argument("--boards", nargs="+", default=None)
    a = ap.parse_args(argv)
    import regress_boards as B
    import regress_harness as H
    cells = tuple(a.cells) if a.cells else ((2.0,) if a.quick else H.CELLS)
    if a.tag and not a.program_root:
        import tempfile
        import study_baseline_release as SB
        dest = Path(a.dest) if a.dest else Path(tempfile.mkdtemp(prefix="pcbt_compat_"))
        if not a.reuse_dest:
            SB.extract(a.tag, dest)
        cmd = [sys.executable, str(HERE / "compat_run.py"), "--program-root", str(dest.resolve()), "--label", a.label or a.tag] + \
              (["--cells"] + [str(c) for c in cells]) + (["--boards"] + a.boards if a.boards else []) + (["--models"] + a.models if a.models else [])
        t0 = time.time()
        rc = subprocess.run(cmd, cwd=str(dest.resolve())).returncode
        print(f"{a.tag}: {time.time() - t0:.0f} s, exit code {rc}")
        return rc
    data = run_compat_suite(a.program_root or str(B.REPO), ROOT / "out" / f"{a.label or 'compat'}.json", a.label or "compat", a.boards or B.board_names(),
                            tuple(a.models) if a.models else H.MODELS, cells, log=print)
    n = {}
    for r in data["records"]:
        n[r["status"]] = n.get(r["status"], 0) + 1
    print(f"{a.label}: program {data['program']['version']}; records by status: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
