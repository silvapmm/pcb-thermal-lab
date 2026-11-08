#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file boards.py
@brief Uniform rectangular boards with one square source at a chosen place, and the readouts (footprint mean, hottest node) of the program's models.
@details Two layers of full copper, no vias. The FVM reference is cached by case key in out/fvm_cache.json (git-ignored) because it does not depend on the Lumped variant.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tree  # noqa: E402,F401
from pcbthermal import Problem, SolverOptions, simulate  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out"
CACHE = OUT / "fvm_cache.json"


def board(w_mm, h_mm, side_mm, pos, layers=2, fill=1.0, power=1.0, h_top=10.0, h_bot=15.0, h_side=10.0, thickness_mm=1.6, copper_um=35.0):
    """!
    @brief A uniform board with a square source on layer 1.
    @param w_mm Width in mm.
    @param h_mm Height in mm.
    @param side_mm Side of the source in mm.
    @param pos Centre (x, y) of the source in mm.
    @param layers Copper layers.
    @param fill Copper fill of every layer.
    @param power Power in W.
    @param h_top Top coefficient in W/m2K.
    @param h_bot Bottom coefficient in W/m2K.
    @param h_side Edge coefficient in W/m2K.
    @param thickness_mm Board thickness in mm.
    @param copper_um Copper thickness in um.
    @return Problem.
    """
    p = Problem.new(w_mm, h_mm, layers=layers, thickness_mm=thickness_mm, copper_um=copper_um, h_top=h_top, h_bottom=h_bot, h_side=h_side)
    p.add_full_copper(fill=fill)
    s = side_mm / 2
    p.add_heater(1, power, rect=(pos[0] - s, pos[1] - s, pos[0] + s, pos[1] + s), name="U")
    return p


def readout(p, model, cell_mm, side_mm, pos):
    """!
    @brief Footprint mean and hottest rise of one model on layer 1.
    @param p Problem.
    @param model Model key.
    @param cell_mm Cell in mm.
    @param side_mm Side of the source in mm.
    @param pos Centre of the source in mm.
    @return (mean over the cells whose centre lies in the footprint or, if none, the cell holding the centre; rise of the hottest node) in K.
    """
    r = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model]
    T = np.asarray(r.T)[0] - p.board.ambient
    ny, nx = T.shape
    xs = (np.arange(nx) + 0.5) * r.dx * 1e3
    ys = (np.arange(ny) + 0.5) * r.dy * 1e3
    m = (abs(xs[None, :] - pos[0]) <= side_mm / 2) & (abs(ys[:, None] - pos[1]) <= side_mm / 2)
    if not m.any():
        m = np.zeros_like(T, dtype=bool)
        m[min(int(pos[1] / (r.dy * 1e3)), ny - 1), min(int(pos[0] / (r.dx * 1e3)), nx - 1)] = True
    return float(T[m].mean()), float(r.t_max - p.board.ambient)


def fvm(key, p, cell_mm, side_mm, pos):
    """!
    @brief Cached FVM readout.
    @param key Case key (text).
    @param p Problem.
    @param cell_mm Cell in mm.
    @param side_mm Side of the source in mm.
    @param pos Centre of the source in mm.
    @return (mean, hottest) in K.
    """
    OUT.mkdir(exist_ok=True)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    k = f"{key}|{cell_mm}"
    if k not in cache:
        cache[k] = list(readout(p, "fvm", cell_mm, side_mm, pos))
        CACHE.write_text(json.dumps(cache))
    return tuple(cache[k])
