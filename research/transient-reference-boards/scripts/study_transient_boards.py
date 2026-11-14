#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_transient_boards.py
@brief The independent finite-element transient (`independent-fem-extensions/lib/transient.py`) against the program's step responses on five synthetic boards: the step response,
       the steady value, the time to 63 % and a square wave. Modes (cache `research/transient-reference-boards/out/boards.json`, git-ignored):
       `fem <board> <level>`  finite-element step response (scratch interpreter with scikit-fem and pyamg; one job at a time, under 2 GB);
       `femwave <board> <level> <period> <duty> [cycles]`  the periodic wave by time stepping from the steady state of the mean power (6 periods by default; the slow
       modes of the board need about five of their time constants to forget that start, so a wave on a slow board needs more periods: key suffix `|c<cycles>`);
       `prog <board>`  the program's models (`.venv/bin/python`): FVM and FDM at 2, 1, 0.5 mm, Lumped and Analytic at 1 and 0.5 mm, every response stored;
       `report`  the tables (needs both caches).
@details Run from the repository root, for example
         `<scratch>/femenv/bin/python research/transient-reference-boards/scripts/study_transient_boards.py fem simple4 0.4` and
         `.venv/bin/python research/transient-reference-boards/scripts/study_transient_boards.py prog simple4`.
         Rises in K per watt of the part. The finite-element hottest node is the hottest top-face node of the footprint in the steady field; the footprint mean is the area mean of the
         top face over the part. The program's FVM and FDM read the hottest cell or node of the board (`fvm.step_responses`).
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import numpy as np                                                       # noqa: E402
import refboards as R                                                    # noqa: E402

OUT = os.path.join(HERE, "..", "out", "boards.json")


def load():
    """!
    @brief Read the cache.
    @return dict.
    """
    return json.load(open(OUT)) if os.path.exists(OUT) else {}


def save(res):
    """!
    @brief Write the cache (atomic).
    @param res dict.
    @return None.
    """
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT + ".tmp", "w"))
    os.replace(OUT + ".tmp", OUT)


def fem_setup(name, level):
    """!
    @brief Build the model, the transient object and the two readouts (footprint mean, hottest footprint node of the steady field).
    @param name Board.
    @param level Mesh level.
    @return Tuple (Transient, readouts dict, n unknowns) or None when the memory estimate is above 2 GB.
    """
    import transient
    m, rho_c, fp = R.fem_board(name, level)
    n = m.nodes.shape[0]
    est = n * (46000.0 if n <= 30000 else 8500.0) / 1e9
    print(f"{name} level {level}: {n} nodes, {m.elems.shape[0]} elements, estimate {est:.2f} GB", flush=True)
    if est > 2.0:
        print("refused: above 2 GB")
        return None
    tr = transient.Transient(m, rho_c, consistent=True)
    wm = tr.reduce_weights(transient.face_weights(m, fp))
    steady = tr.steady()
    nodes = np.unique(fp)
    full = tr.full(steady)
    hot = nodes[int(np.nanargmax(full[nodes]))]
    wh = np.zeros(m.nodes.shape[0])
    wh[hot] = 1.0
    return tr, {"mean": wm, "hot": tr.reduce_weights(wh)}, tr.n


def fem_step(name, level):
    """!
    @brief Finite-element step response of the footprint mean and the hottest node; the steady values, the energy residual and the time to 63 %.
    @param name Board.
    @param level Mesh level.
    @return None (stored in the cache).
    """
    s = fem_setup(name, level)
    if s is None:
        return
    tr, ro, n = s
    t0 = time.time()
    r = tr.step_response(ro, R.T_END[name], dt0=R.DT0[name], per_level=5, factor=2.5)
    e_in, e_store, e_lost = r["energy"]
    out = {"n": n, "solver": tr.how, "t": r["t"].tolist(), "seconds": time.time() - t0, "energy_residual": abs(e_in - e_store - e_lost) / e_in}
    for k in ro:
        z = r["series"][k]
        st = float(ro[k] @ tr.steady())
        out[k] = z.tolist()
        out[k + "_steady"] = st
        out[k + "_end"] = float(z[-1])
        out[k + "_t63"] = R.t_at(r["t"], z, (1 - np.exp(-1.0)) * st)
    print({k: (round(v, 5) if isinstance(v, float) else v) for k, v in out.items() if not isinstance(v, list)}, flush=True)
    res = load()
    res[f"fem|{name}|{level}"] = out
    save(res)


def fem_wave(name, level, period, duty, cycles=6):
    """!
    @brief The periodic state of a square wave by time stepping from the steady state of the mean power (the finite-element side of the wave comparison).
    @param name Board.
    @param level Mesh level.
    @param period Period in s.
    @param duty On fraction.
    @param cycles Periods marched.
    @return None (stored in the cache).
    """
    import transient
    s = fem_setup(name, level)
    if s is None:
        return
    tr, ro, n = s
    n_on, n_off = max(int(60 * duty), 8), max(int(60 * (1 - duty)), 8)
    segs = transient.square_segments(period, duty, n_on, n_off, cycles)
    t0 = time.time()
    run = tr.march(tr.steady(duty), segs, transient.square_power(period, duty), ro)
    t = run["t"]
    out = {"n": n, "seconds": time.time() - t0, "period": period, "duty": duty}
    for k in ro:
        s_ = run["series"][k]
        last = t > (cycles - 1) * period
        prev = (t > (cycles - 2) * period) & (t <= (cycles - 1) * period)
        out[k] = (float(s_[last].max()), float(s_[last].min()))
        out[k + "_periodicity"] = float(abs((s_[last].max() - s_[last].min()) - (s_[prev].max() - s_[prev].min())) / (s_[last].max() - s_[last].min()))
    print(out, flush=True)
    res = load()
    res[f"femwave|{name}|{level}|{period}|{duty}" + ("" if cycles == 6 else f"|c{cycles}")] = out
    save(res)


def prog(name, equal_slabs=False):
    """!
    @brief The program's step responses of a board with every model that can run it; the response curve, the steady resistance and the time to 63 % are stored.
    @param name Board.
    @param equal_slabs True: the thickness of every node of a simple stack-up of three or more layers is T / L (the rule of 2.6.0 and before, put back on a copy by replacing
           `model.Board.slab_thicknesses` in this process only); the entries are then stored under `progold`.
    @return None (stored in the cache).
    """
    import logging
    sys.path.insert(0, R.ROOT)
    from pcbthermal import analytic, fdm, fvm, lumped
    logging.disable(logging.WARNING)
    tag = "prog"
    if equal_slabs:
        from pcbthermal import model
        tag = "progold"
        orig = model.Board.slab_thicknesses

        def old_rule(self):
            """!
            @brief The 2.6.0 rule: T / L per node for three or more layers.
            @param self Board.
            @return numpy.ndarray.
            """
            return np.full(self.layers, self.total_thickness() / self.layers) if self.layers >= 3 else orig(self)
        model.Board.slab_thicknesses = old_rule
    res = load()
    p = R.program_problem(name)
    jobs = [("fvm", c) for c in (2.0, 1.0, 0.5)] + [("fdm", c) for c in (2.0, 1.0, 0.5)]
    if True:                                                                # the refusal of a model (block, outline) is recorded, not assumed
        jobs += [("lumped", 1.0), ("lumped", 0.5), ("analytic", 1.0), ("analytic", 0.5)]
    for model, cell in jobs:
        t0 = time.time()
        try:
            if model == "fvm":
                t, z, r = fvm.step_responses(p, cell_mm=cell, t_end=R.T_END[name])
            elif model == "fdm":
                t, z, r = fdm.step_responses(p, cell_mm=cell, t_end=R.T_END[name])
            elif model == "lumped":
                t, z, r = lumped.step_responses(p, rings=10, cell_mm=cell, t_end=R.T_END[name])
            else:
                t, z, r = analytic.step_responses(p, cell_mm=cell, t_end=R.T_END[name])
        except Exception as exc:                                         # a refusal of a model is reported, not hidden
            print(name, model, cell, "refused:", str(exc)[:120], flush=True)
            res[f"{tag}|{name}|{model}|{cell}"] = {"error": str(exc)[:300]}
            continue
        t, z0, rth = np.asarray(t, float), np.asarray(z, float)[0], float(np.asarray(r)[0])
        o = {"t": t.tolist(), "z": z0.tolist(), "rth": rth, "t63": R.t_at(t, z0, (1 - np.exp(-1.0)) * rth), "z_end": float(z0[-1]), "seconds": time.time() - t0}
        res[f"{tag}|{name}|{model}|{cell}"] = o
        print(name, model, cell, {k: round(v, 4) for k, v in o.items() if not isinstance(v, list)}, flush=True)
        save(res)


def main(argv):
    """!
    @brief Command line.
    @param argv Arguments after the script name.
    @return None.
    """
    mode = argv[0]
    if mode == "fem":
        fem_step(argv[1], float(argv[2]) if argv[1] != "disc" else int(argv[2]))
    elif mode == "femwave":
        fem_wave(argv[1], float(argv[2]) if argv[1] != "disc" else int(argv[2]), float(argv[3]), float(argv[4]), int(argv[5]) if len(argv) > 5 else 6)
    elif mode == "prog":
        prog(argv[1])
    elif mode == "progold":
        prog(argv[1], equal_slabs=True)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
