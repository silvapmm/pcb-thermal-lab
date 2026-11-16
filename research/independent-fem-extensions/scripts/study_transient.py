#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_transient.py
@brief Study 5 of the finite-element extensions: the transient reference. (vi) the new integrator on the disc board against the axisymmetric modal reference of
       `research/fast-wave-oscillation` (step response and the periodic 20 Hz wave), (vii) the periodic state by time stepping and by the frequency domain on the same mesh,
       the 20 Hz, 30 %, 1 W wave on the 60 x 40 mm two-layer plate at 0.4 / 0.2 / 0.1 mm against the program's decision and the two earlier references, and the step response of
       the study-2 plate (part over the via cluster, aluminium plate) at 0.2 mm against the program's FVM and FDM.
@details Run from the repository root, one mode at a time (each under 2 GB):
         `research/independent-fem-edge/.venv-research/bin/python research/independent-fem-extensions/scripts/study_transient.py disc` (checks vi and vii),
         `... fast 0.4` (also 0.2, 0.1), `... plate 0.2`; with the program's interpreter `.venv/bin/python .../study_transient.py prog` and `... report`.
         Cache: `research/independent-fem-extensions/out/s5.json`. Rises over the ambient in K per watt of the on-power unless stated.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "independent-fem-edge", "lib"))
sys.path.insert(0, os.path.join(ROOT, "research", "fast-wave-oscillation", "lib"))
import numpy as np                                                       # noqa: E402

OUT = os.path.join(HERE, "..", "out", "s5.json")
RC_CU, RC_FR4 = 8960 * 385.0, 1850 * 900.0


def load():
    """!
    @brief Read the cache.
    @return dict.
    """
    return json.load(open(OUT)) if os.path.exists(OUT) else {}


def save(res):
    """!
    @brief Write the cache.
    @param res dict.
    @return None.
    """
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1)


def board_rho_c(m):
    """!
    @brief Heat capacity per element of a `board.Board` model: copper where the through-thickness conductivity is that of copper, laminate elsewhere (the program's Materials).
    @param m fem.Model.
    @return numpy.ndarray (E,).
    """
    return np.where(m.k[:, 2] > 100.0, RC_CU, RC_FR4)


def t_at(t, z, target):
    """!
    @brief Time at which a rising curve crosses a value (linear in log time between samples, as the program's t63).
    @param t Times (first may be 0).
    @param z Curve.
    @param target Value.
    @return float or None.
    """
    t, z = np.asarray(t), np.asarray(z)
    ix = np.nonzero(z >= target)[0]
    if ix.size == 0:
        return None
    k = ix[0]
    if k == 0:
        return float(t[0])
    f = (target - z[k - 1]) / (z[k] - z[k - 1])
    if t[k - 1] <= 0:
        return float(t[k - 1] + f * (t[k] - t[k - 1]))
    return float(np.exp(np.log(t[k - 1]) + f * (np.log(t[k]) - np.log(t[k - 1]))))


def disc_source_board(n_side, n_gap, ratio=1.3, n_rad=8, n_cu=1):
    """!
    @brief The disc board of check (vi): radius 10 mm, insulated rim, two copper layers, h 10, a source on the DISC of the area of a 4 mm square (a circle level of the O-grid,
           so the source is the same shape as the one of `axisym_stack.Reference`), 1 W.
    @param n_side Intervals per side of the inner square of the O-grid (the mesh scale).
    @param n_gap Elements across a laminate gap.
    @param ratio Grading ratio of the gap elements.
    @param n_rad Rings between the source circle and the rim.
    @param n_cu Elements through a copper layer.
    @return Board.
    """
    import axisym_stack as A
    import board as B
    import mesh2d
    a = A.part_radius(4e-3)
    R = 10e-3
    radii = [a] + list(a + (R - a) * np.arange(1, n_rad + 1) / n_rad)
    plan = mesh2d.ogrid(0, 0, 0.7 * a / np.sqrt(2), radii, n_side, ("circle", R), n_inner=max(n_side // 3, 1))
    ang = np.linspace(0, 2 * np.pi, 721)[:-1]
    poly = np.column_stack([a * 1.0001 * np.cos(ang), a * 1.0001 * np.sin(ang)])                  # the quads inside the first circle level carry the source
    return B.Board(plan, 2, board_t=1.6e-3, k_xy=0.9, k_z=0.3, n_gap=n_gap, gap_ratio=ratio, n_cu=n_cu, h_top=10.0, h_bottom=10.0, h_side=0.0, heaters=[(poly, 1.0)])


def disc_checks(n_side=12, n_gap=24, consistent=True):
    """!
    @brief Checks (iv), (vi) and (vii): the disc board against `axisym_stack.Reference` (step response and the 20 Hz, 30 % wave), the periodic state by time stepping and by the
           frequency domain on the same mesh, the energy residual and the plateau.
    @param n_side Mesh scale of the O-grid.
    @param n_gap Elements across a gap.
    @param consistent True: the consistent mass.
    @return None.
    """
    import axisym_stack as A
    import transient
    res = load()
    b = disc_source_board(n_side, n_gap)
    m, info = b.build()
    tr = transient.Transient(m, board_rho_c(m), consistent=consistent)
    wmean = tr.reduce_weights(transient.face_weights(m, np.vstack(info["heater_faces"])))
    tag = f"disc|{n_side}|{n_gap}|{'cons' if consistent else 'lump'}"
    print(f"{tag}: {tr.n} unknowns ({tr.how})", flush=True)
    st = A.Stack(layers=2)
    ref = A.Reference(st, A.part_radius(4e-3), 10e-3, 10.0, 10.0)
    r = tr.step_response({"mean": wmean}, 800.0, dt0=1e-3, per_level=6, factor=2.0)
    e_in, e_store, e_lost = r["energy"]
    out = {"n": tr.n}
    out["energy_residual"] = abs(e_in - e_store - e_lost) / e_in
    print(f"(iv) energy: residual {out['energy_residual']:.2e}", flush=True)
    ss = float(wmean @ tr.steady())
    out["step"] = []
    for t in (0.01, 0.1, 1.0, 10.0, 100.0, 500.0):
        zf = float(np.interp(t, r["t"], r["series"]["mean"]))
        zr = float(ref.step(np.array([t]), "mean")[0])
        out["step"].append((t, zf, zr))
        print(f"(vi) step t={t:7.2f} s  FEM {zf:.5f}  axisym {zr:.5f}  FEM/axisym - 1 = {100 * (zf / zr - 1):+.2f} %", flush=True)
    out["plateau"] = (float(r["series"]["mean"][-1]), ss, float(ref.step(np.array([1e7]), "mean")[0]))
    print(f"(iii) plateau: end of run {out['plateau'][0]:.5f} steady {ss:.5f} (axisym steady {out['plateau'][2]:.5f})", flush=True)
    period, duty = 0.05, 0.3
    segs = transient.square_segments(period, duty, 60, 140, 10)
    run = tr.march(tr.steady(duty), segs, transient.square_power(period, duty), {"mean": wmean})
    s, t = run["series"]["mean"], run["t"]
    last, prev = t > 9 * period, (t > 8 * period) & (t <= 9 * period)
    sw_a, sw_prev = s[last].max() - s[last].min(), s[prev].max() - s[prev].min()
    print(f"(vii a) time stepping: swing last cycle {sw_a:.5f} K/W, previous {sw_prev:.5f} (periodicity {abs(sw_a - sw_prev) / sw_a:.1e})", flush=True)
    mx, mn = ref.square_wave(period, duty, "mean")
    out["wave"] = {"a": sw_a, "axisym": mx - mn, "periodicity": abs(sw_a - sw_prev) / sw_a}
    if tr.n <= 25000:
        freqs = np.logspace(-0.5, 4.5, 41)
        t0 = time.time()
        H = transient.harmonic_response(tr, wmean, freqs)
        tb, Tb = transient.periodic_wave(freqs, H, ss, period, duty)
        sw_b = Tb.max() - Tb.min()
        out["wave"]["b"] = sw_b
        print(f"(vii b) frequency domain: swing {sw_b:.5f} K/W ({time.time() - t0:.0f} s); (a) vs (b): {100 * (sw_a / sw_b - 1):+.3f} %", flush=True)
    print(f"(vi) 20 Hz wave: FEM {sw_a:.5f} vs axisym {mx - mn:.5f}: {100 * (sw_a / (mx - mn) - 1):+.2f} %", flush=True)
    res[tag] = out
    save(res)


def zconv():
    """!
    @brief Convergence of the disc check in the number of elements across the laminate gap (coarse plan, consistent mass, direct solves): the 20 Hz swing and the step response
           at 0.01 s and 1 s against the axisymmetric reference.
    @return None.
    """
    import axisym_stack as A
    import transient
    res = load()
    ref = A.Reference(A.Stack(layers=2), A.part_radius(4e-3), 10e-3, 10.0, 10.0)
    mx, mn = ref.square_wave(0.05, 0.3, "mean")
    out = []
    for n_gap, ratio in ((12, 1.3), (24, 1.3), (36, 1.3), (48, 1.3), (24, 1.15)):
        b = disc_source_board(8, n_gap, ratio, n_rad=6)
        m, info = b.build()
        tr = transient.Transient(m, board_rho_c(m), consistent=True)
        w = tr.reduce_weights(transient.face_weights(m, np.vstack(info["heater_faces"])))
        segs = transient.square_segments(0.05, 0.3, 60, 140, 8)
        run = tr.march(tr.steady(0.3), segs, transient.square_power(0.05, 0.3), {"m": w})
        s, t = run["series"]["m"], run["t"]
        sw = s[t > 7 * 0.05].max() - s[t > 7 * 0.05].min()
        st = tr.step_response({"m": w}, 2.0, dt0=1e-3, per_level=6, factor=2.0)
        e = [100 * (float(np.interp(tt, st["t"], st["series"]["m"])) / float(ref.step(np.array([tt]), "mean")[0]) - 1) for tt in (0.01, 1.0)]
        out.append((n_gap, ratio, tr.n, sw, e[0], e[1]))
        print(f"n_gap {n_gap} ratio {ratio}: {tr.n} unknowns, swing {sw:.5f} ({100 * (sw / (mx - mn) - 1):+.2f} % of axisym {mx - mn:.5f}), step error at 0.01 s {e[0]:+.2f} %, at 1 s {e[1]:+.2f} %", flush=True)
    res["zconv"] = out
    save(res)


def plate_board(hf, n_gap=20, ratio=1.35):
    """!
    @brief The 60 x 40 mm two-layer plate of `research/fast-wave-oscillation` (1.6 mm, 35 um, k 0.9 / 0.3, h 10), quarter domain, 10 mm square part in the centre, 1 W in total.
    @param hf Fine plan size in mm.
    @param n_gap Elements across the gap (graded from both copper faces; the penetration depth of a 20 Hz wave in FR-4 is 0.06 mm).
    @param ratio Grading ratio.
    @return Board.
    """
    import board
    import cases
    import mesh2d
    xn = cases.axis(30.0, [5.0], [(0, 5.3)], hf, 1.3, 1.0)
    yn = cases.axis(20.0, [5.0], [(0, 5.3)], hf, 1.3, 1.0)
    plan = mesh2d.tensor(xn, yn)
    return board.Board(plan, 2, board_t=1.6e-3, k_xy=0.9, k_z=0.3, n_gap=n_gap, gap_ratio=ratio, h_top=10.0, h_bottom=10.0, symmetry=[("x", 0.0), ("y", 0.0)],
                       heaters=[(cases.rect(-1, -1, 5, 5), 0.25)])


def fast(hf, n_gap=24, cycles=7):
    """!
    @brief The 20 Hz, 30 % wave on the plate: periodic state by time stepping (0.25 ms steps, Rannacher after every edge, started from the steady state of the mean power).
    @param hf Fine plan size in mm.
    @param n_gap Elements across a laminate gap.
    @param cycles Periods marched from the steady state of the mean power.
    @return None.
    """
    import transient
    res = load()
    key = f"fast|{hf}|{n_gap}"
    b = plate_board(hf, n_gap, 1.3)
    m, info = b.build()
    n = m.nodes.shape[0]
    est = n * (46000.0 if n <= 30000 else 8500.0) / 1e9
    print(f"plate hf {hf}: {n} nodes, {m.elems.shape[0]} elements, estimate {est:.2f} GB", flush=True)
    if est > 2.0:
        print("refused: above 2 GB")
        return
    t0 = time.time()
    tr = transient.Transient(m, board_rho_c(m), consistent=True)
    hf_faces = np.vstack(info["heater_faces"])
    wmean = tr.reduce_weights(transient.face_weights(m, hf_faces))
    nodes = np.unique(hf_faces)
    wmax_nodes = np.zeros(m.nodes.shape[0])
    sel = np.zeros(m.nodes.shape[0], bool)
    sel[nodes] = True
    period, duty = 0.05, 0.3
    segs = transient.square_segments(period, duty, 60, 140, cycles)
    T0 = tr.steady(duty)
    # the hottest footprint node is read at the end of the run from the field itself; the series keeps the footprint mean and the centre node
    centre = int(np.argmin(np.hypot(m.nodes[:, 0], m.nodes[:, 1]) + 1e9 * (m.nodes[:, 2] != 0.0)))
    wc = np.zeros(m.nodes.shape[0])
    wc[centre] = 1.0
    wc = tr.reduce_weights(wc)
    run = tr.march(T0, segs, transient.square_power(period, duty), {"mean": wmean, "centre": wc})
    t = run["t"]
    out = {"n": tr.n, "solver": tr.how, "seconds": time.time() - t0}
    for name in ("mean", "centre"):
        s = run["series"][name]
        last = t > (cycles - 1) * period
        prev = (t > (cycles - 2) * period) & (t <= (cycles - 1) * period)
        out[name] = float(s[last].max() - s[last].min())
        out[name + "_prev"] = float(s[prev].max() - s[prev].min())
        out[name + "_steady_mean"] = float(s[last].mean())
    e_in, e_store, e_lost = run["energy"]
    out["energy_residual"] = abs(e_in - e_store - e_lost) / e_in
    print(key, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in out.items()}, flush=True)
    res[key] = out
    save(res)


def plate(hf):
    """!
    @brief Step response of the study-2 plate (variant A, 6 x 6 mm part, 4 x 4 cluster of hollow vias, 1 mm aluminium plate through a 0.1 mm interface): the footprint mean in K/W.
    @param hf Fine plan size in mm.
    @return None.
    """
    import cluster
    import transient
    res = load()
    key = f"plate|{hf}"
    st, hd = cluster.build("A", 6.0, hf)
    m, info = st.build()
    n = m.nodes.shape[0]
    est = n * 8500.0 / 1e9
    print(f"study-2 plate hf {hf}: {n} nodes, estimate {est:.2f} GB", flush=True)
    if est > 2.0:
        print("refused")
        return
    t0 = time.time()
    tr = transient.Transient(m, info["rho_c"], consistent=True)
    qs = np.nonzero(hd["inside"](info["c"]))[0]
    w = tr.reduce_weights(transient.face_weights(m, st.level_nodes(info, 0, qs)))
    r = tr.step_response({"mean": w}, 2500.0, dt0=0.05, per_level=6, factor=2.0)
    # the model's source is the quarter of 1 W (`cluster.build(power=1.0)`), so the field is already the rise per watt of the whole board
    e_in, e_store, e_lost = r["energy"]
    out = {"n": tr.n, "solver": tr.how, "t": r["t"].tolist(), "z": (r["series"]["mean"]).tolist(), "steady": float(w @ tr.steady()),
           "energy_residual": abs(e_in - e_store - e_lost) / e_in, "seconds": time.time() - t0}
    tgt = (1 - np.exp(-1.0)) * out["steady"]
    out["t63"] = t_at(r["t"], r["series"]["mean"], tgt)
    print(key, "steady", round(out["steady"], 5), "t63", out["t63"], "energy residual", out["energy_residual"], f"{out['seconds']:.0f} s", flush=True)
    res[key] = out
    save(res)


def prog():
    """!
    @brief The program on the same problems: the 20 Hz wave decision of the plate (node swing, the closed-form floor, the decision) and the step responses of the study-2 plate
           (FVM and FDM, `fvm.step_responses` at 2, 1 and 0.5 mm and the API at its default).
    @return None.
    """
    import logging
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(HERE))
    from pcbthermal import Problem, SolverOptions, profiles
    from pcbthermal.api import step_response
    from pcbthermal.model import SquareWave
    logging.disable(logging.WARNING)
    res = load()
    p = Problem.new(60, 40, 2).add_full_copper()
    p.board.h_top = p.board.h_bottom = 10.0
    p.add_heater(1, 1.0, rect=(25, 15, 35, 25), name="part", profile=SquareWave(p_on=1.0, period=0.05, duty=0.3))
    out = {}
    for cell in (2.0, 1.0):
        resp = profiles.step_response_fvm(p, cell)
        pk, vl = profiles.wave_response(resp, 0, p.heaters[0].profile)
        dec = profiles.decide(p, resp, 1.0)
        out[f"fvm{cell}"] = {"node_swing": float(pk - vl), "decision": float(dec[0].oscillation), "regime": dec[0].regime, "rth": float(resp.rth[0])}
        print("program plate", cell, out[f"fvm{cell}"], flush=True)
    out["floor"] = float(profiles._fast_swing(p, 0, p.heaters[0].profile))
    print("closed-form floor (eq. 10.5), K per W", out["floor"], flush=True)
    res["prog_fast"] = out
    sys.path.insert(0, os.path.join(HERE))
    import study_cluster as sc
    from pcbthermal import fdm, fvm
    q = sc.program_problem(6, False)
    rows = {}
    for model, mod in (("fvm", fvm), ("fdm", fdm)):
        for cell in (2.0, 1.0, 0.5):
            t0 = time.time()
            times, z, rth = mod.step_responses(q, cell_mm=cell)
            z0 = np.asarray(z[0], float)
            tgt = (1 - np.exp(-1.0)) * float(rth[0])
            rows[f"{model}|{cell}"] = {"rth": float(rth[0]), "t63": t_at(np.asarray(times), z0, tgt), "seconds": time.time() - t0}
            print("step", model, cell, rows[f"{model}|{cell}"], flush=True)
    for model in ("fvm", "fdm"):
        sr = step_response(q, model, SolverOptions(models=(model,), cell_mm=1.0))
        z0 = np.asarray(sr.z[0], float)
        rows[f"api|{model}"] = {"rth": float(sr.rth[0]), "t63": t_at(np.asarray(sr.times), z0, (1 - np.exp(-1.0)) * float(sr.rth[0]))}
        print("api step", model, rows[f"api|{model}"], flush=True)
    res["prog_step"] = rows
    save(res)


def report():
    """!
    @brief Print the tables.
    @return None.
    """
    import axisym_stack as A
    res = load()
    print("plate 20 Hz, 30 %, 1 W (K swing per W): FEM footprint mean / centre node")
    for hf in (0.4, 0.2, 0.1):
        r = res.get(f"fast|{hf}|24")
        if r:
            print(f"  hf {hf}: mean {r['mean']:.5f} (prev cycle {r['mean_prev']:.5f}), centre {r['centre']:.5f}, energy residual {r['energy_residual']:.1e}, {r['n']} unknowns, {r['seconds']:.0f} s")
    p = res.get("prog_fast")
    if p:
        print("  program node swing / decision / floor:", {k: v for k, v in p.items()})
    st = A.Stack(layers=2)
    ref = A.Reference(st, A.part_radius(10e-3), A.rectangle_radius(60e-3, 40e-3), 10.0, 10.0)
    for ro in ("center", "mean"):
        mx, mn = ref.square_wave(0.05, 0.3, ro)
        print(f"  axisym reference ({ro}): {mx - mn:.5f}")
    for k in ("plate|0.2", "plate|0.1"):
        r = res.get(k)
        if r:
            print(f"study-2 plate step {k}: steady {r['steady']:.4f} K/W, t63 {r['t63']:.1f} s, energy residual {r['energy_residual']:.1e}")
    ps = res.get("prog_step")
    if ps:
        for k, v in ps.items():
            print("  program", k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items()})


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "disc":
        disc_checks(int(sys.argv[2]) if len(sys.argv) > 2 else 12, int(sys.argv[3]) if len(sys.argv) > 3 else 24, (sys.argv[4] != "lump") if len(sys.argv) > 4 else True)
    elif mode == "zconv":
        zconv()
    elif mode == "fast":
        fast(float(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 24)
    elif mode == "plate":
        plate(float(sys.argv[2]))
    elif mode == "prog":
        prog()
    elif mode == "report":
        report()
