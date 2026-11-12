#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_via_groups_review.py
@brief Review of fix/lumped-via-groups-lone-via: the Lumped and Analytic on 24 random irregular via boards (not the 62 of the studies) against the FVM at 0.25 mm.
@details Four layouts, six boards each, 40 x 40 mm, 2 or 4 full-copper layers, one 5 to 10 mm part of 3 W: an array under the part with satellites at 1.5 to 4 pitches and
         scattered vias, scattered vias only, tight pairs (0.5 to 0.8 mm) with a satellite at 2.2 to 4 times the pair spacing (vias the new rule leaves alone close to
         others), and an array beside the part. Every board is also solved without vias, so the via effect is the difference.
         Run from the root of a checkout with PYTHONPATH naming the tree to measure (the branch, then develop):
         `PYTHONPATH=<tree> .venv/bin/python releases/2.7.0/final-opinion/scripts/study_via_groups_review.py models out.json` (Lumped, Analytic at 1 mm, the zone
         decision, the lone vias and the Analytic tile), `... fvm fvm.json` (the FVM at 0.25 mm, the reference; it does not read the groups) and `... warn w.json`
         (the via lines of the live check for the Lumped).
"""

import json
import sys

import numpy as np

from pcbthermal import Problem, SolverOptions, checks, lumped, simulate, viaconstriction
from pcbthermal.model import Materials

W = 40.0            # board side, mm
AMB = 35.0          # ambient, degC


def via_layout(k, rng, hx, hy, hs):
    """!
    @brief Via positions of board k.
    @param k Board index (the layout is k mod 4).
    @param rng numpy Generator.
    @param hx Part centre x in mm.
    @param hy Part centre y in mm.
    @param hs Part side in mm.
    @return tuple (kind, list of (x, y) in mm).
    """
    kind = ["array+sat", "scattered", "micro", "beside"][k % 4]
    vias = []
    if kind in ("array+sat", "beside"):
        n = int(rng.integers(3, 6))
        p = rng.uniform(0.8, 2.0)
        cx = hx if kind == "array+sat" else hx + hs / 2 + 1.0 + (n - 1) * p / 2
        vias += [(cx + (i - (n - 1) / 2) * p, hy + (j - (n - 1) / 2) * p) for i in range(n) for j in range(n)]
        # Satellites a little beyond the array, then vias scattered over the board
        for _ in range(int(rng.integers(1, 5))):
            ang, d = rng.uniform(0, 2 * np.pi), (n - 1) / 2 * p + p * rng.uniform(1.5, 4.0)
            vias.append((cx + d * np.cos(ang), hy + d * np.sin(ang)))
        vias += [tuple(rng.uniform(3, 37, 2)) for _ in range(int(rng.integers(0, 8)))]
    elif kind == "scattered":
        vias += [tuple(rng.uniform(hx - 12, hx + 12, 2)) for _ in range(int(rng.integers(6, 25)))]
    else:
        # Tight pairs, every other one under the part, each with a satellite that the new rule leaves alone
        for s in range(int(rng.integers(2, 6))):
            c = rng.uniform(hx - hs / 2, hx + hs / 2, 2) if s % 2 == 0 else rng.uniform(hx - 10, hx + 10, 2)
            sp = rng.uniform(0.5, 0.8)
            vias += [(c[0], c[1]), (c[0] + sp, c[1])]
            a, d = rng.uniform(0, 2 * np.pi), sp * rng.uniform(2.2, 4.0)
            vias.append((c[0] + d * np.cos(a), c[1] + d * np.sin(a)))
    return kind, [(x, y) for x, y in vias if 1 < x < W - 1 and 1 < y < W - 1]


def board(nl, hx, hy, hs, vias):
    """!
    @brief The board: full copper on every layer, one 3 W part on layer 1.
    @param nl Number of layers.
    @param hx Part centre x in mm.
    @param hy Part centre y in mm.
    @param hs Part side in mm.
    @param vias List of (x, y) in mm (0.3 mm drills).
    @return Problem.
    """
    p = Problem.new(W, W, nl, 1.6, AMB, h_top=10.0, h_bottom=10.0 if nl == 2 else 50.0, h_side=None, materials=Materials())
    for layer in range(1, nl + 1):
        p.add_zone(layer, rect=(0, 0, W, W))
    p.add_heater(1, 3.0, rect=(hx - hs / 2, hy - hs / 2, hx + hs / 2, hy + hs / 2))
    for x, y in vias:
        p.add_via(x, y, 0.3)
    return p


def rise(p, model, cell):
    """!
    @brief Hottest rise of one model.
    @param p Problem.
    @param model Model key.
    @param cell Cell in mm.
    @return float in K.
    """
    return float(simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max - AMB)


def main(mode, out):
    """!
    @brief Run the 24 boards in one mode and write the records.
    @param mode 'models', 'fvm' or 'warn'.
    @param out Output JSON path.
    @return None.
    """
    rng = np.random.default_rng(2711)
    cases = []
    for k in range(24):
        nl = [2, 4][(k // 4) % 2]
        hx, hy, hs = 20.0 + rng.uniform(-3, 3), 20.0 + rng.uniform(-3, 3), rng.uniform(5, 10)
        kind, vias = via_layout(k, rng, hx, hy, hs)
        p, q = board(nl, hx, hy, hs, vias), board(nl, hx, hy, hs, [])
        rec = {"k": k, "kind": kind, "nl": nl, "nv": len(vias)}
        if mode == "warn":
            rec["w"] = sorted(w[:90] for w in checks.check_input(p, ("lumped",), 1.0) if "via" in w.lower())
        elif mode == "fvm":
            rec["fvm_with"], rec["fvm_none"] = rise(p, "fvm", 0.25), rise(q, "fvm", 0.25)
        else:
            vs = viaconstriction.ViaSet(p)
            rec["n_lone"] = int(np.sum(np.bincount(vs.group)[vs.group] == 1))
            rec["zoned"] = bool(lumped.will_be_zoned(p, p.heaters[0]))
            rec["tile"] = viaconstriction.tile_size(vs, W * 1e-3, W * 1e-3)[1]
            for m in ("lumped", "analytic"):
                rec[m + "_with"], rec[m + "_none"] = rise(p, m, 1.0), rise(q, m, 1.0)
        cases.append(rec)
        print(rec, flush=True)
    with open(out, "w") as f:
        json.dump(cases, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
