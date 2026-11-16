#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file patched.py
@brief A COPY of the program's FVM and FDM networks that read the zones of a drawn board the way they read an import: exact coverage fill and flow-based faces. The program is not edited.
@details `use(mapping)` is a context manager that replaces `fvm.Network` and `fdm.Network` by subclasses. When the problem has zones and no imported copper, the subclass converts the
         zones (every layer that has a zone) to coverage rasters of pixel `cell / 10` (`dc_cases.zone_rasters`), builds a `copper.CopperSource` from them and passes it as the `faces` argument.
         Everything else (the zones stay in the problem for the via rim test, the checks and the blocks) is the program's own code: the imported path of `fvm.py`, `fdm.py` and `copper.py`.
         `mapping` is 'faces' (the imported default), 'lambda' or 'fill'. With `mapping=None` the program is unchanged.
"""
import contextlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dc_cases as D                                                      # noqa: E402
from pcbthermal import copper, fvm, fdm                                   # noqa: E402

PIX_PER_CELL = 10
STATE = {"mapping": "faces", "pix": PIX_PER_CELL, "float": True, "skip": True}


class FloatSource(copper.CopperSource):
    """!
    @brief A CopperSource whose rasters are float coverage in 0..255 kept in memory, not packed bytes: a hatch fill of 0.7 stays 0.7 (the uint8 of a stored import reads 0.698).
    """

    def __init__(self, rasters, pix_m, mapping, n_layers):
        """!
        @param rasters dict layer -> float array (rows from the top), 0..255.
        @param pix_m Pixel in m.
        @param mapping 'faces', 'lambda' or 'fill'.
        @param n_layers Copper layers of the board.
        """
        self.mapping = mapping
        self.reduce_sheet = True
        self.pix = pix_m
        self.entries = {l: {"index": l} for l in rasters}
        self._r = rasters

    def raster(self, layer):
        """!
        @brief The float coverage of a layer.
        @param layer Layer index.
        @return array.
        """
        return self._r[layer]


def layers_with_cut_cells(problem, nx, ny):
    """!
    @brief The layers that have at least one cell that a zone edge cuts (a cell neither empty nor wholly covered by the zones of its layer).
    @details A layer whose every cell is full or empty has, in the import rule, the same faces as in the drawn rule (a window half copper and half bare is the harmonic mean), so it
             keeps the program's own path and its numbers do not move (the float32 raster would move them by 1e-7 K).
    @param problem Problem.
    @param nx Cells along x.
    @param ny Cells along y.
    @return list of layer indices.
    """
    import numpy as np
    from pcbthermal.geometry import exact_coverage
    dx, dy = problem.board.width / nx, problem.board.height / ny
    out = []
    for l in range(problem.board.layers):
        cov = np.zeros((ny, nx))
        for z in problem.zones:
            if z.layer == l:
                cov += exact_coverage(np.asarray(z.polygon), nx, ny, dx, dy)
        if np.any((cov > 1e-9) & (cov < 1.0 - 1e-9)):
            out.append(l)
    return out


def source_of(problem, cell_mm, mapping):
    """!
    @brief The CopperSource of the zones of a problem, or None when it has none or already has imported copper.
    @param problem Problem.
    @param cell_mm Cell (grid spacing) in mm.
    @param mapping 'faces', 'lambda' or 'fill'.
    @return copper.CopperSource or None.
    """
    if getattr(problem, "imported", None) is not None and problem.imported.layers:
        return None
    if not problem.zones:
        return None
    pix = cell_mm / STATE["pix"]
    keep = None
    if STATE["skip"]:
        keep = layers_with_cut_cells(problem, int(round(problem.board.width * 1e3 / cell_mm)), int(round(problem.board.height * 1e3 / cell_mm)))
        if not keep:
            return None
    r = D.zone_rasters(problem, pix, quantise=not STATE["float"], only=keep)
    if STATE["float"]:
        return FloatSource(r, pix * 1e-3, mapping, problem.board.layers)
    layers = sorted(r)
    rec = copper.imported_from_rasters([r[l] for l in layers], pix, mapping, indices=layers)
    return copper.CopperSource(rec, problem.board.layers, problem.board.width, problem.board.height)


class FvmCopy(fvm.Network):
    """!
    @brief fvm.Network with the drawn zones read as an import.
    """

    def __init__(self, problem, nx, ny, *a, faces=None, **kw):
        """!
        @param problem Problem.
        @param nx Cells along x.
        @param ny Cells along y.
        @param a Other positional arguments of fvm.Network.
        @param faces The caller's `faces` (None: the zones are converted).
        @param kw Other keywords of fvm.Network.
        """
        if faces is None and STATE["mapping"]:
            faces = source_of(problem, problem.board.width * 1e3 / nx, STATE["mapping"])
        super().__init__(problem, nx, ny, *a, faces=faces, **kw)


class FdmCopy(fdm.Network):
    """!
    @brief fdm.Network with the drawn zones read as an import.
    """

    def __init__(self, problem, cell_mm=2.0, *a, faces=None, **kw):
        """!
        @param problem Problem.
        @param cell_mm Grid spacing in mm.
        @param a Other positional arguments of fdm.Network.
        @param faces The caller's `faces` (None: the zones are converted).
        @param kw Other keywords of fdm.Network.
        """
        if faces is None and STATE["mapping"]:
            nx = max(int(round(problem.board.width * 1000.0 / cell_mm)), 2)
            faces = source_of(problem, problem.board.width * 1e3 / nx, STATE["mapping"])
        super().__init__(problem, cell_mm, *a, faces=faces, **kw)


@contextlib.contextmanager
def use(mapping="faces"):
    """!
    @brief Run with the copy networks (the program's own again afterwards).
    @param mapping 'faces', 'lambda', 'fill' or None for the program as it is.
    @return Context manager.
    """
    old = dict(STATE)
    f0, d0 = fvm.Network, fdm.Network
    STATE["mapping"] = mapping
    fvm.Network, fdm.Network = FvmCopy, FdmCopy
    try:
        yield
    finally:
        fvm.Network, fdm.Network = f0, d0
        STATE.clear()
        STATE.update(old)
