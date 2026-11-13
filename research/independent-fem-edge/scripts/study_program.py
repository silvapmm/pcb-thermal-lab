#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_program.py
@brief The program of this tree (FVM, and the FDM at its harmonic default) on the boards of the finite-element comparison: the strong-edge plate (simple and physical
       stack-up, default and 8 sub-gaps, cells 0.5 and 0.25 mm, copper to the wall and inset 0.5 mm), the via 0.16 and 3 mm from the wall, the 20 mm squares and the T
       turned 0 .. 45 degrees and shifted (the ten boards of `study_drawn_film.py`), and the disc (shifted 0 and 0.3 cell), cells 1 and 0.5 mm.
@details Run from the repository root: `.venv/bin/python research/independent-fem-edge/scripts/study_program.py [strong|drawn|disc ...]`. Reads the program only (nothing is modified);
         the board builders of `research/strong-edge-laminate/lib/prog.py` and `research/imported-copper-edge-film/scripts/study_drawn_film.py` are imported as they are.
         Results cached in `research/independent-fem-edge/out/prog.json`. Under 1.5 GB.
"""

import json
import logging
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(1, os.path.join(ROOT, "research", "strong-edge-laminate", "lib"))
sys.path.insert(2, os.path.join(ROOT, "research", "imported-copper-edge-film", "scripts"))
import numpy as np                                                                  # noqa: E402

from pcbthermal import Problem, SolverOptions, analysis, simulate                   # noqa: E402
from pcbthermal.model import Dielectric                                             # noqa: E402

logging.disable(logging.WARNING)
OUT = os.path.join(os.path.dirname(HERE), "out", "prog.json")


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
    json.dump(res, open(OUT, "w"), indent=1)


def rise(p, cell, model):
    """!
    @brief Hottest rise and the heater's mean rise (face value of `analysis.heater_stats`) of one model.
    @param p Problem.
    @param cell Cell in mm.
    @param model 'fvm' or 'fdm'.
    @return Tuple (tmax K, heater mean K, balance error).
    """
    r = simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model]
    st = analysis.heater_stats(r, p)[0]
    return float(r.t_max - p.board.ambient), float(st["t_mean"] - p.board.ambient), float(getattr(r, "balance_error", float("nan")))


def strong(res):
    """!
    @brief The strong-edge board: plate (two insets) and vias, FVM in four laminate settings and the FDM at the defaults.
    @param res Cache.
    @return None.
    """
    import prog as sprog

    def physical(p):
        """!
        @brief Advanced stack-up of three equal gaps (the physical slabs of the reference).
        @param p Problem.
        @return Problem.
        """
        p.board.dielectrics = [Dielectric(thickness=sprog.GAP_MM * 1e-3, k_through=0.3, k_inplane=0.3) for _ in range(3)]
        return p
    for h in (10.0, 200.0, 1000.0):
        for d, inset in ((None, 0.0), (None, 0.5), (0.16, 0.0), (3.0, 0.0)):
            if d is not None and h == 10.0:
                continue
            for cell in (0.5, 0.25):
                for n in (None, 8):
                    for phys in (False, True):
                        for model in ("fvm", "fdm"):
                            key = f"strong|{h}|{d}|{inset}|{cell}|{n}|{phys}|{model}"
                            if key in res or (model == "fdm" and n is not None):
                                continue
                            t = time.time()
                            p = sprog.board(h, d, inset_mm=inset)
                            res[key] = sprog.run(physical(p) if phys else p, cell, n, model=model)
                            print(key, round(res[key], 4), f"{time.time() - t:.0f} s", flush=True)
                            save(res)


def drawn(res):
    """!
    @brief The squares and the T of the edge-film study: ten turned and shifted boards, FVM (heater mean by the network weights, as validation 40) and FDM (heater_stats).
    @param res Cache.
    @return None.
    """
    import study_drawn_film as sd
    for name, hs in (("sq_in", (10.0, 200.0, 1000.0)), ("sq_wall", (200.0, 1000.0)), ("T_wall", (200.0,))):
        spec = sd.CASES[name]
        for h in hs:
            for cell in (1.0, 0.5):
                for model in ("fvm", "fdm"):
                    key = f"{name}|{h}|{cell}|{model}"
                    if key in res:
                        continue
                    t = time.time()
                    means, maxes, means_stats = [], [], []
                    for sh in sd.SHIFTS:
                        for ang in sd.ANGLES:
                            p = sd.build(spec, h, ang, sh * cell)
                            if model == "fvm":
                                mean, mx, _ = sd.heater_rise(p, cell)
                                means.append(mean)
                                maxes.append(mx)
                                means_stats.append(rise(p, cell, "fvm")[1])
                            else:
                                mx, mean, _ = rise(p, cell, "fdm")
                                means.append(mean)
                                maxes.append(mx)
                    res[key] = {"mean": means, "tmax": maxes, "mean_stats": means_stats}
                    print(key, "mean of means %.4f (spread %.4f)" % (np.mean(means), np.ptp(means)), f"{time.time() - t:.0f} s", flush=True)
                    save(res)


def disc_problem(h, inset, shift_mm, W=24.0, n_vertices=180):
    """!
    @brief The disc board in the program: a 180-gon outline of radius 10 mm in a 24 mm box, zones to the rim or 1.2 mm inside it, a 4 mm heater at the centre, 1 W.
    @param h Edge coefficient W/m2K.
    @param inset Copper inset, mm.
    @param shift_mm Shift of the centre from the box centre, mm.
    @param W Box side, mm.
    @param n_vertices Vertices of the outline polygon.
    @return Problem.
    """
    c = W / 2 + shift_mm
    ang = np.linspace(0, 2 * math.pi, n_vertices, endpoint=False)
    outline = [[c + 10.0 * math.cos(a), c + 10.0 * math.sin(a)] for a in ang]
    p = Problem.new(W, W, 2, h_side=h)
    p.board.h_top = p.board.h_bottom = 10.0
    p.add_heater(1, 1.0, rect=(c - 2, c - 2, c + 2, c + 2), name="U")
    p.set_outline(outline)
    r = 10.0 - inset
    zone = outline if inset <= 0 else [[c + r * math.cos(a), c + r * math.sin(a)] for a in ang]
    for layer in (1, 2):
        p.add_zone(layer, polygon=zone)
    return p


def disc(res):
    """!
    @brief The disc board: copper to the rim and 1.2 mm inside, 200 and 1000 W/m2K, shifts 0 and 0.3 cell, cells 1 and 0.5 mm, FVM and FDM.
    @param res Cache.
    @return None.
    """
    for inset in (0.0, 1.2):
        for h in (200.0, 1000.0):
            for cell in (1.0, 0.5):
                for model in ("fvm", "fdm"):
                    key = f"disc|{h}|{inset}|{cell}|{model}"
                    if key in res:
                        continue
                    t = time.time()
                    rows = [rise(disc_problem(h, inset, sh * cell), cell, model) for sh in (0.0, 0.3)]
                    res[key] = {"tmax": [r[0] for r in rows], "mean": [r[1] for r in rows]}
                    print(key, res[key], f"{time.time() - t:.0f} s", flush=True)
                    save(res)


if __name__ == "__main__":
    groups = sys.argv[1:] or ["strong", "drawn", "disc"]
    cache = load()
    for g in groups:
        {"strong": strong, "drawn": drawn, "disc": disc}[g](cache)
