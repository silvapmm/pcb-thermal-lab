#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file solid_patch.py
@brief In-memory copy of the via fraction of the 3D solid (`solid3d.Solid.__init__`) with other footprints of the barrel; the program file is not edited.
@details The program puts the plated copper area of a via in the cell of its centre when it fits, and spreads it over the cells of its disc by area when it does not.
         The copies keep the copper area of every via and change only where it is put:
         * `point`  always the cell of the centre (the old rule; a copper fill larger than a cell is clipped at 1);
         * `area`   always the area weights of the disc of the via (also for small vias, so a via on a cell corner is split in four);
         * `tuned`  the footprint of `viakernel.tuned_weights` (effective radius equal to the via radius), a point when the grid is coarse.
         The fraction is the copper share of the through conductivity of every slab of the cell, so the footprint is an "independent links" treatment (no wells).
"""

import contextlib
import inspect
import re
import textwrap

import numpy as np

import lattice
import viakernel as vk

STATE = {"name": "point"}


def via_fraction(problem, nx, ny, dx, dy):
    """!
    @brief Copper area of the vias as a fraction of every plan cell, with the current footprint rule.
    @param problem The Problem.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell size in x in m.
    @param dy Cell size in y in m.
    @return numpy.ndarray (ny, nx), clipped at 1.
    """
    b = problem.board
    A = dx * dy
    out = np.zeros((ny, nx))
    for v in problem.vias:
        if not (0.0 <= v.x < b.width and 0.0 <= v.y < b.height):
            continue
        a_via = v.thermal_area(b.via_plating, b.materials.k_copper)
        rv = v.diameter / 2.0
        name = STATE["name"]
        if name == "point":
            w = vk.disc_weights(v.x, v.y, 0.0, dx, 0.0)
        elif name == "area":
            w = vk.disc_weights(v.x, v.y, rv, dx, 0.0, 16, "area")
        else:
            w = vk.tuned_weights(v.x, v.y, rv, dx, 0.0)
            if w is None:
                w = vk.disc_weights(v.x, v.y, 0.0, dx, 0.0)
        for (i, j), x in w.items():
            if 0 <= i < ny and 0 <= j < nx:
                out[i, j] += a_via * x / A
    return np.minimum(out, 1.0)


@contextlib.contextmanager
def patched(name="point"):
    """!
    @brief Install a copy of the 3D solid constructor with a footprint rule for the vias; restore the original on exit.
    @param name point, area or tuned.
    @return Context manager.
    """
    from pcbthermal import solid3d
    old = solid3d.Solid.__init__
    src = textwrap.dedent(inspect.getsource(old))
    pat = re.compile(r"(?P<ind>[ ]+)via_frac = np\.zeros\(\(ny, nx\)\)\n.*?via_frac = np\.minimum\(via_frac, 1\.0\)\n", re.S)
    m = pat.search(src)
    if m is None:
        raise RuntimeError("via block not found in solid3d")
    src = src[:m.start()] + m.group("ind") + "via_frac = _via_fraction(problem, nx, ny, dx, dy)\n" + src[m.end():]
    ns = {}
    solid3d._via_fraction = via_fraction
    old_state = dict(STATE)
    STATE["name"] = name
    try:
        exec(compile(src, "<patched solid3d.Solid.__init__>", "exec"), solid3d.__dict__, ns)
        solid3d.Solid.__init__ = ns["__init__"]
        yield
    finally:
        solid3d.Solid.__init__ = old
        STATE.clear()
        STATE.update(old_state)
        if hasattr(solid3d, "_via_fraction"):
            del solid3d._via_fraction
