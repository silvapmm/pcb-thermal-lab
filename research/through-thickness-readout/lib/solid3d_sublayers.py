#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file solid3d_sublayers.py
@brief Option C prototype without editing the program: the 3D solid with several slabs through every copper layer.
@details `pcbthermal/solid3d.py` is read as text, the one line that adds the copper slab of a layer (`add("cu", l, tc[l], kx, kz)`) is replaced by a loop of `N_CU` equal slabs and the
         result is executed as a module named `solid3d_sub` in the package namespace (so its relative imports work). The copper slab of a layer is then `N_CU` slabs of the same
         conductivities; the heat of a part still enters the first (top) slab, the films see half of the first or last slab, and the vertical links between the copper sub-slabs are
         half a slab plus half a slab. The program file is not changed. Used by `study_options.py`.
         The change that the program would need is the same one line plus the reading of the layer temperature (the mean over the sub-slabs, the first for the surface).
"""

import importlib.util
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import pcbthermal  # noqa: E402,F401

_OLD = 'add("cu", l, tc[l], kx, kz)'
_NEW = '[add("cu", l, tc[l] / N_CU, kx, kz) for _ in range(N_CU)]'


def load(n_cu):
    """!
    @brief Build the patched solid module with `n_cu` slabs per copper layer.
    @param n_cu Slabs through every copper layer (1 is the program's own rule).
    @return The module (functions `Solid`, `solve_steady` as in pcbthermal.solid3d; `Solid.board_slab[l]` is the first (top) sub-slab of layer l).
    @throws RuntimeError If the program's line changed and the patch does not apply.
    """
    path = os.path.join(ROOT, "pcbthermal", "solid3d.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    if src.count(_OLD) != 1:
        raise RuntimeError("the copper-slab line of solid3d.py was not found exactly once")
    src = src.replace(_OLD, _NEW)
    spec = importlib.util.spec_from_loader("pcbthermal.solid3d_sub", loader=None, origin=path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "pcbthermal"
    mod.N_CU = int(n_cu)
    sys.modules["pcbthermal.solid3d_sub"] = mod
    exec(compile(src, path, "exec"), mod.__dict__)
    mod.N_CU = int(n_cu)
    return mod
