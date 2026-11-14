#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_checks.py
@brief The checks of the review (README section 5): what quantity the first seconds compare, where the Analytic transient reads its point on a board with vias, and where the
       edges of the part fall on a 2 mm cell. Modes (cache `research/transient-reference-boards/out/review.json`, git-ignored):
       `slab`      finite-element step response of `two2` (level 0.5) read at the hottest top node and at the heat-capacity mean of the column under it from the top face to
                   mid-gap (what one program node per layer holds: its copper and half of the gap), plus the hottest node with 12 and 24 elements through the gap at level 1.0
                   (scratch interpreter of `independent-fem-edge`);
       `analytic`  the Analytic step response of `vias` read at its own point (the hottest cell of the board WITHOUT the vias, as the program does) and at the hottest cell of
                   its own steady solve with the vias; the second is made on a copy in this process (a wrapper of `analytic._modal_dynamics`), the program is not edited;
                   also the two example boards and the series length;
       `align`     the 6 mm part of `simple4` at a 2 mm cell with its edges in the middle of cells (the study, 47 to 53 mm) or on cell lines (48 to 54 mm), against 0.5 mm.
@details Run from the repository root: `<scratch>/bin/python research/transient-reference-boards/scripts/study_review_checks.py slab` and
         `.venv/bin/python research/transient-reference-boards/scripts/study_review_checks.py analytic|align`. Rises in K per watt of the part.
"""
import json
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import numpy as np                                                       # noqa: E402
import refboards as R                                                    # noqa: E402

OUT = os.path.join(HERE, "..", "out", "review.json")
TIMES = (0.3, 1.0, 3.0, 10.0, 30.0, 100.0)


def load():
    """!
    @brief Read the cache.
    @return dict.
    """
    return json.load(open(OUT)) if os.path.exists(OUT) else {}


def store(key, value):
    """!
    @brief Write one entry of the cache (atomic).
    @param key Entry name.
    @param value JSON-serialisable value.
    @return None.
    """
    res = load()
    res[key] = value
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT + ".tmp", "w"))
    os.replace(OUT + ".tmp", OUT)


def at(t, z, x):
    """!
    @brief Curve at a time, linear in log time.
    @param t Times (positive).
    @param z Curve.
    @param x Time.
    @return float.
    """
    return float(np.interp(np.log(x), np.log(np.asarray(t, float)), np.asarray(z, float)))


def slab():
    """!
    @brief Finite-element readouts of `two2`: hottest top node and the capacity mean of the column copper plus half gap under it; vertical mesh check.
    @return None (stored in the cache).
    """
    import board
    import cases
    import mesh2d
    import transient
    m, rho_c, fp = R.fem_board("two2", 0.5)
    tr = transient.Transient(m, rho_c, consistent=True)
    st = tr.steady()
    full = tr.full(st)
    nodes = np.unique(fp)
    hot = nodes[int(np.nanargmax(full[nodes]))]
    X = m.nodes
    z0 = X[hot, 2]
    sgn = 1.0 if z0 <= X[:, 2].min() + 1e-12 else -1.0                   # the heated face is the lowest or the highest z of the model
    col = np.nonzero((np.abs(X[:, 0] - X[hot, 0]) < 1e-9) & (np.abs(X[:, 1] - X[hot, 1]) < 1e-9))[0]
    col = col[np.argsort(X[col, 2])]
    tcu = 35e-6
    gap = 1.6e-3 - 2 * tcu
    # Capacity-weighted mean over depth 0 .. t_cu + gap / 2 of the piecewise linear field of the column (midpoint samples)
    n_s = 20000
    dep = (np.arange(n_s) + 0.5) * (tcu + gap / 2) / n_s
    s = z0 + sgn * dep
    rc = np.where(dep < tcu, R.RC_CU, R.RC_FR4)
    zc = X[col, 2]
    k = np.clip(np.searchsorted(zc, s) - 1, 0, len(zc) - 2)
    f = (s - zc[k]) / (zc[k + 1] - zc[k])
    w = np.zeros(X.shape[0])
    np.add.at(w, col[k], rc * (1 - f))
    np.add.at(w, col[k + 1], rc * f)
    w /= w.sum()
    wh = np.zeros(X.shape[0])
    wh[hot] = 1.0
    ro = {"hot": tr.reduce_weights(wh), "slab": tr.reduce_weights(w)}
    r = tr.step_response(ro, R.T_END["two2"], dt0=R.DT0["two2"], per_level=5, factor=2.5)
    out = {"t": r["t"][1:].tolist()}
    for key in ro:
        out[key] = r["series"][key][1:].tolist()
        out[key + "_steady"] = float(ro[key] @ st)
    print("two2 level 0.5", {key: [round(at(out["t"], out[key], x), 4) for x in TIMES] + [round(out[key + "_steady"], 4)] for key in ro}, flush=True)
    store("slab|two2|0.5", out)
    gaps = {}
    for ng in (12, 24):
        xn = cases.axis(30.0, [5.0], [(0, 5.3)], 1.0, 1.3, 1.0)
        yn = cases.axis(20.0, [5.0], [(0, 5.3)], 1.0, 1.3, 1.0)
        b = board.Board(mesh2d.tensor(xn, yn), 2, board_t=1.6e-3, k_xy=0.9, k_z=0.3, n_gap=ng, gap_ratio=1.3, h_top=10.0, h_bottom=10.0,
                        symmetry=[("x", 0.0), ("y", 0.0)], heaters=[(cases.rect(-1, -1, 5, 5), 0.25)])
        mm, info = b.build()
        f2 = np.vstack(info["heater_faces"])
        t2 = transient.Transient(mm, R.board_rho_c(mm), consistent=True)
        fu = t2.full(t2.steady())
        nd = np.unique(f2)
        h2 = nd[int(np.nanargmax(fu[nd]))]
        wv = np.zeros(mm.nodes.shape[0])
        wv[h2] = 1.0
        rr = t2.step_response({"hot": t2.reduce_weights(wv)}, 50.0, dt0=0.01, per_level=5, factor=2.5)
        gaps[str(ng)] = [at(rr["t"][1:], rr["series"]["hot"][1:], x) for x in TIMES[:4]]
        print("n_gap", ng, [round(v, 4) for v in gaps[str(ng)]], flush=True)
    store("ngap|two2|1.0", gaps)


def analytic_point():
    """!
    @brief The Analytic transient of the via board read at its own point and at the hottest cell of its own steady solve (a wrapper in this process, the program unchanged).
    @return None (stored in the cache).
    """
    sys.path.insert(0, R.ROOT)
    from pcbthermal import analytic
    from pcbthermal.project import load_project
    logging.disable(logging.WARNING)
    orig_md, orig_ss = analytic._modal_dynamics, analytic.solve_steady

    def at_steady_hottest(problem, cell_mm, n_terms, via_scale=1.0, heatsink_scale=1.0):
        """!
        @brief `_modal_dynamics` whose board-without-vias system (the base of the local transient) takes the served heater's point from the steady solve WITH the vias.
        @param problem Problem.
        @param cell_mm Cell size in mm.
        @param n_terms Modes per direction.
        @param via_scale Factor of the smeared vias (0 for the base of the local transient).
        @param heatsink_scale Factor of the smeared heatsinks.
        @return dict of `_modal_dynamics`.
        """
        d = orig_md(problem, cell_mm, n_terms, via_scale, heatsink_scale)
        if via_scale == 0.0 and heatsink_scale == 0.0 and (problem.vias or problem.heatsinks):
            powered = [i for i, h in enumerate(problem.heaters) if h.power != 0.0]
            j = powered[0] if len(powered) == 1 else 0
            T = orig_ss(problem, cell_mm=cell_mm, n_terms=n_terms).T
            d["points"][j] = tuple(int(v) for v in np.unravel_index(int(np.argmax(T)), T.shape))
        return d

    def run(problem, cell, fixed, t_end=None):
        """!
        @brief Analytic step responses with or without the wrapper.
        @param problem Problem.
        @param cell Cell in mm.
        @param fixed True: the point of the steady solve.
        @param t_end Last time in s.
        @return Tuple (t, z (heaters, nt), rth).
        """
        analytic._modal_dynamics = at_steady_hottest if fixed else orig_md
        try:
            t, z, r = analytic.step_responses(problem, cell_mm=cell, t_end=t_end)
        finally:
            analytic._modal_dynamics = orig_md
        return np.asarray(t), np.asarray(z), np.asarray(r)

    p = R.program_problem("vias")
    st = orig_ss(p, cell_mm=0.5)
    ms = analytic._ModalSet(p, 0.5, 300)
    T = st.T - p.board.ambient
    pt = tuple(int(v) for v in ms.points[0])
    hp = tuple(int(v) for v in np.unravel_index(int(np.argmax(T)), T.shape))
    d0 = ms.d0
    info = {"own_point": pt, "own_point_mm": [d0["xs"][pt[2]] * 1e3, d0["ys"][pt[1]] * 1e3], "steady_hottest": hp,
            "steady_hottest_mm": [d0["xs"][hp[2]] * 1e3, d0["ys"][hp[1]] * 1e3], "steady_at_own_point": float(T[pt]), "steady_max": float(T.max())}
    print(info, flush=True)
    out = {"info": info}
    for cell in (0.5, 1.0):
        for fixed in (False, True):
            t, z, r = run(p, cell, fixed, 1500.0)
            out[f"vias|{cell}|{'fixed' if fixed else 'asis'}"] = {"t": t.tolist(), "z": z[0].tolist(), "rth": float(r[0]),
                                                                    "t63": R.t_at(t, z[0], (1 - np.exp(-1.0)) * r[0])}
            print("vias", cell, "fixed" if fixed else "as is", round(float(r[0]), 4), [round(at(t, z[0], x), 3) for x in TIMES], flush=True)
    for n in (20, 100, 300, 2500):
        t, z, r = analytic.step_responses(p, cell_mm=0.5, n_terms=n, t_end=1500.0)
        out[f"n_terms|{n}"] = [float(np.asarray(r)[0]), at(t, np.asarray(z)[0], 0.3)]
    pe = load_project(os.path.join(R.ROOT, "examples", "example_board.pcbt.json"))
    pe = pe.problem if hasattr(pe, "problem") else pe
    for fixed in (False, True):
        t, z, r = run(pe, 1.0, fixed)
        out[f"example|1.0|{'fixed' if fixed else 'asis'}"] = [[float(r[i]), R.t_at(t, z[i], (1 - np.exp(-1.0)) * r[i])] for i in range(len(r))]
        print("example_board", "fixed" if fixed else "as is", out[f"example|1.0|{'fixed' if fixed else 'asis'}"], flush=True)
    store("analytic", out)


def align():
    """!
    @brief The 6 mm part of `simple4` at 2 mm with its edges in the middle of cells or on cell lines, against the same part at 0.5 mm (program only).
    @return None (stored in the cache).
    """
    sys.path.insert(0, R.ROOT)
    from pcbthermal import Problem, checks, fvm
    logging.disable(logging.WARNING)
    out = {}
    for x0, y0, tag in ((47, 37, "mid"), (48, 38, "lines")):
        p = Problem.new(100, 80, 4, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=10.0)
        for lay in range(1, 5):
            p.add_zone(lay, rect=(0, 0, 100, 80))
        p.add_heater(1, 1.0, rect=(x0, y0, x0 + 6, y0 + 6), role="source")
        row = {}
        for cell in (2.0, 0.5):
            t, z, r = fvm.step_responses(p, cell_mm=cell, t_end=1500.0)
            row[str(cell)] = [float(r[0]), R.t_at(t, z[0], (1 - np.exp(-1.0)) * r[0])]
        row["cell_warning"] = any("cells wide" in getattr(w, "text", str(w)) for w in checks.check_problem(p, cell_mm=2.0))
        out[tag] = row
        print(tag, row, f"plateau {100 * (row['2.0'][0] / row['0.5'][0] - 1):+.2f} %, t63 {100 * (row['2.0'][1] / row['0.5'][1] - 1):+.2f} %", flush=True)
    store("align", out)


if __name__ == "__main__":
    {"slab": slab, "analytic": analytic_point, "align": align}[sys.argv[1]]()
