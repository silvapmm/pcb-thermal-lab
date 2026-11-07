#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file runner.py
@brief Run the models on a simple board and read the footprint mean and the hottest node; cache the FVM reference in a JSON file.
@details The FVM reference of a case is expensive and does not depend on the Lumped variant, so it is stored by case key in out/fvm_cache.json (git-ignored). Candidates of the
         Lumped ring construction are set with lumped_log.configure() and run through pcbthermal.api with the patched module installed.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import simple as S  # noqa: E402
import lumped_log as LL  # noqa: E402
from pcbthermal import SolverOptions, simulate  # noqa: E402

OUT = HERE.parent / "out"
CACHE = OUT / "fvm_cache.json"
LL.install()


def _load():
    """!
    @brief Read the cache.
    @return dict.
    """
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def readout(p, model, cell_mm, side_mm, pos_mm, **opts):
    """!
    @brief Footprint mean and hottest rise of one model.
    @param p Problem with one source (the square of side side_mm at pos_mm on layer 1).
    @param model Model key.
    @param cell_mm Cell in mm.
    @param side_mm Side of the source in mm.
    @param pos_mm Centre (x, y) in mm.
    @param opts Further SolverOptions fields.
    @return (mean over the cells whose centre lies in the footprint, rise of the hottest node) in K.
    """
    r = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm, **opts)).results[model]
    T = np.asarray(r.T)[0] - p.board.ambient
    ny, nx = T.shape
    xs = (np.arange(nx) + 0.5) * r.dx * 1e3
    ys = (np.arange(ny) + 0.5) * r.dy * 1e3
    m = (abs(xs[None, :] - pos_mm[0]) < side_mm / 2) & (abs(ys[:, None] - pos_mm[1]) < side_mm / 2)
    mean = float(T[m].mean()) if m.any() else float("nan")
    return mean, float(r.t_max - p.board.ambient)


def fvm_reference(key, p, cell_mm, side_mm, pos_mm):
    """!
    @brief FVM readout, cached.
    @param key Case key (text).
    @param p Problem.
    @param cell_mm Cell in mm.
    @param side_mm Side of the source.
    @param pos_mm Centre of the source.
    @return (mean, hottest) in K.
    """
    OUT.mkdir(exist_ok=True)
    cache = _load()
    k = f"{key}|{cell_mm}"
    if k not in cache:
        cache[k] = list(readout(p, "fvm", cell_mm, side_mm, pos_mm))
        CACHE.write_text(json.dumps(cache))
    return tuple(cache[k])


PROPOSAL = os.environ.get("LRU_PROPOSAL", "first 1.5 cells")      # the candidate that the studies call "the proposal"


# Named candidates of the ring construction: (link, first_ring factor of rho_max, first ring in cells, first ring cap in equivalent radii)
CANDIDATES = {
    "program": ("strip", 0.04, 1.5, None),
    "first 1.5 cells": ("strip", 0.0, 1.5, None),
    "cap 0.5 a": ("strip", 0.04, 1.5, 0.5),
    "cap 1 a": ("strip", 0.04, 1.5, 1.0),
    "cap 2 a": ("strip", 0.04, 1.5, 2.0),
    "cap 4 a": ("strip", 0.04, 1.5, 4.0),
    "cap 1.5 a": ("strip", 0.04, 1.5, 1.5),
}


def lumped(p, cand, cell_mm, side_mm, pos_mm, rings=10):
    """!
    @brief Lumped readout with one candidate construction.
    @param p Problem.
    @param cand Key of CANDIDATES.
    @param cell_mm Cell in mm.
    @param side_mm Side of the source.
    @param pos_mm Centre of the source.
    @param rings Rings per heater.
    @return (mean, hottest) in K.
    """
    LL.configure(*CANDIDATES[cand])
    return readout(p, "lumped", cell_mm, side_mm, pos_mm, lumped_rings=rings)
