#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_ring_means.py
@brief Review: test the explanation directly. Is the Lumped error in the link from the footprint to the first ring, and does the cap fix it or move it?
@details The Lumped network keeps one temperature per ring (the area mean of the ring's cells). The same rings are laid on the FVM field of the same board at the same cell
         (0.5 mm), and the FVM's area mean of every ring is compared with the Lumped node, for the program and for the capped first ring (lib/patch_program.py, the change of
         INTEGRATION.md 1 exactly). Printed per case: the first-ring width, the node errors of rings 0 to 4, the drop from ring 0 to ring 1 as a ratio Lumped / FVM, and the spread
         (standard deviation) of the FVM temperature inside each ring, which says how far the ring is from an isotherm. Cases: a 1 mm part centred on 100 x 80 and 200 x 150 mm,
         a 3 mm part centred and 6.5 mm from an edge, 3 x 1 mm and 6 x 2 mm parts (the hot cases of study_shape_and_cell.py). Writes out/ring_means.json (read by make_figures.py).
         Run from the repository root (about 30 s, peak under 1 GB):
         QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_ring_means.py
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import patch_program as PP  # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate, api  # noqa: E402
from pcbthermal import lumped as PROG  # noqa: E402

CAPPED = PP.load_patched()
OUT = HERE.parent / "out"
CASES = [  # (label, board w, h, source sx, sy, centre or None, cell)
    ("1 mm, 200 x 150, centre", 200, 150, 1.0, 1.0, None, 0.5),
    ("1 mm, 100 x 80, centre", 100, 80, 1.0, 1.0, None, 0.5),
    ("3 mm, 200 x 150, centre", 200, 150, 3.0, 3.0, None, 0.5),
    ("3 mm, 100 x 80, 6.5 mm from the edge", 100, 80, 3.0, 3.0, (8.0, 40.0), 0.5),
    ("3 x 1 mm, 200 x 150, centre", 200, 150, 3.0, 1.0, None, 0.5),
    ("6 x 2 mm, 200 x 150, centre, cell 1 mm", 200, 150, 6.0, 2.0, None, 1.0),
]


def board(w, h, sx, sy, pos):
    """!
    @brief Two-layer full-copper board (35 um, 1.6 mm, films 10/15 W/m2K, edge 10 W/m2K) with one 1 W rectangular source on the top layer.
    @param w Width in mm.
    @param h Height in mm.
    @param sx Source width in mm.
    @param sy Source height in mm.
    @param pos Centre (x, y) in mm or None for the board centre.
    @return Problem.
    """
    p = Problem.new(w, h, layers=2, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper(fill=1.0)
    cx, cy = pos or (w / 2.0, h / 2.0)
    p.add_heater(1, 1.0, rect=(cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2), name="U")
    return p


def lumped_rings(p, mod, cell):
    """!
    @brief Run the Lumped with a module and keep its network of the heater (theta per ring, distance map, footprint).
    @param p Problem.
    @param mod Module (the program's lumped or the capped copy).
    @param cell Cell in mm.
    @return (rise of the hottest node in K, captured dict with rn, cov, net).
    """
    cap = {}
    orig = mod._heater_network

    def spy(net, cov, layer, power, rings, vias=None, zone_ok=None):
        # Keep what the network was built from; the result is not changed
        rn = orig(net, cov, layer, power, rings, vias, zone_ok)
        cap.update(rn=rn, cov=cov, net=net)
        return rn

    mod._heater_network = spy
    api.lumped = mod
    try:
        r = simulate(p, SolverOptions(models=("lumped",), cell_mm=cell)).results["lumped"]
    finally:
        api.lumped = PROG
        mod._heater_network = orig
    return r.t_max - p.board.ambient, cap


def main():
    """!
    @brief Print the tables and write out/ring_means.json.
    @return None.
    """
    rows = []
    for (label, w, h, sx, sy, pos, cell) in CASES:
        p = board(w, h, sx, sy, pos)
        T = np.asarray(simulate(p, SolverOptions(models=("fvm",), cell_mm=cell)).results["fvm"].T)[0] - p.board.ambient
        print(f"\n### {label} (FVM hottest {T.max():.2f} K at {cell:g} mm)")
        print("| construction | first ring (mm) | a_eq (mm) | Lumped hottest | node error rings 0..4 (K) | drop 0->1 Lumped / FVM | FVM spread in rings 1..4 (K) |")
        print("| :-- | --: | --: | --: | :-- | --: | :-- |")
        for name, mod in (("program", PROG), ("capped", CAPPED)):
            hot, c = lumped_rings(p, mod, cell)
            rn, cov, net = c["rn"], c["cov"], c["net"]
            foot = cov > 0
            dist = rn["dist"]
            a_eq = float(np.sqrt(foot.sum() * net.dx * net.dy / np.pi))
            extra = {"a_eq": a_eq} if mod is CAPPED else {}
            edges = mod.ring_edges(float(dist.max()), net.dx, net.dy, 10, **extra)
            idx = np.where(foot, 0, 1 + np.minimum(np.searchsorted(edges[1:], dist, side="left"), len(edges) - 2))
            used = np.flatnonzero(np.bincount(idx.ravel()) > 0)
            fv = np.array([T[idx == k].mean() for k in used])
            sd = np.array([T[idx == k].std() for k in used])
            th = np.asarray(rn["theta"][0])
            err = th[:5] - fv[:5]
            ratio = (th[0] - th[1]) / (fv[0] - fv[1])
            rows.append({"case": label, "construction": name, "first_ring_mm": float(edges[1] * 1e3), "a_eq_mm": a_eq * 1e3, "hot_lumped": hot, "hot_fvm": float(T.max()),
                         "edges_mm": [float(e * 1e3) for e in edges[used[:6]]], "fvm_ring_mean": fv[:6].tolist(), "lumped_node": th[:6].tolist(), "drop_ratio": float(ratio),
                         "fvm_spread": sd[:6].tolist()})
            print(f"| {name} | {edges[1] * 1e3:.2f} | {a_eq * 1e3:.2f} | {100 * (hot / T.max() - 1):+.1f} % | " + " / ".join(f"{e:+.2f}" for e in err)
                  + f" | {ratio:.2f} | " + " / ".join(f"{s:.2f}" for s in sd[1:5]) + " |", flush=True)
    OUT.mkdir(exist_ok=True)
    (OUT / "ring_means.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
