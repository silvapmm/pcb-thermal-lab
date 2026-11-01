#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file regress_harness.py
@brief Runs one revision of the program on the regression boards and stores the numbers as a result set (JSON).
@details A result set holds, for every (board, model, cell): the unknowns, the temperatures (maximum, mean, minimum, per layer, a checksum of the whole field), the temperatures
         under every part (hottest point, mean, junction), the heat balance, the warnings and the solve time (information only, never compared). It also holds the time to
         63 % of the steady resistance of the first part (a short transient) and the FVM with the SOR solver on a few boards (sweeps and difference from the direct solver).

         The harness is the same code for every revision. The revision under test is chosen by `use_program(root)`, which puts that tree first on `sys.path`, points the
         configuration folder of the program at an empty scratch folder (no user defaults) and refuses to go on if `pcbthermal` was imported from elsewhere. Memory is kept
         light: FVM and FDM above `max_unknowns` and the 3D solid above `solid_cap` unknowns are recorded as skipped, with the reason.
@note No result of this module is a judgement: the classification of the differences between two result sets is in `regress_classify.py`.
"""

import json
import math
import os
import platform
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import regress_boards as B                                                           # noqa: E402

FORMAT = 1
MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")
CELLS = (2.0, 1.0, 0.5)
MAX_UNKNOWNS = 400_000          # FVM and FDM above this are skipped (memory light; about 7 GB per million unknowns for the layered models)
SOLID_CAP = 150_000             # the 3D solid only below this many unknowns (the program's own limit is 250 000)
TRANSIENT_CELL = 1.0            # one short transient per board and model (the FVM and FDM step responses use at least 2 mm)
SOR_BOARDS = ("plate_uniform", "plate_vias", "plate_lone_via", "two_layer_partial", "example_board")
SOR_CELL = 2.0


def use_program(root, config_dir=None):
    """!
    @brief Make `import pcbthermal` load the tree at `root` and nothing else.
    @param root Folder that contains the `pcbthermal` package (the repository, or an extracted `git archive`).
    @param config_dir Empty folder for the program's configuration (user defaults); a new temporary folder when None.
    @return The imported `pcbthermal` module.
    @throws RuntimeError If `pcbthermal` is already imported from another folder or is not found under `root`.
    """
    root = str(Path(root).resolve())
    os.environ["PCBTHERMAL_CONFIG"] = str(config_dir or tempfile.mkdtemp(prefix="pcbt_regress_cfg_"))    # no user_defaults.json: the shipped defaults only
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if "pcbthermal" in sys.modules:
        loaded = str(Path(sys.modules["pcbthermal"].__file__).resolve())
        if not loaded.startswith(root):
            raise RuntimeError(f"pcbthermal was already imported from {loaded}, not from {root}")
    sys.path.insert(0, root)
    import pcbthermal                                                         # noqa: E402
    where = str(Path(pcbthermal.__file__).resolve())
    if not where.startswith(root):
        raise RuntimeError(f"pcbthermal was loaded from {where}, not from {root}")
    return pcbthermal


def _f(x):
    """!
    @brief A float that survives JSON (NaN and infinity become None).
    @param x Number or None.
    @return float or None.
    """
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def steady_problem(problem):
    """!
    @brief Copy of a problem without power profiles (every part at its average power), so that the steady runs do not start a time simulation.
    @param problem A Problem.
    @return A new Problem.
    """
    import copy
    p = copy.deepcopy(problem)
    for h in p.heaters:
        h.power = h.average_power()
        h.profile = None
    return p


def unknowns_of(problem, model, cell):
    """!
    @brief Unknowns of a model as the program counts them (None for the models that do not expose a count).
    @param problem A Problem.
    @param model Model key.
    @param cell Cell size in mm.
    @return int or None.
    """
    try:
        if model == "fvm":
            from pcbthermal import fvm
            return int(fvm.unknowns(problem, cell)[0])
        if model == "fdm":
            from pcbthermal import fdm
            return int(fdm.unknowns(problem, cell)[0])
        if model == "solid3d":
            from pcbthermal import solid3d
            return int(solid3d.unknowns(problem, cell)[0])
    except Exception:                                                         # a count that cannot be made is not a failure of the run
        return None
    return None


def _parts(sim, model, problem):
    """!
    @brief Temperatures under every part for one model.
    @param sim Simulation.
    @param model Model key.
    @param problem The Problem that was solved.
    @return List of dicts (name, power_w, t_max, t_mean, t_junction, power_top_w) or None when the model has no field.
    """
    from pcbthermal.analysis import heater_stats
    try:
        rows = heater_stats(sim.results[model], problem, sim.power_used.get(model))
    except Exception:
        return None
    return [{"name": r["name"], "power_w": _f(r["power_w"]), "t_max": _f(r["t_max"]), "t_mean": _f(r["t_mean"]), "t_junction": _f(r["t_junction"]),
             "power_top_w": _f(r["power_top_w"])} for r in rows]


def _blocks(sim, model, problem):
    """!
    @brief Temperature of the metal blocks (FVM and FDM only).
    @param sim Simulation.
    @param model Model key.
    @param problem The Problem that was solved.
    @return List of dicts or None.
    """
    if model not in ("fvm", "fdm"):
        return None
    from pcbthermal.analysis import block_stats
    try:
        return [{"name": r.get("name"), "face": r.get("face"), "t_mean": _f(r.get("t_mean")), "t_max": _f(r.get("t_max")), "w_to_block": _f(r.get("w_to_block"))}
                for r in block_stats(sim.results[model], problem)]
    except Exception:
        return None


def run_one(problem, board, model, cell, max_unknowns=MAX_UNKNOWNS, solid_cap=SOLID_CAP, linear_solver="direct"):
    """!
    @brief One steady-state run of one model at one cell size, as a record of the result set.
    @param problem A Problem (it is copied without profiles; the original is not modified).
    @param board Board name (stored in the record).
    @param model Model key.
    @param cell Cell size in mm.
    @param max_unknowns FVM and FDM above this many unknowns are skipped.
    @param solid_cap The 3D solid above this many unknowns is skipped.
    @param linear_solver FVM solver: "direct" or "sor".
    @return dict: board, model, cell_mm, status ("ok", "skipped" or "error"), reason, unknowns, seconds and, when ok, the temperatures, the parts, the balance and the warnings.
    """
    import numpy as np
    from pcbthermal import SolverOptions, simulate
    p = steady_problem(problem)
    rec = {"board": board, "model": model, "cell_mm": cell, "solver": linear_solver, "status": "ok", "reason": "", "unknowns": unknowns_of(p, model, cell)}
    cap = {"fvm": max_unknowns, "fdm": max_unknowns, "solid3d": solid_cap}.get(model)
    if cap is not None and rec["unknowns"] is not None and rec["unknowns"] > cap:
        rec.update(status="skipped", reason=f"{rec['unknowns']} unknowns, more than {cap}")
        return rec
    t0 = time.perf_counter()
    try:
        sim = simulate(p, SolverOptions(models=(model,), cell_mm=cell, linear_solver=linear_solver))
    except Exception as exc:                                                  # a model that refuses a board is a result, not a crash of the suite
        rec.update(status="error", reason=f"{type(exc).__name__}: {exc}", seconds=time.perf_counter() - t0)
        return rec
    wall = time.perf_counter() - t0
    if model not in sim.results:                                              # the 3D solid refuses an oversize model inside simulate and only warns
        rec.update(status="skipped", reason="; ".join(sim.warnings)[:300], seconds=wall)
        return rec
    r = sim.results[model]
    rec.update(seconds=wall, t_max=_f(r.t_max), t_mean=_f(r.t_mean), t_min=_f(r.t_min), power_in=_f(r.power_in), ambient=_f(r.ambient),
               balance_error=_f(r.balance_error), residual=_f(r.residual), layer_mean=[_f(v) for v in r.layer_mean],
               warnings=sorted(sim.warnings), parts=_parts(sim, model, p), blocks=_blocks(sim, model, p),
               extras={k: _f(v) for k, v in (r.extras or {}).items() if isinstance(v, (int, float))})
    if r.T is not None:
        T = np.asarray(r.T, dtype=float)
        rec.update(t_shape=list(T.shape), t_sum=_f(np.nansum(T)), t_sumsq=_f(np.nansum(T * T)))        # a checksum of the whole field: a change anywhere is seen
    return rec


def t63(problem, model, cell=TRANSIENT_CELL):
    """!
    @brief Time to 63.2 % of the steady resistance in the unit-step response of every part (the short transient).
    @param problem A Problem with at least one part.
    @param model "fvm", "fdm", "lumped" or "analytic".
    @param cell Cell size in mm of the options (the FVM and FDM step responses use at least 2 mm).
    @return dict: model, cell_mm, status, reason, parts (list of dicts name, rth, t63_s, reached).
    """
    import numpy as np
    from pcbthermal import SolverOptions
    from pcbthermal.api import step_response
    p = steady_problem(problem)
    out = {"model": model, "cell_mm": cell, "status": "ok", "reason": "", "parts": []}
    t0 = time.perf_counter()
    try:
        sr = step_response(p, model, SolverOptions(models=(model,), cell_mm=cell))
    except Exception as exc:
        out.update(status="error", reason=f"{type(exc).__name__}: {exc}")
        return out
    out["seconds"] = time.perf_counter() - t0
    t = np.asarray(sr.times, dtype=float)
    for i, h in enumerate(p.heaters):
        rth = float(sr.rth[i])
        z = np.asarray(sr.z[i], dtype=float)
        target = (1.0 - math.exp(-1.0)) * rth
        k = int(np.argmax(z >= target)) if (z >= target).any() else -1
        if k < 0:
            out["parts"].append({"name": h.name or f"Heater {i + 1}", "rth": _f(rth), "t63_s": None, "reached": False})
            continue
        if k == 0:
            t_hit = float(t[0] * target / z[0]) if z[0] > 0 else float(t[0])      # below the first sample the response is linear in time
        else:
            f = (target - z[k - 1]) / (z[k] - z[k - 1])
            t_hit = float(math.exp(math.log(t[k - 1]) + f * (math.log(t[k]) - math.log(t[k - 1]))))       # linear in log time between samples
        out["parts"].append({"name": h.name or f"Heater {i + 1}", "rth": _f(rth), "t63_s": _f(t_hit), "reached": True})
    return out


def run_suite(program_root, out_path, label, boards=None, models=MODELS, cells=CELLS, examples_dir=None, max_unknowns=MAX_UNKNOWNS, solid_cap=SOLID_CAP,
              transients=True, sor=True, resume=False, log=print):
    """!
    @brief Run the whole suite on one revision and write the result set.
    @param program_root Folder with the `pcbthermal` package to test.
    @param out_path JSON file to write (rewritten after every board, so a long run can be resumed).
    @param label Name of the result set (for example "v2.4.4" or "rc").
    @param boards Board names (default: all of regress_boards.board_names()).
    @param models Model keys.
    @param cells Cell sizes in mm.
    @param examples_dir Folder with the example files (default: `examples/` of this repository, the same for every revision).
    @param max_unknowns FVM and FDM above this many unknowns are skipped.
    @param solid_cap The 3D solid above this many unknowns is skipped.
    @param transients True to add the time to 63 % for each board and model.
    @param sor True to add the FVM with the SOR solver on SOR_BOARDS.
    @param resume True to keep the boards already in `out_path` and run only the others.
    @param log Function that takes one line of text (progress; the study scripts pass print).
    @return The result set (dict).
    """
    mod = use_program(program_root)
    import numpy
    import scipy
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    names = list(boards or B.board_names())
    data = {"format": FORMAT, "label": label, "program": {"root": str(Path(program_root).resolve()), "version": mod.__version__},
            "environment": {"python": sys.version.split()[0], "numpy": numpy.__version__, "scipy": scipy.__version__, "platform": platform.platform(), "machine": platform.machine()},
            "settings": {"models": list(models), "cells": list(cells), "max_unknowns": max_unknowns, "solid_cap": solid_cap, "transient_cell": TRANSIENT_CELL,
                         "sor_boards": list(SOR_BOARDS), "sor_cell": SOR_CELL, "examples_dir": str(examples_dir or B.REPO / "examples")},
            "boards": {}, "records": [], "transients": [], "sor": [], "done": []}
    if resume and out_path.exists():
        old = json.loads(out_path.read_text(encoding="utf-8"))
        if old.get("program", {}).get("version") == data["program"]["version"] and old.get("format") == FORMAT:
            data = old
        else:
            log("the file to resume is from another program version: ignored")
    for name in names:
        if name in data["done"]:
            log(f"{name}: already done")
            continue
        problem = B.build(name, examples_dir)
        feat = B.features(problem)
        feat["description"] = B.DESCRIPTIONS.get(name, "")
        feat["reference"] = name in B.REFERENCE_SPECS
        data["boards"][name] = feat
        for model in models:
            for cell in cells:
                rec = run_one(problem, name, model, cell, max_unknowns, solid_cap)
                data["records"].append(rec)
                log(f"{name:22s} {model:8s} {cell:4.2f} mm  {rec['status']:7s} " +
                    (f"Tmax {rec['t_max']:8.3f}  Tmean {rec['t_mean']:8.3f}  {rec['seconds']:6.1f} s" if rec["status"] == "ok" else rec["reason"][:80]))
        if transients and problem.heaters:
            for model in ("fvm", "fdm", "lumped", "analytic"):
                if model in models:
                    tr = t63(problem, model)
                    tr["board"] = name
                    data["transients"].append(tr)
                    log(f"{name:22s} {model:8s} t63  {tr['status']}  " + ", ".join(f"{q['t63_s']:.3g} s" for q in tr["parts"] if q["t63_s"] is not None))
        if sor and name in SOR_BOARDS and "fvm" in models:
            rec = run_one(problem, name, "fvm", SOR_CELL, max_unknowns, solid_cap, linear_solver="sor")
            data["sor"].append(rec)
            log(f"{name:22s} fvm sor   {rec['status']}  " + (f"sweeps {rec['extras'].get('iterations')}" if rec["status"] == "ok" else rec["reason"][:80]))
        data["done"].append(name)
        out_path.write_text(json.dumps(data, indent=1), encoding="utf-8")        # after every board: nothing is lost if the run is stopped
    return data
