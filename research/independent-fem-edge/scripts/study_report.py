#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_report.py
@brief Tables of the investigation from the caches of `study_fem_cases.py fem`, `study_references.py fv` and `study_references.py prog`: finite-element convergence (Richardson, GCI), the finite-volume references and the program against the finite-element value.
@details Writes `out/report.json` (read by `make_figures.py`) and prints the tables quoted in README 2 to 6. Missing solves are reported as `n/a`. Run: `.venv/bin/python research/independent-fem-edge/scripts/study_report.py`.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(FOLDER, "..", ".."))
sys.path.insert(0, os.path.join(FOLDER, "lib"))
import conv                                                                    # noqa: E402

OUT = os.path.join(FOLDER, "out")
PLAN = (0.2, 0.1, 0.05)
SQ_PLAN = (0.4, 0.2, 0.1)
VIA_PLAN = (0.28, 0.14, 0.07)


def get(case, key, **kw):
    """!
    @brief Cached solve value or None.
    @param case Board.
    @param key 'tmax' or 'mean'.
    @param kw Board arguments.
    @return float or None.
    """
    k = case + "|" + json.dumps(kw, sort_keys=True)
    cache = conv._load()
    return cache[k][key] if k in cache else None


def rich(vals):
    """!
    @brief Richardson of three values or a degenerate answer.
    @param vals List of three floats (None allowed).
    @return dict.
    """
    if any(v is None for v in vals):
        return None
    out = conv.richardson(*vals)
    out["f"] = list(vals)
    return out


def fem_plate(h):
    """!
    @brief Converged finite-element plate rise at the hottest top-copper point: plan Richardson at 8 bricks per gap plus the through-thickness correction at hf 0.1.
    @param h Wall film.
    @return dict with plan, z, ext (K) and uncertainty (K) or None.
    """
    plan = rich([get("strong", "tmax", h_side=h, hf=hf, n_gap=8) for hf in PLAN])
    z = rich([get("strong", "tmax", h_side=h, hf=0.1, n_gap=n) for n in (4, 8, 16)])
    if plan is None or z is None:
        return None
    f8 = z["f"][1]
    ext = plan["ext"] + (z["ext"] - f8)
    return {"plan": plan, "z": z, "ext": ext, "unc": abs(plan["ext"] - plan["f"][-1]) + abs(z["ext"] - z["f"][-1])}


def fem_via(h, d):
    """!
    @brief Finite-element via effect E = rise without via minus rise with the via, plan sequence at 8 bricks per gap.
    @param h Wall film.
    @param d Via distance from the wall in mm.
    @return dict from `rich` or None.
    """
    vals = []
    for hf in VIA_PLAN:
        a = get("strong", "tmax", h_side=h, hf=hf, n_gap=8)
        b = get("strong", "tmax", h_side=h, hf=hf, n_gap=8, via_dist=d)
        vals.append(None if a is None or b is None else a - b)
    return rich(vals)


def main():
    """!
    @brief Print the tables and write `out/report.json`.
    @return None.
    """
    rep = {}
    fv = json.load(open(os.path.join(OUT, "fv.json"))) if os.path.exists(os.path.join(OUT, "fv.json")) else {}
    pr = json.load(open(os.path.join(OUT, "prog.json"))) if os.path.exists(os.path.join(OUT, "prog.json")) else {}
    print("== (a) plate, hottest rise K: FEM plan sequence (hf 0.2/0.1/0.05, 8 bricks per gap), observed order, GCI, z, extrapolated; FV ref3d 1/4 and 1/8 mm; program")
    for h in (10.0, 200.0, 1000.0):
        e = fem_plate(h)
        if e is None:
            print(f"  h {h}: FEM n/a")
            continue
        rep[f"plate|{h}"] = e
        f4, f8 = (fv.get(f"{h}|None|{dx}", {}).get("tmax") for dx in (0.00025, 0.000125))
        print(f"  h {h:6.0f}: FEM {[round(v, 4) for v in e['plan']['f']]} p {e['plan']['p']:.2f} GCI {100 * e['plan']['gci']:.2f} %  z {[round(v, 4) for v in e['z']['f']]}  ext {e['ext']:.3f} +- {e['unc']:.3f}  |  FV 1/4 {f4} 1/8 {f8}")
        for dx, f in (("1/4", f4), ("1/8", f8)):
            if f:
                print(f"      FV {dx} mm vs FEM ext: {100 * (f / e['ext'] - 1):+.2f} %")
        for cell in (0.5, 0.25):
            row = []
            for n in (None, 8):
                for phys in (False, True):
                    v = pr.get(f"strong|{h}|None|{cell}|{n}|{phys}|fvm")
                    row.append("n/a" if v is None else f"{100 * (v / e['ext'] - 1):+.1f}")
            print(f"      program FVM cell {cell}: default simple / default physical / 8 simple / 8 physical vs FEM: " + " / ".join(row))
        for cell in (0.25,):
            row = [pr.get(f"strong|{h}|None|{cell}|None|{ph}|fdm") for ph in (False, True)]
            print(f"      program FDM cell {cell} default simple/physical: " + " / ".join("n/a" if v is None else f"{100 * (v / e['ext'] - 1):+.1f}" for v in row))
    print("== (b) via effect E (K), via 0.16 and 3 mm from the wall")
    for h in (200.0, 1000.0):
        for d in (0.16, 3.0):
            e = fem_via(h, d)
            if e is None:
                print(f"  h {h} d {d}: FEM n/a")
                continue
            rep[f"via|{h}|{d}"] = e
            f8 = fv.get(f"{h}|None|0.000125", {}).get("tmax")
            fv8 = fv.get(f"{h}|{d * 1e-3}|0.000125", {}).get("tmax")
            print(f"  h {h:6.0f} d {d}: FEM E {[round(v, 4) for v in e['f']]} p {e['p']:.2f} ext {e['ext']:.4f} GCI {100 * e['gci']:.1f} %" +
                  (f"  FV 1/8 E {f8 - fv8:.4f} ({100 * ((f8 - fv8) / e['ext'] - 1):+.1f} % vs FEM)" if f8 and fv8 else ""))
            for cell in (0.5, 0.25):
                row = []
                for n in (None, 8):
                    for phys in (False, True):
                        a = pr.get(f"strong|{h}|None|{cell}|{n}|{phys}|fvm")
                        b = pr.get(f"strong|{h}|{d}|{cell}|{n}|{phys}|fvm")
                        row.append("n/a" if a is None or b is None else f"{100 * ((a - b) / e['ext'] - 1):+.1f}")
                print(f"      program FVM cell {cell}: default simple / default physical / 8 simple / 8 physical vs FEM: " + " / ".join(row))
    print("== (c)/(d) heater mean rise (K): FEM vs the stored FV truth; program (10 boards: turned 0..45 deg, shifted 0 and 0.3 cell) vs FEM")
    cases = [("square", "sq_in", dict(inset=1.2), (10.0, 200.0, 1000.0)), ("square", "sq_wall", dict(inset=0.0), (200.0, 1000.0)), ("tout", "T_wall", dict(), (200.0,))]
    sys.path.insert(0, os.path.join(ROOT, "research", "imported-copper-edge-film", "scripts"))
    import logging
    logging.disable(logging.WARNING)
    import study_drawn_film as sd
    for case, name, kw, hs in cases:
        for h in hs:
            e = rich([get(case, "mean", hf=hf, n_gap=8, h_side=h, **kw) for hf in SQ_PLAN])
            tr = sd.truth_of(name, h)
            if e is None:
                print(f"  {name} h {h}: FEM n/a (truth {tr:.4f})")
                continue
            rep[f"{name}|{h}"] = e
            line = f"  {name:8s} h {h:6.0f}: FEM {[round(v, 4) for v in e['f']]} p {e['p']:.2f} GCI {100 * e['gci']:.2f} % ext {e['ext']:.4f} | FV truth {tr:.4f} ({100 * (tr / e['ext'] - 1):+.2f} % vs FEM)"
            print(line)
            for cell in (1.0, 0.5):
                v = pr.get(f"{name}|{h}|{cell}")
                if v:
                    ev = 100 * (np.array(v) / e["ext"] - 1)
                    et = 100 * (np.array(v) / tr - 1)
                    print(f"      program cell {cell}: vs FEM mean {ev.mean():+.2f} worst {np.abs(ev).max():.2f} | vs FV truth mean {et.mean():+.2f} worst {np.abs(et).max():.2f}")
    json.dump(rep, open(os.path.join(OUT, "report.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
